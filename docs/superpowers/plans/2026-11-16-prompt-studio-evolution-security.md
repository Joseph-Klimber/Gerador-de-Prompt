# Prompt Studio Evolution — Segurança & Arquitetura (Fase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remover credenciais em plaintext da nuvem (Apps Script/Sheets), adicionar HMAC na API nuvem, desacoplar `core/` do Streamlit, e unificar contratos em SSOT único.

**Architecture:** Client-side encryption antes de enviar payload ao Apps Script; HMAC-SHA256 assinado com Fernet key do usuário; mover `core/state.py` e lógica de sessão para adapter em `src/ui/`; consolidar `schemas.py` duplicado em `core/contracts.py`.

**Tech Stack:** Python 3.11+, Streamlit 1.35+, `cryptography` (Fernet), `google-genai`, `hmac`, `hashlib`.

**Spec:** Relatório de auditoria completo (80 achados) + estratégia SaaS (3 fases). Este plano cobre Fase 1 (Segurança & Arquitetura).

---

## Global Constraints
- Zero alteração no fluxo de login local (bypass mantido para dev).
- `test_suite.py` deve continuar passando 100% após cada commit.
- `py_compile` limpo em todos os `.py` modificados.
- Commits atômicos por task com mensagem convencional (`feat:`, `fix:`, `refactor:`).

## Review Focus
1. **Payload Sheets em plaintext** → Criptografar `dados` no client antes do POST; validar que Apps Script recebe blob cifrado.
2. **API nuvem sem autenticação** → HMAC obrigatório no header; Apps Script rejeita sem assinatura válida.
3. **`core/` importando Streamlit** → `core/state.py` e `prompt_builder.py` puros; adapters em `src/ui/state_adapter.py`.
4. **Contratos duplicados** → `schemas.py` órfãos removidos; SSOT único em `core/contracts.py`.
5. **Regex substring frágil** → Substituir `"Fotorrealismo" in text` por `Enum`/`constante` do SSOT.

---

### Task 1: Criptografia Client-Side no `config_store.py`

**Files:**
- Modify: `src/config_store.py:30-110`
- Test: `test_suite.py` (existente: `test_config_store_roundtrip`)

**Interfaces:**
- Consumes: `_encrypt(data: dict) -> str`, `_decrypt(token: str) -> dict` já existentes
- Produces: `salvar_config(email, dados)` envia `{"action": "salvar", "email": email, "payload": encrypted_blob}`; `carregar_config(email)` descriptografa `payload` antes de retornar.

