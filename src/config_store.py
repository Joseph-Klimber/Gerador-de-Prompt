# src/config_store.py
"""Armazenamento de configuração criptografado (local + opcional nuvem via Apps Script).
Compatível com Streamlit Community Cloud (filesystem efêmero)."""
import json
import pathlib
import os
from src.crypto import fernet_disponivel, _fernet
from src.auth import _get_apps_script_url

# Detecta Streamlit Cloud (filesystem efêmero — não persiste entre reboots)
IS_STREAMLIT_CLOUD = (
    os.getenv("STREAMLIT_SHARING_MODE") == "1"
    or "streamlit.app" in os.getenv("HOSTNAME", "")
    or "streamlit.io" in os.getenv("HOSTNAME", "")
)

# Arquivo local de configuração (só usado fora do Cloud)
CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"
if not IS_STREAMLIT_CLOUD:
    CONFIG_DIR.mkdir(exist_ok=True)


def _config_path(email: str) -> pathlib.Path:
    """Caminho do arquivo de config local (hash do e-mail)."""
    import hashlib
    h = hashlib.sha256(email.encode()).hexdigest()[:16]
    return CONFIG_DIR / f"config_{h}.json"


def _encrypt(data: dict) -> str | None:
    """Criptografa dict para JSON string."""
    if not fernet_disponivel():
        return None
    json_str = json.dumps(data, ensure_ascii=False)
    return _fernet().encrypt(json_str.encode()).decode()


def _decrypt(token: str) -> dict | None:
    """Descriptografa JSON string para dict."""
    if not fernet_disponivel():
        return None
    try:
        decrypted = _fernet().decrypt(token.encode()).decode()
        return json.loads(decrypted)
    except Exception:
        return None


def carregar_config(email: str) -> dict:
    """Carrega configuração do usuário (local + nuvem se disponível).
    
    Prioridade: local (mais rápido) → nuvem (fallback).
    No Streamlit Cloud: pula local (filesystem efêmero), vai direto pra nuvem.
    """
    if not email:
        return {}
    
    # 1. Tenta local (só se NÃO estiver no Streamlit Cloud)
    if not IS_STREAMLIT_CLOUD:
        path = _config_path(email)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                data = _decrypt(content)
                if data:
                    return data
            except Exception:
                pass
    
    # 2. Fallback nuvem (se Apps Script configurado)
    APPS_SCRIPT_URL = _get_apps_script_url()
    if APPS_SCRIPT_URL:
        try:
            import urllib.request
            payload = {"action": "carregar", "email": email}
            req = urllib.request.Request(
                APPS_SCRIPT_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok") and data.get("config"):
                # Salva localmente para próxima vez (só se não Cloud)
                if not IS_STREAMLIT_CLOUD:
                    salvar_config(data["config"], email=email)
                return data["config"]
        except Exception:
            pass
    
    return {}


def salvar_config(dados: dict, email: str) -> tuple[bool, str | None]:
    """Salva configuração (local + nuvem se disponível).
    
    Returns:
        (ok, erro_msg)
    No Streamlit Cloud: salva só na nuvem (filesystem efêmero).
    """
    if not email:
        return False, "E-mail não fornecido"
    
    if not fernet_disponivel():
        return False, "Criptografia indisponível (configure PS_FERNET_KEY)"
    
    encrypted = _encrypt(dados)
    if not encrypted:
        return False, "Falha na criptografia"
    
    # 1. Salva local (só se NÃO estiver no Streamlit Cloud)
    if not IS_STREAMLIT_CLOUD:
        try:
            path = _config_path(email)
            path.write_text(encrypted, encoding="utf-8")
        except Exception as e:
            return False, f"Erro ao salvar local: {e}"
    else:
        # No Cloud: avisa que config fica só na sessão atual
        pass
    
    # 2. Tenta nuvem (não bloqueia se falhar)
    APPS_SCRIPT_URL = _get_apps_script_url()
    if APPS_SCRIPT_URL:
        try:
            import urllib.request
            payload = {"action": "salvar", "email": email, "config": dados}
            req = urllib.request.Request(
                APPS_SCRIPT_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            if not result.get("ok"):
                if IS_STREAMLIT_CLOUD:
                    return False, f"Falha ao salvar na nuvem: {result.get('erro')}"
                return True, f"Aviso: nuvem falhou ({result.get('erro')}) — local salvo"
        except Exception as e:
            if IS_STREAMLIT_CLOUD:
                return False, f"Falha ao salvar na nuvem: {e}"
            return True, f"Aviso: nuvem indisponível ({e}) — local salvo"
    
    if IS_STREAMLIT_CLOUD and not APPS_SCRIPT_URL:
        return False, "APPS_SCRIPT_URL não configurado — config não será persistida"
    
    return True, None