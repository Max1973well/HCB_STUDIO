# Caderno Técnico - Acoplamento Arm 09 -> Arm 10 v2

## Objetivo
Definir o acoplamento correto entre `Arm 09` e `Arm 10` para o HCB Studio sem reduzir o sistema ao caso de vídeo.

Este caderno assume:
1. cada gaveta = um projeto
2. o projeto pode ser mídia, ensino, ciência, empresa, casa ou assistivo
3. o sistema precisa permitir revisão retroativa sem perder coerência
4. o `Arm 09` não entrega só texto; entrega unidade operacional
5. o `Arm 10` não organiza só arquivos; organiza processo temporal editável

## Princípio central
`Timelapse` no HCB Studio não significa apenas tempo audiovisual.

Aqui, `timelapse` significa:
1. ordem de construção
2. ordem de execução
3. ordem de dependência
4. ordem de revisão
5. possibilidade de voltar ao início e reencaixar algo novo sem quebrar o resto

## Universalidade do modelo
O mesmo modelo deve servir para:
1. criador de conteúdo
2. professor
3. pesquisador/físico/químico/CERN
4. empresa
5. rotina doméstica
6. perfil assistivo com limitação cognitiva ou física

O que muda entre domínios:
1. o tipo da unidade
2. os artefatos esperados
3. as regras de dependência
4. a forma de revisão

O que não muda:
1. projeto
2. fluxo
3. unidade de trabalho
4. artefatos filhos
5. dependências
6. revisões

## Camadas do Arm 10
O `Arm 10` v2 deve operar em camadas.

### 1. Projeto
Corresponde à gaveta.

Função:
1. isolar escopo
2. impedir mistura entre trabalhos
3. concentrar timeline, blocos, ativos e revisões

Campos mínimos:
1. `project_id`
2. `project_drawer`
3. `project_domain`
4. `nome`
5. `objetivo`

### 2. Fluxo
Representa o tipo de processo do projeto.

Exemplos:
1. `media_production`
2. `teaching_flow`
3. `research_flow`
4. `business_flow`
5. `home_flow`
6. `assistive_flow`

Função:
1. dizer ao `Arm 10` qual lógica de organização usar
2. evitar heurística excessiva

### 3. Sequência
Bloco macro do projeto.

Exemplos:
1. abertura
2. capítulo 1
3. experimento 2
4. revisão fiscal
5. lista de compras da semana
6. rotina da manhã

Função:
1. segmentar o projeto em partes maiores
2. permitir inserção e revisão localizada

Campos mínimos:
1. `sequence_id`
2. `sequence_label`
3. `sequence_index`

### 4. Unidade de trabalho
Esta é a peça central do acoplamento entre `Arm 09` e `Arm 10`.

Ela não deve ser pensada como "frame" ou "clipe", mas como unidade universal de ação.

Exemplos:
1. narrar conceito
2. gerar gráfico
3. preparar experimento
4. montar lista de compras
5. revisar atividade do aluno
6. emitir lembrete assistivo

Campos mínimos:
1. `unit_id`
2. `unit_type`
3. `unit_goal`
4. `phase`
5. `sequence_id`
6. `sequence_index`

### 5. Artefatos filhos
Cada unidade pode gerar um ou mais artefatos.

Exemplos:
1. voz
2. imagem
3. vídeo
4. trilha
5. texto
6. gráfico
7. checklist
8. instrução
9. evidência

Campos mínimos:
1. `artifact_id`
2. `artifact_type`
3. `target_tool`
4. `expected_output`
5. `status`

### 6. Revisão
Sem revisão formal, o sistema não suporta retorno ao início.

Função:
1. permitir corrigir algo já existente
2. preservar rastreabilidade
3. recalcular impacto local sem destruir o fluxo inteiro

Campos mínimos:
1. `revision_of`
2. `revision_reason`
3. `insertion_mode`
4. `supersedes`

## Papel do Arm 09 v2
O `Arm 09` continua sendo o compilador de intenção.

Mas agora ele precisa entregar uma unidade operacional completa, não só um prompt bonito.

O `Arm 09` v2 deve produzir:
1. prompt
2. contexto operacional
3. vinculação ao projeto
4. vinculação à sequência
5. tipo de unidade
6. artefato esperado
7. regras de dependência declaradas quando souber

