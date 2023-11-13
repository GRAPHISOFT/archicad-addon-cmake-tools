import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile

def ParseArguments():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('-c', '--configFile', dest = 'configFile', required = True, help = 'JSON Configuration file')
    parser.add_argument ('-v', '--acVersion', dest = 'acVersion', nargs = '+', type = str, required = False, help = 'Archicad version number list. Ex: 26 27')
    parser.add_argument ('-l', '--language', dest = 'language', nargs = '+', type = str, required = False, help = 'Add-On language code list. Ex: INT GER. Specify ALL for all languages in the configfile.' )
    parser.add_argument ('-d', '--devKitPath', dest = 'devKitPath', type = str, required = False, help = 'Path to local APIDevKit')
    parser.add_argument ('-r', '--release', dest = 'release', required = False, action='store_true', help = 'Build in localized Release mode.')
    parser.add_argument ('-p', '--package', dest = 'package', required = False, action='store_true', help = 'Create zip archive.')
    args = parser.parse_args ()

    if args.devKitPath is not None and len(args.acVersion) != 1:
        raise Exception('Only one Archicad version supported with local APIDevKit option!')
    
    return args


def PrepareParameters(args):
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
    acVersionList = None
    languageList = None

    if args.acVersion:
        acVersionList = args.acVersion
    else:
        acVersionList = []
        for version in configData['devKitLinks']:
            acVersionList.append(version)

    # Get needed language codes
    if args.release:
        configLangUpper = [lang.upper() for lang in configData['languages']]
        languageList = ['ALL']
        if args.language is not None:
            languageList = [lang.upper() for lang in args.language]

        if 'ALL' in languageList:
            languageList = configLangUpper
        else:
            for lang in languageList:
                if lang not in configLangUpper:
                    raise Exception('Language not supported!')
                
    return [configData, platformName, addOnName, acVersionList, languageList]


def PrepareDirectories(args, configData, platformName, addOnName, acVersionList):
    # Create directory for Build and Package
    workspaceRootFolder = pathlib.Path(__file__).parent.absolute().parent.absolute()        # needed, because parent.parent.absolute() doesn't work when not running from workspace root
    buildFolder = workspaceRootFolder / 'Build'
    packageRootFolder = buildFolder / 'Package' / addOnName
    devKitFolderList = {}

    if not buildFolder.exists():
        buildFolder.mkdir(parents=True)

    if args.package:
        if (packageRootFolder).exists():
            shutil.rmtree (packageRootFolder)

    # Set APIDevKit directory if local is used, else create new directories
    if args.devKitPath is not None:
        devKitFolderList[acVersionList[0]] = pathlib.Path(args.devKitPath)
    else:
        # For every ACVersion
        # Check if APIDevKitLink is provided
        # Create directory for APIDevKit
        # Download APIDevKit
        for version in acVersionList:
            if version in configData['devKitLinks']:

                devKitFolder = workspaceRootFolder / f'APIDevKit-{version}'
                if not devKitFolder.exists():
                    devKitFolder.mkdir()

                devKitFolderList[version] = devKitFolder
                DownloadAndUnzip(configData['devKitLinks'][version], devKitFolder, platformName)

            else:
                raise Exception('APIDevKit download link not provided!')
            
    return [workspaceRootFolder, buildFolder, packageRootFolder, devKitFolderList]


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


def GetProjectGenerationParams(configData, workspaceRootFolder, buildPath, platformName, devKitFolder, version, configuration, languageCode, optionalParams):
    # Add params to configure cmake
    projGenParams = ['cmake',
                    '-B', str(buildPath)]

    if platformName == 'WIN':
        projGenParams.append (f'-G {configData["winCMakeProjectGenerator"]}')
        toolset = 'v142'
        if int(version) < 25:
            toolset = 'v141'
        projGenParams.append (f'-T {toolset}')
    elif platformName == 'MAC':
        projGenParams.extend (['-G', 'Xcode'])

    projGenParams.append (f'-DAC_API_DEVKIT_DIR={str(devKitFolder / "Support")}')
    projGenParams.append (f'-DCMAKE_BUILD_TYPE={configuration}')

    if languageCode is not None:
        projGenParams.append (f'-DAC_ADDON_LANGUAGE={languageCode}')

    if optionalParams is not None:
        for key in optionalParams:
            projGenParams.append (f'-D{key}={optionalParams[key]}')

    projGenParams.append (str(workspaceRootFolder))

    return projGenParams


