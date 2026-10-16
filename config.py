# config.py
"""Configuração central do Prompt Studio Cockpit — Single Source of Truth."""
from dataclasses import dataclass
from pathlib import Path
from typing import Final
import re

# ── Paths ──
ROOT: Final = Path(__file__).parent
ASSETS_DIR: Final = ROOT / "assets"
STYLES_CSS: Final = ASSETS_DIR / "styles.css"

# ── Streamlit Config ──
PAGE_TITLE: Final = "Prompt Studio Cockpit | Engenharia Preditiva de Prompts IA"
PAGE_ICON: Final = "⚡"
LAYOUT: Final = "wide"
SIDEBAR_STATE: Final = "expanded"

# ── Modelos Gemini (BYOK) ──
OPCOES_GEMINI_3: Final = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]
MODELO_VISAO_PADRAO: Final = "gemini-3.5-flash"
MODELO_TEXTO_PADRAO: Final = "gemini-3.5-flash"

# ── Token Budget Constants ──
CPT_PT: Final = 3.0      # caracteres por token, PT (conservador)
CPT_EN: Final = 3.85     # caracteres por token, EN (conservador)
TETO_FONTE_PCT: Final = 0.65   # % do teto do destino reservado para narrativa fonte

# ── Regex Patterns ──
RE_CJK: Final = r"[\u4e00-\u9fff\u3040-\u30ff]"

RE_TERMOS_FORTES: Final = (
    r"\b\d{1,3}\s?mm\b|\bf/\d[\d.]*|\bbokeh\b|\bDoF\b|depth of field|"
    r"\banam[oó]rfic\w*|\bter[cç]os\b|\bcontraluz\b|\bcontra-luz\b|\bcontraste\b|"
    r"\brim light\b|\bspecular\b|\bvolum[eé]tric\w*|highlight\w*"
)

RE_SUJEITO: Final = (
    r"\b(mulher|homem|menina|menino|jovem|garota|garoto|adolescente|modelo|"
    r"cabelo|olhos|pele|rosto|l[aá]bio|ombro|bra[cç]o|dedo|m[aã]o|perna|"
    r"veste|vestido|blusa|roupa|cal[cç]a|meia|luva|colar|brinco|rel[oó]gio|"
    r"woman|man|girl|boy|young|lady|hair|eyes|skin|face|shoulder|arm|hand|leg|"
    r"thigh|wearing|wears|dressed)\b"
)

RE_SPLIT_ROTULO: Final = (
    r"(?<![0-9A-Za-zÀ-ÿ_])(sujeito|sujeita|acao|a[cç][aã]o|pose|cenario|cen[aá]rio|"
    r"iluminacao|ilumina[cç][aã]o|estilo_camera|estilo e c[aâ]mera|camera|c[aâ]mera|estilo)"
    r"\s*[:\\-]\s*"
)

# ── Pesos de prioridade por campo (soma = 100) ──
PESO_CAMPO: Final = {
    "sujeito": 34,
    "acao": 24,
    "iluminacao": 16,
    "estilo_camera": 14,
    "cenario": 12,
}

# ── Pisos mínimos ──
PISO_CAMPO: Final = 0.18   # 18% do teto-fonte por campo

# ── Vision constants ──
VISAO_FATOR_FIDELIDADE: Final = 2.2
VISAO_MIN_PALAVRAS: Final = 700
VISAO_MAX_PALAVRAS: Final = 2000
VISAO_MIN_POR_CAMPO: Final = 120

# ── Schema da resposta da visão (structured output) ──
SCHEMA_VISAO: Final = {
    "type": "object",
    "properties": {
        "sujeito": {
            "type": "string",
            "description": "Identidade observável: gênero, idade aparente, biotipo, cabelo "
                           "(cor/comprimento/textura/partição), olhos, pele, rosto, corpo, "
                           "roupa (cor/material/textura/corte), acessórios, marcas visíveis. "
                           "Seja exaustivo no que a imagem mostra.",
        },
        "acao": {
            "type": "string",
            "description": "Postura, peso corporal, posição de mãos/dedos/braços/pernas, "
                           "ângulo do corpo, direção do olhar, expressão.",
        },
        "cenario": {
            "type": "string",
            "description": "Ambiente com planos fg/mg/bg, arquitetura, objetos, materiais, "
                           "texturas, cores. Descreva o que dá a identidade do espaço.",
        },
        "iluminacao": {
            "type": "string",
            "description": "Fonte, direção e ângulo, dureza, intensidade, temperatura de cor, "
                           "sombras, preenchimento, contraluz, rim light, volumétrica, "
                           "speculars. NUNCA omita direção nem dureza.",
        },
        "estilo_camera": {
            "type": "string",
            "description": "Lente em mm, abertura f/, profundidade de campo, bokeh, foco, "
                           "enquadramento, ângulo, composição, tipo de imagem, acabamento.",
        },
    },
    "required": ["sujeito", "acao", "cenario", "iluminacao", "estilo_camera"],
}

