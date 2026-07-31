@echo off
setlocal
cd /d "%~dp0"

set DEST_PYTHON=android_project\app\src\main\python
set DEST_ASSETS=android_project\app\src\main\assets\django_app

echo Copie de core\ et couveuse_project\ vers %DEST_PYTHON% ...
if exist "%DEST_PYTHON%\core" rmdir /s /q "%DEST_PYTHON%\core"
if exist "%DEST_PYTHON%\couveuse_project" rmdir /s /q "%DEST_PYTHON%\couveuse_project"
xcopy /e /i /q core "%DEST_PYTHON%\core"
xcopy /e /i /q couveuse_project "%DEST_PYTHON%\couveuse_project"

echo Copie de templates\ et static\ vers %DEST_ASSETS% ...
if exist "%DEST_ASSETS%\templates" rmdir /s /q "%DEST_ASSETS%\templates"
if exist "%DEST_ASSETS%\static" rmdir /s /q "%DEST_ASSETS%\static"
mkdir "%DEST_ASSETS%" 2>nul
xcopy /e /i /q templates "%DEST_ASSETS%\templates"
xcopy /e /i /q static "%DEST_ASSETS%\static"

echo.
echo IMPORTANT : generez d'abord les migrations sur le projet desktop si ce
echo n'est pas deja fait :  python manage.py makemigrations core
echo.
echo Termine. Ouvrez android_project\ dans Android Studio, laissez Gradle
echo synchroniser, puis lancez l'app sur un emulateur ou un telephone connecte.
pause
