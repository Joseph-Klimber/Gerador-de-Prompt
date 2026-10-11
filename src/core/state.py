# core/state.py
"""Gerenciamento de estado da sessão Streamlit — chaves padronizadas e helpers."""
from typing import Any

import streamlit as st


# ── Chaves de Estado (Session State Keys) ──
class StateKeys:
    """Chaves padronizadas para st.session_state — evita typos e colisões."""
    
    # Auth
    AUTENTICADO = "autenticado"
    USER_EMAIL = "user_email"
    EXPIRACAO = "expiracao"
    
    # Config (sidebar)
    MODELO_VISAO_SELECT = "modelo_visao_select"
    MODELO_TEXTO_SELECT = "modelo_texto_select"
    INPUT_KEY_VISAO = "input_key_visao"
    INPUT_KEY_TEXTO = "input_key_texto"
    
    # Passo 0: Destino
    DESTINO_SELECT = "ck_destino_select"
    DESTINO_APLICADO = "ck_destino_aplicado"
    
    # Passo 1: Ideia
    IDEIA_INPUT = "ck_ideia_input"
    IDEIA_HIST_FIX = "ck_ideia_hist_fix"
    
    # Passo 2: Imagem / Visão
    IMG_UPLOADER = "ck_img_uploader"
    IMG_PARAMETROS = "ck_img_parametros"
    NORM_INFO = "ck_norm_info"
    IMG_SUJ = "img_suj"
    IMG_CEN = "img_cen"
    IMG_ACT = "img_act"
    IMG_ILU = "img_ilu"
    IMG_EST = "img_est"
    
    # Passo 3: Modificadores
    ESTILO_CONVERSAO = "ck_estilo_conversao"
    FOCO_CONTEXTO = "ck_foco_contexto"
    SENS_SLIDER = "ck_sens_slider"
    
    # Passo 4: Rascunho / Auditoria
    PREPROMPT = "ck_preprompt"
    PREPROMPT_EDITADO = "ck_preprompt_editado"
    DIAGNOSTICO = "ck_diagnostico"
    SUGESTOES_MARCADAS = "ck_sugestoes_marcadas"
    
    # Passo 5: Síntese Final
    PROMPT_FINAL = "ck_prompt_final"
    PROV_USADO = "ck_prov_usado"
    DEST_USADO = "ck_dest_usado"
    
    # Pending (state sync para evitar StreamlitAPIException)
    PENDING_IDEIA = "_pending_ck_ideia_input"
    PENDING_PREPROMPT_EDITADO = "_pending_ck_preprompt_editado"
    PENDING_IMG_SUJ = "_pending_img_suj"
    PENDING_IMG_CEN = "_pending_img_cen"
    PENDING_IMG_ACT = "_pending_img_act"
    PENDING_IMG_ILU = "_pending_img_ilu"
    PENDING_IMG_EST = "_pending_img_est"


# ── Defaults de Inicialização ──
DEFAULTS: dict[str, Any] = {
    StateKeys.AUTENTICADO: False,
    StateKeys.USER_EMAIL: "",
    StateKeys.EXPIRACAO: "",
    StateKeys.MODELO_VISAO_SELECT: "",
    StateKeys.MODELO_TEXTO_SELECT: "",
    StateKeys.INPUT_KEY_VISAO: "",
    StateKeys.INPUT_KEY_TEXTO: "",
    StateKeys.DESTINO_SELECT: "",
    StateKeys.DESTINO_APLICADO: "",
    StateKeys.IDEIA_INPUT: "",
    StateKeys.IDEIA_HIST_FIX: "",
    StateKeys.IMG_UPLOADER: None,
    StateKeys.IMG_PARAMETROS: None,
    StateKeys.NORM_INFO: None,
    StateKeys.IMG_SUJ: "",
    StateKeys.IMG_CEN: "",
    StateKeys.IMG_ACT: "",
    StateKeys.IMG_ILU: "",
    StateKeys.IMG_EST: "",
    StateKeys.ESTILO_CONVERSAO: "Manter Estilo Original",
    StateKeys.FOCO_CONTEXTO: "Harmônico (Preencher/Embelezar)",
    StateKeys.SENS_SLIDER: "Sugestiva (Insinuação artística)",
    StateKeys.PREPROMPT: "",
    StateKeys.PREPROMPT_EDITADO: "",
    StateKeys.DIAGNOSTICO: None,
    StateKeys.SUGESTOES_MARCADAS: [],
    StateKeys.PROMPT_FINAL: "",
    StateKeys.PROV_USADO: "",
    StateKeys.DEST_USADO: "",
    StateKeys.PENDING_IDEIA: "",
    StateKeys.PENDING_PREPROMPT_EDITADO: "",
    StateKeys.PENDING_IMG_SUJ: "",
    StateKeys.PENDING_IMG_CEN: "",
    StateKeys.PENDING_IMG_ACT: "",
    StateKeys.PENDING_IMG_ILU: "",
    StateKeys.PENDING_IMG_EST: "",
}


