"""Gerador de prompt 1.0 — Etapa 3: cockpit Acolher→Melhorar→Modificar→Auditar→Baixar (texto) + Visão pronta
PRD/TRD/Fluxo/Briefing/Schema/Plano travados em GERADOR_PROMPT_1.0__AntesDeCodar/*__ENTREVISTA.md
"""
import pathlib
import re
import sys
import html
import base64
import json as _json
import urllib.request
import urllib.error
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
# ── Budget de tokens: medidor real (não chars) + compactação sem perda ──
# FATORES CALIBRADOS contra cl100k_base (proxy do tokenizer Gemini):
#   PT medido 3.27 chars/token · EN medido 4.76 · usamos o MENOR (=conservador:
#   subestima tokens => nunca estoura o teto; superestimar traria de volta o bug).
# O código antigo assumia 4.0 p/ texto PT — 22% de folga fantasma.
_CPT_PT = 3.0
_CPT_EN = 3.85
_CPT_CJK = 1.5
_RE_CJK = re.compile(r"[一-鿿぀-ヿ]")
# Termo de alto valor para um prompt de imagem. Uma frase que contém vários
# destes é sempre preferida a uma frase de avaliação genérica quando o
# orçamento força escolha.
_RE_TERMOS_FORTES = re.compile(
    r"\b\d{1,3}\s?mm\b|\bf/\d[\d.]*|\bISO\s?\d{0,4}\b|\bbokeh\b|\bdof\b|\bHDR\b|"
    r"\banam[oó]rfic\w*|\bvulcaniz\w*|\bter[cç]os\b|\b[aá]mbar\b|\bcontraste\b|"
    r"\bgr[aã]o\b|\b[aá]ngulo\b|\bplano médio\b|\bplano geral\b|\bcontra-luz\b|"
    r"\b[aá]gua\b|\bmetal\w*|\btransl[uú]cid\w*|\bveludo\b|\bcetim\b|\b[lí]quido\b",
    re.IGNORECASE | re.UNICODE,
)
# Termo CONCRETO: nomeia material, cor, peça de roupa ou objeto visível.
# Menos valioso que um termo técnico (mm, f/), mas muito mais que adjetivo
# vago ("bonita", "magnífico") — é o que permite reconstruir a imagem.
_RE_CONCRETOS = re.compile(
    r"\b(cabelo|olhos|pele|roupa|vestido|blusa|camisa|calça|saia|meia|sapato|tenis|tênis|"
    r"colar|brinco|relógio|luva|meia|chapéu|boné|capacete|bandana|lençol|travesseiro|"
    r"cama|sofá|poltrona|mesa|cadeira|Janela|parede|piso|teto|espelho|quadro|luminária|"
    r"porta|grade|cortina|vista|paisagem|torre|prédio|rua|calçada|muro|tijolo|"
    r"couro|seda|algodão|metal|ouro|prata|madeira|vidro|cetim|linho|malha|tecido|"
    r"vermelho|azul|verde|preto|branco|cinza|dourado|prateado|bege|marrom|laranja|"
    r"rosa|roxo|amarelo|vinho|creme|castanho|escuro|claro|"
    r"traça|listra|floral|xadrez|bolso|botão|ziper|cordão|gola| manga|decote|"
    r"plano médio|primeiro plano|segundo plano|ao fundo|à esquerda|à direita)\b",
    re.IGNORECASE | re.UNICODE,
)
# Termo de CÂMERA/LUZ: o de maior peso. Define o resultado da imagem no motor,
# enquanto cor/roupa só ajustam. Inclui PT e EN porque a extração mistura os dois
# ("shallow depth of field", "specular highlights").
_RE_CAMERA_LUZ = re.compile(
    r"\b\d{1,3}\s?mm\b|\bf/\d[\d.]*|\bapertura\b|\bISO\s?\d{3,4}\b|\bbokeh\b|"
    r"\bprofundidade de campo\b|\bshallow depth of field\b|\bdepth of field\b|"
    r"\b[dD]o[fF]\b|\bHDR\b|\banam[oó]rfic\w*|\b[lL]ong exposure\b|\bexposição\b|"
    r"\bspecular\b|\bhighlights?\b|\bretroreflex\w*|\brim light\b|"
    r"\bcontraluz\b|\bcontra-luz\b|\bbokeh\b|\blic[uo] retroilumin\w*|"
    r"\bfonte de luz\b|\bilumina[cç][aã]o\b|\bluz (?:de|principal|vinda|suave|quente)\w*|"
    r"\bvolum[eé]tric\w*|\b[sS]hadow[s]?\b|\bsombras?\b|\bm[Bb]okeh\b|"
    r"\bfoco\b|\benquadrament\w*|\b[cC]omposi[cç][aã]o\b|\bplano (?:m[eé]dio|geral|fechado)\b|"
    r"\bc[âa]mera\b|\blente\b|\bgr[aã]o\b|\bcurva de contraste\b|\bcontraste\b|"
    r"\btemperatura de cor\b|\b[aá]mbar\b|\b[aâ]ngulo (?:baixo|alto|lateral)\w*",
    re.IGNORECASE | re.UNICODE,
)
# Marca de SUJEITO: a frase descreve a pessoa/pessoa-viva. Peso máximo — a
# fidelidade do sujeito é a regra nº 1 do prompt mestre e o que mais destrói a
# imagem quando falta.
_RE_SUJEITO = re.compile(
    r"\b(mulher|homem|menina|menino|jovem|garota|garoto|crian[cç]a|adolescente|"
    r"[eé]lfa|elfo|anjo|dem[oô]nio|robot|androide|pessoa|personagem|modelo|"
    r"cabelo|olhos|pele|rosto|sobancelha|l[aá]bio|l[aá]bios|bochecha|queixo|"
    r"nariz|orelha|ombro|clav[ií]cula|bra[cç]o|perna|coxa|m[aã]o|dedo|cabelo|"
    r"c[aó]mplice|poses?|postura|veste|vestindo|usa|usando|cal[cç]a|meia|"
    r"luva|colar|brinco|rel[oó]gio|tatuagem|makeup|biquini|lingerie|"
    r"woman|man|girl|boy|young|lady|guy|hair|eyes|skin|face|shoulder|arm|leg|"
    r"thigh|wearing|wears|dressed)\b",
    re.IGNORECASE | re.UNICODE,
)


