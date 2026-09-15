# -*- coding: utf-8 -*-
"""
Prompt Studio Cockpit — Interface Minimalista de Alta Precisão
Arquitetura: Shift-Left (Modificadores no Ponto Zero) + BYOK (Traga sua Chave) + Carga Distribuída.

v2.0 — Melhorias:
  • Chaves criptografadas em repouso (Fernet, chave via st.secrets/ambiente)
  • Persistência via Google Sheets (Apps Script do login) com fallback local
  • Erros amigáveis (sem traceback cru exposto ao usuário)
  • Clientes de API cacheados (st.cache_resource)
  • Estado do pré-prompt editado mais robusto
  • Histórico de prompts salvos
  • Detalhador Pericial de Imagem (Editável)
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
# 2. CONSTANTES E DICIONÁRIO DE TRADUÇÃO JURAMENTADA
# ==============================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzgEj3YPwqiUbiueyu8wjZ9ZZK0Rcc6G3kucysRSJ2gNmzRzUdMuLqv_q55N1kSO8PQ/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/xo0m3rF"

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
    """Normaliza um e-mail para usar como nome de arquivo/pasta com segurança."""
    return re.sub(r'[^\w\-.]', '_', (email or "anonimo").strip().lower()) or "anonimo"

def normalizar_texto(texto):
    """Remove acentos e normaliza minúsculas — usado na marcação origem vs IA."""
    return "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )

def parse_json_ia(texto):
    """Extrai um JSON de uma resposta de IA, tolerando cercas ```json e lixo ao redor."""
    if not texto:
        return None
    limpo = str(texto).strip().strip("`")
    if limpo.lower().startswith("json"):
        limpo = limpo[4:].strip()
    ini = limpo.find("{")
    if ini >= 0:
        depth = 0
        for i in range(ini, len(limpo)):
            if limpo[i] == "{":
                depth += 1
            elif limpo[i] == "}":
                depth -= 1
                if depth == 0:
                    limpo = limpo[ini:i+1]
                    break
    try:
        return json.loads(limpo)
    except Exception:
        return None

def _chave_fernet():
    """Deriva uma chave Fernet estável a partir de st.secrets ou variável de ambiente."""
    segredo = None
    try:
        segredo = st.secrets.get("PS_FERNET_KEY")
    except Exception:
        pass
    if not segredo:
        segredo = os.environ.get("PS_FERNET_KEY", "chave-local-nao-segura")
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
    if not f or not texto:
        return texto
    return f.encrypt(texto.encode("utf-8")).decode("utf-8")

def _descriptografar(texto):
    f = _chave_fernet()
    if not f or not texto:
        return texto
    try:
        return f.decrypt(texto.encode("utf-8")).decode("utf-8")
    except Exception:
        return texto

def _mascarar_chaves(config):
    """Remove conteúdo sensível de um dict p/ exibição segura (nunca logar chaves)."""
    copia = dict(config)
    chaves = copia.get("chaves", {})
    copia["chaves"] = {k: (("********") if v else "") for k, v in chaves.items()}
    if copia.get("groq_api_key"): copia["groq_api_key"] = "********"
    if copia.get("cloudflare_api_token"): copia["cloudflare_api_token"] = "********"
    return copia

