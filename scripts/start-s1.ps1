# S1 子赛题演示一键启动 (Windows PowerShell, 本地开发)
# 启动: 拓扑引擎(9001) + LLM服务(9002) + M03后端(8083) + M03前端(9000)
# 前置: MySQL/Redis 已运行
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = (Resolve-Path "$PSScriptRoot/..").Path
$LOG = "$env:TEMP\s1_demo_$(Get-Date -Format yyyyMMdd).log"
Write-Host "S1 演示启动中，日志见 $LOG" -ForegroundColor Cyan

function Start-S1Service {
  param([string]$Name, [string]$Dir, [scriptblock]$Action)
  Write-Host "[启动] $Name ..." -ForegroundColor Green
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Dir'; $Action" -WindowStyle Normal
}

# 1. 拓扑引擎 (9001)
if (Test-Path "$ProjectRoot\packages\m03-topology-engine\start.ps1") {
  Start-S1Service "拓扑引擎(9001)" "$ProjectRoot\packages\m03-topology-engine" { .\start.ps1 }
} else { Write-Host "[跳过] 未找到 start.ps1" -ForegroundColor Yellow }

# 2. LLM 服务 (9002)
if (Test-Path "$ProjectRoot\packages\m03-llm-service") {
  Start-S1Service "LLM服务(9002)" "$ProjectRoot\packages\m03-llm-service" {
    if (-not (Test-Path .venv)) { python -m venv .venv }
    .venv\Scripts\python.exe -m pip install -q -r requirements.txt
    .venv\Scripts\python.exe main.py
  }
} else { Write-Host "[跳过] 未找到 m03-llm-service" -ForegroundColor Yellow }

# 3. M03 后端 (8083)
if (Test-Path "$ProjectRoot\packages\m03-bim-gis\backend") {
  Start-S1Service "M03后端(8083)" "$ProjectRoot\packages\m03-bim-gis\backend" {
    mvn -q spring-boot:run "-Dspring-boot.run.arguments=--server.port=8083"
  }
} else { Write-Host "[跳过] 未找到 m03-bim-gis/backend" -ForegroundColor Yellow }

# 4. M03 前端 (9000)
if (Test-Path "$ProjectRoot\packages\m03-bim-gis\frontend") {
  Start-S1Service "M03前端(9000)" "$ProjectRoot\packages\m03-bim-gis\frontend" {
    if (-not (Test-Path node_modules)) { npm install }
    npm run dev
  }
} else { Write-Host "[跳过] 未找到 m03-bim-gis/frontend" -ForegroundColor Yellow }

Write-Host "全部已在新窗口启动。检查: curl http://127.0.0.1:9001/health" -ForegroundColor Cyan
