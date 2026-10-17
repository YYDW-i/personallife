param([string]$Python = ".venv-desktop\Scripts\python.exe")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot ".runtime-pyinstaller-cache"
$env:MPLCONFIGDIR = Join-Path $env:PYINSTALLER_CONFIG_DIR "matplotlib"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "请先使用 Python 3.12 创建 .venv-desktop 并安装 requirements.txt、requirements-desktop.txt。"
}
& $Python -m PyInstaller --noconfirm --clean LocalLife.spec
if ($LASTEXITCODE -ne 0) { throw "EXE 构建失败" }
& $Python scripts\verify_package_sources.py dist\LocalLife\LocalLife.exe
if ($LASTEXITCODE -ne 0) { throw "发行包源码一致性检查失败，请重新构建。" }
Copy-Item -LiteralPath README.md,CHANGELOG.md,VERIFICATION.md,THIRD_PARTY_NOTICES.md,requirements-lock.txt -Destination dist\LocalLife
New-Item -ItemType Directory -Path dist\LocalLife\images -Force | Out-Null
Copy-Item -LiteralPath images\dashboard-v2.jpg -Destination dist\LocalLife\images
Write-Host "构建完成：dist\LocalLife\LocalLife.exe；分发时请复制整个 LocalLife 目录。"
