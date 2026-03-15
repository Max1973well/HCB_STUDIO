# Caderno Guia - HCB Studio

## Origem
Baseado no "guardanapo do cientista" e na diretriz: pensar primeiro, construir depois.

## North Star
Construir um sistema operacional cognitivo modular para trabalho real, com baixa perda de contexto, execução por blocos e governança forte.

## Perfil de usuário foco (fase atual)
Criador de conteúdo (YouTube e similares), que precisa produzir com ordem:
1. Roteiro/texto
2. Prompts para imagem
3. Prompts para som
4. Prompts para fala
5. Montagem final (CapCut ou outra ferramenta)

## Regra operacional central
Uma IA por vez, por bloco de trabalho, com troca explícita de sessão e checkpoint de transição.

## Novo braço oficial
## Arm 09 - Universal Prompt Writer
Função:
1. Transformar ideia bruta em prompt pronto para copiar e colar na IA/ferramenta alvo.
2. Adaptar idioma (pt/en) conforme desempenho da IA de destino.
3. Gerar variações controladas (curta, padrão, detalhada).

Entradas:
1. Objetivo do bloco (ex: imagem de capa, locução, trilha)
2. Plataforma alvo (ex: Midjourney, Runway, ElevenLabs, Gemini, etc.)
3. Idioma preferencial da plataforma
4. Restrições (tempo, estilo, tom, formato)

Saídas:
1. Prompt final
2. Prompt alternativo
3. Checklist de validação (o que conferir antes de executar)
4. Metadados de bloco (papel, ferramenta, idioma, timestamp)

## Braço complementar de organização
## Arm 10 - Production Block Organizer
Função:
1. Organizar blocos de produção por tipo: `texto`, `imagem`, `audio`, `fala`, `edicao`.
2. Preservar ordem de execução e dependências.
3. Preparar export para montagem (CapCut/outra IA).

Estrutura mínima de bloco:
1. `block_id`
2. `tipo`
3. `objetivo`
4. `ferramenta_alvo`
5. `prompt_final`
6. `assets_gerados`
7. `status` (`draft`, `executando`, `validado`, `concluido`)

## Fluxo recomendado (criador)
1. Definir ideia mestre
2. Quebrar em blocos
3. Gerar prompts por bloco (Arm 09)
4. Executar IA específica por bloco
5. Validar e registrar outputs
6. Montar produto final
7. Gerar checkpoint de transição

## Governança
1. Não transformar toda conversa em cápsula.
2. Cápsula apenas em troca de chat/sessão/papel ou limite de contexto.
3. Registrar conceitos evolutivos no `concept_registry`.
4. Registrar eventos no `event_bus`.

## Perguntas abertas (para próxima sessão)
1. Quais ferramentas-alvo entram no MVP do Prompt Writer?
2. Quais formatos de export o Organizer deve gerar primeiro?
3. Como medir qualidade de prompts por tipo de bloco?
