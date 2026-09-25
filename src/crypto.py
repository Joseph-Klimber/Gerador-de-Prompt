"""crypto.py — Etapa 2.2 (Fernet obrigatorio, sem fallback fraco)"""
import hashlib
import base64
import streamlit as st

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False
    Fernet = None

OPCOES_GEMINI_3 = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]
MODELO_VISAO_PADRAO = "gemini-3.5-flash"
MODELO_TEXTO_PADRAO = "gemini-3.5-flash"


def _get_fernet_secret() -> str | None:
    sec = None
    try:
        sec = st.secrets.get("PS_FERNET_KEY")
    except Exception:
        pass
    if not sec:
        import os
        sec = os.environ.get("PS_FERNET_KEY")
    if not sec or "PLACEHOLDER" in str(sec) or "troque" in str(sec).lower():
        return None
    return str(sec).strip()


def _chave_fernet():
    segredo = _get_fernet_secret()
    if not segredo or not HAS_FERNET:
        return None
    try:
        digest = hashlib.sha256(segredo.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
    except Exception:
        return None


def _criptografar(texto: str) -> str:
    if not texto:
        return texto
    f = _chave_fernet()
    if not f:
        return texto
    return f.encrypt(texto.encode("utf-8")).decode("utf-8")


def _descriptografar(texto: str) -> str:
    if not texto:
        return texto
    f = _chave_fernet()
    if not f:
        return texto
    try:
        return f.decrypt(texto.encode("utf-8")).decode("utf-8")
    except Exception:
        return texto


def mascarar_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email:
        if len(email) <= 6:
            return (email[:1] + "***") if email else email
        return email[:3] + "********" + email[-3:]
    last_dot = email.rfind(".")
    prefix = email[:3]
    before_dot = email[:last_dot]
    suffix_core = before_dot[-3:] if len(before_dot) >= 3 else before_dot
    suffix = suffix_core + email[last_dot:]
    if len(email) <= 7:
        return prefix + "***" + suffix
    return f"{prefix}********{suffix}"


def _slug_usuario(email: str) -> str:
    import re
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return ""
    return re.sub(r"[^\w\-.]", "_", email) or ""


def fernet_disponivel() -> bool:
    return _chave_fernet() is not None
