# Bypass local do login — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Botão "🔓 Entrar (app local)" que entra sem e-mail e sem planilha, habilitado só por flag não versionada.

**Architecture:** Flag `LOCAL_BYPASS` no `.streamlit/secrets.toml` gateia um botão em cada um dos dois pontos de login (`render_login_page` e `_render_sidebar_login`). A sessão recebe a identidade fixa `LOCAL_EMAIL`; o `config_store` pula qualquer chamada ao Apps Script para esse e-mail, e a config existente é migrada por cópia de arquivo (hash de e-mail é unidirecional, mas não precisa do e-mail original).

**Tech Stack:** Streamlit (session_state, st.secrets), Python 3.14 stdlib, testes via `test_suite.py` (não pytest).

**Spec:** `docs/superpowers/specs/2026-11-23-bypass-local-login-design.md` (aprovada no chat em 2026-11-23)

## Global Constraints

- Runner de teste: `.venv/Scripts/python.exe test_suite.py` (exit code é a verdade).
- `py_compile` IMEDIATO após cada patch de Python (pitfall conhecido de indentação mangueada).
- Nenhum import dentro de corpo de função em `src/config_store.py` / `src/ui/steps.py` — imports no topo do módulo.
- Não alterar: fluxo do 🚀 Entrar com e-mail, `verificar_acesso_sheets`, listas de modelo (3.5/3.6/3.7-flash).
- `secrets.toml` e `config/` são gitignored — flag e migração NUNCA entram no commit.
- Push para `origin/main` ao final (exigência do usuário).
- Strings exatas fixadas pela spec: `LOCAL_EMAIL = "local@prompt-studio.local"`, `EXPIRACAO = "Local — sem validação"`, rótulo `🔓 Entrar (app local)`, flag `LOCAL_BYPASS`.

## Review Focus

1. **Clone sem a flag** → botão deve estar ausente e o login normal intacto. Teste: Task 2 (assert do gate no fonte) + Task 4 GUI baseline sem flag.
2. **Chaves BYOK somem no bypass** → a migração deve preservá-las. Teste: Task 3 (`carregar_config(LOCAL_EMAIL)` não-vazio, comportamental) + Task 4 GUI (cockpit sem `st.info("💡 Conecte suas chaves…")`).
3. **POST acidental na planilha com o e-mail-fixo** → guardas em `carregar_config` e `salvar_config`. Teste: Task 1 (asserts de fonte nos dois) — não fazer teste comportamental de `salvar_config`, porque sem o guard ele POSTaria de verdade.
4. **Flag presente mas secrets ilegível** → `_local_bypass_ativo` deve retornar False sem derrubar a página (try/except). Teste: Task 2 (assert do try/except no fonte) + Task 4 GUI (ausência do botão sem exceção visível).
5. **Logout após bypass** → `EXPIRACAO` como string nunca é parseada (só é setada/limpa); logout limpa a sessão e a tela de login volta com o botão. Teste: Task 4 GUI (logout → botão presente → reentra).

---

### Task 1: `LOCAL_EMAIL` + guardas de nuvem no `config_store` (teste primeiro)

**Files:**
- Modify: `core/state.py` (constante perto das chaves de estado)
- Modify: `src/config_store.py:178` (`if APPS_SCRIPT_URL:` de `carregar_config`) e `src/config_store.py:255` (o mesmo em `salvar_config`)
- Test: `test_suite.py` (novo grupo 11, inserido após o grupo 10 e antes do banner)

**Interfaces:**
- Produces: `LOCAL_EMAIL: str` em `core/state.py` — valor exato `"local@prompt-studio.local"`; consumido por `config_store` (guardas) e, na Task 2, por `sidebar`.

- [ ] **Step 1: Escrever o teste falhando** — adicionar ao `test_suite.py`, após `print('   OK Nenhum segredo/credencial hardcoded nos fontes')` + `print()`:

```python
# 11. BYPASS LOCAL
print('11. BYPASS LOCAL')
from core.state import LOCAL_EMAIL
assert LOCAL_EMAIL == 'local@prompt-studio.local', 'LOCAL_EMAIL deve ser o e-mail-fixo da spec'
import src.config_store as _cs
assert 'LOCAL_EMAIL' in inspect.getsource(_cs.carregar_config), 'carregar_config deve pular a nuvem p/ LOCAL_EMAIL'
assert 'LOCAL_EMAIL' in inspect.getsource(_cs.salvar_config), 'salvar_config deve pular a nuvem p/ LOCAL_EMAIL'
print('   OK LOCAL_EMAIL + guardas de nuvem no config_store')
print()
```

