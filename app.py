"""Gerador de prompt 1.0 — Etapa 3: cockpit Acolher→Melhorar→Modificar→Auditar→Baixar (texto) + Visão pronta
PRD/TRD/Fluxo/Briefing/Schema/Plano travados em GERADOR_PROMPT_1.0__AntesDeCodar/*__ENTREVISTA.md
"""
import pathlib
import sys
import html
import re  # usado pelo orçamento de tokens e pelos cortes por frase
ROOT = pathlib.Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Prompt Studio Cockpit | Engenharia Preditiva de Prompts IA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Design tokens (Briefing) ---
css_path = pathlib.Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# --- Imports ---
from src.auth import verificar_acesso_sheets
from src.config_store import carregar_config, salvar_config
from src.crypto import fernet_disponivel, mascarar_email, OPCOES_GEMINI_3, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO
from src.text_engines import (
    BANCO_DE_MOTORES, OPCOES_DESTINO, OPCOES_SENSUALIDADE,
    SYS_GERADOR_PREPROMPT, SYS_COMPOSITOMETRO, SYS_MESTRE_CORE,
    _chamar_motor_texto, _msg_erro_amigavel, _msg_erro_diagnostico,
    _build_gemini_config, _ps_markup_origin, parse_json_ia,
)

# Model optimization profiles (added for per-model prompt optimization)
# Each profile defines: max_tokens, structure, technical hint, required tags, prohibitions
MODEL_PROFILES = {
    "flux": {
        "max_tokens": 800,
        "structure": "subject-context-lighting-style",
        "dica_tecnica": "Use weighting: subject:1.2, background:1.0, lighting:1.1",
        "tags_obrigatorias": ["subject", "environment"],
        "proibicoes": ["repetitive adjectives"]
    },
    "ideogram": {
        "max_tokens": 500,
        "structure": "concept-elements-colors-style-composition",
        "dica_tecnica": "Max 2 main characters, limit colors to 3",
        "tags_obrigatorias": ["concept"],
        "proibicoes": ["more than 3 adjectives consecutively"]
    },
    "pony": {
        "max_tokens": 900,
        "structure": "positive-negative-quality",
        "dica_tecnica": "Use 'bad hands, bad feet' na negative always",
        "tags_obrigatorias": ["positive", "negative"],
        "proibicoes": ["contradictory tags"]
    },
    "illustrious": {
        "max_tokens": 700,
        "structure": "style-subject-quality-negative",
        "dica_tecnica": "Always include artist name or art movement first",
        "tags_obrigatorias": ["style", "subject"],
        "proibicoes": ["generic tags like 'masterpiece' without context"]
    },
    "krea2": {
        "max_tokens": 600,
        "structure": "instructions-subject-style-params-output",
        "dica_tecnica": "Use 'precise' para retratos, 'creative' para arte abstrata",
        "tags_obrigatorias": ["instructions", "subject"],
        "proibicoes": ["creativity and precision in both positive and negative"]
    },
    "midjourney": {
        "max_tokens": 500,
        "structure": "subject-parameters-ar-quality",
        "dica_tecnica": "Menos é mais - MJ v6 entende linguagem natural melhor",
        "tags_obrigatorias": ["subject"],
        "proibicoes": ["long complex words; MJ prefere simples"]
    },
    "qwen": {
        "max_tokens": 1000,
        "structure": "task-context-style-output-spec",
        "dica_tecnica": "Modelo understands both Chinese and English prompts natively",
        "tags_obrigatorias": ["task", "context"],
        "proibicoes": ["prompts extremamente curtos (<100 tokens)"]
    },
    "ernie": {
        "max_tokens": 800,
        "structure": "concept-elements-style-restrictions",
        "dica_tecnica": "Incluir pelo menos 1 termo chinês para assuntos orientais",
        "tags_obrigatorias": ["concept", "elements"],
        "proibicoes": ["prompts only in English for Chinese subjects"]
    },
    "zit": {
        "max_tokens": 400,
        "structure": "subject-minimal-context-speed-params",
        "dica_tecnica": "Turbo mode: max 3 adjectivos, sem descrições longitudes",
        "tags_obrigatorias": ["subject"],
        "proibicoes": ["any unnecessary words - each token counts for speed"]
    },
    "comfyui_sdxl": {
        "max_tokens": 800,
        "structure": "positive-negative-quality",
        "dica_tecnica": "Positive < 500 tokens, Negative < 300 tokens for best cache",
        "tags_obrigatorias": ["positive", "negative"],
        "proibicoes": ["contradictory tags, very long negative prompts"]
    }
}
from src.vision import _chamar_motor_visao

# ─────────────────────────────────────────────────────────────────────────────
# PERFIL DO DESTINO — resolução por ALIAS (o bug mais caro deste arquivo)
# ─────────────────────────────────────────────────────────────────────────────
# O código fazia MODEL_PROFILES.get(dest_sel.lower()). As chaves de
# MODEL_PROFILES são curtas ("flux", "zit", "krea2") e os rótulos de
# OPCOES_DESTINO são longos ("Flux.1 / Flux.2 (Klein)"), então o get() NUNCA
# casava: 0 de 10 destinos acertavam e todos caíam no fallback de 800 tokens.
# Consequência real: Midjourney (500), Z-Image (400) e Qwen (1000) recebiam
# 800 — o teto do modelo errado, e a extração da visão não podia ser
# calibrada para o destino certo.
ALIASES_DESTINO = [
    ("comfyui_sdxl", ["comfyui / sdxl base natural", "sdxl base natural", "sdxl natural"]),
    ("illustrious",   ["comfyui / illustrious", "illustrious"]),
    ("pony",         ["comfyui / pony sdxl", "pony sdxl", "pony"]),
    ("flux",         ["flux.1", "flux.2", "flux"]),
    ("ideogram",     ["ideogram"]),
    ("krea2",        ["krea 2", "krea2", "krea"]),
    ("midjourney",   ["midjourney"]),
    ("qwen",         ["qwen / tongyi", "tongyi", "qwen"]),
    ("ernie",        ["ernie"]),
    ("zit",          ["z-image turbo", "z-image", "zit", "zi t"]),
]


def _perfil_do_destino(dest_sel):
    """Perfil de otimização do destino. {} se nenhum alias casar."""
    dl = (dest_sel or "").lower()
    for chave, apelidos in ALIASES_DESTINO:
        if any(a in dl for a in apelidos):
            return MODEL_PROFILES.get(chave, {})
    return {}


