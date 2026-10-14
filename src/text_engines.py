"""text_engines.py — Etapa 3 (BANCO_DE_MOTORES + SYS_* + motor Texto + helpers)
Reaproveitado do legado 1.0-3.py sem reescrever prompts (F07/F08).
Ajuste: MODELO_TEXTO_PADRAO = gemini-3.5-flash nas duas vias (não 3.7). Abaixo de 3.X é obsoleto (C-A2).
"""
import re
import json
import html
import time
import random
import secrets
import unicodedata
import streamlit as st
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
OPCOES_SENSUALIDADE = ["1 - Seguro (SFW)","2 - Menos Seguro","3 - Ecchi Leve","4 - Ecchi","5 - Picante","6 - Dual (Com & Sem Censura)"]
BANCO_DE_MOTORES = {
    "ComfyUI / Pony SDXL": {
        "regra_positivo": (
            "Tradução TAG-A-TAG ultra-compacta. Mantenha 100% dos atributos visuais sem usar artigos (a, an, the) ou verbos de ligação. "
            "Ordem com Front-Loading Óptico: score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up -> source_* -> rating_* -> "
            "[enquadramento, ângulo e iluminação principal] -> [contagem e gênero, ex: 1girl, solo] -> [descrição física e rosto completos] -> "
            "[roupa, cores, materiais e adornos completos] -> [ação e pose exata] -> [cenário fg/mg/bg completo]. Use vírgulas. Zero omissão de atributos."
        ),
        "regra_negativo": "Sem regras fixas. Crie tags que sejam o oposto exato das características principais (oposto da roupa, oposto da luz, oposto do cenário, oposto da qualidade). Ex: se positivo tem 'highly detailed', negativo tem 'low detail, blurry'."
    },
    "ComfyUI / Illustrious": {
        "regra_positivo": (
            "Tradução TAG-A-TAG hierárquica de alta densidade. Mantenha 100% dos detalhes eliminando conectivos gramaticais. "
            "Ordem com Front-Loading: masterpiece, best quality, amazing quality, very aesthetic, absurdres, newest -> rating -> "
            "[enquadramento, lente e iluminação] -> [contagem e gênero] -> [corpo, rosto, olhos, cabelo e adornos] -> "
            "[roupa completa, cortes e materiais] -> [pose exata de membros e olhar] -> [cenário fg/mg/bg completo]. Use vírgulas. Nunca omita atributos."
        ),
        "regra_negativo": "Sem regras fixas. Crie tags antônimas. Oponha-se diretamente ao estilo, anatomia e elementos visuais do prompt positivo. Adicione 'displeasing, very displeasing'."
    },
    "Flux.1 / Flux.2 (Klein)": {
        "regra_positivo": (
            "Tradução em PROSA TELEGRÁFICA DE ALTA DENSIDADE. Mantenha 100% dos detalhes da narrativa original (zero omissão de sujeito, roupa, ação, cenário, iluminação ou lente), "
            "mas com Compactação Sintática: elimine frases de preenchimento ('who is', 'there is', 'located in', 'we see') e una adjetivos em termos compostos diretos (ex: 'sunlit cobblestone alley' em vez de 'an alley made of cobblestone that is lit by the sun'). "
            "Ordem obrigatória: [Enquadramento + Lente + Estilo + Iluminação Principal] -> [Sujeito + Biotipo + Rosto + Cabelo + Adornos + Roupa completa] -> [Ação e Pose anatômica] -> [Cenário FG/MG/BG e Micro-texturas]. PROIBIDO OMITIR ATRIBUTOS."
        ),
        "regra_negativo": "Não aplicável (deixe em branco)."
    },
    "Midjourney v6.1+": {
        "regra_positivo": (
            "Tradução em PROSA DENSA E COMPACTA (Token-Packed). Ordem de máxima atenção: "
            "[Enquadramento, Lente e Iluminação] + [Sujeito detalhado com roupa exata, tecidos e cores] + [Ação e Pose] + [Cenário FG/MG/BG]. "
            "Elimine artigos e verbos auxiliares desnecessários para concentrar 100% dos tokens em substantivos visuais e adjetivos técnicos. "
            "Adicione no final: --ar 16:9 --v 6.1 --stylize 250 --style raw. PROIBIDO OMITIR ATRIBUTOS."
        ),
        "regra_negativo": "Não aplicável (deixe em branco)."
    },
    "ComfyUI / SDXL Base Natural": {
        "regra_positivo": (
            "Tradução em PROSA COMPACTA OTIMIZADA PARA CLIP (77/154 tokens). "
            "Estrutura enxuta sem pronomes relativos: '[Enquadramento, câmera, lente e iluminação], [Sujeito + biotipo + rosto + cabelo + roupas completas em termos compostos], "
            "[Ação e pose exata], [Cenário FG/MG/BG e texturas]'. Mantenha 100% dos detalhes visuais eliminando palavras vazias ('who is', 'located in', 'the lighting is')."
        ),
        "regra_negativo": "Sem regras fixas. Crie um parágrafo de palavras que representem o oposto do estilo e qualidade solicitados, focando em deformações, baixa qualidade e estilos opostos (ex: cartoon se o pedido for foto)."
    },
    "Ideogram 4": {
        "regra_positivo": (
            "Tradução em PROSA DESCRITIVA DENSA E COMPACTA. Foco na diagramação, cores exatas e tipografia. "
            "Ordem: [Estilo, Enquadramento e Tipografia entre ASPAS DUPLAS] -> [Sujeito, roupa e materiais com 100% dos detalhes] -> [Ação] -> [Cenário e Iluminação]. "
            "Use sintaxe enxuta sem conectivos redundantes para preservar todos os detalhes sem diluir a atenção do modelo."
        ),
        "regra_negativo": "Não aplicável (deixe em branco)."
    },
    "Krea 2": {
        "regra_positivo": (
            "Tradução em PROSA ESTRUTURADA E COMPACTA (Alta Densidade Fotográfica). "
            "Ordem: [Câmera, Lente, Ângulo, DOF e Iluminação Física] -> Foreground ([100% dos detalhes de sujeito, rosto, adornos, roupa e pose em sintaxe direta]) -> "
            "Midground ([elementos intermediários e interação espacial]) -> Background ([cenário de fundo e texturas]). "
            "Elimine verbos explicativos e mantenha 100% dos atributos visuais."
        ),
        "regra_negativo": "Crie um negativo baseado estritamente no oposto do que foi pedido. Foque em evitar falhas geométricas e iluminação irreal que contrariem o positivo."
    },
    "Qwen / Tongyi Wanxiang": {
        "regra_positivo": (
            "Tradução em INGLÊS DIRETO DE ALTA DENSIDADE (VLM-Optimized). "
            "Ordem: [Câmera/Lente + Atmosfera e Luz] + [Sujeito, Biotipo, Rosto e Roupas Detalhadas] + [Ação/Movimento] + [Cenário fg/mg/bg]. "
            "Mantenha 100% dos detalhes visuais usando frases curtas, diretas e sem metáforas ou conectivos longos."
        ),
        "regra_negativo": "Crie um negativo focando exclusivamente no oposto do conceito central e nas falhas anatómicas e de qualidade indesejáveis para esse contexto específico."
    },
    "Ernie (ViLG)": {
        "regra_positivo": (
            "Tradução em INGLÊS FACTUAL E COMPACTO. Foco em posição espacial exata e atributos diretos. "
            "Ordem: [Enquadramento e Luz] + [Sujeito completo, roupa e objetos] + [Posição espacial FG/MG/BG no cenário]. Zero metáforas e zero palavras vazias."
        ),
        "regra_negativo": "Crie um negativo com termos técnicos de arte que representem o oposto do estilo desejado e que protejam contra anatomia falha."
    },
    "Z-Image Turbo (ZiT)": {
        "regra_positivo": (
            "Tradução em PROSA TELEGRÁFICA ULTRA-COMPACTA (Empacotamento Semântico). "
            "Converta 100% dos atributos da narrativa para adjetivos compostos em inglês, eliminando todos os artigos e conectivos dispensáveis. "
            "Ordem: [Câmera + Luz] -> [Sujeito + cor/material exato da roupa + adornos] -> [Ação/Pose] -> [Cenário fg/mg/bg]. "
            "Retenção de 100% dos detalhes visuais com mínimo consumo de tokens."
        ),
        "regra_negativo": "Crie um negativo que seja a antítese do pedido. Foque em proibir estilos opostos e texturas irrealistas."
    }
}

