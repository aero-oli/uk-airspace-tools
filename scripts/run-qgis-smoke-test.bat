@echo off
setlocal EnableExtensions

if not defined QGIS_ROOT call :detect_qgis_root
if not exist "%QGIS_ROOT%\bin\o4w_env.bat" (
  echo QGIS environment not found.
  echo Set QGIS_ROOT to a QGIS install directory containing bin\o4w_env.bat.
  exit /b 1
)

call "%QGIS_ROOT%\bin\o4w_env.bat"
path %OSGEO4W_ROOT%\apps\qgis-ltr\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis-ltr
set GDAL_FILENAME_IS_UTF8=YES
set VSI_CACHE=TRUE
set VSI_CACHE_SIZE=1000000
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr\qtplugins;%OSGEO4W_ROOT%\apps\qt5\plugins
set QT_QPA_PLATFORM=offscreen
set PYTHONPATH=%~dp0..;%OSGEO4W_ROOT%\apps\qgis-ltr\python;%PYTHONPATH%
set PYTHONFAULTHANDLER=1

python "%~dp0qgis-smoke-test.py" %*
exit /b %ERRORLEVEL%

:detect_qgis_root
for /d %%D in ("%ProgramFiles%\QGIS*") do (
  if exist "%%~D\bin\o4w_env.bat" (
    set "QGIS_ROOT=%%~D"
    exit /b 0
  )
)
for %%D in ("%SystemDrive%\OSGeo4W" "%SystemDrive%\OSGeo4W64") do (
  if exist "%%~D\bin\o4w_env.bat" (
    set "QGIS_ROOT=%%~D"
    exit /b 0
  )
)
exit /b 0
