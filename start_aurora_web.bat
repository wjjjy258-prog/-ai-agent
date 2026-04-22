@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title Aurora Agent Web Launcher

echo [1/8] Checking Python...
py -3 --version >nul 2>nul
if not errorlevel 1 (
  set "PY_BOOT=py -3"
) else (
  python --version >nul 2>nul
  if not errorlevel 1 (
    set "PY_BOOT=python"
  ) else (
    echo [ERROR] Python 3.10+ is required but not found.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [2/8] Creating virtual environment...
  py -3 -m venv .venv >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv >nul 2>nul
    if errorlevel 1 (
      echo [ERROR] Failed to create .venv
      pause
      exit /b 1
    )
  )
) else (
  echo [2/8] Virtual environment exists.
)

set "PYTHON_BIN=.venv\Scripts\python.exe"
if not exist "%PYTHON_BIN%" (
  echo [ERROR] Python in .venv not found.
  pause
  exit /b 1
)

echo [3/8] Installing dependencies...
"%PYTHON_BIN%" -m pip install --upgrade pip >nul 2>nul
"%PYTHON_BIN%" -m pip install -e .
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)

echo [4/8] Applying runtime defaults...
if "%AURORA_LLM_PROVIDER%"=="" set "AURORA_LLM_PROVIDER=ollama"
if "%AURORA_ENABLE_LLM_CHAT%"=="" set "AURORA_ENABLE_LLM_CHAT=true"
if "%AURORA_OLLAMA_TIMEOUT_SEC%"=="" set "AURORA_OLLAMA_TIMEOUT_SEC=180"
if "%AURORA_OPENAI_TIMEOUT_SEC%"=="" set "AURORA_OPENAI_TIMEOUT_SEC=120"
if "%AURORA_LLM_HISTORY_LIMIT%"=="" set "AURORA_LLM_HISTORY_LIMIT=20"
if "%AURORA_INTENT_CONFIDENCE_THRESHOLD%"=="" set "AURORA_INTENT_CONFIDENCE_THRESHOLD=0.72"
if "%AURORA_OLLAMA_MODEL%"=="" set "AURORA_OLLAMA_MODEL=qwen3.5:4b"
if "%AURORA_OPENAI_MODEL%"=="" set "AURORA_OPENAI_MODEL=qwen-plus"
if "%AURORA_OPENAI_BASE_URL%"=="" set "AURORA_OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
if "%AURORA_AUTO_START_OLLAMA%"=="" set "AURORA_AUTO_START_OLLAMA=1"
if "%AURORA_WEB_HOST%"=="" set "AURORA_WEB_HOST=127.0.0.1"
if "%AURORA_WEB_PORT%"=="" set "AURORA_WEB_PORT=8000"
if "%AURORA_OLLAMA_BASE_URL%"=="" set "AURORA_OLLAMA_BASE_URL=http://127.0.0.1:11434"
if not "%AURORA_OLLAMA_MODELS_DIR%"=="" set "OLLAMA_MODELS=%AURORA_OLLAMA_MODELS_DIR%"
for /f "usebackq delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$hostRaw=(''+$env:AURORA_WEB_HOST).Trim(); if(-not $hostRaw){$hostRaw='127.0.0.1'}; Write-Output $hostRaw"`) do set "AURORA_WEB_HOST=%%H"
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$raw=(''+$env:AURORA_WEB_PORT).Trim(); $value=8000; $tmp=0; if([int]::TryParse($raw, [ref]$tmp)){ $value=$tmp }; if($value -lt 1000 -or $value -gt 65535){ $value=8000 }; Write-Output $value"`) do set "AURORA_WEB_PORT=%%P"

echo [5/8] Cleaning old Aurora instances...
if /I "%AURORA_KEEP_RUNNING%"=="1" (
  echo      Skip cleanup because AURORA_KEEP_RUNNING=1
) else (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$targets=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'ai_agent\.web\.app|aurora-web|aurora_agent' }; foreach($t in $targets){ try { Stop-Process -Id $t.ProcessId -Force -ErrorAction Stop; Write-Output $t.ProcessId } catch {} }"`) do (
    echo      Stopped old process PID %%P
  )
)

