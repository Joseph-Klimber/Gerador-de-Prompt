# ui/steps.py
"""Componentes de UI para cada passo do cockpit (Passos 0-5)."""
import streamlit as st
from datetime import datetime
from PIL import Image, ImageOps

from config import (
    OPCOES_SENSUALIDADE, OPCOES_ESTILO_CONVERSAO,
    OPCOES_FOCO_CONTEXTO, MODELO_VISAO_PADRAO, MODELO_TEXTO_PADRAO,
)
from src.text_engines import OPCOES_DESTINO
from core.state import StateKeys
from src.ui.state_adapter import sync_pending, get_ideia_fonte, backup_ideia, restore_ideia_if_empty, is_destino_valido
from core.destination import (
    perfil_do_destino, teto_destino, estrutura_destino, dica_tecnica_destino,
    validar_destino_escolhido,
)
from core.prompt_builder import build_rascunho_prompt, build_auditoria_prompt, PromptContext, montar_prompt_mestre
from src.text_engines import (
    BANCO_DE_MOTORES, SYS_GERADOR_PREPROMPT, SYS_COMPOSITOMETRO, SYS_MESTRE_CORE,
    _chamar_motor_texto, _msg_erro_amigavel, _msg_erro_diagnostico, parse_json_ia,
    _ps_markup_origin, _build_gemini_config,
)
from src.vision import _chamar_motor_visao
from src.config_store import carregar_config
from src.crypto import fernet_disponivel