def _cpt(txt: str) -> float:
    """Fator chars/token com detecção de idioma. Salvaguarda: mínimo
    conservador, para que o orçamento NUNCA possa ser furado."""
    if not txt:
        return _CPT_EN
    n = max(len(txt), 1)
    cjk = len(_RE_CJK.findall(txt)) / n
    base = _CPT_PT if cjk < 0.2 else _CPT_EN
    return max(_CPT_CJK, round(base * (1 - cjk) + _CPT_CJK * cjk, 2))


def _estimar_tokens(txt: str) -> int:
    """Tokens = chars / fator. Mesma conta que o corte usa, então o número
    reportado bate com o texto entregue. ~5% de erro vs tiktoken, offline e grátis."""
    if not txt:
        return 0
    return max(1, round(len(txt) / _cpt(txt)))


def _pt_para_denso(texto: str) -> str:
    """Compacta prosa PT de forma SEGURA — sem quebrar gramática.
    Regra: só remove redundância que não carrega significado. NÃO remove
    adjetivos nem preposições (uma versão anterior fazia isso e produzia
    "a iluminação é e natural" / "banco madeira escura" — dano sem ganho:
    a prosa da visão é densa, não enchida de adjetivo, então render ~4%).
    Ganho real de tokens vem do orçamento estruturado por campo, não daqui."""
    t = texto
    # fillers de observação (zero informação visual)
    t = re.sub(r"(?i)[,;]?\s*\b(é possível observar|observa-se|nota-se|o que se ve|não há)\b", "", t)
    # rótulos duplicados ("Sujeito: X Sujeito: X")
    t = re.sub(r"(?im)^(\s*\w+)\s*:\s*", r"\1: ", t)
    # "de" / "do" colados por colagem de vírgula  →  "banco madeira" NÃO é seguro
    # manter; apenas normaliza espaçamento e quebras.
    t = re.sub(r"\s+([,;:.!?])", r"\1", t)
    return re.sub(r"[ \t]{2,}", " ", re.sub(r"\n{3,}", "\n\n", t)).strip()


def _densidade(fr: str) -> tuple:
    """Nota de valor de uma frase, para escolher o que sobrevive ao corte.
    Usada direto em sorted(reverse=True): pontuação maior = mais essencial.

    Peso de câmera/luz é o mais alto de propósito: `85mm`, `f/1.8`, `bokeh`
    e a direção da luz definem o resultado no motor; uma lista de móveis
    (`cama`, `quadro`, `criado-mudo`) é cenário genérico que qualquer imagem
    com o prompt certo reconstrói. Sem esse peso, a frase do 85mm perdia para
    uma frase de enumeração de móveis — exatamente o que acontecia na
    extração real (Arquivo.md).
    """
    n_tec = len(_RE_TERMOS_FORTES.findall(fr))
    n_cam = len(_RE_CAMERA_LUZ.findall(fr))
    n_conc = len(_RE_CONCRETOS.findall(fr))
    n_subj = len(_RE_SUJEITO.findall(fr))
    return (n_subj * 8 + n_cam * 6 + n_tec * 3 + n_conc, -len(fr))


def _cortar_por_palavra(txt: str, max_tokens: int, cpt: float) -> str:
    """Corte SEMIÓTICO por fronteira de FRASE — nunca no meio de uma oração.

    Escolhe as frases por DENSIDADE DE INFORMAÇÃO, não por ordem de aparição.
    O bug que isto corrige: a versão anterior preenchia o orçamento em ordem
    (greedy), ficava sem espaço para a última frase — que é onde a visão
    Engine coloca lente/abertura/bokeh, exatamente o dado mais valioso. Na
    extração real do Arquivo.md, `85mm`, `shallow depth of field` e `bokeh`
    eram exatamente o que sumia.

    A ordem original das frases é preservada na saída, então a leitura continua
    natural para o modelo — só a SELEÇÃO muda.
    """
    limite = int(max_tokens * cpt)
    if len(txt) <= limite:
        return txt
    partes = re.split(r"(?<=[.;:])\s+", txt)
    if len(partes) < 2:
        return txt[:limite].rsplit(" ", 1)[0].rstrip() + "…"
    # ordena por densidade, guardando o índice para reordenar ao final
    ordem = sorted(range(len(partes)), key=lambda i: _densidade(partes[i]), reverse=True)
    orcamento, escolhidos = limite, []
    for i in ordem:
        fr = partes[i]
        n = len(fr) + (1 if escolhidos else 0)
        if n <= orcamento:
            orcamento -= n
            escolhidos.append(i)
    if not escolhidos:
        return txt[:limite].rsplit(" ", 1)[0].rstrip() + "…"
    # devolve na ordem original do texto
    escolhidos.sort()
    saida = " ".join(partes[i] for i in escolhidos)
    return saida + (" …" if len(escolhidos) < len(partes) else "")


