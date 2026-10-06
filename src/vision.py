"""vision.py — Etapa 3 stub / Etapa 4 full (extração óptica)
Reaproveitado do legado 1.0-3.py — PS_LEITOR_PARAMETRICO copiado via text_engines.
Proporção canônica no topo da faixa de tiles (LANCZOS), validação 10MB.

FIDELIDADE > COMPACTAÇÃO. A visão é a ÚNICA etapa que enxerga a imagem: o que
ela omite se perde para sempre, porque nenhuma etapa posterior consegue
reconstruir o que não foi descrito. Por isso o orçamento aqui é GENEROSO e
DERIVADO do destino escolhido no Passo 0, e o adensamento com hierarquia
(sujeito > ação > cenário > luz > câmera) fica no consumidor (app.py).
"""
from PIL import Image, ImageOps
import streamlit as st
try:
    from google import genai
except ImportError:
    genai = None

from src.text_engines import SYS_LEITOR_PARAMETRICO, MODELO_VISAO_PADRAO, OPCOES_GEMINI_3, _build_gemini_config, _gerar_com_retry, parse_json_ia

# Multiplicador de fidelidade: a visão escreve ~2.2 palavras por token do teto do
# destino, com piso e teto absolutos. Generoso de propósito — sobrar é
# recuperável (o consumidor adensa com hierarquia), faltar é fatal.
VISAO_FATOR_FIDELIDADE = 2.2
VISAO_MIN_PALAVRAS = 700
VISAO_MAX_PALAVRAS = 2000

# ── LIMIAR DE FIDELIDADE DA EXTRAÇÃO ────────────────────────────────────────
# O teto do destino é o orçamento FINAL (prompt + negative + legenda +
# hashtags). Com um teto menor que ~600 tokens, o consumidor não tem folga
# para adensar a extração por campo — a visão teria de resumir na origem,
# perdendo sujeito/luz/óptica em definitivo. Abaixo disso o app BLOQUEIA a
# extração (destinos como Z-Image Turbo 400 e Midjourney/Ideogram 500): modo
# de visão só fica disponível para os destinos com teto suficiente para uma
# boa coerência. Ajuste fino: 600 é a fronteira entre os 400/500 (bloqueados)
# e os 600/700/800/900/1000 (liberados).
VISAO_TETO_MINIMO_DESTINO = 600

# ──────────────────────────────────────────────────────────────────────────
# PROPORÇÕES CANÔNICAS DE MERCADO — de aqui derivam todas as outras.
# Cada razão-fixa tem um tamanho canônico EXATO: pares inteiros da própria
# razão posicionados no TOPO da faixa de tiles do Gemini (faixa = 768 px;
# 1 tile de 768×768 = 256 tokens; resto fracionário paga o tile inteiro).
# Assim o custo da imagem vira conta fechada e previsível:
#   10 formatos = 4 tiles = 1024 tokens no máximo · 21:9 = 2 tiles = 512.
# Imagem com proporção "quebrada" (desvio ≤ 3%) assume a canônica mais
# próxima por recorte central — recorte nunca distorce. Mais fora que isso,
# a própria razão fica intata e só se reduz o necessário para caber.
# Nada aqui amplia: o alvo só é aplicado quando a imagem é maior que ele.
# ──────────────────────────────────────────────────────────────────────────
PROPORCOES_CANONICAS = (
    ("1:1",    1,  1, 1536, 1536),
    ("4:5",    4,  5, 1228, 1535),
    ("3:4",    3,  4, 1152, 1536),
    ("2:3",    2,  3, 1024, 1536),
    ("9:16",   9, 16,  864, 1536),
    ("4:3",    4,  3, 1536, 1152),
    ("3:2",    3,  2, 1536, 1024),
    ("16:9",  16,  9, 1536,  864),
    ("16:10", 16, 10, 1536,  960),
    ("5:4",    5,  4, 1280, 1024),
    ("21:9",   7,  3, 1533,  657),
)
TOLERANCIA_RECORTE = 0.03   # desvio até o qual se assume a canonica mais proxima
TOLERANCIA_FAIXA = 0.02    # quanto acima de um limite de faixa ainda se desce
LADO_FAIXA = 768            # faixa de tile do Gemini
TETO_TILES = 4              # orcamento em forca: 4 tiles = 1024 tokens
TETO_LADO = 1536            # 2 faixas — teto do lado maior em qualquer caso
_LANCZOS = Image.Resampling.LANCZOS


