# core/prompt_builder.py
"""Construtor do prompt final para o Mestre — separa lógica de montagem da UI."""
from dataclasses import dataclass

from src.config.settings import OPCOES_SENSUALIDADE
from src.text_engines import BANCO_DE_MOTORES
from src.core.destination import injetar_estrutura_destino, teto_destino
from src.core.state import StateKeys, get_ideia_fonte
from src.core.token_budget import orcamento_fonte, estimar_tokens


@dataclass(frozen=True)
class PromptContext:
    """Contexto imutável para construção do prompt do Mestre."""
    destino: str
    sensualidade: str
    estilo_conversao: str
    foco_contexto: str
    sugestoes: list[str]
    ideia_fonte: str
    max_tokens: int
    structure: str
    dica_tecnica: str


def build_prompt_context() -> PromptContext:
    """Coleta todo contexto necessário do session_state e monta PromptContext."""
    destino = StateKeys.get_destino()  # será resolvido via session_state
    return PromptContext(
        destino=st.session_state.get(StateKeys.DESTINO_SELECT, ""),
        sensualidade=st.session_state.get(StateKeys.SENS_SLIDER, OPCOES_SENSUALIDADE[1]),
        estilo_conversao=st.session_state.get(StateKeys.ESTILO_CONVERSAO, "Manter Estilo Original"),
        foco_contexto=st.session_state.get(StateKeys.FOCO_CONTEXTO, "Harmônico (Preencher/Embelezar)"),
        sugestoes=st.session_state.get(StateKeys.SUGESTOES_MARCADAS, []),
        ideia_fonte=get_ideia_fonte(),
        max_tokens=teto_destino(st.session_state.get(StateKeys.DESTINO_SELECT, "")),
        structure="",  # preenchido depois
        dica_tecnica="",  # preenchido depois
    )


def montar_prompt_mestre(ctx: PromptContext, perfil) -> str:
    """Monta o prompt completo para o SYS_MESTRE_CORE.
    
    Args:
        ctx: Contexto com parâmetros da UI
        perfil: DestinationProfile resolvido
    
    Returns:
        Prompt string pronto para envio ao modelo.
    """
    max_tokens = ctx.max_tokens
    structure = perfil.structure
    dica_tecnica = perfil.dica_tecnica
    
    # ── 1. Orçamento real na narrativa fonte ──
    txt_b = ctx.ideia_fonte
    if not txt_b.strip():
        raise ValueError("Narrativa vazia — escreva no Passo 1 ou gere rascunho no Passo 4")
    
    est_antes = estimar_tokens(txt_b)
    txt_b, est_fonte, cortou = orcamento_fonte(txt_b, max_tokens)
    
    # ── 2. P-Base (bloco de instruções fixas) ──
    eng = BANCO_DE_MOTORES.get(ctx.destino, {})
    regra_pos = eng.get("regra_positivo", "Tradução literal detalhada.")
    regra_neg = eng.get("regra_negativo", "N/A")
    
    sug_str = "\n".join(f"- {s}" for s in ctx.sugestoes) if ctx.sugestoes else "Nenhuma sugestão."
    _dica_txt = f"\n💡 DICA TÉCNICA: {dica_tecnica}" if dica_tecnica else ""
    
    bloco = (
        f"DESTINO: {ctx.destino}\n"
        f"RATING: {ctx.sensualidade}\n"
        f"FORMATO: {structure}\n\n"
        f"1. NARRATIVA VISUAL (FONTE DA TRADUÇÃO):\n{txt_b}\n\n"
        f"2. SUGESTÕES CIRÚRGICAS INCORPORADAS:\n{sug_str}"
        f"\n\n======================================\n"
        f"3. SINTAXE NATIVA: {ctx.destino}\n"
        f"======================================\n"
        f"- POSITIVO: {regra_pos}\n"
        f"- NEGATIVO: {regra_neg}"
        f"{_dica_txt}\n\n"
        f"SAÍDA OBRIGATÓRIA:\n"
        f"1. PROMPT (ENGLISH)\n"
        f"2. NEGATIVE PROMPT DINÂMICO (ENGLISH)\n"
        f"3. LEGENDA\n"
        f"4. HASHTAGS"
    )
    
    # ── 3. Injeção estrutural por destino ──
    p = injetar_estrutura_destino(bloco, ctx.destino)
    
    # ── 4. Estilo e regras ──
    if "Fotorrealismo" in ctx.estilo_conversao:
        p += (
            "\n[STYLE OVERRIDE — CONVERT TO PHOTOREALISM]: "
            "Rewrite entire scene as photorealistic photo, real skin, photographic texture, "
            "photorealistic. PROHIBIT anime/cartoon/illustration/drawing/cel shading terms."
        )
    elif "Anime" in ctx.estilo_conversao:
        p += (
            "\n[STYLE OVERRIDE — CONVERT TO ANIME 2D]: "
            "Rewrite entire scene as 2D anime illustration, clean anime linework, cel shading, "
            "anime style. Replace photo/smartphone/26mm/photorealistic with anime illustration terms. "
            "PROHIBIT photo/smartphone lens/photorealistic terms."
        )
    
    if "Literal" in ctx.foco_contexto:
        p += (
            "\n[MODO LITERAL]: Remova floreios poéticos/metafóricos, MAS MANTENHA todas as "
            "características do sujeito e os detalhes principais da composição. "
            "LITERAL NÃO É RESUMO E NÃO É OMISSÃO."
        )
    
    # ── 5. Orçamento de saída (teto duro) ──
    p += (
        f"\n\n⚠️ ORÇAMENTO DE SAÍDA — TETO DURO: {max_tokens} tokens para TUDO "
        f"(PROMPT + NEGATIVE + LEGENDA + HASHTAGS).\n"
        "- DENSIDADE, NÃO VOLUME: cada palavra deve ganhar peso. "
        "Adjetivo genérico ('bonito','belo','incrível') = 0 pontos. "
        "Nominal técnico ('85mm','rim light','f1.4') = alto valor.\n"
        "- ORDEM DE PRIORIDADE quando o teto aperta: "
        "(1) sujeito/fidelidade (2) ação+pose (3) cenário fg/mg/bg "
        "(4) luz (5) câmera (6) legenda/hashtags — corte do 6 para o 1, "
        "nunca do 1 para o 2.\n"
        "- PRECEDÊNCIA: FIDELIDADE > ORÇAMENTO, mas 'acima do orçamento' NÃO é "
        "licença para inflar nem omitir: é ordem de espremer MAIS DENSIDADE no mesmo teto.\n"
        "- 'PROMPT' E 'NEGATIVE' EXCLUSIVAMENTE EM INGLÊS."
    )
    
    return p


