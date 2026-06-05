# compile_driver.ps1
# Direct compilation of HwBpDriver.sys (no VS WDK integration needed)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$VS = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
$WDK = "C:\Program Files (x86)\Windows Kits\10"
$SDK_VER = "10.0.22621.0"
$WDK_VER = "10.0.22000.0"

# Find MSVC version
$msvcDir = Get-ChildItem "$VS\VC\Tools\MSVC" -Directory | Sort-Object Name -Descending | Select-Object -First 1
if (-not $msvcDir) { Write-Host "MSVC not found!" -ForegroundColor Red; exit 1 }
$MSVC = $msvcDir.FullName

# Find cl.exe and link.exe
$cl = Get-ChildItem "$MSVC\bin\Hostx64\x64\cl.exe" -ErrorAction SilentlyContinue
if (-not $cl) { Write-Host "cl.exe not found!" -ForegroundColor Red; exit 1 }
$link = Get-ChildItem "$MSVC\bin\Hostx64\x64\link.exe" -ErrorAction SilentlyContinue
if (-not $link) { Write-Host "link.exe not found!" -ForegroundColor Red; exit 1 }

Write-Host "=== Compiler ===" -ForegroundColor Cyan
Write-Host "MSVC: $MSVC"
Write-Host "CL:   $($cl.FullName)"
Write-Host "LINK: $($link.FullName)"
Write-Host ""

# Output directory
$OutDir = "$ScriptDir\bin\Release"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Build CL arguments
$IncFlags = @(
    "/I`"$WDK\Include\$WDK_VER\km`""
    "/I`"$WDK\Include\$SDK_VER\shared`""
    "/I`"$WDK\Include\$WDK_VER\shared`""
    "/I`"$WDK\Include\$WDK_VER\km\crt`""
    "/I`"$WDK\Include\wdf\kmdf\1.31`""
    "/I`"$MSVC\include`""
) -join " "

$DefFlags = @(
    "/D_WIN64"
    "/D_AMD64_"
    "/D_WIN32"
    "/DWINVER=0x0A00"
    "/D_WIN32_WINNT=0x0A00"
    "/DNTDDI_VERSION=0x0A00000B"
    "/DDBG=1"
    "/DDEVL=1"
    "/D_KERNEL_MODE"
    "/DUNICODE"
    "/D_UNICODE"
    "/DNDEBUG"
) -join " "

$CompileFlags = @(
    "/nologo"
    "/c"
    "/GS-"
    "/Gs9999999"
    "/Zp8"
    "/Gy"
    "/Gm-"
    "/Zi"
    "/O1"
    "/Oi"
    "/Os"
    "/Oy-"
    "/W3"
    "/WX-"
    "/Gz"
    "/Fd$OutDir\"
    "/Fo$OutDir\"
) -join " "

$Source = "$ScriptDir\hwbp_driver.c"
$Obj = "$OutDir\hwbp_driver.obj"

$ClArgs = "$CompileFlags $DefFlags $IncFlags `"$Source`""
Write-Host "Compiling..." -ForegroundColor Yellow
Write-Host "cl.exe $ClArgs" -ForegroundColor Gray

$proc = Start-Process -FilePath $cl.FullName -ArgumentList $ClArgs -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host "COMPILE FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "Compile OK" -ForegroundColor Green

# Build LINK arguments
$LibFlags = "/LIBPATH:`"$WDK\Lib\$WDK_VER\km\x64`" /LIBPATH:`"$WDK\Lib\$SDK_VER\um\x64`" /LIBPATH:`"$MSVC\lib\x64`""

$LinkFlags = @(
    "/NOLOGO"
    "/DRIVER"
    "/NODEFAULTLIB"
    "/ENTRY:DriverEntry"
    "/SUBSYSTEM:NATIVE"
    "/MACHINE:X64"
    "/OPT:REF"
    "/OPT:ICF"
    "/RELEASE"
    "/MERGE:_PAGE=PAGE"
    "/MERGE:_TEXT=.text"
    "/IGNORE:4198,4010,4037,4039,4065,4070,4078,4087,4089,4096,4098,4108,4200,4221,4104"
    "/STACK:0x40000,0x1000"
    "/MANIFEST:NO"
    "/PDB:$OutDir\hwbp_driver.pdb"
    "/OUT:$OutDir\hwbp_driver.sys"
    "`"$Obj`""
    "ntoskrnl.lib"
    "hal.lib"
    "wmilib.lib"
    "ntstrsafe.lib"
    "bufferoverflowfastfailk.lib"
) -join " "

$LinkArgs = "$LinkFlags $LibFlags"
Write-Host "Linking..." -ForegroundColor Yellow
Write-Host "link.exe $LinkArgs" -ForegroundColor Gray

$proc = Start-Process -FilePath $link.FullName -ArgumentList $LinkArgs -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host "LINK FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "Link OK" -ForegroundColor Green

# Verify
if (Test-Path "$OutDir\hwbp_driver.sys") {
    $size = (Get-Item "$OutDir\hwbp_driver.sys").Length
    Write-Host ""
    Write-Host "=== BUILD SUCCESS ===" -ForegroundColor Green
    Write-Host "Output: $OutDir\hwbp_driver.sys" -ForegroundColor Cyan
    Write-Host "Size: $([math]::Round($size/1024, 1)) KB" -ForegroundColor Cyan
} else {
    Write-Host "BUILD FAILED: Output not found" -ForegroundColor Red
    exit 1
}