# src/config_store.py
"""Armazenamento de configuração criptografado (local + opcional nuvem via Apps Script).
Compatível com Streamlit Community Cloud (filesystem efêmero)."""
import json
import pathlib
import os
import time
import urllib.request
import hmac
import hashlib
import base64
from datetime import datetime
from src.crypto import fernet_disponivel, _fernet, _get_ps_fernet_key
from src.auth import _get_apps_script_url

# Cache em memória para evitar chamadas de rede repetidas
_CONFIG_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 300  # 5 minutos

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


def _now() -> str:
    """Retorna timestamp atual formatado HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def _msg(msg: str) -> str:
    """Prefixa mensagem com timestamp."""
    return f"[{_now()}] {msg}"


def _config_path(email: str) -> pathlib.Path:
    """Caminho do arquivo de config local (hash do e-mail)."""
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
        result = json.loads(decrypted)
        return result if isinstance(result, dict) else {}
    except Exception:
        return None


def _hmac_sign(payload: str) -> str:
    """Gera assinatura HMAC-SHA256 para payload usando a chave mestra."""
    key = _get_ps_fernet_key() or ""
    hmac_key = hashlib.sha256(key.encode()).digest()
    sig = hmac.new(hmac_key, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _hmac_verify(payload: str, signature: str) -> bool:
    """Verifica assinatura HMAC-SHA256 do payload."""
    expected = _hmac_sign(payload)
    return hmac.compare_digest(expected, signature)


def _verify_config_hmac(response_data: dict) -> bool:
    """Verifica HMAC na resposta do Apps Script (espera campo 'hmac' no JSON)."""
    hmac_received = response_data.pop("hmac", None)
    if not hmac_received:
        return False
    payload_str = json.dumps(response_data, sort_keys=True, separators=(",", ":"))
    return _hmac_verify(payload_str, hmac_received)


def _fetch_from_apps_script(email: str) -> dict:
    """Busca configuração do Apps Script (com retry)."""
    APPS_SCRIPT_URL = _get_apps_script_url()
    if not APPS_SCRIPT_URL:
        return {}

    max_retries = 2
    backoff_delays = [1, 2]
    payload = {"action": "carregar", "email": email}
    data_bytes = json.dumps(payload).encode("utf-8")

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                APPS_SCRIPT_URL,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not _verify_config_hmac(data):
                raise ValueError("HMAC inválido na resposta do servidor")
            if data.get("ok"):
                if data.get("payload"):
                    decrypted = _decrypt(data["payload"])
                    return decrypted if isinstance(decrypted, dict) else {}
                elif data.get("config"):
                    cfg = data["config"]
                    return cfg if isinstance(cfg, dict) else {}
                return {}
        except Exception:
            if attempt == max_retries:
                return {}
            time.sleep(backoff_delays[attempt])
    return {}


def carregar_config(email: str) -> dict:
    """Carrega configuração do usuário (local + nuvem se disponível).

    Prioridade: local (mais rápido) → nuvem (fallback).
    No Streamlit Cloud: pula local (filesystem efêmero), vai direto pra nuvem.
    Cacheado por 5 minutos para evitar chamadas de rede repetidas.
    """
    if not email:
        return {}

    # Verifica cache
    now = time.time()
    if email in _CONFIG_CACHE:
        cached_data, cached_time = _CONFIG_CACHE[email]
        if now - cached_time < _CACHE_TTL:
            return cached_data

    # 1. Tenta local (só se NÃO estiver no Streamlit Cloud)
    if not IS_STREAMLIT_CLOUD:
        path = _config_path(email)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                data = _decrypt(content)
                if data:
                    _CONFIG_CACHE[email] = (data, now)
                    return data
            except Exception:
                pass

    # 2. Fallback nuvem (se Apps Script configurado)
    config_data = _fetch_from_apps_script(email)

    # Garante que é dict
    if not isinstance(config_data, dict):
        config_data = {}

    # Salva localmente para próxima vez (só se não Cloud)
    if config_data and not IS_STREAMLIT_CLOUD:
        salvar_config(config_data, email=email)

    _CONFIG_CACHE[email] = (config_data, now)
    return config_data


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

    # 2. Tenta nuvem (não bloqueia se falhar) - SEMPRE envia payload criptografado com assinatura HMAC
    APPS_SCRIPT_URL = _get_apps_script_url()
    if APPS_SCRIPT_URL:
        max_retries = 2
        backoff_delays = [1, 2]
        payload_dict = {"action": "salvar", "email": email, "payload": encrypted}
        payload_str = json.dumps(payload_dict)
        sig = _hmac_sign(payload_str)

        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(
                    APPS_SCRIPT_URL,
                    data=payload_str.encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Signature": sig
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                if not result.get("ok"):
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {result.get('erro')}")
                    return True, _msg(f"Aviso: nuvem falhou ({result.get('erro')}) — local salvo")
                break  # Success
            except Exception as e:
                if attempt == max_retries:
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {e}")
                    return True, _msg(f"Aviso: nuvem indisponível ({e}) — local salvo")
            if attempt < max_retries:
                time.sleep(backoff_delays[attempt])

    if IS_STREAMLIT_CLOUD and not APPS_SCRIPT_URL:
        return False, "APPS_SCRIPT_URL não configurado — config não será persistida"

    # Invalida cache após salvar
    _CONFIG_CACHE.pop(email, None)
    return True, None
