@echo off
echo ===================================================
echo   MEMULAI PROSES BUILD AKP CONTRUCTION BUILDING (.EXE)
echo   Mode: Standalone Folder (Instan Startup / No Lag)
echo ===================================================

echo [1/3] Memeriksa dependensi Python...
python -m pip install -r requirements.txt

echo [2/3] Mengompilasi aplikasi ke format folder terdistribusi...
python -m PyInstaller --clean -y "AKP_Contruction_Building.spec"

echo.
echo ===================================================
if exist "dist\AKP Contruction Building\AKP Contruction Building.exe" (
    echo [SUKSES] Executable berhasil dibuat!
    echo Lokasi Folder: dist\AKP Contruction Building\
    echo.
    echo Menyiapkan file pendukung dalam paket distribusi...
    if exist "akp_beton.db" copy /Y "akp_beton.db" "dist\AKP Contruction Building\_internal\akp_init.dat"
    if exist "dist\AKP Contruction Building\akp_beton.db" del /F /Q "dist\AKP Contruction Building\akp_beton.db"
    if exist "Buat_Shortcut_Desktop.bat" copy /Y "Buat_Shortcut_Desktop.bat" "dist\AKP Contruction Building\"
    
    echo.
    echo [3/3] Mengompresi paket distribusi ke file ZIP...
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\AKP Contruction Building' -DestinationPath 'dist\AKP_Contruction_Building.zip' -Force"
    echo.
    echo ===================================================
    echo [SELESAI] Paket distribusi siap dibagikan:
    echo 1. Folder: dist\AKP Contruction Building\
    echo 2. File ZIP: dist\AKP_Contruction_Building.zip
    echo Aplikasi akan terbuka instan tanpa jeda dekompresi!
) else (
    echo [GAGAL] Terjadi kesalahan saat proses build.
)
echo ===================================================
pause