SYS_MESTRE_CORE = r"""Você é um COMPILADOR VISUAL DE ALTA DENSIDADE do Prompt Studio.
Sua ÚNICA função é converter a "Narrativa Visual" fornecida (em português) para um Prompt na sintaxe do motor destino (em inglês) com 100% de retenção de atributos e 0% de desperdício de tokens.

DIRETIVAS CRÍTICAS INEGOCIÁVEIS:
1. FIDELIDADE ABSOLUTA DE ATRIBUTOS (100% DOS DETALHES VISUAIS):
Você DEVE incluir NO PROMPT FINAL EM INGLÊS absolutamente TODOS os atributos visuais presentes na Narrativa Visual original:
- Etnia, biotipo, formato do rosto, expressões, cor/formato de olhos, cabelo (cor, comprimento, padrão).
- Todos os adornos (piercings, tatuagens, unhas, joias, maquiagem).
- TODAS as peças de roupa (cores exatas, tecidos, estampas, cortes e caimentos).
- Posicionamento corporal exato (direção do olhar, inclinação da cabeça, posição de cada braço/mão/perna, objetos segurados).
- Cenário completo (primeiro plano, plano médio, fundo, texturas de parede/chão, mobiliário/objetos).
- Iluminação exata (tipo, direção, temperatura, sombras) e especificações de câmera/lente/DOF.
- Nomes de franquias e personagens citados (ex: Street Fighter, Chun-Li) — preserve LITERALMENTE no prompt em inglês.
SE VOCÊ OMITIR UM ÚNICO ATRIBUTO VISUAL DA NARRATIVA, VOCÊ FALHOU NA SUA MISSÃO.

2. DESIDRATAÇÃO SINTÁTICA (TOKEN PACKING — COMO NÃO ESTOURAR OS TOKENS):
Proibido omitir detalhes visuais, mas OBRIGATÓRIO eliminar "gordura gramatical" na tradução para o inglês:
- Elimine expressões vazias como "there is", "we can see", "who is", "which is", "located in", "featuring a", "with a lighting that".
- Use aglutinação adjetiva do inglês para reduzir tokens mantendo 100% da informação (Ex: em vez de "a jacket made of black leather with zippers of silver", escreva "silver-zippered black leather jacket").
- Troque orações longas por locuções diretas separadas por vírgula ou ponto-e-vírgula, preservando cada cor, textura, posição e material.

3. NEGATIVO DINÂMICO (A REGRA DOS ANTÔNIMOS):
Se o motor suportar Prompts Negativos, gere um negativo que seja o oposto direto da descrição fornecida. NUNCA use as palavras exatas do positivo no negativo (não escreva "no beard" ou "without beard").
- Se o positivo descreve um "banheiro limpo e branco", o negativo deve incluir "dirty, dark, cluttered, outdoor".
- Se o positivo é "foto fotorrealista", o negativo deve incluir "illustration, anime, cartoon, 3d render, drawing".

4. SINTAXE E FRONT-LOADING DO MOTOR:
Respeite a ordem de montagem exigida pelo motor selecionado (posicionando câmera/lente/luz na frente quando especificado para evitar truncamento no final do prompt).

FORMATO EXATO DE SAÍDA:
1. PROMPT (ENGLISH)
[O seu prompt compilado completo, ultra-denso e com 100% dos atributos aqui]
2. NEGATIVE PROMPT (ENGLISH)
[O seu prompt negativo baseado em antônimos aqui]
3. LEGENDA
[Resumo em PT-BR]
4. HASHTAGS
[5-8 hashtags]
"""
def normalizar_texto(texto):
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
def _ps_markup_origin(preprompt, ideia_original):
    try:
        if not preprompt: return ""
        texto_orig = set(normalizar_texto(ideia_original).split())
        partes = []
        for token in re.split(r"(\s+)", str(preprompt)):
            if not token.strip(): partes.append(html.escape(token))
            elif normalizar_texto(token) in texto_orig: partes.append(f"<span class=\"ps-user-word\">{html.escape(token)}</span>")
            else: partes.append(f"<span class=\"ps-ai-word\">{html.escape(token)}</span>")
        return "".join(partes)
    except Exception: return html.escape(str(preprompt or ""))