def _orcamento_texto_fonte(txt: str, max_tokens: int) -> tuple:
    """Aplica orçamento à narrativa fonte. Devolve (texto, token_est, avisos).
    O teto do destino (max_tokens) é da SAÍDA final — prompt + negative +
    legenda + hashtags. A fonte entra como insumo, então fica em 65% dele;
    o resto é o que o modelo precisa para escrever a saída dentro do teto.

    Blindagem de SUJEITO: quando a extração é prosa sem rótulos (formato real
    do motor de visão), a seleção por densidade sozinha favorecia cenário — na
    extração do Arquivo.md perdia a frase que descrevia a mulher e ficava com
    cama/janela/pôster. Isso viola "FIDELIDADE DO SUJEITO >= 95%". Por isso as
    frases de sujeito recebem peso extra e entram ANTES de qualquer seleção.
    """
    avisos = []
    if not txt:
        return txt, 0, avisos
    est = _estimar_tokens(txt)
    teto_fonte = int(max_tokens * 0.65)
    if est <= teto_fonte:
        return txt, est, avisos
    denso = _pt_para_denso(txt)
    est_d = _estimar_tokens(denso)
    if est_d <= teto_fonte:
        avisos.append(f"📥 Extração compacta: {est} → {est_d} tok (fonte) · detalhe preservado")
        return denso, est_d, avisos

    # Ainda acima do teto: adensa por BLOCO rótulado, com orçamento por peso.
    # Sujeito tem peso 34% e ação 26% — os blocos de menor peso (cenário/luz/
    # estilo) cedem tokens, então nenhum bloco inteiro some e os termos
    # técnicos do fim (85mm, f/1.8, bokeh) sobrevivem.
    campos = _campos_de_prosa(denso)
    if campos:
        ajustados, _ = _aplicar_pesos(campos, teto_fonte)
        novo_txt = _formatar_campos(ajustados)
        est_a = _estimar_tokens(novo_txt)
        if est_a <= teto_fonte:
            avisos.append(
                f"📥 Extração adensada por campo: {est} → {est_a} tok (fonte) · "
                f"sujeito/ação preservados"
            )
            return novo_txt, est_a, avisos

    # Último recurso: corte por fronteira de frase (nunca no meio da oração).
    cortado = _cortar_por_palavra(denso, teto_fonte, _cpt(denso))
    est_c = _estimar_tokens(cortado)
    avisos.append(f"📥 Extração adensada: {est} → {est_c} tok (fonte) · teto {teto_fonte}")
    return cortado, est_c, avisos


def _campos_de_prosa(txt: str) -> dict:
    """Reconstrói os campos {sujeito, acao, ...} a partir da prosa rotulada.
    Devolve {} se o texto não tem a forma "Titulo: corpo" da extração de visão."""
    partes = _RE_BLOCO_TITULO.split(txt)
    if len(partes) < 2:
        return {}
    campos = {}
    for parte in partes:
        m = re.match(r"(?s)^\s*([\w\s/à-ú]{1,20}?)\s*:\s*(.+)$", parte.strip())
        if not m or not m.group(1).strip():
            continue
        cab, corpo = _normalizar_campo(m.group(1)), m.group(2).strip()
        if not corpo:
            continue
        campos[cab] = (campos[cab] + " " + corpo).strip() if cab in campos else corpo
    return campos


_RE_BLOCO_TITULO = re.compile(r"(?im)(?=^\s*\w[\w\s/]{0,20}\s*:)")

# NOTA: PESO_CAMPOS e PISO_CAMPO são definidos junto ao MOTOR DE VISÃO, acima —
# é lá que a ordem de prioridade é uma decisão do programador, não do usuário.

_APELIDOS_CAMPO = {
    "sujeito": "sujeito", "sujeita": "sujeito", "personagem": "sujeito", "subject": "sujeito",
    "acao": "acao", "ação": "acao", "pose": "acao", "postura": "acao", "action": "acao",
    "cenario": "cenario", "cenário": "cenario", "ambiente": "cenario", "background": "cenario",
    "environment": "cenario", "fundo": "cenario",
    "iluminacao": "iluminacao", "iluminação": "iluminacao", "luz": "iluminacao",
    "light": "iluminacao", "lighting": "iluminacao",
    "estilo_camera": "estilo_camera", "estilo e câmera": "estilo_camera",
    "estilo e camera": "estilo_camera", "estilo": "estilo_camera",
    "camera": "estilo_camera", "câmera": "estilo_camera", "style": "estilo_camera",
    "estilo/câmera": "estilo_camera", "estilo/camera": "estilo_camera",
}


def _normalizar_campo(titulo: str) -> str:
    t = re.sub(r"\s+", " ", titulo.strip().lower())
    return _APELIDOS_CAMPO.get(t, t)


