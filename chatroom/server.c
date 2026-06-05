#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "server.h"
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

    

    Client clients[64];
    int client_count = 0;
    
    /*
            select() wakes up
            → New connection? Accept it, add to array
            → For each client: did they send something?
            → Yes and data > 0: broadcast to everyone else
            → Yes and data = 0: they left, remove them
            → No: skip, they're idle
            → Back to select(), wait again

    Old Design Drawbacks :  it received bytes and forwarded them. 
    It had no concept of "who" sent what. 
    Every client was just a file descriptor number. If three people were chatting, you'd see messages with no idea who said them
    */

    /*
        CONNECTED (has_nickname = 0)
            → receives first message
            → saves nickname
            → broadcasts "[name] has joined"
    
        IDENTIFIED (has_nickname = 1)
            → receives messages
            → broadcasts "[name]: message" to everyone else

        DISCONNECTED (read returns 0)
            → close fd
            → remove from array
    snprintf(formatted, sizeof(formatted), "[%s]: %s", ...) constructs a new string safely with a size limit. This prevents buffer overflows — if someone sends a 500-byte message and their nickname is 30 bytes, we don't write past the end of our array.

    New Approach : This is a fundamental concept in server design. 
    Instead of just tracking a file descriptor, we track a session — a struct that holds everything you know about that client. 
    Right now that's their fd, their nickname, and whether they've set a nickname yet. 
    */
    
    while(1)
    {
        fd_set read_fds;

        FD_ZERO(&read_fds);
        FD_SET(server_fd,&read_fds);

        int max_fd = server_fd;

        for(int i = 0; i< client_count;i++)
        {
            FD_SET(clients[i].fd,&read_fds);
            if(clients[i].fd > max_fd)
            {
                max_fd = clients[i].fd;
            }
        }

        select(max_fd + 1, &read_fds,NULL,NULL,NULL);
        if(FD_ISSET(server_fd,&read_fds))
        {
            int new_client =  accept(server_fd,NULL,NULL);
            clients[client_count].fd = new_client;
            clients[client_count].has_nickname = 0;
            client_count++;
            
            printf("New client connected! Total: %d\n", client_count);
        }
        
        for(int i = 0; i< client_count;i++)
        {
            if(FD_ISSET(clients[i].fd,&read_fds))
            {

                char buffer[256];
                int n = recv(clients[i].fd,buffer,sizeof(buffer),0);

                if(n <= 0)
                {
                    close(clients[i].fd);
                    clients[i].fd = clients[--client_count].fd;
                }
                else
                {
                    buffer[n] = '\0';
                    if(clients[i].has_nickname == 0)
                    {
                        buffer[strcspn(buffer,"\n")] = '\0';
                        strncpy(clients[i].nickname,buffer,31);
                        clients[i].has_nickname = 1;

                        char join_msg[256];
                        snprintf(join_msg,sizeof(join_msg),"[%s] has joined the chat\n",clients[i].nickname);
                        printf("%s",join_msg);
                        for(int j = 0; j < client_count;j++)
                        {
                            if(j != i)
                            {
                                write(clients[j].fd,join_msg,strlen(join_msg));
                            }
                        }
                    }
                    else{

                        if(strncmp(buffer,"/msg ",5) == 0)
                        {
                            //Parse: "/msg Kent hey there"
                            char target_name[32];
                            char private_msg[256];
                            sscanf(buffer,"/msg %s %[^\n]",target_name,private_msg);

                            //Finding the target client
                            for(int j = 0; j < client_count;j++)
                            {
                                if(strcmp(clients[j].nickname,target_name) == 0)
                                {
                                    char formatted[512];
                                    snprintf(formatted,sizeof(formatted),"[PM from %s]: %s\n",clients[i].nickname,private_msg);
                                    write(clients[j].fd,formatted,strlen(formatted));
                                    break;
                                }
                            }
                        }
                        else
                        {
                            char formatted[512];
                            snprintf(formatted,sizeof(formatted),"[%s]: %s",clients[i].nickname,buffer);
                            printf("%s",formatted);
                            for(int j = 0; j < client_count;j++)
                            {
                                if(j != i) write(clients[j].fd,formatted,strlen(formatted));
                            }
                        }
                    }
                    
                }
            }
        }

    }
}