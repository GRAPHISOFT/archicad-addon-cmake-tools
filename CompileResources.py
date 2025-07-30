import os
import sys
import platform
import subprocess
import shutil
import codecs
import argparse

class ResourceCompiler (object):
    def __init__ (self, devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization):
        self.devKitPath = devKitPath
        self.addonName = addonName
        self.languageCode = languageCode
        self.defaultLanguageCode = defaultLanguageCode
        self.sourcesPath = sourcesPath
        self.resourcesPath = resourcesPath
        self.resourceObjectsPath = resourceObjectsPath
        self.permissiveLocalization = permissiveLocalization
        self.resConvPath = None
        self.nativeResourceFileExtension = None
        
    def IsValid (self):
        if self.resConvPath == None:
            return False
        if not os.path.exists (self.resConvPath):
            return False
        return True

    def GetPrecompiledGRCResourceFilePath (self, grcFilePath):
        grcFileName = os.path.split (grcFilePath)[1]
        return os.path.join (self.resourceObjectsPath, grcFileName + '.i')

    def CompileJSONResourceFile (self, jsonFilePath, localized):
        jsonResourceProcessorPath = os.path.join (self.devKitPath, 'Tools', 'JSONResourceProcessor')
        schemaValidationResult = subprocess.call ([
            sys.executable,
            os.path.join (jsonResourceProcessorPath, 'SchemaValidator.py'),
            '-i', jsonFilePath,
            '-o', os.path.join (self.resourceObjectsPath, os.path.basename (jsonFilePath) + '.valid'),
            '--schemaFolder', os.path.join (self.devKitPath, 'Tools', 'SchemaFiles'),
        ])
        assert schemaValidationResult == 0, 'JSON Schema validation command failed: ' + jsonFilePath

        translatedJsonPath = jsonFilePath

        if localized:
            xliffFileToTranslateWith = None
            if self.languageCode == self.defaultLanguageCode:
                xliffFileToTranslateWith = os.path.join (self.resourcesPath, 'R' + self.defaultLanguageCode, self.addonName + '.xlf')
            else:
                childXliffPath = os.path.join (self.resourcesPath, 'ResourceLibrary', self.languageCode, 'XLF', self.addonName + '.xlf')
                parentTxtPath = os.path.join (self.resourcesPath, 'ResourceLibrary', self.languageCode, 'XLF', '_parent.txt')
                if os.path.exists (parentTxtPath):
                    parentLanguageCode = codecs.open (parentTxtPath, 'r', 'utf-8').read ().strip ()
                    parentXliffPath = os.path.join (self.resourcesPath, 'ResourceLibrary', parentLanguageCode, 'XLF', self.addonName + '.xlf')
                    mergedXliffOutputPath = os.path.join (self.resourceObjectsPath, self.addonName + '.merged.xlf')
                    mergeParentChildXliffResult = subprocess.call ([
                        sys.executable,
                        os.path.join (jsonResourceProcessorPath, 'MergeParentChildXliff.py'),
                        '--childXliff', childXliffPath,
                        '--parentXliff', parentXliffPath,
                        '-o', mergedXliffOutputPath
                    ])
                    assert mergeParentChildXliffResult == 0, 'Merge parent child XLIFF command failed: ' +  jsonFilePath
                    xliffFileToTranslateWith = mergedXliffOutputPath
                else:
                    xliffFileToTranslateWith = childXliffPath

            translatedJsonPath = os.path.join (self.resourceObjectsPath, os.path.basename (jsonFilePath) + '.translated')
            xliffTranslationCommand = [
                sys.executable,
                os.path.join (jsonResourceProcessorPath, 'XliffJsonTranslator.py'),
                '-i', jsonFilePath,
                '-m', self.addonName,
                '-d', xliffFileToTranslateWith,
                '-o', translatedJsonPath,
            ]
            if self.permissiveLocalization:
                xliffTranslationCommand.append ('--permissive')
            xliffTranslationResult = subprocess.call (xliffTranslationCommand)
            assert xliffTranslationResult == 0, 'XLIFF translation command failed: ' +  jsonFilePath

        envForJson = os.environ.copy ()
        if platform.system () == 'Windows':
            dllFolder = os.path.join (jsonResourceProcessorPath, 'dlls')
            envForJson['PATH'] = str (dllFolder) + os.pathsep + envForJson['PATH']
        elif platform.system () == 'Darwin':
            if platform.processor () == 'arm':
                envForJson['DYLD_FALLBACK_LIBRARY_PATH'] = os.path.join (jsonResourceProcessorPath, 'dylibs_ARM')
            else:
                envForJson['DYLD_FALLBACK_LIBRARY_PATH'] = os.path.join (jsonResourceProcessorPath, 'dylibs')
        else:
            assert False, 'Unsupported platform: ' + platform.system ()

        nativeResCreationResult = subprocess.call ([
            sys.executable,
            os.path.join (jsonResourceProcessorPath, 'GSCreateNativeResourceFromJSON.py'),
            '-i', translatedJsonPath,
            '-o', os.path.join (self.resourceObjectsPath, os.path.basename (jsonFilePath) + self.nativeResourceFileExtension),
            '-d', self.GetPlatformDefine (),
        ], env=envForJson)
        assert nativeResCreationResult == 0, 'Native resource creation command failed: ' + translatedJsonPath

        postCheckersCommand = [
            sys.executable,
            os.path.join (jsonResourceProcessorPath, 'RunPostCheckers.py'),
            '-i', jsonFilePath,
            '-o', os.path.join (self.resourceObjectsPath, os.path.basename (jsonFilePath) + '.postcheck'),
        ]
        if localized:
            postCheckersCommand.append ('--localized')
        postCheckersResult = subprocess.call (postCheckersCommand)
        assert postCheckersResult == 0, 'Post-checkers command failed: ' + jsonFilePath

    def CompileLocalizedResources (self):
        locResourcesFolder = os.path.join (self.resourcesPath, 'R' + self.languageCode)
        grcFiles = self.CollectFilesFromFolderWithExtension (locResourcesFolder, '.grc')
        for grcFilePath in grcFiles:
            assert self.CompileGRCResourceFile (grcFilePath), 'Failed to compile resource: ' + grcFilePath

        locResourcesFolderDefault = os.path.join (self.resourcesPath, 'R' + self.defaultLanguageCode)
        jsonFiles = self.CollectFilesFromFolderWithExtension (locResourcesFolderDefault, '.json')
        for jsonFilePath in jsonFiles:
            self.CompileJSONResourceFile (jsonFilePath, localized=True)

    def CompileFixResources (self):
        fixResourcesFolder = os.path.join (self.resourcesPath, 'RFIX')
        grcFiles = self.CollectFilesFromFolderWithExtension (fixResourcesFolder, '.grc')
        for grcFilePath in grcFiles:
            assert self.CompileGRCResourceFile (grcFilePath), 'Failed to compile resource: ' + grcFilePath

        jsonFiles = self.CollectFilesFromFolderWithExtension (fixResourcesFolder, '.json')
        for jsonFilePath in jsonFiles:
            self.CompileJSONResourceFile (jsonFilePath, localized=False)

    def RunResConv (self, platformSign, codepage, inputFilePath):
        imageResourcesFolder = os.path.join (self.resourcesPath, 'RFIX', 'Images')
        inputFileBaseName = os.path.splitext (os.path.split (inputFilePath)[1])[0]
        nativeResourceFilePath = os.path.join (self.resourceObjectsPath, inputFileBaseName + self.nativeResourceFileExtension)
        result = subprocess.call ([
            self.resConvPath,
            '-m', 'r',                        # resource compile mode
            '-T', platformSign,                # target platform
            '-q', 'utf8', codepage,            # code page conversion
            '-w', '2',                        # HiDPI image size list
            '-p', imageResourcesFolder,        # image search path
            '-i', inputFilePath,            # input path
            '-o', nativeResourceFilePath    # output path
        ])
        if result != 0:
            return False
        return True

    def CollectFilesFromFolderWithExtension (self, folderPath, extension):
        result = []
        if not os.path.exists (folderPath):
            return result
        for fileName in os.listdir (folderPath):
            fileExtension = os.path.splitext (fileName)[1]
            if fileExtension.lower () == extension.lower ():
                fullPath = os.path.join (folderPath, fileName)
                result.append (fullPath)
        return result

