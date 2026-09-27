"""Gerador de prompt 1.0 — Etapa 3: cockpit Acolher→Melhorar→Modificar→Auditar→Baixar (texto) + Visão pronta
PRD/TRD/Fluxo/Briefing/Schema/Plano travados em GERADOR_PROMPT_1.0__AntesDeCodar/*__ENTREVISTA.md
"""
import pathlib
import sys
import html
ROOT = pathlib.Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Prompt Studio Cockpit | Engenharia Preditiva de Prompts IA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Design tokens (Briefing) ---
css_path = pathlib.Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# --- Imports ---
from src.auth import verificar_acesso_sheets
from src.config_store import carregar_config, salvar_config
from src.crypto import fernet_disponivel, mascarar_email, OPCOES_GEMINI_3, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO
from src.text_engines import (
    BANCO_DE_MOTORES, OPCOES_DESTINO, OPCOES_SENSUALIDADE,
    SYS_GERADOR_PREPROMPT, SYS_COMPOSITOMETRO, SYS_MESTRE_CORE,
    _chamar_motor_texto, _msg_erro_amigavel, _msg_erro_diagnostico,
    _build_gemini_config, _ps_markup_origin, parse_json_ia,
)
from src.vision import _chamar_motor_visao

def _get_secret(name: str):
    try:
        return st.secrets[name]
    except Exception:
        return None

PS_FERNET_KEY = _get_secret("PS_FERNET_KEY")
APPS_SCRIPT_URL = _get_secret("APPS_SCRIPT_URL")

# Estado auth
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "expiracao" not in st.session_state:
    st.session_state["expiracao"] = ""

