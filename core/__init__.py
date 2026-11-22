# src/core/__init__.py
"""Core logic do Prompt Studio Cockpit."""
from .token_budget import (
    estimar_tokens, cortar_por_frase, extrair_campos_rotulados,
    cortar_por_campo, orcamento_fonte,
)
from .destination import (
    DestinationProfile, perfil_do_destino, teto_destino,
    estrutura_destino, dica_tecnica_destino, injetar_estrutura_destino,
    validar_destino_escolhido,
)
from .state import (
    StateKeys, init_state, sync_pending, clear_ideia_cascade,
    clear_sintese, get_ideia_fonte, is_destino_valido,
)
from .prompt_builder import (
    PromptContext, build_prompt_context, montar_prompt_mestre,
    build_rascunho_prompt, build_auditoria_prompt,
)

__all__ = [
    "estimar_tokens", "cortar_por_frase", "extrair_campos_rotulados",
    "cortar_por_campo", "orcamento_fonte",
    "DestinationProfile", "perfil_do_destino", "teto_destino",
    "estrutura_destino", "dica_tecnica_destino", "injetar_estrutura_destino",
    "validar_destino_escolhido",
    "StateKeys", "init_state", "sync_pending", "clear_ideia_cascade",
    "clear_sintese", "get_ideia_fonte", "is_destino_valido",
    "PromptContext", "build_prompt_context", "montar_prompt_mestre",
    "build_rascunho_prompt", "build_auditoria_prompt",
]