def _aplicar_pesos(campos: dict, teto_fonte: int) -> tuple:
    """Adensa cada campo proporcionalmente ao seu peso, SEM descartar campo
    algum. Garante que sujeito/ação sobrevivam e que o conjunto inteiro caiba
    no teto — em vez de o último bloco ser cortado por inteiro.

    Este é o ponto que resolve a raiz: a extração de visão é ESTRUTURADA
    (JSON com 5 campos). Achatar isso em prosa cria um bloco monolítico que
    só pode ser cortado pelo fim. Com orçamento por campo, cada um é adensado
    na proporção da sua importância e nenhum bloco inteiro desaparece."""
    if not campos:
        return campos, teto_fonte
    ests = {k: _estimar_tokens(v) for k, v in campos.items() if v}
    if not ests:
        return campos, teto_fonte
    total = sum(ests.values())
    if total <= teto_fonte:
        return campos, teto_fonte

    # Alocação: o teto da fonte é DIVIDIDO entre os campos por peso de
    # fidelidade. Bug anterior: aplicava a escala global (teto/total) SOBRE a
    # cota proporcional, encolhendo duas vezes — as cotas somavam 246 para um
    # teto de 520, jogando fora 53% do orçamento (e com ele os termos técnicos).
    # Aqui: cota = teto * peso_do_campo / soma_dos_pesos.
    disp = sum(PESO_CAMPOS.get(k, 10) for k in campos) or 1
    cotas = {k: max(int(teto_fonte * PESO_CAMPOS.get(k, 10) / disp), 16) for k in campos}
    out = dict(campos)
    for k in ests:
        if ests[k] > cotas[k]:
            out[k] = _cortar_por_palavra(campos[k], cotas[k], _cpt(campos[k]))

    # Convergência: se a soma ainda estourar (corte por frase arredonda para
    # baixo e as cotas têm piso), reduz o campo de MENOR peso. Piso absoluto de
    # PISO_CAMPO impede esvaziar qualquer campo; se não couber, aceitamos o
    # excedente em vez de destruir detalhe — o aviso de orçamento informa isso.
    for _ in range(8):
        restante = sum(_estimar_tokens(v) for v in out.values()) - teto_fonte
        if restante <= 0:
            break
        base = {k: int(ests[k] * PISO_CAMPO) for k in ests}
        candidatos = [k for k in out
                      if _estimar_tokens(out[k]) > base[k] and out[k] != campos[k]]
        if not candidatos:
            break
        candidatos.sort(key=lambda k: (PESO_CAMPOS.get(k, 5), -_estimar_tokens(out[k])))
        alvo_campos = candidatos[:1]  # 1 por vez: converge devagar, preserva o resto
        for k in alvo_campos:
            passo = max(4, int(restante * 0.6))
            corte = max(base[k], _estimar_tokens(out[k]) - passo)
            novo = _cortar_por_palavra(out[k], corte, _cpt(out[k]))
            if novo == out[k]:
                break  # chegou no piso deste campo
            out[k] = novo
    return out, teto_fonte


def _orcamento_estruturado(dados: dict, max_tokens: int) -> tuple:
    """Orçamento por campo para a extração de visão (quando ela vem em JSON).
    Preserva o rótulo de cada bloco e nunca sacrifica o sujeito inteiro."""
    campos = {}
    for chave, valor in (dados or {}).items():
        if not isinstance(valor, str) or not valor.strip():
            continue
        campos[_normalizar_campo(chave)] = valor.strip()
    if not campos:
        return None, [], {}
    est_total = sum(_estimar_tokens(v) for v in campos.values())
    teto_fonte = int(max_tokens * 0.65)
    avisos = []
    if est_total <= teto_fonte:
        return campos, avisos, {"total": est_total, "teto": teto_fonte}
    # agrupa equivalentes (ex.: "estilo_camera" e "camera" -> um só)
    campos_aj = {}
    for k, v in campos.items():
        campos_aj[k] = (campos_aj[k] + " " + v).strip() if k in campos_aj else v
    ajustados, teto_fonte = _aplicar_pesos(campos_aj, teto_fonte)
    novo = sum(_estimar_tokens(v) for v in ajustados.values())
    avisos.append(
        f"📥 Extração adensada por campo: {est_total} → {novo} tok (fonte) · "
        f"sujeito e ação preservados"
    )
    return ajustados, avisos, {"total": novo, "teto": teto_fonte}


def _formatar_campos(campos: dict) -> str:
    """Renderiza os campos com rótulo legível PT para o prompt final."""
    ROTULO = {
        "sujeito": "Sujeito", "acao": "Ação", "cenario": "Cenário",
        "iluminacao": "Iluminação", "estilo_camera": "Estilo e câmera",
    }
    partes = []
    for k, v in campos.items():
        if v and v.strip():
            partes.append(f"{ROTULO.get(k, k.replace('_', ' ').title())}: {v.strip()}")
    return "\n\n".join(partes)


# Aliases do destino → chave do perfil. Extraído para uma função porque o
# destino agora é escolhido no PASSO 0 e consultado em três lugares: a visão
# (orçamento), o rascunho (formato) e a síntese final (teto).
#
# Bug histórico que isso evita: comparava "sdxl" in "comfyui sdxl" (True, match
# errado) e "zit" nunca batia em "Z-Image Turbo" → caía no fallback de 800.
ALIASES_DESTINO = [
    ("comfyui_sdxl", ["comfyui sdxl", "comfyui_sdxl", "sdxl"]),
    ("flux", ["flux"]),
    ("ideogram", ["ideogram"]),
    ("pony", ["pony"]),
    ("illustrious", ["illustrious"]),
    ("krea2", ["krea"]),
    ("midjourney", ["midjourney", "mj"]),
    ("qwen", ["qwen"]),
    ("ernie", ["ernie"]),
    ("zit", ["z-image", "z image", "zimage", "zit", "turbo"]),
]


def _perfil_do_destino(dest_sel: str) -> dict:
    """Perfil de otimização do destino. {} se nenhum alias bater."""
    dest_lower = (dest_sel or "").lower()
    for key, aliases in ALIASES_DESTINO:
        if any(a in dest_lower for a in aliases):
            return MODEL_PROFILES.get(key, {})
    return {}


