# ========================================
# 通信基建数智化平台 - 一键启动脚本
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "通信基建数智化平台 - 开发环境启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置项目根目录
$PROJECT_ROOT = "D:\homework\xind2\xind2"

# 检查目录是否存在
if (-not (Test-Path $PROJECT_ROOT)) {
    Write-Host "错误: 项目目录不存在 - $PROJECT_ROOT" -ForegroundColor Red
    Write-Host "请确认项目已克隆到正确位置" -ForegroundColor Yellow
    exit 1
}

# 设置环境变量
$env:JAVA_HOME = "D:\java\jdk-21.0.11"
$env:MAVEN_HOME = "D:\maven\apache-maven-3.9.16-bin"

Write-Host "[1/4] 检查 MySQL 服务..." -ForegroundColor Yellow
# 检查 MySQL 服务（简化检查）
Write-Host "  ✓ 请确保 Navicat 中数据库 comm_platform 已配置完成" -ForegroundColor Green

Write-Host ""
Write-Host "[2/4] 检查 Redis 服务..." -ForegroundColor Yellow
# 尝试连接 Redis
$redisCheck = & "D:\redis\Redis-7.2.14-Windows-x64-msys2\redis-cli.exe" ping 2>$null
if ($redisCheck -eq "PONG") {
    Write-Host "  ✓ Redis 服务运行正常" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Redis 未运行，请手动启动:" -ForegroundColor Yellow
    Write-Host "    cd D:\redis\Redis-7.2.14-Windows-x64-msys2" -ForegroundColor Gray
    Write-Host "    .\redis-server.exe redis.conf" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "请在新的终端窗口中依次执行以下命令:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "【终端 1 - M01 认证服务】" -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "cd $PROJECT_ROOT\packages\m01-auth\backend" -ForegroundColor Cyan
Write-Host "D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd spring-boot:run" -ForegroundColor Cyan
Write-Host ""
Write-Host "【终端 2 - M05 运维服务】" -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "cd $PROJECT_ROOT\packages\m05-twin-ops\backend" -ForegroundColor Cyan
Write-Host "D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd spring-boot:run" -ForegroundColor Cyan
Write-Host ""
Write-Host "【终端 3 - M06 前端门户】" -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "cd $PROJECT_ROOT\packages\m06-portal" -ForegroundColor Cyan
Write-Host "npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动完成后访问: http://localhost:5173" -ForegroundColor Yellow
Write-Host "登录账号: admin / admin123" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 询问是否直接启动
$response = Read-Host "是否现在启动后端服务? (Y/N)"
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    Write-Host "正在启动 M01 认证服务..." -ForegroundColor Cyan

    # 启动 M01 服务
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PROJECT_ROOT\packages\m01-auth\backend'; Write-Host 'M01 认证服务启动中，请等待...'; D:\maven\apache-maven-3.9.16-bin\bin\mvn.cmd spring-boot:run" -Verb RunAs

    Start-Sleep -Seconds 2

    Write-Host "M01 服务已在新的管理员窗口中启动" -ForegroundColor Green
}

Write-Host ""
Write-Host "脚本执行完成！" -ForegroundColor Cyan
