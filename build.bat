@echo off
echo ========================================================
echo   AURORA BUILDER - SISTEM WARGA ONLY
echo ========================================================

:: --- 1. CEK & AKTIFKAN VIRTUAL ENVIRONMENT ---
:: Ganti 'venv' dengan nama folder venv Anda jika berbeda (misal: env, .venv)
if exist venv\Scripts\activate.bat (
    echo [INFO] Mengaktifkan Virtual Environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Folder 'venv' tidak ditemukan!
    echo Pastikan nama folder virtual environment Anda adalah 'venv'.
    pause
    exit /b
)

:: --- 2. BERSIHKAN BUILD LAMA ---
echo [1/2] Membersihkan file build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

:: --- 3. COMPILE APLIKASI UTAMA ---
echo [2/2] Mengompilasi Sistem Warga...
echo       Mohon tunggu, proses ini memakan waktu beberapa menit...

:: Perintah PyInstaller dijalankan DI DALAM venv yang sudah aktif
pyinstaller --noconfirm --onefile --windowed --clean ^
 --name "SistemWarga_App" ^
 --icon "static/iplrw20.png" ^
 --add-data "templates;templates" ^
 --add-data "static;static" ^
 --hidden-import "sqlalchemy.sql.default_comparator" ^
 --hidden-import "engineio.async_drivers.threading" ^
 app.py

:: --- 4. NONAKTIFKAN VENV & SELESAI ---
call deactivate

echo.
echo ========================================================
echo   SUKSES! File 'SistemWarga_App.exe' ada di folder 'dist'
echo ========================================================
pause