def build_rascunho_prompt(destino: str, perfil, ideia: str, sensualidade: str,
                           estilo_conversao: str, foco_contexto: str) -> str:
    """Monta prompt para o GERADOR_PREPROMPT (rascunho da cena)."""
    _estilo = estilo_conversao
    p = f"IDEIA:\n{ideia}\n\n[AGENTE: SENSUALIDADE NÍVEL '{sensualidade}']"
    p += (
        f"\n[DESTINO ALVO: {destino}]"
        f"\n[FORMATO EXIGIDO: {perfil.structure}]"
        f"\n[ORIENTAÇÃO TÉCNICA DO DESTINO: {perfil.dica_tecnica}]"
        "\n[RASCUNHO = FONTE DA SÍNTESE FINAL]: descreva a cena nos termos que o "
        "destino consome (nominal técnico, sem adjetivo genérico). Não escreva "
        "meta-comentário sobre o formato."
    )
    if "Fotorrealismo" in _estilo:
        p += (
            "\n[MODIFICADOR ESTILO — CONVERTER PARA FOTORREALISMO]: Reescreva TODA a cena "
            "como FOTOGRAFIA REAL. Substitua 'anime, ilustração, desenho, traço' por "
            "'foto fotorrealista, pele real, textura fotográfica'. "
            "PROÍBA vocabulário anime/cartoon/ilustração."
        )
    elif "Anime" in _estilo:
        p += (
            "\n[MODIFICADOR ESTILO — CONVERTER PARA ANIME 2D]: Reescreva TODA a cena como "
            "ILUSTRAÇÃO ANIME 2D. Substitua 'foto, câmera de smartphone, lente 26mm, "
            "fotorrealista' por 'ilustração anime, traço anime limpo, cel shading, "
            "linhas nítidas, anime style'. PROÍBA 'foto, smartphone, lente, fotorrealista'."
        )
    if "Literal" in foco_contexto:
        p += "\n[AGENTE LITERAL]: Seja 100% fiel, sem floreios estéticos inúteis."
    return p


def build_auditoria_prompt(ideia: str) -> str:
    """Monta prompt para o COMPOSITÔMETRO (auditoria)."""
    return f"AVALIE:\n{ideia}"