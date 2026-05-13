#include<stdio.h>
#include<string.h>
#include<stdlib.h>

void ReverseString(char* str)
{
    int length = strlen(str);
    int start = 0;
    int end = length - 1;
    char temp;
    
    while(start < end)
    {
        temp = str[start];
        str[start] = str[end];
        str[end] = temp;

        start++;
        end--;
    }
}

int main(int argc, char **argv)
{
    if(argc != 2)
    {
        return EXIT_FAILURE;
    }

    char *Str = argv[1];
    ReverseString(Str);
    printf("Reversed String: %s\n",Str);
    return EXIT_SUCCESS;
}