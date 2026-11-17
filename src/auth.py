# src/auth.py
"""Autenticação via Google Sheets (Apps Script) com resiliência, retry e timestamp."""
import urllib.request
import urllib.error
import json
import time
from datetime import datetime
import streamlit as st


def _now() -> str:
    """Retorna timestamp atual formatado HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def _msg(msg: str) -> str:
    """Prefixa mensagem com timestamp."""
    return f"[{_now()}] {msg}"


def _get_apps_script_url() -> str:
    """Obtém URL do Apps Script do secrets (lazy)."""
    try:
        return st.secrets.get("APPS_SCRIPT_URL", "")
    except Exception:
        return ""


def verificar_acesso_sheets(email: str) -> tuple[bool, str | None, str | None]:
    """Verifica se e-mail tem acesso válido na planilha com retry e timeout.
    
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
    data_bytes = json.dumps(payload).encode("utf-8")
    
    max_retries = 2
    backoff_delays = [1, 2]
    
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                APPS_SCRIPT_URL,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            if data.get("ok"):
                exp = data.get("expiracao", "")
                return True, exp, None
            else:
                return False, None, _msg(data.get("erro", "E-mail não autorizado"))
        
        except urllib.error.HTTPError as e:
            if attempt == max_retries:
                return False, None, _msg(f"Erro HTTP {e.code} ao consultar planilha")
        except urllib.error.URLError as e:
            if attempt == max_retries:
                return False, None, _msg(f"Erro de conexão: {e.reason}")
        except json.JSONDecodeError:
            if attempt == max_retries:
                return False, None, _msg("Resposta inválida do servidor")
        except Exception as e:
            if attempt == max_retries:
                return False, None, _msg(f"Erro inesperado: {e}")
        
        if attempt < max_retries:
            time.sleep(backoff_delays[attempt])
    
    return False, None, _msg("Falha de comunicação após múltiplas tentativas")