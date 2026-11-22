# src/auth.py
"""Autenticação via Google Sheets (Apps Script).
Retry com backoff (1s, 2s), timeout 15s, erros com timestamp [HH:MM:SS] (BR_TZ).
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import streamlit as st

# Brasil timezone (UTC-3) para timestamps user-facing
BR_TZ = timezone(timedelta(hours=-3))


def _now() -> str:
    """Timestamp no fuso do Brasil (HH:MM:SS)."""
    return datetime.now(BR_TZ).strftime("%H:%M:%S")


def _msg(text: str) -> str:
    """Prefixa mensagem com timestamp [HH:MM:SS]."""
    return f"[{_now()}] {text}"


def _get_apps_script_url() -> str:
    """Obtém URL do Apps Script do secrets (lazy)."""
    try:
        return st.secrets.get("APPS_SCRIPT_URL", "")
    except Exception:
        return ""


def _resilient_post(url: str, payload: dict, timeout: int = 15, max_retries: int = 2) -> dict:
    """POST com retry (1s, 2s), timeout, erros timestampados."""
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if attempt == max_retries:
                return {"ok": False, "erro": _msg(f"Erro HTTP {e.code} ao consultar planilha")}
        except urllib.error.URLError as e:
            if attempt == max_retries:
                return {"ok": False, "erro": _msg(f"Erro de conexão: {e.reason}")}
        except json.JSONDecodeError:
            if attempt == max_retries:
                return {"ok": False, "erro": _msg("Resposta inválida do servidor")}
        except Exception as e:
            if attempt == max_retries:
                return {"ok": False, "erro": _msg(f"Erro inesperado: {e}")}

        if attempt < max_retries:
            time.sleep((1, 2)[attempt])

    return {"ok": False, "erro": _msg("Falha após múltiplas tentativas")}


def verificar_acesso_sheets(email: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Verifica se e-mail tem acesso válido na planilha.

    Returns:
        (ok, expiracao_str, erro_str)
    """
    APPS_SCRIPT_URL = _get_apps_script_url()
    if not APPS_SCRIPT_URL:
        return False, None, _msg("APPS_SCRIPT_URL não configurado no secrets.toml")

    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, None, _msg("E-mail inválido")

    payload = {"action": "verificar", "email": email}

    response = _resilient_post(APPS_SCRIPT_URL, payload, timeout=15, max_retries=2)

    if response.get("ok"):
        exp = response.get("expiracao", "")
        return True, exp, None
    else:
        return False, None, response.get("erro", _msg("E-mail não autorizado"))