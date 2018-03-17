#include <stdio.h>
#include <stdlib.h>

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>

static const int DEBUG = 0;

//def evaluate1(code, parameter_buffer=None, init_memory=None,max_steps=None, output_memory=False):

    // from STDIN OR File READ:
    //  8 byte integer : Program code size in bytes
    //  8 byte memory size
    //  8 byte integer max_steps
    //  1 byte  do output_memory boolean
    //  x bytes program code
    //  x bytes input
    // 

int main(int argc, char *argv[])
{

    unsigned long long codesize = 0;
    unsigned long long inputsize = 0;
    unsigned long long memorysize = 0;
    unsigned long long maxsteps = 0;
    char do_output_memory = 0;
  
    
    int fd = 0;
    if (argc < 2) {
        fd = STDIN_FILENO;
    } else {
        fd = open(argv[1], O_RDONLY);

        if(fd < 0){
            fprintf(stderr, "Error opening %s!\n", argv[1]);
            perror("open");
            exit(1);
        }
    }   

    char memory[500];

    char* jumpmap[50000];
    
    char program[50000];
    ssize_t program_toread  = 0;
    ssize_t program_readcnt = 0;
    char *program_ptr;

    ssize_t parameter_buffer_toread  = 0;
    ssize_t parameter_buffer_readcnt = 0;
    char *parameter_buffer_ptr;
    char parameter_buffer[33];    
    
    ssize_t input_buffer_toread  = 0;
    ssize_t input_buffer_readcnt = 0;
    char *input_buffer_ptr;
    char input_buffer[500000];     
    
    char output_buffer[500000];     
    
    
    ssize_t ret = 0; // read return value
    
    while(1){
        memset(memory, 0, sizeof memory);   
        memset(jumpmap, 0, sizeof jumpmap);   
        memset(input_buffer, 0, sizeof input_buffer);   
        
        parameter_buffer_toread = sizeof(parameter_buffer);
        parameter_buffer_readcnt = 0;
        parameter_buffer_ptr = parameter_buffer;
        
        ret = read(fd, parameter_buffer_ptr, parameter_buffer_toread);
        if(ret == 0){
            exit(0);
        }
        while (ret && (parameter_buffer_readcnt < sizeof(parameter_buffer))) {
            parameter_buffer_toread -= ret;
            parameter_buffer_readcnt += ret;
            parameter_buffer_ptr += ret;
            ret = read(fd, parameter_buffer_ptr, parameter_buffer_toread);
        }
        codesize = *((unsigned long long*) parameter_buffer);
        inputsize = *((unsigned long long*) (parameter_buffer+8));
        memorysize = *((unsigned long long*) (parameter_buffer+16));
        maxsteps = *((unsigned long long*) (parameter_buffer+24));
        do_output_memory = *((char*) (parameter_buffer+32));
        if (DEBUG) fprintf(stderr, "codesize %llu!\n",codesize);
        if (DEBUG) fprintf(stderr, "inputsize %llu!\n",inputsize);
        if (DEBUG) fprintf(stderr, "memorysize %llu!\n",memorysize);
        if (DEBUG) fprintf(stderr, "maxsteps %llu!\n",maxsteps);
        if (DEBUG) fprintf(stderr, "do_output_memory %llu!\n",do_output_memory);
        
        // Read Program
        program_toread = codesize;
        program_readcnt = 0;
        program_ptr = program;        
        ret = read(fd, program_ptr, program_toread);
        if(ret == 0){
            exit(0);
        } 
        while (ret && (program_readcnt < sizeof(program))) {
            program_toread -= ret;
            program_readcnt += ret;
            program_ptr += ret;
            ret = read(fd, program_ptr, program_toread);
        }
        //fprintf(stderr, "program read %s!\n",program);

        // Read Input   
        
        input_buffer_toread = inputsize;
        input_buffer_readcnt = 0;
        input_buffer_ptr = input_buffer;     
        if(input_buffer_toread > 0 ){
            //fprintf(stderr, "input_buffer_toread > 0\n");

            ret = read(fd, input_buffer_ptr, input_buffer_toread);
            if(ret == 0){
                exit(0);
            } 
            while (ret && (input_buffer_readcnt < sizeof(input_buffer))) {
                input_buffer_toread -= ret;
                input_buffer_readcnt += ret;
                input_buffer_ptr += ret;
                ret = read(fd, input_buffer_ptr, input_buffer_toread);
            }        
        }
        
        
        char *ip = program,
        char *ptr = memory+(sizeof memory / 2),
        int count = 0;
        int position = 0;
        unsigned long long steps = 0;
        int input_buffer_position = 0;
        int output_buffer_position = 0;

        char* s = program + program_readcnt;
        while (ip < s && steps < maxsteps) {
            //fprintf(stderr, "'%i' \n",ip);
            if (DEBUG) fprintf(stderr, "c: '%c' \n",*ip);
            if (DEBUG) fprintf(stderr, "step: '%i' \n",steps);
            steps += 1;
            switch(*ip) {
                case '>': 
                    if ((ptr - memory) < sizeof memory){
                        ++ptr; 
                    }else{
                        ptr = memory;
                        //fprintf(stderr,"positive end of memory \n");
                    }
                    break;
                case '<': 
                    if ((ptr - memory) > 0){
                        --ptr; 
                    }else{
                        ptr = memory + sizeof memory - 1; 
                        //fprintf(stderr,"negative end of memory \n");
                    } 
                    break;
                case '+': ++(*ptr); break;
                case '-': --(*ptr); break;
                case '.': output_buffer[output_buffer_position] = *ptr; 
                          ++output_buffer_position;
                          //fflush(stdout); 
                          break;
                case ',': 
                    if (input_buffer_position >= input_buffer_readcnt){
                        //input_buffer_position = 0;
                    }else{
                        *ptr = input_buffer[input_buffer_position]; 
                        ++input_buffer_position;
                    }
                    
                    break;
                case '[':
                    //fprintf(stderr,"jmp2");
                    if (!*ptr) {
                        position = ip - program;
                        if(jumpmap[position] == 0){ 
                            count = 1;
                            while (count && ip < s) {
                                ++ip;
                                if (*ip == '[') ++count;
                                if (*ip == ']') --count;
                            }
                            //fprintf(stderr,"jmp1");
                            if(ip >= s){
                                //fprintf(stderr,"jmp");
                                jumpmap[position] = position + program;
                            }else{
                                jumpmap[position] = ip;    
                            }
                            
                        }else{
                            ip = jumpmap[position];
                        }
                    }
                    break;
                case ']':
                    if (*ptr) {
                        position = ip - program;
                        if(jumpmap[position] == 0){
                            count = 1;
                            while (count && ip >= program) {
                                --ip;
                                if (*ip == ']') ++count;
                                if (*ip == '[') --count;
                            }
                            jumpmap[position] = ip;
                        }else{
                            ip = jumpmap[position];
                        }
                    }
                    break;
               default:
                    break;
            }
            ++ip;
            if (DEBUG) fprintf(stderr, "%i steps executed!\n", steps);
        }
        if (DEBUG) fprintf(stderr, "%i steps executed!\n", steps);
        //if (DEBUG) fprintf(stderr, "'%s' output generated!\n", output_buffer);
        if (DEBUG) fprintf(stdout, "cccccc\n");
        
        fwrite((const void*) & steps,sizeof(unsigned long long),1,stdout); 
        fwrite((const void*) & output_buffer_position,sizeof(int),1,stdout);
        fwrite((const void*) & output_buffer,output_buffer_position,1,stdout);
        fflush(stdout);
    }
    fprintf(stderr, "brainfuck.c exiting");
    return 0;
}
