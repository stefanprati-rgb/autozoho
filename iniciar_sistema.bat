@echo off
chcp 65001 > nul
setlocal

echo =======================================================
echo          AUTOZOHO - INICIALIZADOR DO SISTEMA
echo =======================================================
echo.

:: 1. Verificar Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python 3.10+ e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Setup Virtual Environment
if not exist ".venv" (
    echo [SETUP] Criando ambiente virtual .venv...
    python -m venv .venv
    echo [SETUP] Ambiente criado com sucesso.
)

:: 3. Ativar e Atualizar
echo [SISTEMA] Verificando dependencias...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ERRO] Ambiente virtual nao encontrado ou corrompido em .venv\Scripts\activate.bat.
    echo Tente excluir a pasta .venv e rodar novamente.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
if %errorlevel% neq 0 echo [AVISO] Nao foi possivel atualizar o pip.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

:: 4. Iniciar Launcher
echo.
python launcher.py

:: 5. Fim
echo.
echo [SISTEMA] Encerrado.
pause
