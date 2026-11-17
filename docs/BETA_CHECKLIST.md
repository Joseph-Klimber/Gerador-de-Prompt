# Checklist de Prontidão para Beta (Prompt Studio)

## ✅ Código & Arquitetura

### Autenticação & Segurança
- [x] **Bypass removido** - Login só via Google Sheets (`src/ui/sidebar.py`)
- [x] **HMAC-SHA256 assinatura** - Requests e responses assinados (`src/config_store.py`, `apps_script/Code.gs`)
- [x] **Verificação HMAC no cliente** - Rejeita configs adulteradas
- [x] **Chave mestra única** - `PS_FERNET_KEY` = `HMAC_KEY` (Fernet + HMAC)
- [x] **Zero segredos no repo** - `.gitignore` protege `.streamlit/secrets.toml`
- [x] **Criptografia client-side** - Chaves BYOK criptografadas antes de ir pra nuvem

### Rate Limiting & Observabilidade (Apps Script)
- [x] **Dual rate limit** - 20 req/min por e-mail + 60 req/min por IP
- [x] **Lock de concorrência** - `LockService` previne race conditions
- [x] **Logging estruturado** - JSON com `ts, email, action, ok, latencyMs, error`
- [x] **Cloud Logging ready** - `console.info(JSON.stringify(...))`

### Resiliência Client-Side
- [x] **Timeout 15s** - Todas as chamadas HTTP têm timeout
- [x] **Retry com backoff** - 2 retries (1s, 2s) em falhas transitórias
- [x] **Erros com timestamp** - Formato `[HH:MM:SS]` em todas mensagens usuário
- [x] **Fallback gracioso** - Local save funciona sem nuvem

---

## ✅ Qualidade & Testes

### Suite de Testes (12/12 passing)
- [x] Imports e estrutura
- [x] Resolução de destino (7 perfis)
- [x] Prompt Builder (rascunho + auditoria)
- [x] Orçamento de tokens (3 destinos)
- [x] Detecção erros transitórios (text + vision)
- [x] Gerenciamento estado (session_state)
- [x] Motor Visão - estrutura + integração UI
- [x] Motor Texto - estrutura + integração UI
- [x] Correções UI aplicadas (race condition, indentação)
- [x] Segurança - criptografia payload nuvem
- [x] Segurança - zero segredos expostos

### Lint & Compilação
- [x] `py_compile` limpo em todos módulos
- [x] Sem erros de sintaxe
- [x] Type hints consistentes

---

## ✅ Documentação & Deploy

### Guias de Configuração
- [x] `.streamlit/secrets.toml.example` - Template completo
- [x] `docs/SECRETS_SETUP.md` - Guia passo a passo (chave, Apps Script, Sheets, Cloud)
- [x] `apps_script/Code.gs` - Backend produção com HMAC, rate limit, logging
- [x] `apps_script/deploy.md` - Instruções deploy Web App
- [x] `docs/E2E_TEST_PROCEDURE.md` - Procedimento teste 3 casos

### Configuração Produção
- [ ] **Planilha Google Sheets criada** - Aba `Assinaturas` (Email | Expiracao | Config)
- [ ] **Apps Script deployado** - Execute as Me, Anyone access, URL no secrets
- [ ] **PS_FERNET_KEY gerada** - `openssl rand -base64 32` (igual no Apps Script HMAC_KEY)
- [ ] **Streamlit Cloud secrets** - Todos os 7 segredos configurados
- [ ] **Links Kiwify reais** - 4 planos na página de login

---

## ✅ Validação E2E (Manual)

### Casos de Teste (3 imagens)
- [ ] **Caso 1 - Anime**: elfa/character → Z-Image/Flux → Score ≥ 80%
- [ ] **Caso 2 - Foto**: retrato/paisagem → ComfyUI SDXL → Score ≥ 80%
- [ ] **Caso 3 - Arte**: ilustração/pintura → Illustrious/Pony → Score ≥ 80%

### Critérios de Aceite
- [ ] Tempo total imagem→prompt < 30s
- [ ] ComfyUI queue→done < 60s
- [ ] Zero erros permanentes (timeouts recuperados com retry)
- [ ] Logs mostram timestamps `[HH:MM:SS]`
- [ ] Rate limit dispara corretamente (teste burst > 20 req/min)

---

## ✅ Smoke Test Pós-Deploy (Streamlit Cloud)

### Login & Auth
- [ ] Login com e-mail válido (planilha) → sucesso
- [ ] Login com e-mail inválido → erro `[HH:MM:SS] E-mail não autorizado`
- [ ] Login com e-mail expirado → erro `[HH:MM:SS] Não autorizado`
- [ ] Logout limpa sessão corretamente

### Funcionalidade Core
- [ ] Upload imagem → Passo 1 extrai visão OK
- [ ] Modificações globais (Passo 2) → aplicadas no prompt
- [ ] Ideia (Passo 3) → narrativa salva
- [ ] Rascunhar (Passo 4) → prompt gerado com estrutura correta
- [ ] Destino (Passo 5) → seleção muda estrutura do prompt
- [ ] Auditoria (Passo 6) → score calculado, ≥ 80% para casos válidos

### Integração ComfyUI
- [ ] Prompt copiado → colado no ComfyUI → gera imagem
- [ ] Imagem gerada corresponde à ideia original

### Rate Limit & Segurança
- [ ] 21 requisições rápidas mesmo e-mail → 429 "Muitas tentativas"
- [ ] HMAC válido → request aceito
- [ ] HMAC inválido → 401 "Assinatura inválida"
- [ ] Config adulterada na nuvem → rejeitada no load

---

## 🚀 Go/No-Go para Beta

| Critério | Status | Notas |
|----------|--------|-------|
| Todos testes unitários passam | ✅ | 12/12 |
| py_compile limpo | ✅ | |
| Bypass removido | ✅ | |
| HMAC implementado | ✅ | |
| Rate limiting ativo | ✅ | |
| Logging estruturado | ✅ | |
| Erros com timestamp | ✅ | |
| Retry/backoff | ✅ | |
| Documentação deploy completa | ✅ | |
| E2E 3 casos validados | ⏳ | Pendente execução manual |
| Secrets produção configurados | ⏳ | Pendente (requer chaves reais) |
| Smoke test Cloud OK | ⏳ | Pendente deploy |

### Decisão
- [ ] **GO** - Todos critérios ✅, beta autorizado
- [ ] **NO-GO** - Itens pendentes listados acima

---

## Pós-Beta (Próximos Passos)

1. **Monitorar métricas** - Latência, taxa erro, uso rate limit
2. **Coletar feedback** - Qualidade prompts, UX, bugs
3. **Iterar** - Ajustar modelos, prompts, limites
4. **Escalar** - Adicionar mais destinos, idiomas, features