"""vision.py — Etapa 3 stub / Etapa 4 full (extração óptica)
Reaproveitado do legado 1.0-3.py — PS_LEITOR_PARAMETRICO copiado via text_engines.
Resize 1536 LANCZOS, validação 10MB.
"""
from PIL import Image, ImageOps
import streamlit as st
try:
    from google import genai
except ImportError:
    genai = None

from src.text_engines import SYS_LEITOR_PARAMETRICO, MODELO_VISAO_PADRAO, OPCOES_GEMINI_3, _build_gemini_config, _gerar_com_retry, parse_json_ia

def _chamar_motor_visao(arquivo_imagem, estilo_conversao, nivel_sensualidade, modelo_gemini=None):
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
    try:
        arquivo_imagem.seek(0)
        img_pil = Image.open(arquivo_imagem)
        try:
            img_pil = ImageOps.exif_transpose(img_pil) or img_pil
            img_pil.load()
            max_lado = 1536
            if max(img_pil.size) > max_lado:
                ratio = max_lado / max(img_pil.size)
                novo = (int(img_pil.size[0] * ratio), int(img_pil.size[1] * ratio))
                resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
                img_pil = img_pil.resize(novo, resample_filter)
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
                        return {"tipo": "json", "dados": dados}
                    return {"tipo": "texto", "texto": texto}
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
