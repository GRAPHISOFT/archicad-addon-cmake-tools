# Archicad Add-On CMake Tools

This repository contains the tools needed for Archicad Add-On compilation. The recommended way to use these tools is to add this code as a submodule to your own repository. See [archicad-addon-cmake](https://github.com/GRAPHISOFT/archicad-addon-cmake) for a usage example.

## APIDevKitLinks.json

There is a configuration file that consists of an object containing key-value pairs, in which the keys are Archicad version numbers, and their respective values are the direct download URLs to the public API Development Kit releases.

## Build script

The repo includes a BuildAddOn.py python script, that handles the building of the Add-Ons. This script takes up to 9 arguments:

- -c, --configFile (mandatory): Path to the JSON configuration file.
- -v, --acVersion (optional, but mandatory if --devKitPath is used): A list of Archicad version numbers, that the Add-On is built for. These versions must be present in the object keys of the APIDevKitLinks file. When not specified, the script takes all versions specified in the APIDevKitLinks file.
- -b, --buildConfig (optional): List of Archicad build configurations. If not specified, defaults to RelWithDebInfo only. Ex: -b Debug Release RelWithDebInfo.
- -l, --allLocalizedVersions (optional): Toggles creating localized builds for all languages listed in the language object of the JSON configuration file. If not enabled, the configured defaultLanguage will be used.
- -d, --devKitPath (optional): Path to a single local APIDevKit folder. When this argument is used, only one Archicad version should be provided in the --acVersion list.
- -n, --buildNum (optional, but mandatory if --devKitPath is used): Build number of the used local APIDevKit. Ex: -n 3001.
- -p, --package (optional): Toggles creating zip archive with the built Add-On files.
- -a, --additionalCMakeParams (optional): A list of additional AddOn-specific CMake parameters as keys or key=value pairs. The build script will forward it to CMake. Ex: -a var1=value1 var2="value 2" var3.
- -q, --quiet (optional): Suppresses output of the build tool.
