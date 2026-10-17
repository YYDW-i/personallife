param(
    [string]$Python = ".venv-desktop\Scripts\python.exe",
    [ValidatePattern('^LocalLife(?:-[A-Za-z0-9_.-]+)?$')][string]$ReleaseName = "LocalLife",
    [switch]$ReuseAnalysis
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) {
    throw "请先使用 Python 3.12 创建 .venv-desktop 并安装 requirements.txt、requirements-desktop.txt。"
}
$outputDir = Join-Path $PSScriptRoot "dist\$ReleaseName"
$outputExe = Join-Path $outputDir "LocalLife.exe"
$running = @(Get-Process LocalLife -ErrorAction SilentlyContinue)
if ($running | Where-Object { $_.Path -eq $outputExe }) {
    if ($ReleaseName -eq "LocalLife") {
        $ReleaseName = "LocalLife-2.0.1"
        $outputDir = Join-Path $PSScriptRoot "dist\$ReleaseName"
        $outputExe = Join-Path $outputDir "LocalLife.exe"
        Write-Host "旧版仍在运行，改为构建独立目录：$outputDir"
    }
    if ($running | Where-Object { $_.Path -eq $outputExe }) {
        throw "目标发行目录的程序仍在运行。请先关闭它，或使用 -ReleaseName LocalLife-自定义名称。"
    }
}
$env:LOCALLIFE_RELEASE_NAME = $ReleaseName
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot ".runtime-pyinstaller-cache"
$env:MPLCONFIGDIR = Join-Path $env:PYINSTALLER_CONFIG_DIR "matplotlib"
$installerArgs = @("--noconfirm")
if (-not $ReuseAnalysis) { $installerArgs += "--clean" }
& $Python -m PyInstaller @installerArgs LocalLife.spec
if ($LASTEXITCODE -ne 0) { throw "EXE 构建失败" }
& $Python scripts\verify_package_sources.py $outputExe
if ($LASTEXITCODE -ne 0) { throw "发行包源码一致性检查失败，请重新构建。" }
Copy-Item -LiteralPath README.md,CHANGELOG.md,VERIFICATION.md,THIRD_PARTY_NOTICES.md,requirements-lock.txt,LICENSE -Destination $outputDir
New-Item -ItemType Directory -Path "$outputDir\images","$outputDir\docs\screenshots","$outputDir\static\images" -Force | Out-Null
Copy-Item -LiteralPath images\dashboard-v2.jpg -Destination "$outputDir\images"
Copy-Item -Path docs\screenshots\*.jpg -Destination "$outputDir\docs\screenshots"
Copy-Item -LiteralPath static\images\logo.svg -Destination "$outputDir\static\images"
Write-Host "构建完成：$outputExe；分发时请复制整个 $ReleaseName 目录。"