echo [6/8] Resolving available port...
set "FREE_PORT="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$bindHost=$env:AURORA_WEB_HOST; $start=[int]$env:AURORA_WEB_PORT; function Test-Port([string]$h,[int]$p){$listener=$null; try { $ip=[System.Net.IPAddress]::Loopback; [void][System.Net.IPAddress]::TryParse($h, [ref]$ip); $listener=[System.Net.Sockets.TcpListener]::new($ip,$p); $listener.Start(); return $true } catch { return $false } finally { if ($listener) { $listener.Stop() } }}; if (Test-Port $bindHost $start) { Write-Output $start; exit 0 }; for($i=1; $i -le 40; $i++){ $p=$start+$i; if($p -gt 65535){break}; if(Test-Port $bindHost $p){ Write-Output $p; exit 0 } }; exit 1"`) do set "FREE_PORT=%%P"
if "%FREE_PORT%"=="" (
  echo [ERROR] No free port found near %AURORA_WEB_PORT%.
  pause
  exit /b 1
)
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$fallback=8000; $tmp=0; if([int]::TryParse((''+$env:AURORA_WEB_PORT).Trim(), [ref]$tmp)){ $fallback=$tmp }; $raw=(''+$env:FREE_PORT).Trim(); $value=$fallback; $parsed=0; if([int]::TryParse($raw, [ref]$parsed)){ $value=$parsed }; if($value -lt 1000 -or $value -gt 65535){ $value=$fallback }; Write-Output $value"`) do set "FREE_PORT=%%P"
if not "%FREE_PORT%"=="%AURORA_WEB_PORT%" (
  echo      [WARN] Port %AURORA_WEB_PORT% is occupied, switching to %FREE_PORT%.
  set "AURORA_WEB_PORT=%FREE_PORT%"
)
set "APP_URL=http://%AURORA_WEB_HOST%:%AURORA_WEB_PORT%"

echo [7/8] Checking model service...
if /I "%AURORA_LLM_PROVIDER%"=="ollama" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$u=$env:AURORA_OLLAMA_BASE_URL + '/api/tags';" ^
    "try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 4; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
  if errorlevel 1 (
    echo      [WARN] Ollama not reachable at %AURORA_OLLAMA_BASE_URL%
    if /I "%AURORA_AUTO_START_OLLAMA%"=="1" (
      echo      Trying to auto-start Ollama...
      powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$base=$env:AURORA_OLLAMA_BASE_URL.TrimEnd('/');" ^
        "function Test-Ollama { param([string]$u) try { $r=Invoke-WebRequest -Uri ($u + '/api/tags') -UseBasicParsing -TimeoutSec 3; return ($r.StatusCode -eq 200) } catch { return $false } }" ^
        "$started=$false;" ^
        "if (-not (Test-Ollama $base)) {" ^
        "  $cmd=Get-Command ollama -ErrorAction SilentlyContinue;" ^
        "  if ($cmd) { try { Start-Process -FilePath $cmd.Source -ArgumentList 'serve' -WindowStyle Minimized; $started=$true } catch {} }" ^
        "}" ^
        "if (-not (Test-Ollama $base)) {" ^
        "  $cand=@();" ^
        "  if ($env:LOCALAPPDATA) { $cand += (Join-Path $env:LOCALAPPDATA 'Programs\\Ollama\\ollama.exe'); $cand += (Join-Path $env:LOCALAPPDATA 'Programs\\Ollama\\Ollama.exe') }" ^
        "  foreach($p in $cand){ if(Test-Path $p){ try { Start-Process -FilePath $p -WindowStyle Minimized; $started=$true; break } catch {} } }" ^
        "}" ^
        "for($i=0; $i -lt 14; $i++){ if(Test-Ollama $base){ exit 0 }; Start-Sleep -Seconds 1 }" ^
        "exit 1"
      if errorlevel 1 (
        echo      [WARN] Auto-start failed. UI will start anyway.
      ) else (
        echo      Ollama started and reachable at %AURORA_OLLAMA_BASE_URL%
      )
    ) else (
      echo      UI will start anyway. LLM replies may fail until Ollama is running.
    )
  ) else (
    echo      Ollama reachable at %AURORA_OLLAMA_BASE_URL%
  )
) else (
  echo      Provider is %AURORA_LLM_PROVIDER%; skip local Ollama check.
)

echo [8/8] Launching web...
set "CACHE_BUSTER=%RANDOM%%RANDOM%"
start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "$appUrl=$env:APP_URL + '/?v=' + $env:CACHE_BUSTER; $healthUrl=$env:APP_URL + '/api/health'; for($i=0; $i -lt 60; $i++){ try { $r=Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ Start-Process $appUrl; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; Start-Process $appUrl" >nul 2>nul

echo.
echo ------------------------------------------------------------
echo Aurora is launching at: %APP_URL%
echo Press Ctrl+C to stop server.
echo ------------------------------------------------------------
echo.

"%PYTHON_BIN%" -m ai_agent.web.app
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Server exited with code %EXIT_CODE%.
) else (
  echo Server stopped.
)
pause
exit /b %EXIT_CODE%
