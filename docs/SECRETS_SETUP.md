# Guia de Configuração de Segredos (Secrets)

## Visão Geral

O Prompt Studio usa **criptografia client-side (Fernet)** + **assinatura HMAC-SHA256** para proteger as chaves BYOK dos usuários. A mesma chave mestra (`PS_FERNET_KEY`) deve estar configurada no:

1. **Streamlit Local/Cloud** → `.streamlit/secrets.toml`
2. **Google Apps Script** → Propriedade de script `HMAC_KEY`

---

## 1. Gerar a Chave Mestra (PS_FERNET_KEY)

### Opção A: OpenSSL (Linux/macOS/Git Bash/WSL)
```bash
openssl rand -base64 32
# Exemplo: l-xh7kSMXEc7fAvRpnjG-celm8v6URPsyJTzDGSMoO0=
```

### Opção B: Python (Windows PowerShell)
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Opção C: Node.js
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64').replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,''))"
```

**Importante:** A chave deve ser **url-safe base64** (44 chars, termina com `=`). Guarde-a com segurança — quem tem essa chave pode descriptografar configs.

---

## 2. Configurar Local (.streamlit/secrets.toml)

```bash
# No repo do projeto
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edite `.streamlit/secrets.toml` com seus valores reais:

```toml
PS_FERNET_KEY = "sua-chave-base64-aqui"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/SEU_DEPLOYMENT_ID/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_VITALICIO = "https://pay.kiwify.com.br/..."
```

---

## 3. Configurar Google Apps Script

### 3.1 Planilha (JÁ EXISTE)

**ID:** `180xWEBt4Lu8dqHQCBIwfyMgYA1vdN8eD1FehK-aiXLI`
**URL:** https://docs.google.com/spreadsheets/d/180xWEBt4Lu8dqHQCBIwfyMgYA1vdN8eD1FehK-aiXLI/edit

Verifique se a aba se chama **`Assinaturas`** com cabeçalhos:
- A1: `Email`
- B1: `Expiracao`
- C1: `Config`

Adicione usuários beta (ver seção 5).

### 3.2 Criar Projeto Apps Script
1. Acesse [script.google.com](https://script.google.com)
2. `Novo projeto` → "Prompt Studio Backend"
3. Substitua `Code.gs` pelo conteúdo de `apps_script/Code.gs` (o **SHEET_ID já está preenchido**)
4. **Substitua apenas o placeholder**:
   ```javascript
   const HMAC_KEY = "SUA_PS_FERNET_KEY_AQUI";  // IGUAL à do secrets.toml
   ```

### 3.3 Definir Propriedade de Script (Opcional - mais seguro)
Em vez de hardcoded no código:
1. No Apps Script: `Configurações do projeto` → `Propriedades do script`
2. `Adicionar propriedade`: `HMAC_KEY` = sua chave
3. No código: `const HMAC_KEY = PropertiesService.getScriptProperties().getProperty('HMAC_KEY');`

### 3.4 Deploy como Web App
1. `Implantar` → `Nova implantação`
2. Tipo: **Aplicativo da Web**
3. **Executar como**: Eu
4. **Quem tem acesso**: Qualquer pessoa
5. `Implantar` → Autorize
6. Copie a **URL** → cole no `APPS_SCRIPT_URL` do secrets.toml

---

## 4. Streamlit Community Cloud (Produção)

1. No dashboard do app → `Settings` → `Secrets`
2. Cole o conteúdo completo do `.streamlit/secrets.toml` (valores reais)
3. `Save` → o app reinicia automaticamente

---

## 5. Adicionar Usuários de Teste (Planilha)

Na aba `Assinaturas`, adicione linhas:

| Email | Expiracao | Config |
|-------|-----------|--------|
| teste@exemplo.com | 2026-12-31 23:59:59 | {} |
| beta@user.com | 2026-11-30 23:59:59 | {} |

**Formato data:** `YYYY-MM-DD HH:MM:SS` (24h)

---

## 6. Verificar Funcionamento

### Teste Local
```bash
cd D:/recuperacao/hermes bkp/Gerador-de-Prompt
.venv/Scripts/python.exe -c "
from src.auth import verificar_acesso_sheets
ok, exp, err = verificar_acesso_sheets('teste@exemplo.com')
print(f'OK: {ok} | Exp: {exp} | Err: {err}')
"
```

Deve retornar: `OK: True | Exp: 2026-12-31 23:59:59 | Err: None`

### Teste HMAC
```bash
.venv/Scripts/python.exe -c "
from src.config_store import _hmac_sign, _hmac_verify
payload = 'teste'
sig = _hmac_sign(payload)
print('Sign:', sig)
print('Verify:', _hmac_verify(payload, sig))
print('Tampered:', _hmac_verify(payload + 'x', sig))
"
```

Deve retornar: `Verify: True` e `Tampered: False`

---

## 7. Rotacionar Chave (Emergência)

Se a chave vazar:

1. Gere nova chave (`openssl rand -base64 32`)
2. Atualize no **Apps Script** (`HMAC_KEY`) + redeploy
3. Atualize no **Streamlit Cloud** (`PS_FERNET_KEY`)
4. **Configs antigas ficam ilegíveis** — usuários precisarão reinserir chaves BYOK
5. Invalide sessões ativas (mude `PS_FERNET_KEY` força logout)

---

## Checklist Pré-Beta

- [ ] `PS_FERNET_KEY` gerada e idêntica nos dois lados
- [ ] `APPS_SCRIPT_URL` aponta para deploy "Anyone" ativo
- [ ] Planilha `Assinaturas` criada com cabeçalhos corretos
- [ ] Pelo menos 2 e-mails de teste com expiração futura na planilha
- [ ] Teste local `verificar_acesso_sheets()` retorna `OK: True`
- [ ] Teste HMAC sign/verify passa
- [ ] `.streamlit/secrets.toml` **NÃO** está no git (verifique `.gitignore`)
- [ ] Streamlit Cloud secrets configurados
- [ ] Links Kiwify reais na página de login