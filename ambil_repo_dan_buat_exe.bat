@echo off
setlocal enabledelayedexpansion
title Setup Repository ^& Build EXE - AKP HEIMA BETON
color 0A

echo ===================================================================
echo     AKP CONTRUCTION BUILDING - SETUP REPOSITORY ^& BUILD EXE
echo     Repository: https://github.com/spc02/AKP-HEIMA-BETON.git
echo ===================================================================
echo.

:: 1. Cek Apakah Git Terpasang
where git >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Git terdeteksi di komputer ini.
    if exist ".git" (
        echo [*] Mengambil pembaruan terbaru dari repository (git pull)...
        git pull origin main
    ) else (
        echo [*] Melakukan clone repository...
        git clone https://github.com/spc02/AKP-HEIMA-BETON.git temp_repo
        if exist "temp_repo" (
            xcopy /E /H /Y "temp_repo\*" ".\"
            rmdir /S /Q "temp_repo"
        )
    )
) else (
    echo [!] Git tidak ditemukan. Mengunduh kode sumber langsung dalam bentuk ZIP dari GitHub...
    set "ZIP_URL=https://github.com/spc02/AKP-HEIMA-BETON/archive/refs/heads/main.zip"
    set "ZIP_FILE=AKP-HEIMA-BETON-main.zip"
    
    echo [*] Sedang mengunduh file ZIP dari GitHub...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('!ZIP_URL!', '!ZIP_FILE!')"
    
    if exist "!ZIP_FILE!" (
        echo [*] Mengekstrak file ZIP...
        powershell -NoProfile -Command "Expand-Archive -Path '!ZIP_FILE!' -DestinationPath 'temp_extract' -Force"
        if exist "temp_extract\AKP-HEIMA-BETON-main" (
            xcopy /E /H /Y "temp_extract\AKP-HEIMA-BETON-main\*" ".\"
            rmdir /S /Q "temp_extract"
            del /F /Q "!ZIP_FILE!"
            echo [OK] Kode sumber berhasil diunduh dan diekstrak!
        )
    ) else (
        echo [ERROR] Gagal mengunduh file ZIP dari GitHub. Pastikan komputer terhubung ke internet.
        pause
        exit /b 1
    )
)

echo.
echo ===================================================================
echo [2/4] Memeriksa Instalasi Python...
echo ===================================================================
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di PATH sistem!
    echo Silakan install Python 3.10 atau versi terbaru dari https://www.python.org/
    echo Pastikan mencentang "Add Python to PATH" saat menginstall.
    pause
    exit /b 1
)

python --version
echo.
echo ===================================================================
echo [3/4] Menginstall Dependensi (PySide6, PyInstaller, dll)...
echo ===================================================================
python -m pip install --upgrade pip
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
) else (
    python -m pip install PySide6 openpyxl reportlab cryptography
)
python -m pip install pyinstaller

echo.
echo ===================================================================
echo [4/4] Memulai Proses Kompilasi ke Format Executable (.EXE)...
echo ===================================================================
if exist "build.bat" (
    call build.bat
) else (
    python -m PyInstaller --clean -y "AKP_Contruction_Building.spec"
    if exist "dist\AKP Contruction Building\AKP Contruction Building.exe" (
        echo Menyiapkan arsip ZIP...
        powershell -NoProfile -Command "Compress-Archive -Path 'dist\AKP Contruction Building' -DestinationPath 'dist\AKP_Contruction_Building.zip' -Force"
    )
)

echo.
echo ===================================================================
if exist "dist\AKP Contruction Building\AKP Contruction Building.exe" (
    echo [BERHASIL] File Executable (.exe) dan ZIP siap digunakan!
    echo Folder Aplikasi : dist\AKP Contruction Building\
    echo File ZIP        : dist\AKP_Contruction_Building.zip
    echo.
    echo Membuka folder output di Windows Explorer...
    explorer "dist\AKP Contruction Building"
) else (
    echo [PERHATIAN] Periksa log di atas jika ada dependensi yang belum selesai terpasang.
)
echo ===================================================================
pause
