import json
import os
import random
import time
from google import genai
from google.genai import types
import requests
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA (Apenas UMA chamada no topo)
# ==============================================================================
st.set_page_config(
    page_title="Gerador de Prompts IA", page_icon="🚀", layout="wide"
)

# ==============================================================================
# 2. CONSTANTES E LINKS DE CONFIGURAÇÃO
# ==============================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyLlqkhYChBHM6K08DnNP67C9t7E2kRS3N0pINa65oYa81--Cv4amoJm3OZ_v_MSDA7/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/xo0m3rF"

CONFIG_FILE = "config_prompts.json"
PASTA_RESULTADOS = "resultados"
PASTA_LISTAS = "listas"

opcoes_tipo_sujeito = [
    "Feminino",
    "Masculino",
    "Objeto / Item",
    "Paisagem / Cenário",
    "Criatura / Monstro / Androide",
]
opcoes_categoria_arte = [
    "Anime / Manga / Ilustração",
    "Fotorealismo / Foto Realista",
    "Arte Digital / 3D Render",
    "Pintura Clássica / Artística",
]

system_instruction = """
Você é um Engenheiro de Prompts Mestre, especialista em dois ecossistemas distintos de Geração de Imagens por Inteligência Artificial:

=============================================================================
MOTOR 1: STABLE DIFFUSION LOCAL (ILLUSTRIOUS IA & PONY SDXL PARA COMFYUI / WEBUI)
=============================================================================
Seu objetivo é criar prompts hiper-detalhados em inglês (baseados em Danbooru e conceitos visuais) e organizar a saída em formato estruturado.

### 📐 1.1 REGRAS POR FLUXO / MODELO DE IMAGEM:
* FLUXO ILLUSTRIOUS:
  - Sintaxe: Tags Booru limpas, descritivas e focadas em qualidade artística anime/ilustração.
  - Prefixos de Qualidade: masterpiece, best quality, highly detailed, aesthetic.
  - Prompt Negativo OBRIGATÓRIO: bad anatomy, low quality, worst quality, blurry, distorted, watermark, signature, bad hands, missing fingers, extra digit, fewer digits, cropped, jpeg artifacts, ugly, bad feet, bad legs, bad arms.

* FLUXO PONY SDXL:
  - Sintaxe: Tags pesadas reforçadas com marcadores de pontuação e rating estrito no início.
  - Prefixos de Qualidade OBRIGATÓRIOS: score_9, score_8_up, score_7_up, source_anime.
  - Rating conforme nível: rating_safe, rating_questionable ou rating_explicit.
  - Prompt Negativo OBRIGATÓRIO: score_6, score_5, score_4, score_3, score_2, score_1, worst quality, low quality, bad anatomy, bad hands, missing fingers, extra digits, fewer digits, fused fingers, too many fingers, deformed, bad proportions, gross proportions, bad feet, bad legs, bad body, blurry, cropped.
  - Regra Estrita de Exclusão no Negativo:
    - Se Nível 1 ou 2 (SFW): Adicione obrigatoriamente `rating_questionable, rating_explicit` ao PROMPT NEGATIVO.
    - Se Nível 3 ou 4 (Ecchi): Adicione obrigatoriamente `rating_explicit` ao PROMPT NEGATIVO.

---

### 🧠 1.2 PROTOCOLO DE SENSUALIDADE E CENSURA (NÍVEIS 1 A 6):
- Nível 1 (SFW/Comportado): Modéstia total. Roupas do personagem fiéis e normais. rating_safe.
- Nível 2 (Sutil/Atraente): Poses atraentes, roupas normais com leve ajuste de caimento. rating_safe.
- Nível 3 (Ecchi/Sugestivo): Roupas de banho (biquíni), lingerie, maiôs, trajes de academia ajustados. rating_questionable.
- Nível 4 (Risco/Ousado): Micro trajes, transparências estratégicas, decotes profundos, molhada. rating_questionable.
- Nível 5 (Máximo Convencional): Nudez artística ou trajes mínimos explícitos. rating_explicit.
- Nível 6 (Censura Estratégica / Cobertura Total):
  - VERSÃO A (Censurada): Aplicação de adereços de censura no prompt: censored, bar censorship, sticker censorship, mosaic censorship, heart stickers covering chest.
  - VERSÃO B (Sem Censura): Remover as tags de censura, mantendo a cena em rating_explicit.

---

### 🧬 1.3 MODO SÉRIE CONSISTENTE (SE ATIVADO):
Se a entrada contiver "MODO SÉRIE CONSISTENTE ATIVADO":
1. Gere exatamente a quantidade de variações solicitada.
2. Mantenha os traços faciais, cabelo e identidade do personagem rigorosamente congelados.
3. Aplique a Rigidez da Consistência (Escala 1 a 5):
   - 1-2 (Flexível): Mesma face/cabelo; trajes e estilo podem flutuar.
   - 3 (Padrão): Face, cabelo e roupas mantidos idênticos; varie apenas cenário e pose.
   - 4-5 (Trava Total): Fixação absoluta de 100% de todos os atributos visuais.
4. Varie APENAS os elementos solicitados (ex: trocar apenas o cenário ou apenas a pose).

---

### 🏙️ 1.4 ADAPTAÇÃO POR TIPO DE SUJEITO E CATEGORIA DE ARTE:
- TIPO DE SUJEITO:
  - Se "Paisagem / Cenário" ou "Objeto / Item": Remova rigorosamente qualquer referência a corpos humanos, roupas, faces ou anatomia. No PROMPT NEGATIVO, adicione obrigatoriamente: `human, person, woman, man, girl, boy, face, body, hands`.
  - Se "Paisagem / Cenário": Foque 100% em arquitetura, elementos da natureza, perspectiva, profundidade de campo, clima, hora do dia, escala e iluminação ambiental.
  - Se "Objeto / Item": Foque em fotografia de produto, textura do material (metal, vidro, madeira, plástico), reflexos, iluminação de estúdio (softbox, rim light) e profundidade de campo focada no item.
  - Se "Feminino" / "Masculino" / "Criatura": Mantenha a estruturação de personagens focada em características físicas, vestuário, pose e expressão.

- CATEGORIA DE ARTE:
  - Se "Fotorealismo / Foto Realista": Use linguagem fotográfica profissional (ex: RAW photo, 8k uhd, dslr, 35mm lens, depth of field, realistic skin texture, natural lighting, shot on 35mm). Desative tags no estilo cartoon/anime.
  - Se "Anime / Manga / Ilustração": Force estética 2D/Ilustrada (ex: anime style, vibrant colors, lineart, cel shading, digital illustration).
  - Se "Arte Digital / 3D Render": Use termos de renderização gráfica (ex: 3d render, octane render, unreal engine 5, volumetric lighting, digital concept art).
  - Se "Pintura Clássica / Artística": Use termos de técnicas tradicionais (ex: oil painting, brush strokes, canvas texture, impressionism, fine art).

---

=============================================================================
MOTOR 2: GERADOR DE PROMPTS PARA IAS DE IMAGEM VIA WEB
=============================================================================
Se a entrada contiver "MODO GENERATOR IMAGEM WEB ATIVADO", você atuará como Engenheiro de Prompts especialista em plataformas de imagem web. Adapte A SINTAXE E A ESTRUTURA do prompt em inglês de acordo com a "Plataforma Alvo" selecionada e processe todos os blocos de detalhes fornecidos:

### 🌐 2.1 REGRAS POR PLATAFORMA WEB:

1. 🍌 Nano Banana / Web Engine:
   - Sintaxe: Linguagem hiper-detalhada, focada na máxima fidelidade gráfica e física de renderização do motor.
   - Detalhes OBRIGATÓRIOS: Especifique detalhadamente texturas de pele/materiais, física de iluminação global, ray tracing, profundidade de campo, dispersão de subsuperfície (subsurface scattering) e renderização 8k.
   - Estrutura: Prompt corrido em inglês técnico e visualmente rico, incluindo a especificação do aspect ratio na descrição.

2. 🎨 Midjourney v6.1:
   - Sintaxe: Palavras-chave e blocos conceituais separados por vírgulas em inglês fluente e descritivo.
   - Parâmetros OBRIGATÓRIOS no final do prompt: Adicione os comandos nativos do Midjourney correspondentes ao ratio selecionado (Ex: `--ar 16:9` ou `--ar 9:16`), acrescidos de `--v 6.1 --stylize 250`.

3. ⚡ Flux.1 (Dev/Schnell):
   - Sintaxe: Descrição em linguagem natural fluida e contínua (estilo parágrafo narrativo).
   - Foco: Descreva a composição da cena, a posição do sujeito/objeto/paisagem, a lente utilizada (ex: 85mm lens), o tipo de iluminação e o ambiente em um texto coeso sem empilhar apenas tags soltas.

4. 🔤 Ideogram 2.0:
   - Sintaxe: Foco prioritário na integração entre arte visual e tipografia/texto renderizado.
   - Regra Rígida de Texto: Se houver "Texto na Imagem", coloque a palavra ou frase exatamente entre aspas duplas dentro do prompt (Ex: a stylish graphic poster that displays the text "Coffee Shop" in bold neon letters).

5. 🖼️ DALL-E 3 / Bing Image Creator:
   - Sintaxe: Prompt narrativo amplo, expressivo e highly conceitual.
   - Foco: Riqueza de contexto, composição artística, estilo de arte claramente definido (ex: fotorealismo, pintura a óleo, arte digital) e paleta de cores.

6. 🎭 Leonardo.Ai / SeaArt:
   - Sintaxe: Combinação de tags de estilo/preset com descrições estruturadas.
   - Foco: Iluminação de estúdio, detalhamento visual do sujeito/cenário, renderização 3D/Cinematográfica e atmosfera ambiental.

---

=============================================================================
FORMATOS OBRIGATÓRIOS DE SAÍDA (OUTPUT)
=============================================================================

--- SE FOR IMAGEM WEB (MOTOR 2) ---
### 🌐 PROMPT OTIMIZADO PARA WEB: [{PLATAFORMA_SELECIONADA}]
1. PROMPT (Inglês): [Prompt formatado na sintaxe exata exigida pela plataforma]
2. DESCRIÇÃO REDES SOCIAIS (Português): [Legenda engajadora e atrativa para publicação]
3. HASHTAGS: [Hashtags virais e relevantes]
💡 DICA DE APLICAÇÃO: [Instrução prática sobre como colar e ajustar os parâmetros no site da plataforma]

--- SE FOR IMAGEM LOCAL (MOTOR 1 - NÍVEL 1 A 5) ---
### 🖼️ IMAGEM: [Nome/Tema do Sujeito] - [Fluxo Selecionado]
1. PROMPT (Inglês): [Prompt formatado com tags do fluxo escolhido]
2. DESCRIÇÃO FACEBOOK (Português): [Legenda atrativa para redes sociais]
3. HASHTAGS: [Hashtags relevantes]
4. PROMPT NEGATIVO: [Tags negativas exigidas pelo fluxo e regras de sujeito/rating]

--- SE FOR IMAGEM LOCAL (MOTOR 1 - NÍVEL 6 - CENSURA ESTRATÉGICA) ---
### 🖼️ IMAGEM: [Nome/Tema do Sujeito] - [Fluxo Selecionado] (CENSURA ESTRATÉGICA)
1. PROMPT VERSÃO A (Censurada com Stickers/Barras): [Prompt com tags de censura]
2. PROMPT VERSÃO B (Sem Censura/Explícito): [Prompt sem tags de censura]
3. DESCRIÇÃO FACEBOOK: [Legenda redes sociais]
4. HASHTAGS: [Hashtags]
5. PROMPT NEGATIVO: [Prompt negativo do fluxo com regras de sujeito/rating]

--- SE FOR SÉRIE CONSISTENTE LOCAL ---
### 🧬 SÉRIE CONSISTENTE: [Nome do Personagem]
#### 🖼️ VARIAÇÃO [Número]: [Resumo do elemento alterado]
- PROMPT (Inglês): [Prompt]
- PROMPT NEGATIVO: [Prompt Negativo]
"""


