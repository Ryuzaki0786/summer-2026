#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int main()
{
    //Creating a socket
    int server_fd = socket(AF_INET,SOCK_STREAM, 0);
    printf("Socket created: %d\n",server_fd);

    //Binding to port 8080
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(9090);

    int opt = 1;
    setsockopt(server_fd,SOL_SOCKET,SO_REUSEADDR,&opt,sizeof(opt));

    int b = bind(server_fd, (struct sockaddr*)&addr, sizeof(addr));
    printf("Bind result: %d\n",b);

    //Listen
    listen(server_fd, 5);
    printf("Server listening on port 9090...\n");

    //Accept a client
    int client_fd =  accept(server_fd,NULL,NULL);
    printf("Client connected: %d\n",client_fd);

    //Echo loop - read from client, send it back
    char buffer[256];
    while(1)
    {
        ssize_t Bytes_read = read(client_fd,buffer,256);
        
        if(Bytes_read == 0)
        {
            printf("The client disconnected");
            break;
        }
        buffer[Bytes_read] = '\0'; 
        printf("Received: %s", buffer);

        write(client_fd,buffer,Bytes_read);
    }
}