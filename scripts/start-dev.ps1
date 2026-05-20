#!/usr/bin/env pwsh
# 一键启动脚本 - Windows PowerShell
# 使用方法: .\start-dev.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  通信基建数智化平台 - 一键启动" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 检测是否以管理员权限运行
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[警告] 建议以管理员权限运行以避免端口冲突" -ForegroundColor Yellow
}

# 1. 检查 Docker 是否运行
Write-Host "[1/5] 检查 Docker 状态..." -ForegroundColor Green
try {
    docker info | Out-Null
    Write-Host "  Docker 运行正常" -ForegroundColor Green
} catch {
    Write-Host "  [错误] Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 2. 启动 Docker Compose 服务
Write-Host "[2/5] 启动数据库和中间件服务..." -ForegroundColor Green
Set-Location $ProjectRoot
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [错误] Docker Compose 启动失败" -ForegroundColor Red
    exit 1
}
Write-Host "  Docker Compose 服务启动成功" -ForegroundColor Green

# 等待 MySQL 启动
Write-Host "  等待 MySQL 启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 3. 初始化数据库
Write-Host "[3/5] 初始化数据库..." -ForegroundColor Green
$sqlContent = Get-Content "$ProjectRoot\scripts\init-db.sql" -Raw

docker exec -i comm-mysql mysql -uroot -proot123 <<< $sqlContent
if ($LASTEXITCODE -eq 0) {
    Write-Host "  数据库初始化成功" -ForegroundColor Green
} else {
    Write-Host "  [警告] 数据库初始化可能失败，请检查" -ForegroundColor Yellow
}

# 4. 启动后端服务
Write-Host "[4/5] 启动后端服务..." -ForegroundColor Green

# M01 认证服务
Write-Host "  启动 M01 认证服务 (端口 8080)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\packages\m01-auth\backend'; mvn spring-boot:run" -WindowStyle Normal

# M05 运维服务
Write-Host "  启动 M05 智慧运维服务 (端口 8085)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\packages\m05-twin-ops\backend'; mvn spring-boot:run" -WindowStyle Normal

# 5. 安装并启动前端
Write-Host "[5/5] 启动前端门户..." -ForegroundColor Green

# 检查 Node.js
try {
    node --version | Out-Null
} catch {
    Write-Host "  [错误] Node.js 未安装" -ForegroundColor Red
    exit 1
}

Write-Host "  安装前端依赖..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\packages\m06-portal"
npm install

Write-Host "  启动前端开发服务器 (端口 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\packages\m06-portal'; npm run dev" -WindowStyle Normal

# 完成
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  启动完成！" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址：" -ForegroundColor White
Write-Host "  - 前端门户: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  - M01 API:  http://localhost:8080" -ForegroundColor Cyan
Write-Host "  - M05 API:  http://localhost:8085" -ForegroundColor Cyan
Write-Host "  - MinIO:    http://localhost:9001" -ForegroundColor Cyan
Write-Host "  - EMQX:     http://localhost:18083" -ForegroundColor Cyan
Write-Host ""
Write-Host "默认账号: admin / admin123" -ForegroundColor Yellow
Write-Host ""
Write-Host "按 Ctrl+C 停止所有服务" -ForegroundColor Gray
Write-Host ""

# 等待用户中断
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "正在停止所有服务..." -ForegroundColor Yellow
    docker-compose down
}
