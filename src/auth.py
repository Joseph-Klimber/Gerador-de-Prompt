# src/auth.py
"""Autenticação via Google Sheets (Apps Script)."""
import urllib.request
import urllib.error
import json
import streamlit as st


def _get_apps_script_url() -> str:
    """Obtém URL do Apps Script do secrets (lazy)."""
    try:
        return st.secrets.get("APPS_SCRIPT_URL", "")
    except Exception:
        return ""


def verificar_acesso_sheets(email: str) -> tuple[bool, str | None, str | None]:
    """Verifica se e-mail tem acesso válido na planilha.
    
    Returns:
        (ok, expiracao_str, erro_str)
    """
    APPS_SCRIPT_URL = _get_apps_script_url()
    if not APPS_SCRIPT_URL:
        return False, None, "APPS_SCRIPT_URL não configurado no secrets.toml"
    
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, None, "E-mail inválido"
    
    payload = {"action": "verificar", "email": email}
    
    try:
        req = urllib.request.Request(
            APPS_SCRIPT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("ok"):
            exp = data.get("expiracao", "")
            return True, exp, None
        else:
            return False, None, data.get("erro", "E-mail não autorizado")
    
    except urllib.error.HTTPError as e:
        return False, None, f"Erro HTTP {e.code} ao consultar planilha"
    except urllib.error.URLError as e:
        return False, None, f"Erro de conexão: {e}"
    except json.JSONDecodeError:
        return False, None, "Resposta inválida do servidor"
    except Exception as e:
        return False, None, f"Erro inesperado: {e}"