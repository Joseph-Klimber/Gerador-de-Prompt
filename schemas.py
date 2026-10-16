# schemas.py
"""Contratos de dados (Data Contracts) — Single Source of Truth para tipos."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class SensualidadeLevel(str, Enum):
    ESTrita = "Estrita (Sem conteúdo sensual)"
    SUGESTIVA = "Sugestiva (Insinuação artística)"
    ARTISTICA = "Artística (Sensualidade estética)"
    EXPLICITA = "Explícita (Conteúdo adulto)"


class EstiloConversao(str, Enum):
    MANTER = "Manter Estilo Original"
    FOTORREALISMO = "📸 Converter para Fotorrealismo"
    ANIME = "🎨 Converter para Anime"


class FocoContexto(str, Enum):
    HARMONICO = "Harmônico (Preencher/Embelezar)"
    LITERAL = "Literal (Direto, Sem Floreios)"


@dataclass(frozen=True)
class DestinationProfile:
    """Perfil imutável de otimização para um destino de imagem."""
    key: str
    max_tokens: int
    structure: str
    dica_tecnica: str
    tags_obrigatorias: List[str] = field(default_factory=list)
    proibicoes: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, key: str, data: Dict[str, Any]) -> "DestinationProfile":
        return cls(
            key=key,
            max_tokens=data.get("max_tokens", 800),
            structure=data.get("structure", "general"),
            dica_tecnica=data.get("dica_tecnica", ""),
            tags_obrigatorias=data.get("tags_obrigatorias", []),
            proibicoes=data.get("proibicoes", []),
        )


@dataclass(frozen=True)
class VisionExtraction:
    """Extração estruturada da visão (5 campos obrigatórios)."""
    sujeito: str
    acao: str
    cenario: str
    iluminacao: str
    estilo_camera: str

    def to_narrativa(self) -> str:
        """Converte para narrativa visual formatada."""
        return (
            f"Sujeito: {self.sujeito}\n\n"
            f"Ação: {self.acao}\n\n"
            f"Cenário: {self.cenario}\n\n"
            f"Iluminação: {self.iluminacao}\n\n"
            f"Estilo: {self.estilo_camera}"
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "sujeito": self.sujeito,
            "acao": self.acao,
            "cenario": self.cenario,
            "iluminacao": self.iluminacao,
            "estilo_camera": self.estilo_camera,
        }


@dataclass(frozen=True)
class PromptContext:
    """Contexto imutável para construção do prompt do Mestre."""
    destino: str
    sensualidade: str
    estilo_conversao: str
    foco_contexto: str
    sugestoes: List[str]
    ideia_fonte: str
    max_tokens: int
    structure: str
    dica_tecnica: str


@dataclass(frozen=True)
class CompositometroDiagnostic:
    """Resultado da auditoria do Compositômetro."""
    sujeito_status: str
    sujeito_resumo: str
    acao_status: str
    cenario_status: str
    iluminacao_status: str
    camera_status: str
    nivel_sensualidade_sugerido: int
    diagnostico_texto: str
    sugestoes_cirurgicas: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromptFinalOutput:
    """Saída final estruturada do Mestre."""
    prompt: str           # PROMPT (ENGLISH)
    negative_prompt: str  # NEGATIVE PROMPT (ENGLISH)
    legenda: str          # LEGENDA (PT-BR)
    hashtags: List[str]   # 5-8 hashtags

    def to_text(self) -> str:
        """Formato texto para download/exibição."""
        tags = " ".join(self.hashtags)
        return (
            f"1. PROMPT (ENGLISH)\n{self.prompt}\n\n"
            f"2. NEGATIVE PROMPT (ENGLISH)\n{self.negative_prompt}\n\n"
            f"3. LEGENDA\n{self.legenda}\n\n"
            f"4. HASHTAGS\n{tags}"
        )


@dataclass(frozen=True)
class ModelConfig:
    """Configuração de modelo Gemini."""
    modelo_visao: str
    modelo_texto: str
    chave_visao: str
    chave_texto: str


@dataclass(frozen=True)
class UserSession:
    """Estado da sessão do usuário autenticado."""
    email: str
    expiracao: str
    autenticado: bool = True


@dataclass
class AppState:
    """Estado mutável da aplicação (session_state wrapper)."""
    # Auth
    autenticado: bool = False
    user_email: str = ""
    expiracao: str = ""
    
    # Config (sidebar)
    modelo_visao_select: str = ""
    modelo_texto_select: str = ""
    input_key_visao: str = ""
    input_key_texto: str = ""
    
    # Passo 0: Destino
    destino_select: str = ""
    destino_aplicado: str = ""
    
    # Passo 1: Ideia
    ideia_input: str = ""
    ideia_hist_fix: str = ""
    
    # Passo 2: Imagem / Visão
    img_uploader: Optional[Any] = None
    img_parametros: Optional[VisionExtraction] = None
    norm_info: Optional[Dict] = None
    img_suj: str = ""
    img_cen: str = ""
    img_act: str = ""
    img_ilu: str = ""
    img_est: str = ""
    
    # Passo 3: Modificadores
    estilo_conversao: str = "Manter Estilo Original"
    foco_contexto: str = "Harmônico (Preencher/Embelezar)"
    sens_slider: str = "Sugestiva (Insinuação artística)"
    
    # Passo 4: Rascunho / Auditoria
    preprompt: str = ""
    preprompt_editado: str = ""
    diagnostico: Optional[CompositometroDiagnostic] = None
    sugestoes_marcadas: List[str] = field(default_factory=list)
    
    # Passo 5: Síntese Final
    prompt_final: str = ""
    prov_usado: str = ""
    dest_usado: str = ""
    
    # Pending (state sync)
    pending_ideia: str = ""
    pending_preprompt_editado: str = ""
    pending_img_suj: str = ""
    pending_img_cen: str = ""
    pending_img_act: str = ""
    pending_img_ilu: str = ""
    pending_img_est: str = ""

    def get_ideia_fonte(self) -> str:
        """Obtém a narrativa fonte priorizando: ajuste fino > rascunho > ideia original."""
        ajuste = (self.preprompt_editado or "").strip()
        base = (self.preprompt or "").strip()
        ideia = (self.ideia_input or "").strip()
        return ajuste or base or ideia

    def is_destino_valido(self) -> bool:
        """Verifica se destino foi escolhido e é válido."""
        dest = self.destino_select or ""
        return bool(dest) and dest != "Selecione o Motor Destino..."