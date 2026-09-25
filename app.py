"""Gerador de prompt 1.0 — Etapa 2: dados e autenticação
PRD/TRD/Fluxo/Briefing/Schema/Plano travados em GERADOR_PROMPT_1.0__AntesDeCodar/*__ENTREVISTA.md
"""
import pathlib
import sys
# garante que `src/` na raiz do repo seja importável no Streamlit Cloud
ROOT = pathlib.Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Prompt Studio Cockpit | Engenharia Preditiva de Prompts IA",
    page_icon="\u26a1",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Design tokens (Briefing) ---
css_path = pathlib.Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# --- Imports Etapa 2 ---
from src.auth import verificar_acesso_sheets
from src.config_store import carregar_config, salvar_config
from src.crypto import fernet_disponivel, mascarar_email, OPCOES_GEMINI_3, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO

# --- Secrets check (TRD: via st.secrets, nunca hard-coded) ---
def _get_secret(name: str):
    try:
        return st.secrets[name]
    except Exception:
        return None

PS_FERNET_KEY = _get_secret("PS_FERNET_KEY")
APPS_SCRIPT_URL = _get_secret("APPS_SCRIPT_URL")

# Estado
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "expiracao" not in st.session_state:
    st.session_state["expiracao"] = ""

# ── Sidebar: Centro de Conexão (Fluxo Ação Conectar) ──
with st.sidebar:
    st.markdown("### \u26a1 Prompt Studio")
    if st.session_state["autenticado"]:
        st.caption(f"Logado: {mascarar_email(st.session_state['user_email'])}")
        if not fernet_disponivel():
            st.warning("\u26a0\ufe0f Criptografia desabilitada — configure PS_FERNET_KEY.")
        st.markdown("---")
        st.markdown("#### \U0001f50c Centro de Conex\u00e3o")
        st.caption("2 motores isolados — mesma chave pode ser usada nas duas vias (cotas separadas).")
        # carrega config atual
        _cfg = carregar_config(st.session_state["user_email"])
        # inputs com valores atuais descriptografados
        chave_visao_input = st.text_input("Chave Vis\u00e3o (BYOK)", value=_cfg.get("chaves", {}).get("Chave Visao", ""), type="password", key="input_key_visao")
        modelo_visao_sel = st.selectbox("Modelo Vis\u00e3o", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_visao", MODELO_VISAO_PADRAO)) if _cfg.get("modelo_visao") in OPCOES_GEMINI_3 else 0, key="modelo_visao_select")
        chave_texto_input = st.text_input("Chave Texto (BYOK)", value=_cfg.get("chaves", {}).get("Chave Texto", ""), type="password", key="input_key_texto")
        modelo_texto_sel = st.selectbox("Modelo Texto", OPCOES_GEMINI_3, index=OPCOES_GEMINI_3.index(_cfg.get("modelo_texto", MODELO_TEXTO_PADRAO)) if _cfg.get("modelo_texto") in OPCOES_GEMINI_3 else 0, key="modelo_texto_select")
        if st.button("\U0001f50c Conectar Motores Isolados", use_container_width=True, type="primary"):
            if not fernet_disponivel():
                st.error("Criptografia desabilitada — configure PS_FERNET_KEY antes de salvar.")
            elif modelo_visao_sel not in OPCOES_GEMINI_3 or modelo_texto_sel not in OPCOES_GEMINI_3:
                st.error("Modelo inv\u00e1lido — use 3.5/3.6/3.7-flash (abaixo de 3.X \u00e9 obsoleto).")
            else:
                dados = {"chaves": {"Chave Visao": chave_visao_input.strip(), "Chave Texto": chave_texto_input.strip()}, "modelo_visao": modelo_visao_sel, "modelo_texto": modelo_texto_sel, "modelo_padrao": modelo_texto_sel}
                ok, msg = salvar_config(dados, email=st.session_state["user_email"])
                if ok:
                    st.success("Motores conectados com sucesso!")
                else:
                    st.warning(msg or "Erro ao salvar na nuvem — c\u00f3pia local salva.")
        st.markdown("---")
        if st.button("\U0001f6aa Sair do Sistema", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["user_email"] = ""
            st.session_state["expiracao"] = ""
            st.rerun()
    else:
        st.caption("Fa\u00e7a login com o e-mail da compra.")

# ── Tela 1: Página de Entrada (Login) ──
if not st.session_state["autenticado"]:
    if not fernet_disponivel():
        st.warning("\u26a0\ufe0f Criptografia desabilitada — configure PS_FERNET_KEY em .streamlit/secrets.toml (Etapa 1.3).")

    # Hero
    st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT \u00b7 ATRITO ZERO</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Pare de lutar contra a IA.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Transforme ideia vaga em prompt pronto para ComfyUI/Midjourney — qualidade suprema sem inventar, menos tentativas.</p>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;"><span class="byok-badge">\U0001f50c BYOK — suas chaves, suas cotas, nada salvo no servidor</span></div>', unsafe_allow_html=True)

    # Showcase
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"uma elfa na escadaria"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">score_9, score_8_up, source_anime, 1girl, solo, long silver hair, green eyes, ornate armor, standing on stone stairs, volumetric light, highly detailed...</div>', unsafe_allow_html=True)
        img1 = pathlib.Path(__file__).parent / "assets" / "carro.jpg"
        try:
            if img1.exists():
                st.image(str(img1), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">\U0001f4da</div>', unsafe_allow_html=True)
            st.caption("carro.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"carro esportivo futurista"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown('<div class="code-prompt">photorealistic, ultra detailed, sports car, metallic paint, studio lighting, 85mm lens, shallow depth of field, 8k...</div>', unsafe_allow_html=True)
        img2 = pathlib.Path(__file__).parent / "assets" / "elfa.jpg"
        try:
            if img2.exists():
                st.image(str(img2), use_container_width=True)
            else:
                raise FileNotFoundError
        except Exception:
            st.markdown('<div style="height:140px;border-radius:12px;background:linear-gradient(135deg,#059669 0%,#2563eb 100%);display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;">\U0001f4f8</div>', unsafe_allow_html=True)
            st.caption("elfa.jpg no servidor")
        st.markdown('</div>', unsafe_allow_html=True)

    # Planos Kiwify
    st.markdown('<div class="plan-container">', unsafe_allow_html=True)
    st.markdown("### Escolha seu plano")
    st.caption("Pagamento fora do app — compra na Kiwify libera seu e-mail na planilha.")
    c1, c2, c3 = st.columns(3)
    def _kiwify_link(days_key):
        v = _get_secret(days_key)
        return v if v and "PLACEHOLDER" not in str(v) else "#"
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
    st.caption("Use o e-mail da compra na Kiwify. Valida\u00e7\u00e3o e prazo na planilha (sem senha).")
    email_input = st.text_input("E-mail da compra", placeholder="seu@email.com", key="login_email")
    if st.button("Entrar no Sistema", type="primary", use_container_width=True):
        email = (email_input or "").strip()
        if not email:
            st.error("Digite seu e-mail.")
        elif "@" not in email:
            st.error("E-mail inv\u00e1lido — verifique o e-mail da compra.")
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
                st.error(erro or "E-mail n\u00e3o encontrado — verifique o e-mail da compra.")

    st.caption("LGPD: Imagens com pessoas s\u00e3o processadas apenas para extra\u00e7\u00e3o e descartadas. Nada \u00e9 salvo no servidor.")
    st.stop()

# ── Tela 2: Cockpit Único (Etapa 3 virá aqui) ──
st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT \u00b7 ATRITO ZERO</p>', unsafe_allow_html=True)
st.markdown('<h1 class="ps-title">Sua Ideia. Seu Motor. Controle Total.</h1>', unsafe_allow_html=True)
st.markdown('<p class="ps-slogan">Etapa 2 pronta — cockpit de texto/imagem entra na Etapa 3.</p>', unsafe_allow_html=True)

if not fernet_disponivel():
    st.warning("\u26a0\ufe0f Conecte suas chaves na barra lateral para ativar os motores. (Criptografia desabilitada sem PS_FERNET_KEY)")
else:
    # banner se nenhuma chave conectada
    _cfg_check = carregar_config(st.session_state["user_email"])
    if not _cfg_check.get("chaves", {}).get("Chave Visao") and not _cfg_check.get("chaves", {}).get("Chave Texto"):
        st.info("\U0001f4a1 Conecte suas chaves na barra lateral para ativar os motores.")

st.info("\U0001f6a7 Cockpit completo (Acolher \u2192 Melhorar \u2192 Modificar \u2192 Auditar \u2192 Baixar) entra na **Etapa 3**.")
st.caption("Etapa 2 \u2713 — login e-mail + prazo (4 formatos) + cache 600s + Fernet obrigat\u00f3rio + 2 chaves isoladas + modelos 3.5/3.6/3.7 (padr\u00e3o 3.5, <3.X obsoleto)")
