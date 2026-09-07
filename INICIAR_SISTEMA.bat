@echo off
title Sistema de Tesoreria - Todo Electrico Valencia
echo ======================================================
echo    TODO ELECTRICO VALENCIA, C.A.
echo    Sistema de Tesoreria, Gastos y Flujo de Caja
echo ======================================================
echo Abriendo navegador en http://localhost:8000 ...
start http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