def _teto_destino(dest_sel):
    """Teto de tokens da SAÍDA final (prompt + negative + legenda + hashtags)."""
    return _perfil_do_destino(dest_sel).get("max_tokens", 800)


# ─────────────────────────────────────────────────────────────────────────────
# ORÇAMENTO DE TOKENS — medição real, não contagem de caracteres
# ─────────────────────────────────────────────────────────────────────────────
# O código antigo fazia txt_b[:max_tokens] e chamava aquilo de "tokens".
# Português rende ~3 caracteres por token, então 400 caracteres são ~133
# tokens: o texto era cortado em ~67% antes da hora, sempre no meio de uma
# frase. Medir de verdade é o que faz o teto respeitar a qualidade.
_CPT_PT = 3.0   # caracteres por token, PT (conservador)
_CPT_EN = 3.85  # caracteres por token, EN (conservador)
_RE_CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")


def _cpt(txt):
    """Fator caracteres/token com detecção de idioma. Conservador para nunca
    subestimar tokens (o que faria o teto ser furado)."""
    if not txt:
        return _CPT_EN
    n = max(len(txt), 1)
    cjk = len(_RE_CJK.findall(txt)) / n
    base = _CPT_PT if cjk < 0.2 else _CPT_EN
    return max(1.5, round(base * (1 - cjk) + 1.5 * cjk, 2))


def _estimar_tokens(txt):
    if not txt:
        return 0
    return max(1, round(len(txt) / _cpt(txt)))


# Ordem de prioridade quando o teto aperta. Espelha a regra do mestre
# (FIDELIDADE DO SUJEITO): cede cenário e acabamento, nunca o sujeito nem a
# direção/dureza da luz nem os dados ópticos (mm, f/, DoF, bokeh).
_RE_TERMOS_FORTES = re.compile(
    r"\b\d{1,3}\s?mm\b|\bf/\d[\d.]*|\bbokeh\b|\bDoF\b|depth of field|"
    r"\banam[oó]rfic\w*|\bter[cç]os\b|\bcontraluz\b|\bcontra-luz\b|\bcontraste\b|"
    r"\brim light\b|\bspecular\b|\bvolum[eé]tric\w*|highlight\w*",
    re.IGNORECASE | re.UNICODE,
)
_RE_SUJEITO = re.compile(
    r"\b(mulher|homem|menina|menino|jovem|garota|garoto|adolescente|modelo|"
    r"cabelo|olhos|pele|rosto|l[aá]bio|ombro|bra[cç]o|dedo|m[aã]o|perna|"
    r"veste|vestido|blusa|roupa|cal[cç]a|meia|luva|colar|brinco|rel[oó]gio|"
    r"woman|man|girl|boy|young|lady|hair|eyes|skin|face|shoulder|arm|hand|leg|"
    r"thigh|wearing|wears|dressed)\b",
    re.IGNORECASE | re.UNICODE,
)


def _densidade(fr):
    """Nota de valor de uma frase. Maior = mais essencial.
    Câmera/luz e sujeito pesam mais que enumeração de objetos: `85mm`, `f/1.8`,
    `bokeh` e a identidade definem o resultado no motor, enquanto uma lista de
    móveis é cenário genérico que qualquer imagem com o prompt certo reconstrói."""
    n_subj = len(_RE_SUJEITO.findall(fr))
    n_cam = len(_RE_TERMOS_FORTES.findall(fr))
    return (n_subj * 8 + n_cam * 6, -len(fr))


