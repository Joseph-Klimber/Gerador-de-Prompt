# ui/sidebar.py
"""Barra lateral: Centro de Conexão e Autenticação."""
import streamlit as st

from src.crypto import fernet_disponivel, mascarar_email, OPCOES_GEMINI_3, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO
from src.core.state import StateKeys, init_state
from src.config_store import carregar_config, salvar_config
from src.auth import verificar_acesso_sheets


def render_sidebar() -> None:
    """Renderiza a sidebar completa (auth + centro de conexão)."""
    with st.sidebar:
        st.markdown("### ⚡ Prompt Studio")
        
        if st.session_state[StateKeys.AUTENTICADO]:
            _render_sidebar_logged_in()
        else:
            _render_sidebar_login()


def _render_sidebar_logged_in() -> None:
    """Sidebar para usuário autenticado."""
    email = st.session_state[StateKeys.USER_EMAIL]
    st.caption(f"Logado: {mascarar_email(email)}")
    
    if not fernet_disponivel():
        st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY.")
    
    st.markdown("---")
    st.markdown("#### 🔌 Centro de Conexão")
    st.caption("2 motores isolados — mesma chave pode ser usada nas duas vias (cotas separadas).")
    
    _cfg = carregar_config(email)
    
    # Chave Visão
    chave_visao = st.text_input(
        "Chave Visão (BYOK)",
        value=_cfg.get("chaves", {}).get("Chave Visao", ""),
        type="password",
        key=StateKeys.INPUT_KEY_VISAO,
    )
    
    modelo_visao = st.selectbox(
        "Modelo Visão",
        OPCOES_GEMINI_3,
        index=(
            OPCOES_GEMINI_3.index(_cfg.get("modelo_visao", MODELO_VISAO_PADRAO))
            if _cfg.get("modelo_visao") in OPCOES_GEMINI_3 else 0
        ),
        key=StateKeys.MODELO_VISAO_SELECT,
    )
    
    # Chave Texto
    chave_texto = st.text_input(
        "Chave Texto (BYOK)",
        value=_cfg.get("chaves", {}).get("Chave Texto", ""),
        type="password",
        key=StateKeys.INPUT_KEY_TEXTO,
    )
    
    modelo_texto = st.selectbox(
        "Modelo Texto",
        OPCOES_GEMINI_3,
        index=(
            OPCOES_GEMINI_3.index(_cfg.get("modelo_texto", MODELO_TEXTO_PADRAO))
            if _cfg.get("modelo_texto") in OPCOES_GEMINI_3 else 0
        ),
        key=StateKeys.MODELO_TEXTO_SELECT,
    )
    
    if st.button("🔌 Conectar Motores Isolados", use_container_width=True, type="primary"):
        _conectar_motores(chave_visao, modelo_visao, chave_texto, modelo_texto, email)
    
    st.markdown("---")
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        _logout()


def _conectar_motores(chave_visao: str, modelo_visao: str, chave_texto: str,
                       modelo_texto: str, email: str) -> None:
    """Salva configuração dos motores."""
    if not fernet_disponivel():
        st.error("Criptografia desabilitada — configure PS_FERNET_KEY antes de salvar.")
        return
    
    if modelo_visao not in OPCOES_GEMINI_3 or modelo_texto not in OPCOES_GEMINI_3:
        st.error("Modelo inválido — use 3.5/3.6/3.7-flash (abaixo de 3.X é obsoleto).")
        return
    
    dados = {
        "chaves": {
            "Chave Visao": chave_visao.strip(),
            "Chave Texto": chave_texto.strip(),
        },
        "modelo_visao": modelo_visao,
        "modelo_texto": modelo_texto,
        "modelo_padrao": modelo_texto,
    }
    ok, msg = salvar_config(dados, email=email)
    if ok:
        st.success("Motores conectados com sucesso!")
    else:
        st.warning(msg or "Erro ao salvar na nuvem — cópia local salva.")


def _logout() -> None:
    """Realiza logout e limpa sessão."""
    for key in [StateKeys.AUTENTICADO, StateKeys.USER_EMAIL, StateKeys.EXPIRACAO]:
        st.session_state[key] = DEFAULTS[key]
    st.rerun()


def _render_sidebar_login() -> None:
    """Sidebar para tela de login (compacta)."""
    st.caption("Faça login com o e-mail da compra.")


