# AdSense API Backend Setup Script for PowerShell
# Detects Python installation and sets up the environment

Write-Host "AdSense API Backend Setup Script" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Function to test Python command
function Test-PythonCommand {
    param($cmd)
    try {
        & $cmd --version 2>$null | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Find Python executable
$pythonCmd = $null
$pythonCommands = @("python", "python3", "py")

Write-Host "Checking Python installation..." -ForegroundColor Yellow

foreach ($cmd in $pythonCommands) {
    if (Test-PythonCommand $cmd) {
        $pythonCmd = $cmd
        break
    }
}

if ($null -eq $pythonCmd) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org or Microsoft Store" -ForegroundColor Red
    Write-Host "Then add it to your PATH environment variable." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Python found: $pythonCmd" -ForegroundColor Green
& $pythonCmd --version

Write-Host ""
Write-Host "Installing required packages..." -ForegroundColor Yellow

try {
    & $pythonCmd -m pip install --upgrade pip
    & $pythonCmd -m pip install -r requirements.txt
    
    if ($LASTEXITCODE -ne 0) {
        throw "Package installation failed"
    }
    
    Write-Host ""
    Write-Host "Setup completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run the server with:" -ForegroundColor Cyan
    Write-Host "  $pythonCmd start_server.py --mode dev" -ForegroundColor White
    Write-Host ""
    Write-Host "Or install and run in one command:" -ForegroundColor Cyan
    Write-Host "  $pythonCmd start_server.py --install --mode dev" -ForegroundColor White
    Write-Host ""
    Write-Host "Available modes:" -ForegroundColor Cyan
    Write-Host "  --mode dev     : Development server with auto-reload" -ForegroundColor White
    Write-Host "  --mode prod    : Production server with Gunicorn" -ForegroundColor White
    Write-Host "  --mode unicorn : Unicorn-compatible configuration" -ForegroundColor White
    Write-Host ""
}
catch {
    Write-Host "ERROR: Failed to install packages" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Read-Host "Press Enter to continue"