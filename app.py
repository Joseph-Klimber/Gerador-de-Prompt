import streamlit as st
import os
import random
import time
from google import genai

# Configuração da página
st.set_page_config(page_title="Gerador de Prompts", page_icon="🎨", layout="wide")

st.title("🌸 PAINEL COMPLETO DE GERADOR DE PROMPTS (LOCAL & WEB)")

# ===========================================================================
# LEITURA DE ARQUIVOS DE TEXTO (LISTAS)
# ===========================================================================
PASTA_LISTAS = os.path.dirname(__file__)

def ler_arquivo_txt(nome_arquivo):
    caminho = os.path.join(PASTA_LISTAS, nome_arquivo)
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return [linha.strip() for linha in f if linha.strip()]
        except Exception:
            return []
    return []

# ===========================================================================
# SIDEBAR: CONFIGURAÇÕES DA API GEMINI
# ===========================================================================
st.sidebar.header("🔑 Configuração da API Gemini")

api_key_input = st.sidebar.text_input(
    "Chave API do Gemini:", 
    type="password", 
    help="Cole sua API Key do Google AI Studio aqui."
)

modelo_selecionado = st.sidebar.selectbox(
    "🤖 Modelo:",
    options=['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-flash']
)

# ===========================================================================
# LÓGICA DE INTERFACE COM STREAMLIT (ABAS)
# ===========================================================================
opcoes_sujeito = ["Feminino", "Masculino", "Objeto / Item", "Paisagem / Cenário", "Criatura / Monstro / Androide"]
opcoes_arte = ["Anime / Manga / Ilustração", "Fotorealismo / Foto Realista", "Arte Digital / 3D Render", "Pintura Clássica / Artística"]

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "👤 Personagem 1", "👤 Personagem 2", "👤 Personagem 3", "🧬 Série Consistente", "🌐 Imagem Web"
])

def renderizar_formulario_padrao(prefixo):
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_sujeito = st.selectbox("Tipo de Sujeito:", opcoes_sujeito, key=f"{prefixo}_tipo")
        nome = st.text_input("Nome / Sujeito:", placeholder="Ex: Android 18", key=f"{prefixo}_nome")
        fluxo = st.selectbox("Fluxo Base:", ["Illustrious", "Pony SDXL"], key=f"{prefixo}_fluxo")
        categoria_arte = st.selectbox("Categoria de Arte:", opcoes_arte, key=f"{prefixo}_cat")
        sensualidade = st.slider("Sensualidade (1-6):", 1, 6, 6, key=f"{prefixo}_sens")
        orientacao = st.selectbox("Orientação (Ratio):", ["Vertical (Portrait 9:16)", "Horizontal (Landscape 16:9)", "Quadrado (Square 1:1)"], key=f"{prefixo}_orient")
        enquadramento = st.selectbox("Enquadramento:", ["Corpo todo (Full body)", "Meio corpo (Half body)", "Busto (Bust shot)"], key=f"{prefixo}_enq")

    with col2:
        acao = st.text_input("Ação / Estado:", placeholder="Ex: em pose de combate", key=f"{prefixo}_acao")
        estilo = st.text_input("Estilo Visual:", placeholder="Ex: estilo Makoto Shinkai", key=f"{prefixo}_estilo")
        emocao = st.text_input("Expressão:", placeholder="Ex: olhar frio", key=f"{prefixo}_emocao")
        pose = st.text_input("Pose / Posição:", placeholder="Ex: flutuando no ar", key=f"{prefixo}_pose")
        cenario = st.text_input("Ambiente/Cenário:", placeholder="Ex: laboratório futurista", key=f"{prefixo}_cenario")
        iluminacao = st.text_input("Iluminação:", placeholder="Ex: neon brilhante", key=f"{prefixo}_ilum")
        efeitos = st.text_input("Efeitos Especiais:", placeholder="Ex: faíscas elétricas", key=f"{prefixo}_efeitos")

    return {
        "nome": nome, "fluxo": fluxo, "tipo_sujeito": tipo_sujeito, "categoria_arte": categoria_arte,
        "sensualidade": sensualidade, "orientacao": orientacao, "enquadramento": enquadramento,
        "acao": acao, "estilo": estilo, "emocao": emocao, "pose": pose, "cenario": cenario,
        "iluminacao": iluminacao, "efeitos": efeitos
    }

