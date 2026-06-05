# compile_dll.ps1
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$VS = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
$MSVC = Get-ChildItem "$VS\VC\Tools\MSVC" -Directory | Sort-Object Name -Descending | Select-Object -First 1
if (-not $MSVC) { Write-Host "MSVC not found at $VS" -ForegroundColor Red; exit 1 }
$cl = "$MSVC\bin\Hostx64\x64\cl.exe"
$link = "$MSVC\bin\Hostx64\x64\link.exe"
$SDK = "C:\Program Files (x86)\Windows Kits\10"
$SDK_VER = "10.0.22621.0"

$OutDir = "$ScriptDir\bin"
New-Object -TypeName System.IO.DirectoryInfo -ArgumentList $OutDir | ForEach-Object { if(!$_.Exists){$_.Create()} }

$IncFlags = "/I`"$SDK\Include\$SDK_VER\um`" /I`"$SDK\Include\$SDK_VER\shared`" /I`"$MSVC\include`""
$LibFlags = "/LIBPATH:`"$SDK\Lib\$SDK_VER\um\x64`" /LIBPATH:`"$MSVC\lib\x64`""

Write-Host "Compiling veh_hook.dll ..." -ForegroundColor Yellow
& $cl /nologo /c /O1 /GS- "$ScriptDir\veh_hook.c" /Fo"$OutDir\veh_hook.obj" $IncFlags /D_WIN64 /D_AMD64_ /DWIN32 /D_WINDOWS
if ($LASTEXITCODE -ne 0) { Write-Host "COMPILE FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Compile OK" -ForegroundColor Green

& $link /NOLOGO /DLL /MACHINE:X64 /OUT:"$OutDir\veh_hook.dll" "$OutDir\veh_hook.obj" $LibFlags kernel32.lib user32.lib
if ($LASTEXITCODE -ne 0) { Write-Host "LINK FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Link OK" -ForegroundColor Green

if (Test-Path "$OutDir\veh_hook.dll") {
    $size = (Get-Item "$OutDir\veh_hook.dll").Length
    Write-Host "=== BUILD SUCCESS ===" -ForegroundColor Green
    Write-Host "Output: $OutDir\veh_hook.dll ($([math]::Round($size/1024,1)) KB)" -ForegroundColor Cyan
}