def _teto_destino(dest_sel: str) -> int:
    """Teto de tokens da saída final para este destino (400 a 1000)."""
    return _perfil_do_destino(dest_sel).get("max_tokens", 800)


# ════════════════════════════════════════════════════════════════════════════
# MOTOR DE VISÃO — PARTE DO CÓDIGO, NÃO DO USUÁRIO
# ════════════════════════════════════════════════════════════════════════════
# A visão é uma ORIGEM DE DADOS do prompt final, ao lado da ideia digitada.
# Não existe controle do usuário sobre ela: teto, schema, densidade e ordem de
# prioridade são decididos aqui, no código, e valem para toda extração.
#
# FIDELIDADE > COMPACTAÇÃO. A visão é a ÚNICA etapa que enxerga a imagem: se
# ela resume, o detalhe se perde para sempre — nenhuma etapa downstream
# consegue recuperar o que não foi descrito. Portanto o orçamento aqui é
# GENEROSO e derivado do DESTINO escolhido no Passo 0 (que já é obrigatório),
# e o adensamento acontece no consumidor, com hierarquia.
#
# POR QUE O DESTINO ENTRA AQUI: o destino define o formato e o teto da saída
# final. Com ele escolhido antes (Passo 0), a visão já extrai ciente do alvo.
# Escolher o destino por último (como era) obrigava a refazer a extração.

# Hierarquia de fidelidade. Espelha a regra do mestre (FIDELIDADE DO SUJEITO
# >= 95%): quando o teto aperta, cede cenário e acabamento — nunca sujeito,
# nem direção/dureza da luz, nem dados ópticos (mm, f/, bokeh).
PESO_CAMPOS = {
    "sujeito": 34, "acao": 26, "cenario": 16, "iluminacao": 12, "estilo_camera": 12,
}
PISO_CAMPO = 0.30  # nenhum campo pode ficar abaixo de 30% da sua cota

# Multiplicador de fidelidade: a visão escreve ~2.2 palavras por token do teto
# do destino, com piso e teto absolutos. Generoso de propósito — o corte real
# acontece no consumidor, que tem a hierarquia; aqui só impedimos o runaway.
#
# Por que 2.2 e não 1.5: com 1.5, um destino de 400 tokens (Z-Image Turbo)
# resultava em 600 palavras de fonte para 260 tokens de orçamento — pouco demais
# para descrição fiel. A visão é a ÚNICA etapa que enxerga a imagem, então o
# insumo precisa ser substancialmente maior que a saída: sobrar é recuperável,
# faltar é fatal. A redução de 3-4x numa extração detalhada preserva
# sujeito, luz e óptica (verificado em _aplicar_pesos).
VISAO_FATOR_FIDELIDADE = 2.2
VISAO_MIN_PALAVRAS = 700
VISAO_MAX_PALAVRAS = 2000
VISAO_MIN_POR_CAMPO = 120  # nenhum campo pode ser estrangulado abaixo disso


def _teto_visao_palavras(max_tokens_destino: int) -> dict:
    """Orçamento da visão DERIVADO do teto do destino escolhido no Passo 0.

    Aloca as palavras entre os campos pela hierarquia de fidelidade. É teto
    SOFT (a instrução pede fidelidade); o corte rígido fica no consumidor.
    """
    total = int(min(max(int(max_tokens_destino) * VISAO_FATOR_FIDELIDADE,
                         VISAO_MIN_PALAVRAS), VISAO_MAX_PALAVRAS))
    soma = sum(PESO_CAMPOS.values()) or 1
    return {k: max(int(total * PESO_CAMPOS.get(k, 10) / soma), VISAO_MIN_POR_CAMPO)
            for k in PESO_CAMPOS}


# Schema da resposta. Structured output rotula os campos — é o que permite ao
# consumidor adensar POR CAMPO (preservando sujeito e óptica) em vez de cortar
# o fim do texto. Não é a causa raiz do problema de orçamento: o problema era
# não haver teto na origem, não haver estrutura.
SCHEMA_VISAO = {
    "type": "object",
    "properties": {
        "sujeito": {
            "type": "string",
            "description": "Identidade observável: gênero, idade aparente, biotipo, cabelo "
                           "(cor/comprimento/textura/partição), olhos, pele, rosto, corpo, "
                           "roupa (cor/material/textura/corte), acessórios, marcas visíveis. "
                           "Seja exaustivo no que a imagem mostra.",
        },
        "acao": {
            "type": "string",
            "description": "Postura, peso corporal, posição de mãos/dedos/braços/pernas, "
                           "ângulo do corpo, direção do olhar, expressão.",
        },
        "cenario": {
            "type": "string",
            "description": "Ambiente com planos fg/mg/bg, arquitetura, objetos, materiais, "
                           "texturas, cores. Descreva o que dá a identidade do espaço.",
        },
        "iluminacao": {
            "type": "string",
            "description": "Fonte, direção e ângulo, dureza, intensidade, temperatura de cor, "
                           "sombras, preenchimento, contraluz, rim light, volumétrica, "
                           "speculars. NUNCA omita direção nem dureza.",
        },
        "estilo_camera": {
            "type": "string",
            "description": "Lente em mm, abertura f/, profundidade de campo, bokeh, foco, "
                           "enquadramento, ângulo, composição, tipo de imagem, acabamento.",
        },
    },
    "required": ["sujeito", "acao", "cenario", "iluminacao", "estilo_camera"],
}

