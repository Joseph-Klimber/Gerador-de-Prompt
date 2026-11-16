# core/contracts.py
"""Contratos de dados unificados (SSOT) — tipos imutáveis e enums do domínio."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Any


class StrEnum(str, Enum):
    """Enum base cujos membros comparam como strings."""
    def __str__(self) -> str:
        return str(self.value)


class EstiloConversao(StrEnum):
    """Estilos de conversão de imagem/prompt."""
    MANTER_ORIGINAL = "Manter Estilo Original"
    FOTORREALISMO = "📸 Converter para Fotorrealismo — Fotográfico Realista (Anti-Porcelana)"
    ANIME = "🎨 Converter para Anime / 2D — Estilo Ilustração Nippônica"
    LITERAL = "🔍 Modo Literal / Fiel ao Original"
    
    # Marcadores para detecção de modificadores especiais
    ANTI_PORCELANA_MARKER = "Anti-Porcelana"


class FocoContexto(StrEnum):
    """Modo de foco de contexto para expansão do prompt."""
    HARMONICO = "Harmônico (Preencher/Embelezar)"
    LITERAL = "Literal (Strict/Sem Adições)"
    CRIATIVO = "Criativo (Explorar Possibilidades)"


@dataclass(frozen=True)
class DestinationProfile:
    """Perfil imutável do motor de destino."""
    key: str
    label: str
    max_tokens: int
    structure: str
    dica_tecnica: str = ""
    tags_obrigatorias: Tuple[str, ...] = field(default_factory=tuple)
    proibicoes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PromptContext:
    """Contexto imutável para construção do prompt do Mestre."""
    destino: str
    sensualidade: str
    estilo_conversao: str
    foco_contexto: str
    sugestoes: Tuple[str, ...] = field(default_factory=tuple)
    ideia_fonte: str = ""
    max_tokens: int = 800
    structure: str = ""
    dica_tecnica: str = ""
