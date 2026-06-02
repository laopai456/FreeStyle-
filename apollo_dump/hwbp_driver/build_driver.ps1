# build_driver.ps1
# 编译 HwBpDriver.sys 内核驱动
#
# 前置条件:
#   1. Visual Studio 2022 安装 "Desktop development with C++"
#   2. Windows Driver Kit (WDK) for Windows 10
#   3. 管理员权限 (用于测试签名)
#
# 用法:
#   .\build_driver.ps1              # 编译 Release 版本
#   .\build_driver.ps1 -Debug       # 编译 Debug 版本
#   .\build_driver.ps1 -Sign        # 编译并测试签名

param(
    [switch]$Debug,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Configuration = if ($Debug) { "Debug" } else { "Release" }
$Platform = "x64"
$OutputDir = Join-Path $ScriptDir "bin\$Configuration"

Write-Host "=== HwBpDriver Build Script ===" -ForegroundColor Cyan
Write-Host "Configuration: $Configuration"
Write-Host "Platform: $Platform"
Write-Host ""

# 查找 VS 和 WDK
$VSWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $VSWhere) {
    $VSPath = & $VSWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($VSPath) {
        Write-Host "Found Visual Studio: $VSPath" -ForegroundColor Green
    }
}

# 查找 msbuild
$msbuild = Get-ChildItem -Path "C:\Program Files\Microsoft Visual Studio\2022" -Filter "MSBuild.exe" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -eq "Current" -or $_.Directory.Name -match "^15\." -or $_.Directory.Name -match "^16\." } |
    Select-Object -First 1

if (-not $msbuild) {
    $msbuild = Get-ChildItem -Path "C:\Program Files (x86)\Microsoft Visual Studio" -Filter "MSBuild.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

if (-not $msbuild) {
    Write-Host "ERROR: Cannot find MSBuild.exe. Please install Visual Studio." -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Use 'Developer Command Prompt for VS 2022' and run:"
    Write-Host "  msbuild hwbp_driver.vcxproj /p:Configuration=$Configuration /p:Platform=$Platform"
    exit 1
}

Write-Host "MSBuild: $($msbuild.FullName)"
Write-Host ""

# 编译
$ProjectFile = Join-Path $ScriptDir "hwbp_driver.vcxproj"
Write-Host "Building $ProjectFile ..." -ForegroundColor Yellow

$result = & $msbuild.FullName $ProjectFile `
    /p:Configuration=$Configuration `
    /p:Platform=$Platform `
    /t:Build `
    /v:minimal

if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "BUILD SUCCESS" -ForegroundColor Green
Write-Host ""

# 查找输出文件
$driverFile = Get-ChildItem -Path $ScriptDir -Filter "*.sys" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*HwBp*" -and $_.FullName -like "*$Configuration*" } |
    Select-Object -First 1

if ($driverFile) {
    Write-Host "Driver: $($driverFile.FullName)" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($driverFile.Length / 1024, 1)) KB"
    Write-Host ""

    # 复制到输出目录
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    Copy-Item $driverFile.FullName -Destination (Join-Path $OutputDir "HwBpDriver.sys") -Force
    Write-Host "Copied to: $OutputDir\HwBpDriver.sys" -ForegroundColor Green
}

# 测试签名
if ($Sign) {
    Write-Host ""
    Write-Host "--- Signing (Test) ---" -ForegroundColor Yellow
    $signTool = Get-ChildItem -Path "C:\Program Files (x86)\Windows Kits\10\bin" -Filter "signtool.exe" -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*x64*" } |
        Select-Object -First 1

    if ($signTool) {
        $outputSys = Join-Path $OutputDir "HwBpDriver.sys"
        if (Test-Path $outputSys) {
            & $signTool.FullName sign /v /fd SHA256 /a $outputSys
            Write-Host "Test signing complete" -ForegroundColor Green
        }
    } else {
        Write-Host "SignTool not found, skipping signing" -ForegroundColor Yellow
        Write-Host "To sign manually: signtool sign /v /fd SHA256 /a HwBpDriver.sys"
    }
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Enable test signing: bcdedit /set testsigning on"
Write-Host "2. Reboot"
Write-Host "3. Load driver: sc create HwBpDriver type= kernel binPath= `"$OutputDir\HwBpDriver.sys`""
Write-Host "4. Start driver: sc start HwBpDriver"
Write-Host "5. Run client: python hwbp_driver_client.py"