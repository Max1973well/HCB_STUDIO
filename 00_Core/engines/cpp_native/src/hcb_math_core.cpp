
// hcb_math_core.cpp
// Motor de Cálculo Nativo para HCB Studio
// Compilar como DLL/Shared Lib

#include <iostream>
#include <vector>

extern "C" {
    // Função exportada para ser chamada pelo Python
    __declspec(dllexport) double hcb_fast_process(double* data, int size) {
        double sum = 0;
        for(int i = 0; i < size; i++) {
            sum += (data[i] * 1.5); // Simulação de carga pesada
        }
        return sum;
    }

    __declspec(dllexport) void hcb_identity() {
        std::cout << "[CPP KERNEL] HCB Native Core v1.0 Online." << std::endl;
    }
}
