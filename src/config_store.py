# src/config_store.py
"""Armazenamento de configuração criptografado (local + opcional nuvem via Apps Script).
Compatível com Streamlit Community Cloud (filesystem efêmero).
HMAC-SHA256 request/response signing: key = PS_FERNET_KEY string bytes directly.
Response HMAC verification rejects unsigned/tampered configs.
In-memory cache 5 min TTL; invalidated on salvar_config.
"""
import json
import pathlib
import os
import time
import hashlib
import hmac
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any

from src.crypto import fernet_disponivel, _fernet, _get_ps_fernet_key
from core.state import LOCAL_EMAIL

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

# Brasil timezone (UTC-3) para timestamps user-facing
BR_TZ = timezone(timedelta(hours=-3))

# In-memory cache: {email: (timestamp, config_dict)}
_CONFIG_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes


def _now() -> str:
    """Timestamp no fuso do Brasil (HH:MM:SS)."""
    return datetime.now(BR_TZ).strftime("%H:%M:%S")


def _msg(text: str) -> str:
    """Prefixa mensagem com timestamp [HH:MM:SS]."""
    return f"[{_now()}] {text}"


def _hmac_key() -> bytes:
    """Chave HMAC = bytes da string PS_FERNET_KEY (mesma do Fernet)."""
    key = _get_ps_fernet_key() or ""
    return key.strip().encode()


