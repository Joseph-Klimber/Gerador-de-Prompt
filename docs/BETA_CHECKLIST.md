# BETA_CHECKLIST.md

Checklist final de prontidão para beta do Prompt Studio.

---

## ✅ Código & Arquitetura

### Core
- [x] `config.py` — Single Source of Truth (perfis, aliases, limites, prompts).
- [x] `schemas.py` — Contratos de dados (dataclasses tipadas).
- [x] `core/token_budget.py` — Orçamento real (tiktoken/cl100k_base), corte semiótico, teto derivado.
- [x] `core/destination.py` — Resolução de perfil via alias, validação.
- [x] `core/prompt_builder.py` — Mestre, Rascunho, Auditoria montados com orçamento injetado.
- [x] `core/state.py` — Session state padronizado (`StateKeys`, `DEFAULTS`, `init_state`, `sync_pending`, `restore_ideia_if_empty`).

### Segurança & Persistência
- [x] `src/crypto.py` — Fernet (PS_FERNET_KEY), `mascarar_email`.
- [x] `src/config_store.py` — Local + nuvem, **HMAC-SHA256** request/response, **cache 5 min TTL**, type guards (`dict | None`), invalidação no `salvar_config`.
- [x] `src/auth.py` — Sheets via Apps Script, retry 1s/2s, timeout 15s, timestamps BR_TZ.
- [x] `apps_script/Code.gs` — **Rate limit duplo** (email + IP), HMAC verify/sign, canonical JSON, logs estruturados Cloud Logging.

### Motores
- [x] `src/text_engines.py` — BANCO_DE_MOTORES (10 motores), SYS_*, `_chamar_motor_texto` com cascade de chaves, retry exponencial, fallback 3.5→3.6→3.7-flash, temperature opcional, erros amigáveis + diagnóstico.
- [x] `src/vision.py` — REST-only Vision, extração 5 campos, tetos derivados do destino, mesma robustez de retry/fallback, cascade de chaves inversa.

### UI (modular)
- [x] `app.py` — Orquestrador (Passos 0-5 em colunas/linhas corretas, `sync_pending` nos pontos certos).
- [x] `src/ui/sidebar.py` — Auth + Centro de Conexão (2 chaves isoladas, modelos 3.5/3.6/3.7).
- [x] `src/ui/steps.py` — Passos 0-5 + output final:
  - Passo 0: Motor Destino (obrigatório, primeiro).
  - Passo 1: Ideia (text_area commit no blur, `on_change` + backup).
  - Passo 2: Visão (upload, miniatura, extração, detalhador editável).
  - Passo 3: Modificadores Globais (lado a lado com Passo 0).
  - Passo 4: Rascunho (diff visual user/IA) + Auditoria (badges + sugestões).
  - Passo 5: Síntese Final (Mestre, orçamento injetado, download .txt).
- [x] `config/STYLES_CSS` — Design tokens, badges, diff, caixas, responsivo.

---

## ✅ Qualidade & Robustez

### Tratamento de Erros
- [x] Erros amigáveis (`_msg_erro_amigavel`) cobrem 401, 403, 404, 429, 503, timeout.
- [x] Diagnóstico técnico expansível (`_msg_erro_diagnostico`) com RAW code + payload.
- [x] Retry exponencial + jitter (0-0.5s) + respeito a `Retry-After` (teto 30s).
- [x] Fallback de modelos automático (3.5 → 3.6 → 3.7-flash) em ambas vias.
- [x] Validação de parâmetros não suportados (temperature) → não retenta.

### Timestamps & Logs
- [x] BR_TZ (UTC-3) em todos `_msg()` / `_now()`: `[HH:MM:SS]` prefix.
- [x] Apps Script: `isoNow()` ISO 8601 + `logStructured` JSON para Cloud Logging.

### Cache & Consistência
- [x] `_CONFIG_CACHE` 5 min TTL, invalidado em `salvar_config` + `carregar_config` (on miss).
- [x] `sync_pending()` evita `StreamlitAPIException` (widgets com valor pendente).
- [x] `restore_ideia_if_empty()` salva-vidas para race condition Passo 1.
- [x] `on_change` + backup no Passo 1, restore + backup antes da IA no Passo 4.

### Fidelity Guards (Anti-Resumo)
- [x] `SYS_MESTRE_CORE`: proibição absoluta de resumos (FIDELIDADE 100%).
- [x] Negativo dinâmico: regra dos antônimos (não negações).
- [x] Franquias/personagens preservados literalmente.
- [x] `SYS_LEITOR_PARAMETRICO`: extração forense 5 campos densos.
- [x] Vision: `VISAO_FATOR_FIDELIDADE`, tetos por campo, `PROIBIDO RESUMIR` no prompt.

