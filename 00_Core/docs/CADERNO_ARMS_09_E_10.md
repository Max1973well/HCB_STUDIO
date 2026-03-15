# Caderno de Design - Arms 09 & 10 (Criador de Conteúdo)

Este caderno documenta a arquitetura teórica e a transição lógica entre o **Arm 09 (Universal Prompt Writer)** e o **Arm 10 (Production Block Organizer)** no ecossistema do HCB Studio.

## 1. Arm 09 - Universal Prompt Writer (A "Mente Criativa")

O objetivo do Arm 09 é atuar como um roteirista/tradutor magistral. O Criador entra com uma "ideia bruta de padaria" e o Arm 09 devolve os prompts perfeitos para as IAs especialistas.

### 1.1 Funcionalidades Principais
- **Ingestão de Intenção:** Recebe uma ordem vaga (ex: "Quero uma imagem de um dragão neon cyberpunk para a capa do vídeo").
- **Adaptação de Target:** Ajusta as palavras-chave, formato, peso e idioma com base na IA destino (Midjourney usa descritores técnicos em inglês com pesos `::`; ElevenLabs precisa de marcações de pausa rítmicas de voz natural, etc).
- **Geração de Variações:** Nunca gera um único prompt. Sempre oferece a versão principal, a versão curta (para testes rápidos) e a variante artística/ousada.
- **Validação de Restrições:** Incorpora os limites do formato que o Criador precisa (Stories 9:16, YouTube 16:9, etc).

### 1.2 Estrutura do Artefato (Output do Arm 09)
O resultado do Arm 09 NÃO é apenas um texto na tela. Ele gera um artefato (JSON/Markdown) interno:
```json
{
  "block_id": "blk_9x21abc",
  "tipo_de_ativo": "image",
  "ferramenta_destino": "midjourney",
  "prompt_oficial": "A neon-lit cyberpunk dragon swooping over a rainy metropolis at night, dramatic atmospheric lighting, neon reflections on wet asphalt, cinematic composition, hyper-detailed, 8k resolution, Unreal Engine 5 render, trending on ArtStation --ar 16:9 --v 6.0",
  "prompt_curto": "cyberpunk dragon over rainy neon city, dramatic lighting --ar 16:9",
  "estado": "aguardando_geracao"
}
```

---

## 2. A Transição Lógica: Arm 09 -> Arm 10

A grande mágica do HCB Studio é que o fluxo não morre quando o prompt é gerado. A "cola" entre as duas braços funciona assim:

1. O Criador usa o **Arm 09**.
2. O **Arm 09** emite o Output JSON estruturado (visto acima) e deposita na zona de trânsito (ex: `04_TEMP` ou `02_STORAGE/blocks`).
3. Imediatamente após a aprovação do prompt pelo usuário, o sistema repassa a posse (handoff) desse bloco para o **Arm 10**.

O Arm 09 diz: *"Fiz minha parte, o roteiro está pronto."*  
O Arm 10 diz: *"Recebido! Vou colocar esse bloco na minha fila de produção e vigiar até virar um arquivo real."*

---

## 3. Arm 10 - Production Block Organizer (A "Timeline de Edição")

Você tocou no ponto perfeito: um painel estilo Kanban ("A Fazer", "Feito") é inútil para edição de vídeo. O Arm 10 precisa ser uma verdadeira **Timeline de Metadados**. Ele atua organizando Ativos no Espaço e no Tempo (Frequência, Segundo, Milissegundo).

O Arm 10 garante uma *Organização Precisa*, o que significa que o JSON do projeto agora não é uma pilha de arquivos, mas uma Árvore de Trilha (Track Tree):

### 3.1 A Estrutura de Tempo (Timeline Blocks)
Em vez de um status simples, cada bloco gerado recebe ancoragem temporal.
As trilhas principais que o Arm 10 deve gerenciar são:
- **`V1` (Video Main):** Atores, B-Rolls principais.
- **`V2` (Video Overlay):** Transições, FX, B-rolls sobrepostos.
- **`A1` (Audio Voice):** Locução/Speech (ex: ElevenLabs).
- **`A2` (Audio SFX):** Sons ambientes, Wooshes, Impactos.
- **`A3` (Audio Music):** Trilha sonora (BGM).

Um Bloco do Arm 10 se parecerá com isso:
```json
{
  "track": "A1",
  "block_id": "blk_voz_abertura",
  "in_point_ms": 0,
  "out_point_ms": 4500,
  "file_reference": "02_STORAGE/audio/locucao_abertura.wav",
  "prompt_origin_id": "blk_9x21abc"
}
```

### 3.2 Funcionalidades Principais do Arm 10
- **Agrupamento de Sincronicidade:** Se o locutor fala "dragão neon" aos 00:12s (12000ms), o Arm 10 permite ancorar a imagem do Dragão (`V1`) exatamente em `in_point_ms: 12000`.
- **Validador de Lacunas (Gap-Finder):** O sistema varre a timeline e acusa: "Você tem um buraco de 3 segundos no vídeo entre 00:15 e 00:18, precisa gerar um prompt preenchedor lá."
- **Exportador Universal (EDL/XML):** O Santo Graal do Arm 10 é que, uma vez que todas as peças existam na pasta e a timeline esteja populada em milissegundos, o Arm 10 vai compilar um script legível por máquina (como `.fcpxml` ou `.xml` do Premiere/DaVinci Resolve). Você importa no editor de vídeo e a timeline "monta sozinha" magicamente, os arquivos já caem nos canais e nos tempos corretos.

### 3.3 Essa organização precisa é possível?
**Sim.**
A inteligência artificial não consegue editar o vídeo final perfeitamente, mas ela é **excelente** em organizar o metadados. Se instruirmos o Arm 10 a armazenar não apenas *o que* foi gerado, mas *quando* aquilo entra na timeline (Track, Timestamp IN, Timestamp OUT), ele consegue exportar a "timeline crua" (EDL/XML). O editor humano só vai precisar abrir o Premiere/CapCut desktop e dar os retoques estéticos finos.

## 4. Próximos Passos na Implementação
1. **Contrato de Timeline:** Criar `timeline.schema.json` para definir `tracks`, `in_point_ms` e `out_point_ms`.
2. **Arm 09 (Prompt Writer):** Implementar e injetar o motor de IAs em `arm_09_prompt_writer.py`.
3. **Arm 10 (Block Organizer):** Implementar o gerenciador de tempo em `arm_10_block_organizer.py`.
