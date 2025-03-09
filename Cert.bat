:: Runs Powershell script titled sign_script.ps1 in signing kit folder 
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0sign_script.ps1"

timeout /t 1

:: Renames the .exe file without spaces (if applicable) as spaces cannot be included! 
ren "My Application Name.exe" "MyApplicationName.exe"

timeout /t 1

:: Opens first CMD Session and closes it thereafter
start cmd /c signtool.exe sign /f MyApplicationName.pfx /fd SHA256 /p YourPassword MyApplicationName.exe

timeout /t 1

:: Opens second CMD Session as new session is required to apply the timestamp
start cmd /c signtool.exe timestamp -t http://timestamp.digicert.com MyApplicationName.exe

timeout /t 1

:: Renames the .exe back to the original file name (if applicable)
ren "MyApplicationName.exe" "My Application Name.exe"

timeout /t 1

:: Tells the user that the signing has completed!
@echo Signing Complete! Press any key to continue! 
pause
