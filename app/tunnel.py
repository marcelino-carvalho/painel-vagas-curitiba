"""
Gerenciador de Endereço Público para Publicação de Painéis e QR Code.

Garante que o endereço utilizado no QR Code NUNCA seja localhost, IP privado
(127.x, 192.168.x, 10.x, 172.16-31.x) ou caminho local de arquivo.

Ordem de prioridade do endereço público:
1. Variável de ambiente `PUBLIC_BASE_URL` (quando configurado em produção/hospedagem).
2. Domínio público detectado no cabeçalho HTTP (`X-Forwarded-Host` / `Host`), quando hospedado
   em nuvem (Render, Railway, Fly.io, Google Cloud Run, servidor institucional).
3. Túnel HTTPS público automático via Cloudflare Quick Tunnel (`cloudflared`), permitindo que
   qualquer celular na internet (4G/5G) acesse imediatamente os painéis publicados.
"""

import ipaddress
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARED_BIN = BASE_DIR / "bin" / ("cloudflared.exe" if os.name == "nt" else "cloudflared")

_tunnel_lock = threading.Lock()
_tunnel_proc: Optional[subprocess.Popen] = None
_tunnel_public_url: Optional[str] = None
_custom_public_base_url: Optional[str] = None


def is_local_or_private_host(host: str) -> bool:
    """Verifica se um host é localhost, loopback, nome sem domínio público ou endereço IP privado."""
    if not host:
        return True
    hostname = host.split(":")[0].strip().lower()
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", "testserver"):
        return True
    if "." not in hostname:
        return True
    if hostname.endswith(".local") or hostname.endswith(".internal") or hostname.endswith(".lan"):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified
    except ValueError:
        return False


def ensure_cloudflared_binary() -> Path:
    """Baixa o binário oficial do cloudflared caso ainda não exista."""
    if CLOUDFLARED_BIN.exists():
        return CLOUDFLARED_BIN
    CLOUDFLARED_BIN.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    else:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    urllib.request.urlretrieve(download_url, str(CLOUDFLARED_BIN))
    if os.name != "nt":
        os.chmod(str(CLOUDFLARED_BIN), 0o755)
    return CLOUDFLARED_BIN


def start_public_tunnel(local_port: int = 8000) -> Optional[str]:
    """
    Inicia um túnel HTTPS público via Cloudflare Quick Tunnel apontando para a porta local.
    Retorna a URL pública (ex.: https://xxxx.trycloudflare.com).
    """
    global _tunnel_proc, _tunnel_public_url
    with _tunnel_lock:
        if _tunnel_public_url and _tunnel_proc and _tunnel_proc.poll() is None:
            return _tunnel_public_url

        try:
            bin_path = ensure_cloudflared_binary()
            _tunnel_proc = subprocess.Popen(
                [str(bin_path), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{local_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            t0 = time.time()
            while time.time() - t0 < 20:
                if _tunnel_proc.stderr is None:
                    break
                line = _tunnel_proc.stderr.readline()
                if not line:
                    if _tunnel_proc.poll() is not None:
                        break
                    continue
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if match:
                    _tunnel_public_url = match.group(0).rstrip("/")
                    return _tunnel_public_url
        except Exception as exc:
            print(f"[AVISO] Falha ao iniciar túnel público cloudflared: {exc}")

        return _tunnel_public_url


def set_custom_public_base_url(url: Optional[str]) -> Optional[str]:
    """Permite configurar manualmente um domínio público base se desejado."""
    global _custom_public_base_url
    if not url or not url.strip():
        _custom_public_base_url = None
        return None
    cleaned = url.strip().rstrip("/")
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        cleaned = "https://" + cleaned
    host_part = re.sub(r"^https?://", "", cleaned).split("/")[0]
    if is_local_or_private_host(host_part):
        raise ValueError(
            "O endereço público não pode ser localhost nem endereço IP privado. "
            "Informe um domínio público acessível pela internet."
        )
    _custom_public_base_url = cleaned
    return _custom_public_base_url


def get_public_base_url(request_host: Optional[str] = None, request_scheme: str = "https", local_port: int = 8000) -> str:
    """
    Obtém a URL base pública garantidamente acessível pela internet.
    """
    # 1. URL customizada em memória
    if _custom_public_base_url:
        return _custom_public_base_url

    # 2. Variável de ambiente PUBLIC_BASE_URL
    env_url = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if env_url:
        host_part = re.sub(r"^https?://", "", env_url).split("/")[0]
        if not is_local_or_private_host(host_part):
            return env_url

    # 3. Se a requisição já veio por um domínio público (ex.: Render, Railway, TryCloudflare)
    if request_host and not is_local_or_private_host(request_host):
        scheme = "https" if "trycloudflare.com" in request_host or request_scheme == "https" else request_scheme
        return f"{scheme}://{request_host}".rstrip("/")

    # 4. Túnel público automático cloudflared
    tunnel_url = start_public_tunnel(local_port=local_port)
    if tunnel_url:
        return tunnel_url

    raise RuntimeError(
        "Não foi possível obter um endereço público acessível pela internet. "
        "Verifique a conexão com a internet ou defina a variável PUBLIC_BASE_URL."
    )


def get_current_tunnel_status() -> dict:
    env_url = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    active_url = _custom_public_base_url or env_url or _tunnel_public_url
    return {
        "public_base_url": active_url,
        "tunnel_running": bool(_tunnel_proc and _tunnel_proc.poll() is None),
        "mode": "custom" if _custom_public_base_url else ("env" if env_url else "cloudflared_tunnel"),
    }
