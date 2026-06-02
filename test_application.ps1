# 测试应用程序启动脚本
$appPath = "d:\py\反编译\FreeStyle\bin\Debug\net8.0-windows\FS服装搭配专家v1.0.exe"
$logPath = "d:\py\反编译\app_test.log"

# 清空之前的日志
Clear-Content -Path $logPath -ErrorAction SilentlyContinue

Write-Host "开始测试应用程序启动..."
Write-Host "应用程序路径: $appPath"
Write-Host "日志文件: $logPath"

# 启动应用程序并捕获输出
try {
    # 记录启动时间
    $startTime = Get-Date
    Write-Host "启动时间: $startTime"
    Add-Content -Path $logPath -Value "=== 测试开始 ==="
    Add-Content -Path $logPath -Value "启动时间: $startTime"
    
    # 启动应用程序
    $process = Start-Process -FilePath $appPath -PassThru -NoNewWindow
    
    # 等待应用程序启动
    Write-Host "应用程序已启动，进程ID: $($process.Id)"
    Add-Content -Path $logPath -Value "应用程序已启动，进程ID: $($process.Id)"
    
    # 等待一段时间，让应用程序有时间初始化
    Start-Sleep -Seconds 10
    
    # 检查进程是否仍在运行
    if ($process.HasExited) {
        Write-Host "应用程序已退出，退出代码: $($process.ExitCode)"
        Add-Content -Path $logPath -Value "应用程序已退出，退出代码: $($process.ExitCode)"
    } else {
        Write-Host "应用程序仍在运行"
        Add-Content -Path $logPath -Value "应用程序仍在运行"
        
        # 尝试获取窗口信息
        try {
            $mainWindowTitle = $process.MainWindowTitle
            Write-Host "主窗口标题: $mainWindowTitle"
            Add-Content -Path $logPath -Value "主窗口标题: $mainWindowTitle"
        } catch {
            Write-Host "无法获取窗口标题: $($_.Exception.Message)"
            Add-Content -Path $logPath -Value "无法获取窗口标题: $($_.Exception.Message)"
        }
        
        # 终止进程（仅用于测试）
        # $process.Kill()
        # Write-Host "已终止测试进程"
        # Add-Content -Path $logPath -Value "已终止测试进程"
    }
    
    # 记录结束时间
    $endTime = Get-Date
    $duration = New-TimeSpan -Start $startTime -End $endTime
    Write-Host "结束时间: $endTime"
    Write-Host "持续时间: $($duration.TotalSeconds) 秒"
    Add-Content -Path $logPath -Value "结束时间: $endTime"
    Add-Content -Path $logPath -Value "持续时间: $($duration.TotalSeconds) 秒"
    Add-Content -Path $logPath -Value "=== 测试完成 ==="
    
} catch {
    Write-Host "启动应用程序时出错: $($_.Exception.Message)"
    Add-Content -Path $logPath -Value "启动应用程序时出错: $($_.Exception.Message)"
    Add-Content -Path $logPath -Value "堆栈跟踪: $($_.Exception.StackTrace)"
    Add-Content -Path $logPath -Value "=== 测试失败 ==="
}

Write-Host "测试完成，请查看日志文件获取详细信息: $logPath"