# Renderiza as 3 primeiras abas
with aba1: dados1 = renderizar_formulario_padrao("p1")
with aba2: dados2 = renderizar_formulario_padrao("p2")
with aba3: dados3 = renderizar_formulario_padrao("p3")

# Aba 4: Série Consistente
with aba4:
    st.subheader("🧬 Configurações de Variação Dinâmica")
    col_chk, col_cfg = st.columns(2)
    with col_chk:
        chk_cenario = st.checkbox("Variar Cenário", value=True)
        chk_iluminacao = st.checkbox("Variar Iluminação")
        chk_estilo = st.checkbox("Variar Estilo Visual")
        chk_acao = st.checkbox("Variar Ação")
        chk_pose = st.checkbox("Variar Pose")
    with col_cfg:
        total_var = st.selectbox("Total de Imagens:", [3, 5, 8, 10], index=1)
        rigidez = st.slider("Rigidez do Prompt (1-5):", 1, 5, 3)
    
    st.divider()
    dados4 = renderizar_formulario_padrao("serie")
    dados4.update({"chk_cenario": chk_cenario, "chk_iluminacao": chk_iluminacao, "chk_estilo": chk_estilo, "chk_acao": chk_acao, "chk_pose": chk_pose, "total_variacoes": total_var, "rigidez": rigidez})

# Aba 5: Imagem Web
with aba5:
    plataforma_web = st.selectbox("Plataforma Web:", ["🍌 Nano Banana / Web Engine", "🎨 Midjourney v6.1", "⚡ Flux.1 (Dev/Schnell)", "🔤 Ideogram 2.0", "🖼️ DALL-E 3 / Bing"])
    texto_web = st.text_input("Texto na Imagem (Opcional):", placeholder="Ex: Palavra ou frase na cena")
    st.divider()
    dados5 = renderizar_formulario_padrao("web")
    dados5.update({"plataforma_web": plataforma_web, "texto_web": texto_web, "is_web_image": True})

# Lista com os dicionários para captura
lista_dados_abas = [dados1, dados2, dados3, dados4, dados5]

# ===========================================================================
# BOTÃO DE AÇÃO E CHAMADA DO GEMINI
# ===========================================================================
st.divider()

if st.button("🚀 GERAR PROMPTS COM GEMINI", type="primary", use_container_width=True):
    if not api_key_input:
        st.error("❌ Por favor, informe uma Chave API do Gemini na barra lateral esquerda.")
    else:
        aba_atual_idx = 0 # Pode ser ajustado conforme controle de abas do Streamlit
        dados_execucao = lista_dados_abas[aba_atual_idx]
        
        with st.spinner("⏳ Gerando prompt com inteligência artificial..."):
            try:
                client = genai.Client(api_key=api_key_input)
                
                # Monta a instrução para o Gemini
                prompt_sistema = f"""
                Você é um Engenheiro de Prompts especialista em Inteligência Artificial geradora de imagens.
                Com base nos parâmetros abaixo, crie um prompt em INGLÊS perfeitamente otimizado:
                - Sujeito: {dados_execucao['nome']} ({dados_execucao['tipo_sujeito']})
                - Categoria de Arte: {dados_execucao['categoria_arte']}
                - Enquadramento: {dados_execucao['enquadramento']}
                - Orientação: {dados_execucao['orientacao']}
                - Ação: {dados_execucao['acao']}
                - Estilo: {dados_execucao['estilo']}
                - Expressão: {dados_execucao['emocao']}
                - Pose: {dados_execucao['pose']}
                - Cenário: {dados_execucao['cenario']}
                - Iluminação: {dados_execucao['iluminacao']}
                - Efeitos: {dados_execucao['efeitos']}
                
                Retorne o prompt final estruturado de forma profissional.
                """
                
                response = client.models.generate_content(
                    model=modelo_selecionado,
                    contents=prompt_sistema
                )
                
                st.success("✅ Prompt Gerado com Sucesso!")
                st.code(response.text, language="text")
                
            except Exception as e:
                st.error(f"⚠️ Ocorreu um erro ao chamar o Gemini: {e}")