# ── Sidebar: Centro de Conexão ──
with st.sidebar:
    st.markdown("### ⚡ Prompt Studio")
    if st.session_state["autenticado"]:
        st.caption(f"Logado: {mascarar_email(st.session_state['user_email'])}")
        if not fernet_disponivel():
            st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY.")
        st.markdown("---")
        st.markdown("#### 🔌 Centro de Conexão")
        st.caption("2 motores isolados — mesma chave pode ser usada nas duas vias (cotas separadas).")
        _cfg = carregar_config(st.session_state["user_email"])
        chave_visao_input = st.text_input("Chave Visão (BYOK)", value=_cfg.get("chaves", {}).get("Chave Visao", ""), type="password", key="input_key_visao")
        modelo_visao_sel = st.selectbox("Modelo Visão", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_visao", MODELO_VISAO_PADRAO)) if _cfg.get("modelo_visao") in OPCOES_GEMINI_3 else 0, key="modelo_visao_select")
        chave_texto_input = st.text_input("Chave Texto (BYOK)", value=_cfg.get("chaves", {}).get("Chave Texto", ""), type="password", key="input_key_texto")
        modelo_texto_sel = st.selectbox("Modelo Texto", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_texto", MODELO_TEXTO_PADRAO)) if _cfg.get("modelo_texto") in OPCOES_GEMINI_3 else 0, key="modelo_texto_select")
        if st.button("🔌 Conectar Motores Isolados", use_container_width=True, type="primary"):
            if not fernet_disponivel():
                st.error("Criptografia desabilitada — configure PS_FERNET_KEY antes de salvar.")
            elif modelo_visao_sel not in OPCOES_GEMINI_3 or modelo_texto_sel not in OPCOES_GEMINI_3:
                st.error("Modelo inválido — use 3.5/3.6/3.7-flash (abaixo de 3.X é obsoleto).")
            else:
                dados = {"chaves": {"Chave Visao": chave_visao_input.strip(), "Chave Texto": chave_texto_input.strip()}, "modelo_visao": modelo_visao_sel, "modelo_texto": modelo_texto_sel, "modelo_padrao": modelo_texto_sel}
                ok, msg = salvar_config(dados, email=st.session_state["user_email"])
                if ok:
                    st.success("Motores conectados com sucesso!")
                else:
                    st.warning(msg or "Erro ao salvar na nuvem — cópia local salva.")
        st.markdown("---")
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["user_email"] = ""
            st.session_state["expiracao"] = ""
            st.rerun()
    else:
        st.caption("Faça login com o e-mail da compra.")

# ── Tela 1: Página de Entrada (Login) ──
if not st.session_state["autenticado"]:
    if not fernet_disponivel():
        st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY em .streamlit/secrets.toml (Etapa 1.3).")
    st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Pare de lutar contra a IA.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Transforme ideia vaga em prompt pronto para ComfyUI/Midjourney — qualidade suprema sem inventar, menos tentativas.</p>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;"><span class="byok-badge">🔌 BYOK — suas chaves, suas cotas, nada salvo no servidor</span></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"uma elfa na escadaria"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">score_9, score_8_up, source_anime, 1girl, solo, long silver hair, green eyes, ornate armor, standing on stone stairs, volumetric light, highly detailed...</div>', unsafe_allow_html=True)
        img1 = pathlib.Path(__file__).parent / "assets" / "elfa.jpg"
        try:
            if img1.exists():
                st.image(str(img1), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">📚</div>', unsafe_allow_html=True)
            st.caption("elfa.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"carro esportivo futurista"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">photorealistic, ultra detailed, sports car, metallic paint, studio lighting, 85mm lens, shallow depth of field, 8k...</div>', unsafe_allow_html=True)
        img2 = pathlib.Path(__file__).parent / "assets" / "carro.jpg"
        try:
            if img2.exists():
                st.image(str(img2), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#059669 0%,#2563eb 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">📸</div>', unsafe_allow_html=True)
            st.caption("carro.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="plan-container">', unsafe_allow_html=True)
    st.markdown("### Escolha seu plano")
    st.caption("Pagamento fora do app — compra na Kiwify libera seu e-mail na planilha.")
    c1, c2, c3 = st.columns(3)
    _KIWIFY_FALLBACK = {
        "LINK_KIWIFY_15_DIAS": "https://pay.kiwify.com.br/MXVL98k",
        "LINK_KIWIFY_30_DIAS": "https://pay.kiwify.com.br/dyfEGe5",
        "LINK_KIWIFY_90_DIAS": "https://pay.kiwify.com.br/xo0m3rF",
    }
    def _kiwify_link(days_key):
        v = _get_secret(days_key)
        if v and "PLACEHOLDER" not in str(v) and str(v).strip() not in ("", "#"):
            return v
        return _KIWIFY_FALLBACK.get(days_key, "#")
    with c1:
        st.markdown("**15 dias**")
        st.link_button("Comprar 15 dias", _kiwify_link("LINK_KIWIFY_15_DIAS"), use_container_width=True)
    with c2:
        st.markdown("**30 dias**")
        st.link_button("Comprar 30 dias", _kiwify_link("LINK_KIWIFY_30_DIAS"), use_container_width=True, type="primary")
    with c3:
        st.markdown("**90 dias**")
        st.link_button("Comprar 90 dias", _kiwify_link("LINK_KIWIFY_90_DIAS"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Entrar no Sistema")
    st.caption("Use o e-mail da compra na Kiwify. Validação e prazo na planilha (sem senha).")
    email_input = st.text_input("E-mail da compra", placeholder="seu@email.com", key="login_email")
    if st.button("Entrar no Sistema", type="primary", use_container_width=True):
        email = (email_input or "").strip()
        if not email:
            st.error("Digite seu e-mail.")
        elif "@" not in email:
            st.error("E-mail inválido — verifique o e-mail da compra.")
        else:
            with st.spinner("Verificando acesso..."):
                ok, exp, erro = verificar_acesso_sheets(email)
            if ok:
                st.session_state["autenticado"] = True
                st.session_state["user_email"] = email.lower()
                st.session_state["expiracao"] = exp
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error(erro or "E-mail não encontrado — verifique o e-mail da compra.")
    st.caption("LGPD: Imagens com pessoas são processadas apenas para extração e descartadas. Nada é salvo no servidor.")
    st.stop()

# ── Tela 2: Cockpit Único (Etapa 3 + 4) ──
st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
st.markdown('<h1 class="ps-title">Sua Ideia. Seu Motor. Controle Total.</h1>', unsafe_allow_html=True)
st.markdown('<div class="ps-slogan">A porta é nossa, mas as chaves são suas.</div>', unsafe_allow_html=True)

# State Sync — evita StreamlitAPIException ao alterar widget após criação
for _pk, _rk in [
    ("_pending_ck_ideia_input", "ck_ideia_input"),
    ("_pending_ck_preprompt_editado", "ck_preprompt_editado"),
    ("_pending_img_suj", "img_suj"),
    ("_pending_img_cen", "img_cen"),
    ("_pending_img_act", "img_act"),
    ("_pending_img_ilu", "img_ilu"),
    ("_pending_img_est", "img_est"),
]:
    if _pk in st.session_state:
        st.session_state[_rk] = st.session_state.pop(_pk)

# Init chaves ancoradas
if "ck_ideia_input" not in st.session_state: st.session_state.ck_ideia_input = ""
if "ck_preprompt_editado" not in st.session_state: st.session_state.ck_preprompt_editado = ""
if "img_suj" not in st.session_state: st.session_state.img_suj = ""
if "img_cen" not in st.session_state: st.session_state.img_cen = ""
if "img_act" not in st.session_state: st.session_state.img_act = ""
if "img_ilu" not in st.session_state: st.session_state.img_ilu = ""
if "img_est" not in st.session_state: st.session_state.img_est = ""
if "ck_estilo_conversao" not in st.session_state: st.session_state.ck_estilo_conversao = "Manter Estilo Original"
if "ck_foco_contexto" not in st.session_state: st.session_state.ck_foco_contexto = "Harmônico (Preencher/Embelezar)"
if "ck_sens_slider" not in st.session_state: st.session_state.ck_sens_slider = OPCOES_SENSUALIDADE[1]

if not fernet_disponivel():
    st.warning("⚠️ Conecte suas chaves na barra lateral para ativar os motores. (Criptografia desabilitada sem PS_FERNET_KEY)")
else:
    _cfg_check = carregar_config(st.session_state["user_email"])
    if not _cfg_check.get("chaves", {}).get("Chave Visao") and not _cfg_check.get("chaves", {}).get("Chave Texto"):
        st.info("💡 Conecte suas chaves na barra lateral para ativar os motores.")

# --------------------------------------------------------------------------
# PASSO 1: A Ideia
# --------------------------------------------------------------------------
st.markdown("### 1️⃣ Passo 1: A Sua Ideia (A Narrativa Visual)")
st.caption("O ponto de partida. Descreva o que imagina ou veja a caixa preencher-se usando o Passo 2.")
st.text_area("Insira a sua Ideia:", key="ck_ideia_input", height=140, label_visibility="collapsed")
if st.button("🗑️ Limpar Ideia", use_container_width=False):
    for k in ["ck_img_parametros", "ck_preprompt", "ck_preprompt_editado", "ck_diagnostico", "ck_prompt_final", "ck_sugestoes_marcadas",
              "ck_ideia_input", "img_suj", "img_cen", "img_act", "img_ilu", "img_est",
              "_pending_ck_ideia_input", "_pending_ck_preprompt_editado", "_pending_img_suj", "_pending_img_cen", "_pending_img_act", "_pending_img_ilu", "_pending_img_est"]:
        st.session_state.pop(k, None)
    st.session_state["_pending_ck_ideia_input"] = ""
    st.session_state["_pending_ck_preprompt_editado"] = ""
    st.session_state["_pending_img_suj"] = ""
    st.session_state["_pending_img_cen"] = ""
    st.session_state["_pending_img_act"] = ""
    st.session_state["_pending_img_ilu"] = ""
    st.session_state["_pending_img_est"] = ""
    st.rerun()

# --------------------------------------------------------------------------
# PASSO 2: Referência Óptica (Imagem Opcional) — Etapa 4 pronta, já incluída
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 2️⃣ Passo 2: Referência Óptica (Opcional)")
st.caption("Sem inspiração para escrever? Faça upload de uma imagem. A Via de Visão extrairá os micro-detalhes para o Passo 1.")
col_img1, col_img2 = st.columns([4, 6])
with col_img1:
    img_file = st.file_uploader("Upload de Referência", type=["png", "jpg", "jpeg", "webp"], key="ck_img_uploader", label_visibility="collapsed")
with col_img2:
    st.write(" ")
    btn_ler = st.button("👁️ Extrair Imagem (Motor de Visão)", use_container_width=True)
if btn_ler:
    if not img_file: st.warning("Selecione uma imagem primeiro.")
    else:
        with st.spinner("Analisando matriz óptica com Varredura Ultra-Densa..."):
            try:
                modelo_base = st.session_state.get("modelo_visao_select", MODELO_VISAO_PADRAO)
                estilo_conversao = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                sens_escolhida = st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1])
                res = _chamar_motor_visao(img_file, estilo_conversao, sens_escolhida, modelo_base)
                if res["tipo"] == "json":
                    st.session_state["ck_img_parametros"] = res["dados"]
                    st.session_state["_pending_img_suj"] = res["dados"].get("sujeito", "")
                    st.session_state["_pending_img_cen"] = res["dados"].get("cenario", "")
                    st.session_state["_pending_img_act"] = res["dados"].get("acao", "")
                    st.session_state["_pending_img_ilu"] = res["dados"].get("iluminacao", "")
                    st.session_state["_pending_img_est"] = res["dados"].get("estilo_camera", "")
                    ideia_extraida = f"Sujeito: {res['dados'].get('sujeito','')}\n\nAção: {res['dados'].get('acao','')}\n\nCenário: {res['dados'].get('cenario','')}\n\nIluminação: {res['dados'].get('iluminacao','')}\n\nEstilo: {res['dados'].get('estilo_camera','')}"
                    st.session_state["_pending_ck_ideia_input"] = ideia_extraida
                else:
                    st.session_state["_pending_ck_ideia_input"] = res["texto"]
                    st.session_state.pop("ck_img_parametros", None)
                st.session_state.pop("ck_preprompt", None)
                st.rerun()
            except Exception as e: st.error(_msg_erro_amigavel(e))
if st.session_state.get("ck_img_parametros"):
    with st.expander("🔬 Detalhador Pericial Extraído (Editável)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("👤 Sujeito:", key="img_suj", height=150)
            st.text_area("🏞️ Cenário:", key="img_cen", height=150)
        with c2:
            st.text_area("🏃 Ação:", key="img_act", height=100)
            st.text_area("💡 Iluminação:", key="img_ilu", height=100)
            st.text_area("📷 Estilo:", key="img_est", height=100)
        if st.button("🔄 Atualizar Caixa da Ideia com estas edições", use_container_width=True):
            nova_ideia = f"Sujeito: {st.session_state.img_suj}\n\nAção: {st.session_state.img_act}\n\nCenário: {st.session_state.img_cen}\n\nIluminação: {st.session_state.img_ilu}\n\nEstilo: {st.session_state.img_est}"
            st.session_state["_pending_ck_ideia_input"] = nova_ideia
            st.rerun()

# --------------------------------------------------------------------------
# PASSO 3: Modificadores
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 3️⃣ Passo 3: Modificadores Globais")
st.caption("ℹ️ *Aviso: Estes filtros guiam a geração do seu prompt final. (Também alteram a leitura caso envie uma Imagem no Passo 2).*")
with st.container(border=True):
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: estilo_conversao = st.selectbox("Estilo de Arte:", ["Manter Estilo Original", "📸 Converter para Fotorrealismo", "🎨 Converter para Anime"], key="ck_estilo_conversao")
    with col_m2: foco_contexto = st.selectbox("Foco e Contexto:", ["Harmônico (Preencher/Embelezar)", "Literal (Direto, Sem Floreios)"], key="ck_foco_contexto")
    with col_m3: sens_escolhida = st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key="ck_sens_slider", value=st.session_state.get("ck_sens_slider", OPCOES_SENSUALIDADE[1]))

# --------------------------------------------------------------------------
# PASSO 4: Rascunho & Validação (Opcionais Prévios)
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 4️⃣ Passo 4: Rascunho & Validação (Opcional)")
col_b1, col_b2 = st.columns(2)
with col_b1: btn_pre = st.button("👁️ Rascunhar Cena (Via Motor de Texto)", use_container_width=True)
with col_b2: btn_ava = st.button("🔍 Auditar no Compositômetro (Raio-X)", use_container_width=True)
if btn_pre:
    if not st.session_state.ck_ideia_input.strip(): st.warning("Escreva a sua Ideia no Passo 1.")
    else:
        with st.spinner("Desenhando a cena com o Motor de Texto..."):
            try:
                _estilo = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                p = f"IDEIA:\n{st.session_state.ck_ideia_input}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sens_escolhida}']"
                if "Fotorrealismo" in _estilo:
                    p += "\n[MODIFICADOR ESTILO — CONVERTER PARA FOTORREALISMO]: Reescreva TODA a cena como FOTOGRAFIA REAL. Substitua 'anime, ilustração, desenho, traço' por 'foto fotorrealista, pele real, textura fotográfica'. PROÍBA vocabulário anime/cartoon/ilustração."
                elif "Anime" in _estilo:
                    p += "\n[MODIFICADOR ESTILO — CONVERTER PARA ANIME 2D]: Reescreva TODA a cena como ILUSTRAÇÃO ANIME 2D. Substitua 'foto, câmera de smartphone, lente 26mm, fotorrealista' por 'ilustração anime, traço anime limpo, cel shading, linhas nítidas, anime style'. PROÍBA 'foto, smartphone, lente, fotorrealista'."
                if "Literal" in foco_contexto: p += "\n[AGENTE LITERAL]: Seja 100% fiel, sem floreios estéticos inúteis."
                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
                txt, prov = _chamar_motor_texto(SYS_GERADOR_PREPROMPT, p, modelo_gemini=modelo_base)
                st.session_state["ck_ideia_hist_fix"] = st.session_state.ck_ideia_input
                st.session_state["ck_preprompt"] = txt
                st.session_state["_pending_ck_preprompt_editado"] = txt
                st.rerun()
            except Exception as e: st.error(_msg_erro_amigavel(e))
if btn_ava:
    if not st.session_state.ck_ideia_input.strip(): st.warning("Escreva a sua Ideia no Passo 1.")
    else:
        with st.spinner("Raio-X em andamento com o Motor de Texto..."):
            try:
                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
                txt, prov = _chamar_motor_texto(SYS_COMPOSITOMETRO, f"AVALIE:\n{st.session_state.ck_ideia_input}", modelo_gemini=modelo_base)
                diag = parse_json_ia(txt)
                if not diag: st.error("⚠️ Erro de formato no Raio-X. Tente novamente.")
                else: st.session_state["ck_diagnostico"] = diag; st.rerun()
            except Exception as e: st.error(_msg_erro_amigavel(e))
if st.session_state.get("ck_preprompt"):
    st.markdown("<div class='ps-legend'><span><span class='ps-user-word'>Ideia Original</span></span> • <span><span class='ps-ai-word'>Ajuste da IA</span></span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ps-preprompt'>{_ps_markup_origin(st.session_state['ck_preprompt'], st.session_state.get('ck_ideia_hist_fix', ''))}</div>", unsafe_allow_html=True)
    st.text_area("Ajuste fino do Rascunho (Esta caixa substituirá a Ideia para o Motor Final):", key="ck_preprompt_editado", height=130)
diag = st.session_state.get("ck_diagnostico")
if diag:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        def _bdg(s): return ("comp-green","✓") if s in ["Definido","Presente"] else ("comp-amber","!") if s in ["Vago","Estática"] else ("comp-blue","⚙️")
        for col, key, label in zip([c1,c2,c3,c4,c5], ["sujeito_status","acao_status","cenario_status","iluminacao_status","camera_status"], ["Sujeito","Ação","Cenário","Luz","Câmera"]):
            cl, ic = _bdg(diag.get(key, ""))
            col.markdown(f"<div class='comp-badge {cl}'>{ic} {label}: {diag.get(key, 'Pendente')}</div>", unsafe_allow_html=True)
        if diag.get("diagnostico_texto"): st.caption(f"ℹ️ **Diagnóstico:** {diag.get('diagnostico_texto')}")
        sugestoes = diag.get("sugestoes_cirurgicas", [])
        if sugestoes:
            st.markdown("##### ✨ Sugestões Cirúrgicas Opcionais (Ajudam o Motor):")
            selecionadas = []
            for idx, sug in enumerate(sugestoes):
                if st.checkbox(sug, key=f"sug_chk_{idx}"): selecionadas.append(sug)
            st.session_state["ck_sugestoes_marcadas"] = selecionadas
        else: st.session_state["ck_sugestoes_marcadas"] = []

# --------------------------------------------------------------------------
# PASSO 5: Motor Destino & Síntese Final
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 5️⃣ Passo 5: Motor Destino & Síntese Final")
col_dest1, col_dest2 = st.columns([6, 4])
with col_dest1: dest_sel = st.selectbox("Selecione a Plataforma de Imagem Alvo:", OPCOES_DESTINO, index=0, key="ck_destino_select")
with col_dest2:
    st.write("")
    st.write("")
    btn_exec = st.button("⚡ Gerar Código do Prompt", type="primary", use_container_width=True)
if btn_exec:
    if dest_sel == "Selecione o Motor Destino...": st.error("🛑 Pare! Selecione para qual motor de IA este prompt será compilado.")
    elif not st.session_state.ck_ideia_input.strip(): st.warning("Descreva a sua Ideia no Passo 1 antes de gerar.")
    else:
        with st.spinner(f"Compilando sintaxe ultra-otimizada para {dest_sel}..."):
            try:
                eng = BANCO_DE_MOTORES[dest_sel]
                _dica = eng.get('dica_tecnica', '')
                _dica_txt = f"\n💡 DICA TÉCNICA: {_dica}" if _dica else ""
                bloco = f"\n\n======================================\n3. SINTAXE NATIVA: {dest_sel}\n======================================\n- POSITIVO: {eng['regra_positivo']}\n- NEGATIVO: {eng.get('regra_negativo', 'N/A')}{_dica_txt}\n\nSAÍDA OBRIGATÓRIA:\n1. PROMPT (ENGLISH)\n2. NEGATIVE PROMPT DINÂMICO (ENGLISH)\n3. LEGENDA\n4. HASHTAGS"
                txt_b = st.session_state.ck_preprompt_editado if st.session_state.get("ck_preprompt") else st.session_state.ck_ideia_input
                sug_aceitas = st.session_state.get("ck_sugestoes_marcadas", [])
                sug_str = "\n".join(f"- {s}" for s in sug_aceitas) if sug_aceitas else "Nenhuma sugestão."
                p = f"DESTINO: {dest_sel}\nRATING: {sens_escolhida}\n\n1. NARRATIVA VISUAL (FONTE DA TRADUÇÃO):\n{txt_b}\n\n2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}"
                _estilo_final = st.session_state.get("ck_estilo_conversao", "Manter Estilo Original")
                if "Fotorrealismo" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO PHOTOREALISM]: Rewrite entire scene as photorealistic photo, real skin, photographic texture, photorealistic. PROHIBIT anime/cartoon/illustration/drawing/cel shading terms."
                elif "Anime" in _estilo_final:
                    p += "\n[STYLE OVERRIDE — CONVERT TO ANIME 2D]: Rewrite entire scene as 2D anime illustration, clean anime linework, cel shading, anime style. Replace photo/smartphone/26mm/photorealistic with anime illustration terms. PROHIBIT photo/smartphone lens/photorealistic terms."
                if "Literal" in foco_contexto: p += "\n[MODO LITERAL ATIVADO]: Remova floreios poéticos/metafóricos, MAS MANTENHA todas as características do sujeito e os detalhes principais da composição. LITERAL NÃO É RESUMO E NÃO É OMISSÃO."
                p += "\n\n⚠️ REGRAS FINAIS — DUAS ORDENS DISTINTAS:\n- ORDEM 1 · FIDELIDADE DO SUJEITO >=95%: preserve as características do sujeito (gênero, etnia, cabelo/olhos/pele, roupa cor/material/textura/corte/acessórios).\n- ORDEM 2 · INTEGRIDADE DA COMPOSIÇÃO: não omita detalhes principais ao traduzir para a linguagem do motor (ação/pose, cenário fg/mg/bg, luz, câmera); e NÃO infle/abstraia — texto exagerado dilui e torna o resultado abstrato.\n- 'PROMPT' E 'NEGATIVE' EXCLUSIVAMENTE EM INGLÊS."
                modelo_base = st.session_state.get("modelo_texto_select", MODELO_TEXTO_PADRAO)
                res, prov = _chamar_motor_texto(SYS_MESTRE_CORE, bloco + "\n\n" + p, modelo_gemini=modelo_base)
                st.session_state["ck_prompt_final"] = res
                st.session_state["ck_prov_usado"] = prov
                st.session_state["ck_dest_usado"] = dest_sel
                st.rerun()
            except Exception as e:
                st.error(_msg_erro_amigavel(e))
                with st.expander("🔍 Diagnóstico técnico — copie e me envie se persistir"):
                    st.code(_msg_erro_diagnostico(e), language="text")
                    try:
                        _sys_len = len(SYS_MESTRE_CORE)
                        _user_len = len(bloco + "\n\n" + p)
                        _cfg_preview = str(_build_gemini_config(SYS_MESTRE_CORE, modelo_base, temperature=0.25))[:800]
                    except Exception as _diag_e:
                        _sys_len = _user_len = 0
                        _cfg_preview = str(_diag_e)[:600]
                    st.caption(f"Modelo: {modelo_base} · System: {_sys_len} chars · User+Bloco: {_user_len} chars")
                    st.code(_cfg_preview, language="text")

# OUTPUT FINAL — BOX COM QUEBRA AUTOMÁTICA + DOWNLOAD LOCAL (SEM NUVEM)
if st.session_state.get("ck_prompt_final"):
    st.markdown("---")
    st.markdown(f"### 📋 Prompt Especializado ({st.session_state.get('ck_dest_usado')})")
    st.caption(f"Gerado via {st.session_state.get('ck_prov_usado')} · Download local — nada é salvo no servidor")
    _final_txt = st.session_state["ck_prompt_final"]
    st.markdown(f"<div class='ps-final-box'>{html.escape(_final_txt)}</div>", unsafe_allow_html=True)
    st.caption("↔️ Quebra automática ativa — sem scroll horizontal.")
    st.download_button("⬇️ Baixar Prompt (.txt)", data=_final_txt, file_name=f"prompt_studio_{st.session_state.get('ck_dest_usado','prompt').replace('/','_').replace(' ','_')}.txt", mime="text/plain", use_container_width=True)
    with st.expander("📋 Copiar manualmente"):
        st.code(_final_txt, language="text")
        st.caption("Selecione tudo (Ctrl+A) → Copiar (Ctrl+C)")
