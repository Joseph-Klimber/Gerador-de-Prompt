# Pendências — Gerador de prompt 1.0

## Etapa 1 — Base (em andamento)
- [ ] Preencher `.streamlit/secrets.toml` com valores reais de prod (APPS_SCRIPT_URL, PS_FERNET_KEY, LINK_KIWIFY_*)
- [ ] Confirmar `carro.jpg` / `elfa.jpg` no servidor (assets/) — hoje placeholder gradiente
- [ ] Criar repo GitHub e conectar Streamlit Cloud

## Pré-Etapa 2 (Faltando — ver 7_AUDITORIA_PRE_CODIGO)
- F01 Links Kiwify reais
- F02 APPS_SCRIPT_URL prod
- F03 PS_FERNET_KEY prod
- F04 repo/branch
- F05 planilha usuarios/configs + seed teste@123.com
- F06 Kiwify → usuarios (webhook ou manual)
- F07 SYS_* do legado 1.0-3
- F08 BANCO_DE_MOTORES (10 motores) do legado

## Validação V1 — 25/09/2026
- Fallback 3.5→3.6 verificado: gemini-3.5-flash 503 high demand (temporário Google) → 3.6-flash assumiu em A/B/C/D sem mudar código; padrão continua 3.5
