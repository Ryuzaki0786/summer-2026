#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int main()
{
    int sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(9090);
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);

    int result = connect(sock, (struct sockaddr*)&addr, sizeof(addr));
    printf("Connect result: %d\n",result);

    printf("Connected to server!\n");

    char buffer[256];
    while (1)
    {
        printf("You: ");
        fgets(buffer, 256, stdin);
        write(sock, buffer, strlen(buffer));

        ssize_t bytes = read(sock, buffer, 256);
        if (bytes <= 0) break;
        buffer[bytes] = '\0';
        printf("Server: %s", buffer);
    }

    close(sock);
    return 0;
}