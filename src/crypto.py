# src/crypto.py
"""Criptografia Fernet para chaves BYOK (chaves do usuário)."""
import os
import base64
import streamlit as st
from cryptography.fernet import Fernet
from typing import Optional


def _get_ps_fernet_key() -> Optional[str]:
    """Obtém chave mestra do secrets (lazy)."""
    try:
        return st.secrets.get("PS_FERNET_KEY")
    except Exception:
        return os.getenv("PS_FERNET_KEY")


def fernet_disponivel() -> bool:
    """Verifica se criptografia está disponível (chave mestra configurada)."""
    key = _get_ps_fernet_key()
    return bool(key and key.strip())


def _fernet() -> Fernet:
    """Retorna instância Fernet (cacheada)."""
    if not hasattr(_fernet, "_instance"):
        key = _get_ps_fernet_key()
        if not key:
            raise RuntimeError("PS_FERNET_KEY não configurado")
        # Garante que a chave tem 32 bytes url-safe base64
        key = key.strip()
        if len(key) != 44:  # Fernet key é 32 bytes = 44 chars base64url
            # Deriva chave de 32 bytes via SHA256 se necessário
            import hashlib
            key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode()
        _fernet._instance = Fernet(key.encode())
    return _fernet._instance


def mascarar_email(email: str) -> str:
    """Mascarar e-mail para exibição (ex: sergio@exemplo.com -> ser***@exemplo.com)."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 3:
        masked = local[0] + "*" * (len(local) - 1)
    else:
        masked = local[:3] + "*" * (len(local) - 3)
    return f"{masked}@{domain}"


# Constantes de modelos Gemini (re-exportadas para compatibilidade)
OPCOES_GEMINI_3 = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]
MODELO_VISAO_PADRAO = "gemini-3.5-flash"
MODELO_TEXTO_PADRAO = "gemini-3.5-flash"