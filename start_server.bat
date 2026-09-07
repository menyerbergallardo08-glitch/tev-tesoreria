@echo off
title Todo Electrico Valencia - Sistema de Tesoreria
color 0A
echo =====================================================================
echo           TODO ELECTRICO VALENCIA, C.A.
echo       Sistema de Tesoreria, Gastos y Flujo de Caja
echo =====================================================================
echo.
echo Iniciando servidor en http://localhost:8000 ...
echo Puede acceder desde su navegador o en la red local.
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
