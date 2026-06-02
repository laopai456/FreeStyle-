@echo off
chcp 936 >nul
setlocal enabledelayedexpansion

:MENU
cls
echo.
echo   FreeStyle 发型替换工具
echo   ========================
echo.
echo   [ 1] 极限超赛发型       50120651
echo   [ 2] 超赛之神发型       50121251
echo   [ 3] 淡粉超赛发型       50121981
echo   [ 4] 鬼魅发型           50122451
echo   [ 5] 火焰超赛发型       50122921
echo   [ 6] 金色超赛发型       50124241
echo   [ 7] 萌犬球帽发型       50124741
echo   [ 8] 狂战士纯白发型     50124871
echo   [ 9] 鬼魅白发           50124941
echo   [10] 霓虹超赛发型       50124971
echo   [11] 破坏者超赛发型     50125031
echo   [12] 疾风剑客黑发       50125491
echo   [13] 闪耀金超赛发型     50125651
echo   [14] 少年漫主角发型     50125671
echo   [15] 少年漫劲敌发型     50125681
echo   [16] 紫色超赛发型       50125711
echo.
echo   [ 0] 退出
echo.

set "code="
set /p choice=请输入序号:

if "%choice%"=="" goto MENU
if "%choice%"=="0" exit /b

if "%choice%"=="1"  set "code=50120651"
if "%choice%"=="2"  set "code=50121251"
if "%choice%"=="3"  set "code=50121981"
if "%choice%"=="4"  set "code=50122451"
if "%choice%"=="5"  set "code=50122921"
if "%choice%"=="6"  set "code=50124241"
if "%choice%"=="7"  set "code=50124741"
if "%choice%"=="8"  set "code=50124871"
if "%choice%"=="9"  set "code=50124941"
if "%choice%"=="10" set "code=50124971"
if "%choice%"=="11" set "code=50125031"
if "%choice%"=="12" set "code=50125491"
if "%choice%"=="13" set "code=50125651"
if "%choice%"=="14" set "code=50125671"
if "%choice%"=="15" set "code=50125681"
if "%choice%"=="16" set "code=50125711"

if "%code%"=="" (
    echo.
    echo  无效选择!
    pause
    goto MENU
)

echo.
echo  已选择: %code%
echo.

cd /d "D:\py\反编译\FreeStyle\apollo_dump"
python 1.py %code%

echo.
echo  按任意键返回菜单换发型，或关闭窗口退出...
pause >nul
goto MENU
