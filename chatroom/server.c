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

    

    int clients[64];
    int client_count = 0;
    
    /*
            select() wakes up
            → New connection? Accept it, add to array
            → For each client: did they send something?
            → Yes and data > 0: broadcast to everyone else
            → Yes and data = 0: they left, remove them
            → No: skip, they're idle
            → Back to select(), wait again
    */
    while(1)
    {
        fd_set read_fds;

        FD_ZERO(&read_fds);
        FD_SET(server_fd,&read_fds);

        int max_fd = server_fd;

        for(int i = 0; i< client_count;i++)
        {
            FD_SET(clients[i],&read_fds);
            if(clients[i] > max_fd)
            {
                max_fd = clients[i];
            }
        }

        select(max_fd + 1, &read_fds,NULL,NULL,NULL);
        if(FD_ISSET(server_fd,&read_fds))
        {
            int new_client =  accept(server_fd,NULL,NULL);
            clients[client_count++] = new_client;
            printf("New client connected! Total: %d\n", client_count);
        }
        
        for(int i = 0; i< client_count;i++)
        {
            if(FD_ISSET(clients[i],&read_fds))
            {

                char buffer[256];
                int n = recv(clients[i],buffer,sizeof(buffer),0);

                if(n <= 0)
                {
                    close(clients[i]);
                    clients[i] = clients[--client_count];
                }
                else
                {
                    buffer[n] = '\0';
                    printf("Received: %s",buffer);

                    for(int j = 0; j<client_count;j++)
                    {
                        if(j != i)
                        {
                            write(clients[j],buffer,n);
                        }
                        
                    }
                }
            }
        }


    }
}