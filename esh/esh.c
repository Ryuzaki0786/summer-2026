#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>

#include <sys/wait.h>

void remove_newline(char*);
void execute_pipe(char*,char*);
void executeGreater_Than(char*,char*);
void executeSmaller_Than(char*,char*);

int main()
{
    char input[256];
    signal(SIGINT,SIG_IGN);

    while(1)
    {
        printf("esh> ");
        fgets(input,256,stdin);

        if(fgets(input,256,stdin) == NULL)
        {
            printf("\n");
            break;
        }

        remove_newline(input);
        
        if(input[0] == '\0') continue;

        char* pipe_pos = strchr(input,'|');
        if (pipe_pos != NULL)
        {
            *pipe_pos = '\0';         // split into two strings
            char* left = input;
            char* right = pipe_pos + 1;
            execute_pipe(left, right);
            continue;
        }
        

        char* GreaterThan_Pos = strchr(input, '>');
        if(GreaterThan_Pos != NULL)
        {
            *GreaterThan_Pos = '\0';
            char* left =  input;
            char* right = GreaterThan_Pos +  1;
            executeGreater_Than(left,right);
            continue;
        }

        char* SmallerThan_Pos = strchr(input, '<');
        if(SmallerThan_Pos != NULL)
        {
            *SmallerThan_Pos = '\0';
            char* left =  input;
            char* right = SmallerThan_Pos +  1;
            executeSmaller_Than(left,right);
            continue;
        }

        //Tokenize
        char* args[64];
        int argc = 0;

        //strtok splits a string into pieces based on delimiter
        /*
        When the user types ls -l -a, that's one string: "ls -l -a". But execvp needs each word separately — "ls", "-l", "-a".
        After the loop, args looks like: ["ls", "-l", "-a", NULL] — exactly what execvp needs.
            First call:  strtok("ls -l -a", " ")  → returns "ls"
            Second call: strtok(NULL, " ")        → returns "-l"
            Third call:  strtok(NULL, " ")        → returns "-a"
            Fourth call: strtok(NULL, " ")        → returns NULL (no more tokens)
        */
        char* token = strtok(input," ");
        while(token != NULL)
        {
            args[argc] = token;
            argc++;
            token = strtok(NULL," ");
        }
        args[argc] = NULL;

        if(strcmp(args[0],"exit") == 0)
        {
            break;
        }

        //For handling cd and cd..
        if(strcmp(args[0],"cd")==0)
        {
            if(args[1] == NULL)
            {
                chdir(getenv("HOME"));
            }
            else{
                chdir(args[1]);
            }
            continue;
        }
        

        pid_t pid = fork();

        if(pid == 0)
        {
            signal(SIGINT,SIG_DFL);
            execvp(args[0],args);
            printf("esh: command not found: %s\n",args[0]);
            exit(1);
        }

        else{
            waitpid(pid,NULL,0);
        }


    }


}

void remove_newline(char* str)
{
    int i = 0;
    while(str[i] != '\0')
    {
        if(str[i] == '\n' || str[i] == '\r')
        {
            str[i] = '\0';
            break;
        }
        i++;
    } 
    return;  
}



/*pipe(fd) creates:

    fd[1] ----→ [  TUBE  ] ----→ fd[0]
   (write end)              (read end)


   With a pipe, we rewire the connections:
        First child (ls): We want ls to print into the tube instead of the screen. dup2(fd[1], 1) says "file descriptor 1 (stdout) now points to the write end of the tube." So when ls prints, the output goes into the tube.
        ls → stdout → [was: screen] → [now: pipe write end]


        Second child (grep): We want grep to read from the tube instead of the keyboard. dup2(fd[0], 0) says "file descriptor 0 (stdin) now points to the read end of the tube." So when grep reads input, it reads from the tube.
        grep → stdin → [was: keyboard] → [now: pipe read end]

   The Full Picture


   ls (child 1)                        grep (child 2)
   prints "esh.c"                      reads input
      ↓                                   ↑
   stdout                              stdin
      ↓                                   ↑
   fd[1] ----→ [  TUBE  ] ----→ fd[0]
*/




