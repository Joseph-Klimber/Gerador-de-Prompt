# Deploy do Apps Script (Produção)

## Pré-requisitos

- Conta Google (mesma do Streamlit Cloud / Sheets)
- Planilha Google Sheets com aba `Assinaturas` (colunas: Email | Expiracao | Config)
- `PS_FERNET_KEY` configurada no Streamlit secrets (32-byte url-safe base64, 44 chars)

---

## 1. Preparar a Planilha

1. Abra [sheets.google.com](https://sheets.google.com) → Nova planilha
2. Renomeie a aba para **`Assinaturas`**
3. Cabeçalhos na linha 1:
   | Email | Expiracao | Config |
   |-------|-----------|--------|
   | (e-mail do usuário) | `YYYY-MM-DD HH:MM:SS` (24h, UTC-3) | (deixe vazio — o app preenche) |
4. Exemplo de expiração: `2026-12-31 23:59:59`
5. Copie o **ID da planilha** da URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

---

## 2. Criar Projeto Apps Script

1. Acesse [script.google.com](https://script.google.com) → Novo projeto
2. Cole o conteúdo de `apps_script/Code.gs` no editor
3. ⚙️ **Propriedades do script** → Adicionar:
   - `HMAC_KEY` = **exatamente o mesmo valor** de `PS_FERNET_KEY` do `secrets.toml` (inclua padding `=` se houver)
   - `SHEET_ID` = ID copiado no passo 1
4. Salve (Ctrl+S)

> **Importante**: `HMAC_KEY` **deve ser idêntico** ao `PS_FERNET_KEY` do Streamlit (string 44 chars url-safe base64). O Apps Script usa essa string diretamente como chave HMAC (sem base64Decode, sem SHA256 derivação) — contrato compatível com o cliente Python.

---

## 3. Deploy como Web App

1. Deploy → Nova implantação
2. Tipo: **App da Web** (ícone de globo)
3. Configurações:
   - **Descrição**: `Prompt Studio Beta v1`
   - **Executar como**: **Eu** (sua conta)
   - **Quem tem acesso**: **Qualquer pessoa**
4. Clique **Implantar**
5. Autorize o acesso (primeira vez: "Avançado" → "Acessar projeto (inseguro)")
6. Copie a **URL do app da web** gerada (ex: `https://script.google.com/macros/s/AKfycb.../exec`)

---

## 4. Configurar Streamlit

### Local (`.streamlit/secrets.toml`)
```toml
PS_FERNET_KEY = "COLE_A_MESMA_CHAVE_44_CHARS_AQUI"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/SEU_DEPLOY_ID/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/MXVL98k"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/dyfEGe5"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/xo0m3rF"
LINK_KIWIFY_VITALICIO = "#"
```

### Streamlit Cloud
1. App → Settings → Secrets
2. Cole o mesmo conteúdo acima (valores reais, não placeholders)

---

## 5. Testar

### Login (ação `verificar`)
```bash
curl -X POST "SUA_APPS_SCRIPT_URL" \
  -H "Content-Type: application/json" \
  -d '{"action":"verificar","email":"seu@email.com"}'
# Esperado: {"ok":true,"expiracao":"2026-12-31 23:59:59","erro":""}
```

### Salvar config (ação `salvar` — requer HMAC)
O cliente Python assina automaticamente via `X-Signature`. Teste manual requer gerar HMAC:
```python
import hmac, hashlib, base64, json
key = "SUA_PS_FERNET_KEY".encode()
body = '{"action":"salvar","email":"test@x.com","payload":"gAAAAAB..."}'
sig = base64.urlsafe_b64encode(hmac.new(key, body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
curl -X POST "URL" -H "Content-Type: application/json" -H "X-Signature: $sig" -d "$body"
```

### Carregar config (ação `carregar` — requer HMAC + retorna HMAC)
Igual ao acima; resposta inclui `"hmac":"..."` que o cliente verifica.

---

## 6. Rate Limits

- **Por e-mail**: 20 req/min (chave `rate:email:{email}`)
- **Por IP**: 60 req/min (chave `rate:ip:{ip}`)
- Cache TTL: 60s
- IP detectado via `X-Forwarded-For` / `X-Real-IP` → fallback UA hash

---

## 7. Logs Estruturados

Todos os requests logam JSON no Cloud Logging:
```json
{"ts":"2026-11-22T20:45:12.345Z","email":"user@x.com","action":"salvar","ip":"187.x.x.x","ok":true,"latencyMs":142,"error":""}
```
Filtre no Cloud Logging: `resource.type="app_script"`

---

## 8. Atualizações Futuras

- Edite `Code.gs` no editor
- Deploy → **Gerenciar implantações** → Lápis (editar) → Nova versão → **Implantar**
- URL **não muda** entre versões

---

## 9. Rotação de Chave (Emergência)

Se `PS_FERNET_KEY` vazar:
1. Gere nova: `openssl rand -base64 32` (ou `python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`)
2. Atualize `PS_FERNET_KEY` no Streamlit secrets
3. Atualize `HMAC_KEY` nas Propriedades do script Apps Script
4. **Re-deploy** Apps Script (nova versão)
5. **Configs antigas na planilha tornam-se ilegíveis** (Fernet token antigo não descriptografa) — usuários reconectam chaves (BYOK)