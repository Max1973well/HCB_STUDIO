#include "../include/hcb_bridge.h"
#include <windows.h>

// Ponteiros globais para a memória compartilhada
HANDLE hMapFile = NULL;
HcbMemoryCapsule* pBuf = NULL;

extern "C" {
    // Inicializa a ponte de memória na RAM
    __declspec(dllexport) bool __stdcall InitializeBridge() {
        hMapFile = CreateFileMappingA(
            INVALID_HANDLE_VALUE,
            NULL,
            PAGE_READWRITE,
            0,
            SHM_SIZE,
            SHM_NAME);

        if (hMapFile == NULL) return false;

        pBuf = (HcbMemoryCapsule*) MapViewOfFile(hMapFile,
            FILE_MAP_ALL_ACCESS,
            0,
            0,
            SHM_SIZE);

        if (pBuf == NULL) {
            CloseHandle(hMapFile);
            return false;
        }

        return true;
    }

    // NOVA FUNÇÃO: Entrega o endereço da memória para o Python/Rust
    __declspec(dllexport) HcbMemoryCapsule* __stdcall GetMemoryPointer() {
        return pBuf;
    }

    // Escreve o batimento cardíaco
    __declspec(dllexport) void __stdcall SetHeartbeat(long long value) {
        if (pBuf) pBuf->heartbeat = value;
    }

    // Fecha a conexão
    __declspec(dllexport) void __stdcall CloseBridge() {
        if (pBuf) UnmapViewOfFile(pBuf);
        if (hMapFile) CloseHandle(hMapFile);
    }
}