# Roteiro de Teste Manual — V1 (4 critérios PRD)

> Executar logado como `teste@123.com` em `gemini-3.5-flash` padrão (fallback `3.6→3.7` só se 503). Chave Texto e Visão conectadas na sidebar (pode ser mesma string isolada).

## Cenário A — Dado que colei ideia → Melhorar sem inventar
1. Passo 1: colar `uma elfa loira de armadura dourada na escadaria de pedra`
2. Clicar `Rascunhar Cena (Via Motor de Texto)`
3. Esperado: `ps-preprompt` com texto expandido, marcação azul (palavra original) vs dourado (IA), sem inventar personagem/franquia/gênero fora do pedido. `ps-preprompt` editável reflete no Motor Final.

## Cenário B — Dado que enviei imagem → extrair editável
1. Passo 1 deixar vazio, Passo 2 upload `elfa.jpg` (≤10MB, PNG/JPG/WEBP)
2. Clicar `Extrair Imagem (Motor de Visão)` com `gemini-3.5-flash` padrão
3. Esperado: `ck_img_parametros` preenchido + expansor `Detalhador Pericial` com 5 campos editáveis + `Sujeito/Ação/Cenário/Iluminação/Estilo` na caixa da Ideia. Editar `Sujeito` e clicar `Atualizar Caixa da Ideia` reflete no Passo 1.

## Cenário C — Dado que modifiquei estilo → sem misturar
1. Passo 1: `retrato de guerreira`
2. Passo 3: `Estilo de Arte = Converter para Fotorrealismo` (ou Anime)
3. Passo 5: selecionar `ComfyUI / Pony SDXL` e `Gerar Código do Prompt`
4. Esperado Fotorrealismo: prompt sem `anime, ilustração, cartoon, drawing`; Anime: prompt sem `photo, smartphone, 26mm, photorealistic`. Trocar seletor e gerar de novo muda todo o prompt.

## Cenário D — Dado que auditei → vê vago antes de gastar cota
1. Passo 1: `uma figura`
2. Clicar `Auditar no Compositômetro (Raio-X)`
3. Esperado: 5 badges `Sujeito/Ação/Cenário/Luz/Câmera` (verde `Definido` ou âmbar `Vago` + ícone) + `diagnostico_texto` + `sugestoes_cirurgicas` marcáveis. Aviso: Auditoria consome 1 chamada Texto para evitar desperdício na Síntese.

## Estados de erro (11) — checar mensagens PT-BR
- Ideia vazia ao Melhorar/Auditar/Gerar → `Escreva sua Ideia no Passo 1.`
- Imagem vazia ao Extrair → `Selecione uma imagem primeiro.`
- Imagem >10MB → `Imagem limite: 10 MB.` (sem chamar IA)
- Sem chave Visão/Texto → `Nenhuma chave configurada para ...`
- Sem Motor Destino → `Selecione para qual motor`
- Login inválido/não encontrado/expirado/sem internet → mensagens em `src/auth.py`
- 401/404/429/503 → `_msg_erro_amigavel` PT-BR + `RAW [code]` sem expor chave

## Checklist rápido
- [ ] A passa
- [ ] B passa
- [ ] C passa (fotorrealismo e anime)
- [ ] D passa
- [ ] 11 erros em PT-BR
- [ ] Tema claro/escuro sem camuflagem (var(--text-color))
- [ ] LGPD: nada em Sheets além de e-mail+config criptografada
