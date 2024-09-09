import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import traceback
import urllib.parse
import urllib.request
import zipfile
import tarfile

def ParseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('-c', '--configFile', dest = 'configFile', required = True, help = 'JSON Configuration file')
    parser.add_argument ('-v', '--acVersion', dest = 'acVersion', nargs = '+', type = str, required = False, help = 'Archicad version number list. Ex: 26 27')
    parser.add_argument ('-b', '--buildConfig', dest = 'buildConfig', nargs = '+', type = str, required = False, help = 'Build configuration list. Ex: Debug Release RelWithDebInfo')
    parser.add_argument ('-l', '--allLocalizedVersions', dest = 'allLocalizedVersions', required = False, action='store_true', help = 'Create localized release builds for all configured languages.')
    parser.add_argument ('-d', '--devKitPath', dest = 'devKitPath', type = str, required = False, help = 'Path to local APIDevKit')
    parser.add_argument ('-n', '--buildNum', dest = 'buildNum', type = str, required = False, help = 'Build number of local APIDevKit')
    parser.add_argument ('-p', '--package', dest = 'package', required = False, action='store_true', help = 'Create zip archive.')
    parser.add_argument ('-a', '--additionalCMakeParams', dest = 'additionalCMakeParams', nargs = '+', required = False, help = 'Add-On specific CMake parameter list of key=value pairs. Ex: var1=value1 var2="value 2"')
    parser.add_argument ('-q', '--quiet', dest = 'quiet', required = False, action='store_true', help = 'Less verbose cmake output.')
    args = parser.parse_args ()

    if args.devKitPath is not None:
        if args.acVersion is None or args.buildNum is None:
            raise Exception ('Must provide Archicad version and APIDevKit build number with local APIDevKit option!')
        if len (args.acVersion) != 1:
            raise Exception ('Only one Archicad version supported with local APIDevKit option!')

    if args.buildConfig is not None:
        for config in args.buildConfig:
            if config != 'Debug' and config != 'RelWithDebInfo' and config != 'Release':
                raise Exception ('Invalid build configuration! Options are: Debug, Release, RelWithDebInfo')

    return args


def GetPlatformName ():
    if platform.system () == 'Windows':
        return 'WIN'
    elif platform.system () == 'Darwin':
        return 'MAC'