def BuildAddOn (configData, platformName, workspaceRootFolder, buildFolder, devKitFolder, version, configuration, languageCode=None):
    addOnName = configData['addOnName']
    optionalParams = None
    if 'addOnSpecificCMakeParameters' in configData:
        optionalParams = configData['addOnSpecificCMakeParameters']

    buildPath = buildFolder / addOnName / version
    if languageCode is not None:
        buildPath = buildPath / languageCode

    # Add params to configure cmake
    projGenParams = GetProjectGenerationParams(configData, workspaceRootFolder, buildPath, platformName, devKitFolder, version, configuration, languageCode, optionalParams)
    projGenResult = subprocess.call (projGenParams)
    if projGenResult != 0:
        raise Exception('Failed to generate project!')
    

    # Add params to build AddOn
    buildParams = [
        'cmake',
        '--build', str(buildPath),
        '--config', configuration
        ]

    buildResult = subprocess.call (buildParams)
    if buildResult != 0:
        raise Exception('Failed to build project!')


def BuildAddOns(args, configData, platformName, languageList, workspaceRootFolder, buildFolder, devKitFolderList):
    # At this point, devKitFolderList dictionary has all provided ACVersions as keys
    # For every ACVersion
    # If release, build Add-On for all languages with RelWithDebInfo configuration
    # Else build Add-On with Debug and RelWithDebInfo configurations, without language specified   
    # In each case, if package creation is enabled, copy the .apx/.bundle files to the Package directory
    try:
        for version in devKitFolderList:
            devKitFolder = devKitFolderList[version]

            if args.release is True:
                for languageCode in languageList:
                    BuildAddOn(configData, platformName, workspaceRootFolder, buildFolder, devKitFolder, version, 'RelWithDebInfo', languageCode)

            else:
                BuildAddOn(configData, platformName, workspaceRootFolder, buildFolder, devKitFolder, version, 'Debug')
                BuildAddOn(configData, platformName, workspaceRootFolder, buildFolder, devKitFolder, version, 'RelWithDebInfo')

    except Exception as e:
                raise e



def checkIf7ZInstalled():
    try:
        subprocess.call('7z', stdout=subprocess.DEVNULL)
    except:
        raise Exception('7Zip not installed!')


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

# Zip packages
def PackageAddOns(args, addOnName, platformName, acVersionList, languageList, buildFolder, packageRootFolder):
    checkIf7ZInstalled()

    for version in acVersionList:
        if args.release:
            for languageCode in languageList:
                CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo', languageCode, True)
        else:
            CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'Debug')
            CopyResultToPackage(packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo')
        
        buildType = 'Release_Localized' if args.release else 'Daily'
        subprocess.call ([
            '7z', 'a',
            str(packageRootFolder.parent / f'{addOnName}-{version}_{buildType}_{platformName}.zip'),
            str(packageRootFolder / version / '*')
        ])

def Main():
    try:
        args = ParseArguments()

        [configData, platformName, addOnName, acVersionList, languageList] = PrepareParameters(args)

        [workspaceRootFolder, buildFolder, packageRootFolder, devKitFolderList] = PrepareDirectories(args, configData, platformName, addOnName, acVersionList)

        os.chdir (workspaceRootFolder)
        
        BuildAddOns(args, configData, platformName, languageList, workspaceRootFolder, buildFolder, devKitFolderList)

        if args.package:
            PackageAddOns(args, addOnName, platformName, acVersionList, languageList, buildFolder, packageRootFolder)

        print ('Build succeeded!')
        return 0
    
    except Exception as e:
        print(e)
        return 1

if __name__ == "__main__":
    Main ()
