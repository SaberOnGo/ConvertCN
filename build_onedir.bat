@echo off
chcp 65001 >nul
REM ================================================
REM ConvertCN 一键打包（文件夹版）
REM 生成 dist\ConvertCN\ConvertCN.exe，误报率更低
REM ================================================

echo [1/3] 安装依赖...
pip install -r requirements.txt pyinstaller

echo [2/3] 开始打包（文件夹模式）...
pyinstaller --onedir --windowed ^
  --name ConvertCN ^
  --collect-data opencc ^
  --collect-submodules chardet ^
  encoding_gui_4.py

echo [3/3] 打包完成！
echo 可执行文件位于 dist\ConvertCN\ConvertCN.exe
pause