# ---- Persistência: Google Sheets (Apps Script) com fallback local ----
def _req_apps_script(params, timeout=20):
    """Faz GET no Apps Script e devolve JSON, tratando erros de rede com clareza."""
    try:
        resp = requests.get(APPS_SCRIPT_URL.strip(), params=params, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.json()
        return {"ok": False, "erro": f"Servidor retornou HTTP {resp.status_code}."}
    except Exception as e:
        return {"ok": False, "erro": f"Falha de conexão com o serviço de dados: {e}"}

def carregar_config(email=None):
    """Carrega config do usuário: tenta Sheets primeiro; fallback p/ arquivo local."""
    config = {
        "chaves": {"Chave 1": ""}, "groq_api_key": "", "cloudflare_account_id": "",
        "cloudflare_api_token": "", "provedor_ia": "Gemini", "fallback_automatico": True,
        "gemini_so_visao": True, "modelo_groq": "llama3-70b-8192",
        "modelo_cloudflare": "@cf/meta/llama-3-8b-instruct", "modelo_padrao": "gemini-3.8-flash"
    }
    dados = _req_apps_script({"acao": "carregar_config", "email": (email or "").strip().lower()})
    if dados and dados.get("ok") and dados.get("config"):
        try:
            config.update(json.loads(dados["config"]))
            config["chaves"] = {k: _descriptografar(v) for k, v in config.get("chaves", {}).items()}
            if config.get("groq_api_key"): config["groq_api_key"] = _descriptografar(config["groq_api_key"])
            if config.get("cloudflare_api_token"): config["cloudflare_api_token"] = _descriptografar(config["cloudflare_api_token"])
            return config
        except Exception:
            pass
            
    caminho = os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass
            
    return config

def salvar_config(dados, email=None):
    """Salva config: Sheets (chaves criptografadas) + espelho local p/ testes."""
    dados = dict(dados)
    dados["chaves"] = {k: _criptografar(v) for k, v in dados.get("chaves", {}).items()}
    if dados.get("groq_api_key"): dados["groq_api_key"] = _criptografar(dados["groq_api_key"])
    if dados.get("cloudflare_api_token"): dados["cloudflare_api_token"] = _criptografar(dados["cloudflare_api_token"])
    payload = json.dumps(dados, ensure_ascii=False)
    resp = _req_apps_script({"acao": "salvar_config", "email": (email or "").strip().lower(), "config": payload})
    if not (resp and resp.get("ok")):
        os.makedirs(PASTA_CONFIGS, exist_ok=True)
        with open(os.path.join(PASTA_CONFIGS, f"config_{_slug_usuario(email)}.json"), "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        return False, resp.get("erro", "Não foi possível salvar no servidor. Salvo apenas localmente.")
    return True, None

def salvar_resultado_manual(texto, nome_sujeito, email=None):
    """Salva um prompt em arquivo local (mesma pasta do original), retornando nome."""
    if not texto or not str(texto).strip():
        return "⚠️ Nenhum resultado para salvar."
    pasta = os.path.join(PASTA_RESULTADOS, _slug_usuario(email))
    os.makedirs(pasta, exist_ok=True)
    nome_base = re.sub(r"[^\w\-]", "_", str(nome_sujeito or "prompt")).strip("_").lower() or "prompt"
    nome = f"prompt_{nome_base}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(os.path.join(pasta, nome), "w", encoding="utf-8") as f:
        f.write(texto)
    return f"💾 Prompt salvo no servidor: `{nome}`"

def _extrair_texto_resposta(obj):
    if isinstance(obj, str): return obj.strip()
    if isinstance(obj, list): return "\n".join(p for p in [_extrair_texto_resposta(i) for i in obj] if p).strip()
    if isinstance(obj, dict):
        for k in ("text", "content", "output_text", "response", "generated_text", "message", "choices", "result"):
            if k in obj and obj[k]: return _extrair_texto_resposta(obj[k])
    return ""

# ==============================================================================
# 2.2 ERROS AMIGÁVEIS
# ==============================================================================
def _msg_erro_amigavel(e):
    """Converte exceções de API em mensagens claras, sem expor traceback."""
    texto = str(e)
    if "Nenhuma chave configurada" in texto or "Nenhuma chave de API" in texto:
        return "🔑 **Nenhum motor conectado.** Abra o **Centro de Conexão** na barra lateral e cole sua chave (Gemini/Groq/Cloudflare)."
    if "REF-VERIF" in texto or "Falha de Comunicação" in texto:
        detalhes = texto.split("Detalhes:")[-1].strip() if "Detalhes:" in texto else ""
        return f"⚠️ **Falha ao chamar o motor de IA.** Verifique sua chave, cota e conexão. {detalhes[:200]}"
    if "401" in texto or "Unauthorized" in texto or "API key not valid" in texto:
        return "🔑 **Chave de API inválida ou expirada.** Verifique no painel do provedor e atualize no Centro de Conexão."
    if "429" in texto or "quota" in texto.lower() or "rate limit" in texto.lower():
        return "⏳ **Limite de uso atingido (429).** O provedor está com cota esgotada. Aguarde ou use outro motor (fallback)."
    if "503" in texto or "overloaded" in texto.lower() or "overload" in texto.lower():
        return "🔌 **Provedor sobrecarregado (503).** Tente novamente em instantes ou mude o provedor prioritário."
    if "timeout" in texto.lower() or "timed out" in texto.lower():
        return "⏱️ **Tempo esgotado na chamada.** Tente novamente; se persistir, use outro provedor."
    return f"⚠️ **Algo deu errado.** {texto[:300]}"

# ==============================================================================
# 3. AUTENTICAÇÃO, CONFIGURAÇÃO E MOTOR DE CHAMADA
# ==============================================================================
def verificar_acesso_sheets(email):
    try:
        params = {"acao": "verificar_acesso", "email": (email or "").strip().lower()}
        response = requests.get(APPS_SCRIPT_URL.strip(), params=params, timeout=15, allow_redirects=True)
        if response.status_code == 200:
            dados = response.json()
            if not dados.get("encontrado", False):
                return False, dados.get("expiracao", ""), "⚠️ E-mail não encontrado na base de clientes autorizados."
            exp = str(dados.get("expiracao", "")).strip()
            if exp:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                    try:
                        if datetime.strptime(exp.split("T")[0], fmt).date() < datetime.now().date():
                            return False, exp, f"⚠️ Seu acesso expirou em {exp}."
                        break
                    except Exception:
                        continue
            return True, exp, None
        return False, "", f"⚠️ Erro do servidor {response.status_code}."
    except Exception as e:
        return False, "", f"⚠️ Falha na conexão: {e}"

def _chamar_provedor_ia(system_prompt, user_prompt, modelo_gemini="gemini-3.8-flash", temperature=0.25):
    config = carregar_config(st.session_state.get("user_email", ""))
    provedores = []
    
    g_key = st.session_state.get("input_key_1", "").strip() or config.get("chaves", {}).get("Chave 1", "")
    if g_key and genai is not None: provedores.append(("Gemini", g_key))
    
    gr_key = st.session_state.get("input_groq_api", "").strip() or config.get("groq_api_key", "")
    if gr_key: provedores.append(("Groq", gr_key))
    
    cf_t = st.session_state.get("input_cloudflare_token", "").strip() or config.get("cloudflare_api_token", "")
    cf_a = st.session_state.get("input_cloudflare_account", "").strip() or config.get("cloudflare_account_id", "")
    if cf_t and cf_a: provedores.append(("Cloudflare", (cf_t, cf_a)))

    if not provedores:
        raise RuntimeError("Nenhuma chave configurada. Acesse as configurações na barra lateral esquerda para conectar seu motor.")

    if st.session_state.get("ps_provedor_manual", "Automático") != "Automático":
        provedores = sorted(provedores, key=lambda x: 0 if x[0] == st.session_state.get("ps_provedor_manual") else 1)

    if st.session_state.get("gemini_so_visao", config.get("gemini_so_visao", True)):
        provedores = [p for p in provedores if p[0] != "Gemini"] + [p for p in provedores if p[0] == "Gemini"]

    if not st.session_state.get("fallback_automatico", config.get("fallback_automatico", True)):
        provedores = provedores[:1]

    sys_final = system_prompt + f"\n\n[REF-VERIF:{secrets.token_hex(8)}]"
    erros = []
    
    for nome, cred in provedores:
        try:
            if nome == "Gemini":
                client = genai.Client(api_key=cred)
                cfg = types.GenerateContentConfig(system_instruction=sys_final, temperature=temperature) if types else {"system_instruction": sys_final, "temperature": temperature}
                resp = client.models.generate_content(model=modelo_gemini, contents=user_prompt, config=cfg)
                texto = getattr(resp, "text", "")
                
            elif nome == "Groq":
                url_groq = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)".strip()
                payload = {
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "system", "content": sys_final}, {"role": "user", "content": user_prompt}], 
                    "temperature": temperature
                }
                resp = requests.post(url_groq, headers={"Authorization": f"Bearer {cred}"}, json=payload, timeout=90)
                resp.raise_for_status()
                texto = _extrair_texto_resposta(resp.json())
                
            elif nome == "Cloudflare":
                cf_modelo = "@cf/meta/llama-3.1-8b-instruct"
                url_cf = f"[https://api.cloudflare.com/client/v4/accounts/](https://api.cloudflare.com/client/v4/accounts/){cred[1].strip()}/ai/run/{cf_modelo}".strip()
                payload = {
                    "messages": [{"role": "system", "content": sys_final}, {"role": "user", "content": user_prompt}], 
                    "temperature": temperature, 
                    "max_tokens": 4096
                }
                resp = requests.post(url_cf, headers={"Authorization": f"Bearer {cred[0]}"}, json=payload, timeout=90)
                resp.raise_for_status()
                texto = _extrair_texto_resposta(resp.json())
            
            texto = str(texto or "").strip()
            if texto and "[REF-VERIF:" not in texto: return texto, nome
        except Exception as e: 
            erros.append(f"{nome}: {str(e)}")

    raise RuntimeError("Falha de Comunicação com as APIs. Detalhes: " + " | ".join(erros))

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

