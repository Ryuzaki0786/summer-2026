#ifndef QUANTUM_REGISTER_H
#define QUANTUM_REGISTER_H


#include <complex>
#include <stdexcept>
#include <cmath>
#include "matrix.h"
#include "vector.h"

namespace quantum {
    class QuantumRegister {
        public:
            using Complex = std :: complex<double>;

            explicit QuantumRegister(int n);

            int numQubits() const {return n_qubits_;}
            int size() const { return state_.size(); }

            double probability(int basis_state) const;

            void applyGate(const Matrix<Complex>& gate);

            void applyGateToQubit(const Matrix<Complex>& gate,int target);

            void print() const;

            const Vector<Complex>& state() const {return state_; }
        

        private:
            int n_qubits_;
            Vector<Complex> state_;
    };

    QuantumRegister :: QuantumRegister(int n)
    : n_qubits_(n),
        state_(1 << n)
        {
            if( n < 1) throw std::invalid_argument("QuantumRegister needs at least 1 quibit");
            state_(0) = Complex(1.0,0.0);
        }
    double QuantumRegister :: probability(int basis_state) const
    {
        return (std :: norm(state_(basis_state)));
    }

    void QuantumRegister :: applyGate(const Matrix<Complex>& gate)
    {
        int dim = size();
        if(gate.rows() != dim || gate.cols() != dim){
            throw std::invalid_argument("Whole-register gate must be 2^n x 2^n");
        }
        state_ = gate * state_;
    }

    void QuantumRegister :: applyGateToQubit(const Matrix<Complex>& gate, int target){
        if (target < 0 || target > n_qubits_ - 1)
            throw std::invalid_argument("target qubit out of range");
        if (gate.rows() != 2 || gate.cols() != 2)
            throw std::invalid_argument("single-qubit gate must be 2x2");

        int bit = 1 << target;          
        for(int i = 0; i < size();i++)
        {
            if((i & bit) == 0){
                int j = i | bit;
                Complex a = state_(i);
                Complex b = state_(j);

                state_(i) = gate(0,0) * a + gate(0,1) * b;
                state_(j) = gate(1,0) * a + gate(1,1) * b;
                
            }
        }
    }
    
}

#endif