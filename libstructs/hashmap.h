#include<stdio.h>
#include<stdlib.h>
#include<string.h>

#ifndef HASHMAP_H
#define HASHMAP_H

typedef struct Entry{
    char* key;
    int value;
    struct Entry* next;

}entry;

typedef struct{
    entry** buckets;
    int capacity;
    int NumElems;
}map;

map* map_create(int capacity);
void map_destroy(map*);

unsigned int hash(const char*,int);
void Put(map*,const char*,int);
int Get(map*,const char*,int*);
void Delete(map*,const char*);


#endif