(`inspect` já é importado no grupo 7.)

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `./.venv/Scripts/python.exe test_suite.py`
Expected: traceback `ImportError: cannot import name 'LOCAL_EMAIL' from 'core.state'` (exit ≠ 0)

- [ ] **Step 3: Implementar**

Em `core/state.py`, logo após a classe `StateKeys` (nível módulo):

```python
# Identidade fixa do bypass local (sem planilha) — ver specs/2026-11-23-bypass-local-login-design.md
LOCAL_EMAIL = "local@prompt-studio.local"
```

Em `src/config_store.py`, no topo (junto aos imports, após `from src.crypto import ...`):

```python
from core.state import LOCAL_EMAIL
```

Nos dois pontos, trocar `if APPS_SCRIPT_URL:` por `if APPS_SCRIPT_URL and email != LOCAL_EMAIL:` (linha ~178 em `carregar_config`, linha ~255 em `salvar_config`). Em `salvar_config`, o fluxo então cai direto no `return True, None` final (local já foi salvo).

- [ ] **Step 4: Rodar e confirmar a passagem**

Run: `./.venv/Scripts/python.exe -m py_compile core/state.py src/config_store.py && ./.venv/Scripts/python.exe test_suite.py`
Expected: exit 0, grupo 11 imprime `OK LOCAL_EMAIL + guardas de nuvem no config_store`, banner `TODOS OS TESTES PASSARAM`

- [ ] **Step 5: Commit**

```bash
git add core/state.py src/config_store.py test_suite.py
git commit -m "feat: LOCAL_EMAIL + guardas de nuvem no config_store (bypass local, preparo)"
```

---

### Task 2: Botão de bypass nas duas telas de login

**Files:**
- Modify: `src/ui/sidebar.py` (import de `LOCAL_EMAIL`, dois helpers, dois botões)
- Test: `test_suite.py` (continuação do grupo 11)

**Interfaces:**
- Consumes: `LOCAL_EMAIL` (Task 1), `StateKeys.AUTENTICADO/USER_EMAIL/EXPIRACAO`
- Produces: `_local_bypass_ativo() -> bool` e `_entrar_bypass_local() -> None` em `src/ui/sidebar.py`

- [ ] **Step 1: Escrever o teste falhando** — após o assert do grupo 11 existente, adicionar:

```python
_side_src = open('src/ui/sidebar.py', encoding='utf-8').read()
assert 'def _local_bypass_ativo' in _side_src, 'helper de gate ausente'
assert 'except Exception' in _side_src.split('def _local_bypass_ativo')[1].split('def _entrar_bypass_local')[0], '_local_bypass_ativo deve tolerar secrets ilegível (try/except -> False)'
assert _side_src.count('Entrar (app local)') >= 2, 'botão nas DUAS telas de login (principal e sidebar)'
assert 'LOCAL_BYPASS' in _side_src, 'botão deve ser gateado pela flag LOCAL_BYPASS'
print('   OK bypass: gate + botao nas duas telas de login')
print()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `./.venv/Scripts/python.exe test_suite.py`
Expected: AssertionError `helper de gate ausente` (exit ≠ 0)

- [ ] **Step 3: Implementar em `src/ui/sidebar.py`**

- Trocar o import: `from core.state import StateKeys, DEFAULTS` → `from core.state import StateKeys, DEFAULTS, LOCAL_EMAIL`.
- Após `_processar_login`, adicionar (corpos exatos, fixados pela spec):

```python
def _local_bypass_ativo() -> bool:
    """Bypass local habilitado apenas pela flag LOCAL_BYPASS no secrets.toml (não versionado)."""
    try:
        return bool(st.secrets.get("LOCAL_BYPASS", False))
    except Exception:
        return False


def _entrar_bypass_local() -> None:
    """Entra direto, sem e-mail nem planilha — identidade fixa LOCAL_EMAIL (app local)."""
    st.session_state[StateKeys.AUTENTICADO] = True
    st.session_state[StateKeys.USER_EMAIL] = LOCAL_EMAIL
    st.session_state[StateKeys.EXPIRACAO] = "Local — sem validação"
    st.rerun()
```

- Em `render_login_page`, logo após o botão `🚀 Entrar`:

```python
    if _local_bypass_ativo() and st.button("🔓 Entrar (app local)", use_container_width=True):
        _entrar_bypass_local()
