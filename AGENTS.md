# AGENTS.md — Governança Arquitetural do Projeto

Este arquivo é lido automaticamente pelo Hermes Agent em todas as sessões deste repositório. Siga estas regras estritamente antes de criar ou modificar qualquer arquivo.

## 1. Regras de Ouro do Repositório
- **Zero Retrabalho / Zero Placeholders:** Nunca omita linhas de código com `# ...` ou `// TODO`. Sempre grave arquivos completos ou faça edições cirúrgicas verificadas.
- **Trava contra Regressão:** Módulos marcados como `[ESTÁVEL]` na seção de Arquitetura abaixo **NÃO PODEM** ter suas assinaturas ou lógicas alteradas sem autorização explícita do usuário.
- **Verificação Obrigatória no Terminal:** Após qualquer edição, execute validação sintática (`python -m py_compile` para Python ou checagem de build para JS/TS) antes de concluir a resposta.

## 2. Padrão de Arquitetura Modular
Mantenha a separação estrita de responsabilidades:
- `config.py`: Constantes, variáveis de ambiente, chaves e configurações globais (Single Source of Truth).
- `schemas.py`: Contratos de dados (`dataclasses` frozen, enums) — tipos imutáveis.
- `core/`: Motores de processamento, regras de negócio, lógica pura (zero dependência de Streamlit).
  - `token_budget.py` [ESTÁVEL] — medição/corte semiótico de tokens
  - `destination.py` [ESTÁVEL] — resolução de perfil via alias
  - `prompt_builder.py` — montagem de prompts (Mestre, Rascunho, Auditoria)
  - `state.py` [ESTÁVEL] — session_state wrapper tipado
- `src/` — Módulos de infraestrutura e integrações externas:
  - `crypto.py` [ESTÁVEL] — Fernet encryption
  - `config_store.py` — config local + nuvem (Apps Script)
  - `auth.py` — autenticação via Google Sheets
  - `text_engines.py` — BANCO_DE_MOTORES, SYS_*, helpers de chamada
  - `vision.py` — motor de visão (Gemini Vision)
- `ui/` — Camada exclusiva de apresentação visual:
  - `sidebar.py` — auth + centro de conexão
  - `steps.py` — Passos 0-5 + output final
- `app.py` — Entry point, wiring, orquestração do pipeline

## 3. Diretriz Estética (Anti-AI-Slop)
- **Arquétipo Visual Ativo:** Precision Industrial Dark (`#0b0f14` surface, `#111820` panel, `#1e293b` 1px borders, `#e2e8f0` text, `#22d3ee` accent).
- **Tipografia:** `Plus Jakarta Sans` (UI/Corpo) + `JetBrains Mono` (Dados técnicos, parâmetros, badges).
- **Proibições Visuais:** Proibido usar gradientes roxos/azuis genéricos, sombras pesadas borradas ou layouts clichês de 3 colunas simétricas.

## 4. Mapa de Módulos e Status (Atualizado pelo Agente)
- [x] `config.py`: **ESTÁVEL** — Single Source of Truth
- [x] `schemas.py`: **ESTÁVEL** — Data contracts
- [x] `core/token_budget.py`: **ESTÁVEL** — Token budget engine
- [x] `core/destination.py`: **ESTÁVEL** — Destination resolver
- [x] `core/prompt_builder.py`: Ativo
- [x] `core/state.py`: **ESTÁVEL** — State management
- [x] `src/crypto.py`: **ESTÁVEL** — Encryption
- [x] `src/config_store.py`: Ativo
- [x] `src/auth.py`: Ativo
- [x] `src/text_engines.py`: Ativo
- [x] `src/vision.py`: Ativo
- [x] `ui/sidebar.py`: Ativo
- [x] `ui/steps.py`: Ativo
- [x] `app.py`: Ativo