# ==============================================================================
# 3. FUNÇÕES AUXILIARES E GERENCIAMENTO DE DADOS
# ==============================================================================
# 3. Função para checar acesso no Google Sheets via Google Apps Script
def verificar_acesso_sheets(email):
    try:
        # Tratamento basico no e-mail (remove espacos e força minusculas)
        email_limpo = email.strip().lower()
        
        # Aumentamos o timeout para 15 segundos (Google Apps Script pode ser lento para "acordar")
        response = requests.get(
            APPS_SCRIPT_URL, 
            params={"email": email_limpo}, 
            timeout=15,
            allow_redirects=True
        )
        
        if response.status_code == 200:
            dados = response.json()
            return dados.get("encontrado", False), dados.get("expiracao", "")
            
    except requests.exceptions.Timeout:
        st.error("⚠️ O Google Sheets demorou a responder. Por favor, clique em ENRAR novamente.")
    except Exception as e:
        st.error(f"Erro ao conectar com a base de dados: {e}")
        
    return False, ""


def carregar_config():
    config = {
        "chaves": {"Chave 1": "", "Chave 2": ""},
        "modelo_padrao": "gemini-2.5-flash",
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                config.update(dados)
        except Exception:
            pass

    if not config["chaves"].get("Chave 1") and os.path.exists(".api_key.txt"):
        try:
            with open(".api_key.txt", "r", encoding="utf-8") as f:
                chave_txt = f.read().strip()
                if chave_txt:
                    config["chaves"]["Chave 1"] = chave_txt
        except Exception:
            pass

    return config


def salvar_config(chaves_dict, modelo_padrao):
    dados = {"chaves": chaves_dict, "modelo_padrao": modelo_padrao}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def salvar_resultado_manual(texto, nome_sujeito):
    if not texto:
        return "⚠️ Nenhum resultado para salvar."
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_clean = (
        nome_sujeito.replace(" ", "_").lower() if nome_sujeito else "prompts"
    )
    nome_arquivo = f"prompts_{nome_clean}_{timestamp}.txt"
    caminho_completo = os.path.join(PASTA_RESULTADOS, nome_arquivo)
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(texto)
    return f"💾 Cópia salva no servidor: `{caminho_completo}`"


def carregar_lista_dual(nome_arquivo, genero="feminino"):
    caminho_arquivo = nome_arquivo
    if not os.path.exists(caminho_arquivo):
        caminho_alt = os.path.join(PASTA_LISTAS, nome_arquivo)
        if os.path.exists(caminho_alt):
            caminho_arquivo = caminho_alt

    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                linhas = [
                    l.strip()
                    for l in f.readlines()
                    if l.strip() and not l.startswith("#")
                ]

            bloco_atual = None
            linhas_genero = []
            linhas_gerais = []

            for linha in linhas:
                linha_lower = linha.lower()
                if "[feminino]" in linha_lower:
                    bloco_atual = "feminino"
                    continue
                elif "[masculino]" in linha_lower:
                    bloco_atual = "masculino"
                    continue
                elif (
                    "[geral]" in linha_lower or "[ambos]" in linha_lower
                ):
                    bloco_atual = "geral"
                    continue

                if bloco_atual == genero:
                    linhas_genero.append(linha)
                elif bloco_atual == "geral":
                    linhas_gerais.append(linha)
                elif bloco_atual is None:
                    linhas_gerais.append(linha)

            resultado = list(
                dict.fromkeys(
                    linhas_genero if linhas_genero else linhas_gerais
                )
            )
            if resultado:
                return resultado
        except Exception:
            pass

    return ["Opção Padrão 1", "Opção Padrão 2"]


def carregar_lista_nomes(genero="feminino"):
    arquivo_alvo = (
        "nomes_femininos.txt" if genero == "feminino" else "nomes_masculinos.txt"
    )
    caminhos_tentativa = [
        os.path.join(PASTA_LISTAS, arquivo_alvo),
        arquivo_alvo,
        os.path.join(PASTA_LISTAS, "personagens.txt"),
        "personagens.txt",
    ]

    for caminho in caminhos_tentativa:
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    linhas = list(
                        dict.fromkeys(
                            [
                                l.strip()
                                for l in f
                                if l.strip()
                                and not l.startswith("#")
                                and not l.startswith("[")
                            ]
                        )
                    )
                if linhas:
                    return linhas
            except Exception:
                pass

    if genero == "feminino":
        return [
            "Nami",
            "Nico Robin",
            "Android 18",
            "Tsunade",
            "Hinata Hyuga",
            "Mikasa Ackerman",
            "Yor Forger",
        ]
    return [
        "Goku",
        "Vegeta",
        "Luffy",
        "Zoro",
        "Naruto",
        "Sasuke",
        "Gojo Satoru",
        "Levi Ackerman",
    ]


def carregar_lista_integrada_web(arquivo_padrao, arquivo_web, genero_ref):
    opcoes = []
    opcoes.extend(carregar_lista_dual(arquivo_padrao, genero_ref))
    caminho_web = arquivo_web
    if not os.path.exists(caminho_web):
        caminho_alt = os.path.join(PASTA_LISTAS, arquivo_web)
        if os.path.exists(caminho_alt):
            caminho_web = caminho_alt

    if os.path.exists(caminho_web):
        try:
            with open(caminho_web, "r", encoding="utf-8") as f:
                linhas = [
                    l.strip()
                    for l in f
                    if l.strip() and not l.startswith("#")
                ]
                opcoes.extend(linhas)
        except Exception:
            pass

    resultado = list(dict.fromkeys(opcoes))
    return resultado if resultado else ["Opção Padrão 1"]


def chamar_gemini_api(dados_personagem, client, modelo="gemini-2.5-flash"):
    if not client:
        return "❌ Erro: Cliente da API não inicializado. Verifique sua Chave API."

    tipo_sujeito = dados_personagem.get("tipo_sujeito", "Feminino")
    is_objeto_ou_paisagem = tipo_sujeito in [
        "Paisagem / Cenário",
        "Objeto / Item",
    ]

    sensualidade = (
        "Não se aplica (Inativo para Paisagem/Objeto)"
        if is_objeto_ou_paisagem
        else dados_personagem.get("intensidade", 6)
    )
    emocao = (
        "Não se aplica"
        if is_objeto_ou_paisagem
        else (dados_personagem.get("emocao", "").strip() or "Nenhuma específica")
    )

    if dados_personagem.get("is_web_image"):
        prompt_usuario = f"""
        --- MODO GENERATOR IMAGEM WEB ATIVADO ---
        Plataforma Alvo Solicitada: {dados_personagem.get('plataforma_web', 'Midjourney v6.1')}
        
        Gere o prompt final otimizado em inglês com base nas especificações detalhadas fornecidas:
        - Sujeito / Tema Principal: {dados_personagem.get('nome', '').strip()}
        - Tipo de Sujeito: {tipo_sujeito}
        - Categoria de Arte: {dados_personagem.get('categoria_arte', 'Anime / Manga / Ilustração')}
        - Nível de Sensualidade: {sensualidade}
        - Orientação (Ratio): {dados_personagem.get('orientacao', '').strip()}
        - Enquadramento: {dados_personagem.get('enquadramento', '').strip()}
        - Ação do Sujeito / Estado: {dados_personagem.get('acao', '').strip()}
        - Estilo Visual Específico: {dados_personagem.get('estilo', '').strip()}
        - Expressão / Emoção: {emocao}
        - Pose / Posição / Ângulo: {dados_personagem.get('pose', '').strip()}
        - Cenário / Ambiente: {dados_personagem.get('cenario', '').strip()}
        - Iluminação: {dados_personagem.get('iluminacao', '').strip()}
        - Efeitos Especiais: {dados_personagem.get('efeitos', '').strip()}
        - Texto na Imagem (Tipografia Opcional): {dados_personagem.get('texto_web', 'Nenhum').strip()}
        """
    else:
        prompt_usuario = f"""
        Gere os prompts de imagem com base nas seguintes especificações fornecidas pelo usuário:
        
        - Nome / Sujeito: {dados_personagem.get('nome', '').strip()}
        - Fluxo Base: {dados_personagem.get('fluxo', 'Illustrious')}
        - Tipo de Sujeito: {tipo_sujeito}
        - Categoria de Arte: {dados_personagem.get('categoria_arte', 'Anime / Manga / Ilustração')}
        - Nível de Sensualidade: {sensualidade}
        - Orientação (Ratio): {dados_personagem.get('orientacao', '').strip()}
        - Enquadramento: {dados_personagem.get('enquadramento', '').strip()}
        - Ação do Sujeito / Estado: {dados_personagem.get('acao', '').strip()}
        - Estilo Visual Específico: {dados_personagem.get('estilo', '').strip()}
        - Expressão / Emoção: {emocao}
        - Pose / Posição / Ângulo: {dados_personagem.get('pose', '').strip()}
        - Cenário / Ambiente: {dados_personagem.get('cenario', '').strip()}
        - Iluminação: {dados_personagem.get('iluminacao', '').strip()}
        - Efeitos Especiais: {dados_personagem.get('efeitos', '').strip()}
        """

        if dados_personagem.get("is_serie"):
            alvos = dados_personagem.get("variaveis_alvo_str", "")
            if not alvos:
                alvos = "Pose, Cenário e Expressão"

            prompt_usuario += f"""
            
            --- MODO SÉRIE CONSISTENTE ATIVADO ---
            - Elementos para Variar Dinamicamente: {alvos}
            - Quantidade de Variações a Gerar: {dados_personagem.get('total_variacoes', 5)} variações completas.
            - Rigidez da Consistência: Nível {dados_personagem.get('rigidez', 3)} de 5.
            """

    try:
        response = client.models.generate_content(
            model=modelo,
            contents=prompt_usuario,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=0.7
            ),
        )
        if response and hasattr(response, "text") and response.text is not None:
            return response.text
        else:
            return "⚠️ A API retornou uma resposta vazia."
    except Exception as e:
        return f"❌ Erro na comunicação com o modelo '{modelo}': {str(e)}"