void execute_pipe(char* left_cmd,char* right_cmd)
{
    char* left_args[64];
    int i = 0;
    char* token = strtok(left_cmd," ");
    while(token != NULL)
    {
        left_args[i++] = token;
        token = strtok(NULL," ");
    }
    left_args[i] = NULL;

    char* right_args[64];
    i = 0;
    token = strtok(right_cmd," ");
    while(token != NULL)
    {
        right_args[i++] = token;
        token = strtok(NULL," ");
    }
    right_args[i] = NULL;

    int fd[2];
    pipe(fd);

    //First Child: runs the left command
    pid_t pid1 = fork();
    if(pid1 == 0)
    {
        dup2(fd[1],1); //stdout goes to pipe
        close(fd[0]); //close read end, don't need it
        close(fd[1]); //close write end, dup2 already copied it
        execvp(left_args[0],left_args);
        printf("esh: command not found: %s\n",left_args[0]);
        exit(1);
    }

    //Second Child: runs the right command
    pid_t pid2 = fork();
    if(pid2 == 0)
    {
        dup2(fd[0],0);
        close(fd[1]);
        close(fd[0]);
        execvp(right_args[0],right_args);
        printf("esh: command not found: %s\n",right_args[0]);
        exit(1);
    }

    close(fd[0]);
    close(fd[1]);

    waitpid(pid1,NULL,0);
    waitpid(pid2,NULL,0);
}


/* Output Redirection: esh> ls > output.txt
    Instead of printing to the screen, ls should write to a file. Same concept as pipes we're rewiring stdout. But instead of pointing it to a pipe, we point it to a file.
    The logic is:

        Detect > in the input
        Split into the command and the filename
        Fork a child
        In the child: open the file, dup2 the file descriptor to stdout, then exec
*/



void executeGreater_Than(char* left_cmd,char* right_cmd)
{
    char* left_args[64];
    int i = 0;
    char* token = strtok(left_cmd," ");
    while(token != NULL)
    {
        left_args[i++] = token;
        token = strtok(NULL," ");
    }
    left_args[i] = NULL;

    char* right_args[64];
    i = 0;
    token = strtok(right_cmd," ");
    while(token != NULL)
    {
        right_args[i++] = token;
        token = strtok(NULL," ");
    }
    right_args[i] = NULL;

    pid_t pid = fork();

    if(pid == 0)
    {
        int fd = open(right_args[0],O_WRONLY | O_CREAT | O_TRUNC, 0644);
        dup2(fd, 1);  // stdout now goes to the file
        close(fd);
        execvp(left_args[0],left_args);
        printf("esh: command not found: %s\n",left_args[0]);
        exit(1);
    }
    else{
        waitpid(pid,NULL,0);
    }

}


void executeSmaller_Than(char* left_cmd,char* right_cmd)
{
    char* left_args[64];
    int i = 0;
    char* token = strtok(left_cmd," ");
    while(token != NULL)
    {
        left_args[i++] = token;
        token = strtok(NULL," ");
    }
    left_args[i] = NULL;

    char* right_args[64];
    i = 0;
    token = strtok(right_cmd," ");
    while(token != NULL)
    {
        right_args[i++] = token;
        token = strtok(NULL," ");
    }
    right_args[i] = NULL;

    pid_t pid = fork();

    if(pid == 0)
    {
        int fd = open(right_args[0],O_RDONLY,0644);
        dup2(fd, 0);  // stdin now goes to the file
        close(fd);
        execvp(left_args[0],left_args);
        printf("esh: command not found: %s\n",left_args[0]);
        exit(1);
    }
    else{
        waitpid(pid,NULL,0);
    }

}