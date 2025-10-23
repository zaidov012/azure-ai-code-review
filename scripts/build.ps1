#!/usr/bin/env pwsh
# Build and package Azure DevOps extension

param(
    [switch]$Clean,
    [switch]$Build,
    [switch]$Package,
    [switch]$All
)

$ErrorActionPreference = "Stop"

$ROOT_DIR = $PSScriptRoot | Split-Path -Parent
$TASK_DIR = Join-Path $ROOT_DIR "task"
$DIST_DIR = Join-Path $TASK_DIR "dist"
$OUTPUT_DIR = Join-Path $ROOT_DIR "dist"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  AI Code Review Extension Build  " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Clean
if ($Clean -or $All) {
    Write-Host "🧹 Cleaning..." -ForegroundColor Yellow
    
    if (Test-Path $DIST_DIR) {
        Remove-Item -Path $DIST_DIR -Recurse -Force
        Write-Host "  ✓ Removed task/dist" -ForegroundColor Green
    }
    
    if (Test-Path $OUTPUT_DIR) {
        Remove-Item -Path $OUTPUT_DIR -Recurse -Force
        Write-Host "  ✓ Removed dist" -ForegroundColor Green
    }
    
    if (Test-Path (Join-Path $TASK_DIR "node_modules")) {
        Remove-Item -Path (Join-Path $TASK_DIR "node_modules") -Recurse -Force
        Write-Host "  ✓ Removed node_modules" -ForegroundColor Green
    }
    
    Write-Host ""
}

# Build
if ($Build -or $All) {
    Write-Host "🔨 Building..." -ForegroundColor Yellow
    
    # Check Node.js
    try {
        $nodeVersion = node --version
        Write-Host "  ✓ Node.js: $nodeVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Node.js not found. Please install Node.js 16+." -ForegroundColor Red
        exit 1
    }
    
    # Check Python
    try {
        $pythonVersion = python --version
        Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Python not found. Please install Python 3.8+." -ForegroundColor Red
        exit 1
    }
    
    # Install Node dependencies
    Write-Host "  📦 Installing Node.js dependencies..." -ForegroundColor Cyan
    Push-Location $TASK_DIR
    try {
        npm install | Out-Null
        Write-Host "  ✓ Node.js dependencies installed" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
    
    # Install Python dependencies
    Write-Host "  📦 Installing Python dependencies..." -ForegroundColor Cyan
    Push-Location $ROOT_DIR
    try {
        python -m pip install -r requirements.txt --quiet
        Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
    
    # Build TypeScript
    Write-Host "  🔧 Compiling TypeScript..." -ForegroundColor Cyan
    Push-Location $TASK_DIR
    try {
        npm run build
        Write-Host "  ✓ TypeScript compiled" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
    
    # Run tests
    Write-Host "  🧪 Running tests..." -ForegroundColor Cyan
    Push-Location $ROOT_DIR
    try {
        python -m pytest tests/ -v --tb=short
        Write-Host "  ✓ Tests passed" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ Some tests failed" -ForegroundColor Yellow
    }
    finally {
        Pop-Location
    }
    
    Write-Host ""
}

# Package
if ($Package -or $All) {
    Write-Host "📦 Packaging extension..." -ForegroundColor Yellow
    
    # Check tfx-cli
    try {
        $tfxVersion = tfx version
        Write-Host "  ✓ tfx-cli: $tfxVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ tfx-cli not found. Installing..." -ForegroundColor Yellow
        npm install -g tfx-cli
    }
    
    # Create output directory
    if (-not (Test-Path $OUTPUT_DIR)) {
        New-Item -Path $OUTPUT_DIR -ItemType Directory | Out-Null
    }
    
    # Create extension package
    Write-Host "  📦 Creating VSIX package..." -ForegroundColor Cyan
    Push-Location $ROOT_DIR
    try {
        tfx extension create --manifest-globs vss-extension.json --output-path $OUTPUT_DIR
        
        $vsixFile = Get-ChildItem -Path $OUTPUT_DIR -Filter "*.vsix" | Select-Object -First 1
        if ($vsixFile) {
            Write-Host "  ✓ Package created: $($vsixFile.Name)" -ForegroundColor Green
            Write-Host "  📍 Location: $($vsixFile.FullName)" -ForegroundColor Cyan
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host ""
}

# Summary
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "✅ Build completed successfully!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

if ($Package -or $All) {
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test the extension locally" -ForegroundColor White
    Write-Host "  2. Publish to marketplace: " -NoNewline -ForegroundColor White
    Write-Host "tfx extension publish --manifest-globs vss-extension.json --share-with your-org" -ForegroundColor Cyan
    Write-Host ""
}
