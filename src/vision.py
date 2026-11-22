# src/vision.py
"""Motor de Visão — Extração estruturada de imagens via Gemini Vision.
REST-only path (SDK removido — timeout indefinido). Retry exponencial + fallback 3.5→3.6→3.7-flash.
Cascade de API key: input_key_visao → Chave Visao → Chave Visão → input_key_texto → Chave Texto → Chave Texto (BYOK).
"""
import base64
import json
import re
import time
import random
import urllib.request
import urllib.error
import streamlit as st
from datetime import datetime, timezone, timedelta

from config import (
    OPCOES_SENSUALIDADE, PESO_CAMPO, PISO_CAMPO,
    VISAO_FATOR_FIDELIDADE, VISAO_MIN_PALAVRAS, VISAO_MAX_PALAVRAS,
    VISAO_MIN_POR_CAMPO, SCHEMA_VISAO, SYS_VISAO_EXTRACAO, DIR_VISAO,
    OPCOES_GEMINI_3, MODELO_VISAO_PADRAO,
)
from core.token_budget import estimar_tokens

# Brasil timezone (UTC-3) para timestamps user-facing
BR_TZ = timezone(timedelta(hours=-3))


def _now() -> str:
    """Timestamp no fuso do Brasil (HH:MM:SS)."""
    return datetime.now(BR_TZ).strftime("%H:%M:%S")


def _msg(text: str) -> str:
    """Prefixa mensagem com timestamp [HH:MM:SS]."""
    return f"[{_now()}] {text}"


def _validar_consistencia_lateralidade(dados: dict) -> dict:
    """Validação leve de consistência interna (defesa em profundidade).
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
    """Verifica se erro de visão é transitório (retry automático)."""
    s = str(e).lower()
    # Erros de validação/configuração → NÃO transitórios
    if any(k in s for k in ("invalid argument", "validation", "not supported", "unsupported", "unknown field")):
        return False
    # Códigos de erro transitórios conhecidos
    if any(k in s for k in ("503", "429", "500", "502", "504", "overloaded", "unavailable",
                            "resource exhausted", "internal error", "deadline exceeded",
                            "timed out", "timeout", "read operation timed out",
                            "connection reset", "connection refused", "remote end closed")):
        # Mas se for erro de parâmetro não suportado (ex: temperature), não retentar
        if any(p in s for p in ("temperature", "top_p", "top_k", "candidate_count", "thinking")):
            if "temperature" in s or "not supported" in s or "unsupported" in s:
                return False
        return True
    # Tentativa extra via code/status_code attributes
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
        if m:
            return min(float(m.group(1)), 30.0)
        m2 = re.search(r"Retry-After:\s*([0-9]+)", erro_str, re.IGNORECASE)
        if m2:
            return min(float(m2.group(1)), 30.0)
    except Exception:
        pass
    return None


def _gerar_com_retry_visao(corpo: dict, modelo: str, api_key: str, tentativas: int = 3) -> dict:
    """Chama API de visão com retry exponencial e respeito a Retry-After.

    Erros de timeout (read hang) NÃO repetem no mesmo modelo: uma tentativa e
    passa a bola para o fallback de modelos, limitando o pior caso a
    ~timeout x nº de candidatos em vez de timeout x tentativas x candidatos.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    data = json.dumps(corpo).encode("utf-8")

    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            ultimo_erro = e
            corpo_err = e.read().decode("utf-8", "replace")
            if not _eh_erro_transitorio_visao(e) or tentativa == tentativas - 1:
                raise RuntimeError(_msg(f"Visão · HTTP {e.code}: {corpo_err[:600]}")) from e
            retry_after = _extrair_retry_after_segundos(corpo_err)
            espera = retry_after if retry_after is not None else (2 ** (tentativa + 1)) + random.uniform(0, 0.5)
            espera = min(espera, 30.0)
            time.sleep(espera)
        except Exception as e:
            ultimo_erro = e
            s = str(e).lower()
            eh_timeout = any(k in s for k in ("timed out", "timeout", "read operation timed out"))
            if not _eh_erro_transitorio_visao(e) or tentativa == tentativas - 1 or eh_timeout:
                raise RuntimeError(_msg(f"Visão · {e}")) from e
            retry_after = _extrair_retry_after_segundos(str(e))
            espera = retry_after if retry_after is not None else (2 ** (tentativa + 1)) + random.uniform(0, 0.5)
            espera = min(espera, 30.0)
            time.sleep(espera)
    raise ultimo_erro


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
        p += "\n\n[DIRETRIZ DE LEITURA — FOTORREALISMO] " + DIR_VISAO["Fotorrealismo"]
    elif "Anime" in (estilo or ""):
        p += "\n\n[DIRETRIZ DE LEITURA — ANIME 2D] " + DIR_VISAO["Anime"]
    if "Anti-Porcelana" in (estilo or ""):
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


