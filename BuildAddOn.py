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

def ParseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('-c', '--configFile', dest = 'configFile', required = True, help = 'JSON Configuration file')
    parser.add_argument ('-v', '--acVersion', dest = 'acVersion', nargs = '+', type = str, required = False, help = 'Archicad version number list. Ex: 26 27')
    parser.add_argument ('-l', '--allLocalizedVersions', dest = 'allLocalizedVersions', required = False, action='store_true', help = 'Create localized release builds for all configured languages.' )
    parser.add_argument ('-d', '--devKitPath', dest = 'devKitPath', type = str, required = False, help = 'Path to local APIDevKit')
    parser.add_argument ('-p', '--package', dest = 'package', required = False, action='store_true', help = 'Create zip archive.')
    parser.add_argument ('-a', '--additionalCMakeParams', dest = 'additionalCMakeParams', nargs = '+', required = False, help = 'Add-On specific CMake parameter list of key=value pairs. Ex: var1=value1 var2="value 2"')
    args = parser.parse_args ()

    if args.devKitPath is not None:
        if args.acVersion is None:
            raise Exception ('Must provide one Archicad version with local APIDevKit option!')
        if len (args.acVersion) != 1:
            raise Exception ('Only one Archicad version supported with local APIDevKit option!')
    
    return args


def PrepareParameters (args):
    # Check platform operating system
    platformName = None
    if platform.system () == 'Windows':
        platformName = 'WIN'
    elif platform.system () == 'Darwin':
        platformName = 'MAC'

    # Load DevKit download data
    devKitDataPath = pathlib.Path (__file__).absolute ().parent / 'APIDevKitLinks.json'
    devKitDataFile = open (devKitDataPath)
    devKitData = json.load (devKitDataFile)

    # Load config data
    configPath = pathlib.Path (args.configFile)
    if configPath.is_dir ():
        raise Exception (f'{configPath} is a directory!')
    configFile = open (configPath)
    configData = json.load (configFile)
    addOnName = configData['addOnName']
    acVersionList = None

    if args.acVersion:
        acVersionList = args.acVersion
    else:
        acVersionList = []
        for version in devKitData[platformName]:
            acVersionList.append (version)

    # Get needed language codes
    languageList = [].append (configData['defaultLanguage'])
    if args.allLocalizedVersions:
        languageList = [lang.upper () for lang in configData['languages']]
                
    # Get additional CMake parameters
    additionalParams = None
    if 'additionalCMakeParams' in configData or args.additionalCMakeParams:
        additionalParams = {}

        if 'additionalCMakeParams' in configData:
            for key in configData['additionalCMakeParams']:
                additionalParams[key] = configData['additionalCMakeParams'][key]

        if args.additionalCMakeParams:
            for param in args.additionalCMakeParams:  #TODO
                if '=' not in param:
                    additionalParams[param] = None
                else:
                    key, value = param.split ('=', 1)
                    if not value:
                        value = None
                    additionalParams[key] = value
                
    return [devKitData, platformName, addOnName, acVersionList, languageList, additionalParams]


def PrepareDirectories (args, devKitData, platformName, addOnName, acVersionList):
    # Create directory for Build and Package
    workspaceRootFolder = pathlib.Path (__file__).parent.absolute ().parent.absolute ()
    buildFolder = workspaceRootFolder / 'Build'
    packageRootFolder = buildFolder / 'Package' / addOnName
    devKitFolderList = {}

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
        # For every ACVersion
        # Check if APIDevKitLink is provided
        # Create directory for APIDevKit
        # Download APIDevKit
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

    print (f'Unzipping {fileName}')
    if platform.system () == 'Windows':
        with zipfile.ZipFile (filePath, 'r') as zip:
            zip.extractall (dest)
    elif platform.system () == 'Darwin':
        subprocess.call ([
            'unzip', '-qq', filePath,
            '-d', dest
        ])


def GetInstalledVisualStudioGenerator ():
    vsWherePath = pathlib.Path (os.environ["ProgramFiles(x86)"]) / 'Microsoft Visual Studio' / 'Installer' / 'vswhere.exe'
    if not vsWherePath.exists ():
        raise Exception ('Microsoft Visual Studio Installer not found!')
    vsWhereOutputStr = subprocess.check_output ([vsWherePath, '-sort', '-format', 'json'])
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

    projGenParams.append (f'-DAC_ADDON_NAME={addOnName}')
    projGenParams.append (f'-DAC_API_DEVKIT_DIR={str (devKitFolder / "Support")}')

    if languageCode is not None:
        projGenParams.append (f'-DAC_ADDON_LANGUAGE={languageCode}')

    if additionalParams is not None:
        for key in additionalParams:
            projGenParams.append (f'-D{key}={additionalParams[key]}')

    projGenParams.append (str (workspaceRootFolder))

    return projGenParams


def BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, configuration, languageCode=None):
    buildPath = buildFolder / addOnName / version
    if languageCode is not None:
        buildPath = buildPath / languageCode

    # Add params to configure cmake
    projGenParams = GetProjectGenerationParams (workspaceRootFolder, buildPath, addOnName, platformName, devKitFolder, version, languageCode, additionalParams)
    projGenResult = subprocess.call (projGenParams)
    if projGenResult != 0:
        raise Exception ('Failed to generate project!')
    
    # Add params to build AddOn
    buildParams = [
        'cmake',
        '--build', str (buildPath),
        '--config', configuration
    ]

    buildResult = subprocess.call (buildParams)
    if buildResult != 0:
        raise Exception ('Failed to build project!')


def BuildAddOns (args, addOnName, platformName, languageList, additionalParams, workspaceRootFolder, buildFolder, devKitFolderList):
    # At this point, devKitFolderList dictionary has all provided ACVersions as keys
    # For every ACVersion
    # If release, build Add-On for all languages with RelWithDebInfo configuration
    # Else build Add-On with Debug and RelWithDebInfo configurations, without language specified   
    # In each case, if package creation is enabled, copy the .apx/.bundle files to the Package directory
    try:
        for version in devKitFolderList:
            devKitFolder = devKitFolderList[version]

            if args.allLocalizedVersions is True:
                for languageCode in languageList:
                    BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, 'RelWithDebInfo', languageCode)

            else:
                BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, 'Debug')
                BuildAddOn (addOnName, platformName, additionalParams, workspaceRootFolder, buildFolder, devKitFolder, version, 'RelWithDebInfo')

    except Exception as e:
        raise e


def Check7ZInstallation ():
    try:
        subprocess.call ('7z', stdout=subprocess.DEVNULL)
    except:
        raise Exception ('7Zip not installed!')


def CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, configuration, languageCode=None, isRelease=False):
    packageFolder = packageRootFolder / version
    sourceFolder = buildFolder / addOnName / version

    if languageCode is not None:
        packageFolder = packageFolder / languageCode
        sourceFolder = sourceFolder / languageCode
    sourceFolder = sourceFolder / configuration

    if not packageFolder.exists ():
        packageFolder.mkdir (parents=True)

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
            'cp', '-R',
            sourceFolder / f'{addOnName}.bundle',
            packageFolder / f'{fileName}.bundle'
        ])


def GetDevKitBuildNum (devKitData, version, platformName):
    url = devKitData[platformName][version]
    buildNum = url.split('/')[-2]
    return buildNum


# Zip packages
def PackageAddOns (args, devKitData, addOnName, platformName, acVersionList, languageList, buildFolder, packageRootFolder):
    Check7ZInstallation ()

    for version in acVersionList:
        if args.allLocalizedVersions:
            for languageCode in languageList:
                CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo', languageCode, True)
        else:
            CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, 'Debug')
            CopyResultToPackage (packageRootFolder, buildFolder, version, addOnName, platformName, 'RelWithDebInfo')
        
        if args.allLocalizedVersions:
            buildType = 'Release'
            subprocess.call ([
                '7z', 'a',
                str (packageRootFolder.parent / f'{addOnName}-{version}_{buildType}_{platformName}.zip'),
                str (packageRootFolder / version / '*')
            ])
        else:
            buildType = 'Daily'
            buildNum = GetDevKitBuildNum (devKitData, version, platformName)
            subprocess.call ([
                '7z', 'a',
                str (packageRootFolder.parent / f'{addOnName}-{version}.{buildNum}_{buildType}_{platformName}.zip'),
                str (packageRootFolder / version / '*')
            ])


def Main ():
    try:
        args = ParseArguments ()

        [devKitData, platformName, addOnName, acVersionList, languageList, additionalParams] = PrepareParameters (args)

        [workspaceRootFolder, buildFolder, packageRootFolder, devKitFolderList] = PrepareDirectories (args, devKitData, platformName, addOnName, acVersionList)

        os.chdir (workspaceRootFolder)
        
        BuildAddOns (args, addOnName, platformName, languageList, additionalParams, workspaceRootFolder, buildFolder, devKitFolderList)

        if args.package:
            PackageAddOns (args, devKitData, addOnName, platformName, acVersionList, languageList, buildFolder, packageRootFolder)

        print ('Build succeeded!')
        sys.exit (0)
    
    except Exception as e:
        print (e)
        sys.exit (1)

if __name__ == "__main__":
    Main ()