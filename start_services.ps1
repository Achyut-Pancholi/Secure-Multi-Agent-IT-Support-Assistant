# Start Mock Services on port 8001 in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\myvenv\Scripts\Activate.ps1; uvicorn mock_services.main:app --port 8001"

# Start Main Backend API on port 8000 in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\myvenv\Scripts\Activate.ps1; python app/main.py"

Write-Host "Both Mock Services (8001) and Backend API (8000) have been launched in separate windows!" -ForegroundColor Green
Write-Host "You can now return to your Streamlit browser tab at http://localhost:8501 and retry your query." -ForegroundColor Cyan