## Papel do Arm 10 v2
O `Arm 10` recebe a unidade produzida pelo `Arm 09` e faz:
1. posicionamento no projeto
2. organização por fluxo
3. associação de artefatos filhos
4. revisão e reencaixe
5. visibilidade do processo
6. export futuro

Ele não deve inferir tudo por heurística textual.

## Contrato mínimo do handoff v2
O artefato do `Arm 09` deve trazer pelo menos:
1. `project_drawer`
2. `project_domain`
3. `workflow_type`
4. `user_id`
5. `mode`
6. `sequence_id`
7. `sequence_label`
8. `sequence_index`
9. `unit_id`
10. `unit_type`
11. `unit_goal`
12. `phase`
13. `artifact_type`
14. `target_tool`
15. `prompt_oficial`
16. `prompt_curto`
17. `expected_output`
18. `expected_asset_match`
19. `dependency_targets`
20. `insertion_mode`
21. `revision_of`
22. `status`

## unit_type universal
Lista inicial de tipos universais:
1. `instruction_block`
2. `planning_block`
3. `teaching_block`
4. `evidence_block`
5. `media_block`
6. `support_block`
7. `review_block`
8. `assistive_block`

## artifact_type universal
Lista inicial:
1. `text`
2. `speech`
3. `image`
4. `video`
5. `audio`
6. `graphic`
7. `checklist`
8. `table`
9. `note`
10. `task`

## phase
Toda unidade precisa de fase explícita.

Lista inicial:
1. `capture`
2. `plan`
3. `generate`
4. `validate`
5. `organize`
6. `review`
7. `finalize`

## insertion_mode
Permite alterar o começo ou o meio do processo sem destruir o restante.

Valores iniciais:
1. `append`
2. `insert_before`
3. `insert_after`
4. `replace`
5. `fork_revision`

## dependency_targets
No v2, dependência precisa poder ser explícita.

Formato inicial:
1. lista de `unit_id`
2. opcionalmente lista de `artifact_id`

Regra:
1. heurística continua existindo como apoio
2. mas dependência explícita vence heurística

## expected_asset_match
O vínculo de ativo não deve depender apenas de substring solta.

Estratégia inicial:
1. `expected_asset_match.id`
2. `expected_asset_match.filename_prefix`
3. `expected_asset_match.artifact_type`

Estratégia futura:
1. sidecar metadata
2. manifest do artefato
3. hash

## Track versus Workflow Lane
`track` continua útil, mas só para contextos de mídia.

Acima dele deve existir `workflow_lane`, universal.

Exemplos:
1. `instruction`
2. `evidence`
3. `visual`
4. `audio`
5. `review`
6. `support`

Regra:
1. todo bloco tem `workflow_lane`
2. só alguns blocos também têm `track`

## Precisão atômica
Para o nível de precisão que queremos, o sistema precisa garantir:
1. projeto certo
2. sequência certa
3. unidade certa
4. artefato certo
5. dependência certa
6. revisão certa

Sem isso, o `Arm 10` vira um organizador aproximado.

## O que não fazer
1. não tratar tudo como vídeo
2. não inferir sequência por texto solto apenas
3. não usar substring frouxa como regra primária de vínculo
4. não misturar revisão com substituição silenciosa
5. não deixar o `Arm 10` adivinhar contexto que o `Arm 09` deveria declarar

## MVP v2 realista
O v2 não precisa resolver tudo de uma vez.

Primeiro passo correto:
1. adicionar `workflow_type`
2. adicionar `sequence_id`
3. adicionar `unit_id`
4. adicionar `unit_type`
5. adicionar `expected_asset_match`
6. adicionar `dependency_targets`
7. adicionar `insertion_mode`
8. adicionar `revision_of`

## Estado atual do projeto
O que já existe e continua aproveitável:
1. gaveta por projeto
2. status operacional
3. timeline básica
4. ingestão de blocos
5. vínculo com ativo gerado

O que precisa subir de nível:
1. handoff explícito
2. contexto universal
3. revisão retroativa
4. vínculo de ativo preciso
5. separação entre `workflow_lane` e `track`

## Próximos passos
1. validar este caderno
2. atualizar `prompt_block.schema.json`
3. atualizar `timeline.schema.json`
4. só depois adaptar `Arm 09` e `Arm 10`
