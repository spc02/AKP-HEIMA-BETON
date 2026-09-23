@echo off
echo =========================================================
echo   MEMBUAT SHORTCUT DESKTOP AKP CONTRUCTION BUILDING
echo =========================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Desktop = [System.Environment]::GetFolderPath('Desktop'); " ^
  "$Shortcut = $WshShell.CreateShortcut(\"$Desktop\AKP Contruction Building.lnk\"); " ^
  "$Shortcut.TargetPath = \"$PSScriptRoot\AKP Contruction Building.exe\"; " ^
  "$Shortcut.WorkingDirectory = \"$PSScriptRoot\"; " ^
  "$Shortcut.IconLocation = \"$PSScriptRoot\AKP Contruction Building.exe,0\"; " ^
  "$Shortcut.Description = 'AKP Contruction Building - Sistem Batching Plant'; " ^
  "$Shortcut.Save(); " ^
  "Write-Host '[SUKSES] Shortcut aplikasi berhasil dipasang di Desktop!' -ForegroundColor Green"
echo.
echo =========================================================
pause