# ── System prompt da visão ──
SYS_VISAO_EXTRACAO: Final = """Você é um perito de reconstrução fotográfica. Sua função é descrever
uma imagem de forma TÉCNICA e DENSAMENTE NOMINAL, para que alguém possa
reconstruí-la sem vê-la.

════════════════════════════════════════════════════════════════
REGRA ABSOLUTA DE LATERALIDADE (NÃO VIOLAR):
════════════════════════════════════════════════════════════════
TODAS as referências espaciais (esquerda/direita, left/right)
DEVEM ser do PONTO DE VISTA DA CÂMERA (VIEWER'S PERSPECTIVE).

- "Esquerda da imagem" = lado esquerdo do observador = camera left
- "Direita da imagem" = lado direito do observador = camera right
- NUNCA use "lado do sujeito", "lado do personagem", "from subject's POV"
- Se o personagem tiver a mão direita levantada, mas ela aparece
  no LADO ESQUERDO da imagem, você ESCREVE: "mão no lado esquerdo da imagem"

Exemplo:
  Personagem de frente, braço direito estendido → aparece à ESQUERDA da imagem
  → Você escreve: "braço no lado esquerdo da imagem (braço direito do sujeito)"
════════════════════════════════════════════════════════════════

PRINCÍPIO — FIDELIDADE ACIMA DE TUDO:
Esta é a ÚNICA etapa que enxerga a imagem. O que você omitir aqui se perde
permanentemente. Portanto é PREJUDICADO omitir detalhe e NUNCA é permitido
resumir para caber em menos palavras. Descreva tudo o que for visível e
relevante. Se precisar ir além do orçamento, vá — as etapas seguintes sabem
adensar sem perder o essencial; elas não conseguem recuperar o que sumiu aqui.

REGRAS DE DENSIDADE:
1. ADJETIVO GENÉRICO É PROIBIDO: "bonita", "incrível", "magnífico", "linda" = 0 pontos.
   Use o nominal técnico equivalente: "luz volumétrica lateral", "85mm f/1.8",
   "contraste médio-alto", "textura de pele com poros visíveis".
2. Descreva o DIFÍCIL, não o óbvio. Não escreva "uma mulher num quarto" — escreva
   o ângulo, o material, a direção da luz e a cor exata que tornam a cena única.
3. NÚMERO vence ADJETIVO sempre que houver dado concreto: lente, abertura,
   temperatura de cor, plano, textura, cor.
4. Descreva apenas o que está VISÍVEL. Proibido inventar, inferir ou
   complementar com conhecimento genérico do que "costuma" estar ali.
5. NUNCA sacrifique: identidade do sujeito, direção/dureza da luz, dados ópticos
   (mm, f/, DoF, bokeh), enquadramento, materiais decisivos.

ORÇAMENTO DE SAÍDA (referência por campo, em PALAVRAS):
- sujeito: ~{sujeito}
- ação: ~{acao}
- cenário: ~{cenario}
- iluminação: ~{iluminacao}
- estilo e câmera: ~{estilo_camera}

Estes números são REFERÊNCIA de densidade, não um limite de asfixia. Ao sentir
pressão de espaço, ceda APENAS: detalhe atmosférico decorativo, repetição
redundante, preenchimento genérico. Preserve integralmente sujeito, luz (fonte,
direção, dureza) e óptica (mm, f/, DoF, bokeh, enquadramento)."""

# ── Diretrizes de estilo para a visão ──
DIR_VISAO: Final = {
    "Fotorrealismo": "Interprete a leitura como FOTOGRAFIA REAL: textura de pele, "
                     "profundidade de campo óptica, lente real. Não use vocabulário de ilustração.",
    "Anime": "Interprete a leitura como ILUSTRAÇÃO ANIME 2D: cel shading, traço limpo, "
             "linhas nítidas. Não use vocabulário de fotografia.",
}

