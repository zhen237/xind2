@echo off
chcp 65001
echo ========================================
echo   通信平台 - 一键启动脚本
echo ========================================
echo.

echo [1/5] 启动MySQL服务...
net start MySQL80 2>nul
if %errorlevel% equ 0 (
    echo   ✓ MySQL已启动
) else (
    echo   ⚠ MySQL已在运行或启动失败
)
echo.

echo [2/5] 启动Redis服务...
net start Redis 2>nul
if %errorlevel% equ 0 (
    echo   ✓ Redis已启动
) else (
    echo   ⚠ Redis已在运行或未安装
)
echo.

echo [3/5] 启动M01认证服务（端口8080）...
start "M01-Auth" cmd /k "cd /d D:\homework\xind2\xind2\packages\m01-auth\backend && mvn spring-boot:run"
echo   ✓ 已在新窗口启动M01
echo.

echo [4/5] 启动M05运维服务（端口8085）...
start "M05-TwinOps" cmd /k "cd /d D:\homework\xind2\xind2\packages\m05-twin-ops\backend && mvn spring-boot:run"
echo   ✓ 已在新窗口启动M05
echo.

echo [5/5] 启动M06前端门户（端口5173）...
start "M06-Portal" cmd /k "cd /d D:\homework\xind2\xind2\packages\m06-portal && npm run dev"
echo   ✓ 已在新窗口启动M06
echo.

echo ========================================
echo   启动完成！
echo ========================================
echo.
echo   访问地址：
echo   - 前端：http://localhost:5173
echo   - M01 API：http://localhost:8080
echo   - M05 API：http://localhost:8085
echo.
echo   请等待各服务完全启动后访问
echo ========================================
pause
