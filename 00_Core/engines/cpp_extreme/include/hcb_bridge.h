#ifndef HCB_BRIDGE_H
#define HCB_BRIDGE_H

#include <windows.h>
#include <iostream>
#include <string>

// Definição de constantes de sinalização
#define SHM_NAME "Local\\HCB_STUDIO_SHARED_MEM"
#define SHM_SIZE 4096 // 4KB é mais que suficiente para metadados e sinais

// Estrutura da Cápsula (O que reside na memória RAM)
struct HcbMemoryCapsule {
    // Sinais de Sincronização (Atômicos)
    int sentinel_active;    // 1 se Python estiver rodando
    int cortex_active;      // 1 se Rust estiver rodando
    int last_action_code;   // Código da última tarefa (1=Classificou, 2=Encriptou, 3=Voz)

    // Dados de Telemetria
    unsigned long long total_processed;
    float system_load;

    // Buffer de Comunicação (Onde as strings de comando passam)
    char last_command[256];
    char last_file_path[512];

    // Timestamp da última pulsação
    unsigned long long heartbeat;
};

// Interface da DLL
extern "C" {
    __declspec(dllexport) bool __stdcall InitializeBridge();
    __declspec(dllexport) bool __stdcall WriteSignal(int action_code, const char* message);
    __declspec(dllexport) HcbMemoryCapsule* __stdcall GetMemoryPointer();
    __declspec(dllexport) void __stdcall CloseBridge();
}

#endif