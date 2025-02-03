function (SetGlobalCompilerDefinitions acVersion)

    if (WIN32)
        add_definitions (-DUNICODE -D_UNICODE -D_ITERATOR_DEBUG_LEVEL=0)
        set (CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL PARENT_SCOPE)
    else ()
        add_definitions (-Dmacintosh=1)
        if (${acVersion} GREATER_EQUAL 26)
            set (CMAKE_OSX_ARCHITECTURES "x86_64;arm64" CACHE STRING "" FORCE)
        endif ()
    endif ()
    add_definitions (-DACExtension)

endfunction ()

function (SetCompilerOptions target acVersion)

    if (${acVersion} LESS 27)
        target_compile_features (${target} PUBLIC cxx_std_14)
    else ()
        target_compile_features (${target} PUBLIC cxx_std_17)
    endif ()
    target_compile_options (${target} PUBLIC "$<$<CONFIG:Debug>:-DDEBUG>")
    if (WIN32)
        target_compile_options (${target} PUBLIC /W4 /WX
            /Zc:wchar_t-
            /wd4499
            /EHsc
            -D_CRT_SECURE_NO_WARNINGS
        )
    else ()
        target_compile_options (${target} PUBLIC -Wall -Wextra -Werror
            -fvisibility=hidden
            -Wno-multichar
            -Wno-ctor-dtor-privacy
            -Wno-invalid-offsetof
            -Wno-ignored-qualifiers
            -Wno-reorder
            -Wno-overloaded-virtual
            -Wno-unused-parameter
            -Wno-unused-value
            -Wno-unused-private-field
            -Wno-deprecated
            -Wno-unknown-pragmas
            -Wno-missing-braces
            -Wno-missing-field-initializers
            -Wno-non-c-typedef-for-linkage
            -Wno-uninitialized-const-reference
            -Wno-shorten-64-to-32
            -Wno-sign-compare
            -Wno-switch
        )
        if (${acVersion} LESS_EQUAL "24")
            target_compile_options (${target} PUBLIC -Wno-non-c-typedef-for-linkage)
        endif ()
    endif ()

endfunction ()

