# deploy_driver.ps1 - 部署驱动脚本 (需以管理员身份运行)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutDir = "$ScriptDir\bin\Release"
$DriverPath = "$OutDir\hwbp_driver.sys"
$DriverName = "HwBpDriver"
$ServiceName = "HwBpDriver"

Write-Host "=== HwBpDriver 部署脚本 ===" -ForegroundColor Cyan

if (!(Test-Path $DriverPath)) {
    Write-Host "错误: 找不到驱动文件 $DriverPath" -ForegroundColor Red
    Write-Host "请先运行 compile_driver.ps1 编译驱动" -ForegroundColor Yellow
    exit 1
}

# 1. 开启 Test Signing
Write-Host "[1/4] 开启 Test Signing..." -ForegroundColor Yellow
$testsigning = bcdedit /enum | Select-String "testsigning"
if ($testsigning -match "Yes") {
    Write-Host "  Test Signing 已开启" -ForegroundColor Green
} else {
    bcdedit /set testsigning on
    Write-Host "  Test Signing 已开启，需要重启后生效" -ForegroundColor Yellow
    $rebootNeeded = $true
}

# 2. 导入证书
Write-Host "[2/4] 导入签名证书..." -ForegroundColor Yellow
$certFile = "$OutDir\hwbp_cert.cer"
if (Test-Path $certFile) {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certFile)
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $existing = $store.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if ($existing) {
        Write-Host "  证书已在受信任的根证书颁发机构中" -ForegroundColor Green
    } else {
        $store.Add($cert)
        Write-Host "  证书已导入到受信任的根证书颁发机构" -ForegroundColor Green
    }
    $store.Close()

    $tpStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher", "LocalMachine")
    $tpStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $tpExisting = $tpStore.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if ($tpExisting) {
        Write-Host "  证书已在受信任的发布者中" -ForegroundColor Green
    } else {
        $tpStore.Add($cert)
        Write-Host "  证书已导入到受信任的发布者" -ForegroundColor Green
    }
    $tpStore.Close()
}

# 3. 停止并删除旧服务
Write-Host "[3/4] 配置驱动服务..." -ForegroundColor Yellow
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -eq "Running") {
        sc.exe stop $ServiceName 2>$null
        Start-Sleep -Seconds 2
    }
    sc.exe delete $ServiceName 2>$null
    Start-Sleep -Seconds 1
    Write-Host "  旧服务已删除" -ForegroundColor Gray
}

# 4. 创建新服务
sc.exe create $ServiceName type= kernel start= demand binPath= "$DriverPath" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  创建服务失败" -ForegroundColor Red
} else {
    Write-Host "  服务创建成功" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Cyan
if ($rebootNeeded) {
    Write-Host ""
    Write-Host "!!! 需要重启系统以启用 Test Signing !!!" -ForegroundColor Red
    Write-Host ""
    Write-Host "重启后，以管理员身份运行以下命令启动驱动:" -ForegroundColor Yellow
    Write-Host "  sc.exe start HwBpDriver" -ForegroundColor White
    Write-Host ""
    Write-Host "或者使用 Python 客户端:" -ForegroundColor Yellow
    Write-Host "  python hwbp_driver_client.py" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "现在可以启动驱动:" -ForegroundColor Yellow
    Write-Host "  sc.exe start HwBpDriver" -ForegroundColor White
}