import json
import os
import random
import re
import time
from google import genai
from google.genai import types
import requests
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS GLOBAL
# ==============================================================================
st.set_page_config(
    page_title="Gerador de Prompts IA", page_icon="🚀", layout="wide"
)

# Injeção de CSS para forçar quebra de linha automática (word wrap) no resultado
st.markdown(
    """
    <style>
    code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
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

opcoes_sensualidade = [
    "1 - Seguro (SFW)",
    "2 - Menos Seguro",
    "3 - Ecchi Leve",
    "4 - Ecchi",
    "5 - Picante",
    "6 - Dual (Com & Sem Censura)",
]

opcoes_seios = [
    "Padrão do Personagem / Não especificar",
    "Pequenos",
    "Médios",
    "Grandes",
    "Volumosos",
]

opcoes_mamilos = [
    "Não especificar",
    "Discretos",
    "Eretos",
    "Muito eretos",
]

system_instruction = """Você é um Engenheiro de Prompts Mestre, especialista em dois ecossistemas distintos de Geração de Imagens por Inteligência Artificial:

=============================================================================
PROTOCOLO DE FIDELIDADE ABSOLUTA 100% (CANON DIRETO & DANBOORU MAPPING)
=============================================================================
Sempre que o Nome/Sujeito for um personagem existente da cultura pop (anime, games, filmes, quadrinhos):

0. PESQUISA E CONSULTA CANÔNICA OBRIGATÓRIA (WEB GROUNDING):
   - Antes de gerar qualquer tag, faça uma busca rápida na web sobre o personagem `[nome_do_personagem]` da franquia `([nome_da_franquia])`.
   - Verifique explicitamente em wikis ou bases Booru:
     1. Cor exata dos olhos e tom do cabelo (ex: se é loiro-platinado, azul-escuro, etc.).
     2. Paleta de cores do traje oficial principal.
     3. Acessórios marcantes e detalhes que costumam ser esquecidos (ex: laços, cicatrizes, presilhas, formato do calçado).
   - Use os dados retornados pela busca para preencher as Camadas 1, 2 e 3 do prompt com 100% de precisão de cores.

1. HIERARQUIA DE CAMADAS MANDATÓRIA (ORDEM DE ATENÇÃO DO MOTOR):
   O prompt positivo montado DEVE seguir rigorosamente esta sequência do início ao fim para garantir que o motor priorize a fidelidade visual antes de elementos acessórios:
   [CAMADA 1: IDENTIDADE E FRANQUIA] -> [CAMADA 2: ROSTO, CABELO E OLHOS] -> [CAMADA 3: TRAJE CANÔNICO] -> [CAMADA 4: POSE, EXPRESSÃO E ENQUADRAMENTO] -> [CAMADA 5: MODIFICADORES, ANATOMIA E AMBIENTE]

2. SINTAXE DE IDENTIFICAÇÃO E ANCORAGEM DE CORES (PROIBIDO USAR ESPAÇOS EM CORES):
   - Tag do Personagem: `[nome_do_personagem]` (formato booru com underline, ex: `android_18`, `nico_robin`, `2b`).
   - Tag de Franquia/Série OBRIGATÓRIA entre parênteses: `([nome_da_franquia])` (ex: `(dragon_ball)`, `(one_piece)`, `(nier_automata)`).
   - ANCORAGEM OBRIGATÓRIA COM UNDERLINE: NUNCA use espaços entre a cor e a característica física. O underline une o token e impede o vazamento de cor para outras partes da cena.
     * Incorreto: `blonde hair, blue eyes, black vest`
     * Correto: `blonde_hair, blue_eyes, black_vest`

3. DESCONSTRUÇÃO CANÔNICA EM TAGS BOORU ATÔMICAS (PROIBIDO RESUMIR):
   Você DEVE consultar seu conhecimento de banco de dados e desmembrar a imagem oficial do personagem em tags booru atômicas exatas nas seguintes camadas:
   - Camada 1 (Identidade): `[nome_do_personagem]`, `([nome_da_franquia])`.
   - Camada 2 (Rosto e Cabelo): Tom exato de cor, comprimento, divisão da franja, estilo, cor dos olhos, formato de sobrancelha e marcas faciais únicas (`[cor]_hair`, `[estilo]_hair`, `[cor]_eyes`, `ahoge`, `scar_on_cheek`).
   - Camada 3 (Vestuário Superior e Inferior): Roupa interna, jaqueta/colete, gola, estampa, botões, cinto, saia/calça, textura, meias (`[cor]_[peça]`).
   - Camada 4 (Calçados e Acessórios): Botas, brincos, luvas, tatuagens, armas e itens icônicos.

4. EXEMPLO OBRIGATÓRIO DE EXPANSÃO DE FIDELIDADE (FEW-SHOT CORRIGIDO):
   - Entrada: "Android 18"
   - Saída Obrigatória de Identidade no Prompt:
     `android_18, (dragon_ball), blonde_hair, short_hair, side_parted_hair, forehead, blue_eyes, gold_hoop_earrings, black_vest, collar, button_vest, white_long_sleeves, striped_sleeves, black_t-shirt, denim_skirt, brown_belt, black_pantyhose, brown_boots`

5. REGRA DE MUTAÇÃO DE TRAJE E MODIFICADORES:
   - Se o usuário NÃO pediu troca de roupa: Aplique 100% das tags do traje canônico oficial.
   - Se o usuário pediu novo traje (ex: "em roupa de banho"): Remova APENAS as tags das roupas originais (Camada 3). MANTENHA 100% das tags da Camada 1 e Camada 2 (rosto, cabelo, olhos, sobrancelha, brincos e características físicas canônicas).
   - Se o usuário ativou modificadores anatômicos ou de vestuário no painel (ex: transparência, tamanho de seios, mamilos): Adicione essas tags APENAS na CAMADA 5 (final do prompt), garantindo que não sobreponham nem alterem a identidade canônica das Camadas 1 e 2.

=============================================================================
REGRA RIGOROSA: PROMPT NEGATIVO DINÂMICO E CONTEXTUALIZADO (100% ADAPTATIVO)
=============================================================================
Você NUNCA deve entregar um prompt negativo estático ou padronizado. O prompt negativo DEVE ser gerado do zero adaptando-se estritamente aos parâmetros da requisição combinando 5 camadas:

1. CAMADA BASE DO MOTOR:
   - Se Pony SDXL: Inicie obrigatoriamente com `score_6, score_5, score_4, score_3, score_2, score_1, worst quality, low quality`.
   - Se Illustrious: Inicie obrigatoriamente com `bad quality, worst quality, low quality, lowres, jpeg artifacts`.

2. CAMADA DE ANTI-ESTILO (EXCLUSÃO CRÍTICA DE ESTILO OPOSTO):
   - Se Categoria = "Fotorealismo / Foto Realista": Adicione obrigatoriamente `anime, cartoon, drawing, illustration, 3d render, painting, artwork, CGI, fake skin, smooth skin, doll, plastic`.
   - Se Categoria = "Anime / Manga / Ilustração": Adicione obrigatoriamente `photorealistic, 3d render, photo, realistic skin, real life, volumetric rendering`.
   - Se Categoria = "Arte Digital / 3D Render": Adicione obrigatoriamente `2d, lineart, flat colors, photo, traditional painting`.
   - Se Categoria = "Pintura Clássica / Artística": Adicione obrigatoriamente `photo, 3d render, anime, CGI, digital vector`.

3. CAMADA DE ANATOMIA E SUJEITO:
   - Se Sujeito = "Paisagem" ou "Objeto": NUNCA inclua tags de anatomia humana no prompt positivo. No PROMPT NEGATIVO, adicione obrigatoriamente `human, person, woman, man, girl, boy, face, body, hands, legs, feet, crowd`.
   - Se Sujeito = "Feminino", "Masculino" ou "Criatura": Adicione tags anatômicas precisas baseadas no enquadramento (ex: se for Busto/Rosto, foque em `cross-eyed, bad eyes, deformed iris, bad mouth, bad teeth, bad face`; se for Corpo Todo, inclua `bad anatomy, bad hands, missing fingers, extra digit, fewer digits, fused fingers, bad feet, bad legs, extra limbs, disconnected limbs, deformed body`).

4. CAMADA DE ILUMINAÇÃO E COMPOSIÇÃO:
   - Negue artefatos ambientais com base no cenário e estilo escolhidos (`blurry, bad lighting, overexposed, underexposed, dark shadows, watermark, signature, text, banner, border, cropped, out of frame, cluttered background`).

5. CAMADA DE RATING / SENSUALIDADE:
   - Nível 1 ou 2 (SFW): Adicione obrigatoriamente `rating_questionable, rating_explicit, nsfw, nude, cleavage`.
   - Nível 3 ou 4 (Ecchi): Adicione obrigatoriamente `rating_explicit, nude, fully nude, nipple`.
=============================================================================
MOTOR 1: STABLE DIFFUSION LOCAL (ILLUSTRIOUS IA & PONY SDXL PARA COMFYUI / WEBUI)
=============================================================================
Seu objetivo é criar prompts hiper-detalhados em inglês e organizar a saída em formato estruturado.

### 📐 1.1 REGRAS POR FLUXO / MODELO DE IMAGEM:
* FLUXO ILLUSTRIOUS:
  - Sintaxe: Tags Booru limpas, descritivas e focadas em qualidade artística anime/ilustração.
  - Prefixos de Qualidade: masterpiece, best quality, highly detailed, aesthetic.

* FLUXO PONY SDXL:
  - Sintaxe: Tags pesadas reforçadas com marcadores de pontuação e rating estrito no início.
  - Prefixos de Qualidade OBRIGATÓRIOS: score_9, score_8_up, score_7_up, source_anime.
  - Rating conforme nível: rating_safe, rating_questionable ou rating_explicit.

---

### 🧠 1.2 PROTOCOLO DE SENSUALIDADE, VESTUÁRIO E ANATOMIA:
- Nível 1 - Seguro (SFW): Modéstia total. Trajes normais. rating_safe.
- Nível 2 - Menos Seguro: Poses atraentes, ajustes leves de caimento. rating_safe.
- Nível 3 - Ecchi Leve: Roupas de banho (biquíni), lingerie padrão, maiôs, trajes de academia. rating_questionable.
- Nível 4 - Ecchi: Micro trajes, transparências, decotes profundos. rating_questionable.
- Nível 5 - Picante: Nudez artística ou trajes mínimos explícitos. rating_explicit.
- Nível 6 - Dual (Com & Sem Censura):
  - VERSÃO A (Censurada): Adicione tags de censura: `censored, bar censorship, sticker censorship, mosaic censorship, heart stickers covering chest`.
  - VERSÃO B (Sem Censura): Remova as tags de censura, mantendo a cena em `rating_explicit`.

- AJUSTES ANATÔMICOS E DETALHES DE VESTUÁRIO (MAPEAMENTO PARA TAGS DANBOORU):
  - Tamanho dos Seios: Pequenos (`small breasts`), Médios (`medium breasts`), Grandes (`large breasts`), Volumosos (`huge breasts`).
  - Transparência no Traje: Adicione `see-through, transparent clothes, translucent fabric`.
  - Realçar Contorno dos Seios: Adicione `clothes pull, fabric hugging breasts, tight clothes, breast outline`.
  - Detalhes de Mamilos: Discretos (`nipple outline`), Eretos (`hard nipples, erect nipples through clothes`), Muito eretos (`prominent nipples, hard nipples showing through clothes`).

---

### 🧬 1.3 MODO SÉRIE CONSISTENTE (SE ATIVADO):
Se a entrada contiver "MODO SÉRIE CONSISTENTE ATIVADO":
1. Gere exatamente a quantidade de variações solicitada.
2. Mantenha os traços faciais, cabelo e identidade do personagem congelados.
3. Aplique a Rigidez da Consistência (Escala 1 a 5):
   - 1-2 (Flexível): Mesma face/cabelo; trajes e estilo podem flutuar.
   - 3 (Padrão): Face, cabelo e roupas mantidos idênticos; varie apenas cenário e pose.
   - 4-5 (Trava Total): Fixação absoluta de 100% de todos os atributos visuais.
4. Varie APENAS os elementos solicitados.

---

=============================================================================
MOTOR 2: GERADOR DE PROMPTS PARA IAS DE IMAGEM VIA WEB
=============================================================================
Se a entrada contiver "MODO GENERATOR IMAGEM WEB ATIVADO", adapte A SINTAXE E A ESTRUTURA do prompt em inglês para a plataforma escolhida:

### 🌐 2.1 REGRAS POR PLATAFORMA WEB:
1. 🍌 Nano Banana / Web Engine:
   - Sintaxe: Linguagem hiper-detalhada, focada na máxima fidelidade gráfica, ray tracing, profundidade de campo e renderização 8k.
2. 🎨 Midjourney v6.1:
   - Sintaxe: Palavras-chave em inglês descritivo. Adicione parâmetros no final (Ex: `--ar 16:9 --v 6.1 --stylize 250`).
3. ⚡ Flux.1 (Dev/Schnell):
   - Sintaxe: Descrição em linguagem natural fluida e contínua (estilo parágrafo narrativo).
4. 🔤 Ideogram 2.0:
   - Sintaxe: Foco na integração entre arte e tipografia. Coloque textos exatos entre aspas duplas no prompt.
5. 🖼️ DALL-E 3 / Bing Image Creator:
   - Sintaxe: Prompt narrativo amplo, expressivo e altamente conceitual.
6. 🎭 Leonardo.Ai / SeaArt:
   - Sintaxe: Tags de estilo com descrições estruturadas e iluminação ambiental.

---

=============================================================================
2.2 DIRETRIZES DE DESCRIÇÃO / LEGENDA PARA REDES SOCIAIS (FACEBOOK / INSTAGRAM)
=============================================================================
- A legenda em português DEVE SER CURTA, DIRETA E IMPACTANTE (no máximo 2 a 3 frases).
- Conecte o Nome/Sujeito com a Ação e o Cenário.
- REGRA CRÍTICA DE CTA (OBRIGATÓRIO): Toda legenda DEVE FINALIZAR OBRIGATORIAMENTE com uma Chamada para Ação (CTA) forte e persuasiva. NUNCA OMITA A CTA.

=============================================================================
FORMATOS OBRIGATÓRIOS DE SAÍDA (OUTPUT)
=============================================================================

--- SE FOR IMAGEM WEB (MOTOR 2) ---
### 🌐 PROMPT OTIMIZADO PARA WEB: [{PLATAFORMA_SELECIONADA}]
1. PROMPT (Inglês): [Prompt formatado com expansão canônica 100% no início]
2. DESCRIÇÃO REDES SOCIAIS (Português): [Legenda curta de 2 a 3 frases + CTA forte]
3. HASHTAGS: [Hashtags virais e relevantes]
💡 DICA DE APLICAÇÃO: [Instrução prática sobre como usar no site]

--- SE FOR IMAGEM LOCAL (MOTOR 1 - NÍVEIS 1 A 5) ---
### 🖼️ IMAGEM: [Nome/Tema do Sujeito] - [Fluxo Selecionado]
1. PROMPT (Inglês): [Prompt formatado com tags do fluxo e expansão canônica 100% no início]
2. DESCRIÇÃO FACEBOOK (Português): [Legenda curta de 2 a 3 frases + CTA forte]
3. HASHTAGS: [Hashtags relevantes]
4. PROMPT NEGATIVO: [Prompt negativo dinâmico de 5 camadas]

--- SE FOR IMAGEM LOCAL (MOTOR 1 - NÍVEL 6 - DUAL / CENSURA ESTRATÉGICA) ---
### 🖼️ IMAGEM: [Nome/Tema do Sujeito] - [Fluxo Selecionado] (VERSÃO DUAL)
1. PROMPT VERSÃO A (Censurada com Stickers/Barras): [Prompt com tags de censura]
2. PROMPT VERSÃO B (Sem Censura/Explícito): [Prompt sem tags de censura]
3. DESCRIÇÃO FACEBOOK: [Legenda curta de 2 a 3 frases + CTA forte]
4. HASHTAGS: [Hashtags]
5. PROMPT NEGATIVO: [Prompt negativo dinâmico de 5 camadas]

--- SE FOR SÉRIE CONSISTENTE LOCAL ---
### 🧬 SÉRIE CONSISTENTE: [Nome do Personagem]
#### 🖼️ VARIAÇÃO [Número]: [Resumo do elemento alterado]
- PROMPT (Inglês): [Prompt]
- PROMPT NEGATIVO: [Prompt Negativo Dinâmico]
"""

# ==============================================================================
# 3. FUNÇÕES AUXILIARES E GERENCIAMENTO DE DADOS
# ==============================================================================
def verificar_acesso_sheets(email):
    try:
        email_limpo = email.strip().lower()
        response = requests.get(
            APPS_SCRIPT_URL, 
            params={"email": email_limpo}, 
            timeout=15,
            allow_redirects=True
        )
        
        if response.status_code == 200:
            if "application/json" in response.headers.get("Content-Type", ""):
                dados = response.json()
                return dados.get("encontrado", False), dados.get("expiracao", "")
            else:
                st.error("⚠️ O servidor respondeu com formato inválido.")
            
    except requests.exceptions.Timeout:
        st.error("⚠️ O Google Sheets demorou a responder. Por favor, clique em ENTRAR novamente.")
    except Exception as e:
        st.error(f"Erro ao conectar com a base de dados: {e}")
        
    return False, ""


def carregar_config():
    config = {
        "chaves": {"Chave 1": "", "Chave 2": ""},
        "modelo_padrao": "gemini-3.6-flash",
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
    nome_sanitizado = re.sub(r'[^\w\-]', '_', nome_sujeito).lower() if nome_sujeito else "prompts"
    nome_arquivo = f"prompts_{nome_sanitizado}_{timestamp}.txt"
    caminho_completo = os.path.join(PASTA_RESULTADOS, nome_arquivo)
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(texto)
    return f"💾 Cópia salva no servidor: `{caminho_completo}`"


@st.cache_data(show_spinner=False)
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
                elif bloco_atual == "geral" or bloco_atual is None:
                    linhas_gerais.append(linha)

            resultado = list(dict.fromkeys(linhas_genero + linhas_gerais))
            if resultado:
                return resultado
        except Exception:
            pass

    return ["Opção Padrão 1", "Opção Padrão 2"]


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
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
                    if l.strip() and not l.startswith("#") and not l.startswith("[")
                ]
                opcoes.extend(linhas)
        except Exception:
            pass

    resultado = list(dict.fromkeys(opcoes))
    return resultado if resultado else ["Opção Padrão 1"]


def chamar_gemini_api(dados_personagem, client, modelo="gemini-3.6-flash"):
    if not client:
        return "❌ Erro: Cliente da API não inicializado. Verifique sua Chave API."

    def obter_str_limpa(chave, valor_padrao=""):
        val = dados_personagem.get(chave)
        return (val if val is not None else valor_padrao).strip()

    tipo_sujeito = obter_str_limpa("tipo_sujeito", "Feminino")
    is_objeto_ou_paisagem = tipo_sujeito in [
        "Paisagem / Cenário",
        "Objeto / Item",
    ]

    sensualidade = (
        "Inativo (Paisagem/Objeto)"
        if is_objeto_ou_paisagem
        else obter_str_limpa("sensualidade", "2 - Menos Seguro")
    )
    emocao = (
        "Não se aplica"
        if is_objeto_ou_paisagem
        else (obter_str_limpa("emocao") or "Nenhuma específica")
    )

    seios = "Não especificar" if is_objeto_ou_paisagem else obter_str_limpa("seios", "Padrão do Personagem / Não especificar")
    mamilos = "Não especificar" if is_objeto_ou_paisagem else obter_str_limpa("mamilos", "Não especificar")
    transparencia = "Não" if is_objeto_ou_paisagem else ("Sim" if dados_personagem.get("transparencia") else "Não")
    contorno = "Não" if is_objeto_ou_paisagem else ("Sim" if dados_personagem.get("contorno") else "Não")

    if dados_personagem.get("is_web_image"):
        prompt_usuario = f"""--- MODO GENERATOR IMAGEM WEB ATIVADO ---
Plataforma Alvo Solicitada: {obter_str_limpa('plataforma_web', 'Midjourney v6.1')}

Gere o prompt final otimizado em inglês e crie uma DESCRIÇÃO/LEGENDA CURTA EM PORTUGUÊS (COM CTA OBRIGATÓRIA NO FINAL) baseada nos detalhes da cena fornecidos:
- Sujeito / Tema Principal: {obter_str_limpa('nome')} (EXIGÊNCIA DE FIDELIDADE CANÔNICA 1:1: Se for um personagem existente, desmembre OBRIGATORIAMENTE em tags Booru detalhadas do Danbooru para rosto, cabelo, olhos, vestuário canônico completo e acessórios no início do prompt!)
- Tipo de Sujeito: {tipo_sujeito}
- Categoria de Arte: {obter_str_limpa('categoria_arte', 'Anime / Manga / Ilustração')}
- Nível de Sensualidade: {sensualidade}
- Detalhes Anatômicos / Vestuário:
  * Tamanho dos Seios: {seios}
  * Transparência no Traje: {transparencia}
  * Realçar Contorno dos Seios: {contorno}
  * Estilo dos Mamilos: {mamilos}
- Orientação (Ratio): {obter_str_limpa('orientacao')}
- Enquadramento: {obter_str_limpa('enquadramento')}
- Ação do Sujeito / Estado: {obter_str_limpa('acao')}
- Estilo Visual Específico: {obter_str_limpa('estilo')}
- Expressão / Emoção: {emocao}
- Pose / Posição / Ângulo: {obter_str_limpa('pose')}
- Cenário / Ambiente: {obter_str_limpa('cenario')}
- Iluminação: {obter_str_limpa('iluminacao')}
- Efeitos Especiais: {obter_str_limpa('efeitos')}
- Texto na Imagem (Tipografia Opcional): {obter_str_limpa('texto_web', 'Nenhum')}
"""
    else:
        prompt_usuario = f"""Gere os prompts de imagem em inglês e uma DESCRIÇÃO/LEGENDA CURTA EM PORTUGUÊS (COM CTA OBRIGATÓRIA NO FINAL) para redes sociais conectando os detalhes abaixo:

- Nome / Sujeito: {obter_str_limpa('nome')} (EXIGÊNCIA DE FIDELIDADE CANÔNICA 1:1: Se for um personagem existente, desmembre OBRIGATORIAMENTE em tags Booru detalhadas do Danbooru para rosto, cabelo, olhos, vestuário canônico completo e acessórios no início do prompt!)
- Fluxo Base: {obter_str_limpa('fluxo', 'Illustrious')}
- Tipo de Sujeito: {tipo_sujeito}
- Categoria de Arte: {obter_str_limpa('categoria_arte', 'Anime / Manga / Ilustração')}
- Nível de Sensualidade: {sensualidade}
- Detalhes Anatômicos / Vestuário:
  * Tamanho dos Seios: {seios}
  * Transparência no Traje: {transparencia}
  * Realçar Contorno dos Seios: {contorno}
  * Estilo dos Mamilos: {mamilos}
- Orientação (Ratio): {obter_str_limpa('orientacao')}
- Enquadramento: {obter_str_limpa('enquadramento')}
- Ação do Sujeito / Estado: {obter_str_limpa('acao')}
- Estilo Visual Específico: {obter_str_limpa('estilo')}
- Expressão / Emoção: {emocao}
- Pose / Posição / Ângulo: {obter_str_limpa('pose')}
- Cenário / Ambiente: {obter_str_limpa('cenario')}
- Iluminação: {obter_str_limpa('iluminacao')}
- Efeitos Especiais: {obter_str_limpa('efeitos')}
"""

        if dados_personagem.get("is_serie"):
            alvos = obter_str_limpa("variaveis_alvo_str")
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
                system_instruction=system_instruction,
                temperature=0.7,
                # tools=[{"google_search": {}}],  # Ativa a pesquisa web para validação de cânone
            ),
        )
        if response and hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if hasattr(cand, "finish_reason") and str(cand.finish_reason) == "SAFETY":
                return "⚠️ A requisição foi bloqueada pelos filtros de segurança da API Gemini."
        
        if response and hasattr(response, "text") and response.text is not None:
            return response.text
        else:
            return "⚠️ A API retornou uma resposta vazia."
    except Exception as e:
        erro_str = str(e)
        if "503" in erro_str or "UNAVAILABLE" in erro_str or "high demand" in erro_str:
            return "⚠️ Você está usando API gratuita. O jeito é esperar um pouco e tentar de novo daqui uns 10 segundos."
        return f"❌ Erro na comunicação com o modelo '{modelo}': {erro_str}"


def st_campo_hibrido(label, placeholder, opcoes, key_prefix, disabled=False):
    # Alinhamento vertical na base para alinhar a caixa de texto com o dropdown de Presets
    col_txt, col_drop = st.columns([0.65, 0.35], vertical_alignment="bottom")

    def ao_selecionar_preset():
        sel = st.session_state.get(f"{key_prefix}_drop")
        if sel and sel not in ["Presets...", "Digite manualmente..."]:
            st.session_state[f"{key_prefix}_txt"] = sel
            st.session_state[f"{key_prefix}_drop"] = "Presets..."

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
            label_visibility="collapsed",
        )
    return val


def autocompletar_campos(prefixo, is_web=False):
    tipo_sujeito_atual = st.session_state.get(f"{prefixo}_tipo_sujeito", "Feminino")
    genero_ref = "masculino" if tipo_sujeito_atual == "Masculino" else "feminino"
    is_obj_or_land = tipo_sujeito_atual in ["Paisagem / Cenário", "Objeto / Item"]

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
        if campo == "emocao" and is_obj_or_land:
            continue

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

        sensualidade = st.select_slider(
            "Sensualidade:",
            options=opcoes_sensualidade,
            value="2 - Menos Seguro",
            disabled=is_obj_or_land,
            key=f"{prefixo}_sensualidade",
        )

        # Painel de Ajustes de Vestuário e Anatomia
        with st.expander("👙 Ajustes de Vestuário e Anatomia", expanded=not is_obj_or_land):
            seios = st.selectbox(
                "Tamanho dos Seios:",
                opcoes_seios,
                disabled=is_obj_or_land,
                key=f"{prefixo}_seios",
            )
            mamilos = st.selectbox(
                "Detalhes dos Mamilos:",
                opcoes_mamilos,
                disabled=is_obj_or_land,
                key=f"{prefixo}_mamilos",
            )
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                transparencia = st.checkbox(
                    "Transparência no Traje",
                    disabled=is_obj_or_land,
                    key=f"{prefixo}_transparencia",
                )
            with col_v2:
                contorno = st.checkbox(
                    "Realçar Contorno dos Seios",
                    disabled=is_obj_or_land,
                    key=f"{prefixo}_contorno",
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
            args=(prefixo, is_web),
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
        "sensualidade": sensualidade,
        "seios": seios,
        "mamilos": mamilos,
        "transparencia": transparencia,
        "contorno": contorno,
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
            dados, 
            client, 
            modelo=modelo_selecionado,
            usar_busca_web=st.session_state.get("usar_busca_web", False)
        )
                    st.session_state[f"{prefixo}_resultado"] = resultado
                except Exception as e:
                    st.error(f"❌ Erro ao inicializar cliente: {str(e)}")

    if st.session_state.get(f"{prefixo}_resultado"):
        st.write("")
        st.markdown("---")
        st.write("")
        
        st.markdown("### 📝 Resultado:")
        st.code(st.session_state[f"{prefixo}_resultado"], language="markdown")

        st.write("")
        
        nome_sanitizado = re.sub(r'[^\w\-]', '_', nome).lower() if nome else 'gerado'
        nome_arquivo_dl = f"prompts_{nome_sanitizado}.txt"
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
                email_limpo = email_input.strip().lower()
                
                com_acesso, data_exp = verificar_acesso_sheets(email_limpo)
                if com_acesso:
                    st.session_state.autenticado = True
                    st.session_state.user_email = email_limpo
                    st.session_state.expiracao = data_exp
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
            "gemini-3.5-flash",
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
        usar_busca_web = st.checkbox(
    "🌐 Ativar Pesquisa Web em Tempo Real (Google Grounding)",
    value=False,key="usar_busca_web"
    help="⚠️ REQUER CHAVE DE API PAGA (Pay-as-you-go). Se estiver usando a cota gratuita do Google AI Studio, esta opção causará o erro 429 RESOURCE_EXHAUSTED."
)

if usar_busca_web:
    st.caption("ℹ️ *Apenas para chaves com faturamento ativo. Melhora a precisão de cores e cânone.*")

        if st.button("💾 Salvar Configurações"):
    for slot in st.session_state.chaves_api.keys():
        s_key = f"input_key_{slot}"
        if s_key in st.session_state:
            st.session_state.chaves_api[slot] = st.session_state[s_key].strip()
            
    # Salva o modelo e o estado da busca web
    salvar_config(st.session_state.chaves_api, modelo_selecionado, usar_busca_web)
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