```

- Em `_render_sidebar_login`, após o botão `Entrar`, o mesmo bloco (e atualizar o docstring `"… — via Sheets, sem bypass."` para `"… — via Sheets; bypass local só com flag LOCAL_BYPASS."`).

- [ ] **Step 4: Rodar e confirmar a passagem**

Run: `./.venv/Scripts/python.exe -m py_compile src/ui/sidebar.py && ./.venv/Scripts/python.exe test_suite.py`
Expected: exit 0, novo `OK bypass: gate + botao nas duas telas de login`

- [ ] **Step 5: Commit**

```bash
git add src/ui/sidebar.py test_suite.py
git commit -m "feat: botao 'Entrar (app local)' nas duas telas de login, gateado por LOCAL_BYPASS"
```

---

### Task 3: Migração da config existente + teste comportamental

**Files:**
- Setup (não commita): cópia em `config/` (gitignored)
- Test: `test_suite.py` (fim do grupo 11)

**Interfaces:**
- Produces: `config/<sha256(LOCAL_EMAIL)[:16]>.json` existente e destravável por `carregar_config(LOCAL_EMAIL)`

- [ ] **Step 1: Escrever o teste falhando** — adicionar no fim do grupo 11:

```python
assert _cs._config_path(LOCAL_EMAIL).exists(), 'migração da config local não feita'
_cfg_local = _cs.carregar_config(LOCAL_EMAIL)
assert isinstance(_cfg_local, dict) and _cfg_local, 'config do bypass deve carregar (chaves preservadas)'
print('   OK config migrada e carregando pelo e-mail-fixo')
print()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `./.venv/Scripts/python.exe test_suite.py`
Expected: AssertionError `migração da config local não feita`

- [ ] **Step 3: Migrar (cópia única, uma linha de raciocínio: o Fernet não amarra o e-mail ao blob)**

```bash
./.venv/Scripts/python.exe -c "import hashlib, pathlib, shutil; d=pathlib.Path('config'); h=hashlib.sha256(b'local@prompt-studio.local').hexdigest()[:16]; src=d/'config_327495aaff5267ba.json'; dst=d/f'config_{h}.json'; shutil.copy2(src,dst) if src.exists() and not dst.exists() else None; print('dst:', dst, 'exists:', dst.exists())"
```

Expected: `exists: True`

- [ ] **Step 4: Rodar e confirmar a passagem**

Run: `./.venv/Scripts/python.exe test_suite.py`
Expected: exit 0, `OK config migrada e carregando pelo e-mail-fixo`, banner verde

- [ ] **Step 5: Commit (só o teste — config/ é gitignored)**

```bash
git add test_suite.py
git commit -m "test: bypass local - migração e carga da config pelo e-mail-fixo"
git status --porcelain   # esperado: NADA de config/ nem secrets.toml
```

---

### Task 4: Verificação GUI real (sem flag → com flag) + push

**Files:**
- Modify (local, não commita): `.streamlit/secrets.toml` (+`LOCAL_BYPASS = true`)
- Skill: atualizar `prompt-studio-development` ao final

- [ ] **Step 1: Baseline sem flag — reiniciar servidor e conferir que NADA mudou**

```bash
taskkill -PID <pid-da-porta-8501> -F   # pegar via netstat; módulos ficam em cache — restart é obrigatório
```

Relançar `./.venv/Scripts/python.exe -m streamlit run app.py --server.headless true --server.port 8501` (background) e na GUI real (mouse real): `http://localhost:8501` → tela de login **sem** o botão 🔓, sem exceção visível; clicar 🚀 com campo vazio → `Digite seu e-mail.` (fluxo normal intacto).

- [ ] **Step 2: Ligar a flag e reiniciar**

Adicionar ao fim de `.streamlit/secrets.toml`: `LOCAL_BYPASS = true` → matar servidor → relançar → recarregar a página.

- [ ] **Step 3: GUI com flag — clique real no bypass**

Conferir: botão `🔓 Entrar (app local)` presente na página principal **e** na sidebar; clique real (mouse) → cockpit renderiza (Passos 0–5), e **não** aparece `💡 Conecte suas chaves…` (prova de que a config migrou carregou as chaves); sidebar mostra `Logado: ***…`. Logout → volta à tela de login com o botão → clica de novo → entra. Screenshot de evidência.

- [ ] **Step 4: Verificação final combinada**

Run: `./.venv/Scripts/python.exe test_suite.py` → exit 0 sem FALHA; `py_compile` dos arquivos tocados; `git status` limpo; `git push origin main`.

- [ ] **Step 5: Atualizar a skill `prompt-studio-development`**

Registrar: bypass local (flag `LOCAL_BYPASS` em secrets não versionado, `LOCAL_EMAIL`, guardas no `config_store`), que `secrets.toml`/`config/` nunca entram em commit, e que trocar flag/secrets exige restart do servidor (cache de módulos).