def _now() -> str:
    """Retorna timestamp atual formatado HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def _msg(msg: str) -> str:
    """Prefixa mensagem com timestamp."""
    return f"[{_now()}] {msg}"


def _chaves_configuradas() -> tuple[bool, str]:
    """Verifica se chaves Visão e/ou Texto estão configuradas.
    Returns: (ok, mensagem_se_falta)
    Cacheado por sessão para evitar múltiplas chamadas de rede.
    """
    cache_key = "_chaves_config_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    if not fernet_disponivel():
        result = (False, "Criptografia desabilitada — configure PS_FERNET_KEY")
        st.session_state[cache_key] = result
        return result

    email = st.session_state.get(StateKeys.USER_EMAIL, "")
    cfg = carregar_config(email)
    chaves = cfg.get("chaves", {})

    tem_visao = bool(chaves.get("Chave Visao", "").strip())
    tem_texto = bool(chaves.get("Chave Texto", "").strip())

    # Para extração de imagem precisa Visão; para rascunho/auditoria/síntese precisa Texto
    result = ((tem_visao or tem_texto), "")
    st.session_state[cache_key] = result
    return result


def _chave_visao_ok() -> tuple[bool, str]:
    """Verifica se chave Visão está configurada. Cacheado por sessão."""
    cache_key = "_chave_visao_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    if not fernet_disponivel():
        result = (False, "Criptografia desabilitada — configure PS_FERNET_KEY")
        st.session_state[cache_key] = result
        return result

    email = st.session_state.get(StateKeys.USER_EMAIL, "")
    cfg = carregar_config(email)
    tem_visao = bool(cfg.get("chaves", {}).get("Chave Visao", "").strip())
    result = (tem_visao, "Chave Visão não configurada — conecte na barra lateral")
    st.session_state[cache_key] = result
    return result


def _chave_texto_ok() -> tuple[bool, str]:
    """Verifica se chave Texto está configurada. Cacheado por sessão."""
    cache_key = "_chave_texto_cache"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    if not fernet_disponivel():
        result = (False, "Criptografia desabilitada — configure PS_FERNET_KEY")
        st.session_state[cache_key] = result
        return result

    email = st.session_state.get(StateKeys.USER_EMAIL, "")
    cfg = carregar_config(email)
    tem_texto = bool(cfg.get("chaves", {}).get("Chave Texto", "").strip())
    result = (tem_texto, "Chave Texto não configurada — conecte na barra lateral")
    st.session_state[cache_key] = result
    return result



def render_passo_0_destino() -> bool:
    """Passo 0: Motor Destino (obrigatório e primeiro).
    
    Returns:
        True se destino válido selecionado, False caso contrário.
    """
    st.markdown("### 0️⃣ Passo 0: Motor Destino (Obrigatório)")
    st.caption(
        "Defina primeiro para qual plataforma o prompt será compilado. Tudo o que vem depois — "
        "inclusive a extração da imagem — respeita o formato e o limite de tokens deste motor. "
        "Escolher por último desperdiça trabalho."
    )
    
    dest_sel = st.selectbox(
        "Plataforma de Imagem Alvo:",
        OPCOES_DESTINO,
        key=StateKeys.DESTINO_SELECT,
        label_visibility="collapsed",
    )
    
    perfil = perfil_do_destino(dest_sel) if validar_destino_escolhido(dest_sel) else None
    
    if perfil:
        st.caption(
            f"🎯 **{dest_sel}** · formato **{perfil.structure}** · "
            f"teto **{perfil.max_tokens} tokens** para prompt + negative + legenda + hashtags."
        )
    else:
        st.info(
            "🛑 Escolha o motor de destino para liberar a extração de imagem, o rascunho e a "
            "geração do prompt. Sem ele não há formato nem orçamento definidos."
        )
    
    # Detecta troca de destino e limpa síntese anterior
    destino_anterior = st.session_state.get(StateKeys.DESTINO_APLICADO)
    if perfil and destino_anterior and destino_anterior != dest_sel:
        clear_sintese(destino_anterior)
        st.info(
            f"🔄 Destino alterado para **{dest_sel}**. Rascunho e prompt final anteriores foram "
            "descartados (cada destino tem o seu formato). A extração da imagem foi mantida — "
            "serve para qualquer destino."
        )
    
    if perfil:
        st.session_state[StateKeys.DESTINO_APLICADO] = dest_sel
    
    return bool(perfil)


def _on_ideia_change() -> None:
    """Callback disparado quando o usuário altera o texto do Passo 1."""
    val = (st.session_state.get(StateKeys.IDEIA_INPUT) or "").strip()
    if val:
        st.session_state[StateKeys.IDEIA_HIST_FIX] = val
        st.session_state[StateKeys.PENDING_IDEIA] = val


def render_passo_1_ideia(destino_ok: bool) -> None:
    """Passo 1: A Sua Ideia (narrativa visual)."""
    st.markdown("### 3️⃣ Passo 3: A Sua Ideia (A Narrativa Visual)")

    # Indicador visual das modificações ativas (do Passo 1 - Modificadores Globais)
    estilo = st.session_state.get(StateKeys.ESTILO_CONVERSAO, "Manter Estilo Original")
    foco = st.session_state.get(StateKeys.FOCO_CONTEXTO, "Harmônico (Preencher/Embelezar)")
    sens = st.session_state.get(StateKeys.SENS_SLIDER, OPCOES_SENSUALIDADE[1])
    mods_ativos = []
    if estilo != "Manter Estilo Original":
        mods_ativos.append(f"🎨 {estilo}")
    if foco != "Harmônico (Preencher/Embelezar)":
        mods_ativos.append(f"🎯 {foco}")
    if sens != "Sugestiva (Insinuação artística)":
        mods_ativos.append(f"💋 {sens}")
    if mods_ativos:
        st.caption(_msg("Modificadores ativos: " + " | ".join(mods_ativos)))
    else:
        st.caption(_msg("O ponto de partida. Descreva o que imagina ou veja a caixa preencher-se usando o Passo 2."))

    ideia_val = st.text_area(
        "Insira a sua Ideia:",
        key=StateKeys.IDEIA_INPUT,
        height=140,
        label_visibility="collapsed",
        on_change=_on_ideia_change,
    )
    if ideia_val and ideia_val.strip():
        st.session_state[StateKeys.IDEIA_HIST_FIX] = ideia_val.strip()

    if st.button("🗑️ Limpar Ideia", use_container_width=False, disabled=not destino_ok):
        clear_ideia_cascade()
        st.rerun()


def render_passo_2_visao(destino_ok: bool) -> None:
    """Passo 2: Referência Óptica (Imagem Opcional) — Extração via Visão. Largura total."""
    st.markdown("### 2️⃣ Passo 2: Referência Óptica (Opcional)")
    st.caption("Sem inspiração para escrever? Faça upload de uma imagem. A Via de Visão extrairá os micro-detalhes para o Passo 1.")

    img_file = st.file_uploader(
        "Upload de Referência",
        type=["png", "jpg", "jpeg", "webp"],
        key=StateKeys.IMG_UPLOADER,
        label_visibility="collapsed",
        disabled=not destino_ok,
    )

    # Miniatura da referência (máx 512×512) — a extração continua na imagem original
    if img_file:
        try:
            img_file.seek(0)
            _thumb = ImageOps.exif_transpose(Image.open(img_file))
            _thumb.thumbnail((512, 512))
            st.image(_thumb, caption=f"📎 {img_file.name} — miniatura máx. 512×512")
        except Exception:
            st.warning(_msg("Não foi possível gerar a miniatura desta imagem — a extração pode continuar."))
        st.caption("🔍 Miniatura reduzida para visualização; o Motor de Visão recebe a imagem original em alta.")

    # Verificar chave Visão
    visao_ok, visao_msg = _chave_visao_ok()

    btn_ler = st.button(
        "👁️ Extrair Imagem (Motor de Visão)",
        use_container_width=True,
        disabled=not destino_ok or not visao_ok,
    )

    if not destino_ok:
        st.caption(
            "🔒 Selecione o motor de destino no Passo 0 para liberar a extração — o "
            "orçamento da visão é derivado do teto desse motor."
        )
    elif not visao_ok:
        st.error(_msg(visao_msg))

        # Validação client-side 10MB (Roteiro: mensagem exata "Imagem limite: 10 MB.")
        if img_file and getattr(img_file, "size", 0) > 10 * 1024 * 1024:
            st.error(_msg("Imagem limite: 10 MB."))
            st.caption("🔒 Upload bloqueado localmente — imagem não foi enviada ao modelo.")
            return  # Sai da função sem chamar IA

    # Info de normalização da imagem
    if st.session_state.get(StateKeys.NORM_INFO):
        _ni = st.session_state[StateKeys.NORM_INFO]
        if _ni.get("metodo") == "canonica":
            _rec = f" · recorte {_ni.get('recorte_pct', 0):.1f}%" if _ni.get("recorte_pct", 0) >= 0.1 else ""
            _rotulo = f"📐 Proporção **{_ni.get('proporcao', '?')}** aplicada (desvio {_ni.get('desvio', 0)}%{_rec})"
        else:
            _rotulo = (
                f"📐 Proporção original **{_ni.get('razao_original', '?')}:1** preservada "
                f"— fora do padrão de mercado (mais próxima: {_ni.get('proporcao', '?')}, "
                f"desvio {_ni.get('desvio', 0)}%)"
            )
        st.caption(
            f"{_rotulo} · {_ni.get('antes', '?')} → **{_ni.get('depois', '?')} px** "
            f"· {_ni.get('tiles', '?')} tiles ≈ {_ni.get('tokens_aprox', 0)} tokens de imagem"
        )

    if btn_ler:
            if not img_file:
                st.warning(_msg("Selecione uma imagem primeiro."))
            else:
                with st.spinner("Analisando matriz óptica com Varredura Ultra-Densa..."):
                    try:
                        modelo_base = st.session_state.get(StateKeys.MODELO_VISAO_SELECT, MODELO_VISAO_PADRAO)
                        estilo_conversao = st.session_state.get(StateKeys.ESTILO_CONVERSAO, "Manter Estilo Original")
                        sens_escolhida = st.session_state.get(StateKeys.SENS_SLIDER, OPCOES_SENSUALIDADE[1])
                        max_tokens = teto_destino(st.session_state.get(StateKeys.DESTINO_SELECT, ""))

                        res = _chamar_motor_visao(
                            img_file, estilo_conversao, sens_escolhida, modelo_base, max_tokens
                        )
                        st.session_state[StateKeys.NORM_INFO] = res.get("norm") or {}

                        if res["tipo"] == "json":
                            st.session_state[StateKeys.IMG_PARAMETROS] = res["dados"]
                            st.session_state[StateKeys.PENDING_IMG_SUJ] = res["dados"].get("sujeito", "")
                            st.session_state[StateKeys.PENDING_IMG_CEN] = res["dados"].get("cenario", "")
                            st.session_state[StateKeys.PENDING_IMG_ACT] = res["dados"].get("acao", "")
                            st.session_state[StateKeys.PENDING_IMG_ILU] = res["dados"].get("iluminacao", "")
                            st.session_state[StateKeys.PENDING_IMG_EST] = res["dados"].get("estilo_camera", "")

                            ideia_extraida = (
                                f"Sujeito: {res['dados'].get('sujeito','')}\n\n"
                                f"Ação: {res['dados'].get('acao','')}\n\n"
                                f"Cenário: {res['dados'].get('cenario','')}\n\n"
                                f"Iluminação: {res['dados'].get('iluminacao','')}\n\n"
                                f"Estilo: {res['dados'].get('estilo_camera','')}"
                            )
                            st.session_state[StateKeys.PENDING_IDEIA] = ideia_extraida
                        else:
                            st.session_state[StateKeys.PENDING_IDEIA] = res["texto"]
                            st.session_state.pop(StateKeys.IMG_PARAMETROS, None)

                        st.session_state.pop(StateKeys.PREPROMPT, None)
                        st.rerun()
                    except Exception as e:
                        st.error(_msg(_msg_erro_amigavel(e)))
                        with st.expander("🔍 Diagnóstico técnico — copie e me envie se persistir", expanded=False):
                            st.code(_msg_erro_diagnostico(e), language="text")
                            st.caption(
                                f"Modelo: {st.session_state.get('modelo_visao_select', '?')} · "
                                f"Arquivo: {img_file.name if img_file else '?'} · "
                                f"Tamanho: {img_file.size/1024:.0f} KB" if img_file else ""
                            )
    
    # Detalhador pericial editável
    if st.session_state.get(StateKeys.IMG_PARAMETROS):
        with st.expander("🔬 Detalhador Pericial Extraído (Editável)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.text_area("👤 Sujeito:", key=StateKeys.IMG_SUJ, height=150)
                st.text_area("🏞️ Cenário:", key=StateKeys.IMG_CEN, height=150)
            with c2:
                st.text_area("🏃 Ação:", key=StateKeys.IMG_ACT, height=100)
                st.text_area("💡 Iluminação:", key=StateKeys.IMG_ILU, height=100)
                st.text_area("📷 Estilo:", key=StateKeys.IMG_EST, height=100)
            
            if st.button("🔄 Atualizar Caixa da Ideia com estas edições", use_container_width=True):
                nova_ideia = (
                    f"Sujeito: {st.session_state[StateKeys.IMG_SUJ]}\n\n"
                    f"Ação: {st.session_state[StateKeys.IMG_ACT]}\n\n"
                    f"Cenário: {st.session_state[StateKeys.IMG_CEN]}\n\n"
                    f"Iluminação: {st.session_state[StateKeys.IMG_ILU]}\n\n"
                    f"Estilo: {st.session_state[StateKeys.IMG_EST]}"
                )
                st.session_state[StateKeys.PENDING_IDEIA] = nova_ideia
                st.rerun()


def render_passo_3_modificadores(destino_ok: bool) -> None:
    """Passo 3: Modificadores Globais — metade da tela, lado a lado com o Passo 0."""
    st.markdown("### 1️⃣ Passo 1: Modificadores Globais")
    st.caption("ℹ️ *Aviso: Estes filtros guiam a geração do rascunho (Passo 4) e do prompt final. Não alteram a extração de imagem do Passo 2.*")

    # Detectar mudança de modificadores e invalidar rascunho/síntese
    modificadores_atuais = (
        st.session_state.get(StateKeys.ESTILO_CONVERSAO, "Manter Estilo Original"),
        st.session_state.get(StateKeys.FOCO_CONTEXTO, "Harmônico (Preencher/Embelezar)"),
        st.session_state.get(StateKeys.SENS_SLIDER, OPCOES_SENSUALIDADE[1]),
    )
    modificadores_anteriores = st.session_state.get(StateKeys.MODIFICADORES_HASH)
    if modificadores_anteriores and modificadores_anteriores != hash(modificadores_atuais):
        # Modificadores mudaram - limpar rascunho e síntese
        st.session_state.pop(StateKeys.PREPROMPT, None)
        st.session_state.pop(StateKeys.PROMPT_FINAL, None)
        st.session_state.pop(StateKeys.DIAGNOSTICO, None)
        st.session_state.pop(StateKeys.SUGESTOES_MARCADAS, None)
        st.caption(_msg("⚠️ Modificadores alterados — rascunho e prompt final descartados. Gere novamente."))
    st.session_state[StateKeys.MODIFICADORES_HASH] = hash(modificadores_atuais)

    with st.container(border=True):
        # Estilo em linha própria: o preset Anti-Porcelana tem nome longo
        st.selectbox("Estilo de Arte:", OPCOES_ESTILO_CONVERSAO, key=StateKeys.ESTILO_CONVERSAO, disabled=not destino_ok)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.selectbox("Foco e Contexto:", OPCOES_FOCO_CONTEXTO, key=StateKeys.FOCO_CONTEXTO, disabled=not destino_ok)
        with col_m2:
            st.select_slider("Sensualidade:", options=OPCOES_SENSUALIDADE, key=StateKeys.SENS_SLIDER, disabled=not destino_ok)


def render_passo_4_rascunho_auditoria(destino_ok: bool) -> None:
    """Passo 4: Rascunho & Validação — largura total (após a Ideia)."""
    st.markdown("---")
    st.markdown("### 4️⃣ Passo 4: Rascunho & Validação (Opcional)")

    # Verificar chave Texto
    texto_ok, texto_msg = _chave_texto_ok()
    
    btn_pre = st.button(
        "👁️ Rascunhar Cena (Via Motor de Texto)",
        use_container_width=True,
        disabled=not destino_ok or not texto_ok,
    )
    btn_ava = st.button(
        "🔍 Auditar no Compositômetro (Raio-X)",
        use_container_width=True,
        disabled=not destino_ok or not texto_ok,
    )

    if not destino_ok:
        st.caption(
            "🔒 O rascunho e a auditoria dependem do motor de destino (Passo 0) — sem ele "
            "não há formato-alvo para rascunhar."
        )
        return
    elif not texto_ok:
        st.error(_msg(texto_msg))
        return

    # Rascunho
    if btn_pre:
        restore_ideia_if_empty()
        backup_ideia()
        ideia_fonte = get_ideia_fonte()
        if not ideia_fonte:
            st.warning(_msg("Escreva sua Ideia no Passo 1."))
        else:
            st.session_state[StateKeys.IDEIA_HIST_FIX] = ideia_fonte
            st.session_state[StateKeys.PENDING_IDEIA] = ideia_fonte
            with st.spinner("Desenhando a cena com o Motor de Texto..."):
                try:
                    destino = st.session_state[StateKeys.DESTINO_SELECT]
                    perfil = perfil_do_destino(destino)
                    prompt = build_rascunho_prompt(
                        destino, perfil,
                        ideia_fonte,
                        st.session_state[StateKeys.SENS_SLIDER],
                        st.session_state[StateKeys.ESTILO_CONVERSAO],
                        st.session_state[StateKeys.FOCO_CONTEXTO],
                    )
                    modelo_base = st.session_state.get(StateKeys.MODELO_TEXTO_SELECT, MODELO_TEXTO_PADRAO)
                    txt, prov = _chamar_motor_texto(SYS_GERADOR_PREPROMPT, prompt, modelo_gemini=modelo_base)
                    st.session_state[StateKeys.PREPROMPT] = txt
                    st.session_state[StateKeys.PENDING_PREPROMPT_EDITADO] = txt
                    st.rerun()
                except Exception as e:
                    st.error(_msg(_msg_erro_amigavel(e)))

    # Auditoria
    if btn_ava:
        restore_ideia_if_empty()
        ideia_fonte_auditoria = get_ideia_fonte()
        if not ideia_fonte_auditoria:
            st.warning(_msg("Escreva sua Ideia no Passo 1."))
        else:
            with st.spinner("Raio-X em andamento com o Motor de Texto..."):
                try:
                    modelo_base = st.session_state.get(StateKeys.MODELO_TEXTO_SELECT, MODELO_TEXTO_PADRAO)
                    txt, prov = _chamar_motor_texto(
                        SYS_COMPOSITOMETRO,
                        f"AVALIE:\n{ideia_fonte_auditoria}",
                        modelo_gemini=modelo_base
                    )
                    diag = parse_json_ia(txt)
                    if not diag:
                        st.error(_msg("⚠️ Erro de formato no Raio-X. Tente novamente."))
                    else:
                        st.session_state[StateKeys.DIAGNOSTICO] = diag
                        st.rerun()
                except Exception as e:
                    st.error(_msg(_msg_erro_amigavel(e)))

    # Exibe rascunho com diff
    if st.session_state.get(StateKeys.PREPROMPT):
        st.markdown(
            "<div class='ps-legend'><span><span class='ps-user-word'>Ideia Original</span></span> • "
            "<span><span class='ps-ai-word'>Ajuste da IA</span></span></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='ps-preprompt'>{_ps_markup_origin(st.session_state[StateKeys.PREPROMPT], st.session_state.get(StateKeys.IDEIA_HIST_FIX, ''))}</div>",
            unsafe_allow_html=True
        )
        st.text_area(
            "Ajuste fino do Rascunho (Esta caixa substituirá a Ideia para o Motor Final):",
            key=StateKeys.PREPROMPT_EDITADO,
            height=130,
        )

    # Exibe diagnóstico (badges)
    _render_diagnostico()


def _render_diagnostico() -> None:
    """Renderiza badges do Compositômetro."""
    def _bdg(s: str) -> tuple[str, str]:
        if s in ("Definido", "Definida", "Presente"):
            return ("comp-green", "✓")
        if s in ("Vago", "Estática"):
            return ("comp-amber", "!")
        return ("comp-blue", "⚙️")

    diag = st.session_state.get(StateKeys.DIAGNOSTICO)
    if not diag:
        return

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, key, label in zip(
            [c1, c2, c3, c4, c5],
            ["sujeito_status", "acao_status", "cenario_status", "iluminacao_status", "camera_status"],
            ["Sujeito", "Ação", "Cenário", "Luz", "Câmera"]
        ):
            cl, ic = _bdg(diag.get(key, ""))
            col.markdown(
                f"<div class='comp-badge {cl}'>{ic} {label}: {diag.get(key, 'Pendente')}</div>",
                unsafe_allow_html=True
            )

        if diag.get("diagnostico_texto"):
            st.caption(f"ℹ️ **Diagnóstico:** {diag.get('diagnostico_texto')}")

        sugestoes = diag.get("sugestoes_cirurgicas", [])
        if sugestoes:
            st.markdown("##### ✨ Sugestões Cirúrgicas Opcionais (Ajudam o Motor):")
            selecionadas = []
            for idx, sug in enumerate(sugestoes):
                if st.checkbox(sug, key=f"sug_chk_{idx}"):
                    selecionadas.append(sug)
            st.session_state[StateKeys.SUGESTOES_MARCADAS] = selecionadas
        else:
            st.session_state[StateKeys.SUGESTOES_MARCADAS] = []


def render_passo_5_sintese(destino_ok: bool) -> None:
    """Passo 5: Síntese Final — compila prompt para o Mestre."""

    st.markdown("---")
    st.markdown("### 5️⃣ Passo 5: Síntese Final")

    destino = st.session_state.get(StateKeys.DESTINO_SELECT, "")
    perfil = perfil_do_destino(destino) if destino_ok else None

    if perfil:
        st.caption(
            f"Compilando a narrativa para **{destino}** no formato "
            f"**{perfil.structure}**, teto de **{perfil.max_tokens} tokens**."
        )
    else:
        st.caption("Selecione o destino no Passo 0 para ver o teto e formato.")

    # Verificar chave Texto
    texto_ok, texto_msg = _chave_texto_ok()

    btn_exec = st.button(
        "⚡ Gerar Código do Prompt",
        type="primary",
        use_container_width=True,
        disabled=not destino_ok or not texto_ok,
    )

    if btn_exec:
        if not destino_ok:
            st.error(_msg("Selecione para qual motor"))
            return
        if not texto_ok:
            st.error(_msg(texto_msg))
            return
        if not st.session_state[StateKeys.IDEIA_INPUT].strip():
            st.warning(_msg("Escreva sua Ideia no Passo 1."))
            return

        with st.spinner(f"Compilando sintaxe ultra-otimizada para {destino}..."):
            try:
                eng = BANCO_DE_MOTORES[destino]
                max_tokens = perfil.max_tokens
                structure = perfil.structure

                # Constrói prompt do Mestre
                modelo_base = st.session_state.get(StateKeys.MODELO_TEXTO_SELECT, MODELO_TEXTO_PADRAO)

                ctx = PromptContext(
                    destino=destino,
                    sensualidade=st.session_state.get(StateKeys.SENS_SLIDER, OPCOES_SENSUALIDADE[1]),
                    estilo_conversao=st.session_state.get(StateKeys.ESTILO_CONVERSAO, "Manter Estilo Original"),
                    foco_contexto=st.session_state.get(StateKeys.FOCO_CONTEXTO, "Harmônico (Preencher/Embelezar)"),
                    sugestoes=st.session_state.get(StateKeys.SUGESTOES_MARCADAS, []),
                    ideia_fonte=get_ideia_fonte(),
                    max_tokens=max_tokens,
                    structure=structure,
                    dica_tecnica=perfil.dica_tecnica,
                )

                # monta prompt final (inclui orçamento na narrativa)
                p = montar_prompt_mestre(ctx, perfil)
                res, prov = _chamar_motor_texto(SYS_MESTRE_CORE, p, modelo_gemini=modelo_base)

                st.session_state[StateKeys.PROMPT_FINAL] = res
                st.session_state[StateKeys.PROV_USADO] = prov
                st.session_state[StateKeys.DEST_USADO] = destino
                st.rerun()
            except Exception as e:
                st.error(_msg(_msg_erro_amigavel(e)))
                with st.expander("🔍 Diagnóstico técnico — copie e me envie se persistir"):
                    st.code(_msg_erro_diagnostico(e), language="text")
                    _modelo_diag = st.session_state.get(StateKeys.MODELO_TEXTO_SELECT, MODELO_TEXTO_PADRAO)
                    try:
                        _sys_len = len(SYS_MESTRE_CORE)
                        _user_len = len(p)
                        _cfg_preview = str(_build_gemini_config(SYS_MESTRE_CORE, _modelo_diag, temperature=0.25))[:800]
                    except Exception as _diag_e:
                        _sys_len = _user_len = 0
                        _cfg_preview = str(_diag_e)[:600]
                    st.caption(f"Modelo: {_modelo_diag} · System: {_sys_len} chars · User+Bloco: {_user_len} chars")
                    st.code(_cfg_preview, language="text")


def render_output_final() -> None:
    """Renderiza o prompt final com download e copy."""
    import html

    if not st.session_state.get(StateKeys.PROMPT_FINAL):
        return

    st.markdown("---")
    st.markdown(f"### 📋 Prompt Especializado ({st.session_state.get(StateKeys.DEST_USADO)})")
    st.caption(f"Gerado via {st.session_state.get(StateKeys.PROV_USADO)} · Download local — nada é salvo no servidor")

    _final_txt = st.session_state[StateKeys.PROMPT_FINAL]
    st.markdown(f"<div class='ps-final-box'>{html.escape(_final_txt)}</div>", unsafe_allow_html=True)
    st.caption("↔️ Quebra automática ativa — sem scroll horizontal.")

    st.download_button(
        "⬇️ Baixar Prompt (.txt)",
        data=_final_txt,
        file_name=f"prompt_studio_{st.session_state.get(StateKeys.DEST_USADO,'prompt').replace('/','_').replace(' ','_')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("📋 Copiar manualmente"):
        st.code(_final_txt, language="text")
        st.caption("Selecione tudo (Ctrl+A) → Copiar (Ctrl+C)")
