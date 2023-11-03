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

def DownloadAndUnzip (url, dest, platform):
    # https://github.com/GRAPHISOFT/archicad-api-devkit/releases/download/<tag>/ <filename>
    # https://github.com/GRAPHISOFT/archicad-api-devkit/releases/latest/download/ <filename>   - not used, as there isn't a single latest version

    version = url.split('/')[-1]
    fileName = f'API.Development.Kit.{platform}.{version}.zip'
    url += '/' + fileName
    filePath = pathlib.Path(dest, fileName)
    if filePath.exists():
        return
 
    print ('Downloading ' + fileName)
    urllib.request.urlretrieve (url, filePath)
 
    print ('Unzipping ' + fileName)
    if platform.system () == 'Windows':
        with zipfile.ZipFile (filePath, 'r') as zip:
            zip.extractall (dest)
    elif platform.system () == 'Darwin':
        subprocess.call ([
            'unzip', '-qq', filePath,
            '-d', dest
        ])

def BuildAddOn (rootFolder, buildFolder, devKitFolder, addOnName, platformName, configuration, optionalParams, languageCode=None):
    buildPath = buildFolder / addOnName
    if languageCode is not None:
        buildPath = buildPath / languageCode

    # Add params to configure cmake
    projGenParams = []
    projGenParams.append ('cmake')
    projGenParams.extend (['-B', str(buildPath)])

    if platformName == 'WIN':
        projGenParams.extend (['-G', 'Visual Studio 16 2019'])
    elif platformName == 'MAC':
        projGenParams.extend (['-G', 'Xcode'])

    projGenParams.append ('-DAC_API_DEVKIT_DIR=' + str(devKitFolder / 'Support'))
    projGenParams.append ('-DCMAKE_BUILD_TYPE=' + configuration)

    if languageCode is not None:
        projGenParams.append ('-DAC_ADDON_LANGUAGE=' + languageCode)

    if optionalParams is not None:
        for key in optionalParams:
            projGenParams.append ('-D' + key + '=' + optionalParams[key])

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

def CopyResultToPackage(packageRootFolder, buildFolder, addOnName, platformName, configuration, languageCode=None, isRelease=False):
    packageFolder = packageRootFolder
    sourceFolder = buildFolder / addOnName

    if languageCode is not None:
        packageFolder = packageFolder / languageCode
        sourceFolder = sourceFolder / languageCode
    sourceFolder = sourceFolder / configuration

    if not packageFolder.exists():
        packageFolder.mkdir(parents=True)

    fileName = addOnName
    if not isRelease:
        fileName = fileName + '_' + configuration

    if platformName == 'WIN':
        shutil.copy (
            sourceFolder / (addOnName + '.apx'),
            packageFolder / (fileName + '.apx')
        )
        if configuration == 'Debug':
            shutil.copy (
                sourceFolder / (addOnName + '.pdb'),
                packageFolder / (fileName + '.pdb')
            )

    elif platformName == 'MAC':
        subprocess.call ([
            'cp', '-r',
            sourceFolder / (addOnName + '.bundle'),
            packageFolder / (fileName + '.bundle')
        ])
    


def Main():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('--acVersion', dest = 'acVersion', type = str, required = True, help = 'Archicad version number list. Ex: "26 27"')
    parser.add_argument ('--language', dest = 'language', type = str, required = False, help = 'Add-On language code list. Ex: "INT GER". Specify "ALL" for all languages in the configfile.' )
    parser.add_argument ('--devKitPath', dest = 'devKitPath', type = str, required = False, help = 'Path to local APIDevKit')
    parser.add_argument ('--release', dest = 'release', required = False, action='store_true', help = 'Create zip package.')
    parser.add_argument ('--package', dest = 'package', required = False, action='store_true', help = 'Create zip package.')
    args = parser.parse_args ()

    if args.language is None and args.release:
        print('Must specify AddOn language on release version')
        return 1

    acVersionList = args.acVersion.split()
        
    if args.devKitPath is not None and len(acVersionList) != 1:
        print('Only one Archicad version supported with local APIDevKit option')
        return 1

    # Check platform operating system
    platformName = None
    if platform.system () == 'Windows':
        platformName = 'WIN'
    elif platform.system () == 'Darwin':
        platformName = 'MAC'

    # Load config data
    configFile = open('config.json')
    configData = json.load(configFile)
    addOnName = configData['addOnName']

    optionalParams = None
    if 'addOnSpecificCMakeParameters' in configData:
        optionalParams = configData['addOnSpecificCMakeParameters']

    if args.language:
        configUpper = [lang.upper() for lang in configData['languages']]
        languageList = args.language.upper().split()
        if 'ALL' in languageList:
            languageList = configUpper
        else:
            for lang in languageList:
                if lang not in configUpper:
                    print('Language not supported')
                    return 1

    # Create directory for Build and Package
    rootFolder = pathlib.Path(__file__).parent.absolute()
    os.chdir (rootFolder)

    buildFolder = rootFolder / 'Build'
    if not buildFolder.exists():
        buildFolder.mkdir(parents=True)

    packageRootFolder = buildFolder / 'Package' / addOnName
    if args.package:
        if (packageRootFolder).exists():
            shutil.rmtree (packageRootFolder)

    # Set APIDevKit directory if local is used, else create new directories
    devKitFolderList = {}
    if args.devKitPath is not None:
        devKitFolderList[acVersionList[0]] = pathlib.Path(args.devKitPath)
    else:
        # For every ACVersion
        # Check if APIDevKitLink is provided
        # Create directory for APIDevKit
        # Download APIDevKit
        for version in acVersionList:
            if version in configData['devKitLinks']:

                devKitFolder = rootFolder / f'APIDevKit-{version}'
                if not devKitFolder.exists():
                    devKitFolder.mkdir()

                devKitFolderList[version] = devKitFolder
                DownloadAndUnzip(configData['devKitLinks'][version], devKitFolder, platformName)

            else:
                print('APIDevKit download link not provided')
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
            permissionParams = []
            permissionParams.append ('chmod')
            permissionParams.append ('+x')
            permissionParams.append (str(devKitFolder / 'Support' / 'Tools' / 'OSX' / 'ResConv'))
            permissionResult = subprocess.call (permissionParams)
            if permissionResult != 0:
                print ('Failed to grant permission')
                return 1
            
        if args.release is True:
            for languageCode in languageList:
                if BuildAddOn(rootFolder, buildFolder, devKitFolder, addOnName, platformName, 'RelWithDebInfo', optionalParams, languageCode) != 0:
                    return 1
                if args.package:
                    CopyResultToPackage(packageRootFolder, buildFolder, addOnName, platformName, 'RelWithDebInfo', languageCode, True)

        else:
            if BuildAddOn(rootFolder, buildFolder, devKitFolder, addOnName, platformName, 'Debug', optionalParams) != 0:
                return 1
            if BuildAddOn(rootFolder, buildFolder, devKitFolder, addOnName, platformName, 'RelWithDebInfo', optionalParams) != 0:
                return 1
            if args.package:
                CopyResultToPackage(packageRootFolder, buildFolder, addOnName, platformName, 'Debug')
                CopyResultToPackage(packageRootFolder, buildFolder, addOnName, platformName, 'RelWithDebInfo')

    # Zip packages
    if args.package:
        release = 'Release_Localized' if args.release else 'Daily'
        subprocess.call ([
            '7z', 'a',
            str(packageRootFolder.parent / (addOnName + '_' + release + '_' + platformName + '.zip')),
            str(packageRootFolder / '*')
        ])
    
    print ('Build Successful')
    return 0

sys.exit (Main ())