def st_campo_hibrido(label, placeholder, opcoes, key_prefix, disabled=False):
    col_txt, col_drop = st.columns([0.65, 0.35])

    def ao_selecionar_preset():
        sel = st.session_state.get(f"{key_prefix}_drop")
        if sel and sel not in ["Presets...", "Digite manualmente..."]:
            st.session_state[f"{key_prefix}_txt"] = sel

    validas = list(
        dict.fromkeys(
            [
                o
                for o in opcoes
                if o not in ["Digite manualmente...", "Opção Padrão 1", "Opção Padrão 2"]
            ]
        )
    )

    with col_txt:
        val = st.text_input(
            label,
            placeholder=placeholder,
            key=f"{key_prefix}_txt",
            disabled=disabled,
        )
    with col_drop:
        st.selectbox(
            "Presets",
            ["Presets..."] + validas,
            key=f"{key_prefix}_drop",
            on_change=ao_selecionar_preset,
            disabled=disabled,
        )
    return val


def autocompletar_campos(prefixo, genero_ref, is_web=False):
    if not st.session_state.get(f"{prefixo}_nome_txt", "").strip():
        nomes = carregar_lista_nomes(genero_ref)
        if nomes:
            st.session_state[f"{prefixo}_nome_txt"] = random.choice(nomes)

    campos_map = {
        "acao": ("acoes.txt", "acoes_web.txt"),
        "estilo": ("estilos.txt", "estilos_web.txt"),
        "emocao": ("expressoes.txt", "expressoes_web.txt"),
        "pose": ("poses.txt", "poses_web.txt"),
        "cenario": ("ambientes.txt", "ambientes_web.txt"),
        "iluminacao": ("iluminacoes.txt", "iluminacoes_web.txt"),
        "efeitos": ("efeitos.txt", "efeitos_web.txt"),
    }

    for campo, (arq_std, arq_web) in campos_map.items():
        key = f"{prefixo}_{campo}_txt"
        if not st.session_state.get(key, "").strip():
            lista = (
                carregar_lista_integrada_web(arq_std, arq_web, genero_ref)
                if is_web
                else carregar_lista_dual(arq_std, genero_ref)
            )
            validas = list(
                dict.fromkeys(
                    [
                        o
                        for o in lista
                        if o not in ["Digite manualmente...", "Opção Padrão 1", "Opção Padrão 2"]
                    ]
                )
            )
            if validas:
                st.session_state[key] = random.choice(validas)