class WinResourceCompiler (ResourceCompiler):
    def __init__ (self, devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization):
        super (WinResourceCompiler, self).__init__ (devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
        self.resConvPath = os.path.join (devKitPath, 'Tools', 'Win', 'ResConv.exe')
        self.nativeResourceFileExtension = '.rc2'

    def GetPlatformDefine (self):
        return 'WINDOWS'

    def PrecompileGRCResourceFile (self, grcFilePath):
        precompiledGrcFilePath = self.GetPrecompiledGRCResourceFilePath (grcFilePath)
        result = subprocess.call ([
            'cl',
            '/nologo',
            '/X',
            '/EP',
            '/P',
            '/I', os.path.join (self.devKitPath, 'Inc'),
            '/I', os.path.join (self.devKitPath, 'Modules', 'DGLib'),
            '/I', self.sourcesPath,
            '/I', self.resourceObjectsPath,
            '/D' + self.GetPlatformDefine (),
            '/source-charset:utf-8',
            '/execution-charset:utf-8',
            '/Fi{}'.format (precompiledGrcFilePath),
            grcFilePath,
        ])
        assert result == 0, 'Failed to precompile resource ' + grcFilePath
        return precompiledGrcFilePath

    def CompileGRCResourceFile (self, grcFilePath):
        precompiledGrcFilePath = self.PrecompileGRCResourceFile (grcFilePath)
        return self.RunResConv ('W', '1252', precompiledGrcFilePath)

    def GetNativeResourceFile (self):
        defaultNativeResourceFile = os.path.join (self.resourcesPath, 'RFIX.win', 'AddOnMain.rc2')
        if os.path.exists (defaultNativeResourceFile):
            return defaultNativeResourceFile

        existingNativeResourceFiles = self.CollectFilesFromFolderWithExtension (os.path.join (self.resourcesPath, 'RFIX.win'), '.rc2')
        assert existingNativeResourceFiles, 'Native resource file was not found at RFIX.win folder'

        return existingNativeResourceFiles[0]

    def CompileNativeResource (self, resultResourcePath):
        nativeResourceFile = self.GetNativeResourceFile ()
        result = subprocess.call ([
            'rc',
            '/i', os.path.join (self.devKitPath, 'Inc'),
            '/i', os.path.join (self.devKitPath, 'Modules', 'DGLib'),
            '/i', self.sourcesPath,
            '/i', self.resourceObjectsPath,
            '/fo', resultResourcePath,
            nativeResourceFile
        ])
        assert result == 0, 'Failed to compile native resource ' + nativeResourceFile

class MacResourceCompiler (ResourceCompiler):
    def __init__ (self, devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization):
        super (MacResourceCompiler, self).__init__ (devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
        self.resConvPath = os.path.join (devKitPath, 'Tools', 'OSX', 'ResConv')
        self.nativeResourceFileExtension = '.ro'

    def GetPlatformDefine (self):
        return 'macintosh'

    def PrecompileGRCResourceFile (self, grcFilePath):
        precompiledGrcFilePath = self.GetPrecompiledGRCResourceFilePath (grcFilePath)
        result = subprocess.call ([
            'clang',
            '-x', 'c++',
            '-E',
            '-P',
            '-D' + self.GetPlatformDefine (),
            '-I', os.path.join (self.devKitPath, 'Inc'),
            '-I', os.path.join (self.devKitPath, 'Modules', 'DGLib'),
            '-I', self.sourcesPath,
            '-I', self.resourceObjectsPath,
            '-o', precompiledGrcFilePath,
            grcFilePath,
        ])
        assert result == 0, 'Failed to precompile resource ' + grcFilePath
        return precompiledGrcFilePath

    def CompileGRCResourceFile (self, grcFilePath):
        precompiledGrcFilePath = self.PrecompileGRCResourceFile (grcFilePath)
        return self.RunResConv ('M', 'utf16', precompiledGrcFilePath)

    def CompileNativeResource (self, resultResourcePath):
        resultLocalizedResourcePath = os.path.join (resultResourcePath, 'English.lproj')
        if not os.path.exists (resultLocalizedResourcePath):
            os.makedirs (resultLocalizedResourcePath)
        resultLocalizableStringsPath = os.path.join (resultLocalizedResourcePath, 'Localizable.strings')
        resultLocalizableStringsFile = codecs.open (resultLocalizableStringsPath, 'w', 'utf-16')
        for fileName in os.listdir (self.resourceObjectsPath):
            filePath = os.path.join (self.resourceObjectsPath, fileName)
            extension = os.path.splitext (fileName)[1].lower ()
            if extension == '.tif':
                shutil.copy (filePath, resultResourcePath)
            elif extension == '.rsrd':
                shutil.copy (filePath, resultLocalizedResourcePath)
            elif extension == '.strings':
                stringsFile = codecs.open (filePath, 'r', 'utf-16')
                resultLocalizableStringsFile.write (stringsFile.read ())
                stringsFile.close ()
        resultLocalizableStringsFile.close ()

def Main (argv):
    parser = argparse.ArgumentParser (description = 'Archicad Add-On Resource Compiler.')
    parser.add_argument ('addonName', help = 'Name of the Add-On.')
    parser.add_argument ('languageCode', help = 'Language code of the Add-On.')
    parser.add_argument ('defaultLanguageCode', help = 'Default language code of the Add-On.')
    parser.add_argument ('devKitPath', help = 'Path of the Archicad Development Kit.')
    parser.add_argument ('sourcesPath', help = 'Path of the sources folder of the Add-On.')
    parser.add_argument ('resourcesPath', help = 'Path of the resources folder of the Add-On.')
    parser.add_argument ('resourceObjectsPath', help = 'Path of the folder to build resource objects.')
    parser.add_argument ('resultResourcePath', help = 'Path of the resulting resource.')
    parser.add_argument ('--permissiveLocalization', action='store_true', help = 'Enable permissive localization mode.', default = False)
    args = parser.parse_args ()

    currentDir = os.path.dirname (os.path.abspath (__file__))
    os.chdir (currentDir)

    addonName = args.addonName
    languageCode = args.languageCode
    defaultLanguageCode = args.defaultLanguageCode
    devKitPath = os.path.abspath (args.devKitPath)
    sourcesPath = os.path.abspath (args.sourcesPath)
    resourcesPath = os.path.abspath (args.resourcesPath)
    resourceObjectsPath = os.path.abspath (args.resourceObjectsPath)
    resultResourcePath = os.path.abspath (args.resultResourcePath)
    permissiveLocalization = args.permissiveLocalization

    resourceCompiler = None
    system = platform.system ()
    if system == 'Windows':
        resourceCompiler = WinResourceCompiler (devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
    elif system == 'Darwin':
        resourceCompiler = MacResourceCompiler (devKitPath, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)

    assert resourceCompiler, 'Platform is not supported'
    assert resourceCompiler.IsValid (), 'Invalid resource compiler'

    resourceCompiler.CompileLocalizedResources ()
    resourceCompiler.CompileFixResources ()
    resourceCompiler.CompileNativeResource (resultResourcePath)

    return 0

sys.exit (Main (sys.argv))