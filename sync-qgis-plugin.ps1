# 同步 QGIS 插件代码到 QGIS 插件目录
# 用法: sync-qgis-plugin.ps1
# 放在项目根目录 D:\homework\xind2\xind2\

$SRC = "D:\homework\xind2\xind2\qgis-plugin"
$DST = "C:\Users\gao15\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\qgis-plugin-complete"

Write-Host "[1/3] 同步文件..." -ForegroundColor Cyan

# 递归复制所有文件
$files = Get-ChildItem -Path $SRC -Recurse -File
$count = 0
foreach ($f in $files) {
    $relPath = $f.FullName.Substring($SRC.Length + 1)
    $destFile = Join-Path $DST $relPath
    $destDir = Split-Path $destFile -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -Path $f.FullName -Destination $destFile -Force
    $count++
}

# 创建空目录
$dirs = Get-ChildItem -Path $SRC -Recurse -Directory
foreach ($d in $dirs) {
    $relPath = $d.FullName.Substring($SRC.Length + 1)
    $destDir = Join-Path $DST $relPath
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
}

Write-Host "  已同步 $count 个文件" -ForegroundColor Green

Write-Host "[2/3] 清理 __pycache__ ..." -ForegroundColor Cyan
$pycache_dirs = Get-ChildItem -Path $DST -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
foreach ($p in $pycache_dirs) {
    Remove-Item -Path $p.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "  完成" -ForegroundColor Green

Write-Host "[3/3] 在 QGIS 中: 插件 -> 卸载插件 -> 重新安装 -> 启用" -ForegroundColor Yellow
Write-Host ""
Write-Host "同步完成。" -ForegroundColor Green
