from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import HTTPException


def is_ollama_reachable(base_url: str, timeout_sec: int = 3) -> bool:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return False
    url = f"{cleaned}/api/tags"
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=max(1, timeout_sec)) as response:
            return 200 <= int(getattr(response, "status", 0)) < 300
    except Exception:
        return False


def _extract_semver_like(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    match = re.search(r"(\d+\.\d+\.\d+(?:[-+._a-zA-Z0-9]*)?)", raw)
    if match:
        return match.group(1)
    return raw


def _query_ollama_service_version(base_url: str, timeout_sec: int = 3) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    req = urllib.request.Request(url=f"{cleaned}/api/version", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=max(1, timeout_sec)) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return ""
    version = str(payload.get("version", "")).strip()
    if version:
        return version
    return _extract_semver_like(str(payload))


def _run_ollama_version_command(command: list[str], source: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return {"available": False, "version": "", "raw": "", "source": source}

    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode != 0 and not output:
        return {"available": False, "version": "", "raw": "", "source": source}
    return {
        "available": True,
        "version": _extract_semver_like(output),
        "raw": output,
        "source": source,
    }


def _query_ollama_cli_version() -> dict[str, Any]:
    from_path = _run_ollama_version_command(["ollama", "--version"], "PATH")
    if from_path["available"]:
        return from_path

    if os.name == "nt":
        localapp = os.getenv("LOCALAPPDATA", "").strip()
        if localapp:
            candidates = [
                Path(localapp) / "Programs" / "Ollama" / "ollama.exe",
                Path(localapp) / "Programs" / "Ollama" / "Ollama.exe",
            ]
            for exe in candidates:
                if exe.exists():
                    result = _run_ollama_version_command([str(exe), "--version"], str(exe))
                    if result["available"]:
                        return result
    return from_path


def query_ollama_versions(base_url: str) -> dict[str, Any]:
    service_reachable = is_ollama_reachable(base_url, timeout_sec=2)
    service_version = _query_ollama_service_version(base_url, timeout_sec=3) if service_reachable else ""
    cli = _query_ollama_cli_version()
    cli_available = bool(cli.get("available"))

    if service_reachable and service_version:
        detail = f"Ollama 服务在线，版本 {service_version}。"
    elif service_reachable:
        detail = "Ollama 服务在线，但未返回明确版本号。"
    elif cli_available:
        detail = "已检测到本机 Ollama 程序，但服务当前未连接。"
    else:
        detail = "未检测到本机 Ollama 程序，且服务不可连接。"

    return {
        "base_url": (base_url or "").strip() or "http://127.0.0.1:11434",
        "service_reachable": service_reachable,
        "service_version": service_version,
        "cli_available": cli_available,
        "cli_version": str(cli.get("version", "")).strip(),
        "cli_raw": str(cli.get("raw", "")).strip(),
        "cli_source": str(cli.get("source", "")).strip(),
        "detail": detail,
    }


def start_ollama_service(base_url: str) -> dict[str, Any]:
    if is_ollama_reachable(base_url, timeout_sec=2):
        return {
            "started": False,
            "reachable": True,
            "detail": "Ollama 已在运行。",
            "base_url": base_url,
        }

    attempts: list[str] = []

    def _launch_with_command(command: list[str], label: str) -> bool:
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            attempts.append(f"launch:{label}")
            return True
        except Exception as exc:  # pragma: no cover - platform-specific
            attempts.append(f"fail:{label}:{exc}")
            return False

    started = False
    if os.name == "nt":
        started = _launch_with_command(["ollama", "serve"], "ollama serve")
        if not started:
            localapp = os.getenv("LOCALAPPDATA", "").strip()
            candidates = [
                Path(localapp) / "Programs" / "Ollama" / "ollama.exe",
                Path(localapp) / "Programs" / "Ollama" / "Ollama.exe",
            ]
            for exe in candidates:
                if not exe.exists():
                    continue
                if _launch_with_command([str(exe)], exe.name):
                    started = True
                    break
    else:
        started = _launch_with_command(["ollama", "serve"], "ollama serve")

    reachable = False
    for _ in range(14):
        if is_ollama_reachable(base_url, timeout_sec=2):
            reachable = True
            break
        time.sleep(1)

    if reachable:
        return {
            "started": started,
            "reachable": True,
            "detail": "Ollama 已就绪，可以开始聊天。",
            "base_url": base_url,
            "attempts": attempts,
        }
    return {
        "started": started,
        "reachable": False,
        "detail": "未能自动拉起 Ollama，请确认已安装并允许后台运行。",
        "base_url": base_url,
        "attempts": attempts,
    }


def pick_folder_via_native_dialog() -> str | None:
    if os.name != "nt":
        raise HTTPException(status_code=501, detail="当前仅支持 Windows 原生目录选择。")

    script = r"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '选择模型下载目录'
$dialog.ShowNewFolderButton = $true
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
  Write-Output $dialog.SelectedPath
}
"""
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"打开目录选择器失败：{exc}") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or "").strip() or f"powershell exit code={proc.returncode}"
        raise HTTPException(status_code=500, detail=f"目录选择器执行失败：{detail}")

    selected = (proc.stdout or "").strip()
    if not selected:
        return None
    return selected.splitlines()[-1].strip()
