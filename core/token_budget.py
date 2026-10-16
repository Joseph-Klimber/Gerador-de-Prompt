# core/token_budget.py
"""Orçamento de tokens real — medição e corte semiótico por densidade de informação."""
import re
from dataclasses import dataclass
from typing import Final

from config import (
    CPT_PT, CPT_EN, RE_CJK, RE_TERMOS_FORTES, RE_SUJEITO,
    PESO_CAMPO, PISO_CAMPO, RE_SPLIT_ROTULO,
)

# Compiled regexes
_RE_CJK = re.compile(RE_CJK)
_RE_TERMOS_FORTES = re.compile(RE_TERMOS_FORTES, re.IGNORECASE | re.UNICODE)
_RE_SUJEITO = re.compile(RE_SUJEITO, re.IGNORECASE | re.UNICODE)
_RE_SPLIT_ROTULO = re.compile(RE_SPLIT_ROTULO, re.IGNORECASE)


def _cpt(txt: str) -> float:
    """Fator caracteres/token com detecção de idioma. Conservador para nunca subestimar tokens."""
    if not txt:
        return CPT_EN
    n = max(len(txt), 1)
    cjk = len(_RE_CJK.findall(txt)) / n
    base = CPT_PT if cjk < 0.2 else CPT_EN
    return max(1.5, round(base * (1 - cjk) + 1.5 * cjk, 2))


def estimar_tokens(txt: str) -> int:
    """Estima tokens reais (não caracteres) do texto."""
    if not txt:
        return 0
    return max(1, round(len(txt) / _cpt(txt)))


def _densidade(frase: str) -> tuple[int, int]:
    """Nota de valor de uma frase. Maior = mais essencial.
    
    Câmera/luz e sujeito pesam mais que enumeração de objetos.
    """
    n_subj = len(_RE_SUJEITO.findall(frase))
    n_cam = len(_RE_TERMOS_FORTES.findall(frase))
    return (n_subj * 8 + n_cam * 6, -len(frase))


