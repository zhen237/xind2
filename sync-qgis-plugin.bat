@echo off
REM 同步 QGIS 插件代码到 QGIS 插件目录
REM 用法: sync-qgis-plugin.bat
REM 放在项目根目录 D:\homework\xind2\xind2\

set SRC=D:\homework\xind2\xind2\qgis-plugin
set DST=C:\Users\gao15\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\qgis-plugin-complete

echo [1/3] 同步文件...
xcopy "%SRC%\*" "%DST%\" /E /Y /Q >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: 同步失败
    exit /b 1
)
echo   完成

echo [2/3] 清理缓存...
for /d /r "%DST%" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)
echo   完成

echo [3/3] 在 QGIS 中: 插件 -> 卸载插件 -> 重新安装 -> 启用
echo.
echo 同步完成。
