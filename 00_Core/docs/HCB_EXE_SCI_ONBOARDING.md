# HCB.exe SCI Onboarding

## Objetivo
O `HCB.exe` deve criar a identidade base do usuário antes de qualquer interação operacional.

Regra:
- sem `SCI` carregado, o sistema entra em modo degradado
- com `SCI` carregado, o sistema adapta tom, profundidade e ritmo

## Perguntas objetivas
1. Nome de exibição do usuário
2. Idioma principal
3. Fuso horário
4. Perfil principal de uso
5. Nível técnico
6. Tom preferido
7. Profundidade de resposta
8. Precisa de passo a passo
9. Estilo de correção
10. Precisa de adaptação
11. Suporte visual
12. Suporte motor
13. Suporte para fadiga
14. Observações de acessibilidade

## Perfis válidos
- `general`
- `creator`
- `student`
- `teacher`
- `researcher`
- `business`
- `developer`

## Comandos atuais
Listar perguntas:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py identity questions
```

Wizard no terminal:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py identity wizard --user-id maxwell
```

Bootstrap direto por flags:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py identity init --user-id maxwell --display-name "Maxwell" --role-profile creator --technical-level intermediate --preferred-tone direct --response-depth balanced --step-by-step
```

## Saída esperada
O onboarding gera:
- `01_Archivus/users/sci_profiles/<user_id>.json`

Depois disso, o próximo passo é gerar o estado dinâmico:
- `01_Archivus/users/hcb_states/<user_id>.json`

## Regra de implementação
O onboarding deve ser curto, claro e sem linguagem clínica.
`SCI` captura identidade operacional estável.
`HCB State` captura condição operacional do momento.