SYS_VISAO_EXTRACAO = """Você é um perito de reconstrução fotográfica. Sua função é descrever \
uma imagem de forma TÉCNICA e DENSAMENTE NOMINAL, para que alguém possa \
reconstruí-la sem vê-la.

PRINCÍPIO — FIDELIDADE ACIMA DE TUDO:
Esta é a ÚNICA etapa que enxerga a imagem. O que você omitir aqui se perde
permanentemente. Portanto é PREJUDICADO omitir detalhe e NUNCA é permitido
resumir para caber em menos palavras. Descreva tudo o que for visível e
relevante. Se precisar ir além do orçamento, vá — as etapas seguintes sabem
adensar sem perder o essencial; elas não conseguem recuperar o que sumiu aqui.

REGRAS DE DENSIDADE:
1. ADJETIVO GENÉRICO É PROIBIDO: "bonita", "incrível", "magnífico", "linda" = 0 pontos.
   Use o nominal técnico equivalente: "luz volumétrica lateral", "85mm f/1.8",
   "contraste médio-alto", "textura de pele com poros visíveis".
2. Descreva o DIFÍCIL, não o óbvio. Não escreva "uma mulher num quarto" — escreva
   o ângulo, o material, a direção da luz e a cor exata que tornam a cena única.
3. NÚMERO vence ADJETIVO sempre que houver dado concreto: lente, abertura,
   temperatura de cor, plano, textura, cor.
4. Descreva apenas o que está VISÍVEL. Proibido inventar, inferir ou
   complementar com conhecimento genérico do que "costuma" estar ali.
5. NUNCA sacrifique: identidade do sujeito, direção/dureza da luz, dados ópticos
   (mm, f/, DoF, bokeh), enquadramento, materiais decisivos.

ORÇAMENTO DE SAÍDA (referência por campo, em PALAVRAS):
- sujeito: ~{sujeito}
- ação: ~{acao}
- cenário: ~{cenario}
- iluminação: ~{iluminacao}
- estilo e câmera: ~{estilo_camera}

Estes números são REFERÊNCIA de densidade, não um limite de asfixia. Ao sentir
pressão de espaço, ceda APENAS: detalhe atmosférico decorativo, repetição
redundante, preenchimento genérico. Preserve integralmente sujeito, luz (fonte,
direção, dureza) e óptica (mm, f/, DoF, bokeh, enquadramento)."""

# Estilo e sensualidade vêm do app (escolha do usuário no Passo 3), mas são
# aplicados como instrução de LEITURA, não como controle de formato.
_DIR_VISAO = {
    "Fotorrealismo": "Interprete a leitura como FOTOGRAFIA REAL: textura de pele, "
                     "profundidade de campo óptica, lente real. Não use vocabulário de ilustração.",
    "Anime": "Interprete a leitura como ILUSTRAÇÃO ANIME 2D: cel shading, traço limpo, "
             "linhas nítidas. Não use vocabulário de fotografia.",
}


def _montar_prompt_visao(estilo: str, sens: str, tetos: dict) -> str:
    """Monta o prompt da visão. O formato (schema/tetos) é do código; só o
    estilo e a sensualidade vêm da escolha do usuário no Passo 3.

    `tetos` vem do destino escolhido no Passo 0 — é o que amarra a extração ao
    formato final e evita refazer trabalho.
    """
    p = SYS_VISAO_EXTRACAO.format(**tetos)
    if "Fotorrealismo" in (estilo or ""):
        p += "\n\n[DIRETRIZ DE LEITURA — FOTORREALISMO] " + _DIR_VISAO["Fotorrealismo"]
    elif "Anime" in (estilo or ""):
        p += "\n\n[DIRETRIZ DE LEITURA — ANIME 2D] " + _DIR_VISAO["Anime"]
    if sens:
        p += f"\n\n[NÍVEL DE SENSUALIDADE: {sens}] Avalie o modelo sem omitir nem exagerar atributos."
    p += "\n\nDescreva a imagem nos 5 campos do schema. Responda APENAS com o JSON."
    return p


def _img_para_inline(img_file) -> tuple:
    """Upload de imagem → (base64, mime). Mantém a imagem só em memória."""
    img_file.seek(0)
    bruto = img_file.read()
    mime = getattr(img_file, "type", None) or "image/jpeg"
    return base64.b64encode(bruto).decode(), mime


