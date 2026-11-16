# core/state.py
"""Gerenciamento de estado da sessão — chaves padronizadas e helpers puros."""
from typing import Any

# ── Chaves de Estado (Session State Keys) ──
class StateKeys:
    """Chaves padronizadas para session_state — evita typos e colisões."""
    
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


def prioridade_fonte(state_dict: dict[str, Any]) -> str:
    """Calcula a narrativa fonte a partir do dicionário de estado."""
    ajuste = (state_dict.get(StateKeys.PREPROMPT_EDITADO) or "").strip()
    base = (state_dict.get(StateKeys.PREPROMPT) or "").strip()
    ideia = (state_dict.get(StateKeys.IDEIA_INPUT) or "").strip()
    hist_fix = (state_dict.get(StateKeys.IDEIA_HIST_FIX) or "").strip()
    pending = (state_dict.get(StateKeys.PENDING_IDEIA) or "").strip()
    return ajuste or base or ideia or hist_fix or pending