def _cortar_por_frase(txt, max_tokens):
    """Corte SEMIÓTICO por fronteira de frase — nunca no meio de uma oração.

    Escolhe por DENSIDADE DE INFORMAÇÃO, não por ordem de aparição. O bug que
    isto corrige: preencher o orçamento em ordem (greedy) deixava sem espaço
    para a última frase — que é onde a visão costuma colocar lente, abertura e
    bokeh, exatamente o dado mais valioso. Na extração real os termos `85mm`,
    `depth of field` e `bokeh` eram o que sumia.

    A ordem original das frases é preservada na saída: muda a SELEÇÃO, não a
    leitura.
    """
    limite = int(max_tokens * _cpt(txt))
    if len(txt) <= limite:
        return txt, False
    partes = re.split(r"(?<=[.;:])\s+", txt)
    if len(partes) < 2:
        return txt[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.!?") + "…", True
    ordem = sorted(range(len(partes)), key=lambda i: _densidade(partes[i]), reverse=True)
    orcamento, escolhidos = limite, []
    for i in ordem:
        n = len(partes[i]) + (1 if escolhidos else 0)
        if n <= orcamento:
            orcamento -= n
            escolhidos.append(i)
    if not escolhidos:
        return txt[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.!?") + "…", True
    escolhidos.sort()
    saida = " ".join(partes[i] for i in escolhidos)
    return saida + (" …" if len(escolhidos) < len(partes) else ""), len(escolhidos) < len(partes)


def _orcamento_fonte(txt, max_tokens, teto_fonte_pct=0.65):
    """Aplica orçamento à narrativa fonte. Devolve (texto, tokens, avisou).

    O teto do destino é da SAÍDA final. A fonte entra como insumo, então fica
    em 65% dele; o resto é o que o modelo precisa para escrever dentro do teto.

    PROBLEMA QUE ESTA ETAPA CORRIGE (medido com foto real + Gemini de verdade):
    a visão devolve campos rotulados (sujeito/acao/cenario/iluminacao/
    estilo_camera) somando ~1276 tokens. Com teto-fonte de 260 (Z-Image, 400),
    a seleção por densidade global escolhia quase só frases do sujeito — o campo
    mais denso — e cortava cenario, iluminacao e estilo_camera INTEIROS. Perder
    cenário e iluminação é perder a imagem: o motor de destino não consegue
    reconstruir o que não foi descrito.

    A estratégia é COBERTURA antes de densidade: uma cota por campo, e só dentro da
    cota vale a ordem de densidade. Assim, quando aperta, o corte cai no
    detalhe decorativo de dentro de cada campo — nunca no campo inteiro.
    """
    if not txt:
        return txt, 0, False
    teto_fonte = int(max_tokens * teto_fonte_pct)
    est = _estimar_tokens(txt)
    if est <= teto_fonte:
        return txt, est, False

    # 1) O texto tem ESTRUTURA de campos rotulados? (é o caso da visão real)
    campos = _campos_rotulados(txt)
    if campos:
        saida = _cortar_por_campo(campos, teto_fonte)
        return saida, _estimar_tokens(saida), True

    # 2) Prosas sem rótulo: cai no corte por densidade (comportamento anterior)
    saida, cortou = _cortar_por_frase(txt, teto_fonte)
    return saida, _estimar_tokens(saida), cortou


# Prioridade quando o orçamento aperta. O SUJEITO nunca cede: é a identidade.
# Iluminação e câmera ficam acima de cenário, porque definem o "clima" que o
# modelo não infere; cenário cede antes — é o mais reconstruível pelo prompt.
_PESO_CAMPO = {"sujeito": 34, "acao": 24, "iluminacao": 16,
               "estilo_camera": 14, "cenario": 12}
# Piso por campo: mesmo com teto apertado, todo campo mantém uma amostra.
# Sem piso, o campo inteiro some e a imagem perde informação irrecuperável.
_PISO_CAMPO = 0.18
# Rotulos da extracao estruturada da visao. A fronteira (?<![0-9A-Za-zÀ-ÿ_])
# e' OBRIGATORIA: sem ela o grupo 'acao' casa DENTRO de 'iluminacao'
# (ilumina-CA-O) e o campo iluminacao se perde inteiro — o que So apareceu no
# teste com foto real.
# As variacoes com acento precisam da letra acentuada no grupo: 'Ação' tem ç e ã,
# e um padrao so com [aã] nao casa com maiuscula acentuada (so com re.IGNORECASE
# em ASCII). Medido: 'Ação:' ficava sem rótulo e o campo saia da saida inteira.
_RE_SPLIT_ROTULO = re.compile(
    r"(?<![0-9A-Za-zÀ-ÿ_])(sujeito|sujeita|acao|a[cç][aã]o|pose|cenario|cen[aá]rio|"
    r"iluminacao|ilumina[cç][aã]o|estilo_camera|estilo e c[aâ]mera|camera|c[aâ]mera)"
    r"\s*[:\-]\s*",
    re.IGNORECASE,
)


def _campos_rotulados(txt):
    """Divide o texto em [(rótulo_normalizado, bloco)] se ele for a extração
    estruturada da visão. Devolve [] para prosa comum.

    A visão devolve os campos como 'sujeito: ... cenario: ...' num JSON que o
    app achata numa linha só, e os VALORES contêm dois-pontões próprios. Por
    isso não dá para splitar por string: é preciso achar a posição de cada
    rótulo com finditer e cortar o texto entre uma posição e a seguinte.

    Cuidado com a fronteira (?<![0-9A-Za-zÀ-ÿ_]): sem ela o grupo 'acao' casa
    DENTRO de 'iluminacao' (ilumina-CA-O) e o campo iluminação se perde inteiro.
    """
    if not txt or len(txt.strip()) < 20:
        return []

    # posicoes de cada rotulo, na ordem em que aparecem
    marcas = [(m.start(), m.end(), m.group(1)) for m in _RE_SPLIT_ROTULO.finditer(txt)]
    if len(marcas) < 2:
        return []

    campos = []
    for i, (ini_m, fim_m, rot) in enumerate(marcas):
        # o valor vai do fim do rótulo ate o inicio do próximo (ou o fim do texto)
        prox = marcas[i + 1][0] if i + 1 < len(marcas) else len(txt)
        valor = txt[fim_m:prox].strip()
        if valor:
            campos.append((_norm_rotulo(rot), valor))
    return campos


def _norm_rotulo(r):
    r = (r or "").lower()
    r2 = r.replace("ç","c").replace("ã","a").replace("á","a").replace("â","a").replace("ê","e")
    if r.startswith("sujeit"):
        return "sujeito"
    if r2.startswith("a") and ("c" in r2 or "cao" in r2 or "aca" in r2 or r2.startswith("acao") or "c" in r2.replace("ç","c")):
        return "acao"
    if r2.startswith("pose"):
        return "acao"
    if r2.startswith("cen"):
        return "cenario"
    if r2.startswith("ilum") or r2.startswith("luz"):
        return "iluminacao"
    return "estilo_camera"


def _cortar_por_campo(campos, teto_fonte):
    """Corta por COBERTURA de campo: cada campo recebe uma cota, e só dentro da
    cota vale a ordem de densidade. Assim, quando o orçamento aperta, o corte cai
    no detalhe decorativo de dentro de cada campo — nunca no campo inteiro.

    Devolve o texto com os rótulos preservados, na ordem original em que a
    visão os entregou.
    """
    presentes = [(k, v) for k, v in campos if v.strip()]
    if not presentes:
        return ""
    soma = sum(_PESO_CAMPO.get(k, 8) for k, _ in presentes)
    cotas = {k: max(int(teto_fonte * _PESO_CAMPO.get(k, 8) / soma), 1)
             for k, _ in presentes}
    piso = int(teto_fonte * _PISO_CAMPO)

    # OVERHEAD: cada campo ganha um rotulo ("cenario: ") e um fechamento (" …").
    # Isso sao tokens REAIS na saida final, mas nao contados no gasto durante a
    # distribuicao — o que fazia a saida passar do teto (medido: Krea +9). Reserva
    # o overhead aqui, para que o conteudo caiba de verdade.
    overhead = sum(_estimar_tokens(f"{k}: …") for k, _ in presentes)
    teto_conteudo = max(teto_fonte - overhead, piso)

    # ── 1) Piso IGUAL para todo campo, antes de qualquer coisa ──
    # Se o sujeito (34%) fosse servido primeiro, ele consumia o orçamento e os
    # campos menores ficavam com ZERO — foi o que aconteceu com iluminacao no
    # teste com foto real. Todo campo tem piso antes de o sujeito ganhar extra.
    escolhidos = {}
    gasto = 0
    for k, v in sorted(presentes, key=lambda x: _PESO_CAMPO.get(x[0], 8)):
        if gasto >= teto_conteudo:
            break
        bloco, _ = _cortar_por_frase(v, max(piso, cotas[k]))
        escolhidos[k] = bloco
        gasto += _estimar_tokens(bloco)

    # ── 2) Redistribui o que sobrou: cada campo ganha uma fatia igual ──
    sobra = teto_conteudo - gasto
    if sobra > 0:
        for k, v in sorted(presentes, key=lambda x: -_PESO_CAMPO.get(x[0], 8)):
            if sobra <= 0:
                break
            atual = _estimar_tokens(escolhidos.get(k, ""))
            sobra -= atual
            if sobra <= 0:
                break
            parcela = min(sobra, max(0, _estimar_tokens(v) - atual))
            if parcela <= 0:
                continue
            # teto hard: este campo nao pode fazer o TOTAL passar do teto_fonte
            teto_deste = min(atual + parcela, teto_conteudo - (gasto - atual))
            if teto_deste <= atual:
                continue
            bloco, _ = _cortar_por_frase(v, teto_deste)
            gasto += _estimar_tokens(bloco) - atual
            escolhidos[k] = bloco

    # ── 3) Remonta na ordem original da visão ──
    # O separador e' ". " (ponto + espaco): se fossem so espaco, o rotulo do
    # campo seguinte encostaria no texto do anterior e o app leria os dois como
    # uma frase so — que e como o campo iluminacao desaparecia.
    ordem = {k: i for i, (k, _) in enumerate(presentes)}
    partes = []
    for k, v in sorted(escolhidos.items(), key=lambda x: ordem.get(x[0], 99)):
        v = v.strip()
        if not v:
            continue
        # _cortar_por_frase ja fecha com reticencias; juntar com '. ' daria '…. '.
        # Remove qualquer pontuacao final e devolve UMA reticencia limpa.
        # _cortar_por_frase fecha o trecho como "frase. …" (PONTO + reticencias).
        # Juntar isso com o separador ". " produzia "…. ". Ponto e reticencias
        # sao o mesmo sinal de corte: mantemos UM so.
        # _cortar_por_frase fecha o trecho como "frase. …" (ponto + reticencias).
        # Ponto e reticencias sao o mesmo sinal de corte — mantemos UM so, e o
        # separador entre campos e' so espaco (com '. ' viraria '…. ').
        v = v.rstrip()
        cortado = bool(re.search(r"(\s*\.){1,3}\s*…\s*$", v))
        v = re.sub(r"(\s*\.){1,3}\s*…\s*$", "", v) or v
        v = v.rstrip(" .,;:…")
        # fecha com o sinal que faz sentido: reticencias se cortou, ponto se nao
        partes.append(f"{k}: {v}" + (" …" if cortado else "."))
    saida = " ".join(partes)

    # REDE DE SEGURANCA: a reserva de overhead e' uma ESTIMATIVA — o fechamento
    # (" …") so entra depois da medicao do gasto, e o rstrip pode devolver mais
    # tokens do que retirou (Krea: +9). Se passou, corta o campo menos prioritario
    # ate caber. Melhor perder detalhe do que estourar o teto do destino.
    if _estimar_tokens(saida) > teto_fonte:
        for k, _ in sorted(presentes, key=lambda x: _PESO_CAMPO.get(x[0], 8)):
            if _estimar_tokens(saida) <= teto_fonte:
                break
            curto, cortou = _cortar_por_frase(dict(presentes)[k],
                                              max(piso, _estimar_tokens(dict(escolhidos)[k]) - 12))
            if cortou and curto != escolhidos[k]:
                escolhidos[k] = curto
                partes = []
                for kk, vv in sorted(escolhidos.items(),
                                      key=lambda x: ordem.get(x[0], 99)):
                    c2 = bool(re.search(r"(\s*\.){1,3}\s*…\s*$", vv))
                    vv = re.sub(r"(\s*\.){1,3}\s*…\s*$", "", vv) or vv
                    partes.append(f"{kk}: {vv.rstrip(' .,;:…')}" + (" …" if c2 else "."))
                saida = " ".join(partes)
    return saida


def _get_secret(name: str):
    try:
        return st.secrets[name]
    except Exception:
        return None

PS_FERNET_KEY = _get_secret("PS_FERNET_KEY")
APPS_SCRIPT_URL = _get_secret("APPS_SCRIPT_URL")

# Estado auth
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "expiracao" not in st.session_state:
    st.session_state["expiracao"] = ""

# ── Sidebar: Centro de Conexão ──
with st.sidebar:
    st.markdown("### ⚡ Prompt Studio")
    if st.session_state["autenticado"]:
        st.caption(f"Logado: {mascarar_email(st.session_state['user_email'])}")
        if not fernet_disponivel():
            st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY.")
        st.markdown("---")
        st.markdown("#### 🔌 Centro de Conexão")
        st.caption("2 motores isolados — mesma chave pode ser usada nas duas vias (cotas separadas).")
        _cfg = carregar_config(st.session_state["user_email"])
        chave_visao_input = st.text_input("Chave Visão (BYOK)", value=_cfg.get("chaves", {}).get("Chave Visao", ""), type="password", key="input_key_visao")
        modelo_visao_sel = st.selectbox("Modelo Visão", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_visao", MODELO_VISAO_PADRAO)) if _cfg.get("modelo_visao") in OPCOES_GEMINI_3 else 0, key="modelo_visao_select")
        chave_texto_input = st.text_input("Chave Texto (BYOK)", value=_cfg.get("chaves", {}).get("Chave Texto", ""), type="password", key="input_key_texto")
        modelo_texto_sel = st.selectbox("Modelo Texto", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_texto", MODELO_TEXTO_PADRAO)) if _cfg.get("modelo_texto") in OPCOES_GEMINI_3 else 0, key="modelo_texto_select")
        if st.button("🔌 Conectar Motores Isolados", use_container_width=True, type="primary"):
            if not fernet_disponivel():
                st.error("Criptografia desabilitada — configure PS_FERNET_KEY antes de salvar.")
            elif modelo_visao_sel not in OPCOES_GEMINI_3 or modelo_texto_sel not in OPCOES_GEMINI_3:
                st.error("Modelo inválido — use 3.5/3.6/3.7-flash (abaixo de 3.X é obsoleto).")
            else:
                dados = {"chaves": {"Chave Visao": chave_visao_input.strip(), "Chave Texto": chave_texto_input.strip()}, "modelo_visao": modelo_visao_sel, "modelo_texto": modelo_texto_sel, "modelo_padrao": modelo_texto_sel}
                ok, msg = salvar_config(dados, email=st.session_state["user_email"])
                if ok:
                    st.success("Motores conectados com sucesso!")
                else:
                    st.warning(msg or "Erro ao salvar na nuvem — cópia local salva.")
        st.markdown("---")
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["user_email"] = ""
            st.session_state["expiracao"] = ""
            st.rerun()
    else:
        st.caption("Faça login com o e-mail da compra.")

# ── Tela 1: Página de Entrada (Login) ──
if not st.session_state["autenticado"]:
    if not fernet_disponivel():
        st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY em .streamlit/secrets.toml (Etapa 1.3).")
    st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Pare de lutar contra a IA.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Transforme ideia vaga em prompt pronto para ComfyUI/Midjourney — qualidade suprema sem inventar, menos tentativas.</p>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;"><span class="byok-badge">🔌 BYOK — suas chaves, suas cotas, nada salvo no servidor</span></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"uma elfa na escadaria"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">score_9, score_8_up, source_anime, 1girl, solo, long silver hair, green eyes, ornate armor, standing on stone stairs, volumetric light, highly detailed...</div>', unsafe_allow_html=True)
        img1 = pathlib.Path(__file__).parent / "assets" / "elfa.jpg"
        try:
            if img1.exists():
                st.image(str(img1), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">📚</div>', unsafe_allow_html=True)
            st.caption("elfa.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"carro esportivo futurista"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">photorealistic, ultra detailed, sports car, metallic paint, studio lighting, 85mm lens, shallow depth of field, 8k...</div>', unsafe_allow_html=True)
        img2 = pathlib.Path(__file__).parent / "assets" / "carro.jpg"
        try:
            if img2.exists():
                st.image(str(img2), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#059669 0%,#2563eb 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">📸</div>', unsafe_allow_html=True)
            st.caption("carro.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="plan-container">', unsafe_allow_html=True)
    st.markdown("### Escolha seu plano")
    st.caption("Pagamento fora do app — compra na Kiwify libera seu e-mail na planilha.")
    c1, c2, c3 = st.columns(3)
    _KIWIFY_FALLBACK = {
        "LINK_KIWIFY_15_DIAS": "https://pay.kiwify.com.br/MXVL98k",
        "LINK_KIWIFY_30_DIAS": "https://pay.kiwify.com.br/dyfEGe5",
        "LINK_KIWIFY_90_DIAS": "https://pay.kiwify.com.br/xo0m3rF",
    }
    def _kiwify_link(days_key):
        v = _get_secret(days_key)
        if v and "PLACEHOLDER" not in str(v) and str(v).strip() not in ("", "#"):
            return v
        return _KIWIFY_FALLBACK.get(days_key, "#")
    with c1:
        st.markdown("**15 dias**")
        st.link_button("Comprar 15 dias", _kiwify_link("LINK_KIWIFY_15_DIAS"), use_container_width=True)
    with c2:
        st.markdown("**30 dias**")
        st.link_button("Comprar 30 dias", _kiwify_link("LINK_KIWIFY_30_DIAS"), use_container_width=True, type="primary")
    with c3:
        st.markdown("**90 dias**")
        st.link_button("Comprar 90 dias", _kiwify_link("LINK_KIWIFY_90_DIAS"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Entrar no Sistema")
    st.caption("Use o e-mail da compra na Kiwify. Validação e prazo na planilha (sem senha).")
    email_input = st.text_input("E-mail da compra", placeholder="seu@email.com", key="login_email")
    if st.button("Entrar no Sistema", type="primary", use_container_width=True):
        email = (email_input or "").strip()
        if not email:
            st.error("Digite seu e-mail.")
        elif "@" not in email:
            st.error("E-mail inválido — verifique o e-mail da compra.")
        else:
            with st.spinner("Verificando acesso..."):
                ok, exp, erro = verificar_acesso_sheets(email)
            if ok:
                st.session_state["autenticado"] = True
                st.session_state["user_email"] = email.lower()
                st.session_state["expiracao"] = exp
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error(erro or "E-mail não encontrado — verifique o e-mail da compra.")
    st.caption("LGPD: Imagens com pessoas são processadas apenas para extração e descartadas. Nada é salvo no servidor.")
    st.stop()

# ── Tela 2: Cockpit Único (Etapa 3 + 4) ──
st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
st.markdown('<h1 class="ps-title">Sua Ideia. Seu Motor. Controle Total.</h1>', unsafe_allow_html=True)
st.markdown('<div class="ps-slogan">A porta é nossa, mas as chaves são suas.</div>', unsafe_allow_html=True)

# State Sync — evita StreamlitAPIException ao alterar widget após criação
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

# Init chaves ancoradas
if "ck_ideia_input" not in st.session_state: st.session_state.ck_ideia_input = ""
if "ck_preprompt_editado" not in st.session_state: st.session_state.ck_preprompt_editado = ""
if "img_suj" not in st.session_state: st.session_state.img_suj = ""
if "img_cen" not in st.session_state: st.session_state.img_cen = ""
if "img_act" not in st.session_state: st.session_state.img_act = ""
if "img_ilu" not in st.session_state: st.session_state.img_ilu = ""
if "img_est" not in st.session_state: st.session_state.img_est = ""
if "ck_estilo_conversao" not in st.session_state: st.session_state.ck_estilo_conversao = "Manter Estilo Original"
if "ck_foco_contexto" not in st.session_state: st.session_state.ck_foco_contexto = "Harmônico (Preencher/Embelezar)"
if "ck_sens_slider" not in st.session_state: st.session_state.ck_sens_slider = OPCOES_SENSUALIDADE[1]

if not fernet_disponivel():
    st.warning("⚠️ Conecte suas chaves na barra lateral para ativar os motores. (Criptografia desabilitada sem PS_FERNET_KEY)")
else:
    _cfg_check = carregar_config(st.session_state["user_email"])
    if not _cfg_check.get("chaves", {}).get("Chave Visao") and not _cfg_check.get("chaves", {}).get("Chave Texto"):
        st.info("💡 Conecte suas chaves na barra lateral para ativar os motores.")

# --------------------------------------------------------------------------
# PASSO 0: Motor Destino (OBRIGATÓRIO E PRIMEIRO)
# --------------------------------------------------------------------------
# O destino define o FORMATO e o TETO da saída final. Escolhê-lo por último
# (como estava) obrigava a visão a extrair no escuro e a rascunhar a cena sem
# saber o formato-alvo; só depois se descobria que o material não cabia — com a
# extração e o rascunho já pagos em tokens.
#
# Escolhendo aqui, na PRIMEIRA etapa, tudo abaixo já trabalha ciente do alvo:
#   - a visão extrai com o orçamento DERIVADO deste destino;
#   - o rascunho nasce no formato que o destino espera;
#   - a síntese final não precisa reprocessar nada.
st.markdown("### 0️⃣ Passo 0: Motor Destino (Obrigatório)")
st.caption("Defina primeiro para qual plataforma o prompt será compilado. Tudo o que vem "
            "depois — inclusive a extração da imagem — respeita o formato e o limite de "
            "tokens deste motor. Escolher por último desperdiça trabalho.")
dest_sel = st.selectbox("Plataforma de Imagem Alvo:", OPCOES_DESTINO, key="ck_destino_select",
                        label_visibility="collapsed")
_perfil_destino = _perfil_do_destino(dest_sel) if dest_sel != OPCOES_DESTINO[0] else {}
if _perfil_destino:
    st.caption(f"🎯 **{dest_sel}** · formato **{_perfil_destino.get('structure','')}** · "
               f"teto **{_perfil_destino.get('max_tokens',0)} tokens** para prompt + "
               f"negative + legenda + hashtags.")
else:
    st.info("🛑 Escolha o motor de destino para liberar a extração de imagem, o rascunho e a "
            "geração do prompt. Sem ele não há formato nem orçamento definidos.")
_destino_escolhido = bool(_perfil_destino)

# TROCAR DE DESTINO INVALIDA O TRABALHO JÁ FEITO: a extração foi calibrada para
# o teto/formato do destino anterior, e mantê-la obriga a síntese final a
# reprocessar do zero — o desperdício que esta mudança de sequência elimina.
_destino_anterior = st.session_state.get("ck_destino_aplicado")
if _destino_escolhido and _destino_anterior and _destino_anterior != dest_sel:
    for _k in ["ck_img_parametros", "ck_preprompt", "ck_preprompt_editado",
               "ck_diagnostico", "ck_prompt_final", "ck_sugestoes_marcadas",
               "img_suj", "img_cen", "img_act", "img_ilu", "img_est"]:
        st.session_state.pop(_k, None)
    for _k in ["_pending_img_suj", "_pending_img_cen", "_pending_img_act",
               "_pending_img_ilu", "_pending_img_est", "_pending_ck_preprompt_editado"]:
        st.session_state.pop(_k, None)
    st.info(f"🔄 Destino alterado para **{dest_sel}**. Extração e rascunho anteriores foram "
            "descartados — refaça a extração ciente do novo formato.")
if _destino_escolhido:
    st.session_state["ck_destino_aplicado"] = dest_sel

# --------------------------------------------------------------------------
# PASSO 1: A Ideia
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 1️⃣ Passo 1: A Sua Ideia (A Narrativa Visual)")
st.caption("O ponto de partida. Descreva o que imagina ou veja a caixa preencher-se usando o Passo 2.")
st.text_area("Insira a sua Ideia:", key="ck_ideia_input", height=140, label_visibility="collapsed")
if st.button("🗑️ Limpar Ideia", use_container_width=False):
    for k in ["ck_img_parametros", "ck_preprompt", "ck_preprompt_editado", "ck_diagnostico", "ck_prompt_final", "ck_sugestoes_marcadas",
              "ck_ideia_input", "img_suj", "img_cen", "img_act", "img_ilu", "img_est",
              "_pending_ck_ideia_input", "_pending_ck_preprompt_editado", "_pending_img_suj", "_pending_img_cen", "_pending_img_act", "_pending_img_ilu", "_pending_img_est"]:
        st.session_state.pop(k, None)
    st.session_state["_pending_ck_ideia_input"] = ""
    st.session_state["_pending_ck_preprompt_editado"] = ""
    st.session_state["_pending_img_suj"] = ""
    st.session_state["_pending_img_cen"] = ""
    st.session_state["_pending_img_act"] = ""
    st.session_state["_pending_img_ilu"] = ""
    st.session_state["_pending_img_est"] = ""
    st.rerun()

# --------------------------------------------------------------------------
# PASSO 2: Referência Óptica (Imagem Opcional) — Etapa 4 pronta, já incluída
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 2️⃣ Passo 2: Referência Óptica (Opcional)")
st.caption("Sem inspiração para escrever? Faça upload de uma imagem. A Via de Visão extrairá os micro-detalhes para o Passo 1.")
col_img1, col_img2 = st.columns([4, 6])
with col_img1:
    img_file = st.file_uploader("Upload de Referência", type=["png", "jpg", "jpeg", "webp"], key="ck_img_uploader", label_visibility="collapsed")
with col_img2:
    st.write(" ")
    btn_ler = st.button("👁️ Extrair Imagem (Motor de Visão)", use_container_width=True,
                        disabled=not _destino_escolhido)
if not _destino_escolhido:
    st.caption("🔒 Selecione o motor de destino no Passo 0 para liberar a extração — o "
               "orçamento da visão é derivado do teto desse motor.")
if btn_ler:
    if not img_file: st.warning("Selecione uma imagem primeiro.")
    else:
        with st.spinner("Analisando matriz óptica com Varredura Ultra-Densa..."):
            try:
                modelo_base = st.session_state.get("modelo_visao_select", MODELO_VISAO_PADRAO)
                estilo_conversao = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                sens_escolhida = st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1])
                res = _chamar_motor_visao(img_file, estilo_conversao, sens_escolhida,
                                          modelo_base, _teto_destino(dest_sel))
                if res["tipo"] == "json":
                    st.session_state["ck_img_parametros"] = res["dados"]
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
            except Exception as e:
                st.error(_msg_erro_amigavel(e))
                with st.expander("🔍 Diagnóstico técnico — copie e me envie se persistir", expanded=False):
                    st.code(_msg_erro_diagnostico(e), language="text")
                    st.caption(f"Modelo: {st.session_state.get('modelo_visao_select', MODELO_VISAO_PADRAO)} · Arquivo: {img_file.name if img_file else '?'} · Tamanho: {img_file.size/1024:.0f} KB" if img_file else "")
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
# PASSO 3: Modificadores
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 3️⃣ Passo 3: Modificadores Globais")
st.caption("ℹ️ *Aviso: Estes filtros guiam a geração do seu prompt final. (Também alteram a leitura caso envie uma Imagem no Passo 2).*")
with st.container(border=True):
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: estilo_conversao = st.selectbox("Estilo de Arte:", ["Manter Estilo Original", "📸 Converter para Fotorrealismo", "🎨 Converter para Anime"], key="ck_estilo_conversao")
    with col_m2: foco_contexto = st.selectbox("Foco e Contexto:", ["Harmônico (Preencher/Embelezar)", "Literal (Direto, Sem Floreios)"], key="ck_foco_contexto")
    with col_m3: sens_escolhida = st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider")

# --------------------------------------------------------------------------
# PASSO 4: Rascunho & Validação (Opcionais Prévios)
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 4️⃣ Passo 4: Rascunho & Validação (Opcional)")
col_b1, col_b2 = st.columns(2)
with col_b1: btn_pre = st.button("👁️ Rascunhar Cena (Via Motor de Texto)", use_container_width=True, disabled=not _destino_escolhido)
with col_b2: btn_ava = st.button("🔍 Auditar no Compositômetro (Raio-X)", use_container_width=True, disabled=not _destino_escolhido)
if not _destino_escolhido:
    st.caption("🔒 O rascunho e a auditoria dependem do motor de destino (Passo 0) — sem ele "
               "não há formato-alvo para rascunhar.")
if btn_pre:
    if not st.session_state.ck_ideia_input.strip(): st.warning("Escreva a sua Ideia no Passo 1.")
    else:
        with st.spinner("Desenhando a cena com o Motor de Texto..."):
            try:
                _estilo = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                # O rascunho nasce no FORMATO do destino: antes esta etapa não
                # sabia o alvo e produzia prosa que a síntese final tinha de
                # reprocessar por completo.
                p = f"IDEIA:\n{st.session_state.ck_ideia_input}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sens_escolhida}']"
                p += (f"\n[DESTINO ALVO: {dest_sel}]"
                      f"\n[FORMATO EXIGIDO: {_perfil_destino.get('structure','')}]"
                      f"\n[ORIENTAÇÃO TÉCNICA DO DESTINO: {_perfil_destino.get('dica_tecnica','')}]"
                      "\n[RASCUNHO = FONTE DA SÍNTESE FINAL]: descreva a cena nos termos que o "
                      "destino consome (nominal técnico, sem adjetivo genérico). Não escreva "
                      "meta-comentário sobre o formato.")
                if "Fotorrealismo" in _estilo:
                    p += "\n[MODIFICADOR ESTILO — CONVERTER PARA FOTORREALISMO]: Reescreva TODA a cena como FOTOGRAFIA REAL. Substitua 'anime, ilustração, desenho, traço' por 'foto fotorrealista, pele real, textura fotográfica'. PROÍBA vocabulário anime/cartoon/ilustração."
                elif "Anime" in _estilo:
                    p += "\n[MODIFICADOR ESTILO — CONVERTER PARA ANIME 2D]: Reescreva TODA a cena como ILUSTRAÇÃO ANIME 2D. Substitua 'foto, câmera de smartphone, lente 26mm, fotorrealista' por 'ilustração anime, traço anime limpo, cel shading, linhas nítidas, anime style'. PROÍBA 'foto, smartphone, lente, fotorrealista'."
                if "Literal" in foco_contexto: p += "\n[AGENTE LITERAL]: Seja 100% fiel, sem floreios estéticos inúteis."
                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
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
                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
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
# PASSO 5: Síntese Final
# --------------------------------------------------------------------------
# O destino NÃO é escolhido aqui: vem do Passo 0. Este passo só compila.
st.markdown("---")
st.markdown("### 5️⃣ Passo 5: Síntese Final")
st.caption(f"Compilando a narrativa para **{dest_sel}** no formato "
            f"**{_perfil_destino.get('structure','')}**, teto de "
            f"**{_teto_destino(dest_sel)} tokens**.")
btn_exec = st.button("⚡ Gerar Código do Prompt", type="primary", use_container_width=True)
if btn_exec:
    if not _destino_escolhido:
        st.error("🛑 Pare! Selecione o motor de destino no Passo 0 antes de gerar.")
    elif not st.session_state.ck_ideia_input.strip(): st.warning("Descreva a sua Ideia no Passo 1 antes de gerar.")
    else:
        with st.spinner(f"Compilando sintaxe ultra-otimizada para {dest_sel}..."):
            try:
                eng = BANCO_DE_MOTORES[dest_sel]
                max_tokens = _teto_destino(dest_sel)
                structure = _perfil_destino.get("structure", "general")
                _dica = eng.get("dica_tecnica", "")
                _dica_txt = f"\n💡 DICA TÉCNICA: {_dica}" if _dica else ""
                bloco = f"\n\n======================================\n3. SINTAXE NATIVA: {dest_sel}\n======================================\n- POSITIVO: {eng['regra_positivo']}\n- NEGATIVO: {eng.get('regra_negativo', 'N/A')}{_dica_txt}\n\nSAÍDA OBRIGATÓRIA:\n1. PROMPT (ENGLISH)\n2. NEGATIVE PROMPT DINÂMICO (ENGLISH)\n3. LEGENDA\n4. HASHTAGS"

                # ── ORÇAMENTO REAL (tokens, não caracteres) ──
                # O código antigo usava txt_b[:max_tokens] e chamava de tokens:
                # em PT (≈3 car./token) isso cortava ~67% antes da hora, sempre
                # no meio da frase. Agora mede tokens e corta por fronteira de
                # frase, escolhendo o que sobra por densidade de informação.
                txt_b = st.session_state.ck_preprompt_editado if st.session_state.get("ck_preprompt") else st.session_state.ck_ideia_input
                sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])
                sug_str = "\n".join(f"- {s}" for s in sug_aceitas) if sug_aceitas else "Nenhuma sugestão."
                est_antes = _estimar_tokens(txt_b)
                txt_b, est_fonte, cortou = _orcamento_fonte(txt_b, max_tokens)
                if cortou:
                    st.info(f"📥 Narrativa adensada para o formato do destino: "
                            f"{est_antes} → {est_fonte} tokens (teto-fonte "
                            f"{int(max_tokens*0.65)}). Sujeito, luz e óptica preservados.")

                # ── P-Base ──
                p = f"DESTINO: {dest_sel}\nRATING: {sens_escolhida}\nFORMATO: {structure}\n\n1. NARRATIVA VISUAL (FONTE DA TRADUÇÃO):\n{txt_b}\n\n2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}"

                # ── Injeção estrutural por DESTINO (uma vez, sem duplicação) ──
                # Bug anterior: um if/elif chain com indentação errada, cuja
                # linha inicial ficou dentro do `if len(txt_b) > max_tokens:`.
                # O bloco só rodava quando o texto excedia o teto, e a linha
                # seguinte sobrescrevia `p` incondicionalmente — descartando
                # toda a injeção. Aqui a seleção é por ALIAS do perfil.
                _dest_lower = dest_sel.lower()
                if "flux" in _dest_lower:
                    p += "\n\n[FLUX STRUCTURE: subject | context | lighting | style]"
                elif "ideogram" in _dest_lower:
                    p += "\n\n[IDEOGRAM STRUCTURE: concept | elements | colors (max 3) | composition]"
                elif "midjourney" in _dest_lower:
                    p += "\n\n[MJ STRUCTURE: subject + --v 6.1 --style raw --ar 16:9]"
                elif any(m in _dest_lower for m in ["pony", "sdxl", "comfyui"]):
                    p += "\n\n[SDXL/PONY STRUCTURE: positive-tags, negative-tags]"
                elif "krea" in _dest_lower:
                    p += "\n\n[KREA STRUCTURE: instructions | subject | style-params]"
                elif "illustrious" in _dest_lower:
                    p += "\n\n[ILLUSTRIOUS STRUCTURE: style (artist/movement first) | subject | quality | negative]"

                # Estilo e regras — BLOCO ÚNICO
                _estilo_final = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                if "Fotorrealismo" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO PHOTOREALISM]: Rewrite entire scene as photorealistic photo, real skin, photographic texture, photorealistic. PROHIBIT anime/cartoon/illustration/drawing/cel shading terms."
                elif "Anime" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO ANIME 2D]: Rewrite entire scene as 2D anime illustration, clean anime linework, cel shading, anime style. Replace photo/smartphone/26mm/photorealistic with anime illustration terms. PROHIBIT photo/smartphone lens/photorealistic terms."
                if "Literal" in foco_contexto:
                    p += "\n[MODO LITERAL]: Remova floreios poéticos/metafóricos, MAS MANTENHA todas as características do sujeito e os detalhes principais da composição. LITERAL NÃO É RESUMO E NÃO É OMISSÃO."

                # ── ORÇAMENTO DE SAÍDA (substitui o "IGNORE o limite") ──
                # O código antigo mandava "IGNORE o limite" — sem teto real, o
                # modelo era incentivado a inflar. Agora há teto duro + ordem
                # de prioridade: o excedente cede legenda/hashtags primeiro.
                p += (
                    f"\n\n⚠️ ORÇAMENTO DE SAÍDA — TETO DURO: {max_tokens} tokens para TUDO (PROMPT + NEGATIVE + LEGENDA + HASHTAGS).\n"
                    "- DENSIDADE, NÃO VOLUME: cada palavra deve ganhar peso. Adjetivo genérico ('bonito','belo','incrível') = 0 pontos. Nominal técnico ('85mm','rim light','f1.4') = alto valor.\n"
                    "- ORDEM DE PRIORIDADE quando o teto aperta: (1) sujeito/fidelidade (2) ação+pose (3) cenário fg/mg/bg (4) luz (5) câmera (6) legenda/hashtags — corte do 6 para o 1, nunca do 1 para o 2.\n"
                    "- PRECEDÊNCIA: FIDELIDADE > ORÇAMENTO, mas 'acima do orçamento' NÃO é licença para inflar nem omitir: é ordem de espremer MAIS DENSIDADE no mesmo teto.\n"
                    "- 'PROMPT' E 'NEGATIVE' EXCLUSIVAMENTE EM INGLÊS."
                )

                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
                res, prov = _chamar_motor_texto(SYS_MESTRE_CORE, bloco + "\n\n" + p, modelo_gemini=modelo_base)
                st.session_state["ck_prompt_final"] = res
                st.session_state["ck_prov_usado"] = prov
                st.session_state["ck_dest_usado"] = dest_sel
                st.rerun()
            except Exception as e:
                st.error(_msg_erro_amigavel(e))
                with st.expander("🔍 Diagnóstico técnico — copie e me envie se persistir"):
                    st.code(_msg_erro_diagnostico(e), language="text")
                    try:
                        _sys_len = len(SYS_MESTRE_CORE)
                        _user_len = len(bloco + "\n\n" + p)
                        _cfg_preview = str(_build_gemini_config(SYS_MESTRE_CORE, modelo_base, temperature=0.25))[:800]
                    except Exception as _diag_e:
                        _sys_len = _user_len = 0
                        _cfg_preview = str(_diag_e)[:600]
                    st.caption(f"Modelo: {modelo_base} · System: {_sys_len} chars · User+Bloco: {_user_len} chars")
                    st.code(_cfg_preview, language="text")

# OUTPUT FINAL — BOX COM QUEBRA AUTOMÁTICA + DOWNLOAD LOCAL (SEM NUVEM)
if st.session_state.get("ck_prompt_final"):
    st.markdown("---")
    st.markdown(f"### 📋 Prompt Especializado ({st.session_state.get('ck_dest_usado')})")
    st.caption(f"Gerado via {st.session_state.get('ck_prov_usado')} · Download local — nada é salvo no servidor")
    _final_txt = st.session_state["ck_prompt_final"]
    st.markdown(f"<div class='ps-final-box'>{html.escape(_final_txt)}</div>", unsafe_allow_html=True)
    st.caption("↔️ Quebra automática ativa — sem scroll horizontal.")
    st.download_button("⬇️ Baixar Prompt (.txt)", data=_final_txt, file_name=f"prompt_studio_{st.session_state.get('ck_dest_usado','prompt').replace('/','_').replace(' ','_')}.txt", mime="text/plain", use_container_width=True)
    with st.expander("📋 Copiar manualmente"):
        st.code(_final_txt, language="text")
        st.caption("Selecione tudo (Ctrl+A) → Copiar (Ctrl+C)")
