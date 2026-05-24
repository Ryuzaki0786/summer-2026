#include "dynarray.h"

int main() {
    Vector* v = vector_create();
    Push(v, 10);
    Push(v, 20);
    Push(v, 30);
    printf("Size: %d\n", Size(v));
    printf("Get index 1: %d\n", Get(v, 1));
    Set(v, 1, 99);
    printf("After set: %d\n", Get(v, 1));
    printf("Pop: %d\n", Pop(v));
    printf("Size after pop: %d\n", Size(v));

    // stress test - push 1000 elements
    Vector* big = vector_create();
    for (int i = 0; i < 1000; i++) {
        Push(big, i);
    }
    printf("Big size: %d\n", Size(big));
    printf("Big[999]: %d\n", Get(big, 999));
    vector_destroy(big);

    vector_destroy(v);
    return 0;
}