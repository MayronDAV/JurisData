@echo off
echo ================================================
echo Construindo JurisData Server com Hooks
echo ================================================

if exist "Server\bin" rmdir /s /q "Server\bin"
if exist "build" rmdir /s /q "build"

echo.
echo Configurando hooks...
python Scripts/SetupHooks.py
if errorlevel 1 (
    echo AVISO: Problemas na configuração dos hooks
)

echo.
echo Compilando com hooks...
python Scripts\Compiler.py --batch Server\batch_config.json ^
  --hookspath hooks ^
  --runtime-hook hooks/runtime-hook-playwright.py

if exist "Server\bin\JurisDataServer.exe" (
    echo.
    echo ================================================
    echo BUILD COMPLETO COM SUCESSO!
    echo.
    echo O executável inclui:
    echo - Navegadores Playwright embedded
    echo - Hooks para configuração automática
    echo - Runtime hook para extração de navegadores
    echo.
    echo Executavel: Server\bin\JurisDataServer.exe
    echo ================================================
    
    for %%F in ("Server\bin\JurisDataServer.exe") do (
        set size=%%~zF
        set /a sizeMB=!size! / 1048576
        echo Tamanho: !sizeMB! MB
    )
) else (
    echo.
    echo ERRO: Compilacao falhou!
)

pause