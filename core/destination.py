# core/destination.py
"""Resolução de perfil do destino — alias matching e teto de tokens."""
from dataclasses import dataclass
from typing import Final

from config import MODEL_PROFILES, ALIASES_DESTINO
from src.text_engines import OPCOES_DESTINO


@dataclass(frozen=True)
class DestinationProfile:
    """Perfil imutável de otimização para um destino."""
    key: str
    max_tokens: int
    structure: str
    dica_tecnica: str
    tags_obrigatorias: list[str]
    proibicoes: list[str]
    
    @classmethod
    def from_dict(cls, key: str, data: dict) -> "DestinationProfile":
        return cls(
            key=key,
            max_tokens=data.get("max_tokens", 800),
            structure=data.get("structure", "general"),
            dica_tecnica=data.get("dica_tecnica", ""),
            tags_obrigatorias=data.get("tags_obrigatorias", []),
            proibicoes=data.get("proibicoes", []),
        )


def perfil_do_destino(dest_sel: str) -> DestinationProfile | None:
    """Resolve o perfil de otimização a partir do rótulo da UI (OPCOES_DESTINO).
    
    Args:
        dest_sel: Rótulo selecionado no selectbox (ex: "Flux.1 / Flux.2 (Klein)")
    
    Returns:
        DestinationProfile se achar match via ALIASES_DESTINO, None caso contrário.
    """
    if not dest_sel:
        return None
    
    dl = dest_sel.lower()
    for chave, apelidos in ALIASES_DESTINO:
        if any(a in dl for a in apelidos):
            data = MODEL_PROFILES.get(chave)
            if data:
                return DestinationProfile.from_dict(chave, data)
    return None


def teto_destino(dest_sel: str) -> int:
    """Teto de tokens da SAÍDA final (prompt + negative + legenda + hashtags)."""
    perfil = perfil_do_destino(dest_sel)
    return perfil.max_tokens if perfil else 800


def estrutura_destino(dest_sel: str) -> str:
    """Estrutura esperada pelo destino (ex: 'subject-context-lighting-style')."""
    perfil = perfil_do_destino(dest_sel)
    return perfil.structure if perfil else "general"


def dica_tecnica_destino(dest_sel: str) -> str:
    """Dica técnica específica do destino."""
    perfil = perfil_do_destino(dest_sel)
    return perfil.dica_tecnica if perfil else ""


def injetar_estrutura_destino(prompt: str, dest_sel: str) -> str:
    """Injeta diretiva de estrutura nativa do destino no prompt do Mestre.
    
    Feito uma vez, sem duplicação, com prioridade correta (Illustrious antes de ComfyUI).
    """
    _dest_lower = dest_sel.lower()
    
    # Ordem importa: Illustrious contém "comfyui" no rótulo, deve vir ANTES
    if "illustrious" in _dest_lower:
        return prompt + "\n\n[ILLUSTRIOUS STRUCTURE: style (artist/movement first) | subject | quality | negative]"
    elif "flux" in _dest_lower:
        return prompt + "\n\n[FLUX STRUCTURE: subject | context | lighting | style]"
    elif "ideogram" in _dest_lower:
        return prompt + "\n\n[IDEOGRAM STRUCTURE: concept | elements | colors (max 3) | composition]"
    elif "midjourney" in _dest_lower:
        return prompt + "\n\n[MJ STRUCTURE: subject + --v 6.1 --style raw --ar 16:9]"
    elif any(m in _dest_lower for m in ["pony", "sdxl", "comfyui"]):
        return prompt + "\n\n[SDXL/PONY STRUCTURE: positive-tags, negative-tags]"
    elif "krea" in _dest_lower:
        return prompt + "\n\n[KREA STRUCTURE: instructions | subject | style-params]"
    elif "ernie" in _dest_lower:
        return prompt + "\n\n[ERNIE STRUCTURE: concept | elements | style | restrictions]"
    elif "qwen" in _dest_lower or "tongyi" in _dest_lower:
        return prompt + "\n\n[QWEN STRUCTURE: task | context | style | output-spec]"
    elif any(m in _dest_lower for m in ["z-image", "zit", "zi t"]):
        return prompt + "\n\n[Z-IMAGE STRUCTURE: subject | minimal context | speed params]"
    
    return prompt


def validar_destino_escolhido(dest_sel: str) -> bool:
    """Verifica se o destino selecionado é válido (não é o placeholder)."""
    return dest_sel != OPCOES_DESTINO[0] and perfil_do_destino(dest_sel) is not None