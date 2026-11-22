# ROLLBACK.md — Como voltar atrás (V1: 1 ambiente)

> **V1 sem homologação separada.** 1 ambiente: `local` + `prod` (Streamlit Cloud via push `main`).

## Em < 5 min

### 1) Reverter código
```bash
# ver últimos commits
git log --oneline -5
# reverter o último push (ex: f6097cc)
git revert HEAD --no-edit
git push origin main
# Streamlit Cloud redeploya sozinho (1-2 min) — conferir em Manage app > Logs
```
Alternativa: `git revert <hash>` do commit com defeito e `git push` novamente.

### 2) Reimplantar Apps Script (se a falha foi em `usuarios`/`configs`)
- Apps Script > Gerenciar implantações > `v1` > Editar > selecionar versão anterior > Implantar
- Confirmar `APPS_SCRIPT_URL` em Streamlit Cloud > Settings > Secrets continua igual (não muda)

### 3) Invalidar cache
- Sidebar > Sair e entrar de novo (limpa `st.session_state["_config_cache"]`)
- Ou aguardar 600s (TTL do `_config_cache`)

### 4) Confirmar
- Login `teste@123.com` deve voltar a entrar
- `python -m py_compile app.py src/*.py` sem erro
- Erro anterior deve sumir em `RAW [code]` sem expor chave

## O que NÃO fazer
- Não precisa recriar planilha `usuarios`/`configs` — só reverter código
- Não precisa recriar `PS_FERNET_KEY` — segredo já está em `st.secrets`
