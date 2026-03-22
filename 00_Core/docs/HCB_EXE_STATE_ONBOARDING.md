# HCB.exe HCB State Onboarding

## Objetivo
O `HCB State` captura como o usuário está agora.
Ele não substitui o `SCI`.

Regra:
- `SCI` = identidade estável
- `HCB State` = condição operacional do momento

## Perguntas objetivas
1. Modo atual
2. Energia agora
3. Foco agora
4. Urgência agora
5. Carga cognitiva agora
6. Preferência de resposta agora
7. Projeto ativo
8. Fadiga agora
9. Dor agora
10. Sobrecarga visual agora
11. Precisa de pausa agora
12. Observações do momento

## Comandos atuais
Listar perguntas:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py state questions
```

Wizard no terminal:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py state wizard --user-id maxwell
```

Bootstrap direto por flags:
```powershell
python F:\HCB_STUDIO\00_Core\scripts\hcb_control.py state init --user-id maxwell --mode work --energy medium --focus normal --urgency medium --cognitive-load moderate --response-preference balanced
```

## Saída esperada
O onboarding gera:
- `01_Archivus/users/hcb_states/<user_id>.json`

## Regra de implementação
O `HCB State` deve ser rápido de responder.
Ele existe para adaptar a sessão atual sem reescrever a identidade permanente.
