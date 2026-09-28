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
    "ComfyUI / Pony SDXL": {"regra_positivo": "Tradução TAG-A-TAG. Mantenha 100% dos detalhes. Ordem: score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up -> source_* -> rating_* -> [contagem e gênero, ex: 1girl, solo] -> [descrição física completa] -> [roupa detalhada completa] -> [ação completa] -> [cenário completo]. Use vírgulas. Nunca resuma.", "regra_negativo": "Sem regras fixas. Crie tags que sejam o oposto exato das características principais (oposto da roupa, oposto da luz, oposto do cenário, oposto da qualidade). Ex: se positivo tem 'highly detailed', negativo tem 'low detail, blurry'."},
    "ComfyUI / Illustrious": {"regra_positivo": "Tradução TAG-A-TAG hierárquica. Mantenha 100% dos detalhes. Ordem: masterpiece, best quality, amazing quality, very aesthetic, absurdres, newest -> rating -> [contagem e gênero] -> [corpo e rosto] -> [roupa completa e materiais] -> [pose exata] -> [cenário completo] -> [luz e câmera]. Use vírgulas. Nunca resuma.", "regra_negativo": "Sem regras fixas. Crie tags antônimas. Oponha-se diretamente ao estilo, anatomia e elementos visuais do prompt positivo. Adicione 'displeasing, very displeasing'."},
    "Flux.1 / Flux.2 (Klein)": {"regra_positivo": "Tradução em PROSA FLUIDA E DENSA. Mantenha 100% dos detalhes da narrativa original (sem omitir nada do sujeito, roupa, ação, cenário, iluminação ou lente). Escreva um parágrafo longo e descritivo. Descreva materiais, cores exatas e relações espaciais. NUNCA resuma. PROIBIDO OMITIR.", "regra_negativo": "Não aplicável (deixe em branco)."},
    "Midjourney v6.1+": {"regra_positivo": "Tradução em PROSA DENSA E COMPLETA. Estrutura: [Sujeito detalhado com roupa exata e cores] + [Ação] + [Cenário] + [Luz e Câmera]. Adicione no final: --ar 16:9 --v 6.1 --stylize 250 --style raw. Não omita detalhes vitais. FIDELIDADE > CONCISÃO. PROIBIDO RESUMIR.", "regra_negativo": "Não aplicável (deixe em branco)."},
    "ComfyUI / SDXL Base Natural": {"regra_positivo": "Tradução em PROSA. 'A breathtaking photo of [Sujeito + Roupas completas detalhadas], who is [Ação], located in [Cenário completo]. The lighting is [Luz exata]. Shot on [Câmera e Lente]'. Mantenha todos os detalhes.", "regra_negativo": "Sem regras fixas. Crie um parágrafo de palavras que representem o oposto do estilo e qualidade solicitados, focando em deformações, baixa qualidade e estilos opostos (ex: cartoon se o pedido for foto)."},
    "Ideogram 4": {"regra_positivo": "Tradução em PROSA DESCRITIVA E COMPLETA. Foco na diagramação e tipografia. Descreva o sujeito, roupa e cenário com 100% dos detalhes. Qualquer texto literal solicitado DEVE estar entre ASPAS DUPLAS. FIDELIDADE > BREVIDADE — mantenha todos os detalhes mesmo que ultrapasse 150 palavras. PROIBIDO RESUMIR — omissão = falha.", "regra_negativo": "Não aplicável (deixe em branco)."},
    "Krea 2": {"regra_positivo": "Tradução em PROSA ESTRUTURADA E DENSA. Descreva explicitamente a separação: Foreground (com todos os detalhes do sujeito e roupa), Midground (elementos intermediários e ação) e Background (cenário completo e luz). Mantenha alta densidade de detalhes. PROIBIDO RESUMIR — omitir = falha.", "regra_negativo": "Crie um negativo baseado estritamente no oposto do que foi pedido. Foque em evitar falhas geométricas e iluminação irreal que contrariem o positivo."},
    "Qwen / Tongyi Wanxiang": {"regra_positivo": "Tradução em INGLÊS LITERAL E DIRETO. Ordem: [Sujeito e Roupas Detalhadas] + [Cenário fg/mg/bg] + [Movimento] + [Linguagem de Câmera/Lente] + [Atmosfera e Luz]. Mantenha todos os detalhes sem floreios poéticos.", "regra_negativo": "Crie um negativo focando exclusivamente no oposto do conceito central e nas falhas anatómicas e de qualidade indesejáveis para esse contexto específico."},
    "Ernie (ViLG)": {"regra_positivo": "Tradução em INGLÊS (ou chinês se a cena for asiática). Foco em factualidade e posição espacial exata. Descreva onde cada elemento (sujeito completo, roupa, objetos) está no cenário. Zero metáforas.", "regra_negativo": "Crie um negativo com termos técnicos de arte que representem o oposto do estilo desejado e que protejam contra anatomia falha."},
    "Z-Image Turbo (ZiT)": {"regra_positivo": "Tradução em PROSA DENSA (60-120 palavras, expanda se necessário para manter 95% de fidelidade). Descreva com precisão militar: Sujeito + cor/material exato da roupa + Ação + Cenário fg/mg/bg + Luz + Câmera. Não omita NENHUM atributo da narrativa original. FIDELIDADE > LIMITE DE PALAVRAS. PROIBIDO RESUMIR.", "regra_negativo": "Crie um negativo que seja a antítese do pedido. Foque em proibir estilos opostos e texturas irrealistas."}
}
OPCOES_DESTINO = ["Selecione o Motor Destino..."] + list(BANCO_DE_MOTORES.keys())
OPCOES_GEMINI_3 = ["gemini-3.5-flash","gemini-3.6-flash","gemini-3.7-flash"]
MODELO_VISAO_PADRAO = "gemini-3.5-flash"
MODELO_TEXTO_PADRAO = "gemini-3.5-flash"
SYS_GERADOR_PREPROMPT = r"""Você é o Diretor de Arte Óptica e Composição Visual do Prompt Studio.
Gere um PRÉ-PROMPT visual completo, cinematográfico e coeso em Português a partir da ideia do usuário.
REGRAS MANDATÓRIAS:
1. PRESERVAÇÃO: Preserve nomes de personagens, franquias, gênero e ações informadas.
2. ZERO FLUFF: Adicione somente o que uma câmera captaria. É ESTRITAMENTE PROIBIDO usar metáforas.
3. SAÍDA EXCLUSIVA: Responda APENAS com a descrição visual coesa em Português."""
SYS_COMPOSITOMETRO = r"""Você é o Auditor Óptico e Analista de Composição do Prompt Studio.
Retorne EXCLUSIVAMENTE um JSON válido no formato:
{"sujeito_status": "Definido | Vago | Ausente", "sujeito_resumo": "resumo do sujeito", "acao_status": "Presente | Estática | Ausente", "cenario_status": "Definido | Vago | Ausente", "iluminacao_status": "Definida | Inferida pela IA", "camera_status": "Definida | Inferida pela IA", "nivel_sensualidade_sugerido": 1, "diagnostico_texto": "breve diagnostico", "sugestoes_cirurgicas": [ "sugestão 1", "sugestão 2" ]}"""
SYS_LEITOR_PARAMETRICO = r"""Você é o Cirurgião Óptico FORENSE de ALTA PRECISÃO do Prompt Studio. Desconstrua a imagem com precisão forense MILIMÉTRICA. PROIBIDO RESUMIR.
EXTRAIA 100% DOS DETALHES VISÍVEIS — checklist obrigatório para cada campo do JSON:
- sujeito: etnia, biotipo, formato do rosto, expressão, cor e estilo de olhos, cor/comprimento/padrão/aspecto do cabelo, TODOS os adornos (piercings, tatuagens, unhas, joias, maquiagem)
- acao: pose exata (para onde olha, inclinação da cabeça, posição de cada braço e mão, pernas, objetos segurados)
- cenario: primeiro plano + plano médio + fundo com texturas de parede/chão, objetos pendurados, mobiliário, vegetação, arquitetura
- iluminacao: tipo exato (volumetric, softbox, sunlight, neon), direção, temperatura, sombras
- estilo_camera: lente/distância focal, ângulo, profundidade de campo, estilo (photorealistic/anime), qualidade (8k, highly detailed)
Se faltar um item visível, você FALHOU. Cada valor deve ser denso e conter lista completa, não frase curta.
Retorne EXCLUSIVAMENTE um JSON válido: {"sujeito": "...", "acao": "...", "cenario": "...", "iluminacao": "...", "estilo_camera": "..."}"""
SYS_MESTRE_CORE = r"""Você é um TRADUTOR LITERAL de alta precisão do Prompt Studio.
Sua ÚNICA função é converter a "Narrativa Visual" fornecida (em português) para um Prompt na sintaxe do motor destino (em inglês).
DIRETIVAS CRÍTICAS INEGOCIÁVEIS:
1. PROIBIÇÃO ABSOLUTA DE RESUMOS (FIDELIDADE 100%):
Você DEVE incluir NO PROMPT FINAL EM INGLÊS absolutamente TODOS os detalhes presentes na Narrativa Visual original. 
Isto inclui: 
- Toda a etnia, biotipo, formato do rosto e expressões.
- Toda a cor de olhos, cor e estilo de cabelo (comprimento, padrão, aspecto).
- Todos os adornos (piercings, tatuagens, unhas, etc).
- TODAS as peças de roupa, incluindo cores exatas, tecidos, estampas, cortes e caimentos.
- O posicionamento corporal exato (para onde olha, inclinação da cabeça, posição de cada braço e mão, objetos segurados).
- O cenário detalhado (o que está no primeiro plano, o que está no fundo, texturas de parede, objetos pendurados).
- A iluminação exata descrita.
- As especificações exatas de câmera, lente e foco.
- Nomes de franquias e personagens citados (ex: Street Fighter, Chun-Li) — preserve LITERALMENTE no prompt em inglês, nunca generalize para "inspired by" sem o nome original.
SE VOCÊ OMITIR UM ÚNICO DETALHE DA NARRATIVA, VOCÊ FALHOU NA SUA MISSÃO.
2. NEGATIVO DINÂMICO (A REGRA DOS ANTÔNIMOS):
Se o motor suportar Prompts Negativos, você DEVE gerar um negativo que seja o oposto direto da descrição fornecida. NUNCA use as palavras exatas do positivo no negativo (não escreva "no beard" ou "without beard").
- Se o positivo descreve um "banheiro limpo e branco", o negativo deve incluir "dirty, dark, cluttered, outdoor".
- Se o positivo é "foto fotorrealista", o negativo deve incluir "illustration, anime, cartoon, 3d render, drawing".
- O negativo atua como um escudo para proteger a fidelidade do sujeito. 
4. PRESERVAÇÃO DE FRANQUIAS/PERSONAGENS: Se a narrativa citar franquia/personagem, mantenha o nome exato no PROMPT em inglês (ex: "Street Fighter Chun-Li"). Não omita nem generalize — fidelidade exige o nome.
3. SINTAXE DO MOTOR:
Respeite a ordem de montagem exigida pelo motor (tags vs. prosa), mas sempre priorizando a regra número 1 (100% de detalhes).
FORMATO EXATO DE SAÍDA:
1. PROMPT (ENGLISH)
[O seu prompt traduzido completo e detalhado aqui]
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
