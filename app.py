# -*- coding: utf-8 -*-
"""
Prompt Studio Cockpit — Interface Profissional de Engenharia de Prompts
Versão: 5.1 (Revisão Gold - "Pure-Core")
Arquitetura: Separação de Vias (Visão/Texto), Estado Reativo (State Sync), Bypass de Segurança Nativo.
"""

import os
import json
import copy
import random
import re
import time
import html
import unicodedata
from datetime import datetime
import requests
from PIL import Image
import streamlit as st

# ==============================================================================
# 0. INICIALIZAÇÃO DE SDK
# ==============================================================================
try:
    from google import genai
    from google.genai import types
    SDK_DISPONIVEL = True
except ImportError:
    genai = None
    types = None
    SDK_DISPONIVEL = False

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==============================================================================
st.set_page_config(page_title="Prompt Studio Cockpit", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    :root { --ps-blue: #2563eb; --ps-gold: #b45309; }
    .ps-kicker { color: var(--ps-blue); font-size: .75rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-top: .4rem; }
    .ps-title { font-size: clamp(1.8rem, 3.2vw, 2.7rem); line-height: 1.15; margin: .2rem 0 .4rem; font-weight: 800; }
    .ps-slogan { font-size: 1.15rem; color: var(--ps-blue); font-weight: 700; margin-bottom: 2rem; border-left: 4px solid var(--ps-blue); padding-left: 12px; }
    .hero-title { font-size: 3.5rem; font-weight: 900; line-height: 1.1; margin-bottom: 1rem; text-align: center; letter-spacing: -0.03em; }
    .hero-subtitle { font-size: 1.2rem; opacity: 0.8; text-align: center; max-width: 700px; margin: 0 auto 3rem auto; line-height: 1.6; }
    .showcase-box { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 16px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    .label-ideia { font-size: 0.8rem; font-weight: 800; color: #2563eb; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .text-ideia { font-size: 1.1rem; font-style: italic; border-left: 4px solid #2563eb; padding-left: 1rem; margin-bottom: 1.5rem; }
    .label-prompt { font-size: 0.8rem; font-weight: 800; color: #b45309; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    .code-prompt { background: var(--background-color); padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem; height: 180px; overflow-y: auto; border: 1px solid rgba(128,128,128,0.2); }
    .plan-container { text-align: center; background: var(--secondary-background-color); padding: 2rem; border-radius: 16px; border: 1px solid rgba(128,128,128,0.2); margin-top: 2rem; }
    .byok-badge { display: inline-block; background: rgba(37, 99, 235, 0.1); color: #2563eb; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: bold; margin-bottom: 1rem; border: 1px solid rgba(37, 99, 235, 0.2); }
    .ps-preprompt { background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 12px; padding: 1.25rem 1.4rem; line-height: 1.85; font-size: 1.02rem; margin: 0.8rem 0 1.2rem; }
    .ps-user-word { font-weight: 700; background-color: rgba(37, 99, 235, 0.15); border-left: 2px solid #2563eb; padding: 2px 6px; border-radius: 4px; }
    .ps-ai-word { color: var(--ps-gold); font-weight: 600; }
    .ps-legend { display: flex; gap: 1.5rem; margin: .6rem 0 .9rem; font-size: .88rem; font-weight: 600; align-items: center; }
    .comp-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 700; padding: 4px 10px; border-radius: 9999px; margin-right: 6px; margin-bottom: 6px; }
    .comp-green { background-color: rgba(5, 150, 105, 0.1); color: #10b981; border: 1px solid rgba(5, 150, 105, 0.3); }
    .comp-amber { background-color: rgba(217, 119, 6, 0.1); color: #f59e0b; border: 1px solid rgba(217, 119, 6, 0.3); }
    .comp-blue  { background-color: rgba(37, 99, 235, 0.1); color: #3b82f6; border: 1px solid rgba(37, 99, 235, 0.3); }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSTANTES, REGRAS E BANCO DE MOTORES
# ==============================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzgEj3YPwqiUbiueyu8wjZ9ZZK0Rcc6G3kucysRSJ2gNmzRzUdMuLqv_q55N1kSO8PQ/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/xo0m3rF"

PASTA_CONFIGS = "configs_usuarios"

OPCOES_SENSUALIDADE = [
    "1 - Seguro (SFW)", "2 - Menos Seguro", "3 - Ecchi Leve", 
    "4 - Ecchi", "5 - Picante", "6 - Dual (Com & Sem Censura)"
]

BANCO_DE_MOTORES = {
    "ComfyUI / Pony SDXL": {
        "regra_positivo": "PRIMEIRO, extraia o sujeito e a roupa da narrativa visual. Ordem de Tags OBRIGATÓRIA: 1. Qualidade (score_9, score_8_up) -> 2. CONTAGEM E GÊNERO (ex: 1boy, solo) -> 3. PROFISSÃO/ESPÉCIE -> 4. Vestuário -> 5. Ação -> 6. Cenário.",
        "regra_negativo": "BASE INEGOCIÁVEL: score_6, score_5, score_4, score_3, score_2, score_1, worst quality, low quality, normal quality, text, watermark, jpeg artifacts, ugly, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, mutated, deformed.",
        "dica_tecnica": "Modelos baseados no Pony dependem estritamente da tag de gênero no início."
    },
    "ComfyUI / Illustrious": {
        "regra_positivo": "Traduza fielmente a cena. PREFIXO OBRIGATÓRIO: masterpiece, best quality, ultra-detailed, illustration. Em seguida adicione a contagem e gênero do sujeito.",
        "regra_negativo": "Base: lowres, bad quality, worst quality, bad anatomy, bad hands, text, error, missing fingers, cropped, signature, watermark.",
        "dica_tecnica": "Mantenha CFG entre 5.0 e 7.0."
    },
    "Flux.1 / Flux.2 (Klein)": {
        "regra_positivo": "Traduza TODA a cena para o inglês em um parágrafo longo, fluido e hiper-descritivo. SEM tags isoladas por vírgula. Sujeito, roupa e cenário devem ser descritos como uma fotografia.",
        "regra_negativo": None,
        "dica_tecnica": "Modelos Flux operam melhor sem prompt negativo. Foque na prosa fotográfica."
    },
    "Midjourney v6.1+": {
        "regra_positivo": "REGRA MÁXIMA: Comece descrevendo o SUJEITO, A ROUPA e a AÇÃO. Depois o CENÁRIO. Adicione termos de estética cinematográfica (ex: cinematic lighting) e câmera no final. Termine com: --ar 16:9 --v 6.1 --stylize 250",
        "regra_negativo": None, 
        "dica_tecnica": "Não sobreponha a estética ao sujeito principal."
    },
    "ComfyUI / SDXL Base Natural": {
        "regra_positivo": "FÓRMULA: 'A breathtaking photo of [Sujeito + Roupas], who is [Ação], located in [Cenário Detalhado]. The lighting is [Iluminação]. Shot on [Câmera]'.",
        "regra_negativo": "Base: ugly, deformed, poorly drawn, bad anatomy, missing limbs, mutated hands, unnatural proportions, amateur, watermark.",
        "dica_tecnica": "Refiner em 20% ajuda nos detalhes de rostos."
    },
    "Ideogram 4": {
        "regra_positivo": "Traduza com foco em diagramação. Qualquer texto escrito DEVE ficar ENTRE ASPAS DUPLAS (ex: wearing a shirt that says \"HELLO\").",
        "regra_negativo": None,
        "dica_tecnica": "Perfeito para criar placas, logos e textos legíveis."
    }
}

OPCOES_DESTINO = ["Selecione o Motor Destino..."] + list(BANCO_DE_MOTORES.keys())

# ==============================================================================
# 3. SEGURANÇA E PERSISTÊNCIA (APPS SCRIPT / FERNET)
# ==============================================================================
def mascarar_email(email):
    if not email or "@" not in email: return email
    nome, dominio = email.split("@", 1)
    return f"{nome[:3]}***@{dominio}" if len(nome) > 3 else f"{nome}***@{dominio}"

def normalizar_texto(texto):
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")

def parse_json_ia(texto):
    if not texto: return None
    limpo = re.sub(r"^```(?:json)?\s*", "", str(texto).strip(), flags=re.IGNORECASE)
    limpo = re.sub(r"\s*```$", "", limpo).strip()
    try: return json.loads(limpo)
    except json.JSONDecodeError: pass
    
    inicio = limpo.find("{")
    if inicio < 0: return None
    
    profundidade = 0; em_string = False; escapado = False; fim = None
    for i, c in enumerate(limpo[inicio:], start=inicio):
        if em_string:
            if escapado: escapado = False
            elif c == "\\": escapado = True
            elif c == '"': em_string = False
            continue
        if c == '"': em_string = True
        elif c == "{": profundidade += 1
        elif c == "}":
            profundidade -= 1
            if profundidade == 0:
                fim = i + 1
                break
    try: return json.loads(limpo[inicio:fim]) if fim else None
    except Exception: return None

def _obter_fernet():
    segredo = st.secrets.get("PS_FERNET_KEY") or os.environ.get("PS_FERNET_KEY")
    if not segredo: return None
    try:
        import base64, hashlib
        from cryptography.fernet import Fernet
        digest = hashlib.sha256(segredo.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
    except Exception: return None

def encriptar(t):
    f = _obter_fernet()
    return f.encrypt(t.encode("utf-8")).decode("utf-8") if f and t else t

def desencriptar(t):
    f = _obter_fernet()
    try: return f.decrypt(t.encode("utf-8")).decode("utf-8") if f and t else t
    except Exception: return t

def _request_seguro(method, url, **kwargs):
    for tentativa in range(3):
        try:
            resposta = requests.request(method, url, **kwargs)
            if resposta.status_code not in (429, 500, 502, 503, 504) or tentativa == 2:
                return resposta
            time.sleep(2 ** tentativa)
        except requests.RequestException:
            if tentativa == 2: raise
            time.sleep(2 ** tentativa)
    raise RuntimeError("Falha HTTP.")

def carregar_configuracoes(email):
    email_norm = (email or "").strip().lower()
    config_padrao = {"chaves": {"Chave Visao": "", "Chave Texto": ""}, "modelo_padrao": "gemini-3.5-flash"}
    
    try:
        resp = _request_seguro("GET", APPS_SCRIPT_URL, params={"acao": "carregar_config", "email": email_norm}, timeout=15)
        if resp.status_code == 200 and resp.json().get("ok") and resp.json().get("config"):
            dados = json.loads(resp.json()["config"])
            if "Chave 1" in dados.get("chaves", {}): dados["chaves"]["Chave Visao"] = dados["chaves"].pop("Chave 1")
            if "Chave 2" in dados.get("chaves", {}): dados["chaves"]["Chave Texto"] = dados["chaves"].pop("Chave 2")
            config_padrao.update(dados)
            config_padrao["chaves"] = {k: desencriptar(v) for k, v in config_padrao.get("chaves", {}).items()}
            return config_padrao
    except Exception: pass

    caminho = os.path.join(PASTA_CONFIGS, f"config_{re.sub(r'[^\w\-.]', '_', email_norm)}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                config_padrao.update(dados)
                config_padrao["chaves"] = {k: desencriptar(v) for k, v in config_padrao.get("chaves", {}).items()}
        except Exception: pass
    return config_padrao

def salvar_configuracoes(email, dados):
    email_norm = (email or "").strip().lower()
    dados_enc = copy.deepcopy(dados)
    dados_enc["chaves"] = {k: encriptar(v) for k, v in dados_enc.get("chaves", {}).items()}
    
    try:
        resp = _request_seguro("POST", APPS_SCRIPT_URL, json={"acao": "salvar_config", "email": email_norm, "config": json.dumps(dados_enc, ensure_ascii=False)}, timeout=20)
        if resp.status_code == 200 and resp.json().get("ok"): return True, None
    except Exception: pass

    os.makedirs(PASTA_CONFIGS, exist_ok=True)
    try:
        with open(os.path.join(PASTA_CONFIGS, f"config_{re.sub(r'[^\w\-.]', '_', email_norm)}.json"), "w", encoding="utf-8") as f:
            json.dump(dados_enc, f, indent=4, ensure_ascii=False)
        return False, "Salvo apenas localmente."
    except Exception as e: return False, str(e)

def validar_acesso(email):
    try:
        resp = _request_seguro("GET", APPS_SCRIPT_URL, params={"acao": "verificar_acesso", "email": (email or "").strip().lower()}, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            if not d.get("encontrado"): return False, d.get("expiracao", ""), "E-mail não registado."
            exp = str(d.get("expiracao", "")).strip()
            if exp:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                    try:
                        if datetime.strptime(exp.split("T")[0], fmt).date() < datetime.now().date(): return False, exp, "Acesso expirado."
                        break
                    except Exception: continue
            return True, exp, None
        return False, "", "Falha no servidor de autenticação."
    except Exception as e: return False, "", f"Erro de rede: {e}"

def gerir_historico(acao, email, prompt=None):
    email_norm = (email or "").strip().lower()
    if acao == "adicionar" and prompt:
        try:
            payload = {"acao": "adicionar_historico", "email": email_norm, "prompt": str(prompt)[:25000], "_truncado": len(str(prompt)) > 25000}
            resp = _request_seguro("POST", APPS_SCRIPT_URL, json=payload, timeout=20)
            return (True, None) if resp.status_code == 200 and resp.json().get("ok") else (False, "Falha ao gravar.")
        except Exception as e: return False, str(e)
    elif acao == "listar":
        try:
            resp = _request_seguro("GET", APPS_SCRIPT_URL, params={"acao": "listar_historico", "email": email_norm}, timeout=15)
            return (True, resp.json().get("itens", [])) if resp.status_code == 200 and resp.json().get("ok") else (False, [])
        except Exception: return False, []

# ==============================================================================
# 4. MOTORES DE IA (VISÃO E TEXTO ISOLADOS COM BLOCK_NONE)
# ==============================================================================
def criar_config_seguranca(instrucao_sistema, temperatura):
    """Bypass absoluto dos Safety Settings para evitar respostas em branco no SDK atual."""
    if types:
        safety_settings = [
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        ]
        return types.GenerateContentConfig(system_instruction=instrucao_sistema, temperature=temperatura, safety_settings=safety_settings)
    return {"system_instruction": instrucao_sistema, "temperature": temperatura}

def _tratar_erro_api(e):
    err = str(e).lower()
    if "401" in err or "unauthorized" in err: return "🔑 Chave de API inválida ou revogada."
    if "404" in err or "not found" in err: return "⚠️ Modelo não encontrado. Verifique o nome do modelo nas configurações avançadas."
    if "429" in err or "quota" in err: return "⏳ Limite de uso atingido. A sua chave esgotou a cota gratuita do dia."
    if "503" in err or "overloaded" in err: return "🔌 Servidores da Google estão sobrecarregados. Tente novamente."
    return f"⚠️ Erro do Motor IA: {str(e)[:250]}"

# --- VIA DE VISÃO ---
SYS_VISAO = r"""Motor de Extração Óptica (Dense Captioning). Desconstrua pericialmente a imagem.
Retorne EXCLUSIVAMENTE um JSON: {"sujeito": "...", "acao": "...", "cenario": "...", "iluminacao": "...", "estilo_camera": "..."}"""

def extrair_imagem_visao(arquivo, estilo, sensualidade, modelo):
    if not SDK_DISPONIVEL: raise RuntimeError("Biblioteca 'google-genai' não instalada no servidor.")
    if arquivo.size > 10 * 1024 * 1024: raise RuntimeError("Imagem excede 10MB.")
    
    cfg = carregar_configuracoes(st.session_state.get("user_email"))
    chave = cfg.get("chaves", {}).get("Chave Visao", "").strip()
    if not chave: raise RuntimeError("🔑 Chave de Visão ausente. Adicione no painel lateral.")

    prompt = f"Desconstrua em Ultra-Densidade.\n[MODIFICADOR - SENSUALIDADE]: Nível {sensualidade}."
    if "Fotorrealismo" in estilo: prompt += " Traduza para o MUNDO REAL fotorrealista."
    elif "Anime" in estilo: prompt += " Traduza para ILUSTRAÇÃO 2D ANIME."

    try:
        arquivo.seek(0)
        img = Image.open(arquivo)
        client = genai.Client(api_key=chave)
        configuracao = criar_config_seguranca(SYS_VISAO, 0.2)
        resposta = client.models.generate_content(model=modelo.strip(), contents=[img, prompt], config=configuracao)
        
        texto = getattr(resposta, "text", "") or ""
        if not texto.strip(): raise RuntimeError("A Google devolveu uma resposta em branco. O bypass de segurança falhou ou a região foi bloqueada.")
        
        dados_json = parse_json_ia(texto)
        return {"tipo": "json", "dados": dados_json} if dados_json else {"tipo": "texto", "texto": texto}
    except Exception as e:
        raise RuntimeError(_tratar_erro_api(e))

# --- VIA DE TEXTO ---
SYS_RASCUNHO = "Diretor de Arte Visual. Gere um Pré-Prompt em Português detalhando a cena. PRESERVE A IDEIA. SEM FLUFF. APENAS DESCRIÇÃO VISUAL."
SYS_AUDITOR = 'Auditor de Composição. Retorne JSON: {"sujeito_status": "Definido|Vago", "acao_status": "Presente|Estática", "cenario_status": "Definido|Vago", "iluminacao_status": "...", "camera_status": "...", "diagnostico_texto": "...", "sugestoes_cirurgicas": ["..."]}'
SYS_SINTESE = r"""Engenheiro de Prompts. Traduza a cena para Inglês (Obrigatório). 
Injete tags de Rating correspondentes. 
OBRIGATÓRIO: Crie um NEGATIVE PROMPT DINÂMICO baseando-se no positivo e adicione as regras fixas do motor."""

def executar_motor_texto(sys_prompt, user_prompt, modelo, temp=0.25):
    if not SDK_DISPONIVEL: raise RuntimeError("Biblioteca 'google-genai' não instalada no servidor.")
    
    cfg = carregar_configuracoes(st.session_state.get("user_email"))
    chave = cfg.get("chaves", {}).get("Chave Texto", "").strip()
    if not chave: raise RuntimeError("🔑 Chave de Texto ausente. Adicione no painel lateral.")
    
    try:
        client = genai.Client(api_key=chave)
        configuracao = criar_config_seguranca(sys_prompt, temp)
        resposta = client.models.generate_content(model=modelo.strip(), contents=user_prompt, config=configuracao)
        texto = getattr(resposta, "text", "") or ""
        if not texto.strip(): raise RuntimeError("O modelo retornou uma resposta em branco (Possível bloqueio de segurança regional).")
        return texto.strip()
    except Exception as e:
        raise RuntimeError(_tratar_erro_api(e))

# ==============================================================================
# 5. RENDERIZAÇÃO DA INTERFACE (UI)
# ==============================================================================
def diff_visual(original, editado):
    norm_orig = {normalizar_texto(w) for w in re.findall(r"[\wÀ-ÿ'-]+", original or "") if len(w)>2}
    pieces = []
    for token in re.split(r"(\s+|[^\wÀ-ÿ'-]+)", str(editado or "")):
        if not token: continue
        if re.match(r"^[\wÀ-ÿ'-]+$", token):
            n_tok = normalizar_texto(token)
            pieces.append(f'<span class="ps-user-word">{html.escape(token)}</span>' if n_tok in norm_orig else f'<span class="ps-ai-word">{html.escape(token)}</span>')
        else: pieces.append(html.escape(token))
    return "".join(pieces)

def renderizar_sidebar():
    st.sidebar.markdown("<div style='font-size: 0.95rem; color: var(--ps-blue); font-weight: 700; margin-bottom: 1rem;'>A porta é nossa, as chaves são suas.</div>", unsafe_allow_html=True)
    st.sidebar.markdown("## ⚙️ Conexão de Motores")
    st.sidebar.caption(f"Usuário: **{mascarar_email(st.session_state.get('user_email', ''))}**")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False; st.rerun()

    cfg = carregar_configuracoes(st.session_state.get("user_email"))
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("<a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#059669; text-decoration:none;'>👁️ Chave Gemini (Via Visão)</a>", unsafe_allow_html=True)
    k_vis = st.sidebar.text_input("Visão", value=cfg.get("chaves", {}).get("Chave Visao", ""), type="password", label_visibility="collapsed")
    
    st.sidebar.markdown("<br><a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#2563eb; text-decoration:none;'>📝 Chave Gemini (Via Texto)</a>", unsafe_allow_html=True)
    k_txt = st.sidebar.text_input("Texto", value=cfg.get("chaves", {}).get("Chave Texto", ""), type="password", label_visibility="collapsed")

    with st.sidebar.expander("Ferramentas Avançadas"):
        st.caption("Especifique a versão exata do modelo:")
        mod_base = st.text_input("Modelo Gemini", value=cfg.get("modelo_padrao", "gemini-3.5-flash"))

    if st.sidebar.button("💾 Salvar Conexões", type="primary", use_container_width=True):
        ok, erro = salvar_configuracoes(st.session_state.get("user_email"), {"chaves": {"Chave Visao": k_vis, "Chave Texto": k_txt}, "modelo_padrao": mod_base})
        if ok: st.sidebar.success("Conectado!")
        else: st.sidebar.warning(erro)

    # Histórico
    with st.sidebar.expander("🕘 Histórico de Prompts"):
        ok, itens = gerir_historico("listar", st.session_state.get("user_email"))
        if ok and itens:
            for item in itens[-10:]:
                ts = item.get("quando", "")[:16]
                if st.button(f"{ts} — {str(item.get('prompt', ''))[:40]}...", key=f"hist_{item.get('id', ts)}", use_container_width=True):
                    abrir_modal_historico(item.get("prompt", ""))
        else: st.caption("Nenhum prompt.")

@st.dialog("📝 Visualizador de Histórico")
def abrir_modal_historico(conteudo):
    st.code(conteudo, language="markdown")
    st.download_button("📥 Baixar Prompt (.txt)", data=conteudo, file_name=f"historico_{int(time.time())}.txt", use_container_width=True)

def inicializar_estado():
    chaves_base = ["ideia_principal", "draft_editado", "draft_ia", "diag_dados", "sugestoes_marcadas", "prompt_final_codigo", "visao_json"]
    for k in chaves_base:
        if k not in st.session_state: st.session_state[k] = None

def limpar_estado_geral():
    chaves_base = ["ideia_principal", "draft_editado", "draft_ia", "diag_dados", "sugestoes_marcadas", "prompt_final_codigo", "visao_json"]
    for k in chaves_base:
        st.session_state[k] = None

def renderizar_cockpit():
    inicializar_estado()
    cfg = carregar_configuracoes(st.session_state.get("user_email"))
    modelo_ativo = cfg.get("modelo_padrao", "gemini-3.5-flash")

    st.markdown("<div class='ps-kicker'>PROMPT STUDIO COCKPIT</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='ps-title'>Sua Ideia. Seu Motor.</h1>", unsafe_allow_html=True)
    st.markdown("<div class='ps-slogan'>A porta é nossa, as chaves são suas.</div>", unsafe_allow_html=True)

    # --- PASSO 1: IDEIA ---
    st.markdown("### 1️⃣ Passo 1: A Narrativa Visual")
    texto_atual = st.text_area("Ideia:", value=st.session_state.ideia_principal or "", height=140, label_visibility="collapsed")
    if texto_atual != (st.session_state.ideia_principal or ""):
        st.session_state.ideia_principal = texto_atual

    if st.button("🗑️ Limpar Tudo", use_container_width=False):
        limpar_estado_geral(); st.rerun()

    # --- PASSO 2: VISÃO ---
    st.markdown("---")
    st.markdown("### 2️⃣ Passo 2: Referência Óptica (Opcional)")
    c_img, c_btn = st.columns([4, 6])
    with c_img: file_up = st.file_uploader("Upload", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")
    with c_btn:
        st.write(" ")
        if st.button("👁️ Extrair Cena da Imagem", use_container_width=True):
            if not file_up: st.warning("Anexe uma imagem.")
            else:
                with st.spinner("Extraindo matriz óptica..."):
                    try:
                        res = extrair_imagem_visao(file_up, st.session_state.get("ui_estilo", ""), st.session_state.get("ui_sens", OPCOES_SENSUALIDADE[1]), modelo_ativo)
                        if res["tipo"] == "json":
                            st.session_state.visao_json = res["dados"]
                            st.session_state.ideia_principal = f"Sujeito: {res['dados'].get('sujeito','')}\nAção: {res['dados'].get('acao','')}\nCenário: {res['dados'].get('cenario','')}\nLuz: {res['dados'].get('iluminacao','')}\nEstilo: {res['dados'].get('estilo_camera','')}"
                        else:
                            st.session_state.ideia_principal = res["texto"]
                            st.session_state.visao_json = None
                        
                        # Reseta os passos seguintes
                        st.session_state.draft_ia = None; st.session_state.prompt_final_codigo = None
                        st.rerun()
                    except Exception as e: st.error(str(e))

    # --- PASSO 3: MODIFICADORES ---
    st.markdown("---")
    st.markdown("### 3️⃣ Passo 3: Modificadores Globais")
    with st.container(border=True):
        cm1, cm2, cm3 = st.columns(3)
        with cm1: st.selectbox("Estilo:", ["Manter Original", "Fotorrealismo", "Anime"], key="ui_estilo")
        with cm2: st.selectbox("Foco:", ["Harmônico", "Literal (Sem floreios)"], key="ui_foco")
        with cm3: st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ui_sens", value=OPCOES_SENSUALIDADE[1])

    # --- PASSO 4: RASCUNHO & VALIDAÇÃO ---
    st.markdown("---")
    st.markdown("### 4️⃣ Passo 4: Rascunho & Auditoria")
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("👁️ Rascunhar Cena (Texto)", use_container_width=True):
            if not st.session_state.ideia_principal: st.warning("Preencha o Passo 1.")
            else:
                with st.spinner("Rascunhando..."):
                    try:
                        p = f"IDEIA:\n{st.session_state.ideia_principal}\n[SENS: {st.session_state.ui_sens}]"
                        if "Literal" in st.session_state.ui_foco: p += "\n[LITERAL]: Sem floreios."
                        txt = executar_motor_texto(SYS_GERADOR_PREPROMPT, p, modelo_ativo)
                        st.session_state.draft_ia = txt
                        st.session_state.draft_editado = txt
                        st.rerun()
                    except Exception as e: st.error(str(e))
    with cb2:
        if st.button("🔍 Auditar Composição", use_container_width=True):
            if not st.session_state.ideia_principal: st.warning("Preencha o Passo 1.")
            else:
                with st.spinner("Raio-X..."):
                    try:
                        txt = executar_motor_texto(SYS_COMPOSITOMETRO, f"AVALIE:\n{st.session_state.ideia_principal}", modelo_ativo)
                        st.session_state.diag_dados = parse_json_ia(txt)
                        st.rerun()
                    except Exception as e: st.error(str(e))

    if st.session_state.draft_ia:
        st.markdown("<div class='ps-legend'><span><span class='ps-user-word'>Ideia Original</span></span> • <span><span class='ps-ai-word'>Ajuste IA</span></span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ps-preprompt'>{diff_visual(st.session_state.draft_ia, st.session_state.ideia_principal)}</div>", unsafe_allow_html=True)
        
        ed = st.text_area("Ajuste Fino Manual (Vai para o Motor):", value=st.session_state.draft_editado or "", height=130)
        if ed != (st.session_state.draft_editado or ""): st.session_state.draft_editado = ed

    if st.session_state.diag_dados:
        d = st.session_state.diag_dados
        with st.container(border=True):
            cols = st.columns(5)
            for i, (k, lbl) in enumerate([("sujeito_status","Sujeito"), ("acao_status","Ação"), ("cenario_status","Cenário"), ("iluminacao_status","Luz"), ("camera_status","Câmera")]):
                stt = d.get(k, "")
                cl, ic = ("comp-green","✓") if stt in ["Definido","Presente"] else ("comp-amber","!") if stt in ["Vago","Estática"] else ("comp-blue","⚙️")
                cols[i].markdown(f"<div class='comp-badge {cl}'>{ic} {lbl}: {stt}</div>", unsafe_allow_html=True)
            if d.get("diagnostico_texto"): st.caption(f"**Diagnóstico:** {d['diagnostico_texto']}")
            sugs = d.get("sugestoes_cirurgicas", [])
            st.session_state.sugestoes_marcadas = [s for s in sugs if st.checkbox(s, key=f"sug_{s}")] if sugs else []

    # --- PASSO 5: SÍNTESE FINAL ---
    st.markdown("---")
    st.markdown("### 5️⃣ Passo 5: Motor Destino & Síntese Final")
    cd1, cd2 = st.columns([6, 4])
    with cd1: motor_alvo = st.selectbox("Plataforma Alvo:", OPCOES_DESTINO, index=0)
    with cd2:
        st.write(" ")
        if st.button("⚡ Compilar Código do Prompt", type="primary", use_container_width=True):
            if motor_alvo == OPCOES_DESTINO[0]: st.error("Selecione um motor válido.")
            elif not st.session_state.ideia_principal: st.warning("Preencha a Ideia base.")
            else:
                with st.spinner("Compilando sintaxe..."):
                    try:
                        eng = BANCO_DE_MOTORES[motor_alvo]
                        base = st.session_state.draft_editado or st.session_state.ideia_principal
                        sugs = "\n".join(f"- {s}" for s in (st.session_state.sugestoes_marcadas or [])) or "Nenhuma."
                        
                        p_sys = f"{SYS_MESTRE_CORE}\n\nSINTAXE: {motor_alvo}\nPOS: {eng['regra_positivo']}\nNEG FIXO: {eng.get('regra_negativo','N/A')}\nSAÍDA: 1. PROMPT (EN) 2. NEGATIVE (EN) 3. LEGENDA"
                        p_usr = f"DESTINO: {motor_alvo}\nRATING: {st.session_state.ui_sens}\n\nCENA:\n{base}\n\nSUGESTÕES:\n{sugs}"
                        if "Literal" in st.session_state.ui_foco: p_usr += "\n[MODO LITERAL]: Sem floreios."
                        
                        st.session_state.prompt_final_codigo = executar_motor_texto(p_sys, p_usr, modelo_ativo)
                        st.rerun()
                    except Exception as e: st.error(str(e))

    if st.session_state.prompt_final_codigo:
        st.markdown("---")
        st.markdown("### 📋 Prompt Especializado")
        st.code(st.session_state.prompt_final_codigo, language="markdown", wrap_lines=True)
        
        c_sav, c_dwn = st.columns(2)
        with c_sav:
            if st.button("💾 Gravar no Histórico", use_container_width=True):
                ok, err = gerir_historico("adicionar", st.session_state.get("user_email"), st.session_state.prompt_final_codigo)
                if ok: st.success("Salvo!")
                else: st.warning(err)
        with c_dwn:
            st.download_button("📥 Baixar (.txt)", data=st.session_state.prompt_final_codigo, file_name=f"prompt_{int(time.time())}.txt", use_container_width=True)

# ==============================================================================
# 6. PONTO DE ENTRADA E LOGIN
# ==============================================================================
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<div class='hero-title'>Pare de lutar contra a IA.<br>Retome o controle.</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>IDE Profissional para criadores de imagem. Sem filtros ocultos.</div>", unsafe_allow_html=True)
    c_l1, c_l2, c_l3 = st.columns([1, 4, 1])
    with c_l2:
        st.markdown("<div class='plan-container'>", unsafe_allow_html=True)
        st.markdown("<div class='byok-badge'>🔒 Modelo BYOK: Conecte sua própria chave API.</div>", unsafe_allow_html=True)
        st.markdown("### 🚀 Acesse o Cockpit Agora")
        
        cp1, cp2, cp3 = st.columns(3)
        with cp1: st.link_button("15 Dias (R$ 14,99)", LINK_KIWIFY_15_DIAS, use_container_width=True)
        with cp2: st.link_button("30 Dias (R$ 29,99)", LINK_KIWIFY_30_DIAS, use_container_width=True)
        with cp3: st.link_button("90 Dias (R$ 59,99)", LINK_KIWIFY_90_DIAS, use_container_width=True)
        st.divider()
        
        email_login = st.text_input("E-mail Cadastrado na Kiwify:", placeholder="seu-email@exemplo.com")
        if st.button("Entrar", type="primary", use_container_width=True):
            if not email_login.strip(): st.warning("Digite seu e-mail.")
            else:
                ok, exp, erro = validar_acesso(email_login)
                if ok: st.session_state.update({"autenticado": True, "user_email": email_login}); st.rerun()
                else: st.error(erro)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    renderizar_sidebar()
    renderizar_cockpit()