def _n_tiles(w, h):
    """Tiles do Gemini para uma imagem de w×h (ceil por eixo, 768 px cada)."""
    return (-(-w // LADO_FAIXA)) * (-(-h // LADO_FAIXA))


def _canonica_mais_proxima(w, h):
    """(nome, desvio_relativo, largura_alvo, altura_alvo, razao_canonica)."""
    r = w / h
    melhor = ("", float("inf"), 1, 1, 1.0)
    for nome, a, b, tw, th in PROPORCOES_CANONICAS:
        rc = a / b
        dev = abs(r - rc) / rc
        if dev < melhor[1]:
            melhor = (nome, dev, tw, th, rc)
    return melhor


def _escala_de_borda(w, h):
    """Escala proporcional que desce todas as dimensoes que estao ate
    TOLERANCIA_FAIXA acima de um limite de faixa (768·n) ate o proprio
    limite. 769 px custa o mesmo que 1536 px (4 tiles): o resto fracionario
    e de graça de se tirar. None quando nao ha degrau a saltar."""
    melhor, achou = 1.0, False
    for d in (w, h):
        n = d // LADO_FAIXA
        limite = n * LADO_FAIXA
        if 0 < limite < d <= limite * (1 + TOLERANCIA_FAIXA):
            melhor = min(melhor, limite / d)
            achou = True
    return melhor if achou else None


def normalizar_imagem(img):
    """Aplica a proporção canônica mais próxima da imagem e a reduz ao
    tamanho canônico do topo de faixa. Só reduz (nunca amplia); recorta no
    máximo TOLERANCIA_RECORTE de um dos lados (recorte nunca distorce);
    proporção fora do padrão de mercado mantém a própria razão. Devolve
    (imagem, info) com tiles, tokens e o que foi feito."""
    w0, h0 = img.size
    w, h = w0, h0
    if w <= 0 or h <= 0:
        return img, {}
    nome, dev, tw, th, rc = _canonica_mais_proxima(w, h)
    recorte_pct = 0.0
    if dev <= TOLERANCIA_RECORTE:
        # 1) razão canônica por recorte central — erra no maximo o desvio medido
        r = w / h
        if r > rc:
            nw = max(1, min(w, int(round(h * rc))))
            if nw < w:
                x0 = (w - nw) // 2
                img = img.crop((x0, 0, x0 + nw, h))
                recorte_pct = (w - nw) * 100.0 / w
        elif r < rc:
            nh = max(1, min(h, int(round(w / rc))))
            if nh < h:
                y0 = (h - nh) // 2
                img = img.crop((0, y0, w, y0 + nh))
                recorte_pct = (h - nh) * 100.0 / h
        w, h = img.size
        # 2) tamanho canônico (topo da faixa 2×2) — aplicado só quando reduz
        s = min(tw / w, th / h)
        if s < 1.0:
            img = img.resize((max(1, int(w * s)), max(1, int(h * s))), _LANCZOS)
            w, h = img.size
            # ±1 px do arredondamento: normaliza para o par canônico exato
            if abs(w - tw) <= 1 and abs(h - th) <= 1 and (w, h) != (tw, th):
                img = img.resize((tw, th), _LANCZOS)
                w, h = img.size
        metodo = "canonica"
    else:
        # 3) fora do padrão: a propria razao fica intata; reduz so o suficiente
        if max(w, h) > TETO_LADO:
            s = TETO_LADO / max(w, h)
            img = img.resize((max(1, int(w * s)), max(1, int(h * s))), _LANCZOS)
            w, h = img.size
        metodo = "razao_preservada"
    # 4) degrau de faixa: desce o resto fracionario (custo de fração de %)
    s_borda = _escala_de_borda(w, h)
    if s_borda is not None and s_borda >= 1 - TOLERANCIA_FAIXA:
        img = img.resize((max(1, int(w * s_borda)), max(1, int(h * s_borda))), _LANCZOS)
        w, h = img.size
    tiles = _n_tiles(w, h)
    info = {
        "antes": f"{w0}×{h0}",
        "depois": f"{w}×{h}",
        "proporcao": nome,
        "razao_original": round(w0 / h0, 3),
        "desvio": round(dev * 100, 2),
        "recorte_pct": round(recorte_pct, 2),
        "metodo": metodo,
        "tiles": tiles,
        "tokens_aprox": tiles * 256,
    }
    return img, info


def _teto_visao_palavras(max_tokens_destino):
    """ Orçamento da visão derivado do teto do destino. É referência SOFT: a
    instrução pede fidelidade; nenhum corte rígido é aplicado aqui.

    LIMIAR DE FIDELIDADE: a extração precisa produzir texto suficiente para o
    consumidor adensar por campo — e o total do teto do destino é o que o
    consumidor tem para gastar. Se o teto do destino é MUITO baixo, a visão
    teria de resumir demais na origem (perdendo sujeito/luz/óptica em
    definitivo) — por isso o app bloqueia a extração para destinos abaixo do
    limiar. (Ver VISAO_TETO_MINIMO_DESTINO.) Este teto de palavras é usado só
    quando a extração está liberada.
    """
    total = int(min(max(int(max_tokens_destino) * VISAO_FATOR_FIDELIDADE,
                         VISAO_MIN_PALAVRAS), VISAO_MAX_PALAVRAS))
    # Mesma hierarquia do consumidor: sujeito > ação > cenário > luz > câmera
    pesos = {"sujeito": 34, "acao": 26, "cenario": 16,
             "iluminacao": 12, "estilo_camera": 12}
    soma = sum(pesos.values())
    return {k: max(int(total * p / soma), 120) for k, p in pesos.items()}


def destino_suporta_visao(max_tokens_destino: int) -> bool:
    """Se o destino tem teto de tokens suficiente para uma extração fiel.

    O teto do destino é o orçamento FINAL (prompt + negative + legenda +
    hashtags). Abaixo do limiar, a visão teria de resumir na origem e o
    consumidor não teria texto para adensar — o sujeito/luz/óptica se perdem
    em definitivo. Bloquear a extração é a única forma de não degradar.
    """
    if not max_tokens_destino:
        return False
    return max_tokens_destino >= VISAO_TETO_MINIMO_DESTINO


def _chamar_motor_visao(arquivo_imagem, estilo_conversao, nivel_sensualidade,
                       modelo_gemini=None, max_tokens_destino=800):
    MAX_IMAGE_SIZE_MB = 10
    if arquivo_imagem.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise RuntimeError(f"🖼️ Imagem limite: {MAX_IMAGE_SIZE_MB} MB.")
    from src.config_store import carregar_config
    config = carregar_config(st.session_state.get("user_email", ""))
    chave_visao = st.session_state.get("input_key_visao", "").strip() or config.get("chaves", {}).get("Chave Visao", "")
    if not chave_visao or genai is None:
        raise RuntimeError("Nenhuma chave configurada para Visão. Adicione a 'Chave Gemini (Visão)' no painel lateral.")
    modelo_primeiro_gemini = (modelo_gemini or "").strip() if modelo_gemini else ""
    if not modelo_primeiro_gemini:
        modelo_primeiro_gemini = (st.session_state.get("modelo_visao_select") or "").strip()
    if not modelo_primeiro_gemini:
        modelo_primeiro_gemini = config.get("modelo_visao", MODELO_VISAO_PADRAO)
    if modelo_primeiro_gemini not in OPCOES_GEMINI_3:
        modelo_primeiro_gemini = MODELO_VISAO_PADRAO
    user_prompt = f"Desconstrua pericialmente esta imagem em Ultra-Densidade. \n[MODIFICADOR 2: SENSUALIDADE]: Nível {nivel_sensualidade}."
    if "Fotorrealismo" in estilo_conversao:
        user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza para o MUNDO REAL fotorrealista."
    elif "Anime" in estilo_conversao:
        user_prompt += "\n[MODIFICADOR 1: ESTILO]: Traduza para ILUSTRAÇÃO 2D ANIME."

    # Orçamento DERIVADO do destino escolhido no Passo 0. Referência SOFT de
    # densidade — os números são injetados na instrução, nunca aplicados como
    # corte. A extração é a única etapa que enxerga a imagem: resumir aqui
    # destrói o detalhe em definitivo, enquanto sobrar detalhe é recuperado
    # adiante pela hierarquia do consumidor.
    tetos = _teto_visao_palavras(max_tokens_destino)
    user_prompt += (
        "\n\n[ORÇAMENTO DE EXTRAÇÃO — REFERÊNCIA SOFT (palavras por campo)]:"
        f"\n- sujeito: ~{tetos['sujeito']}"
        f"\n- ação: ~{tetos['acao']}"
        f"\n- cenário: ~{tetos['cenario']}"
        f"\n- iluminação: ~{tetos['iluminacao']}"
        f"\n- estilo e câmera: ~{tetos['estilo_camera']}"
        "\nEstes números são REFERÊNCIA de densidade, não um limite de asfixia."
        "\nPRIORIDADE DE FIDELIDADE: preserve integralmente identidade do sujeito, "
        "direção e dureza da luz, e dados ópticos (mm, f/, DoF, bokeh, enquadramento). "
        "Ceda apenas detalhe atmosférico decorativo, repetição redundante e preenchimento "
        "genérico. É PREJUDICADO omitir detalhe visível: o que não for descrito aqui não "
        "poderá ser recuperado em nenhuma etapa posterior."
    )
    norm = {}
    try:
        arquivo_imagem.seek(0)
        img_pil = Image.open(arquivo_imagem)
        try:
            img_pil = ImageOps.exif_transpose(img_pil) or img_pil
            img_pil.load()
            # Proporção canônica + topo de faixa de tiles: o custo da imagem
            # fica previsível (≤4 tiles ≈ 1024 tokens) e a razão do mercado
            # mais próxima vira a razão enviada — sem ampliar, sem distorcer.
            img_pil, norm = normalizar_imagem(img_pil)
            if img_pil.mode not in ("RGB", "RGBA"):
                img_pil = img_pil.convert("RGB")
        except Exception:
            pass
        candidatos = [modelo_primeiro_gemini] + [m for m in OPCOES_GEMINI_3 if m != modelo_primeiro_gemini]
        ultimo_erro = None
        for modelo_try in candidatos:
            for modo_temp in (0.2, None):
                try:
                    client = genai.Client(api_key=chave_visao)
                    cfg = _build_gemini_config(SYS_LEITOR_PARAMETRICO, modelo_try, temperature=modo_temp)
                    resp = _gerar_com_retry(client, modelo_try, [img_pil, user_prompt], cfg)
                    texto = getattr(resp, "text", "") or ""
                    if not texto.strip():
                        raise RuntimeError("A IA bloqueou a imagem por políticas de segurança.")
                    dados = parse_json_ia(texto)
                    if dados:
                        return {"tipo": "json", "dados": dados, "norm": norm}
                    return {"tipo": "texto", "texto": texto, "norm": norm}
                except Exception as e:
                    ultimo_erro = e
                    s = str(e).lower()
                    eh_validation = any(k in s for k in ("invalid argument", "validation", "not supported", "unsupported"))
                    eh_transitorio = "503" in s or "overloaded" in s or "unavailable" in s or "429" in s or "resource exhausted" in s
                    if eh_validation and modo_temp is not None:
                        continue
                    if eh_transitorio:
                        if modo_temp is not None:
                            continue
                        break
                    if modo_temp is not None:
                        continue
                    break
            if ultimo_erro is not None and any(k in str(ultimo_erro).lower() for k in ("503", "overloaded", "unavailable", "429", "resource exhausted")):
                if modelo_try == candidatos[-1]:
                    break
                continue
            break
        raise RuntimeError(f"Falha no Primeiro Gemini (Leitura Óptica) após fallback {candidatos}: {str(ultimo_erro)}")
    except Exception as e:
        if "apos fallback" in str(e):
            raise
        raise RuntimeError(f"Falha no Primeiro Gemini (Leitura Óptica): {str(e)}")
