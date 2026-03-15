# Caderno Arm 10 - Production Block Organizer

## Objetivo
O `Arm 10` e o organizador de blocos de producao do HCB Studio.
Ele nao cria a ideia e nao gera o prompt.
Ele recebe blocos prontos do `Arm 09` e transforma isso em ordem de execucao, acompanhamento e montagem.

Em termos simples:
- O `Arm 09` pensa e escreve o prompt.
- O `Arm 10` organiza o trabalho real.

## Funcao central
O `Arm 10` existe para impedir que o usuario se perca entre varias IAs, varios arquivos e varias etapas de producao.

Ele deve:
1. Receber blocos de producao prontos.
2. Organizar os blocos por tipo e por etapa.
3. Manter a ordem do projeto.
4. Preparar os blocos para montagem final.
5. Dar visibilidade do que falta, do que esta pronto e do que precisa ser revisado.

## O que entra no Arm 10
Entrada principal:
- artefatos do `Arm 09` salvos como `prompt blocks`

Cada bloco deve trazer pelo menos:
1. `block_id`
2. `tipo_de_ativo`
3. `ferramenta_destino`
4. `prompt_oficial`
5. `prompt_curto`
6. `organizer_hint`
7. `timeline_stub`

## O que o Arm 10 faz com isso
O `Arm 10` pega esse bloco e coloca dentro de uma estrutura de producao.

Ele precisa decidir:
1. Em qual trilha esse bloco pertence.
2. Em que fase do projeto ele esta.
3. Se o ativo ja foi gerado ou nao.
4. Se o ativo precisa de revisao.
5. Se ele ja pode entrar na timeline final.

## Responsabilidades principais
## 1. Organizar por tipo
O `Arm 10` separa os blocos por natureza de trabalho:
- `texto`
- `imagem`
- `video`
- `audio`
- `fala`
- `edicao`

Isso permite que o usuario trabalhe em uma IA por vez sem perder o quadro geral.

## 2. Organizar por estado
Cada bloco precisa de status operacional claro:
- `draft`
- `prompt_pronto`
- `executando`
- `gerado`
- `revisao`
- `aprovado`
- `concluido`
- `descartado`

O `Arm 10` deve mostrar isso com clareza.

## 3. Organizar por timeline
O `Arm 10` nao e so um kanban.
Ele tambem precisa pensar como timeline de montagem.

Trilhas iniciais:
- `V1` = video principal
- `V2` = overlay, apoio visual, recortes
- `A1` = locucao principal
- `A2` = efeitos sonoros
- `A3` = trilha musical

Cada bloco deve poder receber:
1. `track`
2. `in_point_ms`
3. `out_point_ms`
4. `file_reference`
5. `prompt_origin_id`

## 4. Organizar por dependencia
Alguns blocos dependem de outros.

Exemplos:
1. A locucao vem antes da sincronizacao de imagem.
2. A imagem pode depender do texto narrado.
3. A trilha pode depender do tom emocional do bloco de fala.

O `Arm 10` precisa registrar dependencias para evitar caos na montagem.

## 5. Organizar por projeto
O `Arm 10` deve permitir multiplos projetos sem mistura.

Cada projeto precisa de:
1. `project_id`
2. `nome`
3. `objetivo`
4. `timeline`
5. `blocks`
6. `estado_global`

## O que o Arm 10 nao deve fazer
O `Arm 10` nao deve:
1. inventar prompts no lugar do `Arm 09`
2. virar editor de video completo
3. misturar projetos diferentes
4. perder o vinculo entre prompt e ativo final
5. transformar tudo em capsula

## Resultado esperado
No fim, o `Arm 10` deve entregar ordem.

O usuario precisa conseguir:
1. saber o que ja foi feito
2. saber o que falta fazer
3. saber qual IA usar em cada bloco
4. saber onde cada arquivo entra
5. exportar a estrutura para montagem final

## Export futuro
O `Arm 10` deve nascer pensando em exportar para:
1. `json` interno do HCB Studio
2. `timeline.schema.json`
3. formatos futuros como `xml`, `edl`, `fcpxml` ou adaptadores para editores

