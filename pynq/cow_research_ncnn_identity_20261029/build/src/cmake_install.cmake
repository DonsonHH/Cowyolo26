# Install script for directory: /home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/libncnn.a")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ncnn" TYPE FILE FILES
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/allocator.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/benchmark.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/blob.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/c_api.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/command.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/cpu.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/datareader.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/expression.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/gpu.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/layer.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/layer_shader_type.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/layer_type.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/mat.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/modelbin.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/net.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/option.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/paramdict.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/pipeline.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/pipelinecache.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/simpleocv.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/simpleomp.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/simplestl.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/simplemath.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/simplevk.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/source/ncnn-20261020/src/vulkan_header_fix.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/ncnn_export.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/layer_shader_type_enum.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/layer_type_enum.h"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/platform.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn/ncnn.cmake")
    file(DIFFERENT EXPORT_FILE_CHANGED FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn/ncnn.cmake"
         "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/CMakeFiles/Export/lib/cmake/ncnn/ncnn.cmake")
    if(EXPORT_FILE_CHANGED)
      file(GLOB OLD_CONFIG_FILES "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn/ncnn-*.cmake")
      if(OLD_CONFIG_FILES)
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn/ncnn.cmake\" will be replaced.  Removing files [${OLD_CONFIG_FILES}].")
        file(REMOVE ${OLD_CONFIG_FILES})
      endif()
    endif()
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn" TYPE FILE FILES "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/CMakeFiles/Export/lib/cmake/ncnn/ncnn.cmake")
  if("${CMAKE_INSTALL_CONFIG_NAME}" MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn" TYPE FILE FILES "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/CMakeFiles/Export/lib/cmake/ncnn/ncnn-release.cmake")
  endif()
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/ncnn" TYPE FILE FILES
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/ncnnConfig.cmake"
    "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/ncnnConfigVersion.cmake"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/build/src/ncnn.pc")
endif()

