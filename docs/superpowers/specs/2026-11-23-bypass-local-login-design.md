# Bypass local do login — Design (aprovado por Sergio em 2026-11-23)

## Intenção

Entrar no app do backup local (D:) sem e-mail e sem planilha, porque esta
cópia é uso pessoal local e não recebe outras pessoas.

## Decisões aprovadas

1. **Gating — "somente local" de verdade**: flag `LOCAL_BYPASS = true` no
   `.streamlit/secrets.toml` (arquivo **não versionado**). Sem a flag, o app
   é exatamente o de hoje — clones do GitHub continuam validando na planilha.
2. **Identidade sem e-mail**: constante `LOCAL_EMAIL = "local@prompt-studio.local"`
   em `core/state.py`. O clique seta `AUTENTICADO=True`, `USER_EMAIL=LOCAL_EMAIL`,
   `EXPIRACAO="Local — sem validação"` e `st.rerun()`. Zero chamada ao Apps Script.
3. **UI**: botão "🔓 Entrar (app local)" nos dois pontos de login (página
   principal e sidebar), visível só com a flag.
4. **Chaves preservadas**: migração única do `config_327495aaff5267ba.json`
   (config atual de 21/11) para o hash do e-mail-fixo — o hash é unidirecional,
   mas basta copiar o arquivo.
5. **Planilha intocada**: no `config_store`, quando o e-mail é o fixo, pula o
   fallback e o POST do Apps Script (carregar e salvar); save local normal.
6. **Intocados**: fluxo do 🚀 Entrar com e-mail, validação, beta/outras cópias.

## Verificação obrigatória

- CLI: `py_compile` após cada patch + `test_suite.py` (exit 0, sem FALHA).
- GUI real (mouse real): sem flag → botão ausente; com flag → botão presente,
  clique → cockpit renderiza com as chaves carregadas; logout → volta à tela
  com o botão.