def CallCommand (params, quiet = False):
    if quiet:
        result = subprocess.call (params, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    else:
        result = subprocess.call (params)
    return result


def PrepareParameters (args):
    # Check platform operating system
    platformName = GetPlatformName ()

    # Load DevKit download data
    devKitDataPath = pathlib.Path (__file__).absolute ().parent / 'APIDevKitLinks.json'
    with open (devKitDataPath, 'r') as devKitDataFile:
        devKitData = json.load (devKitDataFile)

    # Load config data
    configPath = pathlib.Path (args.configFile)
    if configPath.is_dir ():
        raise Exception (f'{configPath} is a directory!')
    with open (configPath, 'r') as configFile:
        configData = json.load (configFile)

    addOnName = configData['addOnName']
    acVersionList = None
    buildConfigList = None

    if args.acVersion:
        acVersionList = args.acVersion
    else:
        acVersionList = devKitData[platformName].keys ()

    if args.buildConfig:
        buildConfigList = args.buildConfig
    else:
        buildConfigList = ['RelWithDebInfo']    

    # Get needed language codes
    languageList = [configData['defaultLanguage'].upper ()]
    if args.allLocalizedVersions:
        languageList = [lang.upper () for lang in configData['languages']]

    # Get additional CMake parameters
    additionalParams = None
    if 'additionalCMakeParams' in configData or args.additionalCMakeParams:
        additionalParams = {}

        if 'additionalCMakeParams' in configData:
            additionalParams = configData['additionalCMakeParams']

        if args.additionalCMakeParams:
            for param in args.additionalCMakeParams:
                if '=' not in param:
                    additionalParams[param] = 'ON'
                else:
                    key, value = param.split ('=', 1)
                    if not value:
                        raise Exception (f'Value not provided for {key}!')
                    additionalParams[key] = value

    return [devKitData, addOnName, buildConfigList, acVersionList, languageList, additionalParams]


def PrepareDirectories (args, devKitData, addOnName, acVersionList):
    # Create directory for Build and Package
    workspaceRootFolder = pathlib.Path (__file__).parent.absolute ().parent.absolute ()
    buildFolder = workspaceRootFolder / 'Build'
    packageRootFolder = buildFolder / 'Package' / addOnName
    devKitFolderList = {}

    platformName = GetPlatformName ()

    if not buildFolder.exists ():
        buildFolder.mkdir (parents=True)

    if args.package:
        if (packageRootFolder).exists ():
            shutil.rmtree (packageRootFolder)

    # Set APIDevKit directory if local is used, else create new directories
    if args.devKitPath is not None:
        devKitPath = pathlib.Path (args.devKitPath)
        if not devKitPath.is_dir ():
            raise Exception (f'{devKitPath} is not a directory!')
        devKitFolderList[acVersionList[0]] = devKitPath
    else:
        for version in acVersionList:
            if version in devKitData[platformName]:

                devKitFolder = buildFolder / 'DevKit' / f'APIDevKit-{version}'
                if not devKitFolder.exists ():
                    devKitFolder.mkdir (parents=True)

                devKitFolderList[version] = devKitFolder
                DownloadAndUnzip (devKitData[platformName][version], devKitFolder)

            else:
                raise Exception ('APIDevKit download link not provided!')

    return [workspaceRootFolder, buildFolder, packageRootFolder, devKitFolderList]


def DownloadAndUnzip (url, dest):
    fileName = url.split ('/')[-1]
    filePath = pathlib.Path (dest, fileName)
    if filePath.exists ():
        return

    print (f'Downloading {fileName}')
    urllib.request.urlretrieve (url, filePath)

    print (f'Extracting {fileName}')

    if platform.system () == 'Windows':
        if zipfile.is_zipfile (filePath):
            with zipfile.ZipFile (filePath, 'r') as zip:
                zip.extractall (path=dest)
    elif platform.system () == 'Darwin':
        if tarfile.is_tarfile (filePath):
            with tarfile.open (filePath, 'r:gz') as tar:
                tar.extractall (path=dest)
        else:
            CallCommand ([
            'unzip', '-qq', filePath,
            '-d', dest
        ])


def GetInstalledVisualStudioGenerator ():
    vsWherePath = pathlib.Path (os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio' / 'Installer' / 'vswhere.exe'
    if not vsWherePath.exists ():
        raise Exception ('Microsoft Visual Studio Installer not found!')
    vsWhereOutputStr = subprocess.check_output ([vsWherePath, '-sort', '-format', 'json', '-utf8'])
    vsWhereOutput = json.loads (vsWhereOutputStr)
    if len (vsWhereOutput) == 0:
        raise Exception ('No installed Visual Studio detected!')
    vsVersion = vsWhereOutput[0]['installationVersion'].split ('.')[0]
    if vsVersion == '17':
        return 'Visual Studio 17 2022'
    elif vsVersion == '16':
        return 'Visual Studio 16 2019'
    else:
        raise Exception ('Installed Visual Studio version not supported!')


def GetProjectGenerationParams (workspaceRootFolder, buildPath, addOnName, platformName, devKitFolder, version, languageCode, additionalParams):
    # Add params to configure cmake
    projGenParams = [
        'cmake',
        '-B', str (buildPath)
    ]

    if platformName == 'WIN':
        vsGenerator = GetInstalledVisualStudioGenerator ()
        projGenParams.append (f'-G {vsGenerator}')
        toolset = 'v142'
        if int (version) < 25:
            toolset = 'v141'
        projGenParams.append (f'-T {toolset}')
    elif platformName == 'MAC':
        projGenParams.extend (['-G', 'Xcode'])

    projGenParams.append (f'-DAC_VERSION={version}')
    projGenParams.append (f'-DAC_ADDON_NAME={addOnName}-{version}')
    projGenParams.append (f'-DAC_API_DEVKIT_DIR={str (devKitFolder / "Support")}')
    projGenParams.append (f'-DAC_ADDON_LANGUAGE={languageCode}')

    if additionalParams is not None:
        for key in additionalParams:
            projGenParams.append (f'-D{key}={additionalParams[key]}')

    projGenParams.append (str (workspaceRootFolder))

    return projGenParams


def BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, configuration, languageCode, quiet):
    buildPath = buildFolder / addOnName / version / languageCode

    # Add params to configure cmake
    projGenParams = GetProjectGenerationParams (workspaceRootFolder, buildPath, addOnName, platformName, devKitFolder, version, languageCode, additionalParams)
    projGenResult = CallCommand (projGenParams, quiet)

    if projGenResult != 0:
        raise Exception ('Failed to generate project!')

    # Add params to build AddOn
    buildParams = [
        'cmake',
        '--build', str (buildPath),
        '--config', configuration
    ]

    buildResult = CallCommand (buildParams, quiet)

    if buildResult != 0:
        raise Exception ('Failed to build project!')


def BuildAddOns (addOnName, buildConfigList, languageList, additionalParams, workspaceRootFolder, buildFolder, devKitFolderList, quiet):
    platformName = GetPlatformName ()

    try:
        for version in devKitFolderList:
            devKitFolder = devKitFolderList[version]

            for languageCode in languageList:
                for config in buildConfigList:
                    BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, config, languageCode, quiet)

    except Exception as e:
        raise e


