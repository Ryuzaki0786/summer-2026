#include "dynarray.h"


Vector* vector_create()
{
    Vector* V =  malloc(sizeof(Vector));
    V->data = malloc(sizeof(int) * 4);

    if(V == NULL)
    {
        free(V);
        return NULL;
    }
    V->NumElems = 0;
    V->TotalSize = 4;

    return V;
}

void Push(Vector* V, int Val)
{
    if(V->NumElems == V->TotalSize)
    {
        V->TotalSize = V->TotalSize * 2;
        int* temp = realloc(V->data,V->TotalSize * sizeof(int));

        if(temp == NULL)
        {
            free(V);
        }
        V->data = temp;
    }
    V->data[V->NumElems] = Val;
    V->NumElems++;
}

int Get(Vector* V, int index)
{
    if(index > V->NumElems || index < 0)
    {
        return -1;
    }
    return V->data[index];

}

void Set(Vector* V, int index, int val)
{
    if(index > V->NumElems || index < 0)
    {
        return;
    }
    V->data[index] = val;
}

int Pop(Vector* V)
{
    return V->data[--V->NumElems];
}
int Size(Vector* V)
{
    return (V->NumElems);
}
void vector_destroy(Vector* V)
{
    free(V->data);
    free(V);
}