SYS_LEITOR_PARAMETRICO = r"""Você é o Cirurgião Óptico de ALTA PRECISÃO do Prompt Studio. Desconstrua a imagem de forma pericial.
REGRAS: BIOTIPO (trave peso e proporções reais da imagem), CABELO (comprimento/cor exatos), ROUPA (tecido/caimento sem invenção), POSE (mapeie braços/pernas/olhar).
Retorne EXCLUSIVAMENTE um JSON válido:
{"sujeito": "biotipo, etnia, cabelo e roupas precisas", "acao": "pose eixos X/Y", "cenario": "ambiente", "iluminacao": "luz e cores", "estilo_camera": "estilo e enquadramento"}"""

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
    gemini_key = st.session_state.get("input_key_1", "").strip() or carregar_config(st.session_state.get("user_email", "")).get("chaves", {}).get("Chave 1", "")
    if not gemini_key or genai is None: raise RuntimeError("Chave do Google Gemini necessária para leitura de imagens. Adicione na barra lateral.")
    
    img_pil = Image.open(arquivo_imagem)
    user_prompt = "Desconstrua pericialmente esta imagem. \n[MODIFICADOR 2: SENSUALIDADE]: Nível " + str(nivel_sensualidade) + " - Redesenhe a roupa/pose original para refletir EXATAMENTE esse nível (Nível 4 ou 5 exige remoção de roupas)."
    if "Fotorrealismo" in estilo_conversao: user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza a cena inteira para o MUNDO REAL fotorrealista (proibido anime/3d)."
    elif "Anime" in estilo_conversao: user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza a cena para ILUSTRAÇÃO 2D ANIME (proibido poros/fotorrealismo)."

    client = genai.Client(api_key=gemini_key)
    cfg = types.GenerateContentConfig(system_instruction=SYS_LEITOR_PARAMETRICO, temperature=0.2)
    resp = client.models.generate_content(model=modelo_gemini, contents=[img_pil, user_prompt], config=cfg)
    
    texto = getattr(resp, "text", "") or ""
    if not texto.strip(): raise RuntimeError("A IA bloqueou o retorno da imagem.")
    
    dados = parse_json_ia(texto)
    if dados:
        return {"tipo": "json", "dados": dados}
    return {"tipo": "texto", "texto": texto}

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
    st.sidebar.markdown("**O motor é seu.** Pegue suas chaves de API gratuitas nos painéis oficiais e cole abaixo para ativar o Cockpit.")
    
    st.sidebar.markdown("🔑 **Google Gemini** (Visão e Textos)")
    st.sidebar.markdown("[Pegar chave grátis no AI Studio](https://aistudio.google.com/app/apikey)", unsafe_allow_html=True)
    k1 = st.sidebar.text_input("Cole sua Chave Gemini", value=config.get("chaves", {}).get("Chave 1", ""), type="password", key="input_key_1", label_visibility="collapsed")
    
    st.sidebar.markdown("⚡ **Groq** (Texto Ultra-rápido Llama 3)")
    st.sidebar.markdown("[Pegar chave grátis no Groq Console](https://console.groq.com/keys)", unsafe_allow_html=True)
    k_groq = st.sidebar.text_input("Cole sua Chave Groq", value=config.get("groq_api_key", ""), type="password", key="input_groq_api", label_visibility="collapsed")

    with st.sidebar.expander("Ferramentas Avançadas", expanded=False):
        st.selectbox("Provedor Prioritário", ["Automático", "Gemini", "Groq", "Cloudflare"], key="ps_provedor_manual")
        cf_acc = st.text_input("Cloudflare Account ID", value=config.get("cloudflare_account_id", ""), key="input_cloudflare_account")
        cf_tok = st.text_input("Cloudflare Token", value=config.get("cloudflare_api_token", ""), type="password", key="input_cloudflare_token")
        gemini_so_visao_chk = st.checkbox("🛡️ Economia Gemini (Groq p/ Texto, Gemini só Visão)", value=config.get("gemini_so_visao", True), key="gemini_so_visao")
        fallback_chk = st.checkbox("Fallback Automático", value=config.get("fallback_automatico", True), key="fallback_automatico")

    if st.sidebar.button("💾 Conectar Motores", type="primary", use_container_width=True):
        dados_salvos = {
            "chaves": {"Chave 1": k1, "Chave 2": ""}, "groq_api_key": k_groq,
            "cloudflare_account_id": cf_acc, "cloudflare_api_token": cf_tok,
            "provedor_ia": st.session_state.get("ps_provedor_manual", "Automático"),
            "fallback_automatico": fallback_chk, "gemini_so_visao": gemini_so_visao_chk,
            "modelo_groq": "llama3-70b-8192", "modelo_cloudflare": "@cf/meta/llama-3-8b-instruct",
            "modelo_padrao": "gemini-3.8-flash", "usar_busca_web": False
        }
        ok_salvo, erro_salvo = salvar_config(dados_salvos, st.session_state.get("user_email", ""))
        if ok_salvo:
            st.sidebar.success("✅ Motores conectados e prontos!")
        else:
            st.sidebar.warning(f"⚠️ {erro_salvo}")

