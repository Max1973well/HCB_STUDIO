from playsound import playsound


async def falar(texto):
    output_file = r"F:\HCB_STUDIO\04_TEMP\archie_response.mp3"

    # Gerar a voz neural (Antonio é a voz mais sofisticada)
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
    await communicate.save(output_file)

    print(f"[ARCHIE]: {texto}")  # Ele escreve E fala

    # Toca o som de forma invisível
    try:
        playsound(output_file)
    except Exception as e:
        print(f"[AVISO] O player estava ocupado, mas Archie disse: {texto}")