@echo off
REM archive.cmd — 快速归档 + git commit
REM 用法: archive [进度文件名] [commit message]
REM 示例: archive progress_20260531.md
REM        archive (自动找最新的progress文件)

cd /d "D:\py\反编译\FreeStyle\apollo_dump"

if "%~1"=="" (
    REM 找最新的progress文件
    for /f "delims=" %%f in ('dir /b /o-d progress\progress_*.md 2^>nul') do (
        set "LATEST=progress\%%f"
        goto :found
    )
    echo No progress files found
    exit /b 1
    :found
) else (
    set "LATEST=%~1"
)

echo === Archiving: %LATEST% ===
python archive_session.py "%LATEST%"

echo.
echo === Git commit ===
cd /d "D:\py\反编译\FreeStyle"
git add -A
if "%~2"=="" (
    git commit -m "archive: %LATEST%"
) else (
    git commit -m "%~2"
)
echo === Done ===
