# Deploy do Apps Script (Produção)

## 1. Planilha Google Sheets (JÁ EXISTE)

**ID:** `180xWEBt4Lu8dqHQCBIwfyMgYA1vdN8eD1FehK-aiXLI`
**URL:** https://docs.google.com/spreadsheets/d/180xWEBt4Lu8dqHQCBIwfyMgYA1vdN8eD1FehK-aiXLI/edit

Verifique se a aba se chama **`Assinaturas`** com cabeçalhos:
- **A1**: `Email`
- **B1**: `Expiracao`
- **C1**: `Config`

Adicione usuários beta na aba `Assinaturas`:
| Email | Expiracao | Config |
|-------|-----------|--------|
| teste@exemplo.com | 2026-12-31 23:59:59 | {} |
| seu@email.com | 2026-12-31 23:59:59 | {} |

## 2. Criar Projeto Apps Script

1. Acesse [script.google.com](https://script.google.com)
2. `Novo projeto` → nomeie "Prompt Studio Backend"
3. Apague o `Code.gs` padrão
4. Crie arquivo `Code.gs` e cole o conteúdo de `apps_script/Code.gs`
5. **Substitua os placeholders**:
   - `YOUR_SHEET_ID` → ID da sua planilha
   - `YOUR_HMAC_KEY` → **PS_FERNET_KEY** (mesma chave do `.streamlit/secrets.toml`)

## 3. Gerar PS_FERNET_KEY (se não tiver)

```bash
# Linux/macOS/Git Bash
openssl rand -base64 32

# PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Exemplo saída: `l-xh7kSMXEc7fAvRpnjG-celm8v6URPsyJTzDGSMoO0=`

**Use a MESMA chave em:**
- `.streamlit/secrets.toml` → `PS_FERNET_KEY`
- Apps Script `Code.gs` → `HMAC_KEY`

## 4. Deploy como Web App

1. No Apps Script: `Implantar` → `Nova implantação`
2. Tipo: **Aplicativo da Web**
3. Configurações:
   - **Executar como**: Eu (`Me`)
   - **Quem tem acesso**: Qualquer pessoa (`Anyone`)
4. `Implantar` → Autorize as permissões
5. Copie a **URL do app da web** (formato: `https://script.google.com/macros/s/<DEPLOYMENT_ID>/exec`)

## 5. Configurar Secrets

### Local (`.streamlit/secrets.toml`)
```toml
PS_FERNET_KEY = "sua-chave-base64-32-bytes"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/<DEPLOYMENT_ID>/exec"
LINK_KIWIFY_15_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_30_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_90_DIAS = "https://pay.kiwify.com.br/..."
LINK_KIWIFY_VITALICIO = "https://pay.kiwify.com.br/..."
```

### Streamlit Community Cloud
1. No dashboard do app → `Settings` → `Secrets`
2. Cole o conteúdo acima (valores reais, não placeholders)

## 6. Testar

```bash
# Teste local
cd D:/recuperacao/hermes bkp/Gerador-de-Prompt
.venv/Scripts/python.exe -c "
from src.auth import verificar_acesso_sheets
ok, exp, err = verificar_acesso_sheets('seu@email.com')
print('OK:', ok, 'Exp:', exp, 'Err:', err)
"
```

Deve retornar `OK: False` se e-mail não estiver na planilha (sem erro de conexão/HMAC).

## 7. Adicionar Usuários de Teste

Na planilha `Assinaturas`, adicione linhas:
| Email | Expiracao | Config |
|-------|-----------|--------|
| teste@exemplo.com | 2026-12-31 23:59:59 | {} |

## 8. Logs e Monitoramento

- **Logs estruturados**: `console.info(JSON.stringify({...}))` → visíveis no **Cloud Logging** do GCP
- Filtro útil: `resource.type="apps_script_function" jsonPayload.action="carregar"`
- Rate limit logs: aparecem como `ok: false, error: "Muitas tentativas..."`

## 9. Atualizações Futuras

1. Edite o `Code.gs` no Apps Script
2. `Implantar` → `Gerenciar implantações` → clique no lápis → `Nova versão` → `Implantar`
3. A URL **não muda** entre versões

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `HMAC inválido` | Chaves diferentes | Verifique se `PS_FERNET_KEY` == `HMAC_KEY` exatamente |
| `Não autorizado` | E-mail não na planilha | Adicione e-mail com expiração futura |
| `Muitas tentativas` | Rate limit | Aguarde 1 min ou aumente limites no código |
| `Erro interno` | Exceção no código | Veja logs no Cloud Console → Logging |
| `Config corrompida` | JSON inválido na coluna C | Corrija o JSON na planilha |