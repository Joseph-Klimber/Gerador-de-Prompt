"""config_store.py — Etapa 2.4 (cache 600s + normalizacao 3.X + BYOK)"""
import os
import json
import copy
import time
import streamlit as st

from src.crypto import _criptografar, _descriptografar, _slug_usuario, OPCOES_GEMINI_3, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO
from src.auth import _request_with_retry, _get_apps_script_url

PASTA_CONFIGS = "configs_usuarios"


def _get_cache():
    return st.session_state.get("_config_cache", {})


def _set_cache(cache):
    st.session_state["_config_cache"] = cache


def _normalize_modelo(v):
    v = (v or "").strip()
    if v in OPCOES_GEMINI_3:
        return v
    if v == "gemini-3.8-flash":
        return "gemini-3.7-flash"
    return MODELO_VISAO_PADRAO


def carregar_config(email=None):
    email_normalizado = (email or "").strip().lower()
    if not email_normalizado:
        return {"chaves": {"Chave Visao": "", "Chave Texto": ""}, "modelo_visao": MODELO_VISAO_PADRAO, "modelo_texto": MODELO_TEXTO_PADRAO, "modelo_padrao": MODELO_TEXTO_PADRAO}

    cache = _get_cache()
    item = cache.get(email_normalizado)
    if item and time.time() - item[0] < 600:
        return copy.deepcopy(item[1])

    config = {"chaves": {"Chave Visao": "", "Chave Texto": ""}, "modelo_padrao": MODELO_TEXTO_PADRAO, "modelo_visao": MODELO_VISAO_PADRAO, "modelo_texto": MODELO_TEXTO_PADRAO}

    url = _get_apps_script_url()
    if url:
        try:
            resp = _request_with_retry("GET", url, params={"acao": "carregar_config", "email": email_normalizado}, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                dados = resp.json()
                if dados and dados.get("ok") and dados.get("config"):
                    loaded = json.loads(dados["config"])
                    if "Chave 1" in loaded.get("chaves", {}):
                        loaded["chaves"]["Chave Visao"] = loaded["chaves"].pop("Chave 1")
                    if "Chave 2" in loaded.get("chaves", {}):
                        loaded["chaves"]["Chave Texto"] = loaded["chaves"].pop("Chave 2")
                    config.update(loaded)
        except Exception:
            pass

    for k in ("modelo_visao", "modelo_texto"):
        config[k] = _normalize_modelo(config.get(k) or config.get("modelo_padrao", ""))
    config["modelo_padrao"] = config.get("modelo_texto", MODELO_TEXTO_PADRAO)

    if not config.get("chaves", {}).get("Chave Visao") and not config.get("chaves", {}).get("Chave Texto"):
        slug = _slug_usuario(email_normalizado)
        if slug:
            caminho = os.path.join(PASTA_CONFIGS, f"config_{slug}.json")
            if os.path.exists(caminho):
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if "Chave 1" in loaded.get("chaves", {}):
                            loaded["chaves"]["Chave Visao"] = loaded["chaves"].pop("Chave 1")
                        if "Chave 2" in loaded.get("chaves", {}):
                            loaded["chaves"]["Chave Texto"] = loaded["chaves"].pop("Chave 2")
                        if not config.get("chaves", {}).get("Chave Visao"):
                            config["chaves"]["Chave Visao"] = loaded.get("chaves", {}).get("Chave Visao", "")
                        if not config.get("chaves", {}).get("Chave Texto"):
                            config["chaves"]["Chave Texto"] = loaded.get("chaves", {}).get("Chave Texto", "")
                except Exception:
                    pass

    try:
        config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
    except Exception:
        pass

    cache[email_normalizado] = (time.time(), copy.deepcopy(config))
    _set_cache(cache)
    return copy.deepcopy(config)


def salvar_config(dados, email=None):
    email_normalizado = (email or "").strip().lower()
    if not email_normalizado or "@" not in email_normalizado:
        return False, "E-mail invalido."

    slug = _slug_usuario(email_normalizado)
    dados = dict(dados or {})
    for k in ("modelo_visao", "modelo_texto"):
        if k in dados:
            dados[k] = _normalize_modelo(dados[k])
    chaves_plain = dict(dados.get("chaves", {}))
    dados["chaves"] = {k: _criptografar(v) for k, v in chaves_plain.items()}

    url = _get_apps_script_url()
    if url:
        try:
            payload = {"acao": "salvar_config", "email": email_normalizado, "config": json.dumps(dados, ensure_ascii=False)}
            resp = _request_with_retry("POST", url, json=payload, timeout=20, allow_redirects=True)
            if resp.status_code == 200:
                try:
                    j = resp.json()
                    if j.get("ok"):
                        cache = _get_cache()
                        cache.pop(email_normalizado, None)
                        _set_cache(cache)
                        return True, None
                except Exception:
                    pass
        except Exception:
            pass

    try:
        os.makedirs(PASTA_CONFIGS, exist_ok=True)
        caminho = os.path.join(PASTA_CONFIGS, f"config_{slug}.json") if slug else os.path.join(PASTA_CONFIGS, "config_dev.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        cache = _get_cache()
        cache.pop(email_normalizado, None)
        _set_cache(cache)
        return False, "Erro ao salvar na nuvem — copia salva localmente (nao persiste apos reiniciar)."
    except Exception as e:
        return False, f"Falha ao salvar: {e}"