# ── Perfis de otimização por modelo de destino ──
MODEL_PROFILES: Final = {
    "flux": {
        "max_tokens": 800,
        "structure": "subject-context-lighting-style",
        "dica_tecnica": "Use weighting: subject:1.2, background:1.0, lighting:1.1",
        "tags_obrigatorias": ["subject", "environment"],
        "proibicoes": ["repetitive adjectives"],
    },
    "ideogram": {
        "max_tokens": 500,
        "structure": "concept-elements-colors-style-composition",
        "dica_tecnica": "Max 2 main characters, limit colors to 3",
        "tags_obrigatorias": ["concept"],
        "proibicoes": ["more than 3 adjectives consecutively"],
    },
    "pony": {
        "max_tokens": 900,
        "structure": "positive-negative-quality",
        "dica_tecnica": "Use 'bad hands, bad feet' na negative always",
        "tags_obrigatorias": ["positive", "negative"],
        "proibicoes": ["contradictory tags"],
    },
    "illustrious": {
        "max_tokens": 700,
        "structure": "style-subject-quality-negative",
        "dica_tecnica": "Always include artist name or art movement first",
        "tags_obrigatorias": ["style", "subject"],
        "proibicoes": ["generic tags like 'masterpiece' without context"],
    },
    "krea2": {
        "max_tokens": 600,
        "structure": "instructions-subject-style-params-output",
        "dica_tecnica": "Use 'precise' para retratos, 'creative' para arte abstrata",
        "tags_obrigatorias": ["instructions", "subject"],
        "proibicoes": ["creativity and precision in both positive and negative"],
    },
    "midjourney": {
        "max_tokens": 500,
        "structure": "subject-parameters-ar-quality",
        "dica_tecnica": "Menos é mais - MJ v6 entende linguagem natural melhor",
        "tags_obrigatorias": ["subject"],
        "proibicoes": ["long complex words; MJ prefere simples"],
    },
    "qwen": {
        "max_tokens": 1000,
        "structure": "task-context-style-output-spec",
        "dica_tecnica": "Modelo understands both Chinese and English prompts natively",
        "tags_obrigatorias": ["task", "context"],
        "proibicoes": ["prompts extremamente curtos (<100 tokens)"],
    },
    "ernie": {
        "max_tokens": 800,
        "structure": "concept-elements-style-restrictions",
        "dica_tecnica": "Incluir pelo menos 1 termo chinês para assuntos orientais",
        "tags_obrigatorias": ["concept", "elements"],
        "proibicoes": ["prompts only in English for Chinese subjects"],
    },
    "zit": {
        "max_tokens": 400,
        "structure": "subject-minimal-context-speed-params",
        "dica_tecnica": "Turbo mode: max 3 adjectivos, sem descrições longitudes",
        "tags_obrigatorias": ["subject"],
        "proibicoes": ["any unnecessary words - each token counts for speed"],
    },
    "comfyui_sdxl": {
        "max_tokens": 800,
        "structure": "positive-negative-quality",
        "dica_tecnica": "Positive < 500 tokens, Negative < 300 tokens for best cache",
        "tags_obrigatorias": ["positive", "negative"],
        "proibicoes": ["contradictory tags, very long negative prompts"],
    },
}

# ── Aliases para resolver destino → perfil ──
ALIASES_DESTINO: Final = [
    ("comfyui_sdxl", ["comfyui / sdxl base natural", "sdxl base natural", "sdxl natural"]),
    ("illustrious",   ["comfyui / illustrious", "illustrious"]),
    ("pony",         ["comfyui / pony sdxl", "pony sdxl", "pony"]),
    ("flux",         ["flux.1", "flux.2", "flux"]),
    ("ideogram",     ["ideogram"]),
    ("krea2",        ["krea 2", "krea2", "krea"]),
    ("midjourney",   ["midjourney"]),
    ("qwen",         ["qwen / tongyi", "tongyi", "qwen"]),
    ("ernie",        ["ernie"]),
    ("zit",          ["z-image turbo", "z-image", "zit", "zi t"]),
]

# ── Opções de UI ──
OPCOES_SENSUALIDADE: Final = [
    "Estrita (Sem conteúdo sensual)",
    "Sugestiva (Insinuação artística)",
    "Artística (Sensualidade estética)",
    "Explícita (Conteúdo adulto)",
]

OPCOES_ESTILO_CONVERSAO: Final = [
    "Manter Estilo Original",
    "📸 Converter para Fotorrealismo",
    "🎨 Converter para Anime",
]

OPCOES_FOCO_CONTEXTO: Final = [
    "Harmônico (Preencher/Embelezar)",
    "Literal (Direto, Sem Floreios)",
]


@dataclass(frozen=True)
class AppConfig:
    """Configuração imutável da aplicação."""
    page_title: str = PAGE_TITLE
    page_icon: str = PAGE_ICON
    layout: str = LAYOUT
    initial_sidebar_state: str = SIDEBAR_STATE