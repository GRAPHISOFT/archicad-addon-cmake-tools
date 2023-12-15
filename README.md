# Archicad Add-On CMake Tools

This repository contains the tools needed for Archicad Add-On compilation. The recommended way to use these tools is to add this code as a submodule to your own repository. See [archicad-addon-cmake](https://github.com/GRAPHISOFT/archicad-addon-cmake) for a usage example.

## devKitLinks.json

There is a configuration file that consists of an object containing key-value pairs, in which the keys are Archicad version numbers, and their respective values are the direct download URLs to the public API Development Kit releases.

## Build script

The repo includes a BuildAddOn.py python script, that handles the building of the Add-Ons. This script takes up to 7 arguments:

- -c, --configFile (mandatory): path to the JSON configuration file
- -v, --acVersion (optional, but mandatory if --devKitPath is used): a list of Archicad version numbers, that the Add-On is built for. These versions must be present in the JSON configuration file's devKitLinks object keys. When not specified, the script takes all versions specified in the configuration file.
- -l, --language (optional): a list of language codes for creating localized release builds. Only used when the --release option is enabled. The language codes must be present in the JSON configuration file's language list. If language is not specified, or --language ALL is used, the script will create localized builds for all languages in the configuration file.
- -d, --devKitPath (optional): path to a single local APIDevKit folder. When this argument is used, only one Archicad version should be provided in the --acVersion list.
- -p, --package (optional): toggles creating zip archive with the built Add-On files.
- -r, --release (optional): toggles building the localized Add-On with the specified languages.
- -o, --optionalCMakeParams (optional): a list of additional addon-specific CMake parameters as key=value pairs. The build script will forward it to CMake. Ex: -o var1=value1 var2="value 2"

