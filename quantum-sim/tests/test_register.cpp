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

    std::cout << "=== DEBUG: Bell state before measuring ===\n";
    QuantumRegister dbg(2);
    dbg.applyGateToQubit(gates::hadamard(), 0);
    dbg.applyCNOT(0, 1);
    for (int i = 0; i < 4; i++)
        std::cout << "amp[" << i << "] = " << dbg.state()(i) << "\n";
    std::cout.flush();   // force it to print before any crash

    int out0 = dbg.measureQubit(0);
    std::cout << "measured qubit 0 -> " << out0 << "\n";
    std::cout.flush();
    for (int i = 0; i < 4; i++)
        std::cout << "after m0, amp[" << i << "] = " << dbg.state()(i) << "\n";
    std::cout.flush();

    std::cout << "=== measureQubit on Bell state ===\n";
    int matches = 0, trials = 1000;
    for (int trial = 0; trial < trials; ++trial) {
         QuantumRegister bell(2);
         bell.applyGateToQubit(gates::hadamard(), 0);
         bell.applyCNOT(0, 1);                 // Bell state: (|00> + |11>)/√2

         int m0 = bell.measureQubit(0);        // measure qubit 0
         int m1 = bell.measureQubit(1);        // then measure qubit 1
         if (m0 == m1) matches++;              // entanglement: they MUST agree
     }
     std::cout << "qubit0 == qubit1 in " << matches << "/" << trials << " trials\n";
     std::cout << "(expect 1000/1000 — perfect correlation = entanglement)\n";

     int zeros = 0;
     for (int trial = 0; trial < trials; ++trial) {
         QuantumRegister bell(2);
         bell.applyGateToQubit(gates::hadamard(), 0);
         bell.applyCNOT(0, 1);
         if (bell.measureQubit(0) == 0) zeros++;
     }
     std::cout << "qubit0 measured 0 in " << zeros << "/" << trials << " (expect ~500)\n";

    

    return 0;
}