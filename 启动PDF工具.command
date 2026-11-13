#!/bin/bash
# 双击此文件后，在本机启动网页版 PDF 页面统一工具。
set -e
cd "$(dirname "$0")"

printf '\n=======================================\n'
printf ' PDF 页面统一工具 · Mac 免费本地版\n'
printf '=======================================\n\n'
original_python="$HOME/Downloads/PDF页面统一小工具/.venv/bin/python"
if [ -x "$original_python" ] && "$original_python" -c 'import fitz' >/dev/null 2>&1; then
  exec "$original_python" pdf_tool.py
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo '没有找到 Python 3。请先到 https://www.python.org/downloads/ 安装 Python 3，然后重新双击启动。'
  echo '按回车键关闭...'
  read -r
  exit 1
fi

if [ ! -d '.venv' ]; then
  echo '首次运行：正在创建本地 Python 环境...'
  python3 -m venv .venv || { echo '创建失败，请确认安装了完整的 Python 3。'; read -r; exit 1; }
fi

if ! .venv/bin/python -c 'import fitz' >/dev/null 2>&1; then
  echo '首次运行：正在安装免费的 PDF 处理组件（需要网络，之后可离线使用）...'
  .venv/bin/python -m pip install --disable-pip-version-check --quiet 'pymupdf>=1.24' || {
    echo '安装失败，请检查网络连接后重试。'
    echo '按回车键关闭...'
    read -r
    exit 1
  }
fi

echo '即将在浏览器打开工具。如果未自动打开，请复制终端显示的本地网址。'
exec .venv/bin/python pdf_tool.py
