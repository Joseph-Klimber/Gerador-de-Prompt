# Prompt Studio Cockpit — Template para Deploy Grátis (Streamlit Community Cloud)

> **Gerador de prompts de engenharia preditiva para IA de imagem** — ComfyUI, Midjourney, Flux, SDXL, Ideogram, Krea, Qwen, Ernie, Z-Image Turbo.

## 🎯 Para Usuários Finais (Deploy em 3 min)

**[📋 INSTRUÇÕES DE DEPLOY → DEPLOY_INSTRUCTIONS.md](DEPLOY_INSTRUCTIONS.md)**

1. **Fork** este repositório
2. **Deploy** no [Streamlit Cloud](https://share.streamlit.io/) (grátis)
3. **Configure Secrets** (PS_FERNET_KEY + APPS_SCRIPT_URL)
4. **Use** — login com e-mail da compra Kiwify + sua chave Gemini

---

## 🏗️ Arquitetura (Para Desenvolvedores)

```
gerador-prompt/
├── app.py                    # Entry point (modular)
├── requirements.txt          # Dependências mínimas
├── .streamlit/
│   ├── config.toml          # Config Streamlit (sem segredos!)
│   └── secrets.toml         # LOCAL ONLY — NÃO COMITAR (gitignore)
├── src/
│   ├── config_store.py      # Configs criptografadas (Cloud-aware)
│   ├── crypto.py            # Fernet (AES-128-GCM) para chaves BYOK
│   ├── auth.py              # Validação via Google Sheets (Apps Script)
│   ├── text_engines.py      # 10 motores de imagem + system prompts
│   ├── vision.py            # Extração de imagem (Gemini Vision)
│   └── core/                # Lógica de negócio modular
│       ├── settings.py      # Constantes, perfis, aliases
│       ├── token_budget.py  # Orçamento real de tokens + corte semiótico
│       ├── destination.py   # Resolução de perfil via alias
│       ├── state.py         # Session state padronizado
│       ├── prompt_builder.py# Montagem de prompts (Mestre, Rascunho, Auditoria)
│   └── ui/
│       ├── sidebar.py       # Auth + Centro de Conexão
│       └── steps.py         # Passos 0-5 + Output final
├── assets/
│   └── styles.css           # Design tokens (CSS customizado)
├── DEPLOY_INSTRUCTIONS.md   # Guia do usuário final
├── APPS_SCRIPT_CODE.gs      # Backend de licença (Google Apps Script)
└── .gitignore               # Protege secrets, configs locais
```

---

## 🔐 Modelo de Segurança (BYOK + Isolamento Real)

| Camada | Implementação |
|--------|--------------|
| **Chaves do usuário (Gemini)** | `st.secrets` no **próprio deploy do usuário** — ninguém mais acessa |
| **Criptografia at-rest** | Fernet (AES-128-GCM) com `PS_FERNET_KEY` **do usuário** |
| **Licença/Validação** | Apps Script + Google Sheets (seu controle centralizado) |
| **Isolamento** | **Container por usuário** no Streamlit Cloud — zero shared memory |
| **Imagens** | Upload → base64 → **direto para Gemini API** — não tocam disco |
| **Logs/Erros** | Sanitizados — nunca vazam chaves |

---

## 🛠️ Desenvolvimento Local

```bash
# 1. Clone seu fork
git clone https://github.com/seu-usuario/gerador-prompt.git
cd gerador-prompt

# 2. Venv + deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Secrets local (.streamlit/secrets.toml)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edite com SUAS chaves locais

# 4. Rode
streamlit run app.py
```

---

## 📦 Publicar Atualização (Para Você, Dev)

```bash
# 1. Commit + push na main
git add -A
git commit -m "feat: nova feature X"
git push origin main

# 2. Usuários finais:
#    - GitHub: "Sync fork" → "Update branch"
#    - Streamlit Cloud: "Reboot app"
#    Pronto — todos na versão nova
```

---

## 🧪 Testes Rápidos

```bash
# Lint
pip install ruff
ruff check src/

# Type check
pip install pyright
pyright src/

# Smoke test local
streamlit run app.py --server.headless true &
sleep 10
curl -f http://localhost:8501/_stcore/health
```

---

## 📋 Checklist de Release

- [ ] `requirements.txt` atualizado
- [ ] `DEPLOY_INSTRUCTIONS.md` reflete mudanças
- [ ] `APPS_SCRIPT_CODE.gs` compatível (se mudou API)
- [ ] `.gitignore` protege novos segredos
- [ ] Testado local + deploy teste no Streamlit Cloud

---

## 🆘 Suporte / Issues

- **Bug no app:** Logs no Streamlit Cloud (aba Logs) → Issue aqui
- **Licença/Acesso:** Verifique planilha Google Sheets (email + expiração)
- **Chave Gemini:** aistudio.google.com/app/apikey (cota free: 20 req/dia/modelo)

---

## 📄 Licença

Código proprietário — uso autorizado mediante licença válida (Kiwify → planilha).
Template para deploy pessoal **não** concede direitos de redistribuição do código-fonte.