# 🚀 Deploy Grátis em 3 Minutos (Streamlit Community Cloud)

> **Pré-requisitos:** Conta GitHub (grátis) + Chave Gemini API (grátis em [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)) + E-mail da compra no Kiwify (já liberado na planilha).

---

## 1. Fork Este Repositório
Clique no botão **Fork** no topo desta página → seu GitHub.

## 2. Deploy no Streamlit Cloud
1. Acesse **https://share.streamlit.io/**
2. Login com GitHub → **New app**
3. Preencha:
   - **Repository:** `seu-usuario/gerador-prompt` (seu fork)
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Clique em **Advanced settings** → **Secrets** → Cole isto:
   ```toml
   PS_FERNET_KEY = "SUA_CHAVE_FERNET_AQUI"
   APPS_SCRIPT_URL = "SUA_APPS_SCRIPT_URL_AQUI"
   ```
   > **Como gerar `PS_FERNET_KEY`:** Rode no terminal/local:
   > ```bash
   > python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   > ```
   > Copie a string gerada (44 chars) e cole acima.
5. **Deploy!** ⏳ 2-3 minutos → Sua URL: `https://seu-usuario-gerador-prompt.streamlit.app`

## 3. Use o App
1. Abra sua URL pessoal
2. **Login** com o e-mail da compra no Kiwify
3. Sidebar → **Centro de Conexão** → Cole sua **Chave Gemini** (pegue em aistudio.google.com/app/apikey)
4. Pronto! Gere prompts à vontade.

## 4. Atualizações Futuras
Quando houver nova versão no repositório original:
1. No seu fork GitHub: botão **Sync fork** → **Update branch**
2. No Streamlit Cloud: abra seu app → **Reboot app** (canto superior direito)
3. Pronto — nova versão rodando.

---

## ⚠️ Importante: Limitações do Tier Grátis
| Limitação | O que acontece | Como contornar |
|-----------|----------------|----------------|
| App hiberna após **7 dias sem acesso** | Próximo acesso = reinício do zero | Reinsira a chave Gemini na sidebar (30 seg) |
| Sem persistência de disco | Configs não salvam entre reboots | Apps Script (nuvem) salva suas chaves — reconecta automático no login |
| Logs só no painel do Streamlit Cloud | Você não vê erros dos usuários | Usuário copia erro do log e te manda se precisar |

> **Dica:** Se quiser persistência total sem reinserir chaves, o usuário pode assinar **Streamlit Cloud Pro ($21/mês)** — mas o tier grátis já funciona 100%.

---

## 🔐 Segurança (Por Que É Seguro)
- **Sua chave Gemini** fica no **SEU** `secrets.toml` no Streamlit Cloud — **ninguém mais vê** (nem o desenvolvedor)
- **Sua `PS_FERNET_KEY`** também é **sua** — criptografa só seus dados
- **Apps Script URL** é a mesma para todos (validação de licença), mas **não vaza emails nem chaves**
- Cada usuário roda em **container isolado** — zero acesso a dados de outros usuários
- Imagens vão **direto para API do Google** — não tocam servidor algum

---

## 🆘 Problemas Comuns

| Problema | Solução |
|----------|---------|
| **"PS_FERNET_KEY não configurado"** | Verifique se colou certo no Secrets (sem aspas extras, sem espaços) |
| **"APPS_SCRIPT_URL não configurado"** | Cole a URL do seu Apps Script no Secrets |
| **"Chave inválida / 401 / 403"** | Gere nova chave em aistudio.google.com/app/apikey |
| **"Limite de uso atingido (429)"** | Cota gratuita do Gemini acabou — aguarde 24h ou use outra conta Google |
| **App não carrega / tela branca** | No Streamlit Cloud: **Reboot app** → veja logs na aba "Logs" |
| **Erro ao salvar config** | Verifique se `APPS_SCRIPT_URL` responde (teste no navegador) |

---

## 📞 Suporte
- Erro no app? Copie o log do Streamlit Cloud (aba **Logs**) e envie pro desenvolvedor.
- Dúvida de licença/acesso? Verifique se seu e-mail está na planilha com expiração válida.