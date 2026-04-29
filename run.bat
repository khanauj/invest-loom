@echo off
echo =======================================================
echo Starting InvestAI Platform
echo =======================================================
echo.
echo Starting FastAPI Backend...
start "InvestAI Backend" cmd /k "python main.py api"
echo Starting Next.js Frontend...
start "InvestAI Frontend" cmd /k "cd frontend && npm run dev"
echo.
echo Both services are starting in new windows!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo =======================================================
