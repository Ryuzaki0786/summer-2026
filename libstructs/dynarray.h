#include<stdio.h>
#include<stdlib.h>

#ifndef DYNARRAY_H
#define DYNARRAY_H

typedef struct
{
    int* data;
    int NumElems;
    int TotalSize;
}Vector;


//LifeCycle
Vector* vector_create();
void vector_destroy(Vector*);

void Push(Vector*,int);
int Pop(Vector*);
int Get(Vector*,int);
void Set(Vector*,int,int);
int Size(Vector*);






#endif