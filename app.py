# app.py
"""Prompt Studio Cockpit — App principal modular.

Arquitetura:
- config.py                  → constantes, perfis, aliases (Single Source of Truth)
- schemas.py                 → contratos de dados (Pydantic-like dataclasses)
- core/token_budget.py       → orçamento real de tokens, corte semiótico
- core/destination.py        → resolução de perfil via alias
- core/prompt_builder.py     → montagem de prompts (Mestre, Rascunho, Auditoria)
- core/state.py              → session_state padronizado
- src/crypto.py              → criptografia Fernet
- src/config_store.py        → config local + nuvem (Apps Script)
- src/auth.py                → autenticação via Google Sheets
- src/text_engines.py        → motores de texto (BANCO_DE_MOTORES, SYS_*, helpers)
- src/vision.py              → motor de visão (Gemini Vision)
- ui/sidebar.py              → auth + centro de conexão
- ui/steps.py                → Passos 0-5 + output final
"""
import pathlib
import sys

import streamlit as st

# ── Path setup ──
ROOT = pathlib.Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Streamlit Config ──
from config import PAGE_TITLE, PAGE_ICON, LAYOUT, SIDEBAR_STATE, STYLES_CSS

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# ── Design tokens (CSS) ──
if STYLES_CSS.exists():
    st.markdown(f"<style>{STYLES_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ── Imports core ──
from core.state import init_state, sync_pending, StateKeys
from src.ui.sidebar import render_sidebar, render_login_page
from src.ui.steps import (
    render_passo_0_destino,
    render_passo_1_ideia,
    render_passo_2_visao,
    render_passo_3_modificadores,
    render_passo_4_rascunho_auditoria,
    render_passo_5_sintese,
    render_output_final,
)


def main() -> None:
    """Entry point da aplicação."""
    # Inicializa estado
    init_state()
    
    # Sync pending keys (evita StreamlitAPIException)
    sync_pending()
    
    # ── Sidebar (sempre visível) ──
    render_sidebar()
    
    # ── Tela de Login (se não autenticado) ──
    if not st.session_state[StateKeys.AUTENTICADO]:
        render_login_page()
        return  # st.stop() já chamado dentro
    
    # ── Cockpit Principal ──
    st.markdown('<p class="ps-kicker">PROMPT STUDIO COCKPIT · ATRITO ZERO</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="ps-title">Sua Ideia. Seu Motor. Controle Total.</h1>', unsafe_allow_html=True)
    st.markdown('<div class="ps-slogan">A porta é nossa, mas as chaves são suas.</div>', unsafe_allow_html=True)
    
    # Aviso de chaves não conectadas
    from src.crypto import fernet_disponivel
    from src.config_store import carregar_config
    
    if not fernet_disponivel():
        st.warning("⚠️ Conecte suas chaves na barra lateral para ativar os motores. (Criptografia desabilitada sem PS_FERNET_KEY)")
    else:
        _cfg_check = carregar_config(st.session_state[StateKeys.USER_EMAIL])
        if not _cfg_check.get("chaves", {}).get("Chave Visao") and not _cfg_check.get("chaves", {}).get("Chave Texto"):
            st.info("💡 Conecte suas chaves na barra lateral para ativar os motores.")
    
    # ── Pipeline de Passos ──
    destino_ok = render_passo_0_destino()
    
    # CRÍTICO: sync_pending ANTES do Passo 1 para evitar race condition
    # Quando há st.rerun() após extração de visão, o PENDING_IDEIA precisa
    # estar sincronizado para IDEIA_INPUT ANTES do widget text_area ser criado.
    sync_pending()
    
    render_passo_1_ideia(destino_ok)
    render_passo_2_visao(destino_ok)
    render_passo_3_modificadores(destino_ok)
    render_passo_4_rascunho_auditoria(destino_ok)
    render_passo_5_sintese(destino_ok)
    render_output_final()


if __name__ == "__main__":
    main()
