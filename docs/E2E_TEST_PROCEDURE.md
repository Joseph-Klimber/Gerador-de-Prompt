# Procedimento de Teste E2E com ComfyUI

## Visão Geral
Validação completa do fluxo: **Imagem → Prompt Studio → ComfyUI → Imagem Gerada**

## Pré-requisitos
- ComfyUI rodando em `http://localhost:8188`
- Workflow Qwen-Image carregado (ex: `qwen2_1_turbo_nativo_v033_fix_v3.json`)
- Prompt Studio rodando em `http://localhost:8501`
- Usuário logado com chaves BYOK configuradas (Visão + Texto)

---

## Casos de Teste (3 Imagens)

### Caso 1: Anime / Ilustração
- **Imagem**: Personagem anime (ex: elfa, girl, character)
- **Destino esperado**: `zit` (Z-Image Turbo) ou `flux`
- **Critério**: Prompt deve conter tags de qualidade anime (`score_9`, `source_anime`, `1girl`, etc.)

### Caso 2: Fotorealismo / Foto
- **Imagem**: Foto realista (pessoa, paisagem, objeto)
- **Destino esperado**: `comfyui_sdxl` ou `flux`
- **Critério**: Prompt deve conter termos fotográficos (`photorealistic`, `85mm lens`, `studio lighting`, etc.)

### Caso 3: Ilustração Artística / Pintura
- **Imagem**: Arte digital, pintura, conceito artístico
- **Destino esperado**: `illustrious` ou `pony`
- **Critério**: Prompt deve conter termos de estilo artístico (`masterpiece`, `digital art`, `concept art`, etc.)

---

## Passo a Passo

### 1. Preparar Ambiente
```bash
# Terminal 1: ComfyUI
cd F:/comfy
python main.py --port 8188

# Terminal 2: Prompt Studio
cd D:/recuperacao/hermes bkp/Gerador-de-Prompt
.venv/Scripts/activate
streamlit run app.py --server.port 8501
```

### 2. Login e Configuração
1. Abrir `http://localhost:8501`
2. Login com e-mail válido (planilha Google Sheets)
3. No **Centro de Conexão**:
   - Colar **Chave Visão (BYOK)** - Gemini API Key
   - Colar **Chave Texto (BYOK)** - Gemini API Key (pode ser a mesma)
   - Selecionar modelos: `gemini-3.6-flash` (visão) e `gemini-3.5-flash` (texto)
   - Clicar **🔌 Conectar Motores Isolados**
   - Verificar mensagem "Motores conectados com sucesso!"

### 3. Executar Teste por Caso

#### Para cada imagem de teste:
1. **Passo 1 - Imagem**: Fazer upload da imagem de teste
2. **Passo 2 - Modificações Globais** (opcional): Ajustar estilo, iluminação, etc.
3. **Passo 3 - Ideia**: Digitar narrativa visual (ex: "elfa na escadaria, luz volumétrica, armadura ornamentada")
4. **Passo 4 - Rascunhar**: Clicar **📝 Rascunhar Prompt** → aguardar geração
5. **Passo 5 - Destino**: Selecionar destino apropriado (ComfyUI, Z-Image, etc.)
6. **Passo 6 - Auditoria**: Clicar **🔍 Auditar Prompt** → verificar score ≥ 80%
7. **Enviar para ComfyUI**: Copiar prompt final → colar no ComfyUI (positive prompt)
8. **Gerar no ComfyUI**: Clicar **Queue Prompt** → aguardar conclusão (< 60s)
9. **Validar Resultado**: Verificar se imagem gerada corresponde à ideia original

---

## Critérios de Sucesso

| Critério | Threshold |
|----------|-----------|
| Tempo total (imagem → prompt final) | < 30s |
| Tempo ComfyUI (queue → done) | < 60s |
| Score auditoria | ≥ 80% |
| Qualidade visual (subjetivo) | Correspondência ≥ 80% com ideia |
| Sem erros de timeout/retry | 0 falhas permanentes |
| Logs de erro com timestamp | Todos os erros mostram `[HH:MM:SS]` |

---

## Registro de Resultados

| Caso | Imagem | Destino | Tempo Total | Score Auditoria | ComfyUI OK? | Observações |
|------|--------|---------|-------------|-----------------|-------------|-------------|
| 1 | anime | zit/flux | | | | |
| 2 | foto | comfyui_sdxl | | | | |
| 3 | arte | illustrious/pony | | | | |

---

## Troubleshooting Comum

| Problema | Causa | Solução |
|----------|-------|---------|
| "Chave Visão não configurada" | BYOK não salvo | Verificar Centro de Conexão → Conectar Motores |
| Timeout na visão (90s) | Gemini API lento | Retry automático (2 tentativas) - aguardar |
| Prompt vazio no Passo 4 | Ideia não preenchida | Preencher Passo 3 antes de Rascunhar |
| ComfyUI erro "model not found" | Workflow não carregado | Carregar workflow Qwen-Image correto |
| Imagem gerada não corresponde | Prompt inadequado | Ajustar Passo 2/3, re-rascunhar |

---

## Validação de Regressão (Pós-Deploy)

Após qualquer deploy:
1. Executar todos os 3 casos acima
2. Rodar `test_suite.py` → 12/12 OK
3. Verificar `py_compile` limpo
4. Testar login com 2 e-mails diferentes
5. Verificar rate limit (20 req/min por e-mail)