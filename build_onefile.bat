@echo off
chcp 65001 >nul
REM ================================================
REM ConvertCN 一键打包（单文件版）
REM 生成 ConvertCN.exe，方便测试和分享
REM ================================================

echo [1/3] 安装依赖...
pip install -r requirements.txt pyinstaller

echo [2/3] 开始打包（单文件模式）...
pyinstaller --onefile --windowed ^
  --name ConvertCN ^
  --collect-data opencc ^
  --collect-submodules chardet ^
  encoding_gui_4.py

echo [3/3] 打包完成！
echo 可执行文件位于 dist\ConvertCN.exe
pause
