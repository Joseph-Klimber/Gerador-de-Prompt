# -*- coding: utf-8 -*-
"""
Prompt Studio Cockpit — Interface Minimalista de Alta Precisão
Arquitetura: Shift-Left (Modificadores no Ponto Zero) + BYOK (Traga sua Chave) + Carga Distribuída.

v2.3 — Revisão Final Blindada:
  • Arquitetura Tri-Core Definitiva: Gemini 1 -> OpenRouter (Llama 70B Gratuito) -> Gemini 2
  • Leitura de Imagem Ultra-Densa (Dense Captioning) com redundância de chaves Gemini
  • Chaves criptografadas em repouso (Fernet) e persistência via Google Sheets
  • URLs ofuscadas via concatenação (Anti-bug de Markdown)
  • Interface polida com st.text_area dinâmico para edição forense
"""

import os
import json
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
    
    /* CSS NATIVO STREAMLIT (ADAPTA AO MODO CLARO E ESCURO) */
    .ps-brand { color: var(--text-color); font-size: 1.15rem; font-weight: 800; letter-spacing: .15em; margin-top: .2rem; }
    .ps-header-note { color: var(--text-color); opacity: 0.7; font-size: .88rem; margin-bottom: 1.1rem; }
    .ps-kicker { color: var(--ps-blue); font-size: .75rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-top: .4rem; }
    .ps-title { color: var(--text-color); font-size: clamp(1.8rem, 3.2vw, 2.7rem); line-height: 1.15; margin: .2rem 0 .4rem; font-weight: 800; }
    .ps-subtitle { color: var(--text-color); opacity: 0.8; font-size: 1.02rem; max-width: 820px; margin-bottom: 1.2rem; }
    
    /* Vitrine Landing Page Dinâmica */
    .hero-title { font-size: 3.5rem; font-weight: 900; color: var(--text-color); line-height: 1.1; margin-bottom: 1rem; text-align: center; letter-spacing: -0.03em; }
    .hero-subtitle { font-size: 1.2rem; color: var(--text-color); opacity: 0.8; text-align: center; max-width: 700px; margin: 0 auto 3rem auto; line-height: 1.6; }
    .showcase-box { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 16px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    .label-ideia { font-size: 0.8rem; font-weight: 800; color: #2563eb; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .text-ideia { font-size: 1.1rem; color: var(--text-color); font-style: italic; border-left: 4px solid #2563eb; padding-left: 1rem; margin-bottom: 1.5rem; }
    .label-prompt { font-size: 0.8rem; font-weight: 800; color: #b45309; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .code-prompt { background: var(--background-color); padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem; color: var(--text-color); height: 180px; overflow-y: auto; border: 1px solid rgba(128,128,128,0.2); }
    .plan-container { text-align: center; background: var(--secondary-background-color); padding: 2rem; border-radius: 16px; border: 1px solid rgba(128,128,128,0.2); margin-top: 2rem; }
    .byok-badge { display: inline-block; background: rgba(37, 99, 235, 0.1); color: #2563eb; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: bold; margin-bottom: 1rem; border: 1px solid rgba(37, 99, 235, 0.2); }

    /* Pré-prompt e Tags (App Interno) */
    .ps-preprompt { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 12px; padding: 1.25rem 1.4rem; line-height: 1.85; font-size: 1.02rem; color: var(--text-color); margin: 0.8rem 0 1.2rem; }
    .ps-user-word { color: var(--text-color); font-weight: 700; background-color: rgba(37, 99, 235, 0.15); border-left: 2px solid #2563eb; padding: 2px 6px; border-radius: 4px; }
    .ps-ai-word { color: var(--ps-gold); font-weight: 600; }
    .ps-legend { display: flex; gap: 1.5rem; margin: .6rem 0 .9rem; font-size: .88rem; font-weight: 600; align-items: center; }
    
    /* Banners */
    .comp-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 700; padding: 4px 10px; border-radius: 9999px; margin-right: 6px; margin-bottom: 6px; }
    .comp-green { background-color: rgba(5, 150, 105, 0.1); color: #10b981; border: 1px solid rgba(5, 150, 105, 0.3); }
    .comp-amber { background-color: rgba(217, 119, 6, 0.1); color: #f59e0b; border: 1px solid rgba(217, 119, 6, 0.3); }
    .comp-blue  { background-color: rgba(37, 99, 235, 0.1); color: #3b82f6; border: 1px solid rgba(37, 99, 235, 0.3); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CONSTANTES E DICIONÁRIO (COM BLINDAGEM DE URL)
# ==============================================================================
APPS_SCRIPT_URL = "http" + "s://script.google.com/macros/s/AKfycbzgEj3YPwqiUbiueyu8wjZ9ZZK0Rcc6G3kucysRSJ2gNmzRzUdMuLqv_q55N1kSO8PQ/exec"
LINK_KIWIFY_15_DIAS = "http" + "s://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "http" + "s://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "http" + "s://pay.kiwify.com.br/xo0m3rF"

PASTA_CONFIGS = "configs_usuarios"
PASTA_RESULTADOS = "resultados"
HISTORICO_LIMITE = 20

OPCOES_SENSUALIDADE = [
    "1 - Seguro (SFW)",
    "2 - Menos Seguro",
    "3 - Ecchi Leve",
    "4 - Ecchi",
    "5 - Picante",
    "6 - Dual (Com & Sem Censura)",
]

# DICIONÁRIO BLINDADO ANTI-ALUCINAÇÃO
BANCO_DE_MOTORES = {
    "ComfyUI / Pony SDXL": {
        "regra_positivo": "PRIMEIRO, extraia o sujeito e a roupa da narrativa visual. Ordem de Tags OBRIGATÓRIA: 1. Qualidade (score_9, score_8_up) -> 2. CONTAGEM E GÊNERO (ex: 1boy, solo, ou 1girl, solo) -> 3. PROFISSÃO/ESPÉCIE (ex: astronaut) -> 4. Vestuário fiel à narrativa -> 5. Ação -> 6. Cenário. NUNCA invente gêneros ou pessoas que não estão na narrativa original.",
        "regra_negativo": "BASE INEGOCIÁVEL: score_6, score_5, score_4, score_3, score_2, score_1, worst quality, low quality, normal quality, text, watermark, jpeg artifacts, ugly, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, mutated, deformed, out of frame. Se fotorrealista adicione: source_anime, source_cartoon, 3d.",
        "dica_tecnica": "Modelos baseados no Pony dependem estritamente da tag de gênero no início (ex: 1girl, solo)."
    },
    "ComfyUI / Illustrious": {
        "regra_positivo": "Traduza fielmente a cena. PREFIXO OBRIGATÓRIO: masterpiece, best quality, ultra-detailed, illustration. Logo em seguida, adicione OBRIGATORIAMENTE a contagem e gênero do sujeito (ex: 1boy, solo, ou 1girl, multiple girls). Não alucine elementos ausentes no texto.",
        "regra_negativo": "Base: lowres, bad quality, worst quality, bad anatomy, bad hands, text, error, missing fingers, cropped, signature, watermark. Remova 'blurry' se houver foco ou depth of field no positivo.",
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
        "dica_tecnica": "Não sobreponha a estética ao sujeito. O sujeito deve ser a primeira coisa no prompt."
    },
    "ComfyUI / SDXL Base Natural": {
        "regra_positivo": "Traduza a cena integralmente. FÓRMULA: 'A breathtaking photo of [Sujeito + Roupas fiéis], who is [Ação], located in [Cenário Detalhado]. The lighting is [Iluminação]. Shot on [Câmera]'.",
        "regra_negativo": "Base: ugly, deformed, poorly drawn, bad anatomy, missing limbs, mutated hands, unnatural proportions, amateur, watermark.",
        "dica_tecnica": "Refiner em 20% ajuda nos detalhes de rostos."
    },
    "Ideogram 4": {
        "regra_positivo": "Traduza a cena com foco em diagramação e design. Qualquer texto escrito solicitado DEVE ficar ENTRE ASPAS DUPLAS (ex: wearing a shirt that says \"HELLO\").",
        "regra_negativo": None,
        "dica_tecnica": "Perfeito para criar placas, logos e textos perfeitamente legíveis."
    },
    "Krea 2": {
        "regra_positivo": "Traduza a cena dividindo a estrutura mentalmente: Foreground (primeiro plano), Midground, Background. Palavras em inglês com forte impacto.",
        "regra_negativo": "blurry, low quality, deformed geometry, muddy colors, bad proportions, unnatural lighting.",
        "dica_tecnica": "Otimizado para a engine de upscaling e latência zero do Krea."
    },
    "Qwen / Tongyi Wanxiang": {
        "regra_positivo": "Traduza para um inglês estruturado: Sujeito -> Ação -> Ambiente. Evite jargões exaustivos de lente. Seja literal e direto ao ponto.",
        "regra_negativo": "poor quality, bad anatomy, watermark, text, out of frame, mutation.",
        "dica_tecnica": "Modelos Qwen asiáticos respondem melhor à clareza do que à estética carregada."
    },
    "Ernie (ViLG)": {
        "regra_positivo": "Traduza a cena recebida de forma clara em inglês, especificando a relação de proximidade espacial entre sujeito e cenário. Use termos de arte tradicionais.",
        "regra_negativo": "ugly, disfigured, low resolution, bad hands, deformed faces.",
        "dica_tecnica": "Baidu Ernie prefere prompts físicos diretos. Evite metáforas."
    },
    "Z-Image": {
        "regra_positivo": "Traduza a narrativa para um inglês hiper-realista. Foque na coerência do sujeito informado e adicione texturas 8k e iluminação volumétrica.",
        "regra_negativo": "noisy, oversaturated, unrealistic, bad anatomy, bad lighting, watermark.",
        "dica_tecnica": "Z-Image processa bem materiais reflexivos e texturas."
    }
}

OPCOES_DESTINO = ["Selecione o Motor Destino..."] + list(BANCO_DE_MOTORES.keys())

# ==============================================================================
# 2.1 FUNÇÕES PURAS (testáveis) + CRIPTOGRAFIA + PERSISTÊNCIA
# ==============================================================================
def _slug_usuario(email):
    return re.sub(r'[^\w\-.]', '_', (email or "anonimo").strip().lower()) or "anonimo"

def normalizar_texto(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )

def parse_json_ia(texto):
    if not texto: return None
    limpo = str(texto).strip().strip("`")
    if limpo.lower().startswith("json"): limpo = limpo[4:].strip()
    ini = limpo.find("{")
    if ini >= 0:
        depth = 0
        for i in range(ini, len(limpo)):
            if limpo[i] == "{": depth += 1
            elif limpo[i] == "}":
                depth -= 1
                if depth == 0:
                    limpo = limpo[ini:i+1]
                    break
    try: return json.loads(limpo)
    except Exception: return None

def _chave_fernet():
    segredo = None
    try: segredo = st.secrets.get("PS_FERNET_KEY")
    except Exception: pass
    if not segredo: segredo = os.environ.get("PS_FERNET_KEY")
    if not segredo:
        st.error("🔒 Chave de criptografia não configurada. Defina PS_FERNET_KEY em secrets ou ambiente.")
        st.stop()
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

def _mascarar_chaves(config):
    copia = dict(config)
    chaves = copia.get("chaves", {})
    copia["chaves"] = {k: (("********") if v else "") for k, v in chaves.items()}
    if copia.get("openrouter_api_key"): copia["openrouter_api_key"] = "********"
    return copia

def _req_apps_script(params, timeout=20):
    try:
        resp = requests.get(APPS_SCRIPT_URL.strip(), params=params, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200: return resp.json()
        return {"ok": False, "erro": f"Servidor retornou HTTP {resp.status_code}."}
    except Exception as e: return {"ok": False, "erro": f"Falha de conexão com o serviço de dados: {e}"}

def carregar_config(email=None):
    config = {
        "chaves": {"Chave 1": "", "Chave 2": ""}, "openrouter_api_key": "",
        "provedor_ia": "Automático", "fallback_automatico": True,
        "gemini_so_visao": False, "modelo_openrouter": "meta-llama/llama-3.1-70b-instruct:free", 
        "modelo_padrao": "gemini-1.5-flash"
    }
    dados = _req_apps_script({"acao": "carregar_config", "email": (email or "").strip().lower()})
    if dados and dados.get("ok") and dados.get("config"):
        try:
            config.update(json.loads(dados["config"]))
            config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
            if config.get("openrouter_api_key"): config["openrouter_api_key"] = _descriptografar(config["openrouter_api_key"])
            return config
        except Exception: pass
            
    caminho = os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f: config.update(json.load(f))
            config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
            if config.get("openrouter_api_key"): config["openrouter_api_key"] = _descriptografar(config["openrouter_api_key"])
        except Exception: pass
    return config

def salvar_config(dados, email=None):
    dados = dict(dados)
    dados["chaves"] = {k: _criptografar(v) for k, v in dados.get("chaves", {}).items()}
    if dados.get("openrouter_api_key"): dados["openrouter_api_key"] = _criptografar(dados["openrouter_api_key"])
    
    payload = {"acao": "salvar_config", "email": (email or "").strip().lower(), "config": json.dumps(dados, ensure_ascii=False)}
    try:
        resp = requests.post(APPS_SCRIPT_URL.strip(), json=payload, timeout=20, allow_redirects=True)
        if resp.status_code == 200 and resp.json().get("ok"): return True, None
    except Exception: pass
        
    os.makedirs(PASTA_CONFIGS, exist_ok=True)
    with open(os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    return False, "Erro ao salvar na Nuvem. Cópia salva apenas localmente."

def _extrair_texto_resposta(obj):
    if isinstance(obj, str): return obj.strip()
    if isinstance(obj, list): return "\n".join(p for p in [_extrair_texto_resposta(i) for i in obj] if p).strip()
    if isinstance(obj, dict):
        for k in ("text", "content", "output_text", "response", "generated_text", "message", "choices", "result"):
            if k in obj and obj[k]: return _extrair_texto_resposta(obj[k])
    return ""

def _msg_erro_amigavel(e):
    texto = str(e)
    if "Nenhuma chave configurada" in texto: return "🔑 **Nenhum motor conectado.** Cole sua chave na barra lateral."
    if "REF-VERIF" in texto or "Falha de Comunicação" in texto:
        detalhes = texto.split("Detalhes:")[-1].strip() if "Detalhes:" in texto else ""
        return f"⚠️ **Falha ao chamar motores de IA.** Verifique conexão e chaves. {detalhes[:200]}"
    if "401" in texto or "Unauthorized" in texto: return "🔑 **Chave/Token inválido ou expirado.**"
    if "429" in texto or "quota" in texto.lower(): return "⏳ **Limite de uso temporário atingido (429).** Aguarde a renovação da cota."
    if "503" in texto or "overloaded" in texto.lower(): return "🔌 **Servidor sobrecarregado (503).** O fallback deve assumir."
    if "timeout" in texto.lower(): return "⏱️ **Tempo esgotado na chamada.** Tente novamente."
    return f"⚠️ **Algo deu errado.** {texto[:300]}"

def verificar_acesso_sheets(email):
    try:
        params = {"acao": "verificar_acesso", "email": (email or "").strip().lower()}
        response = requests.get(APPS_SCRIPT_URL.strip(), params=params, timeout=15, allow_redirects=True)
        if response.status_code == 200:
            dados = response.json()
            if not dados.get("encontrado", False): return False, dados.get("expiracao", ""), "⚠️ E-mail não encontrado."
            exp = str(dados.get("expiracao", "")).strip()
            if exp:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                    try:
                        if datetime.strptime(exp.split("T")[0], fmt).date() < datetime.now().date(): return False, exp, f"⚠️ Acesso expirou em {exp}."
                        break
                    except Exception: continue
            return True, exp, None
        return False, "", f"⚠️ Erro do servidor {response.status_code}."
    except Exception as e: return False, "", f"⚠️ Falha na conexão: {e}"

# ==============================================================================
# 3. MOTOR DE CHAMADA TRI-CORE COM REDUNDÂNCIA (GEMINI 1 -> OPENROUTER -> GEMINI 2)
# ==============================================================================
def _chamar_provedor_ia(system_prompt, user_prompt, modelo_gemini="gemini-1.5-flash", temperature=0.25):
    config = carregar_config(st.session_state.get("user_email", ""))
    
    g_key_1 = st.session_state.get("input_key_1", "").strip() or config.get("chaves", {}).get("Chave 1", "")
    or_key = st.session_state.get("input_openrouter_api", "").strip() or config.get("openrouter_api_key", "")
    g_key_2 = st.session_state.get("input_key_2", "").strip() or config.get("chaves", {}).get("Chave 2", "")

    provedores = []
    if g_key_1 and genai is not None:
        provedores.append(("Gemini (Principal)", g_key_1))
    if or_key:
        provedores.append(("OpenRouter", or_key))
    if g_key_2 and genai is not None:
        provedores.append(("Gemini (Reserva)", g_key_2))

    if not provedores:
        raise RuntimeError("Nenhuma chave configurada. Acesse as configurações no painel lateral.")

    escolha_manual = st.session_state.get("ps_provedor_manual", "Automático")
    if escolha_manual != "Automático":
        provedores = sorted(provedores, key=lambda x: 0 if x[0] == escolha_manual else 1)
    elif st.session_state.get("gemini_so_visao", config.get("gemini_so_visao", False)):
        provedores = [p for p in provedores if "OpenRouter" in p[0]] + [p for p in provedores if "Gemini" in p[0]]

    if not st.session_state.get("fallback_automatico", config.get("fallback_automatico", True)):
        provedores = provedores[:1]

    sys_final = system_prompt + f"\n\n[REF-VERIF:{secrets.token_hex(8)}]"
    erros = []
    
    for nome, cred in provedores:
        try:
            if "Gemini" in nome:
                client = genai.Client(api_key=cred)
                cfg = types.GenerateContentConfig(system_instruction=sys_final, temperature=temperature) if types else {"system_instruction": sys_final, "temperature": temperature}
                resp = client.models.generate_content(model=modelo_gemini, contents=user_prompt, config=cfg)
                texto = getattr(resp, "text", "")
                
            elif nome == "OpenRouter":
                url_or = "http" + "s://openrouter.ai/api/v1/chat/completions"
                modelo_or = config.get("modelo_openrouter", "meta-llama/llama-3.1-70b-instruct:free")
                payload = {
                    "model": modelo_or,
                    "messages": [{"role": "system", "content": sys_final}, {"role": "user", "content": user_prompt}], 
                    "temperature": temperature
                }
                headers = {
                    "Authorization": f"Bearer {cred}",
                    "HTTP-Referer": "http" + "s://promptstudio.local",
                    "X-Title": "Prompt Studio Cockpit"
                }
                resp = requests.post(url_or, headers=headers, json=payload, timeout=90)
                resp.raise_for_status()
                texto = _extrair_texto_resposta(resp.json())
            
            texto = str(texto or "").strip()
            if texto and "[REF-VERIF:" not in texto: return texto, nome
        except Exception as e: 
            erros.append(f"{nome}: {str(e)}")

    raise RuntimeError("Falha de Comunicação. Detalhes: " + " | ".join(erros))

# ==============================================================================
# 4. ENGENHARIA DE PROMPT MESTRE E LEITURA DE IMAGEM
# ==============================================================================
PS_STOPWORDS = {"a","o","e","de","da","do","das","dos","um","uma","em","no","na","nos","nas","por","para","com","sem","que","se","ao","aos","as","os","é","ser","sob","sobre","como","mais","sua","seu","dele","dela","esse","esta","isso","este","isto","muito","pouco","já"}

def _ps_markup_origin(preprompt_text, original_text):
    clean = str(preprompt_text or "")
    norm_orig = { normalizar_texto(w) for w in re.findall(r"[\wÀ-ÿ'-]+", original_text or "") if len(w) > 2 and w.lower() not in PS_STOPWORDS }
    pieces = []
    for token in re.split(r"(\s+|[^\wÀ-ÿ'-]+)", clean):
        if not token: continue
        if re.match(r"^[\wÀ-ÿ'-]+$", token):
            norm_token = normalizar_texto(token)
            pieces.append(f'<span class="ps-user-word">{html.escape(token)}</span>' if norm_token in norm_orig else f'<span class="ps-ai-word">{html.escape(token)}</span>')
        else: pieces.append(html.escape(token))
    return "".join(pieces)

SYS_GERADOR_PREPROMPT = r"""Você é o Diretor de Arte Óptica e Composição Visual do Prompt Studio.
Gere um PRÉ-PROMPT visual completo, cinematográfico e coeso em Português a partir da ideia do usuário.
REGRAS MANDATÓRIAS:
1. PRESERVAÇÃO: Preserve nomes de personagens, franquias, gênero e ações informadas.
2. ZERO FLUFF: Adicione somente o que uma câmera captaria. É ESTRITAMENTE PROIBIDO usar metáforas.
3. SAÍDA EXCLUSIVA: Responda APENAS com a descrição visual coesa em Português."""

SYS_COMPOSITOMETRO = r"""Você é o Auditor Óptico e Analista de Composição do Prompt Studio.
Retorne EXCLUSIVAMENTE um JSON válido no formato:
{"sujeito_status": "Definido | Vago | Ausente", "sujeito_resumo": "resumo do sujeito", "acao_status": "Presente | Estática | Ausente", "cenario_status": "Definido | Vago | Ausente", "iluminacao_status": "Definida | Inferida pela IA", "camera_status": "Definida | Inferida pela IA", "nivel_sensualidade_sugerido": 1, "diagnostico_texto": "breve diagnostico", "sugestoes_cirurgicas": [ "sugestão 1", "sugestão 2" ]}"""

# --- DIRETRIZ DE ULTRA-DENSIDADE VISUAL ---
SYS_LEITOR_PARAMETRICO = r"""Você é o Motor de Extração Óptica de Ultra-Densidade (nível Dense Captioning) do Prompt Studio.
Sua missão é realizar uma varredura microscópica da imagem e desconstruí-la com precisão forense. Não resuma.

REGRAS DE EXTRAÇÃO:
1. SUJEITO: Especifique etnia, formato do rosto, cor exata dos olhos e micro-expressões. Descreva a roupa detalhando os materiais (ex: couro sintético, látex reflexivo, algodão desgastado), texturas, costuras, logotipos, caimento, dobras e pequenos acessórios menores (brincos, anéis, tatuagens, manchas na pele).
2. AÇÃO/POSE: Mapeie a geometria corporal exata (ex: "braço direito flexionado a 90 graus tocando o pescoço", "peso apoiado na perna esquerda"), direção milimétrica do olhar e a tensão dos músculos.
3. CENÁRIO: Divida obrigatoriamente a análise em Foreground (Primeiro Plano), Midground e Background. Liste objetos ao redor, clima, arquitetura e texturas dos materiais do ambiente.
4. ILUMINAÇÃO: Mapeie a luz principal (Key light), luz de preenchimento (Fill) e contra-luz (Rim light). Especifique se as sombras são duras ou suaves e localize onde os reflexos especulares atingem a pele ou roupas.
5. CÂMERA: Infira a lente aproximada (ex: 35mm, 85mm macro), a profundidade de campo (DoF/desfoque de fundo), ângulo (High angle, Dutch angle) e a granulação/meio fotográfico.

Retorne EXCLUSIVAMENTE um JSON válido neste formato:
{"sujeito": "...", "acao": "...", "cenario": "...", "iluminacao": "...", "estilo_camera": "..."}"""

SYS_MESTRE_CORE = r"""Você é o Motor de Síntese Óptica e Engenharia de Prompts do Prompt Studio.
Sua missão é compilar o prompt na sintaxe do motor destino com FIDELIDADE ABSOLUTA.

=============================================================================
1. TRADUÇÃO JURAMENTADA DA CENA (REGRA DE OURO)
=============================================================================
- Você DEVE extrair 100% das informações da NARRATIVA VISUAL (Sujeito, Roupa, Cenário, Luz) e aplicá-las no prompt final em inglês. NUNCA resuma, esqueça ou substitua o sujeito original da ideia. Você é um tradutor do pré-prompt, não um inventor.

=============================================================================
2. INJEÇÃO DE TAGS RATING E SENSUALIDADE
=============================================================================
ATENÇÃO: A narrativa de figurino já foi resolvida globalmente. Sua função é APENAS injetar as "Tags de Rating":
- Nível 1/2: Injetar 'rating_safe'.
- Nível 3/4: Injetar 'rating_questionable, nsfw'.
- Nível 5: Injetar 'rating_explicit, nude, nsfw, uncensored'. Use tags Danbooru para anatomia exposta.
- Nível 6 (Dual): Gere o prompt: VERSÃO A (Censurada) e VERSÃO B (Explícita).
"""

def processar_imagem_visao(arquivo_imagem, estilo_conversao, nivel_sensualidade, modelo_gemini):
    MAX_IMAGE_SIZE_MB = 10
    if arquivo_imagem.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise RuntimeError(f"🖼️ Imagem limite: {MAX_IMAGE_SIZE_MB} MB.")
    
    config = carregar_config(st.session_state.get("user_email", ""))
    k1 = st.session_state.get("input_key_1", "").strip() or config.get("chaves", {}).get("Chave 1", "")
    k2 = st.session_state.get("input_key_2", "").strip() or config.get("chaves", {}).get("Chave 2", "")
    
    chaves_visao = [k for k in [k1, k2] if k]
    if not chaves_visao or genai is None:
        raise RuntimeError("Chave Gemini necessária para visão. Conecte no painel lateral.")
    
    img_pil = Image.open(arquivo_imagem)
    user_prompt = "Desconstrua pericialmente esta imagem com detalhes microscópicos. \n[MODIFICADOR 2: SENSUALIDADE]: Nível " + str(nivel_sensualidade) + " - Redesenhe a roupa/pose original para refletir EXATAMENTE esse nível (Nível 4 ou 5 exige remoção de roupas)."
    if "Fotorrealismo" in estilo_conversao: user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza a cena inteira para o MUNDO REAL fotorrealista (proibido anime/3d)."
    elif "Anime" in estilo_conversao: user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza a cena para ILUSTRAÇÃO 2D ANIME (proibido poros/fotorrealismo)."

    erros = []
    # Redundância de Visão: se a Chave 1 falhar ou atingir cota, tenta a Chave 2 automaticamente
    for idx, chave in enumerate(chaves_visao):
        try:
            client = genai.Client(api_key=chave)
            cfg = types.GenerateContentConfig(system_instruction=SYS_LEITOR_PARAMETRICO, temperature=0.2)
            resp = client.models.generate_content(model=modelo_gemini, contents=[img_pil, user_prompt], config=cfg)
            texto = getattr(resp, "text", "") or ""
            if not texto.strip(): raise RuntimeError("A IA bloqueou o retorno da imagem.")
            dados = parse_json_ia(texto)
            if dados: return {"tipo": "json", "dados": dados}
            return {"tipo": "texto", "texto": texto}
        except Exception as e:
            erros.append(f"Gemini {idx+1}: {str(e)}")

    raise RuntimeError("Falha na leitura óptica em todas as chaves Gemini conectadas: " + " | ".join(erros))

# ==============================================================================
# 5. UI: BARRA LATERAL (CENTRO DE CONEXÃO BYOK) E LANDING PAGE
# ==============================================================================
def renderizar_sidebar():
    st.sidebar.markdown("## ⚙️ Centro de Conexão (Chaves)")
    st.sidebar.caption(f"Usuário: **{st.session_state.get('user_email', '')}**")
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    config = carregar_config(st.session_state.get("user_email", ""))
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**O motor é seu.** Pegue suas chaves de API gratuitas nos painéis oficiais e conecte abaixo.")
    
    st.sidebar.markdown("<a href='http" + "s://aistudio.google.com/app/apikey' target='_blank' style='color:#2563eb; text-decoration:none;'>🔑 Google Gemini (Principal)</a>", unsafe_allow_html=True)
    k1 = st.sidebar.text_input("Chave Gemini 1", value=config.get("chaves", {}).get("Chave 1", ""), type="password", key="input_key_1", label_visibility="collapsed")
    
    st.sidebar.markdown("<br><a href='http" + "s://openrouter.ai/keys' target='_blank' style='color:#10b981; text-decoration:none;'>🌐 OpenRouter (Llama 70B Gratuito)</a>", unsafe_allow_html=True)
    k_or = st.sidebar.text_input("Chave OpenRouter", value=config.get("openrouter_api_key", ""), type="password", key="input_openrouter_api", label_visibility="collapsed")

    st.sidebar.markdown("<br><span style='color:#b45309; font-weight:600;'>🛡️ Google Gemini (Reserva / Opcional)</span>", unsafe_allow_html=True)
    k2 = st.sidebar.text_input("Chave Gemini 2", value=config.get("chaves", {}).get("Chave 2", ""), type="password", key="input_key_2", label_visibility="collapsed")

    with st.sidebar.expander("Ferramentas Avançadas", expanded=False):
            st.selectbox("Provedor Prioritário", ["Automático", "Gemini (Principal)", "OpenRouter", "Gemini (Reserva)"], key="ps_provedor_manual")
            gemini_so_visao_chk = st.checkbox("🛡️ Priorizar OpenRouter para Texto (Poupa Cota Gemini)", value=config.get("gemini_so_visao", False), key="gemini_so_visao")
            fallback_chk = st.checkbox("Fallback Automático", value=config.get("fallback_automatico", True), key="fallback_automatico")
            st.selectbox("Modelo de Visão (Gemini)", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0, key="modelo_visao_select")

    if st.sidebar.button("💾 Conectar Motores", type="primary", use_container_width=True):
        dados_salvos = {
            "chaves": {"Chave 1": k1, "Chave 2": k2}, 
            "openrouter_api_key": k_or,
            "provedor_ia": st.session_state.get("ps_provedor_manual", "Automático"),
            "fallback_automatico": fallback_chk, "gemini_so_visao": gemini_so_visao_chk,
            "modelo_openrouter": "meta-llama/llama-3.1-70b-instruct:free",
            "modelo_padrao": "gemini-1.5-flash", "usar_busca_web": False
        }
        ok_salvo, erro_salvo = salvar_config(dados_salvos, st.session_state.get("user_email", ""))
        if ok_salvo: st.sidebar.success("✅ Motores conectados e prontos!")
        else: st.sidebar.warning(f"⚠️ {erro_salvo}")

def _historico_sheets(email, prompt_texto=None, acao="listar"):
    email = (email or "").strip().lower()
    if acao == "adicionar":
        if not prompt_texto or not str(prompt_texto).strip(): return False, "Nenhum prompt."
        MAX_HISTORY_CHARS = 25000
        truncado = len(str(prompt_texto)) > MAX_HISTORY_CHARS
        payload = { "acao": "adicionar_historico", "email": email, "prompt": str(prompt_texto)[:MAX_HISTORY_CHARS], "_truncado": truncado }
        try:
            resp = requests.post(APPS_SCRIPT_URL.strip(), json=payload, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and resp.json().get("ok"): return True, None
        except Exception as e: return False, f"Falha de conexão: {e}"
        return False, "Erro ao processar."
    params = {"acao": "listar_historico", "email": email}
    resp = _req_apps_script(params, timeout=20)
    if resp and resp.get("ok"): return True, resp.get("itens", [])
    return False, []

def renderizar_historico():
    with st.sidebar.expander("🕘 Histórico de Prompts", expanded=False):
        ok, itens = _historico_sheets(st.session_state.get("user_email", ""), acao="listar")
        if not ok: st.caption("Histórico indisponível."); return
        if not itens: st.caption("Nenhum prompt salvo ainda."); return
        for item in itens[-10:]:
            ts = item.get("quando", "")[:16]
            preview = str(item.get("prompt", ""))[:90].replace("\n", " ")
            if st.button(f"{ts} — {preview}...", key=f"hist_{item.get('id', ts)}", use_container_width=True):
                st.session_state["ck_historico_ver"] = item.get("prompt", "")

# ==============================================================================
# 6. UI: COCKPIT PRINCIPAL
# ==============================================================================
def renderizar_cockpit():
    st.markdown("<div class='ps-kicker'>PROMPT STUDIO COCKPIT · ATRITO ZERO</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='ps-title'>Sua Ideia. Seu Motor. Controle Total.</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("### 🧬 Agentes Modificadores Globais")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: estilo_conversao = st.selectbox("Estilo de Arte:", ["Manter Estilo Original", "📸 Converter para Fotorrealismo", "🎨 Converter para Anime"], key="ck_estilo_conversao")
        with col_m2: foco_contexto = st.selectbox("Foco e Contexto:", ["Harmônico (Preencher/Embelezar)", "Literal (Direto, Sem Floreios)"], key="ck_foco_contexto")
        with col_m3: sens_escolhida = st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider", value=st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1]))

    with st.container(border=True):
        st.markdown("### 🖼️ Extração Pericial de Imagem (Visão)")
        col_img1, col_img2 = st.columns([4, 6])
        with col_img1: img_file = st.file_uploader("Upload de Referência", type=["png", "jpg", "jpeg", "webp"], key="ck_img_uploader", label_visibility="collapsed")
        with col_img2:
            st.write("Aplica as regras globais de figurino e estilo na leitura.")
            btn_ler = st.button("👁️ Extrair Prompt da Imagem", use_container_width=True)

        if btn_ler:
            if not img_file: st.warning("Selecione uma imagem primeiro.")
            else:
                with st.spinner("Analisando matriz óptica com Varredura Ultra-Densa..."):
                    try:
                        modelo_visao = st.session_state.get("modelo_visao_select", "gemini-1.5-flash")
                        res = processar_imagem_visao(img_file, estilo_conversao, sens_escolhida, modelo_visao)
                        if res["tipo"] == "json":
                            st.session_state["ck_img_parametros"] = res["dados"]
                            st.session_state["ck_ideia_input"] = f"{res['dados'].get('sujeito','')}, {res['dados'].get('acao','')}. Cenário: {res['dados'].get('cenario','')}. Iluminação: {res['dados'].get('iluminacao','')}. Estilo: {res['dados'].get('estilo_camera','')}."
                        else:
                            st.session_state["ck_ideia_input"] = res["texto"]
                            st.session_state.pop("ck_img_parametros", None)
                        st.session_state.pop("ck_preprompt", None)
                        st.rerun()
                    except Exception as e: st.error(_msg_erro_amigavel(e))

        parametros = st.session_state.get("ck_img_parametros")
        if parametros:
            with st.expander("🔬 Detalhador Pericial de Imagem (Editável)", expanded=True):
                st.caption("Ajuste os parâmetros extraídos da imagem.")
                c1, c2 = st.columns(2)
                with c1:
                    p_suj = st.text_area("👤 Sujeito (Biotipo/Roupas):", value=parametros.get("sujeito", ""), height=150)
                    p_cen = st.text_area("🏞️ Cenário:", value=parametros.get("cenario", ""), height=150)
                with c2:
                    p_act = st.text_area("🏃 Ação / Pose:", value=parametros.get("acao", ""), height=100)
                    p_ilu = st.text_area("💡 Iluminação:", value=parametros.get("iluminacao", ""), height=100)
                    p_est = st.text_area("📷 Estilo / Câmera:", value=parametros.get("estilo_camera", ""), height=100)
                if st.button("🔄 Atualizar Narrativa Visual", use_container_width=True):
                    st.session_state["ck_ideia_input"] = f"{p_suj}, {p_act}. Cenário: {p_cen}. Iluminação: {p_ilu}. Estilo: {p_est}."
                    st.session_state["ck_img_parametros"] = {"sujeito": p_suj, "acao": p_act, "cenario": p_cen, "iluminacao": p_ilu, "estilo_camera": p_est}
                    st.rerun()

        st.markdown("---")
        st.markdown("### 💡 Qual é a NARRATIVA VISUAL do seu prompt?")
        ideia_input = st.text_area("Descreva ou edite a cena:", key="ck_ideia_input", height=140)

        col_b1, col_b2, col_b3 = st.columns([4, 4, 2])
        with col_b1: btn_pre = st.button("👁️ Rascunhar Cena (Pré-prompt)", type="primary", use_container_width=True)
        with col_b2: btn_ava = st.button("🔍 Auditar no Compositômetro", use_container_width=True)
        with col_b3:
            if st.button("🗑️ Limpar Tudo", use_container_width=True):
                st.session_state["ck_ideia_input"] = "" 
                for k in ["ck_img_parametros","ck_preprompt","ck_preprompt_editado","ck_diagnostico","ck_prompt_final", "ck_sugestoes_marcadas"]: st.session_state.pop(k, None)
                st.rerun()

    if btn_pre:
        if not ideia_input.strip(): st.warning("Escreva sua ideia antes.")
        else:
            with st.spinner("Desenhando a cena..."):
                try:
                    p = f"IDEIA:\n{ideia_input.strip()}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sens_escolhida}']: Aplique roupas/pose relativas a este nível substituindo a roupa do usuário se explícito."
                    if "Literal" in foco_contexto:
                        p += "\n[AGENTE: CONTEXTO LITERAL]: Seja 100% fiel e obediente à ideia original. Crie APENAS o cenário lógico, físico e elementar inerente à ação. É ESTRITAMENTE PROIBIDO adicionar elementos não solicitados, embelezamentos ou 'fluff' estético."
                    txt, prov = _chamar_provedor_ia(SYS_GERADOR_PREPROMPT, p)
                    st.session_state["ck_ideia"] = ideia_input.strip()
                    st.session_state["ck_preprompt"] = txt
                    st.session_state["ck_preprompt_editado"] = txt 
                    st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if btn_ava:
        if not ideia_input.strip(): st.warning("Escreva sua ideia antes.")
        else:
            with st.spinner("Raio-X em andamento..."):
                try:
                    txt, prov = _chamar_provedor_ia(SYS_COMPOSITOMETRO, f"AVALIE:\n{ideia_input.strip()}")
                    diag = parse_json_ia(txt)
                    if not diag: st.error("⚠️ O Compositômetro retornou um formato inesperado. Tente novamente.")
                    else: st.session_state["ck_diagnostico"] = diag; st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if st.session_state.get("ck_preprompt"):
        with st.container(border=True):
            st.markdown("### 🎨 Pré-prompt (Cena Traduzida)")
            st.markdown("<div class='ps-legend'><span><span class='ps-user-word'>Ideia Original</span></span> • <span><span class='ps-ai-word'>Desenvolvimento da IA</span></span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ps-preprompt'>{_ps_markup_origin(st.session_state['ck_preprompt'], st.session_state.get('ck_ideia', ''))}</div>", unsafe_allow_html=True)
            pre_ed = st.text_area("Ajuste fino manual (Esta caixa será enviada ao Sintetizador):", value=st.session_state.get("ck_preprompt_editado", ""), key="ck_preprompt_editado", height=130)
            if pre_ed != st.session_state.get("ck_preprompt"): st.session_state["ck_preprompt"] = pre_ed

    diag = st.session_state.get("ck_diagnostico")
    if diag:
        with st.container(border=True):
            st.markdown("#### 📊 Raio-X do Compositômetro")
            c1, c2, c3, c4, c5 = st.columns(5)
            def _bdg(s): return ("comp-green","✓") if s in ["Definido","Presente"] else ("comp-amber","!") if s in ["Vago","Estática"] else ("comp-blue","⚙️")
            for col, key, label in zip([c1,c2,c3,c4,c5], ["sujeito_status","acao_status","cenario_status","iluminacao_status","camera_status"], ["Sujeito","Ação","Cenário","Luz","Câmera"]):
                cl, ic = _bdg(diag.get(key, ""))
                col.markdown(f"<div class='comp-badge {cl}'>{ic} {label}: {diag.get(key, 'Pendente')}</div>", unsafe_allow_html=True) 
            
            st.write("")
            if diag.get("diagnostico_texto"): st.caption(f"ℹ️ **Diagnóstico:** {diag.get('diagnostico_texto')}")
            sugestoes = diag.get("sugestoes_cirurgicas", [])
            if sugestoes:
                st.markdown("##### ✨ Sugestões Cirúrgicas Opcionais:")
                selecionadas = []
                for idx, sug in enumerate(sugestoes):
                    if st.checkbox(sug, key=f"sug_chk_{idx}"): selecionadas.append(sug)
                st.session_state["ck_sugestoes_marcadas"] = selecionadas
            else: st.session_state["ck_sugestoes_marcadas"] = []

    st.write("")
    col_dest1, col_dest2 = st.columns([7, 3])
    with col_dest1: dest_sel = st.selectbox("Plataforma / Motor de Imagem Alvo (OBRIGATÓRIO):", OPCOES_DESTINO, index=0, key="ck_destino_select")
    with col_dest2: 
        st.write("")
        st.write("")
        btn_exec = st.button("⚡ Gerar Código do Prompt", type="primary", use_container_width=True)

    if btn_exec:
        if dest_sel == "Selecione o Motor Destino...": st.error("🛑 Pare! Selecione para qual motor de IA este prompt será compilado.")
        elif not ideia_input.strip(): st.warning("Descreva sua ideia antes.")
        else:
            with st.spinner(f"Compilando sintaxe para {dest_sel}..."):
                try:
                    eng = BANCO_DE_MOTORES[dest_sel]
                    bloco = f"\n\n======================================\n3. SINTAXE NATIVA: {dest_sel}\n======================================\n- POSITIVO: {eng['regra_positivo']}\n- NEGATIVO: {eng.get('regra_negativo', 'N/A')}\n\nSAÍDA OBRIGATÓRIA:\n1. PROMPT (MANDATORY IN ENGLISH)\n2. NEGATIVE PROMPT (MANDATORY IN ENGLISH)\n3. LEGENDA (Português)\n4. HASHTAGS\n💡 DICA TÉCNICA: {eng['dica_tecnica']}"
                    
                    txt_b = st.session_state.get("ck_preprompt_editado", ideia_input.strip())
                    sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])
                    sug_str = "\n".join(f"- {s}" for s in sug_aceitas) if sug_aceitas else "Nenhuma sugestão adicional marcada."
                    
                    p = f"DESTINO: {dest_sel}\nRATING: {sens_escolhida}\n\n1. NARRATIVA VISUAL:\n{txt_b}\n\n2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}\n\nGere o prompt garantindo a ancoragem de Sujeito."
                    
                    if "Literal" in foco_contexto: p += "\n[MODO LITERAL ATIVADO]: Você DEVE ignorar diretrizes estéticas excessivas da regra do motor. Remova termos de 'embelezamento' da sintaxe final, focando puramente nos atributos físicos e no cenário lógico elementar."
                    p += "\n\n⚠️ CRITICAL INSTRUCTION: THE FINAL 'PROMPT' AND 'NEGATIVE' SECTIONS MUST BE GENERATED STRICTLY IN ENGLISH. DO NOT TRANSLATE THEM TO PORTUGUESE."

                    res, prov = _chamar_provedor_ia(SYS_MESTRE_CORE + bloco, p)
                    st.session_state["ck_prompt_final"] = res
                    st.session_state["ck_prov_usado"] = prov
                    st.session_state["ck_dest_usado"] = dest_sel
                    st.rerun()
                except Exception as e: st.error(_msg_erro_amigavel(e))

    if st.session_state.get("ck_prompt_final"):
        st.markdown("---")
        st.markdown(f"### 📋 Prompt Especializado ({st.session_state.get('ck_dest_usado')})")
        try: st.code(st.session_state["ck_prompt_final"], language="markdown", wrap_lines=True)
        except Exception: st.markdown(f"<div class='ps-preprompt' style='white-space: pre-wrap; word-wrap: break-word; font-family: monospace;'>{html.escape(st.session_state['ck_prompt_final'])}</div>", unsafe_allow_html=True)
            
        c_save1, c_save2 = st.columns(2)
        with c_save1:
            if st.button("💾 Salvar no Histórico", use_container_width=True):
                ok_hist, erro_hist = _historico_sheets(st.session_state.get("user_email", ""), st.session_state["ck_prompt_final"], acao="adicionar")
                if ok_hist: st.success("✅ Prompt salvo no histórico!")
                else: 
                    if erro_hist and "_truncado" in str(erro_hist): st.warning("⚠️ Prompt truncado no histórico (limite de 25.000 caracteres).")
                    else: st.warning(f"⚠️ {erro_hist or 'Não foi possível salvar.'}")

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
