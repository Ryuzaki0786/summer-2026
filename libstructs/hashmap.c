#include "hashmap.h"


map* map_create(int capacity)
{
    map* m = malloc(sizeof(map));
    m->buckets = calloc(capacity,sizeof(entry*));
    m->capacity = capacity;
    m->NumElems = 0;

    return m;
}

unsigned int hash(const char* key, int capacity)
{
    unsigned long h = 5381;
    int c;
    while((c = *key++))
    {
        h = ((h << 5) + h) + c;

    }
    return h % capacity;
}

void Put(map* m, const char* key, int value)
{
    int index = hash(key,m->capacity);
    
    entry* current = m->buckets[index];
    while(current != NULL)
    {
        if(strcmp(current->key,key) == 0)
        {
            current->value = value;
            return;
        }
        current = current->next;
    }
    //key does not exist
    entry* newEntry =  malloc(sizeof(entry));
    newEntry->key = strdup(key);
    newEntry->value = value;
    newEntry->next = m->buckets[index];
    m->buckets[index] = newEntry;
    m->NumElems++;
}

int Get(map* m, const char* key, int* found)
{
    *found = 0;
    int index = hash(key,m->capacity);
    entry* current = m->buckets[index];

    while(current != NULL)
    {
        if(strcmp(current->key,key)==0)
        {
            *found = 1;
            return current->value;
        }
        current = current->next;
    }
    return 0;
}

void Delete(map* m, const char* key)
{
    int index = hash(key,m->capacity);
    entry* current = m->buckets[index];
    entry* prev = NULL;

    while(current != NULL)
    {
        if(strcmp(current->key,key)==0)
        {
            if(prev==NULL)
            {
                m->buckets[index] = current->next;
            }
            else{
                prev->next = current->next;
            }
            free(current->key);
            free(current);
            m->NumElems--;
            return;
        }
        prev = current;
        current = current->next;
    }
}

void map_destroy(map* m)
{
    free(m->buckets);
    free(m);
}