def limpar_campos(prefixo):
    campos = [
        "nome",
        "acao",
        "estilo",
        "emocao",
        "pose",
        "cenario",
        "iluminacao",
        "efeitos",
        "texto",
    ]
    for c in campos:
        txt_key = f"{prefixo}_{c}_txt"
        drop_key = f"{prefixo}_{c}_drop"
        if txt_key in st.session_state:
            st.session_state[txt_key] = ""
        if drop_key in st.session_state:
            st.session_state[drop_key] = "Presets..."


def renderizar_formulario(
    prefixo, slot_chave, modelo_selecionado, is_web=False, is_serie=False
):
    col1, col2 = st.columns(2)

    with col1:
        tipo_sujeito = st.selectbox(
            "Tipo de Sujeito:", opcoes_tipo_sujeito, key=f"{prefixo}_tipo_sujeito"
        )
        g_ref = "masculino" if tipo_sujeito == "Masculino" else "feminino"

        nome = st_campo_hibrido(
            "Nome / Sujeito:",
            "Ex: Android 18, Katana Antiga",
            carregar_lista_nomes(g_ref),
            f"{prefixo}_nome",
        )

        if not is_web:
            fluxo = st.selectbox(
                "Fluxo Base:", ["Illustrious", "Pony SDXL"], key=f"{prefixo}_fluxo"
            )
        else:
            plataforma_web = st.selectbox(
                "Plataforma Web:",
                [
                    "🍌 Nano Banana / Web Engine",
                    "🎨 Midjourney v6.1",
                    "⚡ Flux.1 (Dev/Schnell)",
                    "🔤 Ideogram 2.0",
                    "🖼️ DALL-E 3 / Bing",
                    "🎭 Leonardo.Ai / SeaArt",
                ],
                key=f"{prefixo}_plataforma_web",
            )

        categoria_arte = st.selectbox(
            "Categoria de Arte:",
            opcoes_categoria_arte,
            key=f"{prefixo}_categoria_arte",
        )

        is_obj_or_land = tipo_sujeito in ["Paisagem / Cenário", "Objeto / Item"]
        intensidade = st.slider(
            "Sensualidade (1-6):",
            1,
            6,
            6,
            disabled=is_obj_or_land,
            key=f"{prefixo}_intensidade",
        )

        orientacao = st.selectbox(
            "Orientação (Ratio):",
            [
                "Vertical (Portrait 9:16)",
                "Horizontal (Landscape 16:9)",
                "Quadrado (Square 1:1)",
            ],
            key=f"{prefixo}_orientacao",
        )
        enquadramento = st.selectbox(
            "Enquadramento:",
            [
                "Corpo todo (Full body)",
                "Meio corpo (Half body)",
                "Busto (Bust shot / Close-up)",
            ],
            key=f"{prefixo}_enquadramento",
        )

    with col2:
        fn_carregar = (
            carregar_lista_integrada_web if is_web else carregar_lista_dual
        )

        acao = st_campo_hibrido(
            "Ação / Estado:",
            "Ex: em pose de combate",
            (
                fn_carregar("acoes.txt", "acoes_web.txt", g_ref)
                if is_web
                else fn_carregar("acoes.txt", g_ref)
            ),
            f"{prefixo}_acao",
        )
        estilo = st_campo_hibrido(
            "Estilo Visual:",
            "Ex: estilo Makoto Shinkai",
            (
                fn_carregar("estilos.txt", "estilos_web.txt", g_ref)
                if is_web
                else fn_carregar("estilos.txt", g_ref)
            ),
            f"{prefixo}_estilo",
        )
        emocao = st_campo_hibrido(
            "Expressão:",
            "Ex: olhar frio",
            (
                fn_carregar("expressoes.txt", "expressoes_web.txt", g_ref)
                if is_web
                else fn_carregar("expressoes.txt", g_ref)
            ),
            f"{prefixo}_emocao",
            disabled=is_obj_or_land,
        )
        pose = st_campo_hibrido(
            "Pose / Posição:",
            "Ex: flutuando no ar",
            (
                fn_carregar("poses.txt", "poses_web.txt", g_ref)
                if is_web
                else fn_carregar("poses.txt", g_ref)
            ),
            f"{prefixo}_pose",
        )
        cenario = st_campo_hibrido(
            "Ambiente / Cenário:",
            "Ex: laboratório futurista",
            (
                fn_carregar("ambientes.txt", "ambientes_web.txt", g_ref)
                if is_web
                else fn_carregar("ambientes.txt", g_ref)
            ),
            f"{prefixo}_cenario",
        )
        iluminacao = st_campo_hibrido(
            "Iluminação:",
            "Ex: neon brilhante",
            (
                fn_carregar("iluminacoes.txt", "iluminacoes_web.txt", g_ref)
                if is_web
                else fn_carregar("iluminacoes.txt", g_ref)
            ),
            f"{prefixo}_iluminacao",
        )
        efeitos = st_campo_hibrido(
            "Efeitos Especiais:",
            "Ex: faíscas elétricas",
            (
                fn_carregar("efeitos.txt", "efeitos_web.txt", g_ref)
                if is_web
                else fn_carregar("efeitos.txt", g_ref)
            ),
            f"{prefixo}_efeitos",
        )

        texto_web = ""
        if is_web:
            texto_web = st.text_input(
                "Texto na Imagem (Opcional):",
                placeholder="Ex: 'Coffee Shop'",
                key=f"{prefixo}_texto_txt",
            )

    variaveis_alvo_str = ""
    total_variacoes = 5
    rigidez = 3
    if is_serie:
        st.markdown("---")
        st.subheader("🧬 Configurações da Série Consistente")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            chk_cenario = st.checkbox(
                "Variar Cenário", value=True, key=f"{prefixo}_chk_cenario"
            )
            chk_iluminacao = st.checkbox(
                "Variar Iluminação", value=False, key=f"{prefixo}_chk_iluminacao"
            )
            chk_estilo = st.checkbox(
                "Variar Estilo Visual", value=False, key=f"{prefixo}_chk_estilo"
            )
            chk_acao = st.checkbox(
                "Variar Ação", value=False, key=f"{prefixo}_chk_acao"
            )
            chk_pose = st.checkbox(
                "Variar Pose", value=False, key=f"{prefixo}_chk_pose"
            )

            alvos = []
            if chk_cenario:
                alvos.append("Cenário")
            if chk_iluminacao:
                alvos.append("Iluminação")
            if chk_estilo:
                alvos.append("Estilo Visual")
            if chk_acao:
                alvos.append("Ação")
            if chk_pose:
                alvos.append("Pose")
            variaveis_alvo_str = (
                ", ".join(alvos) if alvos else "Pose, Cenário e Expressão"
            )

        with col_s2:
            total_variacoes = st.selectbox(
                "Total de Imagens:",
                [3, 5, 8, 10],
                index=1,
                key=f"{prefixo}_total_variacoes",
            )
            rigidez = st.slider(
                "Rigidez do Prompt (1-5):", 1, 5, 3, key=f"{prefixo}_rigidez"
            )

    st.markdown("---")
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    with btn_col1:
        gerar = st.button(
            "🚀 GERAR PROMPTS",
            key=f"{prefixo}_btn_gerar",
            use_container_width=True,
        )
    with btn_col2:
        st.button(
            "✨ AUTOCOMPLETAR",
            key=f"{prefixo}_btn_auto",
            on_click=autocompletar_campos,
            args=(prefixo, g_ref, is_web),
            use_container_width=True,
        )
    with btn_col3:
        st.button(
            "🗑️ LIMPAR CAMPOS",
            key=f"{prefixo}_btn_limpar",
            on_click=limpar_campos,
            args=(prefixo,),
            use_container_width=True,
        )
    with btn_col4:
        salvar = st.button(
            "💾 SALVAR NO SERVIDOR",
            key=f"{prefixo}_btn_salvar",
            use_container_width=True,
        )

    dados = {
        "nome": nome,
        "tipo_sujeito": tipo_sujeito,
        "categoria_arte": categoria_arte,
        "intensidade": intensidade,
        "orientacao": orientacao,
        "enquadramento": enquadramento,
        "acao": acao,
        "estilo": estilo,
        "emocao": emocao,
        "pose": pose,
        "cenario": cenario,
        "iluminacao": iluminacao,
        "efeitos": efeitos,
        "is_web_image": is_web,
        "is_serie": is_serie,
        "variaveis_alvo_str": variaveis_alvo_str,
        "total_variacoes": total_variacoes,
        "rigidez": rigidez,
    }

    if is_web:
        dados["plataforma_web"] = plataforma_web
        dados["texto_web"] = texto_web
    else:
        dados["fluxo"] = fluxo

    if salvar:
        msg = salvar_resultado_manual(
            st.session_state.get(f"{prefixo}_resultado", ""), nome
        )
        st.info(msg)

    if gerar:
        chave_atual = st.session_state.get(
            f"input_key_{slot_chave}", ""
        ).strip()
        if not chave_atual:
            st.error(
                "❌ Por favor, insira sua Chave API do Gemini na barra lateral."
            )
        else:
            with st.spinner("⏳ Processando prompt via Gemini API..."):
                try:
                    client = genai.Client(api_key=chave_atual)
                    resultado = chamar_gemini_api(
                        dados, client, modelo=modelo_selecionado
                    )
                    st.session_state[f"{prefixo}_resultado"] = resultado
                except Exception as e:
                    st.error(f"❌ Erro ao inicializar cliente: {str(e)}")

    if st.session_state.get(f"{prefixo}_resultado"):
        # Inserção de quebra de linha e divisor visual automático
        st.write("")
        st.markdown("---")
        st.write("")
        
        st.markdown("### 📝 Resultado:")
        st.code(st.session_state[f"{prefixo}_resultado"], language="markdown")

        st.write("") # Quebra de linha entre o resultado e o botão de download
        
        nome_arquivo_dl = f"prompts_{(nome.replace(' ', '_').lower() if nome else 'gerado')}.txt"
        st.download_button(
            label="📥 BAIXAR ARQUIVO DE PROMPTS (.TXT)",
            data=st.session_state[f"{prefixo}_resultado"],
            file_name=nome_arquivo_dl,
            mime="text/plain",
            key=f"{prefixo}_btn_download",
        )

