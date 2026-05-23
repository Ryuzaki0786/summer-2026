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

void VecPush(Vector*,int);
int VecPop(Vector*);
int VecGet(Vector*,int);
void VecSet(Vector*,int,int);
int VecSize(Vector*);






#endif