def parse_json_ia(texto):
    if not texto: return None
    limpo = str(texto).strip()
    limpo = re.sub(r"^```(?:json)?\s*", "", limpo, flags=re.IGNORECASE)
    limpo = re.sub(r"\s*```$", "", limpo).strip()
    try: return json.loads(limpo)
    except json.JSONDecodeError: pass
    inicio = limpo.find("{")
    if inicio < 0: return None
    profundidade = 0; em_string=False; escapado=False; fim=None
    for indice in range(inicio, len(limpo)):
        c = limpo[indice]
        if em_string:
            if escapado: escapado=False
            elif c == "\\": escapado=True
            elif c == '"': em_string=False
            continue
        if c == '"': em_string=True
        elif c == "{": profundidade+=1
        elif c == "}":
            profundidade-=1
            if profundidade==0: fim=indice+1; break
    if fim is None: return None
    try: return json.loads(limpo[inicio:fim])
    except (TypeError, json.JSONDecodeError): return None
def _extrair_retry_after_segundos(erro_str):
    try:
        m = re.search(r"retry[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*s", erro_str, re.IGNORECASE)
        if m: return min(float(m.group(1)), 30.0)
        m2 = re.search(r"Retry-After:\s*([0-9]+)", erro_str, re.IGNORECASE)
        if m2: return min(float(m2.group(1)), 30.0)
    except Exception: pass
    return None
