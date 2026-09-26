"""auth.py — Etapa 2.3 (verificar_acesso + retry + 4 formatos de data)"""
import re
import time
import requests
import streamlit as st
from datetime import datetime


APPS_SCRIPT_URL_FALLBACK = "https://script.google.com/macros/s/AKfycbzgEj3YPwqiUbiueyu8wjZ9ZZK0Rcc6G3kucysRSJ2gNmzRzUdMuLqv_q55N1kSO8PQ/exec"

def _get_apps_script_url() -> str:
    url = None
    try:
        url = st.secrets.get("APPS_SCRIPT_URL")
    except Exception:
        pass
    if not url:
        import os
        url = os.environ.get("APPS_SCRIPT_URL")
    if not url or "PLACEHOLDER" in str(url):
        url = APPS_SCRIPT_URL_FALLBACK
    if not url:
        return ""
    return str(url).strip()


def _request_with_retry(method, url, max_retries=2, retry_statuses=(429, 500, 502, 503, 504), **kwargs):
    for tentativa in range(max_retries + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code not in retry_statuses or tentativa == max_retries:
                return resp
            retry_after = resp.headers.get("Retry-After", "")
            try:
                espera = float(retry_after) if retry_after else 2 ** tentativa
            except (TypeError, ValueError):
                espera = 2 ** tentativa
            time.sleep(min(espera, 20))
        except requests.exceptions.RequestException:
            if tentativa == max_retries:
                raise
            time.sleep(2 ** tentativa)
    return resp


def _parse_data_expiracao(exp: str):
    exp = (exp or "").strip()
    if not exp:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(exp, fmt).date()
        except Exception:
            continue
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(exp.replace("T", " ").strip(), fmt).date()
        except Exception:
            continue
    return None


def verificar_acesso_sheets(email: str):
    email = (email or "").strip().lower()
    if not email or "@" not in email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return False, "", "E-mail invalido — verifique o e-mail da compra."
    url = _get_apps_script_url()
    if not url:
        return False, "", "Servico de dados nao configurado — contate o suporte."
    try:
        params = {"acao": "verificar_acesso", "email": email}
        resp = _request_with_retry("GET", url, params=params, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            try:
                dados = resp.json()
            except Exception:
                return False, "", "Resposta invalida do servidor — tente novamente."
            if not dados.get("encontrado", False):
                return False, dados.get("expiracao", ""), "E-mail nao encontrado — verifique o e-mail da compra."
            exp = str(dados.get("expiracao", "")).strip()
            if exp:
                data_exp = _parse_data_expiracao(exp)
                if data_exp and data_exp < datetime.now().date():
                    return False, exp, f"Acesso expirou em {exp} — renove na Kiwify."
            return True, exp, None
        return False, "", f"Erro do servidor {resp.status_code} — tente novamente."
    except Exception as e:
        return False, "", f"Falha na conexao — verifique sua internet e tente novamente. ({e})"
