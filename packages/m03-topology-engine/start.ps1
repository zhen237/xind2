# M03 拓扑规划引擎启动脚本 (Windows, 本地开发用)
# 用法: .\start.ps1   (或在 PowerShell 中运行)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 优先 python3，否则 python
$py = (Get-Command python3 -ErrorAction SilentlyContinue)?.Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source }
if (-not $py) {
    Write-Error "未找到 python3/python，请先安装 Python 3.10+"
    exit 1
}

# 首次运行建 venv 并装依赖
if (-not (Test-Path .venv)) {
    Write-Host "[1/3] 创建虚拟环境 ..."
    & $py -m venv .venv
}
& .venv\Scripts\python.exe -m pip install -q --upgrade pip
Write-Host "[2/3] 安装依赖 ..."
& .venv\Scripts\python.exe -m pip install -q -r requirements.txt

Write-Host "[3/3] 启动拓扑引擎 (127.0.0.1:9001) ..."
# 仅监听本机回环：引擎只供同机 M03 后端调用，不暴露公网
& .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 9001