- [ ] **Step 1: Write failing test**
```python
def test_config_store_encrypts_payload_before_sending(monkeypatch):
    captured = {}
    def mock_post(url, json, timeout):
        captured['payload'] = json
        class R: status_code = 200; text = '{"ok": true}'
        return R()
    monkeypatch.setattr("urllib.request.urlopen", lambda req: mock_post(req.full_url, json.loads(req.data.decode()), 10))
    from src.config_store import salvar_config
    salvar_config("test@test.com", {"chaves": {"Chave Visao": "sk-test"}})
    assert "payload" in captured
    # payload deve ser string Fernet, não dict com chaves em claro
    assert isinstance(captured['payload'], str)
    assert "sk-test" not in captured['payload']
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_config_store_encrypts_payload_before_sending -v`
Expected: FAIL (test doesn't exist yet; current `salvar_config` sends plaintext)

- [ ] **Step 3: Implement encryption in `salvar_config` / `carregar_config`**
Em `src/config_store.py`:
- `salvar_config`: `encrypted = _encrypt(dados)` → POST `{"action": "salvar", "email": email, "payload": encrypted}`
- `carregar_config`: response JSON tem `payload` → `_decrypt(payload)` → retorna dict
- Manter compatibilidade: se response não tem `payload` (dados legados), tentar ler `config` direto (fallback temporário com log warning).

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_config_store_encrypts_payload_before_sending -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/config_store.py test_suite.py
git commit -m "feat: client-side encryption for cloud config payload (Fernet)"
```

---

### Task 2: HMAC Assinado na API Apps Script

**Files:**
- Modify: `src/config_store.py:30-110` (client)
- Modify: `APPS_SCRIPT_CODE.gs` (server)
- Test: `test_suite.py` (novo: `test_hmac_signature`)

**Interfaces:**
- Consumes: `PS_FERNET_KEY` (base64 url-safe 44 chars) derivável para HMAC key
- Produces: Header `X-Signature: <base64_hmac_sha256>` em requests; Apps Script valida e rejeita 401 se inválido.

- [ ] **Step 1: Write failing test**
```python
def test_hmac_signature_on_requests(monkeypatch):
    captured = {}
    def mock_post(url, json, timeout):
        captured['headers'] = dict(monkeypatch._original_headers if hasattr(monkeypatch, '_original_headers') else {})
        class R: status_code = 200; text = '{"ok": true}'
        return R()
    # interceptar headers adicionados pelo config_store
    import urllib.request
    original_urlopen = urllib.request.urlopen
    def intercept(req):
        captured['headers'] = dict(req.headers)
        return original_urlopen(req)
    monkeypatch.setattr("urllib.request.urlopen", intercept)
    from src.config_store import salvar_config
    salvar_config("test@test.com", {"chaves": {}})
    assert "X-Signature" in captured['headers']
    # validar formato base64
    import base64
    base64.b64decode(captured['X-Signature'])  # não deve lançar
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_hmac_signature_on_requests -v`
Expected: FAIL

- [ ] **Step 3: Implement HMAC client-side + server-side**
Client (`src/config_store.py`):
```python
def _hmac_sign(payload: str) -> str:
    key = _get_ps_fernet_key()  # já existe
    hmac_key = hashlib.sha256(key.encode()).digest()
    sig = hmac.new(hmac_key, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")
```
Adicionar header `X-Signature` no request POST.

Server (`APPS_SCRIPT_CODE.gs`):
```javascript
function verifyHmac(payload, signatureHeader) {
  var key = PropertiesService.getScriptProperties().getProperty('HMAC_KEY'); // mesmo PS_FERNET_KEY
  var hmacKey = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, key);
  var expected = Utilities.computeHmacSignature(Utilities.MacAlgorithm.HMAC_SHA_256, payload, hmacKey);
  var provided = Utilities.base64Decode(signatureHeader.replace(/-/g, '+').replace(/_/g, '/'));
  return Utilities.base64Encode(expected) === Utilities.base64Encode(provided);
}
```
Em `doPost(e)`: validar header `X-Signature` antes de processar; retornar 401 se falhar.

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_hmac_signature_on_requests -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/config_store.py APPS_SCRIPT_CODE.gs test_suite.py
git commit -m "feat: HMAC-SHA256 signing for cloud config API"
```

---

### Task 3: Desacoplar `core/` do Streamlit — `core/state.py` → `src/ui/state_adapter.py`

**Files:**
- Create: `src/ui/state_adapter.py`
- Modify: `core/state.py` (remover `import streamlit as st`, tornar funções puras)
- Modify: `src/ui/steps.py`, `src/ui/sidebar.py`, `app.py` (usar adapter)
- Test: `test_suite.py` (existentes: `test_state_*` + novos)

**Interfaces:**
- Consumes: `core.state` funções puras recebendo/devolvendo `dict` ou `AppState`
- Produces: `src.ui.state_adapter` com `get_state()`, `set_state()`, `sync_pending()`, `backup_ideia()`, `restore_ideia_if_empty()` que leem/escrevem `st.session_state`.

- [ ] **Step 1: Write failing test**
```python
def test_core_state_pure_no_streamlit_import():
    import core.state as cs
    import inspect
    source = inspect.getsource(cs)
    assert "import streamlit" not in source
    assert "st.session_state" not in source

def test_state_adapter_wraps_session_state(monkeypatch):
    import streamlit as st
    st.session_state = {}
    from src.ui.state_adapter import init_state, sync_pending
    init_state()
    assert "ck_ideia_input" in st.session_state
    st.session_state["_pending_ck_ideia_input"] = "teste"
    sync_pending()
    assert st.session_state["ck_ideia_input"] == "teste"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_core_state_pure_no_streamlit_import -v`
Expected: FAIL (atualmente importa streamlit)

- [ ] **Step 3: Implement**
1. Criar `src/ui/state_adapter.py` copiando lógica de `core/state.py` mas usando `st.session_state` diretamente.
2. Reescrever `core/state.py`: funções recebem `state: dict` como parâmetro, retornam `dict` atualizado. `DEFAULTS` vira constante pura. `AppState` dataclass movida para `core/contracts.py` (Task 4).
3. Atualizar `steps.py`, `sidebar.py`, `app.py` para importar `src.ui.state_adapter as sa` e chamar `sa.sync_pending()`, `sa.backup_ideia()`, etc.

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_core_state_pure_no_streamlit_import test_suite.py::test_state_adapter_wraps_session_state -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add core/state.py src/ui/state_adapter.py src/ui/steps.py src/ui/sidebar.py app.py test_suite.py
git commit -m "refactor: decouple core/state from Streamlit; add ui adapter"
```

---

### Task 4: Unificar Contratos — `core/contracts.py` (SSOT único)

**Files:**
- Create: `core/contracts.py`
- Delete: `schemas.py` (após migração)
- Modify: `core/destination.py`, `core/prompt_builder.py`, `core/state.py` (importar de `contracts`)
- Modify: `src/ui/state_adapter.py`, `src/ui/steps.py`, `src/ui/sidebar.py`
- Test: `test_suite.py` (existentes + `test_contracts_import`)

**Interfaces:**
- Produces: `DestinationProfile`, `PromptContext`, `StateKeys` (como `Enum`), `AppState` (dataclass frozen) em `core.contracts`.

- [ ] **Step 1: Write failing test**
```python
def test_contracts_single_source():
    from core.contracts import DestinationProfile, PromptContext, StateKeys, AppState
    # todos importam do mesmo módulo
    assert DestinationProfile.__module__ == "core.contracts"
    assert PromptContext.__module__ == "core.contracts"
    # StateKeys é Enum
    import enum
    assert issubclass(StateKeys, enum.Enum)
    # AppState é frozen
    import dataclasses
    assert dataclasses.is_dataclass(AppState)
    assert AppState.__dataclass_params__.frozen == True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_contracts_single_source -v`
Expected: FAIL (arquivo não existe)

- [ ] **Step 3: Implement**
1. Criar `core/contracts.py` consolidando:
   - `DestinationProfile` (de `core/destination.py` + `schemas.py`) — campos `tuple[str, ...]` imutáveis.
   - `PromptContext` (de `core/prompt_builder.py` + `schemas.py`).
   - `StateKeys` como `StrEnum` (Python 3.11+) com todos os valores de `core/state.py:DEFAULTS` keys.
   - `AppState` frozen dataclass com campos tipados correspondentes a `StateKeys`.
2. Atualizar imports em `core/destination.py`, `core/prompt_builder.py`, `core/state.py`, `src/ui/state_adapter.py`, `src/ui/steps.py`, `src/ui/sidebar.py`.
3. Remover `schemas.py` (após confirmar zero referências restantes).

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_contracts_single_source -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add core/contracts.py core/destination.py core/prompt_builder.py core/state.py src/ui/state_adapter.py src/ui/steps.py src/ui/sidebar.py test_suite.py
git rm schemas.py
git commit -m "refactor: unify contracts in core/contracts.py (SSOT); remove schemas.py"
```

---

### Task 5: Substituir Substring Matching por Enum `EstiloConversao`

**Files:**
- Modify: `core/contracts.py` (adicionar `EstiloConversao` Enum)
- Modify: `config.py` (usar Enum no `OPCOES_ESTILO_CONVERSAO`)
- Modify: `core/prompt_builder.py:117,123`, `src/vision.py:159,161,163`
- Test: `test_suite.py` (novo: `test_estilo_conversao_enum`)

**Interfaces:**
- Produces: `EstiloConversao` Enum com valores normalizados (`FOTORREALISMO`, `ANIME`, `ANTI_PORCELANA`, etc.); lógica usa `ctx.estilo_conversao == EstiloConversao.FOTORREALISMO`.

- [ ] **Step 1: Write failing test**
```python
def test_estilo_conversao_enum_no_substring():
    from core.contracts import EstiloConversao
    from core.prompt_builder import _inject_style_blocks
    # verificar que não há "Fotorrealismo" in string no source
    import inspect
    src = inspect.getsource(_inject_style_blocks)
    assert "Fotorrealismo" not in src
    assert "Anti-Porcelana" not in src
    assert "EstiloConversao.FOTORREALISMO" in src or "EstiloConversao.FOTORREALISMO" in src
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_estilo_conversao_enum_no_substring -v`
Expected: FAIL

- [ ] **Step 3: Implement**
1. Em `core/contracts.py`: `class EstiloConversao(StrEnum): FOTORREALISMO = "fotorrealismo"; ANIME = "anime"; ANTI_PORCELANA = "anti_porcelana"; ...`
2. Em `config.py`: `OPCOES_ESTILO_CONVERSAO` usa `EstiloConversao` values; labels de UI mapeiam para Enum.
3. Em `prompt_builder.py` e `vision.py`: substituir `if "Fotorrealismo" in ctx.estilo_conversao:` por `if ctx.estilo_conversao == EstiloConversao.FOTORREALISMO:` (ou `.value` se string).

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_estilo_conversao_enum_no_substring -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add core/contracts.py config.py core/prompt_builder.py src/vision.py test_suite.py
git commit -m "refactor: replace fragile substring matching with EstiloConversao Enum"
```

---

### Task 6: Limpeza de Código Morto e Lixo

**Files:**
- Delete: `src/ui/cockpit.py`, `src/ui/landing.py` (stubs vazios)
- Delete: `nul` (raiz)
- Modify: `src/text_engines.py` (remover imports não usados: `OPCOES_SENSUALIDADE`, `MODELO_VISAO_PADRAO`)
- Modify: `src/vision.py` (remover imports não usados: `OPCOES_SENSUALIDADE`, `PISO_CAMPO`, `estimar_tokens`; remover branch morto `genai_errors`)
- Modify: `config.py` (remover `import re` não usado)
- Test: `test_suite.py` (rodar suite completa)

**Interfaces:** Nenhuma nova — apenas remoção.

- [ ] **Step 1: Write failing test**
```python
def test_no_dead_code_imports():
    # grep por imports não usados já removidos
    import subprocess, sys
    result = subprocess.run([sys.executable, "-m", "py_compile", "src/text_engines.py", "src/vision.py", "config.py"], capture_output=True, text=True)
    assert result.returncode == 0
    # verificar que stubs não existem
    assert not os.path.exists("src/ui/cockpit.py")
    assert not os.path.exists("src/ui/landing.py")
    assert not os.path.exists("nul")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_no_dead_code_imports -v`
Expected: FAIL (arquivos existem)

- [ ] **Step 3: Implement** — Remover arquivos e imports conforme lista acima.

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_no_dead_code_imports -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git rm src/ui/cockpit.py src/ui/landing.py nul
git add src/text_engines.py src/vision.py config.py test_suite.py
git commit -m "chore: remove dead code (stubs, unused imports, nul artifact)"
```

---

### Task 7: Validação Client-Side 10MB + Correção HTML Cards + Alinhamento Mensagens de Erro

**Files:**
- Modify: `src/ui/steps.py` (Passo 2: validação tamanho antes de chamar Vision)
- Modify: `src/ui/sidebar.py` (cards `showcase-box`/`plan-container` em único `st.markdown` ou `st.container`)
- Modify: `src/ui/steps.py`, `src/text_engines.py`, `src/auth.py` (11 mensagens exatas do Roteiro)
- Test: `test_suite.py` (novos: `test_upload_10mb_limit`, `test_error_messages_exact`)

**Interfaces:**
- Produces: Upload >10MB bloqueado com mensagem `"Imagem limite: 10 MB."` (exata); cards renderizam sem HTML quebrado; 11 mensagens batem byte-a-byte com Roteiro.

- [ ] **Step 1: Write failing test**
```python
def test_upload_10mb_limit(monkeypatch):
    from src.ui.steps import render_passo_2_visao
    import streamlit as st
    # mock file > 10MB
    class FakeFile:
        size = 11 * 1024 * 1024
        name = "big.png"
        type = "image/png"
        def getvalue(self): return b"x" * self.size
    st.session_state["ck_img_upload"] = FakeFile()
    # deve mostrar erro e NÃO chamar vision
    with patch("src.ui.steps._chamar_motor_visao") as mock_vision:
        render_passo_2_visao()
        mock_vision.assert_not_called()
    # verificar mensagem exata
    assert "Imagem limite: 10 MB." in st.session_state.get("last_error", "")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_upload_10mb_limit -v`
Expected: FAIL

- [ ] **Step 3: Implement**
1. Em `steps.py` Passo 2: verificar `uploaded_file.size > 10*1024*1024` antes de processar; setar erro exato.
2. Em `sidebar.py`: reescrever `showcase-box` e `plan-container` usando `with st.container(): st.markdown(...)` único bloco HTML.
3. Alinhar 11 mensagens (listar no Roteiro vs código) — substituir textos divergentes.

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py::test_upload_10mb_limit test_suite.py::test_error_messages_exact -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/ui/steps.py src/ui/sidebar.py src/text_engines.py src/auth.py test_suite.py
git commit -m "fix: 10MB client-side validation; fix HTML cards; align error messages to Roteiro"
```

---

### Task 8: Suite Completa + Lint + Compilação (Gate Final Fase 1)

**Files:** Nenhum novo — verificação global.

- [ ] **Step 1: Run full test suite**
Run: `.venv/Scripts/python.exe -m pytest test_suite.py -v`
Expected: ALL PASS

- [ ] **Step 2: Lint + Type Check**
Run: `.venv/Scripts/python.exe -m ruff check .` && `.venv/Scripts/python.exe -m mypy . --ignore-missing-imports`
Expected: Zero erros novos (baseline limpo)

- [ ] **Step 3: Syntax Check All**
Run: `.venv/Scripts/python.exe -m py_compile $(find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*")`
Expected: DONE

- [ ] **Step 4: Commit Final Fase 1**
```bash
git add -A
git commit -m "feat: Fase 1 completa — segurança, arquitetura, contratos, limpeza"
```

---

**Fim do Plano Fase 1.**  
Após aprovação, executo task-by-task com `superpowers:executing-plans` (native mode, já que as tasks são sequenciais e dependentes de interfaces).