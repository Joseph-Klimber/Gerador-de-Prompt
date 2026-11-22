# E2E_TEST_PROCEDURE.md

Procedimento de teste ponta-a-ponta para validar o Prompt Studio antes de liberar beta.

---

## 0. Pré-requisitos

- Python 3.11+ + `streamlit` + dependências (`google-genai`, `cryptography`, `pillow`).
- `.streamlit/secrets.toml` configurado (ver `SECRETS_SETUP.md`).
- Conta Google com acesso ao Apps Script + Planilha.
- Chave Gemini (aistudio.google.com/app/apikey) com cota disponível.
- Imagem de teste (JPG/PNG/WebP, ≤ 10 MB).

---

## 1. Smoke Test (CLI)

```bash
# Compilação de todos os módulos
cd Gerador-de-Prompt
python -m py_compile app.py src/*.py src/ui/*.py

# Inicialização rápida do estado (sem GUI)
python -c "
import streamlit as st
from core.state import init_state
init_state()
print('STATE OK:', list(st.session_state.keys())[:10])
"
```

✅ Esperado: zero erros de sintaxe, estado inicializado.

---

## 2. Login + Autenticação (GUI)

1. `streamlit run app.py` → abre no navegador.
2. Tela de login aparece (hero + showcase + planos).
3. Insira e-mail **cadastrado na planilha** com expiração futura.
4. Clique **🚀 Entrar**.
5. ✅ Sucesso: sidebar mostra "Logado: u***@dominio.com" + Centro de Conexão.
6. ❌ Falha: e-mail não encontrado / expirado / APPS_SCRIPT_URL errado.

**Teste negativo**: e-mail inexistente → erro "E-mail não encontrado".

---

## 3. Centro de Conexão (Sidebar)

1. No sidebar logado, preencha:
   - **Chave Visão (BYOK)**: sua chave Gemini válida.
   - **Modelo Visão**: `gemini-3.5-flash` (padrão).
   - **Chave Texto (BYOK)**: mesma ou outra chave Gemini.
   - **Modelo Texto**: `gemini-3.5-flash` (padrão).
2. Clique **🔌 Conectar Motores Isolados**.
3. ✅ Sucesso: toast "Motores conectados com sucesso!".
4. Verifique: chaves salvas localmente (`config/config_<hash>.json`) + nuvem (Apps Script → planilha coluna C preenchida).

**Teste negativo**: chave inválida / modelo não suportado → erro apropriado.

---

## 4. Passo 0 — Motor Destino

1. No cockpit principal, **Passo 0** (coluna esquerda):
   - Selecione `ComfyUI / Pony SDXL`.
2. ✅ Aparece caption: formato TAGS, teto 2048 tokens.
3. Teste troca: mude para `Midjourney v6.1+` → caption atualiza (PROSA, teto 4096).
4. ✅ Troca limpa síntese anterior (toast informativo).

---

## 5. Passo 2 — Referência Óptica (Visão)

1. **Passo 2** (largura total): faça upload de imagem de teste.
2. Miniatura aparece (≤ 512×512) + caption de normalização (proporção, tiles, tokens).
3. Selecione:
   - Estilo: `Converter para Fotorrealismo — Fotográfico Realista (Anti-Porcelana)`
   - Sensualidade: `Sugestivo (Roupas Íntimas / Implícito)`
4. Clique **👁️ Extrair Imagem (Motor de Visão)**.
5. ✅ Spinner → "Analisando matriz óptica..." → expande **Detalhador Pericial** com 5 campos preenchidos (Sujeito, Ação, Cenário, Iluminação, Estilo).
6. Caixa do Passo 1 (Ideia) preenchida automaticamente com narrativa extraída.
7. ✅ Botão **🔄 Atualizar Caixa da Ideia** funciona (edições nos 5 campos propagam).

**Validação de fidelidade**: verifique se detalhes visuais (cores, materiais, pose) estão no JSON — sem resumo.

---

## 6. Passo 1 — Ideia (Texto Livre)

1. Digite narrativa manual ou use a extraída do Passo 2.
2. ✅ Campo `st.text_area` committa no **blur** (clique fora) — callback `on_change` dispara.
3. Botão **🗑️ Limpar Ideia** zera tudo + limpa cascade (rascunho, diagnóstico, síntese).

---

## 7. Passo 3 — Modificadores Globais

1. Coluna direita (lado a lado com Passo 0):
   - Estilo, Foco, Sensualidade — todos habilitados após Passo 0.
2. Mudança de qualquer select **não** dispara rerun completo (apenas estado).

---

## 8. Passo 4 — Rascunho & Auditoria

### 8.1 Rascunho (👁️ Rascunhar Cena)

