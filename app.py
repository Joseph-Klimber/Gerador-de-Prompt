# -*- coding: utf-8 -*-
"""
Prompt Studio Cockpit — Interface Minimalista de Alta Precisão
Atrito zero para o usuário: Entrada livre de ideias + Compositômetro inteligente +
Slider de Sensualidade com alerta transparente de risco de censura +
Motor técnico mestre com física óptica avançada e negativos compostos calibrados
nativamente por arquitetura de difusão. Exportação em .TXT e .JSON estruturado.
"""

import os
import json
import re
import secrets
import time
import html
import unicodedata
from datetime import datetime
import requests
import streamlit as st

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM (CSS COCKPIT)
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
        --ps-ink: #0f172a;
        --ps-muted: #475569;
        --ps-line: #e2e8f0;
        --ps-blue: #2563eb;
        --ps-blue-subtle: #eff6ff;
        --ps-gold: #b45309;
        --ps-emerald: #059669;
        --ps-amber: #d97706;
        --ps-rose: #e11d48;
    }
    .ps-brand {
        color: var(--ps-ink);
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: .15em;
        margin-top: .2rem;
    }
    .ps-header-note {
        color: var(--ps-muted);
        font-size: .88rem;
        margin-bottom: 1.1rem;
    }
    .ps-kicker {
        color: var(--ps-blue);
        font-size: .75rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-top: .4rem;
    }
    .ps-title {
        color: var(--ps-ink);
        font-size: clamp(1.8rem, 3.2vw, 2.7rem);
        line-height: 1.15;
        margin: .2rem 0 .4rem;
        font-weight: 800;
    }
    .ps-subtitle {
        color: var(--ps-muted);
        font-size: 1.02rem;
        max-width: 820px;
        margin-bottom: 1.2rem;
    }
    .ps-login {
        max-width: 680px;
        margin: 2.5rem auto 1rem;
        text-align: center;
    }
    .ps-preprompt {
        background: #ffffff;
        border: 1px solid var(--ps-line);
        border-radius: 12px;
        padding: 1.25rem 1.4rem;
        line-height: 1.85;
        font-size: 1.02rem;
        color: var(--ps-ink);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin: 0.8rem 0 1.2rem;
    }
    .ps-user-word {
        color: var(--ps-blue);
        font-weight: 700;
        background-color: var(--ps-blue-subtle);
        padding: 2px 6px;
        border-radius: 4px;
    }
    .ps-ai-word {
        color: var(--ps-gold);
        font-weight: 600;
    }
    .ps-legend {
        display: flex;
        gap: 1.5rem;
        margin: .6rem 0 .9rem;
        font-size: .88rem;
        font-weight: 600;
        align-items: center;
    }
    .comp-container {
        background: #ffffff;
        border: 1px solid var(--ps-line);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .comp-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 9999px;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .comp-green { background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .comp-amber { background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .comp-blue  { background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    
    .risk-banner {
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .risk-green { background: #ecfdf5; border-left: 4px solid var(--ps-emerald); color: #065f46; }
    .risk-amber { background: #fffbeb; border-left: 4px solid var(--ps-amber); color: #92400e; }
    .risk-rose  { background: #fff1f2; border-left: 4px solid var(--ps-rose); color: #9f1239; }

    code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    div[data-baseweb="select"] * {
        white-space: normal !important;
        text-overflow: clip !important;
        word-break: break-word !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CONSTANTES, DIRETÓRIOS E LISTAS
# ==============================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyLlqkhYChBHM6K08DnNP67C9t7E2kRS3N0pINa65oYa81--Cv4amoJm3OZ_v_MSDA7/exec"
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

OPCOES_DESTINO = [
    "Recomendado automaticamente",
    "Flux.1 (Dev/Schnell) -> Nano Banana / Fal.ai",
    "ComfyUI / Pony SDXL -> ComfyUI / Forge (Anime & NSFW Local)",
    "ComfyUI / Illustrious -> ComfyUI / WebUI (Anime & 2D Moderno)",
    "ComfyUI / SDXL Base Natural -> Fooocus / ComfyUI (RealVis & Juggernaut)",
    "Midjourney v6.1 -> Midjourney (Discord / Web)",
    "Ideogram 2.0 -> Ideogram.ai (Design & Tipografia)",
    "DALL-E 3 / Bing Image Creator -> ChatGPT Plus / Copilot Designer",
    "Leonardo.Ai / SeaArt -> Leonardo.Ai / SeaArt.ai",
]

# ==============================================================================
# 3. AUTENTICAÇÃO E GESTÃO DE USUÁRIO
# ==============================================================================
def _slug_usuario(email):
    email_limpo = (email or "anonimo").strip().lower()
    return re.sub(r'[^\w\-.]', '_', email_limpo) or "anonimo"


def verificar_acesso_sheets(email):
    """Verifica e-mail e checa se a assinatura está dentro da validade."""
    try:
        email_limpo = (email or "").strip().lower()
        response = requests.get(
            APPS_SCRIPT_URL,
            params={"email": email_limpo},
            timeout=15,
            allow_redirects=True
        )
        if response.status_code == 200:
            try:
                dados = response.json()
                encontrado = dados.get("encontrado", False)
                expiracao_str = str(dados.get("expiracao", "")).strip()

                if not encontrado:
                    return False, expiracao_str, "⚠️ E-mail não encontrado na base de clientes autorizados."

                if expiracao_str:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            dt_clean = expiracao_str.split("T")[0].split(" ")[0].strip()
                            dt_exp = datetime.strptime(dt_clean, fmt)
                            if dt_exp.date() < datetime.now().date():
                                return False, expiracao_str, f"⚠️ Seu acesso expirou em {expiracao_str}. Renove seu plano para continuar gerando."
                            break
                        except Exception:
                            continue

                return True, expiracao_str, None
            except Exception:
                return False, "", "⚠️ Resposta com formato inválido do servidor."
        else:
            return False, "", f"⚠️ Servidor respondeu com código de erro {response.status_code}."
    except requests.exceptions.Timeout:
        return False, "", "⚠️ A conexão com o servidor demorou a responder. Tente novamente."
    except Exception as e:
        return False, "", f"⚠️ Falha na conexão: {e}"


def carregar_config(email=None):
    config = {
        "chaves": {"Chave 1": "", "Chave 2": ""},
        "groq_api_key": "",
        "cloudflare_account_id": "",
        "cloudflare_api_token": "",
        "provedor_ia": "Gemini",
        "fallback_automatico": True,
        "modelo_groq": "llama-3.3-70b-versatile",
        "modelo_cloudflare": "@cf/meta/llama-3.3-70b-instruct",
        "modelo_padrao": "gemini-2.5-flash",
        "usar_busca_web": False,
    }
    slug = _slug_usuario(email)
    caminho = os.path.join(PASTA_CONFIGS, f"config_{slug}.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

    if not config["chaves"].get("Chave 1") and os.path.exists(".api_key.txt"):
        try:
            with open(".api_key.txt", "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    config["chaves"]["Chave 1"] = k
        except Exception:
            pass

    return config


def salvar_config(chaves_dict, modelo_padrao, usar_busca_web=False, email=None,
                  groq_api_key="", cloudflare_account_id="", cloudflare_api_token="",
                  provedor_ia="Gemini", fallback_automatico=True,
                  modelo_groq="llama-3.3-70b-versatile", modelo_cloudflare="@cf/meta/llama-3.3-70b-instruct"):
    dados = {
        "chaves": chaves_dict,
        "groq_api_key": groq_api_key,
        "cloudflare_account_id": cloudflare_account_id,
        "cloudflare_api_token": cloudflare_api_token,
        "provedor_ia": provedor_ia,
        "fallback_automatico": fallback_automatico,
        "modelo_groq": modelo_groq,
        "modelo_cloudflare": modelo_cloudflare,
        "modelo_padrao": modelo_padrao,
        "usar_busca_web": usar_busca_web,
    }
    os.makedirs(PASTA_CONFIGS, exist_ok=True)
    slug = _slug_usuario(email)
    caminho = os.path.join(PASTA_CONFIGS, f"config_{slug}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def _gerar_nome_arquivo_base(destino, sens_escolhida):
    """Gera o nome do arquivo identificando a linguagem/motor, nível SFW e timestamp."""
    nome_motor = destino.split("->")[0].strip() if "->" in destino else destino
    slug_motor = re.sub(r'[^\w]', '_', nome_motor.lower())
    slug_motor = re.sub(r'_+', '_', slug_motor).strip('_')

    slug_sens = re.sub(r'[^\w]', '_', sens_escolhida.lower())
    slug_sens = re.sub(r'_+', '_', slug_sens).strip('_')

    data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"prompt_{slug_motor}_sfw_{slug_sens}_{data_str}"


def _estruturar_prompt_json(texto_prompt, destino, nivel_sens, ideia_orig, preprompt, provedor):
    """Estrutura o resultado em JSON técnico e organizado com metadados da geração."""
    dados = {
        "metadata": {
            "motor_alvo": destino,
            "nivel_sensualidade": nivel_sens,
            "data_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "provedor_ia": provedor,
        },
        "entradas": {
            "ideia_usuario": ideia_orig,
            "preprompt_visual": preprompt,
        },
        "prompt_completo_raw": texto_prompt,
    }

    p_pos = re.search(r'1\.\s*PROMPT\s*(?:\(Inglês\))?:\s*(.*?)(?=\n2\.|\n###|$)', texto_prompt, re.DOTALL | re.IGNORECASE)
    p_neg = re.search(r'2\.\s*PROMPT NEGATIVO:\s*(.*?)(?=\n3\.|\n###|$)', texto_prompt, re.DOTALL | re.IGNORECASE)
    p_desc = re.search(r'3\.\s*DESCRIÇÃO REDES SOCIAIS\s*(?:\(Português\))?:\s*(.*?)(?=\n4\.|\n###|$)', texto_prompt, re.DOTALL | re.IGNORECASE)
    p_hash = re.search(r'4\.\s*HASHTAGS:\s*(.*?)(?=\n💡|\n###|$)', texto_prompt, re.DOTALL | re.IGNORECASE)
    p_dica = re.search(r'💡\s*DICA TÉCNICA:\s*(.*?)$', texto_prompt, re.DOTALL | re.IGNORECASE)

    dados["secoes"] = {
        "prompt_positivo": p_pos.group(1).strip() if p_pos else "",
        "prompt_negativo": p_neg.group(1).strip() if p_neg else "",
        "descricao_redes": p_desc.group(1).strip() if p_desc else "",
        "hashtags": p_hash.group(1).strip() if p_hash else "",
        "dica_tecnica": p_dica.group(1).strip() if p_dica else ""
    }

    return json.dumps(dados, indent=2, ensure_ascii=False)

# ==============================================================================
# 4. MOTOR DE CHAMADA A PROVEDORES DE IA (MULTI-PROVEDOR + RESILIÊNCIA)
# ==============================================================================
def _extrair_texto_resposta(obj):
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, list):
        partes = [_extrair_texto_resposta(item) for item in obj]
        return "\n".join(p for p in partes if p).strip()
    if isinstance(obj, dict):
        for chave in ("text", "content", "output_text", "response", "generated_text", "message", "choices", "result"):
            if chave in obj and obj[chave]:
                return _extrair_texto_resposta(obj[chave])
    return ""


def _chamar_provedor_ia(system_prompt, user_prompt, modelo_gemini="gemini-2.5-flash", temperature=0.25, use_web=False):
    email = st.session_state.get("user_email", "")
    config = carregar_config(email)
    provedor_preferido = st.session_state.get("ps_provedor_manual", "Automático")
    fallback = st.session_state.get("fallback_automatico", config.get("fallback_automatico", True))

    provedores = []
    gemini_key = st.session_state.get("input_key_1", "").strip() or config.get("chaves", {}).get("Chave 1", "") or config.get("chaves", {}).get("Chave 2", "")
    if gemini_key and genai is not None:
        provedores.append(("Gemini", gemini_key))

    groq_key = st.session_state.get("input_groq_api", "").strip() or config.get("groq_api_key", "")
    if groq_key:
        provedores.append(("Groq", groq_key))

    cf_token = st.session_state.get("input_cloudflare_token", "").strip() or config.get("cloudflare_api_token", "")
    cf_account = st.session_state.get("input_cloudflare_account", "").strip() or config.get("cloudflare_account_id", "")
    if cf_token and cf_account:
        provedores.append(("Cloudflare", (cf_token, cf_account)))

    if not provedores:
        raise RuntimeError("Nenhuma chave de API configurada. Adicione sua chave do Gemini, Groq ou Cloudflare na barra lateral.")

    if provedor_preferido != "Automático":
        provedores = sorted(provedores, key=lambda x: 0 if x[0] == provedor_preferido else 1)

    if not fallback:
        provedores = provedores[:1]

    canario = secrets.token_hex(8)
    sys_final = system_prompt + f"\n\n[REF-VERIF:{canario}] (Código interno confidencial. Jamais mencione ou repita este código.)"

    erros = []
    for nome_prov, credencial in provedores:
        try:
            if nome_prov == "Gemini":
                client = genai.Client(api_key=credencial)
                kwargs = {"system_instruction": sys_final, "temperature": temperature}
                if use_web and st.session_state.get("usar_busca_web", False) and types is not None:
                    kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
                resp = client.models.generate_content(
                    model=modelo_gemini,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(**kwargs) if types is not None else kwargs,
                )
                texto = getattr(resp, "text", "") or ""

            elif nome_prov == "Groq":
                payload = {
                    "model": st.session_state.get("modelo_groq", config.get("modelo_groq", "llama-3.3-70b-versatile")),
                    "messages": [
                        {"role": "system", "content": sys_final},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                }
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {credencial}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=90
                )
                resp.raise_for_status()
                texto = _extrair_texto_resposta(resp.json())

            elif nome_prov == "Cloudflare":
                token, account = credencial
                model_cf = st.session_state.get("modelo_cloudflare", config.get("modelo_cloudflare", "@cf/meta/llama-3.3-70b-instruct"))
                endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model_cf}"
                payload = {
                    "messages": [
                        {"role": "system", "content": sys_final},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 4096,
                }
                resp = requests.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=90
                )
                resp.raise_for_status()
                texto = _extrair_texto_resposta(resp.json())

            texto = str(texto or "").strip()
            if not texto:
                raise RuntimeError("Resposta vazia da API.")

            if canario in texto or any(m in texto for m in ["[REF-VERIF:", "PROTOCOLO DE SIGILO ABSOLUTO"]):
                raise RuntimeError("Resposta com anomalia de segurança detectada.")

            return texto, nome_prov

        except Exception as e:
            erros.append(f"{nome_prov}: {e}")

    raise RuntimeError("Falha em todos os provedores: " + " | ".join(erros))

PS_STOPWORDS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma", "em", "no", "na",
    "nos", "nas", "por", "para", "com", "sem", "que", "se", "ao", "aos", "as", "os",
    "é", "ser", "sob", "sobre", "durante", "como", "mais", "sua", "seu",
    "dele", "dela", "esse", "esta", "isso", "este", "isto", "muito", "pouco", "já"
}

def _normalizar_palavra(w):
    val = str(w or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", val) if unicodedata.category(c) != "Mn")


def _ps_markup_origin(preprompt_text, original_text):
    clean_text = str(preprompt_text or "")
    orig_words = re.findall(r"[\wÀ-ÿ'-]+", original_text or "")
    norm_orig = {
        _normalizar_palavra(w) for w in orig_words
        if len(_normalizar_palavra(w)) > 2 and _normalizar_palavra(w) not in PS_STOPWORDS
    }

    pieces = []
    for token in re.split(r"(\s+|[^\wÀ-ÿ'-]+)", clean_text):
        if not token:
            continue
        if re.match(r"^[\wÀ-ÿ'-]+$", token):
            if _normalizar_palavra(token) in norm_orig:
                pieces.append(f'<span class="ps-user-word">{html.escape(token)}</span>')
            else:
                pieces.append(f'<span class="ps-ai-word">{html.escape(token)}</span>')
        else:
            pieces.append(html.escape(token))

    return "".join(pieces)


SYS_GERADOR_PREPROMPT = r"""Você é o Diretor de Arte Óptica e Composição Visual do Prompt Studio.
Sua missão é gerar um PRÉ-PROMPT visual completo, cinematográfico e coeso em Português a partir da ideia do usuário.

REGRAS MANDATÓRIAS:
1. PRESERVAÇÃO INTEGRAL DA IDEIA (INVIOLABILIDADE):
   - Preserve rigorosamente os nomes de personagens, franquias, gênero, cores, objetos e ações fornecidos pelo usuário. Não troque, não omita e não resuma.
2. EXPANSÃO ÓPTICA E FÍSICA (ZERO FLUFF / ZERO POESIA):
   - Adicione somente o que uma câmera ótica profissional captaria: fonte e ângulo da iluminação, sombras, texturas de materiais, disposição espacial de planos (primeiro plano, meio termo e fundo), enquadramento de câmera e atmosfera tangível.
   - É ESTRITAMENTE PROIBIDO usar metáforas poéticas ou conceitos invisíveis (ex: NUNCA use 'sensação de nostalgia', 'vento sussurra segredos', 'aura de bravura', 'testamento ao heroísmo').
3. SAÍDA EXCLUSIVA:
   - Responda APENAS com a descrição visual coesa em Português (um texto fluido e denso).
   - Não use títulos, introduções, saudações ou explicações."""

# ==============================================================================
# 5. ENGENHARIA DE PROMPT: COMPOSITÔMETRO E SYSTEM INSTRUCTION MESTRE
# ==============================================================================
SYS_COMPOSITOMETRO = r"""Você é o Auditor Óptico e Analista de Composição do Prompt Studio.
Analise a ideia escrita pelo usuário para geração de imagens e avalie a presença e integridade dos 5 pilares visuais fundamentais:
1. Sujeito / Identidade: O sujeito principal está claro? (Status: Definido, Vago, ou Ausente)
2. Ação / Dinâmica: Há ação, pose ou estado claro? (Status: Presente, Estática, ou Ausente)
3. Cenário / Ambiente: O local e profundidade estão informados? (Status: Definido, Vago, ou Ausente)
4. Iluminação / Clima: A luz e atmosfera foram ditadas? (Status: Definida, ou Inferida pela IA)
5. Câmera / Enquadramento: A perspectiva/lente foi especificada? (Status: Definida, ou Inferida pela IA)

Além disso:
- Detecte o nível sugerido de sensualidade (número inteiro de 1 a 6) intrínseco na frase.
- Sugira EXATAMENTE 2 a 3 melhorias de composição cirúrgicas e breves (máximo 1 frase cada) priorizando lentes reais (24mm, 35mm, 50mm, 85mm) e esquemas de luz físicos (Chiaroscuro, rim light, flash direto, luz de tungstênio) que o usuário pode opcionalmente aceitar para elevar a qualidade da cena.

Retorne EXCLUSIVAMENTE um JSON válido no seguinte formato:
{
  "sujeito_status": "Definido | Vago | Ausente",
  "sujeito_resumo": "breve texto identificando o sujeito",
  "acao_status": "Presente | Estática | Ausente",
  "cenario_status": "Definido | Vago | Ausente",
  "iluminacao_status": "Definida | Inferida pela IA",
  "camera_status": "Definida | Inferida pela IA",
  "nivel_sensualidade_sugerido": 1,
  "diagnostico_texto": "1 a 2 frases curtas explicando o que a IA manterá e o que inferirá automaticamente",
  "sugestoes_cirurgicas": [
    "sugestão de iluminação ou lente opcional 1",
    "sugestão de perspectiva ou ângulo opcional 2"
  ]
}
Não use markdown extra nem blocos explicativos."""

SYS_MESTRE_SINTETIZADOR = r"""Você é o Engenheiro-Chefe de Prompts Ópticos e Diretor Técnico de Difusão do Prompt Studio.
Sua missão é transformar a intenção do usuário no prompt final de maior fidelidade e profissionalismo, erradicando qualquer traço de vício amador ou fórmulas genéricas de IA.

=============================================================================
1. PROTOCOLO ANTI-FLUFF E FÍSICA PURA (ZERO RETÓRICA)
=============================================================================
- PROIBIÇÃO DE RETÓRICA LITERÁRIA: Text encoders não processam abstrações poéticas ou sentimentos. NUNCA use termos como: 'a sense of foreboding', 'whispers of the past', 'testament to courage', 'aura of destiny', 'capturing the essence', 'eternal soul'.
- ELIMINAÇÃO DE BUZZWORDS OBSOLETAS: Não use '8k', 'photorealistic', 'hyperrealistic', 'trending on artstation', 'masterpiece' ou 'octane render', a menos que a gramática nativa do modelo exija expressamente (como score tags no Pony ou masterpiece no Illustrious).
- DESCRITORES ÓPTICO-MATERIAIS PUROS: Descreva grandezas físicas tangíveis: geometria, anatomia, espessura e caimento de tecidos, índice de refração, dureza/direção da luz, distância focal de lente real (mm), abertura (f-stop) e perfil de sensor/filme.

=============================================================================
2. PRESERVAÇÃO CANÔNICA E ÂNCORAS RÍGIDAS (HARD ANCHORING)
=============================================================================
- O NÚCLEO DO USUÁRIO É SAGRADO: Identidade de personagens conhecidos, franquia, gênero, etnia, idade e traços declarados devem ser preservados integralmente. Nunca mude um idoso para jovem, nunca transforme animais em humanos, nunca troque cores informadas.
- INFERÊNCIA ÓPTICA COERENTE E SILENCIOSA: Deduza com física realista apenas os elementos não especificados (se pediu rua chuvosa à noite: deduza asfalto molhado com reflexos especulares, halos de vapor de sódio, gotas na lente e profundidade de campo; jamais invente naves espaciais ou dragões).

=============================================================================
3. REGRA DE SENSUALIDADE E MODÉSTIA (ACATAR NÍVEL ESCOLHIDO)
=============================================================================
Ajuste os modificadores e tags de classificação estritamente conforme o NÍVEL INFORMADO:
- Nível 1 - Seguro (SFW): rating_safe, modéstia visual total, sem decotes profundos ou poses provocativas.
- Nível 2 - Menos Seguro: rating_safe, caimento atraente, pose estética, modéstia preservada.
- Nível 3 - Ecchi Leve: rating_questionable, roupas de banho, biquíni, maiô, lingerie padrão.
- Nível 4 - Ecchi: rating_questionable, micro trajes, tecidos translúcidos (see-through), decote acentuado.
- Nível 5 - Picante: rating_explicit, nudez artística anatômica ou trajes mínimos sem censura.
- Nível 6 - Dual: Estruture obrigatoriamente duas versões no corpo do prompt:
  * VERSÃO A: Com censura tática (efeito de vapor, reflexo de lente, tarja estilizada).
  * VERSÃO B: Sem censura / Explícita pura.

=============================================================================
4. ADAPTAÇÃO GRAMATICAL NATIVA POR MOTOR ALVO (CORRESPONDÊNCIA EXATA)
=============================================================================

- [ComfyUI / SDXL Base Natural -> Fooocus / ComfyUI (RealVis & Juggernaut)]:
  * PROIBIÇÃO ABSOLUTA: Tags soltas com underscore ou jargões Booru.
  * ESTRUTURAÇÃO POR ENGENHARIA ÓPTICA DINÂMICA (Parágrafo em prosa contínua em inglês):
    1. ARQUÉTIPO DE LENTE E ENQUADRAMENTO (Varie ativamente conforme a narrativa da cena):
       - Se Ambiental/Ação: "Ultra-wide 24mm f/5.6 dynamic shot, deep depth of field, sharp foreground-to-background focus..."
       - Se Urbano/Candid: "Street photography shot on 35mm f/2.8 lens, natural perspective, eye-level unposed capture..."
       - Se Retrato Dramático: "Intimate close-up on 50mm f/1.8 prime lens, natural compression, shallow depth of field..."
       - Se Editorial de Moda: "Fashion editorial captured on 105mm f/2.0 telephoto lens, strong subject isolation..."
    2. FÍSICA DA LUZ: Especifique esquema claro: Chiaroscuro de alto contraste, luz direta de flash, tungstênio + néon noturno, ou luz difusa de dia nublado.
    3. AUTENTICIDADE HUMANA: Assimetria facial, linhas de expressão, textura cutânea fosca com micro-poros visíveis (matte skin texture), penugem natural (peach fuzz), olhos com catchlights da fonte de luz e fios de cabelo rebeldes (flyaway hairs).
    4. CIÊNCIA DE COR: Declare mídia de captura (ex: "Shot on Kodak Portra 400 film, natural organic film grain" OU "Shot on Leica M11, razor-sharp edge micro-contrast").
  * PROMPT NEGATIVO CIRÚRGICO:
    - Se Pessoas: 3d render, cgi, digital painting, illustration, cartoon, anime, waxy skin, plastic doll skin, airbrushed, smooth porcelain face, fake skin, overly smooth textures, bad anatomy, bad proportions, deformed hands, fused fingers, extra fingers, missing digits, mutated limbs, cross-eyed, asymmetric pupils, bad teeth, blurry, low dynamic range, blown out highlights, amateur photograph, watermark, signature
    - Se Objetos/Paisagem: 3d render, cgi, illustration, video game graphics, low dynamic range, flat lighting, blown out highlights, overexposed, low contrast, chromatic aberration, blurry, watermark, logo
  * DICA TÉCNICA: Sampler: DPM++ 2M SDE Karras ou DPM++ 3M SDE Exponential | Steps: 30-40 | CFG: 4.5 a 6.0.

- [ComfyUI / Pony SDXL -> ComfyUI / Forge (Anime & NSFW Local)]:
  * CABEÇALHO OBRIGATÓRIO (Âncora de Qualidade & Estilo):
    - Se Anime / 2D / 2.5D: score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up, rating_[safe|questionable|explicit], source_anime,
    - Se Foto / Realista: score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up, rating_[safe|questionable|explicit], source_photo, raw photo, realistic, professional photograph,
  * QUEBRA DO 'LOOK PADRÃO PONY':
    - NUNCA use 'looking at viewer, standing, smiling' como padrão automático.
    - FORCE dinâmica de câmera nas tags: dynamic_angle, dutch_angle, from_below, from_above, cowboy_shot, profile, looking_away, backlighting, foreshortening.
    - Isole peças e cores em pares contíguos contra color bleeding: [cor]_[peça] (ex: black_leather_jacket, white_crop_top, blue_denim_jeans).
    - Marcadores ópticos Booru: volumetric_lighting, rim_light, ray_tracing, atmospheric_perspective, chromatic_aberration, depth_of_field.
  * PROMPT NEGATIVO DE SUPRESSÃO TOTAL DE DATASET (Cadeia Completa):
    - Inicie SEMPRE com: score_6, score_5, score_4, score_3, score_2, score_1,
    - Se Foto: source_pony, source_furry, source_anime, 3d, 3d render, cgi, digital art, illustration, cartoon, drawing, painting, vector art, cel shading, sketch, airbrushed, plastic skin, waxy skin, doll, mannequin, silicone, fake skin, smooth porcelain face, bad anatomy, bad proportions, bad eyes, poorly drawn eyes, cross-eyed, asymmetric eyes, poorly drawn face, deformed fingers, extra fingers, missing fingers, fused hands, bad hands, bad feet, mutated limbs, unnatural body fold, censor, bar censor, mosaic censoring, text, watermark, signature, blurry, jpeg artifacts, overexposed
    - Se Anime: source_pony, source_furry, source_photo, realistic, photograph, 3d, 3d render, western comic, bad anatomy, bad proportions, bad hands, deformed fingers, extra digits, missing limbs, fused fingers, poorly drawn face, poorly drawn eyes, cross-eyed, blurry, lowres, artifacts, text, watermark
  * DICA TÉCNICA: Sampler: Euler a ou DPM++ 2M Karras | Steps: 28-35 | CFG: 5.0 a 6.0 (CFG > 6.5 satura e destrói o contraste).

- [ComfyUI / Illustrious -> ComfyUI / WebUI (Anime & 2D Moderno)]:
  * CABEÇALHO OBRIGATÓRIO: masterpiece, best quality, amazing quality, very aesthetic, newest,
  * SINTAXE ATÔMICA MODERNA: Apenas tags separadas por vírgula com underscore. Composição avançada via tags: chiaroscuro, rim_light, cinematic_composition, dynamic_pose, dramatic_shadows, expressive_eyes, clean_lineart, detailed_background, subsurface_scattering.
  * PROMPT NEGATIVO EM 4 CAMADAS ATÔMICAS:
    1. Base: bad quality, worst quality, low quality, normal quality, lowres, jpeg artifacts,
    2. Meio Oposto: Se 2D: photorealistic, realistic, photograph, 3d, 3d render, realistic skin; Se 2.5D: flat color, simple background, bad lineart,
    3. Anatomia (se houver pessoas): poorly drawn face, poorly drawn eyes, asymmetric eyes, bad hands, deformed fingers, extra digits, missing fingers, fused fingers, mutated limbs, bad feet,
    4. Limpeza: watermark, signature, username, text, logo, bad anatomy.
  * DICA TÉCNICA: Sampler: Euler a ou Restart | Steps: 28-35 | CFG: 4.5 a 5.5 | Clip Skip: 2.

- [Flux.1 (Dev/Schnell) -> Nano Banana / Fal.ai]:
  * TEXT ENCODER: T5-XXL + CLIP ViT-L. Interpreta relações espaciais e descrições cinematográficas em prosa.
  * ESTRUTURA DO POSITIVO: Parágrafo descritivo denso em inglês natural. Ancore espacialmente em 3 planos: foreground, midground e background. Detalhe a física da luz e dos materiais.
  * TÉCNICA DE NEGAÇÃO POSITIVA COMPOSTA: O modelo NÃO possui canal negativo na rede. Elimine elementos indesejados inserindo uma frase de fechamento no corpo do prompt positivo (ex: "The scene is sharply focused with natural optical depth, entirely free of airbrushed skin, artificial CGI textures, crowds, clutter, watermarks, or text.").
  * PROMPT NEGATIVO: Não aplicável para Flux.1 (A arquitetura Transformer do Flux ignora canal negativo; as exclusões foram integradas na frase final do prompt positivo).
  * DICA TÉCNICA: Flux.1 Dev: Distilled CFG: 3.5 | Steps: 25-30 | Sampler: Euler. Flux.1 Schnell: CFG: 1.0 | Steps: 4-6 | Sampler: Euler.

- [Midjourney v6.1 -> Midjourney (Discord / Web)]:
  * ESTRUTURA: Frases objetivas e ricas em linguagem natural: [Sujeito e Ação imediata], [Lente de Cinema e Enquadramento], [Rig de Iluminação Exato], [Texturas e Materiais], [Perfil de Mídia].
  * PARÂMETROS OBRIGATÓRIOS AO FINAL: --ar 16:9 (ou 9:16 ou 4:5) --v 6.1 --stylize [100 a 250 para fotos realistas; 300 a 600 para estética artística].
  * PARÂMETRO NEGATIVO CIRÚRGICO (--no): Componha de 4 a 6 tokens semânticos cruciais derivados da cena ao final da linha de comando:
    - Se Foto: --no 3d render, illustration, cartoon, smooth skin, airbrushed, oversaturated
    - Se Ilustração: --no photograph, photo, realistic, 3d, border, frame
  * No campo '2. PROMPT NEGATIVO' da resposta, exiba a flag exata a ser utilizada.
  * DICA TÉCNICA: Mantenha --stylize entre 100 e 150 para fotos humanas naturais; evite valores excessivos.

- [Ideogram 2.0 -> Ideogram.ai (Design & Tipografia)]:
  * ESTRUTURA: Diagramação e tipografia precisa. Textos legíveis na arte DEVEM vir estritamente entre aspas duplas: "TEXTO EXATO". Especifique a família tipográfica (bold sans-serif, vintage serif, neon lettering).
  * CAMPO NEGATIVO NATIVO MODULAR: misspelled words, garbled letters, duplicated text, illegible font, distorted typography, bad graphic design, cluttered composition, asymmetrical alignment, overlapping text, watermark, signature, blurry, low resolution
  * DICA TÉCNICA: Selecione o estilo 'Design' para pôsteres/logos ou 'Realistic' para fotos com tipografia integrada.

- [DALL-E 3 / Bing Image Creator -> ChatGPT Plus / Copilot Designer]:
  * ESTRUTURA: Parágrafo cinematográfico fluido em prosa contínua densa para impedir que o GPT-4 altere o comando original.
  * BLINDAGEM DE MODERAÇÃO (Sensualidade Níveis 3 a 5): O filtro semântico bloqueia anatomia explícita. Descreva a sensualidade exclusivamente via física de tecidos e iluminação: "form-fitting translucent silk fabric, sculpted rim lighting accentuating body contours, elegant backless silhouette, wet-draped textiles, low-key lighting with deep cast shadows".
  * TÉCNICA DE EXCLUSÃO POSITIVA: Finalize o parágrafo com uma restrição explícita de cena ("The image is a clean professional shot, free of digital artifacts, distortion, extra limbs, or background clutter").
  * PROMPT NEGATIVO: Não aplicável (DALL-E 3 e Bing não possuem canal negativo; exclusões foram coordenadas no próprio prompt).
  * DICA TÉCNICA: Mantenha o texto com até 90 palavras para evitar truncamento no Bing Image Creator.

- [Leonardo.Ai / SeaArt -> Leonardo.Ai / SeaArt.ai]:
  * ESTRUTURA: Descrição cinematográfica enriquecida com modificadores ponderados: (subsurface scattering:1.15), (sculpted rim light:1.2), (tactile fabric weave:1.1), (natural skin pores:1.1).
  * PROMPT NEGATIVO PONDERADO DE ALTA DENSIDADE:
    (3d render:1.25), (cgi:1.2), (digital painting:1.15), (illustration:1.1), (airbrushed:1.2), (smooth plastic doll skin:1.3), (fake waxy skin:1.2), (overexposed:1.1), (blown out highlights:1.15), (flat lighting:1.1), (deformed hands:1.25), (missing fingers:1.2), (extra digits:1.2), (fused fingers:1.2), (distorted face:1.2), (cross-eyed:1.15), (bad proportions:1.15), watermark, signature, text, logo, amateur photograph, blurry, low dynamic range
  * DICA TÉCNICA: Ative o pipeline PhotoReal no Leonardo.Ai e selecione Preset Style 'Cinematic' ou 'None'.

=============================================================================
FORMATO DE SAÍDA EXATO:
=============================================================================
### 🖼️ PROMPT GERADO: [{MOTOR_DESTINO}]
1. PROMPT (Inglês): [Prompt estruturado na sintaxe exata do motor]
2. PROMPT NEGATIVO: [Prompt Negativo cirúrgico dinâmico ou flag técnica correspondente]
3. DESCRIÇÃO REDES SOCIAIS (Português): [Legenda curta e cativante de 2 a 3 frases conectando sujeito e cena + CTA (Chamada para Ação) persuasiva OBRIGATÓRIA no final]
4. HASHTAGS: [#tags_especificas]
💡 DICA TÉCNICA: [Dica prática de amostragem/steps/cfg ideal para o motor]"""

# ==============================================================================
# 6. FUNÇÕES DE PROCESSAMENTO
# ==============================================================================
def gerar_preprompt_visual(texto_ideia, modelo_gemini):
    """Gera a direção visual (pré-prompt) em português fundindo a ideia do usuário com expansão óptica."""
    if not texto_ideia.strip():
        return ""
    user_prompt = f"DESENVOLVA O PRÉ-PROMPT VISUAL PARA ESTA IDEIA:\n{texto_ideia}"
    texto_pre, prov = _chamar_provedor_ia(SYS_GERADOR_PREPROMPT, user_prompt, modelo_gemini, temperature=0.3)
    return texto_pre.strip()


def analisar_no_compositometro(texto_ideia, modelo_gemini):
    """Executa a leitura óptica e diagnóstico do Compositômetro com extração resiliente de JSON."""
    if not texto_ideia.strip():
        return None
    user_prompt = f"AVALIE ESTA IDEIA NO COMPOSITÔMETRO:\n{texto_ideia}"
    try:
        texto_json, prov = _chamar_provedor_ia(SYS_COMPOSITOMETRO, user_prompt, modelo_gemini, temperature=0.1)
        match = re.search(r'\{.*\}', texto_json, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(texto_json.strip())
    except Exception:
        return None


def sintetizar_prompt_final(texto_ideia, nivel_sensualidade, destino, sugestoes_aceitas, modelo_gemini):
    """Gera o prompt final especializado com base na ideia e nos moduladores."""
    sug_str = "\n".join(f"- {s}" for s in sugestoes_aceitas) if sugestoes_aceitas else "Nenhuma sugestão adicional marcada."

    user_prompt = f"""=== ENTRADA DE SÍNTESE DO COCKPIT ===
PLATAFORMA DESTINO: {destino}
NÍVEL DE SENSUALIDADE ESCOLHIDO PELO USUÁRIO: {nivel_sensualidade}

1. IDEIA LIVRE DO USUÁRIO / DIREÇÃO VISUAL:
{texto_ideia}

2. SUGESTÕES CIRÚRGICAS INCORPORADAS:
{sug_str}

Gere o prompt final aplicando rigidamente o protocolo anti-fluff, hard anchoring do sujeito e a engenharia sintática exigida pelo motor {destino}."""

    return _chamar_provedor_ia(SYS_MESTRE_SINTETIZADOR, user_prompt, modelo_gemini, temperature=0.25)

# ==============================================================================
# 7. INTERFACE PRINCIPAL (COCKPIT MINIMALISTA)
# ==============================================================================
def renderizar_cockpit():
    st.markdown("<div class='ps-kicker'>PROMPT STUDIO COCKPIT · ATRITO ZERO</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='ps-title'>Ideia Livre. Engenharia Invisível.</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='ps-subtitle'>"
        "Escreva sua ideia sem se preocupar com dezenas de caixas. "
        "O Compositômetro avalia os pilares visuais e nosso motor técnico compila nativamente para o seu gerador de imagem."
        "</p>",
        unsafe_allow_html=True
    )

    modelo_ia = st.session_state.get("modelo_gemini_selecionado", "gemini-2.5-flash")

    # --------------------------------------------------------------------------
    # 1. CAMPO DE TEXTO LIVRE PRINCIPAL
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("### 💡 O que você quer criar?")
        ideia_input = st.text_area(
            "Descreva sua cena em linguagem humana natural:",
            value=st.session_state.get("ck_ideia", ""),
            key="ck_ideia_input",
            height=140,
            placeholder="Exemplo: Android 18 sentada perto de uma janela molhada pela chuva em um café acolhedor em Tóquio, tomando chá em uma xícara cerâmica, luz suave da tarde com reflexos aconchegantes..."
        )

        # Invalidação preventiva se o usuário alterar a ideia mas não gerar novo pré-prompt
        if ideia_input.strip() != st.session_state.get("ck_ideia", ""):
            st.session_state["ck_ideia"] = ideia_input.strip()
            st.session_state.pop("ck_preprompt", None)
            st.session_state.pop("ck_preprompt_editado", None)
            st.session_state.pop("ck_diagnostico", None)
            st.session_state.pop("ck_sugestoes_marcadas", None)

        col_b1, col_b2, col_b3 = st.columns([4, 4, 2])
        with col_b1:
            btn_preprompt = st.button("👁️ Pré-prompt", type="primary", help="Gera a direção visual ajustada em português com distinção por cores", use_container_width=True, key="btn_preprompt")
        with col_b2:
            btn_avaliar = st.button("🔍 Avaliar no Compositômetro", help="Verifica a integridade dos pilares visuais da sua ideia", use_container_width=True, key="btn_avaliar")
        with col_b3:
            if st.button("🗑️ Limpar", use_container_width=True, key="btn_limpar_cockpit"):
                st.session_state["ck_ideia"] = ""
                st.session_state["ck_ideia_input"] = ""
                st.session_state.pop("ck_preprompt", None)
                st.session_state.pop("ck_preprompt_editado", None)
                st.session_state.pop("ck_diagnostico", None)
                st.session_state.pop("ck_prompt_final", None)
                st.session_state.pop("ck_sugestoes_marcadas", None)
                st.session_state.pop("ck_sens_slider", None)
                for k in list(st.session_state.keys()):
                    if k.startswith("sug_chk_"):
                        st.session_state.pop(k, None)
                st.rerun()

    # --------------------------------------------------------------------------
    # TRATAMENTO DOS BOTÕES: PRÉ-PROMPT E COMPOSITÔMETRO
    # --------------------------------------------------------------------------
    if btn_preprompt:
        if not ideia_input.strip():
            st.warning("Escreva sua ideia antes de gerar o Pré-prompt.")
        else:
            with st.spinner("Construindo direção visual do Pré-prompt..."):
                pre_texto = gerar_preprompt_visual(ideia_input.strip(), modelo_ia)
                diag = analisar_no_compositometro(ideia_input.strip(), modelo_ia)
                if pre_texto:
                    st.session_state["ck_ideia"] = ideia_input.strip()
                    st.session_state["ck_preprompt"] = pre_texto
                    st.session_state["ck_diagnostico"] = diag
                    for k in list(st.session_state.keys()):
                        if k.startswith("sug_chk_"):
                            st.session_state.pop(k, None)
                    if diag:
                        try:
                            sug_lvl = int(str(diag.get("nivel_sensualidade_sugerido", 1)).strip()[0])
                            if 1 <= sug_lvl <= len(OPCOES_SENSUALIDADE):
                                st.session_state["ck_sens_slider"] = OPCOES_SENSUALIDADE[sug_lvl - 1]
                        except Exception:
                            pass
                    st.rerun()
                else:
                    st.error("Não foi possível gerar o Pré-prompt no momento.")

    if btn_avaliar:
        if not ideia_input.strip():
            st.warning("Escreva sua ideia antes de rodar o Compositômetro.")
        else:
            with st.spinner("Raio-X da composição em andamento..."):
                diag = analisar_no_compositometro(ideia_input.strip(), modelo_ia)
                if diag:
                    st.session_state["ck_ideia"] = ideia_input.strip()
                    st.session_state["ck_diagnostico"] = diag
                    for k in list(st.session_state.keys()):
                        if k.startswith("sug_chk_"):
                            st.session_state.pop(k, None)
                    try:
                        sug_lvl = int(str(diag.get("nivel_sensualidade_sugerido", 1)).strip()[0])
                        if 1 <= sug_lvl <= len(OPCOES_SENSUALIDADE):
                            st.session_state["ck_sens_slider"] = OPCOES_SENSUALIDADE[sug_lvl - 1]
                    except Exception:
                        pass
                    st.rerun()
                else:
                    st.error("Não foi possível processar a avaliação no momento.")

    # --------------------------------------------------------------------------
    # 2. PRÉ-PROMPT VISUAL COM DESTAQUE DE CORES E LEGENDA
    # --------------------------------------------------------------------------
    if st.session_state.get("ck_preprompt"):
        with st.container(border=True):
            st.markdown("### 🎨 Pré-prompt (Direção Visual Ajustada)")
            st.caption("Visualização da composição desenvolvida em português antes da tradução técnica para o motor de imagem.")
            
            st.markdown(
                "<div class='ps-legend'>"
                "<span><span class='ps-user-word'>Sua Ideia</span> (Inserção do Usuário)</span>"
                " &nbsp;&nbsp;•&nbsp;&nbsp; "
                "<span><span class='ps-ai-word'>Desenvolvimento Óptico da IA</span> (Direção Visual)</span>"
                "</div>",
                unsafe_allow_html=True
            )

            markup = _ps_markup_origin(
                st.session_state["ck_preprompt"],
                st.session_state.get("ck_ideia", "")
            )
            st.markdown(f"<div class='ps-preprompt'>{markup}</div>", unsafe_allow_html=True)

            preprompt_editado = st.text_area(
                "Ajustar o Pré-prompt se desejar (o texto abaixo será a base da compilação técnica):",
                value=st.session_state["ck_preprompt"],
                height=130,
                key="ck_preprompt_editado"
            )
            if preprompt_editado != st.session_state["ck_preprompt"]:
                st.session_state["ck_preprompt"] = preprompt_editado

    # --------------------------------------------------------------------------
    # 3. O COMPOSITÔMETRO (FEEDBACK VISUAL PASSIVO + SUGESTÕES DE APOIO)
    # --------------------------------------------------------------------------
    diag_atual = st.session_state.get("ck_diagnostico")
    if diag_atual:
        with st.container(border=True):
            st.markdown("#### 📊 Raio-X do Compositômetro")
            
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
            
            def badge_cor(status):
                if status in ["Definido", "Presente"]:
                    return "comp-green", "✓"
                elif status in ["Vago", "Estática"]:
                    return "comp-amber", "!"
                else:
                    return "comp-blue", "⚙️"

            c1, i1 = badge_cor(diag_atual.get("sujeito_status", ""))
            c2, i2 = badge_cor(diag_atual.get("acao_status", ""))
            c3, i3 = badge_cor(diag_atual.get("cenario_status", ""))
            c4, i4 = badge_cor(diag_atual.get("iluminacao_status", ""))
            c5, i5 = badge_cor(diag_atual.get("camera_status", ""))

            with col_stat1:
                st.markdown(f"<div class='comp-badge {c1}'>{i1} Sujeito: {diag_atual.get('sujeito_status')}</div>", unsafe_allow_html=True)
            with col_stat2:
                st.markdown(f"<div class='comp-badge {c2}'>{i2} Ação: {diag_atual.get('acao_status')}</div>", unsafe_allow_html=True)
            with col_stat3:
                st.markdown(f"<div class='comp-badge {c3}'>{i3} Cenário: {diag_atual.get('cenario_status')}</div>", unsafe_allow_html=True)
            with col_stat4:
                st.markdown(f"<div class='comp-badge {c4}'>{i4} Luz: {diag_atual.get('iluminacao_status')}</div>", unsafe_allow_html=True)
            with col_stat5:
                st.markdown(f"<div class='comp-badge {c5}'>{i5} Câmera: {diag_atual.get('camera_status')}</div>", unsafe_allow_html=True)

            if diag_atual.get("diagnostico_texto"):
                st.caption(f"ℹ️ **Diagnóstico:** {diag_atual.get('diagnostico_texto')}")

            sugestoes = diag_atual.get("sugestoes_cirurgicas", [])
            if sugestoes:
                st.markdown("##### ✨ Sugestões Cirúrgicas Opcionais (Marque para incorporar):")
                selecionadas = []
                for idx, sug in enumerate(sugestoes):
                    if st.checkbox(sug, key=f"sug_chk_{idx}"):
                        selecionadas.append(sug)
                st.session_state["ck_sugestoes_marcadas"] = selecionadas

    # --------------------------------------------------------------------------
    # 4. MODULADOR DE SENSUALIDADE / RISCO NSFW
    # --------------------------------------------------------------------------
    st.write("")
    with st.container(border=True):
        st.markdown("#### 🎚️ Nível de Sensualidade & Modéstia")
        st.caption("A IA pré-ajusta o nível com base na cena. Você tem total controle para modular a barra; nossa função é informar os riscos de compatibilidade.")

        if "ck_sens_slider" not in st.session_state:
            try:
                sug_diag = int(str((st.session_state.get("ck_diagnostico") or {}).get("nivel_sensualidade_sugerido", 2)).strip()[0])
            except Exception:
                sug_diag = 2
            idx_inicial = max(0, min(sug_diag - 1, len(OPCOES_SENSUALIDADE) - 1))
            st.session_state["ck_sens_slider"] = OPCOES_SENSUALIDADE[idx_inicial]

        sens_escolhida = st.select_slider(
            "Selecione o nível desejado:",
            options=OPCOES_SENSUALIDADE,
            key="ck_sens_slider"
        )

        num_nivel = int(sens_escolhida[0]) if sens_escolhida and sens_escolhida[0].isdigit() else 1

        if num_nivel in [1, 2]:
            st.markdown(
                "<div class='risk-banner risk-green'>"
                "🟢 <b>Zona Segura (SFW):</b> Totalmente compatível com todas as plataformas (Midjourney, DALL-E, Flux e ComfyUI). Risco zero de bloqueio."
                "</div>",
                unsafe_allow_html=True
            )
        elif num_nivel in [3, 4]:
            st.markdown(
                "<div class='risk-banner risk-amber'>"
                "🟡 <b>Zona Moderada (Ecchi / Sensual):</b> Pode sofrer avisos ou rejeição em APIs com filtros rígidos (DALL-E / Bing / Midjourney). Otimizado para modelos locais (Pony SDXL, Flux local, SDXL Base)."
                "</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div class='risk-banner risk-rose'>"
                "🔴 <b>Zona Explícita (Picante / Sem Censura):</b> Alto risco de bloqueio em ferramentas comerciais da Web. Projetado para checkpoints locais sem censura (Pony SDXL / Illustrious no ComfyUI)."
                "</div>",
                unsafe_allow_html=True
            )

    # --------------------------------------------------------------------------
    # 5. SELETOR DE MOTOR DESTINO E EXECUÇÃO
    # --------------------------------------------------------------------------
    col_dest1, col_dest2 = st.columns([7, 3])
    with col_dest1:
        destino_selecionado = st.selectbox(
            "Plataforma / Motor de Imagem Alvo:",
            OPCOES_DESTINO,
            index=0,
            key="ck_destino_select"
        )
    with col_dest2:
        st.write("")
        st.write("")
        btn_executar = st.button("⚡ Gerar Prompt Agora", type="primary", use_container_width=True, key="btn_executar_final")

    if btn_executar:
        if not ideia_input.strip():
            st.warning("Por favor, descreva sua ideia no campo de texto.")
        else:
            real_dest = destino_selecionado
            texto_base = st.session_state.get("ck_preprompt_editado") or st.session_state.get("ck_preprompt") or ideia_input.strip()
            
            if real_dest == "Recomendado automaticamente":
                ideia_lower = texto_base.lower()
                if any(term in ideia_lower for term in ["anime", "manga", "desenho", "2d", "ilustração", "waifu"]):
                    real_dest = (
                        "ComfyUI / Pony SDXL -> ComfyUI / Forge (Anime & NSFW Local)"
                        if num_nivel >= 3
                        else "ComfyUI / Illustrious -> ComfyUI / WebUI (Anime & 2D Moderno)"
                    )
                elif num_nivel >= 4:
                    real_dest = "ComfyUI / Pony SDXL -> ComfyUI / Forge (Anime & NSFW Local)"
                elif any(term in ideia_lower for term in ["foto", "retrato", "realista", "cinematográfico", "fotografia"]):
                    real_dest = "Flux.1 (Dev/Schnell) -> Nano Banana / Fal.ai"
                else:
                    real_dest = "Midjourney v6.1 -> Midjourney (Discord / Web)"

            sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])

            with st.spinner(f"Compilando prompt otimizado para {real_dest}..."):
                try:
                    resultado, prov = sintetizar_prompt_final(
                        texto_base,
                        sens_escolhida,
                        real_dest,
                        sug_aceitas,
                        modelo_ia
                    )
                    st.session_state["ck_ideia"] = ideia_input.strip()
                    st.session_state["ck_prompt_final"] = resultado
                    st.session_state["ck_prov_usado"] = prov
                    st.session_state["ck_dest_usado"] = real_dest
                    st.session_state["ck_sens_usada"] = sens_escolhida
                    st.rerun()
                except Exception as ex:
                    st.error(f"Erro ao processar: {ex}")

    # --------------------------------------------------------------------------
    # 6. EXIBIÇÃO DO RESULTADO COMPILADO E DOWNLOADS (.TXT / .JSON)
    # --------------------------------------------------------------------------
    if st.session_state.get("ck_prompt_final"):
        st.write("")
        st.markdown("---")
        st.markdown(f"### 📋 Prompt Final Especializado ({st.session_state.get('ck_dest_usado', 'Padrão')})")
        st.caption(f"Compilado com motor de alta precisão via {st.session_state.get('ck_prov_usado', 'Prompt Studio')}.")

        st.code(st.session_state["ck_prompt_final"], language="markdown")

        nome_base = _gerar_nome_arquivo_base(
            st.session_state.get("ck_dest_usado", "motor"),
            st.session_state.get("ck_sens_usada", "sfw")
        )

        dados_json = _estruturar_prompt_json(
            texto_prompt=st.session_state["ck_prompt_final"],
            destino=st.session_state.get("ck_dest_usado", "Padrão"),
            nivel_sens=st.session_state.get("ck_sens_usada", "SFW"),
            ideia_orig=st.session_state.get("ck_ideia", ""),
            preprompt=st.session_state.get("ck_preprompt", ""),
            provedor=st.session_state.get("ck_prov_usado", "Gemini")
        )

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 Baixar Prompt (.TXT)",
                data=st.session_state["ck_prompt_final"],
                file_name=f"{nome_base}.txt",
                mime="text/plain",
                use_container_width=True,
                key="ck_dn_btn_txt"
            )
        with col_d2:
            st.download_button(
                "📦 Baixar Estrutura (.JSON)",
                data=dados_json,
                file_name=f"{nome_base}.json",
                mime="application/json",
                use_container_width=True,
                key="ck_dn_btn_json"
            )

# ==============================================================================
# 8. BARRA LATERAL (CONFIGURAÇÕES E CREDENCIAIS)
# ==============================================================================
def renderizar_sidebar():
    st.sidebar.markdown("## ⚙️ Configurações do Cockpit")
    st.sidebar.caption(f"Usuário: **{st.session_state.get('user_email', '')}**")
    if st.session_state.get("expiracao"):
        st.sidebar.caption(f"Validade do Acesso: **{st.session_state.expiracao}**")

    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    config = carregar_config(st.session_state.get("user_email", ""))

    with st.sidebar.expander("🔑 Chaves de API e Provedores", expanded=False):
        st.selectbox("Seleção de Provedor", ["Automático", "Avançado"], key="ps_selection_mode")
        if st.session_state.ps_selection_mode == "Avançado":
            st.selectbox("Provedor Prioritário", ["Automático", "Gemini", "Groq", "Cloudflare"], key="ps_provedor_manual")
        else:
            st.session_state.ps_provedor_manual = "Automático"

        st.selectbox("Modelo Gemini", ["gemini-2.5-flash", "gemini-2.0-flash"], index=0, key="modelo_gemini_selecionado")
        k1 = st.text_input("Chave Google Gemini", value=config.get("chaves", {}).get("Chave 1", ""), type="password", key="input_key_1")
        k_groq = st.text_input("Chave Groq API", value=config.get("groq_api_key", ""), type="password", key="input_groq_api")
        cf_acc = st.text_input("Cloudflare Account ID", value=config.get("cloudflare_account_id", ""), key="input_cloudflare_account")
        cf_tok = st.text_input("Cloudflare Token", value=config.get("cloudflare_api_token", ""), type="password", key="input_cloudflare_token")
        fallback_chk = st.checkbox("Fallback Automático", value=config.get("fallback_automatico", True), key="fallback_automatico")
        web_search_chk = st.checkbox("Busca Web Ativa", value=config.get("usar_busca_web", False), key="usar_busca_web")

        if st.button("💾 Salvar Configurações", type="primary", use_container_width=True):
            salvar_config(
                chaves_dict={"Chave 1": k1, "Chave 2": config.get("chaves", {}).get("Chave 2", "")},
                modelo_padrao=st.session_state.get("modelo_gemini_selecionado", "gemini-2.5-flash"),
                usar_busca_web=web_search_chk,
                email=st.session_state.get("user_email", ""),
                groq_api_key=k_groq,
                cloudflare_account_id=cf_acc,
                cloudflare_api_token=cf_tok,
                provedor_ia=st.session_state.get("ps_provedor_manual", "Gemini"),
                fallback_automatico=fallback_chk,
                modelo_groq="llama-3.3-70b-versatile",
                modelo_cloudflare="@cf/meta/llama-3.3-70b-instruct"
            )
            st.sidebar.success("✅ Configurações salvas com sucesso!")

# ==============================================================================
# 9. PONTO DE ENTRADA DO APLICATIVO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "expiracao" not in st.session_state:
    st.session_state.expiracao = ""

if not st.session_state.autenticado:
    st.markdown(
        "<div class='ps-login'>"
        "<div class='ps-kicker'>PROMPT STUDIO COCKPIT</div>"
        "<h1 class='ps-title'>Atrito Zero. Máxima Fidelidade.</h1>"
        "<p class='ps-subtitle'>A evolução da geração de prompts: livre de caixas burocráticas, com diagnóstico óptico em tempo real e sem censura moralista.</p>"
        "</div>",
        unsafe_allow_html=True
    )
    st.divider()

    col_l1, col_l2, col_l3 = st.columns([2, 6, 2])
    with col_l2:
        email_login = st.text_input("E-mail Cadastrado", key="login_email_cockpit", placeholder="seu-email@exemplo.com")
        if st.button("Entrar no Cockpit", type="primary", use_container_width=True, key="btn_login_cockpit"):
            if not email_login.strip():
                st.warning("Por favor, digite seu e-mail cadastrado.")
            else:
                ok, exp, erro = verificar_acesso_sheets(email_login)
                if ok:
                    st.session_state.autenticado = True
                    st.session_state.user_email = email_login.strip().lower()
                    st.session_state.expiracao = exp
                    st.rerun()
                elif erro:
                    st.error(erro)
                else:
                    st.error("E-mail não encontrado ou assinatura expirada.")

        st.write("")
        st.markdown("#### Planos e Assinaturas:")
        st.link_button("Plano 15 Dias — R$ 14,99", LINK_KIWIFY_15_DIAS, use_container_width=True)
        st.link_button("Plano 30 Dias — R$ 29,99", LINK_KIWIFY_30_DIAS, use_container_width=True)
        st.link_button("Plano 90 Dias — R$ 59,99", LINK_KIWIFY_90_DIAS, use_container_width=True)

else:
    renderizar_sidebar()
    st.markdown("<div class='ps-brand'>PROMPT STUDIO COCKPIT</div>", unsafe_allow_html=True)
    st.markdown("<div class='ps-header-note'>Direção Visual Inteligente · Diagnóstico Óptico em Tempo Real</div>", unsafe_allow_html=True)
    renderizar_cockpit()
