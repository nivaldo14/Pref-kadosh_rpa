@echo off
setlocal

echo.
echo =========================================================
echo  Instalador de Dependencias Adicionais e Playwright
echo =========================================================
echo.
echo Este script ira instalar as dependencias Python faltantes
echo e os navegadores necessarios para o Playwright.
echo Este processo pode levar alguns minutos.
echo.

:confirm
set /p proceed="Deseja continuar com a instalacao? (S/N): "
if /i "%proceed%"=="s" goto install
if /i "%proceed%"=="n" goto cancel
echo Resposta invalida. Digite S para sim ou N para nao.
goto confirm

:install
echo.
echo Instalando dependencias Python (requirements.txt)...
echo Certifique-se de ter o pip instalado e acessivel no PATH.
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao instalar as dependencias Python.
    echo Verifique a saida acima e tente resolver o problema.
    pause
    goto end
)
echo Dependencias Python instaladas com sucesso.
echo.

echo Instalando navegadores Playwright...
echo Este processo baixara os binarios do Chromium.
python -m playwright install
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao instalar os navegadores Playwright.
    echo Verifique a saida acima e tente resolver o problema.
    pause
    goto end
)
echo Navegadores Playwright instalados com sucesso.
echo.

echo =========================================================
echo  Instalacao concluida com sucesso!
echo =========================================================
echo.
pause
goto end

:cancel
echo.
echo Instalacao cancelada pelo usuario.
echo.
pause

:end
endlocal