#include "hashmap.h"

int main()
{
    map* m = map_create(16);
    Put(m, "apple", 5);
    Put(m, "banana", 10);
    int found;
    int val = Get(m, "apple", &found);
    printf("apple: %d (found: %d)\n", val, found);
    val = Get(m, "cherry", &found);
    printf("cherry: %d (found: %d)\n", val, found);
    Delete(m, "apple");
    val = Get(m, "apple", &found);
    printf("apple after delete: %d (found: %d)\n", val, found);

    map_destroy(m);
    return 0;
}

