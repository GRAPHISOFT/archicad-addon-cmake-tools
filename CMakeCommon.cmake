function (SetGlobalCompilerDefinitions acVersion)

    if (WIN32)
        add_definitions (-DUNICODE -D_UNICODE -D_ITERATOR_DEBUG_LEVEL=0)
        set (CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL PARENT_SCOPE)
    else ()
        add_definitions (-Dmacintosh=1)
        if (${acVersion} GREATER_EQUAL 26)
            set (CMAKE_OSX_ARCHITECTURES "x86_64;arm64" PARENT_SCOPE CACHE STRING "" FORCE)
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

function (ParseVersion inValue outList)
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
        endforeach ()
        set ("${outList}" "${v1};${v2};${v3}" PARENT_SCOPE)
    else ()
        unset ("${outList}" PARENT_SCOPE)
    endif ()
endfunction ()

function (GenerateAddOnVersionInfo target)
    get_target_property (devKitDir "${target}" GSdevKitDir)
    get_target_property (addOnName "${target}" GSaddOnName)
    get_target_property (acVersion "${target}" GSacVersion)
    if (NOT DEFINED devKitDir OR NOT DEFINED addOnName OR NOT DEFINED acVersion)
        message (FATAL_ERROR "Target '${target}' was not created with GenerateAddOnProject.")
    endif ()

    cmake_parse_arguments (PARSE_ARGV 1 vers "" VERSION "")
    if (DEFINED vers_KEYWORDS_MISSING_VALUES AND "VERSION" IN_LIST vers_KEYWORDS_MISSING_VALUES)
        message (FATAL_ERROR "\
'VERSION' argument is missing its value. Please make sure you replaced the placeholder in CMakeLists.txt:

    GenerateAddOnVersionInfo (CMakeTarget VERSION #[[version goes here]])

Replace the '#[[version goes here]]' comment with a version number that you wish see in the file's properties and bug reports.
Accepted version number formats are:

    123
    1.23
    1.2.3")
    endif ()

    ParseVersion ("${vers_VERSION}" vers)
    if (NOT DEFINED vers)
        message (FATAL_ERROR "'${vers_VERSION}' does not follow the '1.2.3' version format, where the 2nd and 3rd components are optional.")
    endif ()

    set (company "GRAPHISOFT SE")
    string (TIMESTAMP copyright "Copyright © ${company}, 1984-%Y")

    if (WIN32)
        # FIXME(HVA): include GS build num in Windows release as well
        list (APPEND vers "${acVersion}")
        list (JOIN vers , version_comma)
        list (JOIN vers . version)

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

        list (APPEND vers "${gsBuildNum}")
        list (JOIN vers . version)

        string (TOLOWER "${addOnName}" lowerAddOnName)
        string (REGEX REPLACE "[ _]" "-" addOnNameIdentifier "${lowerAddOnName}")

        set (MACOSX_BUNDLE_EXECUTABLE_NAME "${addOnName}")
        set (MACOSX_BUNDLE_INFO_STRING "${addOnName}")
        set (MACOSX_BUNDLE_GUI_IDENTIFIER "com.graphisoft.${addOnNameIdentifier}")
        set (MACOSX_BUNDLE_LONG_VERSION_STRING "${copyright}")
        set (MACOSX_BUNDLE_BUNDLE_NAME "${addOnName}")
        set (MACOSX_BUNDLE_SHORT_VERSION_STRING "${version}.${gsBuildNum}")
        set (MACOSX_BUNDLE_BUNDLE_VERSION "${version}.${gsBuildNum}")
        set (MACOSX_BUNDLE_COPYRIGHT "${copyright}")
        set (MINIMUM_SYSTEM_VERSION "${lsMinimumSystemVersion}")

        set (out "${CMAKE_CURRENT_BINARY_DIR}/AddOnInfo.plist")
        configure_file ("${CMAKE_CURRENT_FUNCTION_LIST_DIR}/AddOnInfo.plist.in" "${out}" @ONLY)
        set_target_properties (
            "${target}" PROPERTIES
            MACOSX_BUNDLE_INFO_PLIST "${out}"

            # Align parameters for Xcode and in Info.plist to avoid warnings
            XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "${MACOSX_BUNDLE_GUI_IDENTIFIER}"
            XCODE_ATTRIBUTE_MACOSX_DEPLOYMENT_TARGET "${lsMinimumSystemVersion}"
        )
    endif ()
endfunction ()

function (GenerateAddOnProject target acVersion devKitDir addOnName addOnSourcesFolder addOnResourcesFolder addOnLanguage)
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

    set_target_properties (
        "${target}" PROPERTIES
        OUTPUT_NAME "${addOnName}"
        GSdevKitDir "${devKitDir}"
        GSaddOnName "${addOnName}"
        GSacVersion "${acVersion}"
    )
    if (WIN32)
        set_property (TARGET "${target}" PROPERTY SUFFIX .apx)
        target_link_options (
            "${target}" PRIVATE
            "${ResourceObjectsDir}/${addOnName}.res"
            "/export:GetExportedFuncAddrs,@1"
            "/export:SetImportedFuncAddrs,@2"
        )
    else ()
        set_target_properties (
            ${target} PROPERTIES
            BUNDLE TRUE
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
