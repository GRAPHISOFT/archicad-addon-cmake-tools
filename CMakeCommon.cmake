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

function (GenerateAddOnProject target acVersion devKitDir addOnName addOnSourcesFolder addOnResourcesFolder addOnLanguage)

    verify_api_devkit_folder ("${devKitDir}")
    check_valid_language_code ("${CMAKE_SOURCE_DIR}/config.json" "${addOnLanguage}")

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
        set_target_properties (${target} PROPERTIES
            SUFFIX ".apx"
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
        )
        target_link_options (${target} PUBLIC "${ResourceObjectsDir}/${addOnName}.res")
        target_link_options (${target} PUBLIC /export:GetExportedFuncAddrs,@1 /export:SetImportedFuncAddrs,@2)
    else ()
        # Prepare various variables for the Info.plist
        string(TOLOWER "${addOnName}" lowerAddOnName)
        string(REGEX REPLACE "[ _]" "-" addOnNameIdentifier "${lowerAddOnName}")
        string(TIMESTAMP copyright "Copyright © GRAPHISOFT SE, 1984-%Y")
        # BE on the safe side; load the info from an existing framework
        file(READ "${devKitDir}/Frameworks/GSRoot.framework/Versions/A/Resources/Info.plist" plist_content NEWLINE_CONSUME)
        string(REGEX REPLACE ".*GSBuildNum[^0-9]+([0-9]+).*" "\\1" gsBuildNum "${plist_content}")
        string(REGEX REPLACE ".*LSMinimumSystemVersion[^0-9]+([0-9\.]+).*" "\\1" lsMinimumSystemVersion "${plist_content}")

        set(MACOSX_BUNDLE_EXECUTABLE_NAME ${addOnName})
        set(MACOSX_BUNDLE_INFO_STRING ${addOnName})
        set(MACOSX_BUNDLE_GUI_IDENTIFIER com.graphisoft.${addOnNameIdentifier})
        set(MACOSX_BUNDLE_LONG_VERSION_STRING ${copyright})
        set(MACOSX_BUNDLE_BUNDLE_NAME ${addOnName})
        set(MACOSX_BUNDLE_SHORT_VERSION_STRING ${acVersion}.0.0.${gsBuildNum})
        set(MACOSX_BUNDLE_BUNDLE_VERSION ${acVersion}.0.0.${gsBuildNum})
        set(MACOSX_BUNDLE_COPYRIGHT ${copyright})
        set(MINIMUM_SYSTEM_VERSION "${lsMinimumSystemVersion}")

        # Configure the Info.plist file
        configure_file(
            "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/AddOnInfo.plist.in"
            "${CMAKE_BINARY_DIR}/AddOnInfo.plist"
            @ONLY
        )
        set_target_properties(${target} PROPERTIES
            BUNDLE TRUE
            MACOSX_BUNDLE_INFO_PLIST "${CMAKE_BINARY_DIR}/AddOnInfo.plist"

            # Align parameters for Xcode and in Info.plist to avoid warnings
            XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER com.graphisoft.${addOnNameIdentifier}
            XCODE_ATTRIBUTE_MACOSX_DEPLOYMENT_TARGET ${lsMinimumSystemVersion}

            LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/$<CONFIG>"
        )
    endif ()

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

function (check_valid_language_code configFile languageCode)
    file (READ "${configFile}" configsContent)
    string (JSON configuredLanguagesList GET "${configsContent}" "languages")
    string (JSON configuredLanguagesListLen LENGTH "${configsContent}" "languages")
    set (i 0)
    while (i LESS configuredLanguagesListLen)
        string (JSON language GET "${configuredLanguagesList}" "${i}")
        if (language STREQUAL languageCode)
            return ()
        endif ()
        math (EXPR i "${i} + 1")
    endwhile()

    message (FATAL_ERROR "Language code ${languageCode} is not part of the configured languages in ${configFile}.")
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