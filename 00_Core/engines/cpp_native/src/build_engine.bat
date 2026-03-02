
@echo off
echo [HCB] Iniciando Protocolo de Compilacao...

:: 1. Tentar configurar o ambiente do VS 2022 Community (Caminho Padrao)
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
) else (
    echo [AVISO] vcvars64.bat nao encontrado no caminho padrao.
    echo [ACAO] Tentando compilar assumindo que o ambiente ja esta configurado...
)

:: 2. Compilar
cd /d "F:\HCB_STUDIO\00_Core\engines\cpp_native\src"
echo [COMPILADOR] Processando hcb_core.cpp...
cl.exe /LD hcb_core.cpp /Fe:"F:\HCB_STUDIO\00_Core\engines\cpp_native\bin\hcb_core.dll"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCESSO] DLL Gerada em: F:\HCB_STUDIO\00_Core\engines\cpp_native\bin\hcb_core.dll
    echo Pode executar o teste Python agora.
) else (
    echo.
    echo [FALHA] Nao foi possivel compilar.
    echo [SOLUCAO] Execute este .bat atraves do "Developer Command Prompt for VS".
)
pause