# ==============================================================================
# 5.1 HISTÓRICO DE PROMPTS (via Apps Script)
# ==============================================================================
def _historico_sheets(email, prompt_texto=None, acao="listar"):
    """Lista ou adiciona prompts no histórico via Apps Script."""
    email = (email or "").strip().lower()
    if acao == "adicionar":
        if not prompt_texto or not str(prompt_texto).strip():
            return False, "Nenhum prompt para salvar."
        params = {"acao": "adicionar_historico", "email": email, "prompt": str(prompt_texto)[:12000]}
        resp = _req_apps_script(params, timeout=30)
        if resp and resp.get("ok"):
            return True, None
        return False, resp.get("erro", "Não foi possível salvar no servidor.")
    params = {"acao": "listar_historico", "email": email}
    resp = _req_apps_script(params, timeout=20)
    if resp and resp.get("ok"):
        return True, resp.get("itens", [])
    return False, []

def renderizar_historico():
    """Exibe na sidebar um expansor com os últimos prompts salvos."""
    with st.sidebar.expander("🕘 Histórico de Prompts", expanded=False):
        ok, itens = _historico_sheets(st.session_state.get("user_email", ""), acao="listar")
        if not ok:
            st.caption("Histórico indisponível no momento.")
            return
        if not itens:
            st.caption("Nenhum prompt salvo ainda.")
            return
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
        col_m1, col_m2 = st.columns(2)
        with col_m1: estilo_conversao = st.selectbox("Tradução de Estilo de Arte:", ["Manter Estilo Original", "📸 Converter para Fotorrealismo", "🎨 Converter para Anime"], key="ck_estilo_conversao")
        with col_m2: sens_escolhida = st.select_slider("Nível de Sensualidade & Modéstia:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider", value=st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1]))

    with st.container(border=True):
        st.markdown("### 🖼️ Extração Pericial de Imagem (Visão)")
        col_img1, col_img2 = st.columns([4, 6])
        with col_img1: img_file = st.file_uploader("Upload de Referência", type=["png", "jpg", "jpeg", "webp"], key="ck_img_uploader", label_visibility="collapsed")
        with col_img2:
            st.