def cortar_por_frase(txt: str, max_tokens: int) -> tuple[str, bool]:
    """Corte SEMIÓTICO por fronteira de frase — nunca no meio de uma oração.
    
    Escolhe por DENSIDADE DE INFORMAÇÃO, não por ordem de aparição.
    A ordem original das frases é preservada na saída.
    """
    if not txt:
        return "", False
    
    limite = int(max_tokens * _cpt(txt))
    if len(txt) <= limite:
        return txt, False
    
    # Split por fronteira de frase (ponto, ponto e vírgula, dois-pontos + espaço)
    partes = re.split(r"(?<=[.;:])\s+", txt)
    if len(partes) < 2:
        # Texto sem pontuação suficiente — corte bruto com reticências
        corte = txt[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.!?") + "…"
        return corte, True
    
    # Ordena por densidade decrescente
    ordem = sorted(range(len(partes)), key=lambda i: _densidade(partes[i]), reverse=True)
    orcamento, escolhidos = limite, []
    
    for i in ordem:
        n = len(partes[i]) + (1 if escolhidos else 0)  # +1 pelo espaço
        if n <= orcamento:
            orcamento -= n
            escolhidos.append(i)
    
    if not escolhidos:
        corte = txt[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.!?") + "…"
        return corte, True
    
    # Restaura ordem original
    escolhidos.sort()
    saida = " ".join(partes[i] for i in escolhidos)
    return saida + (" …" if len(escolhidos) < len(partes) else ""), len(escolhidos) < len(partes)


def _norm_rotulo(rotulo: str) -> str:
    """Normaliza rótulo da visão para chave canônica."""
    r = (rotulo or "").lower()
    r2 = r.replace("ç", "c").replace("ã", "a").replace("á", "a").replace("â", "a").replace("ê", "e")
    if r.startswith("sujeit"):
        return "sujeito"
    if r2.startswith("a") and ("c" in r2 or "cao" in r2 or "aca" in r2 or r2.startswith("acao")):
        return "acao"
    if r2.startswith("pose"):
        return "acao"
    if r2.startswith("cen"):
        return "cenario"
    if r2.startswith("ilum") or r2.startswith("luz"):
        return "iluminacao"
    return "estilo_camera"


def extrair_campos_rotulados(txt: str) -> list[tuple[str, str]]:
    """Divide texto em [(rótulo_normalizado, bloco)] se for extração estruturada da visão.
    
    Retorna [] para prosa comum.
    """
    if not txt or len(txt.strip()) < 20:
        return []
    
    # Posições de cada rótulo na ordem em que aparecem
    marcas = [(m.start(), m.end(), m.group(1)) for m in _RE_SPLIT_ROTULO.finditer(txt)]
    if len(marcas) < 2:
        return []
    
    campos = []
    for i, (ini_m, fim_m, rot) in enumerate(marcas):
        prox = marcas[i + 1][0] if i + 1 < len(marcas) else len(txt)
        valor = txt[fim_m:prox].strip()
        if valor:
            campos.append((_norm_rotulo(rot), valor))
    return campos


def cortar_por_campo(campos: list[tuple[str, str]], teto_fonte: int) -> str:
    """Corta por COBERTURA de campo: cada campo recebe uma cota proporcional ao peso.
    
    Dentro da cota, vale a ordem de densidade. Preserva ordem original da visão.
    """
    presentes = [(k, v) for k, v in campos if v.strip()]
    if not presentes:
        return ""
    
    soma_pesos = sum(PESO_CAMPO.get(k, 8) for k, _ in presentes)
    cotas = {
        k: max(int(teto_fonte * PESO_CAMPO.get(k, 8) / soma_pesos), 1)
        for k, _ in presentes
    }
    piso = int(teto_fonte * PISO_CAMPO)
    
    # OVERHEAD: rótulos + reticências são tokens reais na saída final
    overhead = sum(estimar_tokens(f"{k}: …") for k, _ in presentes)
    teto_conteudo = max(teto_fonte - overhead, piso)
    
    # ── 1) Piso IGUAL para todo campo (ordem por peso crescente) ──
    escolhidos: dict[str, str] = {}
    marcado: dict[str, bool] = {}
    gasto = 0
    
    for k, v in sorted(presentes, key=lambda x: PESO_CAMPO.get(x[0], 8)):
        if gasto >= teto_conteudo:
            break
        bloco, cortou = cortar_por_frase(v, max(piso, cotas[k]))
        escolhidos[k] = bloco
        marcado[k] = cortou
        gasto += estimar_tokens(bloco)
    
    # ── 2) Redistribui sobra (ordem por peso decrescente) ──
    sobra = teto_conteudo - gasto
    if sobra > 0:
        for k, v in sorted(presentes, key=lambda x: -PESO_CAMPO.get(x[0], 8)):
            if sobra <= 0:
                break
            atual = estimar_tokens(escolhidos.get(k, ""))
            parcela = min(sobra, max(0, estimar_tokens(v) - atual))
            if parcela <= 0:
                continue
            teto_deste = min(atual + parcela, teto_conteudo - (gasto - atual))
            if teto_deste <= atual:
                continue
            bloco, _ = cortar_por_frase(v, teto_deste)
            marcado[k] = marcado.get(k, False) or True
            gasto += estimar_tokens(bloco) - atual
            escolhidos[k] = bloco
    
    # ── 3) Remonta na ordem original da visão ──
    ordem = {k: i for i, (k, _) in enumerate(presentes)}
    partes = []
    for k, v in sorted(escolhidos.items(), key=lambda x: ordem.get(x[0], 99)):
        v = v.strip()
        if not v:
            continue
        # Detecta se foi cortado (reticências com ou sem ponto)
        cortado = marcado.get(k) or bool(re.search(r"(\s*\.){1,3}\s*…\s*$", v))
        # Remove reticências duplicadas e fecha limpo
        v = re.sub(r"(\s*\.){1,3}\s*…\s*$", "", v) or v
        v = v.rstrip(" .,;:…")
        partes.append(f"{k}: {v}" + (" …" if cortado else "."))
    
    saida = " ".join(partes)
    
    # ── REDE DE SEGURANÇA: se passou do teto, corta do menos prioritário ──
    if estimar_tokens(saida) > teto_fonte:
        for k, _ in sorted(presentes, key=lambda x: PESO_CAMPO.get(x[0], 8)):
            if estimar_tokens(saida) <= teto_fonte:
                break
            _origem = dict(presentes).get(k, "")
            _atual = escolhidos.get(k, "")
            if not _atual:
                continue
            curto, _ = cortar_por_frase(_origem, max(piso, estimar_tokens(_atual) - 12))
            if curto != _atual:
                escolhidos[k] = curto
                partes = []
                for kk, vv in sorted(escolhidos.items(), key=lambda x: ordem.get(x[0], 99)):
                    c2 = marcado.get(kk) or bool(re.search(r"(\s*\.){1,3}\s*…\s*$", vv))
                    vv = re.sub(r"(\s*\.){1,3}\s*…\s*$", "", vv) or vv
                    vv = vv.rstrip(" .,;:…")
                    partes.append(f"{kk}: {vv}" + (" …" if c2 else "."))
                saida = " ".join(partes)
    
    return saida


def orcamento_fonte(txt: str, max_tokens: int, teto_fonte_pct: float = 0.65) -> tuple[str, int, bool]:
    """Aplica orçamento à narrativa fonte. Devolve (texto, tokens, avisou).
    
    O teto do destino é da SAÍDA final. A fonte entra como insumo (65%).
    Para extrações estruturadas: COBERTURA antes de densidade.
    """
    if not txt:
        return txt, 0, False
    
    teto_fonte = int(max_tokens * teto_fonte_pct)
    est = estimar_tokens(txt)
    if est <= teto_fonte:
        return txt, est, False
    
    # 1) Texto tem estrutura de campos rotulados? (extração da visão)
    campos = extrair_campos_rotulados(txt)
    if campos:
        saida = cortar_por_campo(campos, teto_fonte)
        return saida, estimar_tokens(saida), True
    
    # 2) Prosas sem rótulo: corte por densidade
    saida, cortou = cortar_por_frase(txt, teto_fonte)
    return saida, estimar_tokens(saida), cortou