@echo off
chcp 65001 >nul
echo GitHub repozitoriyasiga yuklanmoqda...
git push -u origin main
if %ERRORLEVEL% equ 0 (
    echo.
    echo ==============================================
    echo Tabriklaymiz! Kodlar GitHub ga muvaffaqiyatli yuklandi!
    echo ==============================================
) else (
    echo.
    echo Xatolik yuz berdi. Iltimos, yuqoridagi xabarni tekshiring.
)
pause
