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

void VecPush(Vector* V, int Val)
{
    if(V->NumElems == V->TotalSize)
    {
        V->TotalSize = V->TotalSize * 2;
        Vector* temp = realloc(V->data,V->TotalSize * sizeof(int));

        if(temp == NULL)
        {
            free(V);
        }
        V->data = temp;
    }
    V->data[V->NumElems] = Val;
    V->NumElems++;
}