def _eh_erro_transitorio_gemini(e):
    s=str(e).lower()
    if any(k in s for k in ("invalid argument","validation","not supported","unsupported","unknown field")): return False
    if any(k in s for k in ("503","429","500","502","504","overloaded","unavailable","resource exhausted","internal error","deadline exceeded")):
        if any(p in s for p in ("temperature","top_p","top_k","candidate_count","thinking")):
            if "temperature" in s or "not supported" in s or "unsupported" in s: return False
        return True
    try:
        code=getattr(e,"code",None) or getattr(e,"status_code",None) or getattr(getattr(e,"response",None),"status_code",None)
        if code in (429,500,502,503,504):
            if any(p in s for p in ("temperature","candidate_count")) and "not supported" in s: return False
            return True
    except Exception: pass
    return False
def _build_gemini_config(system_instruction, model_id, temperature=None):
    if types is None:
        cfg={"system_instruction": system_instruction}
        if temperature is not None: cfg["temperature"]=temperature
        return cfg
    kwargs={"system_instruction": system_instruction}
    if temperature is not None: kwargs["temperature"]=temperature
    return types.GenerateContentConfig(**kwargs)
def _gerar_com_retry(client, model, contents, config, tentativas=3):
    ultimo_erro=None
    for tentativa in range(tentativas):
        try: return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            ultimo_erro=e
            if not _eh_erro_transitorio_gemini(e) or tentativa==tentativas-1: raise
            retry_after=_extrair_retry_after_segundos(str(e))
            espera=retry_after if retry_after is not None else (2**(tentativa+1))+random.uniform(0,1.0)
            espera=min(espera,20.0)
            time.sleep(espera)
    raise ultimo_erro
def _msg_erro_diagnostico(e):
    try:
        raw=str(e); code=getattr(e,"code",None) or getattr(e,"status_code",None) or getattr(getattr(e,"response",None),"status_code",None) or "?"
        return f"RAW [{code}]: {raw[:1200]}"
    except Exception: return str(e)[:1200]
