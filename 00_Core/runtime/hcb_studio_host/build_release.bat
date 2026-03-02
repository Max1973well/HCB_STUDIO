@echo off
setlocal

echo [HCB] Building native host (release)...
cargo build --release
if errorlevel 1 (
  echo [HCB] Build failed.
  exit /b 1
)

set DIST_DIR=F:\HCB_STUDIO\00_Core\dist
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

copy /Y "target\release\hcb_studio_host.exe" "%DIST_DIR%\hcb_studio_host.exe" >nul
if errorlevel 1 (
  echo [HCB] Copy failed.
  exit /b 1
)

echo [HCB] Done. Binary: %DIST_DIR%\hcb_studio_host.exe
exit /b 0
