#ifndef QUANTUM_REGISTER_H
#define QUANTUM_REGISTER_H


#include <complex>
#include <stdexcept>
#include <cmath>
#include <random>
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

            void applyCNOT(int control,int target);

            int measureQubit (int target);

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

    void QuantumRegister :: applyCNOT(int control, int target){

        if (control < 0 || control >= n_qubits_ || target < 0 || target >= n_qubits_)
            throw std::invalid_argument("CNOT qubit index out of range");
        if (control == target)
            throw std::invalid_argument("CNOT control and target must differ");

        int c = 1 << control;
        int t = 1 << target;

        for(int i = 0; i < size(); i++)
        {
            if((i & c) != 0 && (i & t) == 0){
                int j = i | t;

                Complex temp = state_(i);
                state_(i) = state_(j);
                state_(j) = temp;
            }
        }
    }

    int QuantumRegister :: measureQubit(int target){
        int t = 1 << target;

        double p0 = 0.0;
        //P(0) = sum of |amplitude|^2 where target bit is 0
        for(int i = 0; i < size(); i++)
        {
            if((i & t) == 0) p0 += std::norm(state_(i));
        }

        //random draw
        static std:: random_device rd;
        static std:: mt19937 gen(rd());
        static std :: uniform_real_distribution<double> dist(0.0,1.0);
        double r = dist(gen);
        int outcome = (r < p0) ? 0 : 1;

        //Collapse - zero out amplitudes inconsistent with the outcome
        for(int i = 0; i < size(); i++)
        {
            int bit_value = ((i & t) != 0) ? 1 : 0;   // target qubit's value in basis state i
            if (bit_value != outcome) {
                state_(i) = Complex(0.0, 0.0);        // inconsistent → zero it
            }
        }

        state_ = state_.normalize();

        return outcome;
    }

}

#endif