def init_state() -> None:
    """Inicializa todo o session_state com defaults — chama uma vez no topo do app."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def sync_pending() -> None:
    """Sincroniza chaves _pending_* para suas contrapartes reais.
    
    Evita StreamlitAPIException ao alterar widget após criação.
    """
    pending_map = {
        StateKeys.PENDING_IDEIA: StateKeys.IDEIA_INPUT,
        StateKeys.PENDING_PREPROMPT_EDITADO: StateKeys.PREPROMPT_EDITADO,
        StateKeys.PENDING_IMG_SUJ: StateKeys.IMG_SUJ,
        StateKeys.PENDING_IMG_CEN: StateKeys.IMG_CEN,
        StateKeys.PENDING_IMG_ACT: StateKeys.IMG_ACT,
        StateKeys.PENDING_IMG_ILU: StateKeys.IMG_ILU,
        StateKeys.PENDING_IMG_EST: StateKeys.IMG_EST,
    }
    for src, dst in pending_map.items():
        if src in st.session_state:
            st.session_state[dst] = st.session_state.pop(src)


def clear_ideia_cascade() -> None:
    """Limpa estado em cascata a partir da Ideia (Passo 1).
    
    Usado quando usuário clica 'Limpar Ideia' ou troca de destino.
    """
    cascade_keys = [
        StateKeys.IMG_PARAMETROS, StateKeys.PREPROMPT, StateKeys.PREPROMPT_EDITADO,
        StateKeys.DIAGNOSTICO, StateKeys.PROMPT_FINAL, StateKeys.SUGESTOES_MARCADAS,
        StateKeys.NORM_INFO, StateKeys.IDEIA_INPUT, StateKeys.IDEIA_HIST_FIX,
        StateKeys.IMG_SUJ, StateKeys.IMG_CEN, StateKeys.IMG_ACT,
        StateKeys.IMG_ILU, StateKeys.IMG_EST,
        StateKeys.PENDING_IDEIA, StateKeys.PENDING_PREPROMPT_EDITADO,
        StateKeys.PENDING_IMG_SUJ, StateKeys.PENDING_IMG_CEN,
        StateKeys.PENDING_IMG_ACT, StateKeys.PENDING_IMG_ILU, StateKeys.PENDING_IMG_EST,
    ]
    for k in cascade_keys:
        st.session_state.pop(k, None)
    # Repõe defaults dos widgets
    st.session_state[StateKeys.IDEIA_INPUT] = ""
    st.session_state[StateKeys.PENDING_IDEIA] = ""
    st.session_state[StateKeys.PENDING_PREPROMPT_EDITADO] = ""
    st.session_state[StateKeys.PENDING_IMG_SUJ] = ""
    st.session_state[StateKeys.PENDING_IMG_CEN] = ""
    st.session_state[StateKeys.PENDING_IMG_ACT] = ""
    st.session_state[StateKeys.PENDING_IMG_ILU] = ""
    st.session_state[StateKeys.PENDING_IMG_EST] = ""


def clear_sintese(destino_anterior: str | None = None) -> None:
    """Limpa apenas rascunho e síntese final (mantém extração da imagem).
    
    Usado quando troca de destino — cada destino tem seu formato.
    """
    sintese_keys = [
        StateKeys.PREPROMPT, StateKeys.PREPROMPT_EDITADO,
        StateKeys.IDEIA_HIST_FIX, StateKeys.PENDING_PREPROMPT_EDITADO,
    ]
    for k in sintese_keys:
        st.session_state.pop(k, None)
    
    if destino_anterior:
        st.session_state[StateKeys.DESTINO_APLICADO] = ""


def get_ideia_fonte() -> str:
    """Obtém a narrativa fonte priorizando: ajuste fino > rascunho > ideia original."""
    ajuste = (st.session_state.get(StateKeys.PREPROMPT_EDITADO) or "").strip()
    base = (st.session_state.get(StateKeys.PREPROMPT) or "").strip()
    ideia = (st.session_state.get(StateKeys.IDEIA_INPUT) or "").strip()
    return ajuste or base or ideia


def is_destino_valido() -> bool:
    """Verifica se destino foi escolhido e é válido."""
    dest = st.session_state.get(StateKeys.DESTINO_SELECT, "")
    return bool(dest) and dest != ""  # placeholder check happens in UI