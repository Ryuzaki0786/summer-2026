
#ifndef SERVER_H
#define SERVER_H

typedef struct
{
    int fd; //How to talk to other people
    char nickname[32]; //Who they are
    int has_nickname; //have they yet identified themselves
    /* data */
} Client;

#endif