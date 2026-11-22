# SECRETS_SETUP.md

Guia rápido para configurar secrets do Prompt Studio (local + Streamlit Cloud).

---

## 1. Variáveis obrigatórias no `.streamlit/secrets.toml`

```toml
# Chave Fernet (44 chars url-safe base64). Gere uma vez:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
PS_FERNET_KEY = "SUA_CHAVE_FERNET_AQUI"

# URL do Apps Script implantado como Web App ( 누구나 acesso)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/SEU_SCRIPT_ID/exec"

# Links Kiwify (opcional — fallback hardcoded no código)
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/SEU_ID_15"
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/SEU_ID_30"
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/SEU_ID_90"
```

---

## 2. Geração da `PS_FERNET_KEY`

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- Copie a string de 44 chars (ex: `k8X9mP2qR5vY8wZ3aB4cD6eF7gH1jK2lM3nO4pQ5rS=`)
- **NUNCA** commite no git. Use apenas no `secrets.toml` local e no painel do Streamlit Cloud.

---

## 3. Deploy do Apps Script (`apps_script/Code.gs`)

1. Abra [script.google.com](https://script.google.com) → Novo projeto.
2. Cole o conteúdo de `apps_script/Code.gs`.
3. **Propriedades do script** (⚙️ → Propriedades do script):
   - `HMAC_KEY` = **mesma string da `PS_FERNET_KEY`** (bytes idênticos dos dois lados).
   - `SHEET_ID` = ID da sua planilha Google Sheets (aba `Assinaturas`).
4. Deploy → Nova implantação → **Tipo: App da Web**:
   - Executar como: **Eu**
   - Quem tem acesso: **Qualquer pessoa**
5. Copie a URL gerada → cole no `APPS_SCRIPT_URL` do `secrets.toml`.

---

## 4. Estrutura da Planilha (Google Sheets)

Aba: **`Assinaturas`** (nome exato, case-sensitive)

| Coluna A | Coluna B | Coluna C |
|----------|----------|----------|
| Email | Expiracao | Config |
| `usuario@email.com` | `2025-12-31 23:59:59` | `{...fernet_token...}` |

- Coluna A: e-mail da compra (lowercase normalizado pelo backend).
- Coluna B: data/hora de expiração (ISO ou formato reconhecido por `new Date()`).
- Coluna C: token Fernet (ciphertext) — salvo automaticamente pelo `salvar_config`.

---

## 5. Streamlit Community Cloud

1. No dashboard do app → **Settings → Secrets**.
2. Cole o mesmo conteúdo do `.streamlit/secrets.toml` (sem aspas extras).
3. **Não** suba `.streamlit/secrets.toml` para o git (adicione ao `.gitignore`).

---

## 6. Variáveis de ambiente (alternativa local)

Se preferir não usar `secrets.toml` local, defina no shell antes de rodar:

```bash
export PS_FERNET_KEY="sua_chave"
export APPS_SCRIPT_URL="https://script.google.com/..."
export LINK_KIWIFY_15_DIAS="..."
export LINK_KIWIFY_30_DIAS="..."
export LINK_KIWIFY_90_DIAS="..."
streamlit run app.py
```

---

## 7. Checklist rápido de validação

- [ ] `PS_FERNET_KEY` gerada e idêntica nos dois lados (Python + Apps Script).
- [ ] `APPS_SCRIPT_URL` aponta para deploy **Web App** (não library).
- [ ] Apps Script: "Executar como: Eu" + "Quem tem acesso: Qualquer pessoa".
- [ ] Planilha tem aba `Assinaturas` com cabeçalhos `Email | Expiracao | Config`.
- [ ] `SHEET_ID` nas propriedades do script OU constante no código.
- [ ] `HMAC_KEY` nas propriedades do script = `PS_FERNET_KEY`.
- [ ] Secrets no Streamlit Cloud preenchidos (não commitar local).