# src/ui/state_adapter.py
"""Adapter Streamlit para o estado da aplicação.
Isola st.session_state do módulo puro core/state.py."""
import streamlit as st
from core.state import StateKeys, DEFAULTS, prioridade_fonte

def init_state():
    """Inicializa chaves padrão no st.session_state."""
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val

def sync_pending():
    """Sincroniza chaves pendentes com as chaves reais antes de criar widgets."""
    pending_map = {
        StateKeys.PENDING_IDEIA: StateKeys.IDEIA_INPUT,
        StateKeys.PENDING_PREPROMPT_EDITADO: StateKeys.PREPROMPT_EDITADO,
        StateKeys.PENDING_IMG_SUJ: StateKeys.IMG_SUJ,
        StateKeys.PENDING_IMG_CEN: StateKeys.IMG_CEN,
        StateKeys.PENDING_IMG_ACT: StateKeys.IMG_ACT,
        StateKeys.PENDING_IMG_ILU: StateKeys.IMG_ILU,
        StateKeys.PENDING_IMG_EST: StateKeys.IMG_EST,
    }
    for p_key, real_key in pending_map.items():
        if p_key in st.session_state:
            st.session_state[real_key] = st.session_state.pop(p_key)

def backup_ideia():
    """Faz backup explícito da narrativa no histórico."""
    ideia = (st.session_state.get(StateKeys.IDEIA_INPUT) or "").strip()
    if ideia:
        st.session_state[StateKeys.IDEIA_HIST_FIX] = ideia

def restore_ideia_if_empty():
    """Restaura a narrativa se o campo estiver vazio."""
    atual = (st.session_state.get(StateKeys.IDEIA_INPUT) or "").strip()
    if not atual:
        res = prioridade_fonte(dict(st.session_state))
        if res:
            st.session_state[StateKeys.IDEIA_INPUT] = res

def get_ideia_fonte() -> str:
    """Retorna a melhor narrativa disponível no estado."""
    return prioridade_fonte(dict(st.session_state))

def clear_ideia_cascade() -> None:
    """Limpa estado em cascata a partir da Ideia (Passo 1)."""
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
    st.session_state[StateKeys.IDEIA_INPUT] = ""
    st.session_state[StateKeys.PENDING_IDEIA] = ""
    st.session_state[StateKeys.PENDING_PREPROMPT_EDITADO] = ""
    st.session_state[StateKeys.PENDING_IMG_SUJ] = ""
    st.session_state[StateKeys.PENDING_IMG_CEN] = ""
    st.session_state[StateKeys.PENDING_IMG_ACT] = ""
    st.session_state[StateKeys.PENDING_IMG_ILU] = ""
    st.session_state[StateKeys.PENDING_IMG_EST] = ""


def clear_sintese(destino_anterior: str | None = None) -> None:
    """Limpa apenas rascunho e síntese final (mantém extração da imagem)."""
    sintese_keys = [
        StateKeys.PREPROMPT, StateKeys.PREPROMPT_EDITADO,
        StateKeys.IDEIA_HIST_FIX, StateKeys.PENDING_PREPROMPT_EDITADO,
    ]
    for k in sintese_keys:
        st.session_state.pop(k, None)

    if destino_anterior:
        st.session_state[StateKeys.DESTINO_APLICADO] = ""


def is_destino_valido() -> bool:
    """Verifica se há um destino selecionado válido."""
    dest = st.session_state.get(StateKeys.DESTINO_SELECT, "")
    return bool(dest and "Selecione" not in dest)
