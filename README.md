# Archicad Add-on CMake tools

This repository contains the resource compilation necessary for Archicadd Add-On builds.

## Prerequisites

- [Archicad Development Kit](https://archicadapi.graphisoft.com/downloads/api-development-kit) (that matches your Archicad version).
- [CMake](https://cmake.org) (3.16 minimum version is needed).
- [Python](https://www.python.org) for resource compilation (version 2.7+ or 3.8+).

## Usage

- Include the contents of the repository in your project
  - The files should be placed in a directory named **Tools** 
  - It is recomended to use Git submodules:
   ```
   git submodule add https://github.com/GRAPHISOFT/archicad-addon-cmake-tools.git Tools
   ```
   ---
  **NOTE**
  
  The structure of the project should follow the structure of the official example addon: https://github.com/GRAPHISOFT/archicad-addon-cmake/
  
  ---
- Include the <em>CMakeCommon.cmake</em> file in the main CMakeList.txt file of your project
```
include (Tools/CMakeCommon.cmake)
```
- Set the following variables
  - `AC_API_DEVKIT_DIR`: The Support folder of the installed Archicad Add-On Development Kit. You can also set an environment variable with the same name so you don't have to provide this value during project generation.
  - `AC_ADDON_NAME`: (optional) The name of the project file and the result binary Add-On file (default is "ExampleAddOn").
  - `AC_ADDON_LANGUAGE`: (optional) The language code of the Add-On (default is "INT").
- Call the neccessary funtions to generate the project
```
project (${AC_ADDON_NAME})

DetectACVersion (${AC_API_DEVKIT_DIR} ACVersion)
message (STATUS "Archicad Version: ${ACVersion}")

set (AddOnFolder .)
SetGlobalCompilerDefinitions ()

GenerateAddOnProject (${ACVersion} ${AC_API_DEVKIT_DIR} ${AC_ADDON_NAME} ${AddOnFolder} ${AC_ADDON_LANGUAGE})
```