def _resolve_api_key_visao(email: str) -> str | None:
    """Cascade de chaves Visão: session → config (com acento) → texto session → texto config."""
    from src.config_store import carregar_config
    # 1. session input_key_visao
    key = st.session_state.get("input_key_visao", "").strip()
    if key:
        return key
    # 2. config Chave Visao (sem acento)
    config = carregar_config(email)
    key = config.get("chaves", {}).get("Chave Visao", "").strip()
    if key:
        return key
    # 3. config Chave Visão (com acento)
    key = config.get("chaves", {}).get("Chave Visão", "").strip()
    if key:
        return key
    # 4. session input_key_texto
    key = st.session_state.get("input_key_texto", "").strip()
    if key:
        return key
    # 5. config Chave Texto
    key = config.get("chaves", {}).get("Chave Texto", "").strip()
    if key:
        return key
    # 6. config Chave Texto (BYOK)
    key = config.get("chaves", {}).get("Chave Texto (BYOK)", "").strip()
    if key:
        return key
    return None


def _chamar_motor_visao(img_file, estilo_conversao: str, sens_escolhida: str,
                       modelo_gemini: str, max_tokens_destino: int) -> dict:
    """Motor de visão. É origem de dados do prompt final.

    `max_tokens_destino` é o teto do destino escolhido no Passo 0. A visão é a
    única etapa que enxerga a imagem, então NÃO a estrangulamos: extraímos com
    fidelidade e deixamos o adensamento com hierarquia para o consumidor.

    Devolve {"tipo": "json", "dados": {...5 campos...}} ou {"tipo": "texto", ...}.
    Inclui retry exponencial, fallback de modelos e respeito a Retry-After.
    """
    email = st.session_state.get("user_email", "")
    api_key = _resolve_api_key_visao(email)
    if not api_key:
        raise RuntimeError(_msg("Chave Visão não configurada — conecte sua chave na barra lateral."))

    tetos = _teto_visao_palavras(max_tokens_destino)
    b64, mime = _img_para_inline(img_file)

    max_out = int(sum(tetos.values()) * 2.5)

    prompt_sistema = _montar_prompt_visao(estilo_conversao, sens_escolhida, tetos)

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
            "temperature": 0.15,
            "maxOutputTokens": max_out,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA_VISAO,
        },
    }

    modelo_principal = (modelo_gemini or "").strip()
    if not modelo_principal:
        modelo_principal = MODELO_VISAO_PADRAO
    if modelo_principal not in OPCOES_GEMINI_3:
        modelo_principal = MODELO_VISAO_PADRAO

    candidatos = [modelo_principal] + [m for m in OPCOES_GEMINI_3 if m != modelo_principal]
    ultimo_erro = None

    for modelo_try in candidatos:
        corpo = dict(corpo_base)
        try:
            payload = _gerar_com_retry_visao(corpo, modelo_try, api_key)
        except Exception as e:
            ultimo_erro = e
            s = str(e).lower()
            eh_transitorio = _eh_erro_transitorio_visao(e)
            if eh_transitorio or "503" in s or "overloaded" in s or "unavailable" in s or "429" in s or "resource exhausted" in s:
                if modelo_try != candidatos[-1]:
                    continue
            break
        # Sucesso: processa resposta
        try:
            texto = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            finish = (payload.get("candidates") or [{}])[0].get("finishReason", "?")
            raise RuntimeError(_msg(f"Visão · resposta sem texto (finishReason={finish}).")) from e

        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            return {"tipo": "texto", "texto": texto}

        dados = _validar_consistencia_lateralidade(dados)
        return {"tipo": "json", "dados": dados}

    raise RuntimeError(_msg(f"Falha na Visão (Gemini) após fallback {candidatos}: {ultimo_erro}"))