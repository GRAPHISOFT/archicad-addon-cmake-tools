import os
import sys
import platform
import subprocess
import shutil
import codecs
import argparse
import re
import json
import pathlib
from pathlib import Path

class ResourceCompiler (object):
    def __init__ (self, devKitPath: Path, acVersion: str, buildNum: str, addonName: str, languageCode: str, defaultLanguageCode: str, sourcesPath: Path, resourcesPath: Path, resourceObjectsPath: Path, permissiveLocalization: bool):
        self.devKitPath = devKitPath
        self.acVersion = acVersion
        self.buildNum = buildNum
        self.addonName = addonName
        self.languageCode = languageCode
        self.defaultLanguageCode = defaultLanguageCode
        self.sourcesPath = sourcesPath
        self.resourcesPath = resourcesPath
        self.resourceObjectsPath = resourceObjectsPath
        self.permissiveLocalization = permissiveLocalization
        self.resConvPath = None
        self.nativeResourceFileExtension = None
    
    def GetPlatformDevKitLinkKey (self) -> str:
        return ""

    def GetDevKitVersionAndBuildNumber (self) -> tuple[int, int]:
        if self.buildNum != "default":
            return (int (self.acVersion), int (self.buildNum))
        devKitDataPath = pathlib.Path (__file__).absolute ().parent / 'APIDevKitLinks.json'
        with open (devKitDataPath, 'r') as devKitDataFile:
            devKitData = json.load (devKitDataFile)

        devkit_verison_regex = re.search(rf'API\.Development\.Kit\.{self.GetPlatformDevKitLinkKey()}\.(\d+)\.(\d+)',
                                         devKitData[self.GetPlatformDevKitLinkKey()][self.acVersion],
                                         re.IGNORECASE)
        if devkit_verison_regex:
            main_version = devkit_verison_regex.group(1)
            build_number = devkit_verison_regex.group(2)

        return (int (main_version), int (build_number))

    def IsValid (self) -> bool:
        if self.resConvPath is None:
            return False
        if not self.resConvPath.exists ():
            return False
        return True

    def GetPrecompiledGRCResourceFilePath (self, grcFilePath: Path) -> Path:
        grcFileName = grcFilePath.name
        return self.resourceObjectsPath / f'{grcFileName}.i'

    def CompileJSONResourceFile (self, jsonFilePath: Path, localized: bool) -> None:
        jsonResourceProcessorPath = self.devKitPath / 'Tools' / 'JSONResourceProcessor'
        schemaValidationResult = subprocess.call ([
            sys.executable,
            jsonResourceProcessorPath / 'SchemaValidator.py',
            '-i', jsonFilePath,
            '-o', self.resourceObjectsPath / f'{jsonFilePath.name}.valid',
            '--schemaFolder', self.devKitPath / 'Tools' / 'SchemaFiles',
        ])
        assert schemaValidationResult == 0, 'JSON Schema validation command failed: ' + jsonFilePath

        translatedJsonPath = jsonFilePath

        if localized:
            xliffFileToTranslateWith = None
            if self.languageCode == self.defaultLanguageCode:
                xliffFileToTranslateWith = self.resourcesPath / f'R{self.defaultLanguageCode}' / f'{self.addonName}.xlf'
            else:
                childXliffPath = self.resourcesPath / 'ResourceLibrary' / self.languageCode / 'XLF' / f'{self.addonName}.xlf'
                parentTxtPath = self.resourcesPath / 'ResourceLibrary' / self.languageCode / 'XLF' / '_parent.txt'
                if parentTxtPath.exists ():
                    parentLanguageCode = codecs.open (parentTxtPath, 'r', 'utf-8').read ().strip ()
                    parentXliffPath = self.resourcesPath / 'ResourceLibrary' / parentLanguageCode / 'XLF' / f'{self.addonName}.xlf'
                    mergedXliffOutputPath = self.resourceObjectsPath / f'{self.addonName}.merged.xlf'
                    mergeParentChildXliffResult = subprocess.call ([
                        sys.executable,
                        jsonResourceProcessorPath / 'MergeParentChildXliff.py',
                        '--childXliff', childXliffPath,
                        '--parentXliff', parentXliffPath,
                        '-o', mergedXliffOutputPath
                    ])
                    assert mergeParentChildXliffResult == 0, 'Merge parent child XLIFF command failed: ' +  jsonFilePath
                    xliffFileToTranslateWith = mergedXliffOutputPath
                else:
                    xliffFileToTranslateWith = childXliffPath

            translatedJsonPath = self.resourceObjectsPath / f'{jsonFilePath.name}.translated'
            xliffTranslationCommand = [
                sys.executable,
                jsonResourceProcessorPath / 'XliffJsonTranslator.py',
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
            dllFolder = jsonResourceProcessorPath / 'dlls'
            envForJson['PATH'] = str (dllFolder) + os.pathsep + envForJson['PATH']
        elif platform.system () == 'Darwin':
            if platform.processor () == 'arm':
                envForJson['DYLD_FALLBACK_LIBRARY_PATH'] = jsonResourceProcessorPath / 'dylibs_ARM'
            else:
                envForJson['DYLD_FALLBACK_LIBRARY_PATH'] = jsonResourceProcessorPath / 'dylibs'
        else:
            assert False, 'Unsupported platform: ' + platform.system ()

        jsonPartsDir = self.resourceObjectsPath / 'JsonParts'

        if not jsonPartsDir.exists ():
            jsonPartsDir.mkdir (parents=True, exist_ok=True)

        nativeResCreationCommand = [
            sys.executable,
            jsonResourceProcessorPath / 'GSCreateNativeResourceFromJSON.py',
            '-i', translatedJsonPath,
            '-o', jsonPartsDir / (jsonFilePath.name + self.nativeResourceFileExtension),
            '-d', self.GetPlatformDefine (),
        ]
        if not localized:
            imageResourcesFolder = self.resourcesPath / 'RFIX' / 'Images'
            nativeResCreationCommand.extend ([ '-p', imageResourcesFolder ])

        nativeResCreationResult = subprocess.call (nativeResCreationCommand, env=envForJson)

        assert nativeResCreationResult == 0, 'Native resource creation command failed: ' + translatedJsonPath

        postCheckersCommand = [
            sys.executable,
            jsonResourceProcessorPath / 'RunPostCheckers.py',
            '-i', jsonFilePath,
            '-o', self.resourceObjectsPath / f'{jsonFilePath.name}.postcheck',
        ]
        if localized:
            postCheckersCommand.append ('--localized')
        postCheckersResult = subprocess.call (postCheckersCommand)
        assert postCheckersResult == 0, 'Post-checkers command failed: ' + jsonFilePath

    def CompileLocalizedResources (self) -> None:
        locResourcesFolder = self.resourcesPath / f'R{self.languageCode}'
        grcFiles = locResourcesFolder.glob ('*.grc')
        for grcFilePath in grcFiles:
            assert self.CompileGRCResourceFile (grcFilePath), 'Failed to compile resource: ' + grcFilePath

        locResourcesFolderDefault = self.resourcesPath / f'R{self.defaultLanguageCode}'
        jsonFiles = locResourcesFolderDefault.glob ('*.json')
        for jsonFilePath in jsonFiles:
            self.CompileJSONResourceFile (jsonFilePath, localized=True)

    def CompileFixResources (self) -> None:
        fixResourcesFolder = self.resourcesPath / 'RFIX'
        grcFiles = fixResourcesFolder.glob ('*.grc')
        for grcFilePath in grcFiles:
            assert self.CompileGRCResourceFile (grcFilePath), 'Failed to compile resource: ' + grcFilePath

        jsonFiles = fixResourcesFolder.glob ('*.json')
        for jsonFilePath in jsonFiles:
            self.CompileJSONResourceFile (jsonFilePath, localized=False)

    def RunResConv (self, platformSign: str, codepage: str, inputFilePath: Path) -> bool:
        imageResourcesFolder = self.resourcesPath / 'RFIX' / 'Images'
        inputFileBaseName = inputFilePath.stem
        nativeResourceFilePath = self.resourceObjectsPath / (inputFileBaseName + self.nativeResourceFileExtension)
        colorChangeScriptPath = self.resConvPath.parent / 'SVGColorChange.py'
        call_params = [
            self.resConvPath,
            '-m', 'r',                      # resource compile mode
            '-T', platformSign,             # target platform
            '-q', 'utf8', codepage,         # code page conversion
            '-w', '2',                      # HiDPI image size list
            '-p', imageResourcesFolder,     # image search path
            '-i', inputFilePath,            # input path
            '-o', nativeResourceFilePath    # output path
        ]

        devkit_main_version, devkit_build_number= self.GetDevKitVersionAndBuildNumber ()
        if (devkit_main_version > 29 or
            (devkit_main_version == 29 and devkit_build_number >= 3000)):
            call_params.extend (['-py', sys.executable])        # python executable
            call_params.extend (['-sc', colorChangeScriptPath]) # SVG color change script path for generating Dark Mode icons
        result = subprocess.call (call_params)
        if result != 0:
            return False
        return True

class WinResourceCompiler (ResourceCompiler):
    def __init__ (self, devKitPath: Path, acVersion: str, buildNum: str, addonName: str, languageCode: str, defaultLanguageCode: str, sourcesPath: Path, resourcesPath: Path, resourceObjectsPath: Path, permissiveLocalization: bool):
        super (WinResourceCompiler, self).__init__ (devKitPath, acVersion, buildNum, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
        self.resConvPath = devKitPath / 'Tools' / 'Win' / 'ResConv.exe'
        self.nativeResourceFileExtension = '.rc2'

    def GetPlatformDevKitLinkKey(self) -> str:
        return "WIN"

    def GetPlatformDefine (self) -> str:
        return 'WINDOWS'

    def PrecompileGRCResourceFile (self, grcFilePath: Path) -> Path:
        precompiledGrcFilePath = self.GetPrecompiledGRCResourceFilePath (grcFilePath)
        result = subprocess.call ([
            'cl',
            '/nologo',
            '/X',
            '/EP',
            '/P',
            '/I', self.devKitPath / 'Inc',
            '/I', self.devKitPath / 'Modules' / 'DGLib',
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

    def CompileGRCResourceFile (self, grcFilePath: Path) -> bool:
        precompiledGrcFilePath = self.PrecompileGRCResourceFile (grcFilePath)
        return self.RunResConv ('W', '1252', precompiledGrcFilePath)

    def GetNativeResourceFile (self) -> Path:
        defaultNativeResourceFile = self.resourcesPath / 'RFIX.win' / 'AddOnMain.rc2'
        if defaultNativeResourceFile.exists ():
            return defaultNativeResourceFile

        existingNativeResourceFiles = (self.resourcesPath / 'RFIX.win').glob ('*.rc2')
        assert existingNativeResourceFiles, 'Native resource file was not found at RFIX.win folder'

        return existingNativeResourceFiles[0]

    def CompileNativeResource (self, resultResourcePath: Path) -> None:
        nativeResourceFile = self.GetNativeResourceFile ()
        result = subprocess.call ([
            'rc',
            '/i', self.devKitPath / 'Inc',
            '/i', self.devKitPath / 'Modules' / 'DGLib',
            '/i', self.sourcesPath,
            '/i', self.resourceObjectsPath,
            '/fo', resultResourcePath,
            nativeResourceFile
        ])
        assert result == 0, 'Failed to compile native resource ' + nativeResourceFile

class MacResourceCompiler (ResourceCompiler):
    def __init__ (self, devKitPath: Path, acVersion: str, buildNum: str, addonName: str, languageCode: str, defaultLanguageCode: str, sourcesPath: Path, resourcesPath: Path, resourceObjectsPath: Path, permissiveLocalization: bool):
        super (MacResourceCompiler, self).__init__ (devKitPath, acVersion, buildNum, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
        self.resConvPath = devKitPath / 'Tools' / 'OSX' / 'ResConv'
        self.nativeResourceFileExtension = '.ro'

    def GetPlatformDevKitLinkKey(self) -> str:
        return "MAC"

    def GetPlatformDefine (self) -> str:
        return 'macintosh'

    def PrecompileGRCResourceFile (self, grcFilePath: Path) -> Path:
        precompiledGrcFilePath = self.GetPrecompiledGRCResourceFilePath (grcFilePath)
        result = subprocess.call ([
            'clang',
            '-x', 'c++',
            '-E',
            '-P',
            '-D' + self.GetPlatformDefine (),
            '-I', self.devKitPath / 'Inc',
            '-I', self.devKitPath / 'Modules' / 'DGLib',
            '-I', self.sourcesPath,
            '-I', self.resourceObjectsPath,
            '-o', precompiledGrcFilePath,
            grcFilePath,
        ])
        assert result == 0, 'Failed to precompile resource ' + grcFilePath
        return precompiledGrcFilePath

    def CompileGRCResourceFile (self, grcFilePath: Path) -> bool:
        precompiledGrcFilePath = self.PrecompileGRCResourceFile (grcFilePath)
        return self.RunResConv ('M', 'utf16', precompiledGrcFilePath)

    def CompileNativeResource (self, resultResourcePath: Path) -> None:
        resultLocalizedResourcePath = resultResourcePath / 'English.lproj'
        if not resultLocalizedResourcePath.exists ():
            resultLocalizedResourcePath.mkdir (parents=True)
        resultLocalizableStringsPath = resultLocalizedResourcePath / 'Localizable.strings'
        resultLocalizableStringsFile = codecs.open (resultLocalizableStringsPath, 'w', 'utf-16')
        for fileName in self.resourceObjectsPath.iterdir ():
            filePath = self.resourceObjectsPath / fileName
            extension = fileName.suffix.lower ()
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
    parser.add_argument ('acVersion', help = 'Archicad version the Add-On is building for.')
    parser.add_argument ('buildNum', help = 'Development Kit build number.')
    parser.add_argument ('devKitPath', help = 'Path of the Archicad Development Kit.')
    parser.add_argument ('sourcesPath', help = 'Path of the sources folder of the Add-On.')
    parser.add_argument ('resourcesPath', help = 'Path of the resources folder of the Add-On.')
    parser.add_argument ('resourceObjectsPath', help = 'Path of the folder to build resource objects.')
    parser.add_argument ('resultResourcePath', help = 'Path of the resulting resource.')
    parser.add_argument ('--permissiveLocalization', action='store_true', help = 'Enable permissive localization mode.', default = False)
    args = parser.parse_args ()

    currentDir = Path (__file__).parent
    os.chdir (currentDir)

    addonName = args.addonName
    languageCode = args.languageCode
    defaultLanguageCode = args.defaultLanguageCode
    acVersion = args.acVersion
    buildNum = args.buildNum
    devKitPath = Path (args.devKitPath)
    sourcesPath = Path (args.sourcesPath)
    resourcesPath = Path (args.resourcesPath)
    resourceObjectsPath = Path (args.resourceObjectsPath)
    resultResourcePath = Path (args.resultResourcePath)
    permissiveLocalization = args.permissiveLocalization

    resourceCompiler = None
    system = platform.system ()
    if system == 'Windows':
        resourceCompiler = WinResourceCompiler (devKitPath, acVersion, buildNum, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)
    elif system == 'Darwin':
        resourceCompiler = MacResourceCompiler (devKitPath, acVersion, buildNum, addonName, languageCode, defaultLanguageCode, sourcesPath, resourcesPath, resourceObjectsPath, permissiveLocalization)

    assert resourceCompiler, 'Platform is not supported'
    assert resourceCompiler.IsValid (), 'Invalid resource compiler'

    resourceCompiler.CompileLocalizedResources ()
    resourceCompiler.CompileFixResources ()
    resourceCompiler.CompileNativeResource (resultResourcePath)

    return 0

sys.exit (Main (sys.argv))