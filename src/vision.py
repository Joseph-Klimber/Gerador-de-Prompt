# src/vision.py
"""Motor de Visão — Extração estruturada de imagens via Gemini Vision."""
import base64
import json
import urllib.request
import urllib.error
import re
import streamlit as st

from src.config.settings import (
    OPCOES_SENSUALIDADE, PESO_CAMPO, PISO_CAMPO,
    VISAO_FATOR_FIDELIDADE, VISAO_MIN_PALAVRAS, VISAO_MAX_PALAVRAS,
    VISAO_MIN_POR_CAMPO, SCHEMA_VISAO, SYS_VISAO_EXTRACAO, _DIR_VISAO,
)
from src.core.token_budget import estimar_tokens


def _validar_consistencia_lateralidade(dados: dict) -> dict:
    """
    Validação leve de consistência interna (defesa em profundidade).
    Loga warning se detectar contradição lateral na própria extração.
    NÃO altera os dados — o prompt fixo deve resolver na origem.
    """
    if not dados or not isinstance(dados, dict):
        return dados
    
    try:
        import logging
        logger = logging.getLogger(__name__)
    except Exception:
        return dados
    
    texto_completo = " ".join(str(v) for v in dados.values() if isinstance(v, str)).lower()
    
    # Padrões de contradição: mesmo membro descrito dos dois lados
    contradicoes = [
        (r"braço no lado esquerdo", r"mão direita"),
        (r"braço no lado direito", r"mão esquerda"),
        (r"perna no lado esquerdo", r"pé direito"),
        (r"perna no lado direito", r"pé esquerdo"),
        (r"lado esquerdo da imagem.*braço direito", ""),
        (r"lado direito da imagem.*braço esquerdo", ""),
    ]
    
    for padrao1, padrao2 in contradicoes:
        if padrao2 and re.search(padrao1, texto_completo) and re.search(padrao2, texto_completo):
            logger.warning(f"[Vision] Possível inconsistência lateral: {padrao1} + {padrao2}")
        elif padrao2 == "" and re.search(padrao1, texto_completo):
            logger.warning(f"[Vision] Lateralidade explícita mista: {padrao1}")
    
    return dados


def _teto_visao_palavras(max_tokens_destino: int) -> dict:
    """Orçamento da visão DERIVADO do teto do destino escolhido no Passo 0."""
    total = int(min(max(int(max_tokens_destino) * VISAO_FATOR_FIDELIDADE,
                         VISAO_MIN_PALAVRAS), VISAO_MAX_PALAVRAS))
    soma = sum(PESO_CAMPO.values()) or 1
    return {k: max(int(total * PESO_CAMPO.get(k, 10) / soma), VISAO_MIN_POR_CAMPO)
            for k in PESO_CAMPO}


def _montar_prompt_visao(estilo: str, sens: str, tetos: dict) -> str:
    """Monta o prompt da visão com tetos por campo."""
    p = SYS_VISAO_EXTRACAO.format(**tetos)
    if "Fotorrealismo" in (estilo or ""):
        p += "\n\n[DIRETRIZ DE LEITURA — FOTORREALISMO] " + _DIR_VISAO["Fotorrealismo"]
    elif "Anime" in (estilo or ""):
        p += "\n\n[DIRETRIZ DE LEITURA — ANIME 2D] " + _DIR_VISAO["Anime"]
    if sens:
        p += f"\n\n[NÍVEL DE SENSUALIDADE: {sens}] Avalie o modelo sem omitir nem exagerar atributos."
    p += "\n\nDescreva a imagem nos 5 campos do schema. Responda APENAS com o JSON."
    return p


def _img_para_inline(img_file) -> tuple[str, str]:
    """Upload de imagem → (base64, mime). Mantém a imagem só em memória."""
    img_file.seek(0)
    bruto = img_file.read()
    mime = getattr(img_file, "type", None) or "image/jpeg"
    return base64.b64encode(bruto).decode(), mime


def _chamar_motor_visao(img_file, estilo_conversao: str, sens_escolhida: str,
                       modelo_gemini: str, api_key: str, max_tokens_destino: int) -> dict:
    """Motor de visão. É origem de dados do prompt final.
    
    `max_tokens_destino` é o teto do destino escolhido no Passo 0. A visão é a
    única etapa que enxerga a imagem, então NÃO a estrangulamos: extraímos com
    fidelidade e deixamos o adensamento com hierarquia para o consumidor.
    
    Devolve {"tipo": "json", "dados": {...5 campos...}} ou {"tipo": "texto", ...}.
    """
    if not api_key:
        raise RuntimeError("Chave Visão não configurada — conecte sua chave na barra lateral.")
    
    tetos = _teto_visao_palavras(max_tokens_destino)
    b64, mime = _img_para_inline(img_file)
    
    # Teto de runaway: 2.5x o orçamento de palavras (folga p/ JSON + folha de fidelidade)
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
        url, data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
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
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return {"tipo": "texto", "texto": texto}
    
    # Validação leve de consistência lateral (defesa em profundidade)
    # Loga warning se detectar contradição — o prompt fixo resolve na origem
    dados = _validar_consistencia_lateralidade(dados)
    
    # NÃO cortamos aqui. A visão é a única etapa que enxerga a imagem.
    return {"tipo": "json", "dados": dados}