#include <iostream>
#include "../include/quantum_register.h"
#include "../include/quantum_gate.h"

int main() {
    using namespace quantum;

    // --- Test 1: H on qubit 0 of a 1-qubit register (simplest case) ---
    std::cout << "=== Test 1: H on q0, 1-qubit register ===\n";
    QuantumRegister reg1(1);
    reg1.applyGateToQubit(gates::hadamard(), 0);
    std::cout << "P(0)=" << reg1.probability(0)
              << "  P(1)=" << reg1.probability(1) << "\n";
    std::cout << "(expect 0.5, 0.5)\n\n";

    // --- Test 2: H on qubit 0 of a 2-qubit register (tests the pairing logic) ---
    std::cout << "=== Test 2: H on q0, 2-qubit register ===\n";
    QuantumRegister reg2(2);
    reg2.applyGateToQubit(gates::hadamard(), 0);
    for (int i = 0; i < 4; i++)
        std::cout << "P(" << i << ")=" << reg2.probability(i) << "  ";
    std::cout << "\n(expect P(0)=0.5, P(2)=0.5, others 0)\n\n";


    std::cout << "=== Test 3: H on q1, 2-qubit register ===\n";
    QuantumRegister reg3(2);
    reg3.applyGateToQubit(gates::hadamard(), 1);   // qubit 1 this time
    for (int i = 0; i < 4; i++)
        std::cout << "P(" << i << ")=" << reg3.probability(i) << "  ";
    std::cout << "\n(expect P(0)=0.5, P(2)=0.5, others 0)\n";


    std::cout << "=== Bell state: H(q0) then CNOT(0->1) ===\n";
    QuantumRegister bell(2);                      // |00> = [1,0,0,0]
    bell.applyGateToQubit(gates::hadamard(), 0);  // -> [1/√2, 0, 1/√2, 0]
    bell.applyCNOT(0, 1);                         // control=0, target=1 -> entangle
    for (int i = 0; i < 4; i++)
        std::cout << "P(" << i << ")=" << bell.probability(i) << "  ";
    std::cout << "\n(expect P(0)=0.5, P(3)=0.5, P(1)=P(2)=0)\n";
    return 0;
}