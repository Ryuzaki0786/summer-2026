#ifndef MATRIX_H
#define MATRIX_H

#include <vector>
#include <iostream>
#include <stdexcept>
#include <complex>

namespace quantum
{
    template <typename T>

    class Matrix
    {
        private:
            int rows_;
            int cols_;

            //store a 2D matrix as a 1D array. Element (i, j) lives at index i * cols_ + j. This is row-major order — same row elements are next to each other in memory, which is cache-friendly.
            std :: vector<T> data_;
        public:
            //Constructors
            Matrix(int rows,int cols);
            Matrix(int rows,int cols, T initial_value);

            //Element access - mat(i,j)
            T& operator() (int i,int j);
            const T& operator()(int i, int j) const;

            //Getters
            int rows() const {return rows_;}
            int cols() const {return cols_;}

            //Matrix operations
            Matrix<T> operator+(const Matrix<T>& other) const;
            Matrix<T> operator-(const Matrix<T>& other) const;
            Matrix<T> operator*(const Matrix<T>& other) const;

            //Utility
            static Matrix<T> identity(int n);
            Matrix<T> transpose() const;
            void print() const;
    };

    // Creates a rows x cols matrix with every element zero-initialized (T(0)).
    // The flat vector is sized rows*cols; element (i,j) maps to index i*cols+j.
    template <typename T>
    Matrix<T> :: Matrix(int rows, int cols)
        : rows_(rows), cols_(cols),data_(rows * cols, T(0)) {}

    // Creates a rows x cols matrix with every element set to initial_value.
    template <typename T>
    Matrix<T> :: Matrix(int rows, int cols, T initial_value)
        : rows_(rows), cols_(cols), data_(rows * cols, initial_value) {}
    
    template <typename T>
    T& Matrix<T> ::operator()(int i, int j)
    {
        return data_[i * cols_ + j ];
    }
    template <typename T>
    const T& Matrix<T>::operator()(int i, int j) const {
    return data_[i * cols_ + j];
    }

    template <typename T>
    Matrix<T> Matrix<T> :: operator+(const Matrix<T>& other) const{
        if(rows_ != other.rows_ || cols_ != other.cols_)
        {
            throw std::invalid_argument("Matrix dimensions do not match for addition");
        }
        Matrix<T> result(rows_,cols_);
        for(int i = 0; i < rows_ * cols_;i++)
        {
            result.data_[i] = data_[i] + other.data_[i];
        }
        return result;
    }
    template <typename T>
    Matrix<T> Matrix<T> :: operator-(const Matrix<T>& other) const{
        if(rows_ != other.rows_ || cols_ != other.cols_)
        {
            throw std::invalid_argument("Matrix dimensions do not match for subtraction");
        }
        Matrix<T> result(rows_,cols_);
        for(int i = 0; i < rows_ * cols_;i++)
        {
            result.data_[i] = data_[i] - other.data_[i];
        }
        return result;
    }

    template <typename T>
    Matrix<T> Matrix<T> :: operator*(const Matrix<T>& other) const{
        if(cols_ != other.rows_)
        {
            throw std::invalid_argument("Matrix dimensions do not match for Multiplication");
        }
        Matrix<T> result(rows_,other.cols_);
        for(int i = 0; i<rows_;i++)
        {
            for(int j = 0;j < other.cols_; j++)
            {
                for(int k = 0; k < cols_; k++)
                {
                    result.data_[i * other.cols_ + j] += data_[i * cols_ + k] * other.data_[k * other.cols_ + j];
                }
            }
        }
        return result;
    }

    template <typename T>
    Matrix<T> Matrix<T> :: transpose() const {
        Matrix<T> result(cols_,rows_); //flipped dimensions

        for(int i = 0;i < rows_;i++)
        {
            for(int j = 0; j <cols_;j++)
            {
                result.data_[j * rows_ + i] = data_[i * cols_ + j];
            }
        }
        return result;
    }

    template <typename T>
    Matrix<T> Matrix<T>::identity(int n){
        Matrix<T> result(n,n);
        for(int i = 0 ; i < n;i++)
        {
            result.data_[i * n + i] = 1;
        }
        return result;
    }

    template <typename T>
    void Matrix<T>::print() const{
        for(int i = 0; i < rows_;i++)
        {
            for(int j = 0; j<cols_;j++)
            {
                std::cout <<data_[i * cols_ + j]<< " ";
            }
            std::cout<<"\n";
        }
    }

}

#endif