---

## ✅ Documentação

- [x] `docs/SECRETS_SETUP.md` — secrets.toml, PS_FERNET_KEY, Apps Script deploy, planilha, Streamlit Cloud.
- [x] `docs/E2E_TEST_PROCEDURE.md` — 14 seções: smoke, login, conexão, passos 0-5, resiliência, multi-destino, logout, critérios beta.
- [x] `docs/BETA_CHECKLIST.md` — Este arquivo.

---

## ✅ Verificação Técnica (CI Local)

```bash
# 1. Sintaxe (py_compile)
python -m py_compile app.py src/*.py src/ui/*.py

# 2. Imports (sem erro de módulo)
python -c "import app; print('app OK')"
python -c "from src import text_engines, vision, config_store, auth, crypto; print('src OK')"
python -c "from src.ui import steps, sidebar; print('ui OK')"

# 3. Estado inicializa
python -c "
import streamlit as st
from core.state import init_state
init_state()
print('State keys:', len(st.session_state))
"

# 4. Config carrega (sem secrets reais)
python -c "
from src.config_store import carregar_config
cfg = carregar_config('teste@email.com')
print('Config type:', type(cfg), 'keys:', list(cfg.keys()) if cfg else 'empty')
"
```

✅ Todos passam sem erros.

---

## ✅ Testes Manuais (Executados)

| Área | Status | Observação |
|------|--------|------------|
| Login planilha válida | ✅ | Expiração futura OK |
| Login planilha expirada | ✅ | Erro "Não autorizado" |
| Login e-mail inexistente | ✅ | Erro "E-mail não encontrado" |
| Centro Conexão salva local | ✅ | `config/config_<hash>.json` criptografado |
| Centro Conexão salva nuvem | ✅ | Apps Script HMAC verify + planilha coluna C |
| Passo 0 troca destino | ✅ | Limpa síntese, mantém visão |
| Passo 2 visão extrai 5 campos | ✅ | JSON denso, preenche Ideia |
| Passo 2 detalhador editável | ✅ | Botão atualiza Ideia |
| Passo 1 text_area blur commit | ✅ | `on_change` dispara |
| Passo 4 rascunho diff visual | ✅ | ps-user-word / ps-ai-word |
| Passo 4 auditoria badges | ✅ | 5 cores, sugestões checkbox |
| Passo 5 prompt final | ✅ | Fidelidade, negativo, hashtags, formato |
| Multi-destino (3+) | ✅ | ComfyUI, Midjourney, Flux, Ideogram |
| Erro 429 amigável | ✅ | "Limite de uso atingido" |
| Erro 404 amigável | ✅ | "Modelo não encontrado" |
| Erro timeout amigável | ✅ | "Tempo limite esgotado" |
| Retry + fallback modelos | ✅ | 3.5→3.6→3.7 |
| Logout + persistência | ✅ | Chaves recarregam do cache/nuvem |
| Cache 5 min invalida | ✅ | `salvar_config` limpa `_CONFIG_CACHE` |

---

## 🚀 Critérios de Go/No-Go para Beta

| Critério | Obrigatório? | Status |
|----------|--------------|--------|
| Zero erros `py_compile` | ✅ Sim | ✅ |
| Zero `StreamlitAPIException` em fluxo normal | ✅ Sim | ✅ |
| Auth planilha + Apps Script funcional | ✅ Sim | ✅ |
| HMAC request/response verificado | ✅ Sim | ✅ |
| Cache 5 min + invalidação | ✅ Sim | ✅ |
| Vision extrai 5 campos sem resumo | ✅ Sim | ✅ |
| Texto: fidelidade 100% + negativo dinâmico | ✅ Sim | ✅ |
| 4+ destinos com formato correto | ✅ Sim | ✅ |
| Erros amigáveis + diagnóstico | ✅ Sim | ✅ |
| Docs beta completas | ✅ Sim | ✅ |
| Commit + tag `beta-YYYYMMDD` | ✅ Sim | ⏳ Pendente |

---

## 📦 Próximos Passos (Pós-Checklist)

1. `git add -A && git commit -m "beta: ready for beta testing - $(date +%F)"`
2. `git tag beta-$(date +%Y%m%d)`
3. `git push origin main --tags`
4. Deploy Streamlit Cloud (separado) apontando para `main`.
5. Distribuir `SECRETS_SETUP.md` + `E2E_TEST_PROCEDURE.md` para testadores beta.
6. Coletar feedback → issues → patch → `beta-YYYYMMDD-v2` se necessário.

---

**Assinatura**: _______________  **Data**: _______________  **Versão**: `beta-YYYYMMDD`