function (LinkGSLibrariesToProject target acVersion devKitDir)

    if (WIN32)
        if (${acVersion} LESS 27)
            target_link_libraries (${target}
                "${devKitDir}/Lib/Win/ACAP_STAT.lib"
            )
        else ()
            target_link_libraries (${target}
                "${devKitDir}/Lib/ACAP_STAT.lib"
            )
        endif ()
    else ()
        find_library (CocoaFramework Cocoa)
        if (${acVersion} LESS 27)
            target_link_libraries (${target}
                "${devKitDir}/Lib/Mactel/libACAP_STAT.a"
                ${CocoaFramework}
            )
        else ()
            target_link_libraries (${target}
                "${devKitDir}/Lib/libACAP_STAT.a"
                ${CocoaFramework}
            )
        endif ()
    endif ()

    file (GLOB ModuleFolders ${devKitDir}/Modules/*)
    target_include_directories (${target} SYSTEM PUBLIC ${ModuleFolders})
    if (WIN32)
        file (GLOB LibFilesInFolder ${devKitDir}/Modules/*/*/*.lib)
        target_link_libraries (${target} ${LibFilesInFolder})
    else ()
        file (GLOB LibFilesInFolder
            ${devKitDir}/Frameworks/*.framework
            ${devKitDir}/Frameworks/*.dylib
        )
        target_link_libraries (${target} ${LibFilesInFolder})
    endif ()

endfunction ()

function (parse_version inValue outList)
    set (v1 0)
    set (v2 0)
    set (v3 0)
    unset (CMAKE_MATCH_COUNT)
    if (inValue MATCHES [[^([0-9]+)\.([0-9]+)\.([0-9]+)$]])
    elseif (inValue MATCHES [[^([0-9]+)\.([0-9]+)$]])
    elseif (inValue MATCHES [[^([0-9]+)$]])
    endif ()
    if (DEFINED CMAKE_MATCH_COUNT)
        foreach (i RANGE 1 "${CMAKE_MATCH_COUNT}")
            set ("v${i}" "${CMAKE_MATCH_${i}}")
            if ("${v${i}}" LESS "0" OR "${v${i}}" GREATER "65535")
                message (FATAL_ERROR "Component ${i} of version number '${inValue}' is outside the 0-65535 range.")
            endif ()
        endforeach ()
        set ("${outList}" "${v1};${v2};${v3}" PARENT_SCOPE)
    else ()
        unset ("${outList}" PARENT_SCOPE)
    endif ()
endfunction ()

function (generate_add_on_version_info outSemver)
    parse_version ("${addOnVersion}" vers)
    if (NOT DEFINED vers)
        message (FATAL_ERROR "'${addOnVersion}' does not follow the '123' or '1.23' or '1.2.3' version format.")
    endif ()
    if (vers STREQUAL "0;0;0")
        message (WARNING "Addon version is '0.0.0', which is a placeholder version. Please change it in 'config.json'.")
    endif ()

    list (JOIN vers . semver)
    set ("${outSemver}" "${semver}" PARENT_SCOPE)

    string (TIMESTAMP copyright "Copyright © ${addOnCompanyName}, ${addOnCopyrightYear}")

    if (WIN32)
        # FIXME(HVA): include GS build num in Windows release as well
        set (gsBuildNum 0)
        list (APPEND vers 0)
        list (JOIN vers , versionComma)
        list (JOIN vers . version)

        string (REGEX REPLACE [[(\\|")]] [[\\\1]] addOnDescription "${addOnDescription}")

        set (out "${CMAKE_CURRENT_BINARY_DIR}/${target}-VersionInfo.rc")
        configure_file ("${CMAKE_CURRENT_FUNCTION_LIST_DIR}/VersionInfo.rc.in" "${out}" @ONLY)
        target_sources ("${target}" PRIVATE "${out}")
    else ()
        # BE on the safe side; load the info from an existing framework
        file (READ "${devKitDir}/Frameworks/GSRoot.framework/Versions/A/Resources/Info.plist" plist_content NEWLINE_CONSUME)
        string (REGEX MATCH "GSBuildNum[^0-9]+([0-9]+)" unused "${plist_content}")
        set (gsBuildNum "${CMAKE_MATCH_1}")
        string (REGEX MATCH "LSMinimumSystemVersion[^0-9]+([0-9.]+)" unused "${plist_content}")
        set (lsMinimumSystemVersion "${CMAKE_MATCH_1}")

        list (JOIN vers . shortVersion)

        math (EXPR combined "${acVersion} * 100000 + ${gsBuildNum}")
        list (APPEND vers "${combined}")
        list (JOIN vers . longVersion)

        string (REPLACE & &amp\; addOnDescription "${addOnDescription}")
        string (REPLACE < &lt\; addOnDescription "${addOnDescription}")
        string (REPLACE > &gt\; addOnDescription "${addOnDescription}")
        string (REPLACE ' &apos\; addOnDescription "${addOnDescription}")
        string (REPLACE \" &quot\; addOnDescription "${addOnDescription}")

        set (privateBuild "\n\t\t<key>GSPrivateBuild</key>\n\t\t<string>1</string>")
        if (NOT AC_ADDON_FOR_DISTRIBUTION)
            set (privateBuild "")
        endif ()

        string (TOLOWER "${addOnName}" lowerAddOnName)
        string (REGEX REPLACE "[ _]" "-" addOnNameIdentifier "${lowerAddOnName}")
        set (bundleIdentifier "com.graphisoft.${addOnNameIdentifier}")

        set (out "${CMAKE_CURRENT_BINARY_DIR}/AddOnInfo.plist")
        configure_file ("${CMAKE_CURRENT_FUNCTION_LIST_DIR}/AddOnInfo.plist.in" "${out}" @ONLY)
        set_target_properties (
            "${target}" PROPERTIES
            MACOSX_BUNDLE_INFO_PLIST "${out}"

            # Align parameters for Xcode and in Info.plist to avoid warnings
            XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "${bundleIdentifier}"
            XCODE_ATTRIBUTE_MACOSX_DEPLOYMENT_TARGET "${lsMinimumSystemVersion}"
        )
    endif ()
endfunction ()

function (GenerateAddOnProject target acVersion devKitDir addOnSourcesFolder addOnResourcesFolder addOnLanguage)
    verify_api_devkit_folder ("${devKitDir}")
    if (NOT addOnLanguage IN_LIST addOnLanguages)
        message (FATAL_ERROR "Language '${addOnLanguage}' is not among the configured languages in config.json.")
    endif ()

    find_package (Python COMPONENTS Interpreter)

    set (ResourceObjectsDir ${CMAKE_BINARY_DIR}/ResourceObjects)
    set (ResourceStampFile "${ResourceObjectsDir}/AddOnResources.stamp")

    file (GLOB AddOnImageFiles CONFIGURE_DEPENDS
        ${addOnResourcesFolder}/RFIX/Images/*.svg
    )
    if (WIN32)
        file (GLOB AddOnResourceFiles CONFIGURE_DEPENDS
            ${addOnResourcesFolder}/R${addOnLanguage}/*.grc
            ${addOnResourcesFolder}/RFIX/*.grc
            ${addOnResourcesFolder}/RFIX.win/*.rc2
            ${CMAKE_CURRENT_FUNCTION_LIST_DIR}/*.py
        )
    else ()
        file (GLOB AddOnResourceFiles CONFIGURE_DEPENDS
            ${addOnResourcesFolder}/R${addOnLanguage}/*.grc
            ${addOnResourcesFolder}/RFIX/*.grc
            ${addOnResourcesFolder}/RFIX.mac/*.plist
            ${CMAKE_CURRENT_FUNCTION_LIST_DIR}/*.py
        )
    endif ()

    get_filename_component (AddOnSourcesFolderAbsolute "${CMAKE_CURRENT_LIST_DIR}/${addOnSourcesFolder}" ABSOLUTE)
    get_filename_component (AddOnResourcesFolderAbsolute "${CMAKE_CURRENT_LIST_DIR}/${addOnResourcesFolder}" ABSOLUTE)
    if (WIN32)
        add_custom_command (
            OUTPUT ${ResourceStampFile}
            DEPENDS ${AddOnResourceFiles} ${AddOnImageFiles}
            COMMENT "Compiling resources..."
            COMMAND ${CMAKE_COMMAND} -E make_directory "${ResourceObjectsDir}"
            COMMAND ${Python_EXECUTABLE} "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/CompileResources.py" "${addOnLanguage}" "${devKitDir}" "${AddOnSourcesFolderAbsolute}" "${AddOnResourcesFolderAbsolute}" "${ResourceObjectsDir}" "${ResourceObjectsDir}/${addOnName}.res"
            COMMAND ${CMAKE_COMMAND} -E touch ${ResourceStampFile}
        )
    else ()
        add_custom_command (
            OUTPUT ${ResourceStampFile}
            DEPENDS ${AddOnResourceFiles} ${AddOnImageFiles}
            COMMENT "Compiling resources..."
            COMMAND ${CMAKE_COMMAND} -E make_directory "${ResourceObjectsDir}"
            COMMAND ${Python_EXECUTABLE} "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/CompileResources.py" "${addOnLanguage}" "${devKitDir}" "${AddOnSourcesFolderAbsolute}" "${AddOnResourcesFolderAbsolute}" "${ResourceObjectsDir}" "${CMAKE_BINARY_DIR}/$<CONFIG>/${addOnName}.bundle/Contents/Resources"
            COMMAND ${CMAKE_COMMAND} -E copy "${devKitDir}/Inc/PkgInfo" "${CMAKE_BINARY_DIR}/$<CONFIG>/${addOnName}.bundle/Contents/PkgInfo"
            COMMAND ${CMAKE_COMMAND} -E touch ${ResourceStampFile}
        )
    endif ()

    file (GLOB_RECURSE AddOnHeaderFiles CONFIGURE_DEPENDS
        ${addOnSourcesFolder}/*.h
        ${addOnSourcesFolder}/*.hpp
    )
    file (GLOB_RECURSE AddOnSourceFiles CONFIGURE_DEPENDS
        ${addOnSourcesFolder}/*.c
        ${addOnSourcesFolder}/*.cpp
    )
    set (
        AddOnFiles
        ${AddOnHeaderFiles}
        ${AddOnSourceFiles}
        ${AddOnImageFiles}
        ${AddOnResourceFiles}
        ${ResourceStampFile}
    )

    source_group ("Sources" FILES ${AddOnHeaderFiles} ${AddOnSourceFiles})
    source_group ("Images" FILES ${AddOnImageFiles})
    source_group ("Resources" FILES ${AddOnResourceFiles})
    if (WIN32)
        add_library (${target} SHARED ${AddOnFiles})
    else ()
        add_library (${target} MODULE ${AddOnFiles})
    endif ()

    set_target_properties (${target} PROPERTIES OUTPUT_NAME ${addOnName})
    if (WIN32)
        set_target_properties (
            "${target}" PROPERTIES
            SUFFIX .apx
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
        )
        target_link_options (
            "${target}" PRIVATE
            "${ResourceObjectsDir}/${addOnName}.res"
            "/export:GetExportedFuncAddrs,@1"
            "/export:SetImportedFuncAddrs,@2"
        )
    else ()
        set_target_properties(
            "${target}" PROPERTIES
            BUNDLE TRUE
            LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/\$<CONFIG>"
        )
    endif ()
    generate_add_on_version_info (semver)
    target_compile_definitions (
        "${target}" PRIVATE
        "ADDON_VERSION=\"${semver}\""
        "ADDON_NAME=\"${addOnName}\""
        "ADDON_LANGUAGE=\"${addOnLanguage}\""
    )

    target_include_directories (${target} SYSTEM PUBLIC ${devKitDir}/Inc)
    target_include_directories (${target} PUBLIC ${addOnSourcesFolder})

    # use GSRoot custom allocators consistently in the Add-On
    get_filename_component(new_hpp "${devKitDir}/Modules/GSRoot/GSNew.hpp" REALPATH)
    get_filename_component(malloc_hpp "${devKitDir}/Modules/GSRoot/GSMalloc.hpp" REALPATH)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        target_compile_options(
            "${target}" PRIVATE
            "SHELL:/FI \"${new_hpp}\""
            "SHELL:/FI \"${malloc_hpp}\""
        )
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang\$")
        target_compile_options(
            "${target}" PRIVATE
            "SHELL:-include \"${new_hpp}\""
            "SHELL:-include \"${malloc_hpp}\""
        )
    else()
        message(FATAL_ERROR "Unknown compiler ID. Please open an issue at https://github.com/GRAPHISOFT/archicad-addon-cmake-tools")
    endif()

    LinkGSLibrariesToProject (${target} ${acVersion} ${devKitDir})

    set_source_files_properties (${AddOnSourceFiles} PROPERTIES LANGUAGE CXX)
    SetCompilerOptions (${target} ${acVersion})

endfunction ()

function (verify_api_devkit_folder devKitPath)
    if (NOT EXISTS "${devKitPath}")
        message (FATAL_ERROR "The supplied API DevKit path ${devKitPath} does not exist")
    endif ()

    cmake_path (GET devKitPath FILENAME currentFolderName)
    if (NOT currentFolderName STREQUAL "Support")
        message (FATAL_ERROR "The supplied API DevKit path should point to the /Support subfolder of the API DevKit. Actual path: ${devKitPath}")
    endif ()

    if (NOT EXISTS "${devKitPath}/Lib")
        message (FATAL_ERROR "${devKitPath}/Lib does not exist")
    endif ()

    if (NOT EXISTS "${devKitPath}/Modules")
        message (FATAL_ERROR "${devKitPath}/Modules does not exist")
    endif ()

    if (APPLE AND NOT EXISTS "${devKitPath}/Frameworks")
        message (FATAL_ERROR "${devKitPath}/Frameworks does not exist")
    endif ()
endfunction ()

set (GS_CONFIG_JSON_PATH "${CMAKE_SOURCE_DIR}/config.json" CACHE FILEPATH "")
mark_as_advanced (GS_CONFIG_JSON_PATH)

function (ReadConfigJson)
    file (READ "${GS_CONFIG_JSON_PATH}" json)

    set (requiredMembers addOnName defaultLanguage version copyright\\\;name copyright\\\;year description)
    set (returnAs addOnName addOnDefaultLanguage addOnVersion addOnCompanyName addOnCopyrightYear addOnDescription)
    foreach (out members IN ZIP_LISTS returnAs requiredMembers)
        string (JSON "${out}" ERROR_VARIABLE error GET "${json}" ${members})
        if (error)
            string (REPLACE \; . members "${members}")
            message (FATAL_ERROR "Error getting required member (${members}): ${error}")
        endif ()
        set ("${out}" "${${out}}" PARENT_SCOPE)
    endforeach ()

    string (JSON languagesType ERROR_VARIABLE error TYPE "${json}" languages)
    if (error OR NOT languagesType STREQUAL "ARRAY")
        message (FATAL_ERROR "'languages' in config.json must be an array: ${error}")
    endif ()

    string (JSON json GET "${json}" languages)
    set (addOnLanguages "")
    set (i 0)
    while ("ON")
        string (JSON language ERROR_VARIABLE error GET "${json}" "${i}")
        if (error)
            break ()
        endif ()
        list (APPEND addOnLanguages "${language}")
        math (EXPR i "${i} + 1")
    endwhile ()
    set (addOnLanguages "${addOnLanguages}" PARENT_SCOPE)

    if (NOT addOnDefaultLanguage IN_LIST addOnLanguages)
        message (FATAL_ERROR "'defaultLanguage' in config.json does not name a language specified in 'languages'.")
    endif ()
endfunction ()