def render_login_page() -> None:
    """Renderiza a tela de login completa (página principal quando não autenticado)."""
    if not fernet_disponivel():
        st.warning("⚠️ Criptografia desabilitada — configure PS_FERNET_KEY em .streamlit/secrets.toml (Etapa 1.3).")
    
    st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Pare de lutar contra a IA.</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-subtitle">Transforme ideia vaga em prompt pronto para ComfyUI/Midjourney — '
        'qualidade suprema sem inventar, menos tentativas.</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="text-align:center;"><span class="byok-badge">'
        '🔌 BYOK — suas chaves, suas cotas, nada salvo no servidor</span></div>',
        unsafe_allow_html=True
    )
    
    # Showcase
    _render_showcase()
    
    # Planos
    _render_planos()
    
    # Formulário de login
    st.markdown("---")
    st.markdown("### Entrar no Sistema")
    st.caption("Use o e-mail da compra na Kiwify. Validação e prazo na planilha (sem senha).")
    
    email_input = st.text_input("E-mail da compra", placeholder="seu@email.com", key="login_email")
    
    if st.button("Entrar no Sistema", type="primary", use_container_width=True):
        _processar_login(email_input)
    
    st.caption("LGPD: Imagens com pessoas são processadas apenas para extração e descartadas. Nada é salvo no servidor.")
    st.stop()


def _processar_login(email_input: str) -> None:
    """Processa tentativa de login."""
    email = (email_input or "").strip()
    if not email:
        st.error("Digite seu e-mail.")
        return
    if "@" not in email:
        st.error("E-mail inválido — verifique o e-mail da compra.")
        return
    
    with st.spinner("Verificando acesso..."):
        ok, exp, erro = verificar_acesso_sheets(email)
    
    if ok:
        st.session_state[StateKeys.AUTENTICADO] = True
        st.session_state[StateKeys.USER_EMAIL] = email.lower()
        st.session_state[StateKeys.EXPIRACAO] = exp
        st.success("Acesso liberado!")
        st.rerun()
    else:
        st.error(erro or "E-mail não encontrado — verifique o e-mail da compra.")


def _render_showcase() -> None:
    """Renderiza os dois cards de exemplo (elfa + carro)."""
    from pathlib import Path
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"uma elfa na escadaria"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="code-prompt">score_9, score_8_up, source_anime, 1girl, solo, '
            'long silver hair, green eyes, ornate armor, standing on stone stairs, '
            'volumetric light, highly detailed...</div>',
            unsafe_allow_html=True
        )
        _render_showcase_image("elfa.jpg", "📚")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_b:
        st.markdown('<div class="showcase-box">', unsafe_allow_html=True)
        st.markdown('<p class="label-ideia">Ideia simples</p>', unsafe_allow_html=True)
        st.markdown('<p class="text-ideia">"carro esportivo futurista"</p>', unsafe_allow_html=True)
        st.markdown('<p class="label-prompt">Prompt engenharia</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="code-prompt">photorealistic, ultra detailed, sports car, metallic paint, '
            'studio lighting, 85mm lens, shallow depth of field, 8k...</div>',
            unsafe_allow_html=True
        )
        _render_showcase_image("carro.jpg", "📸")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_showcase_image(filename: str, fallback_emoji: str) -> None:
    """Renderiza imagem de showcase ou fallback."""
    img_path = Path(__file__).parent.parent.parent / "assets" / filename
    try:
        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            raise FileNotFoundError
    except Exception:
        st.markdown(
            f'<div style="height:140px;border-radius:12px;background:linear-gradient('
            f'135deg,#2563eb 0%,#7c3aed 100%);display:flex;align-items:center;'
            f'justify-content:center;color:white;font-size:1.8rem;">{fallback_emoji}</div>',
            unsafe_allow_html=True
        )
        st.caption(f"{filename} no servidor")


def _render_planos() -> None:
    """Renderiza cards de planos com botões Kiwify."""
    import os
    
    st.markdown('<div class="plan-container">', unsafe_allow_html=True)
    st.markdown("### Escolha seu plano")
    st.caption("Pagamento fora do app — compra na Kiwify libera seu e-mail na planilha.")
    
    _KIWIFY_FALLBACK = {
        "LINK_KIWIFY_15_DIAS": "https://pay.kiwify.com.br/MXVL98k",
        "LINK_KIWIFY_30_DIAS": "https://pay.kiwify.com.br/dyfEGe5",
        "LINK_KIWIFY_90_DIAS": "https://pay.kiwify.com.br/xo0m3rF",
    }
    
    def _kiwify_link(days_key: str) -> str:
        v = os.getenv(days_key) or st.secrets.get(days_key, "")
        if v and "PLACEHOLDER" not in str(v) and str(v).strip() not in ("", "#"):
            return v
        return _KIWIFY_FALLBACK.get(days_key, "#")
    
    c1, c2, c3 = st.columns(3)
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