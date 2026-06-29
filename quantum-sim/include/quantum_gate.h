#ifndef QUANTUM_GATE_H
#define QUANTUM_GATE_H

#include <complex>
#include <cmath>
#include "matrix.h"

namespace quantum {
namespace gates {

    using Complex = std::complex<double>;

    // Hadamard: (1/√2) [[1, 1], [1, -1]]  — creates superposition
    inline Matrix<Complex> hadamard() {
        Matrix<Complex> H(2, 2);
        double s = 1.0 / std::sqrt(2.0);
        H(0, 0) = Complex(s, 0.0);  H(0, 1) = Complex(s, 0.0);
        H(1, 0) = Complex(s, 0.0);  H(1, 1) = Complex(-s, 0.0);
        return H;
    }

    // Pauli-X: [[0, 1], [1, 0]]  — the quantum NOT, swaps |0> and |1>
    inline Matrix<Complex> pauliX() {
        Matrix<Complex> X(2, 2);
        // YOUR TURN: fill the four entries. X swaps the amplitudes.
        X(0,0) = Complex(0.0,0.0);  X(0,1) = Complex(1.0,0.0);
        X(1,0) = Complex(1.0,0.0);  X(1,1) = Complex(0.0,0.0);
        return X;
    }

} // namespace gates
} // namespace quantum
#endif