1. Clique **👁️ Rascunhar Cena**.
2. ✅ Backup da ideia → spinner "Desenhando a cena..." → Preprompt aparece com **diff visual**:
   - `<span class="ps-user-word">` = palavras da ideia original.
   - `<span class="ps-ai-word">` = adições da IA.
3. Caixa de edição "Ajuste fino do Rascunho" editável.

### 8.2 Auditoria (🔍 Auditar no Compositômetro)

1. Clique **🔍 Auditar no Compositômetro**.
2. ✅ 5 badges coloridos (Sujeito, Ação, Cenário, Luz, Câmera):
   - Verde (✓) = Definido/Presente.
   - Âmbar (!) = Vago/Estática.
   - Azul (⚙️) = Inferido.
3. Diagnóstico textual + **Sugestões Cirúrgicas** (checkboxes).
4. Marcar sugestões → ficam salvas em `StateKeys.SUGESTOES_MARCADAS`.

---

## 9. Passo 5 — Síntese Final

1. Clique **⚡ Gerar Código do Prompt** (botão primary).
2. ✅ Spinner "Compilando sintaxe ultra-otimizada..." → Prompt final renderizado em caixa `ps-final-box` (quebra automática, sem scroll horizontal).
3. Botão **⬇️ Baixar Prompt (.txt)** → download funciona.
4. Expansor "Copiar manualmente" → `st.code` selecionável.

**Validação de fidelidade**:
- Prompt em inglês (exceto tags ComfyUI).
- 100% dos detalhes da narrativa preservados (etnia, roupa exata, pose, cenário, lente, luz).
- Negativo dinâmico (antônimos, não negações).
- Franquias/personagens mantidas literalmente (ex: "Street Fighter Chun-Li").
- Hashtags 5-8 no final.

---

## 10. Testes de Resiliência (Erros & Fallbacks)

| Cenário | Ação | Esperado |
|---------|------|----------|
| Chave expirada | Use chave Gemini sem cota | Erro amigável "Limite de uso atingido (429/Quota)" + diagnóstico técnico |
| Modelo 404 | Selecione modelo inexistente via Ferramentas Avançadas | Erro "Modelo não encontrado (404) — tente outro dos 3" |
| Rede instável | Desconecte internet durante chamada | Retry exponencial (3x) → fallback 3.5→3.6→3.7-flash → erro amigável timeout |
| Imagem grande | Upload > 10 MB | Streamlit bloqueia (limite nativo) |
| Race condition | Navegue rápido entre passos | `sync_pending()` + `restore_ideia_if_empty()` evitam `StreamlitAPIException` |

---

## 11. Testes Multi-destino

Repita Passos 4-5 para **pelo menos 3 destinos** distintos:
1. `ComfyUI / Pony SDXL` (TAGS)
2. `Midjourney v6.1+` (PROSA + parâmetros)
3. `Flux.1 / Flux.2 (Klein)` (PROSA densa)
4. `Ideogram 4` (PROSA + aspas duplas para texto)

Verifique: formato correto, teto respeitado, sintaxe do motor.

---

## 12. Logout + Persistência

1. Sidebar → **🚪 Sair do Sistema**.
2. ✅ Volta para tela de login, estado limpo.
3. Login novamente → chaves carregadas do cache/nuvem (sem digitar de novo).
4. ✅ Passo 0 mantém destino anterior (salvo em `DESTINO_APLICADO`).

---

## 13. Checklist Final de Aceitação (Beta)

- [ ] Smoke test CLI passa.
- [ ] Login/Logout fluido (planilha + Apps Script).
- [ ] Centro de Conexão salva local + nuvem (HMAC verificado).
- [ ] Visão extrai 5 campos densos + preenche Ideia.
- [ ] Rascunho com diff visual (user vs IA) funciona.
- [ ] Compositômetro retorna 5 badges + sugestões.
- [ ] Prompt final: fidelidade 100%, negativo dinâmico, hashtags, formato do motor.
- [ ] 3+ destinos testados com formatos corretos.
- [ ] Erros amigáveis + diagnóstico técnico expansível.
- [ ] Cache 5 min invalida corretamente no `salvar_config`.
- [ ] Sem `StreamlitAPIException` em navegação rápida.
- [ ] Download .txt + copy manual funcionam.
- [ ] Logs estruturados no Apps Script (Cloud Logging) aparecem.

---

## 14. Critérios de "Pronto para Beta"

**Todos** os itens da seção 13 marcados ✅.
Zero erros de sintaxe / runtime não tratados.
Docs (`SECRETS_SETUP.md`, `BETA_CHECKLIST.md`) atualizados.
Commit + push na branch `main` com tag `beta-<data>`.