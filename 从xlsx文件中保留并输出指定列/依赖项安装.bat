@echo off
echo 正在安装数据清洗工具所需的Python依赖项...
echo 请确保已经安装了Python 3.6或更高版本
echo.

:: 检查Python是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到Python。请先安装Python并确保已添加到系统路径。
    echo 可以从 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)

:: 检查pip是否可用
python -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到pip。请确保Python安装正确。
    echo 尝试使用 'python -m ensurepip --default-pip' 安装pip
    pause
    exit /b 1
)

:: 安装核心依赖
echo.
echo 正在安装pandas和openpyxl...
python -m pip install --upgrade pip
python -m pip install pandas openpyxl

:: 验证安装
echo.
echo 验证安装...
python -c "import pandas as pd; import openpyxl; print(f'pandas版本: {pd.__version__}'); print(f'openpyxl版本: {openpyxl.__version__}')"

if %errorlevel% neq 0 (
    echo.
    echo 错误: 依赖项安装失败。
    echo 请检查错误信息并重试。
    pause
    exit /b 1
)

echo.
echo 所有依赖项已成功安装!
echo 您现在可以运行数据清洗工具了。
pause