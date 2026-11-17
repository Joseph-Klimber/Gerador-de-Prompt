# src/vision.py
"""Motor de Visão — Extração estruturada de imagens via Gemini Vision.
Refatorado para usar google.genai client (consistente com text_engines.py)."""
import base64
import json
import urllib.request
import urllib.error
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


def _eh_erro_transitorio_visao(e) -> bool:
    """Verifica se erro de visão é transitório (retry automático)."""
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
    s = str(e).lower()
    if any(k in s for k in ("invalid argument", "validation", "not supported", "unsupported", "unknown field")):
        return False
    if any(k in s for k in ("503", "429", "500", "502", "504", "overloaded", "unavailable", "resource exhausted", "internal error", "deadline exceeded", "timed out", "timeout", "read operation timed out", "connection reset", "connection refused", "remote end closed")):
        return True
    try:
        code = getattr(e, "code", None) or getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
        if code in (429, 500, 502, 503, 504):
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


def _gerar_com_retry_visao(corpo: dict, modelo: str, api_key: str, tentativas=3) -> dict:
    """Chama API de visão via REST com retry exponencial e respeito a Retry-After."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    data = json.dumps(corpo).encode("utf-8")

    for tentativa in range(tentativas):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo_err = e.read().decode("utf-8", "replace")
            if not _eh_erro_transitorio_visao(e) or tentativa == tentativas - 1:
                raise RuntimeError(f"Visão · HTTP {e.code}: {corpo_err[:600]}") from e
            retry_after = _extrair_retry_after_segundos(corpo_err)
            espera = retry_after if retry_after is not None else (2 ** (tentativa + 1)) + random.uniform(0, 0.5)
            time.sleep(min(espera, 30.0))
        except Exception as e:
            s = str(e).lower()
            eh_timeout = any(k in s for k in ("timed out", "timeout", "read operation timed out"))
            if not _eh_erro_transitorio_visao(e) or tentativa == tentativas - 1 or eh_timeout:
                raise RuntimeError(f"Visão · {e}") from e
            retry_after = _extrair_retry_after_segundos(str(e))
            espera = retry_after if retry_after is not None else (2 ** (tentativa + 1)) + random.uniform(0, 0.5)
            time.sleep(min(espera, 30.0))
    raise RuntimeError("Todas as tentativas esgotadas")


def _chamar_motor_visao(img_file, estilo_conversao: str, sens_escolhida: str,
                       modelo_gemini: str, max_tokens_destino: int) -> dict:
    """Motor de visão. É origem de dados do prompt final."""
    from src.config_store import carregar_config, _CONFIG_CACHE
    from core.state import StateKeys
    email = st.session_state.get(StateKeys.USER_EMAIL, "")
    # Bypass cache para garantir leitura fresca das chaves
    _CONFIG_CACHE.pop(email, None)
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
        # Diagnóstico detalhado
        debug_info = {
            "email": email,
            "session_input_visao": bool(st.session_state.get("input_key_visao", "").strip()),
            "session_input_texto": bool(st.session_state.get("input_key_texto", "").strip()),
            "config_chaves_keys": list(chaves_dict.keys()) if chaves_dict else "vazio",
            "config_chave_visao": bool(chaves_dict.get("Chave Visao", "").strip()) if chaves_dict else False,
            "config_chave_visao_acento": bool(chaves_dict.get("Chave Visão", "").strip()) if chaves_dict else False,
            "config_chave_texto": bool(chaves_dict.get("Chave Texto", "").strip()) if chaves_dict else False,
        }
        raise RuntimeError(
            "Nenhuma chave de API encontrada. "
            "Verifique: (1) está logado? (2) salvou as chaves no botão 'Conectar Motores Isolados' na barra lateral? "
            f"Debug: {debug_info}"
        )

    tetos = _teto_visao_palavras(max_tokens_destino)
    b64, mime = _img_para_inline(img_file)
    max_out = int(sum(tetos.values()) * 2.5)
    prompt_sistema = _montar_prompt_visao(estilo_conversao, sens_escolhida, tetos)

    modelo_principal = (modelo_gemini or "").strip()
    if not modelo_principal or modelo_principal not in OPCOES_GEMINI_3:
        modelo_principal = MODELO_VISAO_PADRAO

    candidatos = [modelo_principal] + [m for m in OPCOES_GEMINI_3 if m != modelo_principal]
    ultimo_erro = None

    # Execução via REST (urllib) — timeout explícito, retry exponencial, respeito a Retry-After
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