## Relacao com o Arm 09
Relacao correta:
1. `Arm 09` gera o bloco
2. `Arm 10` recebe o bloco
3. `Arm 10` organiza o bloco
4. o usuario executa a ferramenta externa
5. o `Arm 10` recebe o arquivo final e ancora na timeline

## MVP do Arm 10
Primeira versao precisa fazer apenas isto:
1. ler blocos em `02_STORAGE/blocks/prompt_queue`
2. consolidar tudo em um arquivo de projeto/timeline
3. permitir atualizacao de status
4. registrar `track`, `in_point_ms`, `out_point_ms`
5. apontar o `file_reference` quando o ativo existir

## Perguntas que devem ser validadas juntos antes da implementacao
1. O `Arm 10` sera centrado em um projeto por vez ou multi-projeto desde o inicio?
2. O estado `gerado` entra ja no MVP ou comecamos com `prompt_pronto`, `revisao` e `concluido`?
3. O primeiro export sera apenas JSON interno ou ja vale preparar XML/EDL?
4. A timeline sera preenchida manualmente no inicio ou por sugestao automatica?

## Regra de construcao
O `Arm 10` deve ser construido com calma e validado em blocos.
Ele e um organizador de producao, nao um monstro que tenta fazer tudo ao mesmo tempo.

## Decisoes validadas
1. Cada projeto tera sua propria gaveta especifica.
2. O estado `gerado` entra no fluxo desde o inicio.
3. O objetivo final do `Arm 10` e ser completo no fechamento da montagem.
4. A ancoragem de timeline deve ser automatica por IA sempre que possivel.

## Estrutura de projetos
O `Arm 10` nao deve misturar producoes.
Cada projeto precisa viver em sua propria gaveta de trabalho, com seus blocos, timeline e ativos.

Estrutura esperada:
1. uma gaveta por projeto
2. uma timeline por projeto
3. um conjunto de blocos por projeto
4. uma trilha de ativos por projeto

## Estados obrigatorios do fluxo
Estados minimos aprovados:
1. `draft`
2. `prompt_pronto`
3. `executando`
4. `gerado`
5. `revisao`
6. `aprovado`
7. `concluido`
8. `descartado`

O estado `gerado` e obrigatorio porque o `Arm 10` precisa saber quando a IA externa devolveu um ativo real:
- voz
- som ambiente
- musica
- imagem
- video
- outros derivados

## A IA no meio do fluxo
Sim, existe uma IA no meio, e isso e parte central da arquitetura.

Fluxo correto:
1. o usuario define a ideia
2. o `Arm 09` transforma a ideia em prompt especializado
3. uma IA externa executa esse prompt e gera o ativo
4. o `Arm 10` recebe o ativo gerado
5. o `Arm 10` ancora esse ativo na timeline do projeto

Ou seja:
- o `Arm 09` fala com a IA certa
- a IA externa gera o material
- o `Arm 10` organiza o resultado

O `Arm 10` nao substitui a IA externa.
Ele coordena e organiza o que a IA externa produziu.

## Relacao real entre Arm 09 e Arm 10
O `Arm 09` e o tradutor de intencao.
O `Arm 10` e o organizador de producao.

Juncao correta:
1. `Arm 09` gera bloco de prompt
2. esse bloco vai para a IA especialista
3. a IA devolve um ativo
4. `Arm 10` liga o ativo ao `prompt_origin_id`
5. `Arm 10` posiciona o ativo na timeline

Sem esse vinculo, o sistema perde rastreabilidade.

## Timeline e precisao automatica
A timeline deve ser automatica por padrao, porque a IA consegue manter consistencia estrutural melhor do que o humano em tarefas repetitivas de sincronizacao.

Isso significa que o `Arm 10` deve:
1. sugerir ou preencher `track`
2. sugerir ou preencher `in_point_ms`
3. sugerir ou preencher `out_point_ms`
4. manter vinculacao com o ativo final

O humano revisa.
Mas a primeira organizacao deve vir do sistema.

## Export final
Se for final, tem que ser completo.

Entao o `Arm 10` deve nascer com direcao de export total:
1. JSON interno completo
2. timeline completa
3. referencias de arquivos
4. estados de blocos
5. base para exportadores futuros

O primeiro passo ainda pode ser JSON interno.
Mas a arquitetura ja precisa prever export final serio.
