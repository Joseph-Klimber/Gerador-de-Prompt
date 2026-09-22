# -*- coding: utf-8 -*-
"""
Prompt Studio Cockpit — Interface Minimalista de Alta Precisão
Arquitetura: Separação de Responsabilidades (Visão vs Texto) + BYOK (Traga sua Chave).

v4.0 — Google Pure-Core & State Sync:
  • Eliminada dependência de terceiros (OpenRouter removido).
  • Arquitetura de Cotas Isoladas: 1 Chave para Visão, 1 Chave para Texto.
  • Resolução definitiva do Bug de Estado (Textos injetados instantaneamente na UI).
  • Campo de Modelo livre (Input) para evitar erros 404 em atualizações da Google.
"""

import os
import json
import copy
import random
import re
import secrets
import time
import html
import unicodedata
from datetime import datetime
import requests
from PIL import Image
import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM
# ==============================================================================
st.set_page_config(
    page_title="Prompt Studio Cockpit | Engenharia Preditiva de Prompts IA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    :root {
        --ps-blue: #2563eb;
        --ps-gold: #b45309;
        --ps-emerald: #059669;
        --ps-amber: #d97706;
        --ps-rose: #e11d48;
    }
    
    .ps-brand { color: var(--text-color); font-size: 1.15rem; font-weight: 800; letter-spacing: .15em; margin-top: .2rem; }
    .ps-header-note { color: var(--text-color); opacity: 0.7; font-size: .88rem; margin-bottom: 1.1rem; }
    .ps-kicker { color: var(--ps-blue); font-size: .75rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-top: .4rem; }
    .ps-title { color: var(--text-color); font-size: clamp(1.8rem, 3.2vw, 2.7rem); line-height: 1.15; margin: .2rem 0 .4rem; font-weight: 800; }
    .ps-slogan { font-size: 1.15rem; color: var(--ps-blue); font-weight: 700; margin-bottom: 2rem; border-left: 4px solid var(--ps-blue); padding-left: 12px;}
    
    .hero-title { font-size: 3.5rem; font-weight: 900; color: var(--text-color); line-height: 1.1; margin-bottom: 1rem; text-align: center; letter-spacing: -0.03em; }
    .hero-subtitle { font-size: 1.2rem; color: var(--text-color); opacity: 0.8; text-align: center; max-width: 700px; margin: 0 auto 3rem auto; line-height: 1.6; }
    .showcase-box { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 16px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    .label-ideia { font-size: 0.8rem; font-weight: 800; color: #2563eb; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .text-ideia { font-size: 1.1rem; color: var(--text-color); font-style: italic; border-left: 4px solid #2563eb; padding-left: 1rem; margin-bottom: 1.5rem; }
    .label-prompt { font-size: 0.8rem; font-weight: 800; color: #b45309; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .code-prompt { background: var(--background-color); padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem; color: var(--text-color); height: 180px; overflow-y: auto; border: 1px solid rgba(128,128,128,0.2); }
    .plan-container { text-align: center; background: var(--secondary-background-color); padding: 2rem; border-radius: 16px; border: 1px solid rgba(128,128,128,0.2); margin-top: 2rem; }
    .byok-badge { display: inline-block; background: rgba(37, 99, 235, 0.1); color: #2563eb; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: bold; margin-bottom: 1rem; border: 1px solid rgba(37, 99, 235, 0.2); }

    .ps-preprompt { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 12px; padding: 1.25rem 1.4rem; line-height: 1.85; font-size: 1.02rem; color: var(--text-color); margin: 0.8rem 0 1.2rem; }
    .ps-user-word { color: var(--text-color); font-weight: 700; background-color: rgba(37, 99, 235, 0.15); border-left: 2px solid #2563eb; padding: 2px 6px; border-radius: 4px; }
    .ps-ai-word { color: var(--ps-gold); font-weight: 600; }
    .ps-legend { display: flex; gap: 1.5rem; margin: .6rem 0 .9rem; font-size: .88rem; font-weight: 600; align-items: center; }
    
    .comp-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 700; padding: 4px 10px; border-radius: 9999px; margin-right: 6px; margin-bottom: 6px; }
    .comp-green { background-color: rgba(5, 150, 105, 0.1); color: #10b981; border: 1px solid rgba(5, 150, 105, 0.3); }
    .comp-amber { background-color: rgba(217, 119, 6, 0.1); color: #f59e0b; border: 1px solid rgba(217, 119, 6, 0.3); }
    .comp-blue  { background-color: rgba(37, 99, 235, 0.1); color: #3b82f6; border: 1px solid rgba(37, 99, 235, 0.3); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CONSTANTES E DICIONÁRIO BLINDADO
# ==============================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzgEj3YPwqiUbiueyu8wjZ9ZZK0Rcc6G3kucysRSJ2gNmzRzUdMuLqv_q55N1kSO8PQ/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/xo0m3rF"

PASTA_CONFIGS = "configs_usuarios"

OPCOES_SENSUALIDADE = [
    "1 - Seguro (SFW)",
    "2 - Menos Seguro",
    "3 - Ecchi Leve",
    "4 - Ecchi",
    "5 - Picante",
    "6 - Dual (Com & Sem Censura)",
]

BANCO_DE_MOTORES = {
    "ComfyUI / Pony SDXL": {
        "regra_positivo": "PRIMEIRO, extraia o sujeito e a roupa da narrativa visual. Ordem de Tags OBRIGATÓRIA: 1. Qualidade (score_9, score_8_up) -> 2. CONTAGEM E GÊNERO (ex: 1boy, solo, ou 1girl, solo) -> 3. PROFISSÃO/ESPÉCIE (ex: astronaut) -> 4. Vestuário fiel à narrativa -> 5. Ação -> 6. Cenário.",
        "regra_negativo": "BASE INEGOCIÁVEL: score_6, score_5, score_4, score_3, score_2, score_1, worst quality, low quality, normal quality, text, watermark, jpeg artifacts, ugly, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, mutated, deformed, out of frame.",
        "dica_tecnica": "Modelos baseados no Pony dependem estritamente da tag de gênero no início."
    },
    "ComfyUI / Illustrious": {
        "regra_positivo": "Traduza fielmente a cena. PREFIXO OBRIGATÓRIO: masterpiece, best quality, ultra-detailed, illustration. Logo em seguida, adicione OBRIGATORIAMENTE a contagem e gênero do sujeito (ex: 1boy, solo, ou 1girl, multiple girls).",
        "regra_negativo": "Base: lowres, bad quality, worst quality, bad anatomy, bad hands, text, error, missing fingers, cropped, signature, watermark.",
        "dica_tecnica": "Mantenha CFG entre 5.0 e 7.0."
    },
    "Flux.1 / Flux.2 (Klein)": {
        "regra_positivo": "Traduza TODA a cena para o inglês em um parágrafo longo, fluido e hiper-descritivo. SEM tags isoladas por vírgula. A prioridade máxima é garantir que o sujeito exato, a roupa e o cenário estejam descritos como uma fotografia.",
        "regra_negativo": None,
        "dica_tecnica": "Modelos Flux operam melhor sem prompt negativo. Foque na prosa fotográfica."
    },
    "Midjourney v6.1+": {
        "regra_positivo": "REGRA MÁXIMA: Comece descrevendo o SUJEITO, A ROUPA e a AÇÃO exatamente como estão na Narrativa Visual. Depois descreva o CENÁRIO. SÓ ENTÃO adicione termos de estética cinematográfica (ex: cinematic lighting) e equipamentos de câmera. Termine com: --ar 16:9 --v 6.1 --stylize 250",
        "regra_negativo": None, 
        "dica_tecnica": "Não sobreponha a estética ao sujeito."
    },
    "ComfyUI / SDXL Base Natural": {
        "regra_positivo": "Traduza a cena integralmente. FÓRMULA: 'A breathtaking photo of [Sujeito + Roupas fiéis], who is [Ação], located in [Cenário Detalhado]. The lighting is [Iluminação]. Shot on [Câmera]'.",
        "regra_negativo": "Base: ugly, deformed, poorly drawn, bad anatomy, missing limbs, mutated hands, unnatural proportions, amateur, watermark.",
        "dica_tecnica": "Refiner em 20% ajuda nos detalhes de rostos."
    }
}

OPCOES_DESTINO = ["Selecione o Motor Destino..."] + list(BANCO_DE_MOTORES.keys())

# ==============================================================================
# 2.1 FUNÇÕES PURAS E SEGURANÇA
# ==============================================================================
def mascarar_email(email):
    if not email or "@" not in email: return email
    nome, dominio = email.split("@", 1)
    if len(nome) <= 3: return f"{nome}***@{dominio}"
    return f"{nome[:3]}***@{dominio}"

def _slug_usuario(email):
    return re.sub(r'[^\w\-.]', '_', (email or "anonimo").strip().lower()) or "anonimo"

def normalizar_texto(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )

def _ps_markup_origin(preprompt, ideia_original):
    try:
        if not preprompt:
            return ""
        texto_orig = set(normalizar_texto(ideia_original).split())
        partes = []
        for token in re.split(r"(\s+)", str(preprompt)):
            if not token.strip():
                partes.append(html.escape(token))
            elif normalizar_texto(token) in texto_orig:
                partes.append(f"<span class=\"ps-user-word\">{html.escape(token)}</span>")
            else:
                partes.append(f"<span class=\"ps-ai-word\">{html.escape(token)}</span>")
        return "".join(partes)
    except Exception:
        return html.escape(str(preprompt or ""))

def parse_json_ia(texto):
    if not texto:
        return None
    limpo = str(texto).strip()
    limpo = re.sub(r"^```(?:json)?\s*", "", limpo, flags=re.IGNORECASE)
    limpo = re.sub(r"\s*```$", "", limpo).strip()

    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        pass

    inicio = limpo.find("{")
    if inicio < 0:
        return None

    profundidade = 0
    em_string = False
    escapado = False
    fim = None
    for indice in range(inicio, len(limpo)):
        caractere = limpo[indice]
        if em_string:
            if escapado:
                escapado = False
            elif caractere == "\\":
                escapado = True
            elif caractere == '"':
                em_string = False
            continue
        if caractere == '"':
            em_string = True
        elif caractere == "{":
            profundidade += 1
        elif caractere == "}":
            profundidade -= 1
            if profundidade == 0:
                fim = indice + 1
                break

    if fim is None:
        return None
    try:
        return json.loads(limpo[inicio:fim])
    except (TypeError, json.JSONDecodeError):
        return None

def _chave_fernet():
    segredo = None
    try: segredo = st.secrets.get("PS_FERNET_KEY")
    except Exception: pass
    if not segredo: segredo = os.environ.get("PS_FERNET_KEY")
    if not segredo:
        return None
    try:
        from cryptography.fernet import Fernet
        import base64
        import hashlib
        digest = hashlib.sha256(segredo.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
    except Exception:
        return None

def _criptografar(texto):
    f = _chave_fernet()
    if not f or not texto: return texto
    return f.encrypt(texto.encode("utf-8")).decode("utf-8")

def _descriptografar(texto):
    f = _chave_fernet()
    if not f or not texto: return texto
    try: return f.decrypt(texto.encode("utf-8")).decode("utf-8")
    except Exception: return texto

def _request_with_retry(method, url, max_retries=2, retry_statuses=(429, 500, 502, 503, 504), **kwargs):
    for tentativa in range(max_retries + 1):
        try:
            resposta = requests.request(method, url, **kwargs)
            if resposta.status_code not in retry_statuses or tentativa == max_retries:
                return resposta
            retry_after = resposta.headers.get("Retry-After", "")
            try:
                espera = float(retry_after) if retry_after else 2 ** tentativa
            except (TypeError, ValueError):
                espera = 2 ** tentativa
            time.sleep(min(espera, 8.0))
        except requests.RequestException:
            if tentativa == max_retries:
                raise
            time.sleep(min(2 ** tentativa, 8.0))
    raise RuntimeError("Falha HTTP sem resposta.")

def _req_apps_script(params, timeout=20):
    try:
        resp = _request_with_retry(
            "GET", APPS_SCRIPT_URL.strip(), params=params, timeout=timeout,
            allow_redirects=True
        )
        if resp.status_code == 200: return resp.json()
        return {"ok": False, "erro": f"Servidor retornou HTTP {resp.status_code}."}
    except Exception as e: return {"ok": False, "erro": f"Falha de conexão com o serviço de dados: {e}"}

def carregar_config(email=None):
    email_normalizado = (email or "").strip().lower()
    cache = st.session_state.get("_config_cache", {})
    item_cache = cache.get(email_normalizado)
    if item_cache and time.time() - item_cache[0] < 30:
        return copy.deepcopy(item_cache[1])

    config = {
        "chaves": {"Chave Visao": "", "Chave Texto": ""},
        "modelo_padrao": "gemini-1.5-flash"
    }
    dados = _req_apps_script({"acao": "carregar_config", "email": email_normalizado})
    if dados and dados.get("ok") and dados.get("config"):
        try:
            loaded_config = json.loads(dados["config"])
            if "Chave 1" in loaded_config.get("chaves", {}):
                loaded_config["chaves"]["Chave Visao"] = loaded_config["chaves"].pop("Chave 1")
            if "Chave 2" in loaded_config.get("chaves", {}):
                loaded_config["chaves"]["Chave Texto"] = loaded_config["chaves"].pop("Chave 2")
                
            config.update(loaded_config)
            config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
            cache[email_normalizado] = (time.time(), copy.deepcopy(config))
            st.session_state["_config_cache"] = cache
            return copy.deepcopy(config)
        except Exception: pass
            
    caminho = os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f: 
                loaded_config = json.load(f)
                if "Chave 1" in loaded_config.get("chaves", {}):
                    loaded_config["chaves"]["Chave Visao"] = loaded_config["chaves"].pop("Chave 1")
                if "Chave 2" in loaded_config.get("chaves", {}):
                    loaded_config["chaves"]["Chave Texto"] = loaded_config["chaves"].pop("Chave 2")
                config.update(loaded_config)
            config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
        except Exception: pass
    cache[email_normalizado] = (time.time(), copy.deepcopy(config))
    st.session_state["_config_cache"] = cache
    return copy.deepcopy(config)

def salvar_config(dados, email=None):
    dados = dict(dados)
    dados["chaves"] = {k: _criptografar(v) for k, v in dados.get("chaves", {}).items()}
    
    payload = {"acao": "salvar_config", "email": (email or "").strip().lower(), "config": json.dumps(dados, ensure_ascii=False)}
    try:
        resp = _request_with_retry(
            "POST", APPS_SCRIPT_URL.strip(), json=payload, timeout=20,
            allow_redirects=True
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            if "_config_cache" in st.session_state:
                st.session_state["_config_cache"].pop((email or "").strip().lower(), None)
            return True, None
    except Exception: pass

    os.makedirs(PASTA_CONFIGS, exist_ok=True)
    with open(os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    if "_config_cache" in st.session_state:
        st.session_state["_config_cache"].pop((email or "").strip().lower(), None)
    return False, "Erro ao salvar na Nuvem. Cópia salva localmente."

def _extrair_retry_after_segundos(erro_str):
    try:
        m = re.search(r"retry[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*s", erro_str, re.IGNORECASE)
        if m:
            return min(float(m.group(1)), 30.0)
        m2 = re.search(r"Retry-After:\s*([0-9]+)", erro_str, re.IGNORECASE)
        if m2:
            return min(float(m2.group(1)), 30.0)
    except Exception:
        pass
    return None

def _eh_erro_transitorio_gemini(e):
    s = str(e).lower()
    # 400/validation: não adianta retentar (ex: temperature em 3.8)
    if any(k in s for k in ("invalid argument", "validation", "not supported", "unsupported", "unknown field")):
        return False
    if any(k in s for k in ("503", "429", "500", "502", "504", "overloaded", "unavailable", "resource exhausted", "internal error", "deadline exceeded")):
        # se a mensagem citar parâmetro deprecado, é erro permanente -> não retenta
        if any(p in s for p in ("temperature", "top_p", "top_k", "candidate_count", "thinking")):
            # se for 503 mas menciona parâmetro, é validação mapeada como 503
            if "temperature" in s or "not supported" in s or "unsupported" in s:
                return False
        return True
    # SDK google-genai lança ServerError / APIError com code 503
    try:
        code = getattr(e, "code", None) or getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
        if code in (429, 500, 502, 503, 504):
            # checar novamente mensagem de validação
            if any(p in s for p in ("temperature", "candidate_count")) and "not supported" in s:
                return False
            return True
    except Exception:
        pass
    return False

def _build_gemini_config(system_instruction, model_id, temperature=None):
    """Monta GenerateContentConfig compatível com Gemini 3.x (sem temperature)."""
    eh_gemini3 = str(model_id or "").startswith("gemini-3")
    if types is None:
        cfg = {"system_instruction": system_instruction}
        if not eh_gemini3 and temperature is not None:
            cfg["temperature"] = temperature
        return cfg
    # Gemini 3.x: temperature/top_p/top_k deprecados -> usar thinking_level
    if eh_gemini3:
        try:
            # medium = padrão equilibrado (docs); low seria mais rápido
            thinking = types.ThinkingConfig(thinking_level="medium")
            return types.GenerateContentConfig(system_instruction=system_instruction, thinking_config=thinking)
        except Exception:
            try:
                return types.GenerateContentConfig(system_instruction=system_instruction, thinking_config=types.ThinkingConfig(thinking_level="low"))
            except Exception:
                return types.GenerateContentConfig(system_instruction=system_instruction)
    else:
        kwargs = {"system_instruction": system_instruction}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return types.GenerateContentConfig(**kwargs)

def _gerar_com_retry(client, model, contents, config, tentativas=3):
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            ultimo_erro = e
            if not _eh_erro_transitorio_gemini(e) or tentativa == tentativas - 1:
                raise
            retry_after = _extrair_retry_after_segundos(str(e))
            espera = retry_after if retry_after is not None else (2 ** (tentativa + 1)) + random.uniform(0, 1.0)
            espera = min(espera, 20.0)
            time.sleep(espera)
    raise ultimo_erro

def _msg_erro_amigavel(e):
    texto = str(e)
    if "401" in texto or "Unauthorized" in texto or "403" in texto:
        return "🔑 **Chave inválida, sem permissão ou expirada.** Gere outra em aistudio.google.com/app/apikey e conecte novamente."
    if "404" in texto or "not found" in texto.lower():
        return "⚠️ **Modelo não encontrado (404).** O id 'gemini-3.5-flash' / 'gemini-3.8-flash' pode não estar liberado para sua chave/região. Teste 'gemini-2.5-flash' em Ferramentas Avançadas ou aguarde liberação."
    if "429" in texto or "quota" in texto.lower() or "resource exhausted" in texto.lower():
        return "⏳ **Limite de uso da API atingido (429/Quota).** Sua cota gratuita para esta chave acabou. Troque a chave, aguarde o reset (24h) ou use outra conta."
    if "503" in texto or "overloaded" in texto.lower() or "unavailable" in texto.lower():
        return "🔌 **Servidores do Google sobrecarregados (503).** O código já tentou 3 vezes com backoff. Se persiste por minutos/horas: é sobrecarga regional da Google ou modelo em rollout — tente 'gemini-2.5-flash' como fallback, troque de chave/projeto ou aguarde 5-10 min."
    return f"⚠️ **Erro Sistémico:** {texto[:500]}"

def verificar_acesso_sheets(email):
    try:
        params = {"acao": "verificar_acesso", "email": (email or "").strip().lower()}
        response = _request_with_retry(
            "GET", APPS_SCRIPT_URL.strip(), params=params, timeout=15,
            allow_redirects=True
        )
        if response.status_code == 200:
            dados = response.json()
            if not dados.get("encontrado", False): return False, dados.get("expiracao", ""), "⚠️ E-mail não encontrado."
            exp = str(dados.get("expiracao", "")).strip()
            if exp:
                exp_candidatos = [exp.strip(), exp.split("T")[0].strip()]
                if " " in exp and "T" not in exp:
                    exp_candidatos.append(exp.split(" ")[0].strip())
                data_expiracao = None
                for cand in exp_candidatos:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                        try:
                            data_expiracao = datetime.strptime(cand, fmt).date()
                            break
                        except Exception:
                            continue
                    if data_expiracao is not None:
                        break
                if data_expiracao is None:
                    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                        try:
                            data_expiracao = datetime.strptime(exp.replace("T", " ").strip(), fmt).date()
                            break
                        except Exception:
                            continue
                if data_expiracao is not None and data_expiracao < datetime.now().date():
                    return False, exp, f"⚠️ Acesso expirou em {exp}."
            return True, exp, None
        return False, "", f"⚠️ Erro do servidor {response.status_code}."
    except Exception as e: return False, "", f"⚠️ Falha na conexão: {e}"

# ==============================================================================
# 3. MOTORES PURE-CORE (SEPARADOS)
# ==============================================================================
SYS_GERADOR_PREPROMPT = r"""Você é o Diretor de Arte Óptica e Composição Visual do Prompt Studio.
Gere um PRÉ-PROMPT visual completo, cinematográfico e coeso em Português a partir da ideia do usuário.
REGRAS MANDATÓRIAS:
1. PRESERVAÇÃO: Preserve nomes de personagens, franquias, gênero e ações informadas.
2. ZERO FLUFF: Adicione somente o que uma câmera captaria. É ESTRITAMENTE PROIBIDO usar metáforas.
3. SAÍDA EXCLUSIVA: Responda APENAS com a descrição visual coesa em Português."""

SYS_COMPOSITOMETRO = r"""Você é o Auditor Óptico e Analista de Composição do Prompt Studio.
Retorne EXCLUSIVAMENTE um JSON válido no formato:
{"sujeito_status": "Definido | Vago | Ausente", "sujeito_resumo": "resumo do sujeito", "acao_status": "Presente | Estática | Ausente", "cenario_status": "Definido | Vago | Ausente", "iluminacao_status": "Definida | Inferida pela IA", "camera_status": "Definida | Inferida pela IA", "nivel_sensualidade_sugerido": 1, "diagnostico_texto": "breve diagnostico", "sugestoes_cirurgicas": [ "sugestão 1", "sugestão 2" ]}"""

SYS_LEITOR_PARAMETRICO = r"""Você é o Motor de Extração Óptica de Ultra-Densidade (nível Dense Captioning) do Prompt Studio.
Sua missão é realizar uma varredura microscópica da imagem e desconstruí-la com precisão forense. Não resuma.

REGRAS DE EXTRAÇÃO:
1. SUJEITO: Especifique etnia, formato do rosto, cor exata dos olhos e micro-expressões. Descreva a roupa detalhando os materiais (ex: couro sintético, látex reflexivo), texturas, costuras, logotipos, caimento, dobras e acessórios.
2. AÇÃO/POSE: Mapeie a geometria corporal exata.
3. CENÁRIO: Divida em Foreground, Midground e Background.
4. ILUMINAÇÃO: Mapeie a luz principal, sombras e reflexos especulares.
5. CÂMERA: Infira a lente aproximada, desfoque e ângulo.

Retorne EXCLUSIVAMENTE um JSON válido neste formato:
{"sujeito": "...", "acao": "...", "cenario": "...", "iluminacao": "...", "estilo_camera": "..."}"""

SYS_MESTRE_CORE = r"""Você é o Motor de Síntese Óptica e Engenharia de Prompts do Prompt Studio.
Sua missão é compilar o prompt na sintaxe do motor destino com FIDELIDADE ABSOLUTA.

=============================================================================
1. TRADUÇÃO JURAMENTADA DA CENA (REGRA DE OURO)
=============================================================================
- Extraia 100% das informações da NARRATIVA VISUAL (Sujeito, Roupa, Cenário, Luz) e aplique-as no prompt em inglês.

=============================================================================
2. INJEÇÃO DE TAGS RATING E SENSUALIDADE
=============================================================================
- Nível 1/2: 'rating_safe'
- Nível 3/4: 'rating_questionable, nsfw'
- Nível 5: 'rating_explicit, nude, nsfw, uncensored'

=============================================================================
3. NEGATIVO DINÂMICO (OBRIGATÓRIO E PROFUNDO)
=============================================================================
NUNCA entregue um prompt negativo superficial apenas com a base fixa do motor.
- INJETE DINAMICAMENTE tags opostas que estragariam o resultado.
- Ex: Se positivo é fotorrealista, o negativo DEVE ter 'anime, cartoon, 3d render, illustration'.
- Junte o seu 'Negativo Dinâmico' com a base fixa da Regra do Motor.
"""

def _chamar_motor_visao(arquivo_imagem, estilo_conversao, nivel_sensualidade, modelo_gemini=None):
    """
    PRIMEIRO GEMINI (Motor de Visão):
    Responsabilidade: Extração óptica pericial de imagens.
    Usa OBRIGATORIAMENTE a Chave de Visão e o modelo gemini-3.5-flash.
    """
    MAX_IMAGE_SIZE_MB = 10
    if arquivo_imagem.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise RuntimeError(f"🖼️ Imagem limite: {MAX_IMAGE_SIZE_MB} MB.")
    
    # 1. Isolamento da Chave de API de Visão
    config = carregar_config(st.session_state.get("user_email", ""))
    chave_visao = st.session_state.get("input_key_visao", "").strip() or config.get("chaves", {}).get("Chave Visao", "")
    
    if not chave_visao or genai is None:
        raise RuntimeError("Nenhuma chave configurada para Visão. Adicione a 'Chave Gemini (Visão)' no painel lateral.")
    
    # 2. Definição estrita do modelo do Primeiro Gemini
    modelo_primeiro_gemini = "gemini-3.5-flash"
    
    # 3. Construção do Prompt de Extração
    user_prompt = f"Desconstrua pericialmente esta imagem em Ultra-Densidade. \n[MODIFICADOR 2: SENSUALIDADE]: Nível {nivel_sensualidade}."
    if "Fotorrealismo" in estilo_conversao: 
        user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza para o MUNDO REAL fotorrealista."
    elif "Anime" in estilo_conversao: 
        user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza para ILUSTRAÇÃO 2D ANIME."

    try:
        arquivo_imagem.seek(0)
        img_pil = Image.open(arquivo_imagem)
        # Normaliza imagem grande (evita payload >4MB que gera 503 em free tier)
        try:
            img_pil.load()
            max_lado = 1536
            if max(img_pil.size) > max_lado:
                ratio = max_lado / max(img_pil.size)
                novo = (int(img_pil.size[0] * ratio), int(img_pil.size[1] * ratio))
                img_pil = img_pil.resize(novo, Image.LANCZOS)
            if img_pil.mode not in ("RGB", "RGBA"):
                img_pil = img_pil.convert("RGB")
        except Exception:
            pass
        
        # 4. Instanciação e Chamada (Cliente Isolado) com retry 503/429
        client = genai.Client(api_key=chave_visao)
        cfg = _build_gemini_config(SYS_LEITOR_PARAMETRICO, modelo_primeiro_gemini, temperature=0.2)
        
        resp = _gerar_com_retry(client, modelo_primeiro_gemini, [img_pil, user_prompt], cfg)
        
        texto = getattr(resp, "text", "") or ""
        if not texto.strip(): 
            raise RuntimeError("A IA bloqueou a imagem por políticas de segurança.")
        
        # 5. Validação e Retorno (Mantém a compatibilidade com a UI do Passo 2)
        dados = parse_json_ia(texto)
        if dados: 
            return {"tipo": "json", "dados": dados}
        return {"tipo": "texto", "texto": texto}
        
    except Exception as e:
        raise RuntimeError(f"Falha no Primeiro Gemini (Leitura Óptica): {str(e)}")


def _chamar_motor_texto(system_prompt, user_prompt, modelo_gemini=None, temperature=0.25):
    """
    SEGUNDO GEMINI (Motor de Texto):
    Responsabilidade: Engenharia e Síntese de Prompts Textuais.
    Usa OBRIGATORIAMENTE a Chave de Texto e o modelo gemini-3.8-flash.
    """
    # 1. Isolamento da Chave de API de Texto
    config = carregar_config(st.session_state.get("user_email", ""))
    chave_texto = st.session_state.get("input_key_texto", "").strip() or config.get("chaves", {}).get("Chave Texto", "")

    if not chave_texto or genai is None:
        raise RuntimeError("Nenhuma chave configurada para Texto. Adicione a 'Chave Gemini (Texto)' no painel lateral.")

    # 2. Definição estrita do modelo do Segundo Gemini
    modelo_segundo_gemini = "gemini-3.8-flash"

    # 3. Proteção Anti-Cache (Injeção de Token Dinâmico)
    sys_final = f"{system_prompt}\n\n[REF-VERIF:{secrets.token_hex(8)}]"
    
    try:
        # 4. Instanciação e Chamada (Cliente Isolado) com retry 503/429
        client = genai.Client(api_key=chave_texto)
        cfg = _build_gemini_config(sys_final, modelo_segundo_gemini, temperature=temperature)
        
        resp = _gerar_com_retry(client, modelo_segundo_gemini, user_prompt, cfg)
        
        texto = getattr(resp, "text", "")
        texto = str(texto or "").strip()
        
        # 5. Validação e Retorno (Mantém compatibilidade com Passos 4 e 5)
        if texto and "[REF-VERIF:" not in texto: 
            return texto, "Gemini 3.8 (Texto Especializado)"
            
        raise RuntimeError("O modelo retornou uma resposta em branco.")
        
    except Exception as e: 
        raise RuntimeError(f"Falha no Segundo Gemini (Engenharia de Texto): {str(e)}")

# ==============================================================================
# 5. UI: BARRA LATERAL E HISTÓRICO
# ==============================================================================
def renderizar_sidebar():
    st.sidebar.markdown("<div style='font-size: 0.95rem; color: var(--ps-blue); font-weight: 700; margin-bottom: 1rem;'>A porta é nossa, mas as chaves são suas.</div>", unsafe_allow_html=True)
    st.sidebar.markdown("## ⚙️ Centro de Conexão")
    
    user_email_masked = mascarar_email(st.session_state.get('user_email', ''))
    st.sidebar.caption(f"Usuário: **{user_email_masked}**")
    
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    config = carregar_config(st.session_state.get("user_email", ""))
    st.sidebar.markdown("---")
    # Inicializa estado dos widgets antes de criá-los (corrige bug value+key do Streamlit)
    _cfg_visao = config.get("chaves", {}).get("Chave Visao", "")
    _cfg_texto = config.get("chaves", {}).get("Chave Texto", "")
    _cfg_modelo = config.get("modelo_padrao", "gemini-1.5-flash")
    # Só inicializa na primeira vez ou se veio de troca de usuário; não sobrescreve digitação em andamento
    _email_sess = st.session_state.get("user_email", "")
    if st.session_state.get("_sidebar_init_email") != _email_sess or "input_key_visao" not in st.session_state:
        st.session_state["input_key_visao"] = _cfg_visao
        st.session_state["input_key_texto"] = _cfg_texto
        st.session_state["modelo_geral_select"] = _cfg_modelo
        st.session_state["_sidebar_init_email"] = _email_sess
    
    st.sidebar.markdown("<a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#059669; text-decoration:none;'>👁️ Google Gemini (Via Visão)</a>", unsafe_allow_html=True)
    st.sidebar.caption("Chave dedicada para leitura de imagens.")
    k_visao = st.sidebar.text_input("Chave Visão", type="password", key="input_key_visao", label_visibility="collapsed")
    
    st.sidebar.markdown("<br><a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#2563eb; text-decoration:none;'>📝 Google Gemini (Via Texto)</a>", unsafe_allow_html=True)
    st.sidebar.caption("Chave dedicada para gerar os Prompts Finais.")
    k_texto = st.sidebar.text_input("Chave Texto", type="password", key="input_key_texto", label_visibility="collapsed")

    with st.sidebar.expander("Ferramentas Avançadas", expanded=False):
        st.caption("Insira o nome exato do modelo (Ex: gemini-1.5-flash ou gemini-2.5-flash):")
        modelo_geral = st.text_input("Modelo Base (Ambas as vias)", key="modelo_geral_select")

    if st.sidebar.button("💾 Conectar Motores Isolados", type="primary", use_container_width=True):
        dados_salvos = {
            "chaves": {"Chave Visao": k_visao, "Chave Texto": k_texto}, 
            "modelo_padrao": modelo_geral.strip()
        }
        ok_salvo, erro_salvo = salvar_config(dados_salvos, st.session_state.get("user_email", ""))
        if ok_salvo: st.sidebar.success("✅ Motores conectados com sucesso!")
        else: st.sidebar.warning(f"⚠️ {erro_salvo}")

def _historico_sheets(email, prompt_texto=None, acao="listar"):
    email = (email or "").strip().lower()
    if acao == "adicionar":
        if not prompt_texto or not str(prompt_texto).strip(): return False, "Nenhum prompt."
        MAX_HISTORY_CHARS = 25000
        truncado = len(str(prompt_texto)) > MAX_HISTORY_CHARS
        payload = { "acao": "adicionar_historico", "email": email, "prompt": str(prompt_texto)[:MAX_HISTORY_CHARS], "_truncado": truncado }
        try:
            resp = _request_with_retry(
                "POST", APPS_SCRIPT_URL.strip(), json=payload, timeout=30,
                allow_redirects=True
            )
            if resp.status_code == 200 and resp.json().get("ok"): return True, None
        except Exception as e: return False, f"Falha de conexão: {e}"
        return False, "Erro ao processar."
    params = {"acao": "listar_historico", "email": email}
    resp = _req_apps_script(params, timeout=20)
    if resp and resp.get("ok"): return True, resp.get("itens", [])
    return False, []

@st.dialog("📝 Visualizador de Prompt (Histórico)")
def modal_historico(conteudo):
    st.info("Utilize o ícone de 'Copiar' no canto superior direito do bloco de código abaixo.")
    st.code(conteudo, language="markdown")
    st.download_button("📥 Baixar este Prompt (.txt)", data=conteudo, file_name=f"prompt_historico_{int(time.time())}.txt", use_container_width=True)

def renderizar_historico():
    with st.sidebar.expander("🕘 Histórico de Prompts", expanded=False):
        ok, itens = _historico_sheets(st.session_state.get("user_email", ""), acao="listar")
        if not ok: st.caption("Histórico indisponível."); return
        if not itens: st.caption("Nenhum prompt salvo ainda."); return
        for item in itens[-10:]:
            ts = item.get("quando", "")[:16]
            preview = str(item.get("prompt", ""))[:60].replace("\n", " ")
            if st.button(f"{ts} — {preview}...", key=f"hist_{item.get('id', ts)}", use_container_width=True):
                modal_historico(item.get("prompt", ""))

# ==============================================================================
# 6. UI: COCKPIT PRINCIPAL (FUNIL UX 5 PASSOS COM STATE SYNC)
# ==============================================================================
def renderizar_cockpit():
    st.markdown("<div class='ps-kicker'>PROMPT STUDIO COCKPIT · ATRITO ZERO</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='ps-title'>Sua Ideia. Seu Motor. Controle Total.</h1>", unsafe_allow_html=True)
    st.markdown("<div class='ps-slogan'>A porta é nossa, mas as chaves são suas.</div>", unsafe_allow_html=True)

    # Aplicar valores pendentes agendados no run anterior (evita StreamlitAPIException ao alterar widget após criação)
    for _pk, _rk in [
        ("_pending_ck_ideia_input", "ck_ideia_input"),
        ("_pending_ck_preprompt_editado", "ck_preprompt_editado"),
        ("_pending_img_suj", "img_suj"),
        ("_pending_img_cen", "img_cen"),
        ("_pending_img_act", "img_act"),
        ("_pending_img_ilu", "img_ilu"),
        ("_pending_img_est", "img_est"),
    ]:
        if _pk in st.session_state:
            st.session_state[_rk] = st.session_state.pop(_pk)
    # Inicialização das chaves de memória ancoradas (State Sync Seguro)
    if "ck_ideia_input" not in st.session_state: st.session_state.ck_ideia_input = ""
    if "ck_preprompt_editado" not in st.session_state: st.session_state.ck_preprompt_editado = ""
    if "img_suj" not in st.session_state: st.session_state.img_suj = ""
    if "img_cen" not in st.session_state: st.session_state.img_cen = ""
    if "img_act" not in st.session_state: st.session_state.img_act = ""
    if "img_ilu" not in st.session_state: st.session_state.img_ilu = ""
    if "img_est" not in st.session_state: st.session_state.img_est = ""
    # Defaults dos modificadores antes do Passo 2 (garante leitura consistente na extração óptica)
    if "ck_estilo_conversao" not in st.session_state: st.session_state.ck_estilo_conversao = "Manter Estilo Original"
    if "ck_foco_contexto" not in st.session_state: st.session_state.ck_foco_contexto = "Harmônico (Preencher/Embelezar)"
    if "ck_sens_slider" not in st.session_state: st.session_state.ck_sens_slider = OPCOES_SENSUALIDADE[1]
    
    # --------------------------------------------------------------------------
    # PASSO 1: A IDEIA (Texto Base)
    # --------------------------------------------------------------------------
    st.markdown("### 1️⃣ Passo 1: A Sua Ideia (A Narrativa Visual)")
    st.caption("O ponto de partida. Descreva o que imagina ou veja a caixa preencher-se magicamente usando o Passo 2.")
    
    # Caixa de texto ligada diretamente à chave interna do Streamlit
    st.text_area("Insira a sua Ideia:", key="ck_ideia_input", height=140, label_visibility="collapsed")

    if st.button("🗑️ Limpar Ideia", use_container_width=False):
        for k in ["ck_img_parametros", "ck_preprompt", "ck_preprompt_editado", "ck_diagnostico", "ck_prompt_final", "ck_sugestoes_marcadas",
                  "ck_ideia_input", "img_suj", "img_cen", "img_act", "img_ilu", "img_est",
                  "_pending_ck_ideia_input", "_pending_ck_preprompt_editado", "_pending_img_suj", "_pending_img_cen", "_pending_img_act", "_pending_img_ilu", "_pending_img_est"]:
            st.session_state.pop(k, None)
        # Agenda valores limpos para o próximo run (evita StreamlitAPIException)
        st.session_state["_pending_ck_ideia_input"] = ""
        st.session_state["_pending_ck_preprompt_editado"] = ""
        st.session_state["_pending_img_suj"] = ""
        st.session_state["_pending_img_cen"] = ""
        st.session_state["_pending_img_act"] = ""
        st.session_state["_pending_img_ilu"] = ""
        st.session_state["_pending_img_est"] = ""
        st.rerun()

    # --------------------------------------------------------------------------
    # PASSO 2: REFERÊNCIA ÓPTICA (Imagem Opcional)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 2️⃣ Passo 2: Referência Óptica (Opcional)")
    st.caption("Sem inspiração para escrever? Faça upload de uma imagem. A Via de Visão extrairá os micro-detalhes para o Passo 1.")
    
    col_img1, col_img2 = st.columns([4, 6])
    with col_img1: 
        img_file = st.file_uploader("Upload de Referência", type=["png", "jpg", "jpeg", "webp"], key="ck_img_uploader", label_visibility="collapsed")
    with col_img2:
        st.write(" ")
        btn_ler = st.button("👁️ Extrair Imagem (Motor de Visão)", use_container_width=True)

    if btn_ler:
        if not img_file: st.warning("Selecione uma imagem primeiro.")
        else:
            with st.spinner("Analisando matriz óptica com Varredura Ultra-Densa..."):
                try:
                    modelo_base = st.session_state.get("modelo_geral_select", "gemini-1.5-flash")
                    estilo_conversao = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                    sens_escolhida = st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1])
                    
                    res = _chamar_motor_visao(img_file, estilo_conversao, sens_escolhida, modelo_base)
                    
                    if res["tipo"] == "json":
                        st.session_state["ck_img_parametros"] = res["dados"]
                        # Agenda para o próximo run (evita StreamlitAPIException: widget já instanciado)
                        st.session_state["_pending_img_suj"] = res["dados"].get("sujeito", "")
                        st.session_state["_pending_img_cen"] = res["dados"].get("cenario", "")
                        st.session_state["_pending_img_act"] = res["dados"].get("acao", "")
                        st.session_state["_pending_img_ilu"] = res["dados"].get("iluminacao", "")
                        st.session_state["_pending_img_est"] = res["dados"].get("estilo_camera", "")
                        ideia_extraida = f"Sujeito: {res['dados'].get('sujeito','')}\n\nAção: {res['dados'].get('acao','')}\n\nCenário: {res['dados'].get('cenario','')}\n\nIluminação: {res['dados'].get('iluminacao','')}\n\nEstilo: {res['dados'].get('estilo_camera','')}"
                        st.session_state["_pending_ck_ideia_input"] = ideia_extraida
                    else:
                        st.session_state["_pending_ck_ideia_input"] = res["texto"]
                        st.session_state.pop("ck_img_parametros", None)
                        
                    st.session_state.pop("ck_preprompt", None)
                    st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if st.session_state.get("ck_img_parametros"):
        with st.expander("🔬 Detalhador Pericial Extraído (Editável)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("👤 Sujeito:", key="img_suj", height=150)
                st.text_area("🏞️ Cenário:", key="img_cen", height=150)
            with c2:
                st.text_area("🏃 Ação:", key="img_act", height=100)
                st.text_area("💡 Iluminação:", key="img_ilu", height=100)
                st.text_area("📷 Estilo:", key="img_est", height=100)
            if st.button("🔄 Atualizar Caixa da Ideia com estas edições", use_container_width=True):
                nova_ideia = f"Sujeito: {st.session_state.img_suj}\n\nAção: {st.session_state.img_act}\n\nCenário: {st.session_state.img_cen}\n\nIluminação: {st.session_state.img_ilu}\n\nEstilo: {st.session_state.img_est}"
                st.session_state["_pending_ck_ideia_input"] = nova_ideia
                st.rerun()

    # --------------------------------------------------------------------------
    # PASSO 3: MODIFICADORES
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 3️⃣ Passo 3: Modificadores Globais")
    st.caption("ℹ️ *Aviso: Estes filtros guiam a geração do seu prompt final. (Também alteram a leitura caso envie uma Imagem no Passo 2).*")
    
    with st.container(border=True):
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: estilo_conversao = st.selectbox("Estilo de Arte:", ["Manter Estilo Original", "📸 Converter para Fotorrealismo", "🎨 Converter para Anime"], key="ck_estilo_conversao")
        with col_m2: foco_contexto = st.selectbox("Foco e Contexto:", ["Harmônico (Preencher/Embelezar)", "Literal (Direto, Sem Floreios)"], key="ck_foco_contexto")
        with col_m3: sens_escolhida = st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider", value=st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1]))

    # --------------------------------------------------------------------------
    # PASSO 4: RASCUNHO E VALIDAÇÃO (Opcionais Prévios)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 4️⃣ Passo 4: Rascunho & Validação (Opcional)")
    col_b1, col_b2 = st.columns(2)
    with col_b1: btn_pre = st.button("👁️ Rascunhar Cena (Via Motor de Texto)", use_container_width=True)
    with col_b2: btn_ava = st.button("🔍 Auditar no Compositômetro (Raio-X)", use_container_width=True)

    if btn_pre:
        if not st.session_state.ck_ideia_input.strip(): st.warning("Escreva a sua Ideia no Passo 1.")
        else:
            with st.spinner("Desenhando a cena com o Motor de Texto..."):
                try:
                    p = f"IDEIA:\n{st.session_state.ck_ideia_input}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sens_escolhida}']"
                    if "Literal" in foco_contexto: p += "\n[AGENTE LITERAL]: Seja 100% fiel, sem floreios estéticos inúteis."
                    modelo_base = st.session_state.get("modelo_geral_select", "gemini-1.5-flash")
                    txt, prov = _chamar_motor_texto(SYS_GERADOR_PREPROMPT, p, modelo_gemini=modelo_base)
                    
                    st.session_state["ck_ideia_hist_fix"] = st.session_state.ck_ideia_input
                    st.session_state["ck_preprompt"] = txt
                    st.session_state["_pending_ck_preprompt_editado"] = txt 
                    st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if btn_ava:
        if not st.session_state.ck_ideia_input.strip(): st.warning("Escreva a sua Ideia no Passo 1.")
        else:
            with st.spinner("Raio-X em andamento com o Motor de Texto..."):
                try:
                    modelo_base = st.session_state.get("modelo_geral_select", "gemini-1.5-flash")
                    txt, prov = _chamar_motor_texto(SYS_COMPOSITOMETRO, f"AVALIE:\n{st.session_state.ck_ideia_input}", modelo_gemini=modelo_base)
                    diag = parse_json_ia(txt)
                    if not diag: st.error("⚠️ Erro de formato no Raio-X. Tente novamente.")
                    else: st.session_state["ck_diagnostico"] = diag; st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if st.session_state.get("ck_preprompt"):
        st.markdown("<div class='ps-legend'><span><span class='ps-user-word'>Ideia Original</span></span> • <span><span class='ps-ai-word'>Ajuste da IA</span></span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ps-preprompt'>{_ps_markup_origin(st.session_state['ck_preprompt'], st.session_state.get('ck_ideia_hist_fix', ''))}</div>", unsafe_allow_html=True)
        
        st.text_area("Ajuste fino do Rascunho (Esta caixa substituirá a Ideia para o Motor Final):", key="ck_preprompt_editado", height=130)

    diag = st.session_state.get("ck_diagnostico")
    if diag:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns(5)
            def _bdg(s): return ("comp-green","✓") if s in ["Definido","Presente"] else ("comp-amber","!") if s in ["Vago","Estática"] else ("comp-blue","⚙️")
            for col, key, label in zip([c1,c2,c3,c4,c5], ["sujeito_status","acao_status","cenario_status","iluminacao_status","camera_status"], ["Sujeito","Ação","Cenário","Luz","Câmera"]):
                cl, ic = _bdg(diag.get(key, ""))
                col.markdown(f"<div class='comp-badge {cl}'>{ic} {label}: {diag.get(key, 'Pendente')}</div>", unsafe_allow_html=True) 
            
            if diag.get("diagnostico_texto"): st.caption(f"ℹ️ **Diagnóstico:** {diag.get('diagnostico_texto')}")
            sugestoes = diag.get("sugestoes_cirurgicas", [])
            if sugestoes:
                st.markdown("##### ✨ Sugestões Cirúrgicas Opcionais (Ajudam o Motor):")
                selecionadas = []
                for idx, sug in enumerate(sugestoes):
                    if st.checkbox(sug, key=f"sug_chk_{idx}"): selecionadas.append(sug)
                st.session_state["ck_sugestoes_marcadas"] = selecionadas
            else: st.session_state["ck_sugestoes_marcadas"] = []

    # --------------------------------------------------------------------------
    # PASSO 5: MOTOR E SÍNTESE
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 5️⃣ Passo 5: Motor Destino & Síntese Final")
    col_dest1, col_dest2 = st.columns([6, 4])
    with col_dest1: dest_sel = st.selectbox("Selecione a Plataforma de Imagem Alvo:", OPCOES_DESTINO, index=0, key="ck_destino_select")
    with col_dest2: 
        st.write("")
        st.write("")
        btn_exec = st.button("⚡ Gerar Código do Prompt", type="primary", use_container_width=True)

    if btn_exec:
        if dest_sel == "Selecione o Motor Destino...": st.error("🛑 Pare! Selecione para qual motor de IA este prompt será compilado.")
        elif not st.session_state.ck_ideia_input.strip(): st.warning("Descreva a sua Ideia no Passo 1 antes de gerar.")
        else:
            with st.spinner(f"Compilando sintaxe ultra-otimizada para {dest_sel}..."):
                try:
                    eng = BANCO_DE_MOTORES[dest_sel]
                    bloco = f"\n\n======================================\n3. SINTAXE NATIVA: {dest_sel}\n======================================\n- POSITIVO: {eng['regra_positivo']}\n- NEGATIVO FIXO: {eng.get('regra_negativo', 'N/A')}\n\nSAÍDA OBRIGATÓRIA:\n1. PROMPT (ENGLISH)\n2. NEGATIVE PROMPT DINÂMICO (ENGLISH)\n3. LEGENDA\n4. HASHTAGS\n💡 DICA TÉCNICA: {eng['dica_tecnica']}"
                    
                    txt_b = st.session_state.ck_preprompt_editado if st.session_state.get("ck_preprompt") else st.session_state.ck_ideia_input
                    sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])
                    sug_str = "\n".join(f"- {s}" for s in sug_aceitas) if sug_aceitas else "Nenhuma sugestão."
                    
                    p = f"DESTINO: {dest_sel}\nRATING: {sens_escolhida}\n\n1. NARRATIVA VISUAL:\n{txt_b}\n\n2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}"
                    
                    if "Literal" in foco_contexto: p += "\n[MODO LITERAL ATIVADO]: Remova floreios da sintaxe final. Foque puramente na geometria física."
                    p += "\n\n⚠️ OBRIGATÓRIO: 'PROMPT' E 'NEGATIVE' EXCLUSIVAMENTE EM INGLÊS."

                    modelo_base = st.session_state.get("modelo_geral_select", "gemini-1.5-flash")
                    res, prov = _chamar_motor_texto(SYS_MESTRE_CORE + bloco, p, modelo_gemini=modelo_base)
                    
                    st.session_state["ck_prompt_final"] = res
                    st.session_state["ck_prov_usado"] = prov
                    st.session_state["ck_dest_usado"] = dest_sel
                    st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    # OUTPUT FINAL E DOWNLOADS
    if st.session_state.get("ck_prompt_final"):
        st.markdown("---")
        st.markdown(f"### 📋 Prompt Especializado ({st.session_state.get('ck_dest_usado')})")
        st.caption(f"Gerado via {st.session_state.get('ck_prov_usado')}")
        
        st.code(st.session_state["ck_prompt_final"], language="markdown")
            
        c_save1, c_save2 = st.columns(2)
        with c_save1:
            if st.button("💾 Salvar no Histórico em Nuvem", use_container_width=True):
                ok_hist, erro_hist = _historico_sheets(st.session_state.get("user_email", ""), st.session_state["ck_prompt_final"], acao="adicionar")
                if ok_hist: st.success("✅ Prompt salvo no histórico!")
                else: 
                    if erro_hist and "_truncado" in str(erro_hist): st.warning("⚠️ Prompt truncado no histórico (limite de 25.000 caracteres).")
                    else: st.warning(f"⚠️ {erro_hist or 'Não foi possível salvar.'}")
        with c_save2:
            st.download_button(
                label="📥 Baixar Prompt (.txt)", 
                data=st.session_state["ck_prompt_final"], 
                file_name=f"prompt_studio_{int(time.time())}.txt", 
                use_container_width=True
            )

# ==============================================================================
# 9. PONTO DE ENTRADA (VITRINE DINÂMICA E LOGIN)
# ==============================================================================
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    vitrines = [
        {"id": "Uma garota de anime com cabelo curto encostada na estante de uma biblioteca perto da janela.", "pr": "score_9, score_8_up, 1girl, solo, videl (dragon ball), short black hair, blue eyes, white t-shirt, black spandex shorts, green boots, leaning against bookshelf, window, sunlight, library, anime style, high quality, masterpiece.", "mt": "ComfyUI / Pony SDXL", "im": "carro.jpg"},
        {"id": "Uma mulher loira fotorrealista com blusa vermelha curta e saia jeans em uma escadaria de pedra.", "pr": "A breathtaking highly detailed photograph of a beautiful blonde woman with striking blue eyes, wearing a red long-sleeve crop top and a denim mini skirt. She is standing on ancient outdoor stone steps in a European village. Bright midday sunlight, cinematic lighting, photorealistic, 8k resolution, shot on 35mm lens --ar 4:5 --v 6.1 --stylize 250", "mt": "Midjourney v6.1+", "im": "elfa.jpg"}
    ]
    vit = random.choice(vitrines)

    st.markdown("<div class='hero-title'>Pare de lutar contra a IA.<br>Retome o controle.</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>O Prompt Studio Cockpit é a <b>IDE Profissional</b> (Interface de Desenvolvimento) para criadores de imagem. A porta é nossa, as chaves (BYOK) e o controle criativo são inteiramente seus. Sem filtros ocultos, sem taxas de API surpresa.</div>", unsafe_allow_html=True)

    st.markdown("<div class='showcase-box'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("<div class='label-ideia'>A Ideia Simples (Entrada)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='text-ideia'>\"{vit['id']}\"</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='label-prompt'>A Engenharia do Cockpit (Motor: {vit['mt']})</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='code-prompt'>{vit['pr']}</div>", unsafe_allow_html=True)
    with c2: st.image(vit['im'], use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    c_l1, c_l2, c_l3 = st.columns([1, 4, 1])
    with c_l2:
        st.markdown("<div class='plan-container'>", unsafe_allow_html=True)
        st.markdown("<div class='byok-badge'>🔒 Modelo BYOK: Conecte sua própria chave API após assinar.</div>", unsafe_allow_html=True)
        st.markdown("### 🚀 Acesse o Cockpit Agora")
        cp1, cp2, cp3 = st.columns(3)
        with cp1: st.link_button("15 Dias (R$ 14,99)", LINK_KIWIFY_15_DIAS, use_container_width=True)
        with cp2: st.link_button("30 Dias (R$ 29,99)", LINK_KIWIFY_30_DIAS, use_container_width=True)
        with cp3: st.link_button("90 Dias (R$ 59,99)", LINK_KIWIFY_90_DIAS, use_container_width=True)
        st.divider()
        email_login = st.text_input("E-mail Cadastrado na Kiwify:", key="login_email_cockpit", placeholder="seu-email@exemplo.com")
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            if not email_login.strip(): st.warning("Digite seu e-mail.")
            else:
                ok, exp, erro = verificar_acesso_sheets(email_login)
                if ok: st.session_state.update({"autenticado": True, "user_email": email_login.strip().lower(), "expiracao": exp}); st.rerun()
                else: st.error(erro or "Acesso não encontrado.")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    renderizar_sidebar()
    st.markdown("<div class='ps-brand'>PROMPT STUDIO COCKPIT</div>", unsafe_allow_html=True)
    st.markdown("<div class='ps-header-note'>IDE Paramétrica de Geração de Prompts (BYOK)</div>", unsafe_allow_html=True)
    renderizar_cockpit()
    renderizar_historico()