# ==============================================================================
# 4. GERENCIAMENTO DA SESSÃO DO USUÁRIO
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "expiracao" not in st.session_state:
    st.session_state.expiracao = ""

# ==============================================================================
# TELA 1: LANDING PAGE + LOGIN (Exibida para quem AINDA NÃO SE AUTENTICOU)
# ==============================================================================
if not st.session_state.autenticado:
    st.markdown(
        "<h1 style='text-align: center;'>🚀 Gerador de Prompts Profissionais</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; font-size: 1.2rem; color: #666;'>Crie prompts perfeitos em segundos e extraia o máximo de desempenho das Inteligências Artificiais.</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("### 🔑 Já é cliente? Acesse a ferramenta:")
    col_login1, col_login2 = st.columns([3, 1])

    with col_login1:
        email_input = st.text_input(
            "E-mail de compra:",
            placeholder="seuemail@exemplo.com",
            label_visibility="collapsed",
        )

    with col_login2:
        if st.button("ENTRAR NA FERRAMENTA", type="primary", use_container_width=True):
            if email_input:
                # Trata o e-mail (remove espaços extras e força minúsculas)
                email_limpo = email_input.strip().lower()
                
                com_acesso, data_exp = verificar_acesso_sheets(email_limpo)
                if com_acesso:
                    st.session_state.autenticado = True
                    st.session_state.user_email = email_limpo
                    st.session_state.expiracao = data_exp
                    st.success("Acesso liberado!")
                    st.rerun()
                else:
                    st.error("E-mail não encontrado ou acesso expirado.")
            else:
                st.warning("Por favor, digite o seu e-mail de compra.")

    st.divider()

    st.markdown(
        "<h3 style='text-align: center;'>💳 Ainda não tem acesso? Escolha o plano ideal para você:</h3>",
        unsafe_allow_html=True,
    )
    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🥉 Plano 15 Dias")
        st.markdown("## R$ 19,90")
        st.caption("Ideal para testes rápidos")
        st.write("✓ Acesso total à ferramenta")
        st.write("✓ Prompts otimizados ilimitados")
        st.write("✓ Validade: **15 dias**")
        st.write("")
        st.link_button(
            "Garantir 15 Dias", LINK_KIWIFY_15_DIAS, use_container_width=True
        )

    with col2:
        st.markdown("### 🥈 Plano 30 Dias")
        st.markdown("## R$ 29,90")
        st.caption("Plano mensal padrão")
        st.write("✓ Acesso total à ferramenta")
        st.write("✓ Prompts otimizados ilimitados")
        st.write("✓ Validade: **30 dias**")
        st.write("")
        st.link_button(
            "Garantir 30 Dias", LINK_KIWIFY_30_DIAS, use_container_width=True
        )

    with col3:
        st.markdown("### 🥇 Plano 90 Dias 🔥")
        st.markdown("## R$ 59,90")
        st.caption("🌟 **Mais Popular** — Leve 3, Pague 2")
        st.write("✓ Acesso total à ferramenta")
        st.write("✓ Prompts otimizados ilimitados")
        st.write("✓ Validade: **90 dias**")
        st.write("✓ **Economize R$ 29,80**")
        st.link_button(
            "GARANTIR 90 DIAS (OFERTA)",
            LINK_KIWIFY_90_DIAS,
            type="primary",
            use_container_width=True,
        )

# ==============================================================================
# TELA 2: APLICATIVO PRINCIPAL (Exibida APENAS para quem está AUTENTICADO)
# ==============================================================================
else:
    config_salva = carregar_config()
    if "chaves_api" not in st.session_state:
        st.session_state.chaves_api = config_salva.get(
            "chaves", {"Chave 1": "", "Chave 2": ""}
        )

    # Barra Lateral
    with st.sidebar:
        st.title("👤 Sua Conta")
        st.write(f"**E-mail:** {st.session_state.user_email}")
        st.write(f"**Validade:** {st.session_state.expiracao}")
        st.divider()

        st.header("🔑 Configurações da API")
        slot_chave = st.selectbox(
            "Selecione o Slot:", list(st.session_state.chaves_api.keys())
        )

        chave_key = f"input_key_{slot_chave}"
        if chave_key not in st.session_state:
            st.session_state[chave_key] = st.session_state.chaves_api.get(
                slot_chave, ""
            )

        chave_input = st.text_input(
            "Chave API Gemini:", type="password", key=chave_key
        )

        modelos_disponiveis = [
            "gemini-3.6-flash",
            "gemini-3.6-pro",
            "gemini-3.5-flash",
            "gemini-3.5-pro",
            "gemini-3.0-flash",
            "gemini-3.0-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]
        modelo_salvo = config_salva.get("modelo_padrao", "gemini-3.6-flash")
        modelo_selecionado = st.selectbox(
            "Modelo Gemini:",
            modelos_disponiveis,
            index=(
                modelos_disponiveis.index(modelo_salvo)
                if modelo_salvo in modelos_disponiveis
                else 0
            ),
        )

        if st.button("💾 Salvar Configurações"):
            st.session_state.chaves_api[slot_chave] = chave_input.strip()
            salvar_config(st.session_state.chaves_api, modelo_selecionado)
            st.success("Configurações salvas com sucesso!")

        st.divider()
        if st.button("Sair / Trocar Conta", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.user_email = ""
            st.session_state.expiracao = ""
            st.rerun()

    st.title("🎨 Gerador Mestre de Prompts IA")

    # Abas da Aplicação
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "👤 Personagem 1",
            "👤 Personagem 2",
            "👤 Personagem 3",
            "🧬 Série Consistente",
            "🌐 Imagem Web",
        ]
    )

    with tab1:
        renderizar_formulario("p1", slot_chave, modelo_selecionado)
    with tab2:
        renderizar_formulario("p2", slot_chave, modelo_selecionado)
    with tab3:
        renderizar_formulario("p3", slot_chave, modelo_selecionado)
    with tab4:
        renderizar_formulario(
            "serie", slot_chave, modelo_selecionado, is_serie=True
        )
    with tab5:
        renderizar_formulario(
            "web", slot_chave, modelo_selecionado, is_web=True
        )
