
#include <windows.h>
#include <iostream>

extern "C" {
    // Função para somar arrays com velocidade nativa
    __declspec(dllexport) double hcb_fast_sum(double* data, int size) {
        double total = 0;
        for(int i = 0; i < size; i++) {
            total += data[i];
        }
        return total;
    }

    // Identidade do Motor
    __declspec(dllexport) void hcb_whoami() {
        std::cout << "[CPP-KERNEL] HCB High-Performance Core (v1.0) :: READY" << std::endl;
    }
}