def _hmac_sign(payload: str) -> str:
    """Assina payload (string) com HMAC-SHA256, retorna base64url sem padding."""
    sig = hmac.new(_hmac_key(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _hmac_verify(payload: str, signature_b64url: str) -> bool:
    """Verifica assinatura HMAC (comparação tempo-constante)."""
    expected = _hmac_sign(payload)
    # constant-time compare via hmac.compare_digest
    return hmac.compare_digest(expected, signature_b64url)


def _verify_config_hmac(response_data: dict) -> bool:
    """Verifica HMAC na resposta do Apps Script.
    Remove campo 'hmac', serializa canonicamente (sort_keys, separators),
    compara com assinatura recebida.
    """
    hmac_received = response_data.pop("hmac", None)
    if not hmac_received:
        return False
    # Serialização determinística: chaves ordenadas, sem espaços
    payload_str = json.dumps(response_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _hmac_verify(payload_str, hmac_received)


def _config_path(email: str) -> pathlib.Path:
    """Caminho do arquivo de config local (hash do e-mail)."""
    h = hashlib.sha256(email.encode()).hexdigest()[:16]
    return CONFIG_DIR / f"config_{h}.json"


def _encrypt(data: dict) -> str | None:
    """Criptografa dict para JSON string (Fernet)."""
    if not fernet_disponivel():
        return None
    json_str = json.dumps(data, ensure_ascii=False)
    return _fernet().encrypt(json_str.encode()).decode()


def _decrypt(token: str) -> dict | None:
    """Descriptografa JSON string para dict. Type-guard: retorna dict ou None."""
    if not fernet_disponivel():
        return None
    try:
        decrypted = _fernet().decrypt(token.encode()).decode()
        result = json.loads(decrypted)
        return result if isinstance(result, dict) else None
    except Exception:
        return None


def _get_apps_script_url() -> str:
    """Obtém URL do Apps Script do secrets (lazy)."""
    try:
        import streamlit as st
        return st.secrets.get("APPS_SCRIPT_URL", "")
    except Exception:
        return ""


def _resilient_post(url: str, payload: dict, timeout: int = 10, max_retries: int = 2) -> dict:
    """POST com retry (1s, 2s), timeout, erros timestampados.
    Retorna dict (parsed JSON) ou {'ok': False, 'erro': '[HH:MM:SS] msg'}.
    """
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            if attempt == max_retries:
                return {"ok": False, "erro": _msg(f"Erro HTTP {e.code}")}
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


def carregar_config(email: str) -> dict:
    """Carrega configuração do usuário (cache → local → nuvem com HMAC verify).
    Retorna sempre dict (vazio se falha).
    """
    if not email:
        return {}

    # 0. Cache in-memory (5 min)
    cached = _CONFIG_CACHE.get(email)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]

    # 1. Tenta local (só se NÃO Cloud)
    if not IS_STREAMLIT_CLOUD:
        path = _config_path(email)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                data = _decrypt(content)
                if data:
                    _CONFIG_CACHE[email] = (time.time(), data)
                    return data
            except Exception:
                pass

    # 2. Fallback nuvem (se Apps Script configurado)
    APPS_SCRIPT_URL = _get_apps_script_url()
    if APPS_SCRIPT_URL and email != LOCAL_EMAIL:
        # Assina request body
        request_body = {"action": "carregar", "email": email}
        body_str = json.dumps(request_body, separators=(",", ":"), ensure_ascii=False)
        signature = _hmac_sign(body_str)

        headers = {"Content-Type": "application/json", "X-Signature": signature}
        # reutiliza _resilient_post com headers custom — versão simplificada inline
        for attempt in range(3):  # max_retries=2
            try:
                data_bytes = body_str.encode("utf-8")
                req = urllib.request.Request(
                    APPS_SCRIPT_URL, data=data_bytes, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    response = json.loads(resp.read().decode("utf-8"))

                # Type guard: response must be dict
                if not isinstance(response, dict):
                    break

                # HMAC verification on response
                if not _verify_config_hmac(response):
                    break

                if response.get("ok") and response.get("payload"):
                    token = response["payload"]
                    data = _decrypt(token)
                    if data:
                        _CONFIG_CACHE[email] = (time.time(), data)
                        return data
                break  # resposta inválida (ok=False ou sem payload)
            except urllib.error.HTTPError as e:
                if attempt == 2:
                    break
            except urllib.error.URLError as e:
                if attempt == 2:
                    break
            except json.JSONDecodeError:
                if attempt == 2:
                    break
            except Exception:
                if attempt == 2:
                    break
            if attempt < 2:
                time.sleep((1, 2)[attempt])

    # 3. Empty dict fallback (type-guarded)
    result: dict = {}
    _CONFIG_CACHE[email] = (time.time(), result)
    return result


def salvar_config(dados: dict, email: str) -> tuple[bool, str | None]:
    """Salva configuração (local + nuvem com payload criptografado + HMAC).
    Returns: (ok, erro_msg)
    """
    if not email:
        return False, _msg("E-mail não fornecido")

    if not fernet_disponivel():
        return False, _msg("Criptografia indisponível (configure PS_FERNET_KEY)")

    encrypted = _encrypt(dados)
    if not encrypted:
        return False, _msg("Falha na criptografia")

    # 1. Salva local (só se NÃO Cloud)
    if not IS_STREAMLIT_CLOUD:
        try:
            path = _config_path(email)
            path.write_text(encrypted, encoding="utf-8")
        except Exception as e:
            return False, _msg(f"Erro ao salvar local: {e}")

    # 2. Tenta nuvem (payload criptografado + X-Signature)
    APPS_SCRIPT_URL = _get_apps_script_url()
    if APPS_SCRIPT_URL and email != LOCAL_EMAIL:
        payload = {
            "action": "salvar",
            "email": email,
            "payload": encrypted,  # Fernet token (ciphertext)
        }
        body_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        signature = _hmac_sign(body_str)

        headers = {"Content-Type": "application/json", "X-Signature": signature}

        for attempt in range(3):  # max_retries=2
            try:
                data_bytes = body_str.encode("utf-8")
                req = urllib.request.Request(
                    APPS_SCRIPT_URL, data=data_bytes, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode("utf-8"))

                # Type guard
                if not isinstance(result, dict):
                    break

                if result.get("ok"):
                    _CONFIG_CACHE.pop(email, None)  # invalidar cache
                    return True, None

                # falha com erro do servidor
                erro = result.get("erro", "Falha ao salvar na nuvem")
                if IS_STREAMLIT_CLOUD:
                    return False, _msg(f"Falha ao salvar na nuvem: {erro}")
                return True, _msg(f"Aviso: nuvem falhou ({erro}) — local salvo")

            except urllib.error.HTTPError as e:
                if attempt == 2:
                    erro = f"Erro HTTP {e.code}"
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {erro}")
                    return True, _msg(f"Aviso: nuvem indisponível ({erro}) — local salvo")
            except urllib.error.URLError as e:
                if attempt == 2:
                    erro = f"Erro de conexão: {e.reason}"
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {erro}")
                    return True, _msg(f"Aviso: nuvem indisponível ({erro}) — local salvo")
            except json.JSONDecodeError:
                if attempt == 2:
                    erro = "Resposta inválida do servidor"
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {erro}")
                    return True, _msg(f"Aviso: nuvem indisponível ({erro}) — local salvo")
            except Exception as e:
                if attempt == 2:
                    erro = str(e)
                    if IS_STREAMLIT_CLOUD:
                        return False, _msg(f"Falha ao salvar na nuvem: {erro}")
                    return True, _msg(f"Aviso: nuvem indisponível ({erro}) — local salvo")

            if attempt < 2:
                time.sleep((1, 2)[attempt])

    if IS_STREAMLIT_CLOUD and not APPS_SCRIPT_URL:
        return False, _msg("APPS_SCRIPT_URL não configurado — config não será persistida")

    _CONFIG_CACHE.pop(email, None)  # invalidate cache on success
    return True, None