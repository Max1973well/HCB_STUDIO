import sounddevice as sd
import numpy as np


def test_microphone():
    print("--- HCB STUDIO: TESTE DE HARDWARE DE ÁUDIO ---")
    print("Dispositivos detectados:")
    print(sd.query_devices())

    duration = 3  # segundos
    fs = 44100  # frequência

    print(f"\n[!] Gravando por {duration} segundos... FALE ALGO!")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    volume_norm = np.linalg.norm(recording) * 10
    print(f"\n[RESULTADO] Nível de volume capturado: {volume_norm:.2f}")

    if volume_norm > 0.1:
        print("✅ SUCESSO: O Archie ouviu você!")
    else:
        print("❌ FALHA: Silêncio detectado. Verifique o microfone padrão do Windows.")


if __name__ == "__main__":
    test_microphone()