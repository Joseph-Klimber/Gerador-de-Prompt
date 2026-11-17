# src/vision.py
"""Motor de Visão — Extração estruturada de imagens via Gemini Vision.
Refatorado para usar google.genai client (consistente com text_engines.py)."""
import base64
import json
import re
import time
import random
import streamlit as st

try:
    from google import genai
    from google.genai import types
    from google.genai import errors as genai_errors
except ImportError:
    genai = None
    types = None
    genai_errors = None

from config import (
    PESO_CAMPO,
    VISAO_FATOR_FIDELIDADE, VISAO_MIN_PALAVRAS, VISAO_MAX_PALAVRAS,
    VISAO_MIN_POR_CAMPO, SYS_VISAO_EXTRACAO, DIR_VISAO,
    OPCOES_GEMINI_3, MODELO_VISAO_PADRAO,
)
from core.contracts import EstiloConversao


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


def _eh_erro_transitorio_visao(e) -> bool:
    """Verifica se erro de visão é transitório (retry automático) usando exceções tipadas."""
    if genai_errors is not None:
        if isinstance(e, genai_errors.ServerError):
            return True
        if isinstance(e, genai_errors.ClientError):
            code = getattr(e, "code", None)
            if code == 429:
                return True
            if code in (400, 401, 403, 404):
                return False
            return False
    
    # Fallback: string matching legado
    s = str(e).lower()
    if any(k in s for k in ("invalid argument", "validation", "not supported", "unsupported", "unknown field")):
        return False
    if any(k in s for k in ("503", "429", "500", "502", "504", "overloaded", "unavailable", "resource exhausted", "internal error", "deadline exceeded", "timed out", "timeout", "read operation timed out", "connection reset", "connection refused", "remote end closed")):
        if any(p in s for p in ("temperature", "top_p", "top_k", "candidate_count", "thinking")):
            if "temperature" in s or "not supported" in s or "unsupported" in s:
                return False
        return True
    try:
        code = getattr(e, "code", None) or getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
        if code in (429, 500, 502, 503, 504):
            if any(p in s for p in ("temperature", "candidate_count")) and "not supported" in s:
                return False
            return True
    except Exception:
        pass
    return False


def _extrair_retry_after_segundos(erro_str: str):
    """Extrai Retry-After do erro (header ou corpo)."""
    try:
        m = re.search(r"retry[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*s", erro_str, re.IGNORECASE)
        if m: return min(float(m.group(1)), 30.0)
        m2 = re.search(r"Retry-After:\s*([0-9]+)", erro_str, re.IGNORECASE)
        if m2: return min(float(m2.group(1)), 30.0)
    except Exception:
        pass
    return None


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
    if estilo == EstiloConversao.FOTORREALISMO.value:
        p += "\n\n[DIRETRIZ DE LEITURA — FOTORREALISMO] " + DIR_VISAO["Fotorrealismo"]
    elif estilo == EstiloConversao.ANIME.value:
        p += "\n\n[DIRETRIZ DE LEITURA — ANIME 2D] " + DIR_VISAO["Anime"]
    if EstiloConversao.ANTI_PORCELANA_MARKER in (estilo or ""):
        p += ("\n\n[DIRETRIZ DE LEITURA — FOTOGRÁFICO REALISTA / ANTI-PORCELANA] "
              + DIR_VISAO["Anti-Porcelana"])
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
                       modelo_gemini: str, max_tokens_destino: int) -> dict:
    """Motor de visão. É origem de dados do prompt final."""
    from src.config_store import carregar_config
    from core.state import StateKeys
    email = st.session_state.get(StateKeys.USER_EMAIL, "")
    config = carregar_config(email)
    
    chaves_dict = config.get("chaves", {})
    api_key = (
        st.session_state.get("input_key_visao", "").strip()
        or chaves_dict.get("Chave Visao", "").strip()
        or chaves_dict.get("Chave Visão", "").strip()
        or st.session_state.get("input_key_texto", "").strip()
        or chaves_dict.get("Chave Texto", "").strip()
        or chaves_dict.get("Chave Texto (BYOK)", "").strip()
    )
    if not api_key:
        raise RuntimeError("Nenhuma chave configurada para Visão ou Texto. Conecte sua chave na barra lateral.")

    tetos = _teto_visao_palavras(max_tokens_destino)
    b64, mime = _img_para_inline(img_file)
    max_out = int(sum(tetos.values()) * 2.5)
    prompt_sistema = _montar_prompt_visao(estilo_conversao, sens_escolhida, tetos)

    modelo_principal = (modelo_gemini or "").strip()
    if not modelo_principal or modelo_principal not in OPCOES_GEMINI_3:
        modelo_principal = MODELO_VISAO_PADRAO

    candidatos = [modelo_principal] + [m for m in OPCOES_GEMINI_3 if m != modelo_principal]
    ultimo_erro = None

    # Se a lib oficial genai estiver disponível e configurada, usa ela; senão usa urllib (REST)
    if genai is not None:
        try:
            client = genai.Client(api_key=api_key)
            for modelo_try in candidatos:
                try:
                    response = client.models.generate_content(
                        model=modelo_try,
                        contents=[
                            types.Part.from_bytes(data=b64, mime_type=mime),
                            "Descreva esta imagem com fidelidade absoluta: sujeito, ação, "
                            "cenário, iluminação (fonte/direção/dureza) e óptica/câmera "
                            "(mm, f/, DoF, bokeh, enquadramento). Não resuma. Responda APENAS com JSON válido."
                        ],
                        config={
                            "system_instruction": prompt_sistema,
                            "temperature": 0.25,
                            "max_output_tokens": max_out,
                            "response_mime_type": "application/json",
                        },
                    )
                    texto = response.text or ""
                    from src.text_engines import parse_json_ia
                    dados = parse_json_ia(texto)
                    if not dados:
                        return {"tipo": "texto", "texto": texto}
                    dados = _validar_consistencia_lateralidade(dados)
                    return {"tipo": "json", "dados": dados}
                except Exception as e:
                    ultimo_erro = e
                    if not _eh_erro_transitorio_visao(e) and modelo_try == candidatos[-1]:
                        break
                    continue
        except Exception as e:
            ultimo_erro = e

    # Fallback / Execução via REST (urllib) — Altamente resiliente a erros de SDK
    corpo_base = {
        "system_instruction": {"parts": [{"text": prompt_sistema}]},
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
            "temperature": 0.25,
            "maxOutputTokens": max_out,
            "responseMimeType": "application/json",
        },
    }

    for modelo_try in candidatos:
        corpo = dict(corpo_base)
        try:
            payload = _gerar_com_retry_visao(corpo, modelo_try, api_key)
            texto = payload["candidates"][0]["content"]["parts"][0]["text"]
            from src.text_engines import parse_json_ia
            dados = parse_json_ia(texto)
            if not dados:
                return {"tipo": "texto", "texto": texto}
            dados = _validar_consistencia_lateralidade(dados)
            return {"tipo": "json", "dados": dados}
        except Exception as e:
            ultimo_erro = e
            if not _eh_erro_transitorio_visao(e) and modelo_try == candidatos[-1]:
                break
            continue

    raise RuntimeError(f"Falha na Visão (Gemini) após fallback {candidatos}: {ultimo_erro}")