def _msg_erro_amigavel(e):
    texto=str(e)
    if "401" in texto or "Unauthorized" in texto or "403" in texto: return "🔑 **Chave inválida, sem permissão ou expirada.** Gere outra em aistudio.google.com/app/apikey e conecte novamente."
    if "404" in texto or "not found" in texto.lower(): return "⚠️ **Modelo não encontrado (404).** O id selecionado (gemini-3.5/3.6/3.7-flash) pode não estar liberado para sua chave/região. Tente outro dos 3 em Ferramentas Avançadas."
    if "429" in texto or "quota" in texto.lower() or "resource exhausted" in texto.lower(): return "⏳ **Limite de uso da API atingido (429/Quota).** Sua cota gratuita para esta chave acabou. Troque a chave, aguarde o reset (24h) ou use outra conta."
    if "503" in texto or "overloaded" in texto.lower() or "unavailable" in texto.lower(): return "🔌 **Servidores do Google sobrecarregados (503).** O código já tentou 3 vezes com backoff. Se persiste: é sobrecarga regional — tente outro modelo (3.5/3.6/3.7) em Ferramentas Avançadas, troque de chave/projeto ou aguarde 5-10 min."
    return f"⚠️ **Erro Sistémico:** {texto[:500]}"
def _chamar_motor_texto(system_prompt, user_prompt, modelo_gemini=None, temperature=0.25):
    from src.config_store import carregar_config
    config=carregar_config(st.session_state.get("user_email",""))
    chave_texto=st.session_state.get("input_key_texto","").strip() or config.get("chaves",{}).get("Chave Texto","")
    if not chave_texto or genai is None: raise RuntimeError("Nenhuma chave configurada para Texto. Adicione a 'Chave Gemini (Texto)' no painel lateral.")
    modelo_segundo_gemini=(modelo_gemini or "").strip() if modelo_gemini else ""
    if not modelo_segundo_gemini: modelo_segundo_gemini=(st.session_state.get("modelo_texto_select") or "").strip()
    if not modelo_segundo_gemini: modelo_segundo_gemini=config.get("modelo_texto", MODELO_TEXTO_PADRAO)
    if modelo_segundo_gemini not in OPCOES_GEMINI_3: modelo_segundo_gemini=MODELO_TEXTO_PADRAO
    sys_final=f"{system_prompt}\n\n[REF-VERIF:{secrets.token_hex(8)}]"
    candidatos=[modelo_segundo_gemini]+[m for m in OPCOES_GEMINI_3 if m != modelo_segundo_gemini]
    ultimo_erro=None
    for modelo_try in candidatos:
        for modo_temp in (temperature, None):
            try:
                client=genai.Client(api_key=chave_texto)
                cfg=_build_gemini_config(sys_final, modelo_try, temperature=modo_temp)
                resp=_gerar_com_retry(client, modelo_try, user_prompt, cfg)
                texto=getattr(resp,"text",""); texto=str(texto or "").strip()
                if texto and "[REF-VERIF:" not in texto:
                    sufixo="" if modo_temp is not None else " sem temp"
                    return texto, f"{modelo_try} (Texto{sufixo})"
                raise RuntimeError("O modelo retornou uma resposta em branco.")
            except Exception as e:
                ultimo_erro=e; s=str(e).lower()
                eh_transitorio=_eh_erro_transitorio_gemini(e)
                eh_validation=any(k in s for k in ("invalid argument","validation","not supported","unsupported"))
                if eh_validation and modo_temp is not None: continue
                if eh_transitorio or "503" in s or "overloaded" in s or "unavailable" in s or "429" in s or "resource exhausted" in s:
                    if modo_temp is not None: continue
                    break
                if modo_temp is not None: continue
                break
        if ultimo_erro is not None and (_eh_erro_transitorio_gemini(ultimo_erro) or "503" in str(ultimo_erro).lower() or "overloaded" in str(ultimo_erro).lower()):
            if modelo_try==candidatos[-1]: break
            continue
        if ultimo_erro is not None and not _eh_erro_transitorio_gemini(ultimo_erro) and "503" not in str(ultimo_erro).lower():
            if "404" in str(ultimo_erro).lower() or "not found" in str(ultimo_erro).lower():
                if modelo_try!=candidatos[-1]: continue
        break
    raise RuntimeError(f"Falha no Segundo Gemini (Engenharia de Texto) após fallback {candidatos}: {str(ultimo_erro)}")