def Check7ZInstallation ():
    try:
        CallCommand ('7z', True)
    except:
        raise Exception ('7Zip not installed!')


def CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, configuration, languageCode):
    packageFolder = packageRootFolder / version / languageCode / configuration
    sourceFolder = buildFolder / addOnName / version / languageCode / configuration

    if not packageFolder.exists ():
        packageFolder.mkdir (parents=True)

    if platformName == 'WIN':
        shutil.copy (
            sourceFolder / f'{addOnName}-{version}.apx',
            packageFolder / f'{addOnName}-{version}.apx',
        )
        if configuration != 'Release':
            shutil.copy (
                sourceFolder / f'{addOnName}-{version}.pdb',
                packageFolder / f'{addOnName}-{version}.pdb',
            )

    elif platformName == 'MAC':
        CallCommand ([
            'cp', '-R',
            sourceFolder / f'{addOnName}-{version}.bundle',
            packageFolder / f'{addOnName}-{version}.bundle'
        ])


def GetDevKitVersion (args, devKitData, version, platformName):
    if args.devKitPath:
        buildNum = f'{version}.{args.buildNum}'
    else:
        url = devKitData[platformName][version]
        buildNum = url.split ('/')[-2]

    return buildNum


# Zip packages
def PackageAddOns (args, devKitData, addOnName, buildConfigList, acVersionList, languageList, buildFolder, packageRootFolder):
    platformName = GetPlatformName ()
    Check7ZInstallation ()

    for version in acVersionList:
        versionAndBuildNum = GetDevKitVersion (args, devKitData, version, platformName)

        for languageCode in languageList:
            for config in buildConfigList:
                CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, config, languageCode)
                CallCommand ([
                        '7z', 'a',
                        str (packageRootFolder.parent / version / f'{addOnName}-{versionAndBuildNum}_{platformName}_{languageCode}_{config}.zip'),
                        str (packageRootFolder / version / languageCode / config / '*')
                    ], args.quiet)


def Main ():
    try:
        args = ParseArguments ()

        [devKitData, addOnName, buildConfigList, acVersionList, languageList, additionalParams] = PrepareParameters (args)

        [workspaceRootFolder, buildFolder, packageRootFolder, devKitFolderList] = PrepareDirectories (args, devKitData, addOnName, acVersionList)

        os.chdir (workspaceRootFolder)

        BuildAddOns (addOnName, buildConfigList, languageList, additionalParams, workspaceRootFolder, buildFolder, devKitFolderList, args.quiet)

        if args.package:
            PackageAddOns (args, devKitData, addOnName, buildConfigList, acVersionList, languageList, buildFolder, packageRootFolder)

        print ('Build succeeded!')
        sys.exit (0)

    except Exception as e:
        print (e)
        print (traceback.format_exc())
        sys.exit (1)

if __name__ == "__main__":
    Main ()
