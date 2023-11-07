import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

def ParseArguments():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('--configFile', dest = 'configFile', required = True, help = 'JSON Configuration file')
    parser.add_argument ('--acVersion', dest = 'acVersion', nargs = '+', type = str, required = True, help = 'Archicad version number list. Ex: "26 27"')
    parser.add_argument ('--language', dest = 'language', nargs = '+', type = str, required = False, help = 'Add-On language code list. Ex: "INT GER". Specify "ALL" for all languages in the configfile.' )
    parser.add_argument ('--devKitPath', dest = 'devKitPath', type = str, required = False, help = 'Path to local APIDevKit')
    parser.add_argument ('--release', dest = 'release', required = False, action='store_true', help = 'Build in localized Release mode.')
    parser.add_argument ('--package', dest = 'package', required = False, action='store_true', help = 'Create zip archive.')
    return parser.parse_args ()

def AddRunPermissionToResConv(devKitFolder):
    permissionParams = []
    permissionParams.append ('chmod')
    permissionParams.append ('+x')
    permissionParams.append (str(devKitFolder / 'Support' / 'Tools' / 'OSX' / 'ResConv'))
    permissionResult = subprocess.call (permissionParams)
    return permissionResult == 0

def PrepareDirectories(rootFolder, buildFolder, packageRootFolder, devKitFolderList, args, configData, platformName):
    if not buildFolder.exists():
        buildFolder.mkdir(parents=True)

    if args.package:
        if (packageRootFolder).exists():
            shutil.rmtree (packageRootFolder)

    # Set APIDevKit directory if local is used, else create new directories
    if args.devKitPath is not None:
        devKitFolderList[args.acVersion[0]] = pathlib.Path(args.devKitPath)
    else:
        # For every ACVersion
        # Check if APIDevKitLink is provided
        # Create directory for APIDevKit
        # Download APIDevKit
        for version in args.acVersion:
            if version in configData['devKitLinks']:

                devKitFolder = rootFolder / f'APIDevKit-{version}'
                if not devKitFolder.exists():
                    devKitFolder.mkdir()

                devKitFolderList[version] = devKitFolder
                DownloadAndUnzip(configData['devKitLinks'][version], devKitFolder, platformName)

            else:
                print('APIDevKit download link not provided')
                return 1
        
    return 0

def DownloadAndUnzip (url, dest, platformName):
    # https://github.com/GRAPHISOFT/archicad-api-devkit/releases/download/<tag>/ <filename>
    # https://github.com/GRAPHISOFT/archicad-api-devkit/releases/latest/download/ <filename>   - not used, as there isn't a single latest version

    version = url.split('/')[-1]
    fileName = f'API.Development.Kit.{platformName}.{version}.zip'
    url = f'{url}/{fileName}'
    filePath = pathlib.Path(dest, fileName)
    if filePath.exists():
        return

    print (f'Downloading {fileName}')
    urllib.request.urlretrieve (url, filePath)

    print (f'Unzipping {fileName}')
    if platform.system () == 'Windows':
        with zipfile.ZipFile (filePath, 'r') as zip:
            zip.extractall (dest)
    elif platform.system () == 'Darwin':
        subprocess.call ([
            'unzip', '-qq', filePath,
            '-d', dest
        ])

def BuildAddOn (rootFolder, buildFolder, devKitFolder, version, addOnName, platformName, configuration, optionalParams, languageCode=None):
    buildPath = buildFolder / addOnName / version
    if languageCode is not None:
        buildPath = buildPath / languageCode

    # Add params to configure cmake
    projGenParams = []
    projGenParams.append ('cmake')
    projGenParams.extend (['-B', str(buildPath)])

    if platformName == 'WIN':
        projGenParams.extend (['-G', 'Visual Studio 16 2019'])
        projGenParams.extend (['-T', 'v142'])
    elif platformName == 'MAC':
        projGenParams.extend (['-G', 'Xcode'])

    projGenParams.append (f'-DAC_API_DEVKIT_DIR={str(devKitFolder / "Support")}')
    projGenParams.append (f'-DCMAKE_BUILD_TYPE={configuration}')

    if languageCode is not None:
        projGenParams.append (f'-DAC_ADDON_LANGUAGE={languageCode}')

    if optionalParams is not None:
        for key in optionalParams:
            projGenParams.append (f'-D{key}={optionalParams[key]}')

    projGenParams.append (str(rootFolder))

    projGenResult = subprocess.call (projGenParams)
    if projGenResult != 0:
        print ('Failed to generate project')
        return 1

    # Add params to build AddOn
    buildParams = []
    buildParams.append ('cmake')
    buildParams.extend (['--build', str(buildPath)])
    buildParams.extend (['--config', configuration])

    buildResult = subprocess.call (buildParams)
    if buildResult != 0:
        print ('Failed to build project')
        return 1

    return 0

def CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, configuration, languageCode=None, isRelease=False):
    packageFolder = packageRootFolder / version
    sourceFolder = buildFolder / addOnName / version

    if languageCode is not None:
        packageFolder = packageFolder / languageCode
        sourceFolder = sourceFolder / languageCode
    sourceFolder = sourceFolder / configuration

    if not packageFolder.exists():
        packageFolder.mkdir(parents=True)

    fileName = addOnName
    if not isRelease:
        fileName = f'{fileName}_{configuration}'

    if platformName == 'WIN':
        shutil.copy (
            sourceFolder / f'{addOnName}.apx',
            packageFolder / f'{fileName}.apx',
        )
        if configuration == 'Debug':
            shutil.copy (
            sourceFolder / f'{addOnName}.pdb',
            packageFolder / f'{fileName}.pdb',
        )

    elif platformName == 'MAC':
        subprocess.call ([
            'cp', '-r',
            sourceFolder / f'{addOnName}.bundle',
            packageFolder / f'{fileName}.bundle'
        ])



def Main():
    args = ParseArguments()

    if args.language is None and args.release:
        print('Must specify AddOn language for release version')
        return 1

    if args.devKitPath is not None and len(args.acVersion) != 1:
        print('Only one Archicad version supported with local APIDevKit option')
        return 1

    # Check platform operating system
    platformName = None
    if platform.system () == 'Windows':
        platformName = 'WIN'
    elif platform.system () == 'Darwin':
        platformName = 'MAC'

    # Load config data
    configFile = open(args.configFile)
    configData = json.load(configFile)
    addOnName = configData['addOnName']

    optionalParams = None
    if 'addOnSpecificCMakeParameters' in configData:
        optionalParams = configData['addOnSpecificCMakeParameters']

    if args.language:
        configUpper = [lang.upper() for lang in configData['languages']]
        languageList = [lang.upper() for lang in args.language]
        if 'ALL' in languageList:
            languageList = configUpper
        else:
            for lang in languageList:
                if lang not in configUpper:
                    print('Language not supported')
                    return 1

    # Create directory for Build and Package
    rootFolder = pathlib.Path(__file__).parent.parent.absolute()
    buildFolder = rootFolder / 'Build'
    packageRootFolder = buildFolder / 'Package' / addOnName
    devKitFolderList = {}

    os.chdir (rootFolder)

    if PrepareDirectories(rootFolder, buildFolder, packageRootFolder, devKitFolderList, args, configData, platformName) != 0:
        return 1

    # At this point, devKitFolderList dictionary has all provided ACVersions as keys
    # For every ACVersion
    # Enable execute permission if running on Mac
    # If release, build Add-On for all languages with RelWithDebInfo configuration
    # Else build Add-On with Debug and RelWithDebInfo configurations, without language specified   
    # In each case, if package creation is enabled, copy the .apx/.bundle files to the Package directory
    for version in devKitFolderList:
        devKitFolder = devKitFolderList[version]

        if platformName == 'MAC':
            if not AddRunPermissionToResConv(devKitFolder):
                print ('Failed to grant permission')
                return 1

        if args.release is True:
            for languageCode in languageList:
                if BuildAddOn(rootFolder, buildFolder, devKitFolder, version, addOnName, platformName, 'RelWithDebInfo', optionalParams, languageCode) != 0:
                    return 1
                if args.package:
                    CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo', languageCode, True)

        else:
            if BuildAddOn(rootFolder, buildFolder, devKitFolder, version, addOnName, platformName, 'Debug', optionalParams) != 0:
                return 1
            if BuildAddOn(rootFolder, buildFolder, devKitFolder, version, addOnName, platformName, 'RelWithDebInfo', optionalParams) != 0:
                return 1
            if args.package:
                CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'Debug')
                CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo')

    # Zip packages
    if args.package:
        release = 'Release_Localized' if args.release else 'Daily'
        for version in args.acVersion:
            subprocess.call ([
                '7z', 'a',
                str(packageRootFolder.parent / f'{addOnName}-{version}_{release}_{platformName}.zip'),
                str(packageRootFolder / version / '*')
            ])

    print ('Build Successful')
    return 0

if __name__ == "__main__":
    Main ()
