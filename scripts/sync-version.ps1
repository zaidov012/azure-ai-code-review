#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Synchronize versions across extension files and rebuild VSIX package.

.DESCRIPTION
    This script:
    1. Extracts the version from vss-extension.json
    2. Updates package.json with the new version
    3. Updates task.json with the new version (splits into Major.Minor.Patch)
    4. Removes old VSIX files from the dist directory
    5. Builds a new VSIX package with the updated version

.EXAMPLE
    .\sync-version.ps1
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ROOT_DIR = $PSScriptRoot | Split-Path -Parent
$TASK_DIR = Join-Path $ROOT_DIR "task"
$DIST_DIR = Join-Path $ROOT_DIR "dist"
$VSS_EXTENSION_FILE = Join-Path $ROOT_DIR "vss-extension.json"
$PACKAGE_JSON_FILE = Join-Path $TASK_DIR "package.json"
$TASK_JSON_FILE = Join-Path $TASK_DIR "task.json"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Version Synchronization Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Extract version from vss-extension.json
Write-Host "📋 Step 1: Reading version from vss-extension.json..." -ForegroundColor Yellow

if (-not (Test-Path $VSS_EXTENSION_FILE)) {
    Write-Host "  ✗ vss-extension.json not found at $VSS_EXTENSION_FILE" -ForegroundColor Red
    exit 1
}

try {
    $vssContent = Get-Content $VSS_EXTENSION_FILE -Raw | ConvertFrom-Json
    $version = $vssContent.version
    Write-Host "  ✓ Found version: $version" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Failed to parse vss-extension.json: $_" -ForegroundColor Red
    exit 1
}

# Validate version format (semver)
if ($version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Host "  ✗ Invalid version format: $version (expected X.Y.Z)" -ForegroundColor Red
    exit 1
}

$versionParts = $version.Split('.')
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]
$patch = [int]$versionParts[2]

Write-Host "  Major: $major, Minor: $minor, Patch: $patch" -ForegroundColor Gray
Write-Host ""

# Step 2: Update package.json
Write-Host "📝 Step 2: Updating package.json..." -ForegroundColor Yellow

if (-not (Test-Path $PACKAGE_JSON_FILE)) {
    Write-Host "  ✗ package.json not found at $PACKAGE_JSON_FILE" -ForegroundColor Red
    exit 1
}

try {
    $packageContent = Get-Content $PACKAGE_JSON_FILE -Raw | ConvertFrom-Json
    $oldVersion = $packageContent.version
    $packageContent.version = $version
    $packageContent | ConvertTo-Json -Depth 10 | Set-Content $PACKAGE_JSON_FILE
    Write-Host "  ✓ Updated from $oldVersion to $version" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Failed to update package.json: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Update task.json
Write-Host "📝 Step 3: Updating task.json..." -ForegroundColor Yellow

if (-not (Test-Path $TASK_JSON_FILE)) {
    Write-Host "  ✗ task.json not found at $TASK_JSON_FILE" -ForegroundColor Red
    exit 1
}

try {
    $taskContent = Get-Content $TASK_JSON_FILE -Raw | ConvertFrom-Json
    $oldTaskVersion = "$($taskContent.version.Major).$($taskContent.version.Minor).$($taskContent.version.Patch)"
    
    $taskContent.version.Major = $major
    $taskContent.version.Minor = $minor
    $taskContent.version.Patch = $patch
    
    $taskContent | ConvertTo-Json -Depth 20 | Set-Content $TASK_JSON_FILE
    Write-Host "  ✓ Updated from $oldTaskVersion to $version" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Failed to update task.json: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Remove old VSIX files
Write-Host "🗑️  Step 4: Removing old VSIX files..." -ForegroundColor Yellow

if (Test-Path $DIST_DIR) {
    $vsixFiles = Get-ChildItem -Path $DIST_DIR -Filter "*.vsix" -ErrorAction SilentlyContinue
    
    if ($vsixFiles) {
        $vsixCount = @($vsixFiles).Count
        Write-Host "  Found $vsixCount VSIX file(s)" -ForegroundColor Gray
        
        foreach ($file in $vsixFiles) {
            try {
                Remove-Item $file.FullName -Force
                Write-Host "  ✓ Deleted: $($file.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "  ✗ Failed to delete $($file.Name): $_" -ForegroundColor Red
                if (-not $Force) {
                    exit 1
                }
            }
        }
    }
    else {
        Write-Host "  ℹ No VSIX files found" -ForegroundColor Gray
    }
}
else {
    Write-Host "  ℹ dist directory not found" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Build new VSIX
Write-Host "📦 Step 5: Building new VSIX package..." -ForegroundColor Yellow
Write-Host ""

$buildScript = Join-Path $PSScriptRoot "build.ps1"

if (-not (Test-Path $buildScript)) {
    Write-Host "  ✗ build.ps1 not found at $buildScript" -ForegroundColor Red
    exit 1
}

try {
    & $buildScript -Package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Build failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
catch {
    Write-Host "  ✗ Failed to run build.ps1: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Version synchronization completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Version: $version" -ForegroundColor White
Write-Host "  Package: $PACKAGE_JSON_FILE" -ForegroundColor White
Write-Host "  Task: $TASK_JSON_FILE" -ForegroundColor White
Write-Host "  VSIX: $DIST_DIR" -ForegroundColor White
Write-Host ""