def _chamar_motor_visao(img_file, estilo_conversao: str, sens_escolhida: str,
                       modelo_gemini: str, api_key: str, max_tokens_destino: int) -> dict:
    """Motor de visão. É origem de dados do prompt final, não uma feature
    configurável: o schema, a densidade e a ordem de prioridade estão no código.

    `max_tokens_destino` é o teto do destino escolhido no Passo 0. A visão é a
    única etapa que enxerga a imagem, então NÃO a estrangulamos: extraímos com
    fidelidade e deixamos o adensamento com hierarquia para o consumidor. O
    único limite aqui é de runaway (maxOutputTokens), bem acima do necessário.

    Devolve {"tipo": "json", "dados": {...5 campos...}} ou {"tipo": "texto", ...}.
    """
    if not api_key:
        raise RuntimeError("Chave Visão não configurada — conecte sua chave na barra lateral.")

    tetos = _teto_visao_palavras(max_tokens_destino)
    b64, mime = _img_para_inline(img_file)
    # Teto de runaway: 2.5x o orçamento de palavras (folga p/ JSON + folga de
    # fidelidade). NÃO é um teto de qualidade — a qualidade vem da hierarquia.
    max_out = int(sum(tetos.values()) * 2.5)
    corpo = {
        "system_instruction": {"parts": [{"text": _montar_prompt_visao(estilo_conversao, sens_escolhida, tetos)}]},
        "contents": [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": mime, "data": b64}},
                {"text": "Descreva esta imagem com fidelidade absoluta: sujeito, ação, "
                        "cenário, iluminação (fonte/direção/dureza) e óptica/câmera "
                        "(mm, f/, DoF, bokeh, enquadramento). Não resuma."},
            ],
        }],
        "generationConfig": {
            "temperature": 0.15,  # factual: o mínimo de invenção
            "maxOutputTokens": max_out,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA_VISAO,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_gemini}:generateContent"
    req = urllib.request.Request(
        url, data=_json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        corpo_err = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError(f"Visão · HTTP {e.code}: {corpo_err}") from e
    except Exception as e:
        raise RuntimeError(f"Visão · {e}") from e

    try:
        texto = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        finish = (payload.get("candidates") or [{}])[0].get("finishReason", "?")
        raise RuntimeError(f"Visão · resposta sem texto (finishReason={finish}).") from e

    try:
        dados = _json.loads(texto)
    except _json.JSONDecodeError:
        return {"tipo": "texto", "texto": texto}

    # NÃO cortamos aqui. A visão é a única etapa que enxerga a imagem: cortar
    # agora é o que produzia a perda de fidelidade. O adensamento com
    # hierarquia (sujeito > ação > cenário > luz > câmera) acontece no
    # consumidor, em _orcamento_estruturado, e só quando o destino realmente
    # não comportar o material.
    return {"tipo": "json", "dados": dados}


def _cortar_palavras(txt: str, max_palavras: int) -> str:
    """Corta por contagem de palavras em fronteira de frase. Rede de segurança
    para o modelo; em operação normal a visão já respeita o teto."""
    partes = re.split(r"(?<=[.;:])\s+", txt)
    saida, total = [], 0
    for fr in partes:
        n = len(fr.split())
        if total + n > max_palavras:
            break
        saida.append(fr)
        total += n
    if not saida:
        # Sem fronteira de frase: corta por palavras brutas, nunca no meio
        palavras = txt.split()
        if len(palavras) <= max_palavras:
            return txt
        return " ".join(palavras[:max_palavras]).rstrip(",;:.!?")
    return " ".join(saida)


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
# (como era) obrigava a visão a extrair no escuro, a rascunhar a cena sem
# saber o formato-alvo, e só então descobrir que o material não cabia — com
# a extração e o rascunho já pagos em tokens.
#
# Escolhendo aqui, na PRIMEIRA etapa, tudo abaixo já trabalha ciente do alvo:
#   - a visão extrai com o teto DERIVADO deste destino;
#   - o rascunho é escrito no formato que o destino espera;
#   - a síntese final não precisa reprocessar nada.
st.markdown("### 0️⃣ Passo 0: Motor Destino (Obrigatório)")
st.caption("Defina primeiro para qual plataforma o prompt será compilado. Tudo o que vem "
            "depois — inclusive a extração da imagem — respeita o formato e o limite de "
            "tokens deste motor. Escolher por último desperdiça trabalho.")
dest_sel = st.selectbox(
    "Plataforma de Imagem Alvo:",
    OPCOES_DESTINO,
    key="ck_destino_select",
    label_visibility="collapsed",
)
_perfil_destino = _perfil_do_destino(dest_sel) if dest_sel != OPCOES_DESTINO[0] else {}
if _perfil_destino:
    st.caption(f"🎯 **{dest_sel}** · formato **{_perfil_destino.get('structure','')}** · "
               f"teto **{_perfil_destino.get('max_tokens',0)} tokens** para prompt + negative "
               f"+ legenda + hashtags.")
else:
    st.info("🛑 Escolha o motor de destino para liberar a extração de imagem, o rascunho e a "
            "geração do prompt. Sem ele não há formato nem orçamento definidos.")

# A visão só roda com destino escolhido — ela deriva o orçamento dele.
_destino_escolhido = bool(_perfil_destino)

# TROCAR DE DESTINO INVALIDA O TRABALHO JÁ FEITO. A extração foi calibrada
# para o teto/formato do destino anterior; mantê-la produz uma narrativa fora do
# formato-alvo e obriga a síntese final a reprocessar do zero (o desperdício que
# esta mudança de sequência existe para eliminar).
_destino_anterior = st.session_state.get("ck_destino_aplicado")
if _destino_escolhido and _destino_anterior and _destino_anterior != dest_sel:
    for _k in ["ck_img_parametros", "ck_preprompt", "ck_preprompt_editado",
               "ck_diagnostico", "ck_prompt_final", "ck_sugestoes_marcadas",
               "img_suj", "img_cen", "img_act", "img_ilu", "img_est"]:
        st.session_state.pop(_k, None)
    for _k in ["_pending_img_suj", "_pending_img_cen", "_pending_img_act",
               "_pending_img_ilu", "_pending_img_est", "_pending_ck_preprompt_editado"]:
        st.session_state.pop(_k, None)
    st.info(f"🔄 Destino alterado para **{dest_sel}**. Extração e rascunho anterior "
            "foram descartados — refaça a extração da imagem ciente do novo formato.")
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
    btn_ler = st.button(
        "👁️ Extrair Imagem (Motor de Visão)",
        use_container_width=True,
        disabled=not _destino_escolhido,
    )
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
                # _cfg vive no escopo do sidebar; recarrega a config do usuário.
                _cfg_visao = carregar_config(st.session_state["user_email"])
                chave_visao = _cfg_visao.get("chaves", {}).get("Chave Visao", "")
                res = _chamar_motor_visao(
                    img_file, estilo_conversao, sens_escolhida,
                    modelo_base, chave_visao,
                    _teto_destino(dest_sel),  # orçamento derivado do destino
                )
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
    with col_m3: sens_escolhida = st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider", value=st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1]))

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
                _perfil = _perfil_do_destino(dest_sel)
                _fmt_dest = _perfil.get("structure", "")
                _dica_dest = _perfil.get("dica_tecnica", "")
                p = f"IDEIA:\n{st.session_state.ck_ideia_input}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sens_escolhida}']"
                p += (f"\n[DESTINO ALVO: {dest_sel}]"
                      f"\n[FORMATO EXIGIDO: {_fmt_dest}]"
                      f"\n[ORIENTAÇÃO TÉCNICA DO DESTINO: {_dica_dest}]"
                      "\n[RASCUNHO = FONTE DA SÍNTESE FINAL]: escreva a cena já descrita em "
                      "termos que o destino consome (nominal técnico, sem adjetivo genérico). "
                      "Não escreva meta-comentário sobre o formato.")
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
# PASSO 5: Motor Destino & Síntese Final
# --------------------------------------------------------------------------
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

                # --- DEFINIÇÕES OBRIGATÓRIAS (evita NameError) ---
                _dica = eng.get("dica_tecnica", "")
                _dica_txt = f"\n💡 DICA TÉCNICA: {_dica}" if _dica else ""
                bloco = f"\n\n======================================\n3. SINTAXE NATIVA: {dest_sel}\n======================================\n- POSITIVO: {eng['regra_positivo']}\n- NEGATIVO: {eng.get('regra_negativo', 'N/A')}{_dica_txt}\n\nSAÍDA OBRIGATÓRIA:\n1. PROMPT (ENGLISH)\n2. NEGATIVE PROMPT DINÂMICO (ENGLISH)\n3. LEGENDA\n4. HASHTAGS"

                # --- LÓGICA DE PROMPT E ESTRUTURA ---
                txt_b = st.session_state.ck_preprompt_editado if st.session_state.get("ck_preprompt") else st.session_state.ck_ideia_input
                sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])
                sug_str = "\n".join(f"- {s}" for s in sug_aceitas) if sug_aceitas else "Nenhuma sugestão."

                dest_lower = dest_sel.lower()
                max_tokens = _teto_destino(dest_sel)

                # Orçamento real. Dois caminhos, ambos com o MESMO teto:
                #  A) estruturado — a extração de visão devolveu JSON; usa
                #     orçamento POR CAMPO, que preserva sujeito/ação e os termos
                #     técnicos de câmera em vez de cortar o fim do texto.
                #  B) prosa — ideia digitada ou visão em texto; usa o orçamento
                #     por frase. Nunca corta no meio da oração (o txt_b[:N]
                #     original destruía a composição e perdia luz/estilo).
                _campos_vis, _avisos, _meta = (None, [], {})
                _img_params = st.session_state.get("ck_img_parametros")
                if _img_params and isinstance(_img_params, dict) and len(_img_params) >= 2:
                    _campos_vis, _avisos, _meta = _orcamento_estruturado(_img_params, max_tokens)
                if _campos_vis:
                    txt_b = _formatar_campos(_campos_vis)
                    _est_fonte = _meta.get("total", _estimar_tokens(txt_b))
                else:
                    txt_b, _est_fonte, _avisos = _orcamento_texto_fonte(txt_b, max_tokens)
                for _av in _avisos:
                    st.warning(_av)

                # P-Base (Narrativa + Sugestões)
                p = f"DESTINO: {dest_sel}\nRATING: {sens_escolhida}\n\n1. NARRATIVA VISUAL (FONTE DA TRADUÇÃO):\n{txt_b}\n\n2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}"

                # Injeção estrutural (sem duplicação)
                if "flux" in dest_lower:
                    p += "\n\n[FLUX STRUCTURE: subject | context | lighting | style]"
                elif "ideogram" in dest_lower:
                    p += "\n\n[IDEOGRAM STRUCTURE: concept | elements | colors | composition]"
                elif "midjourney" in dest_lower:
                    p += "\n\n[MJ STRUCTURE: subject + --v 6.1 --style raw --ar 16:9]"
                elif any(m in dest_lower for m in ["pony", "sdxl", "comfyui", "illustrious"]):
                    p += "\n\n[SDXL/PONY STRUCTURE: positive-tags, negative-tags]"
                elif "krea" in dest_lower:
                    p += "\n\n[KREA STRUCTURE: instructions | subject | style-params]"

                # Re-adiciona estilo e regras (BLOCO ÚNICO — antes STYLE OVERRIDE,
                # MODO LITERAL e REGRAS FINAIS eram injetados 2×, gastando o
                # orçamento antes de o modelo escrever uma palavra).
                _estilo_final = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                _literal = "Literal" in st.session_state.get("ck_foco_contexto", "")
                if "Fotorrealismo" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO PHOTOREALISM]: Rewrite entire scene as photorealistic photo, real skin, photographic texture, photorealistic. PROHIBIT anime/cartoon/illustration/drawing/cel shading terms."
                elif "Anime" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO ANIME 2D]: Rewrite entire scene as 2D anime illustration, clean anime linework, cel shading, anime style. Replace photo/smartphone/26mm/photorealistic with anime illustration terms. PROHIBIT photo/smartphone lens/photorealistic terms."
                if _literal:
                    p += "\n[MODO LITERAL]: Remova floreios poéticos/metafóricos, MAS MANTENHA todas as características do sujeito e os detalhes principais da composição. LITERAL NÃO É RESUMO E NÃO É OMISSÃO."
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
