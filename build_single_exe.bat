@echo off
title Build 1 File EXE Standalone - AKP Beton
color 0A
echo ===================================================
echo   MEMBUAT 1 FILE EXE STANDALONE (SIAP KIRIM LANGSUNG)
echo   Output: dist\AKP_Beton_Standalone.exe
echo ===================================================
echo.
echo [1/2] Memeriksa dependensi...
python -m pip install -r requirements.txt pyinstaller
echo.
echo [2/2] Mengompilasi menjadi satu file .EXE tunggal...
python -m PyInstaller --clean -y AKP_Beton_SingleFile.spec

if exist "dist\AKP_Beton_Standalone.exe" (
    echo.
    echo ===================================================
    echo [SUKSES] File EXE tunggal siap dikirimkan!
    echo Anda bisa langsung mengirimkan file ini ke teman Anda:
    echo   dist\AKP_Beton_Standalone.exe
    echo ===================================================
    explorer /select,"dist\AKP_Beton_Standalone.exe"
) else (
    echo [GAGAL] Terjadi kesalahan saat proses kompilasi.
)
pause
