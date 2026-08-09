# Resume Analyzer - Run Script
# Activates virtual environment and starts the FastAPI server

Write-Host "Starting Resume Analyzer..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
    Exit 1
}

Write-Host ""
Write-Host "Starting FastAPI server on http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Open your browser and navigate to the URL above" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run the app
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
