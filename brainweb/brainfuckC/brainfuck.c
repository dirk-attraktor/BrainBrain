#include <stdio.h>
#include <stdlib.h>

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <sys/time.h>

#define DEBUG 0

#define MAX_MEMORY_SIZE        50000
#define MAX_PROGRAM_LENGTH     50000
#define MAX_INPUT_BUFFER_SIZE  50000
#define MAX_OUTPUT_BUFFER_SIZE 50000


// jump lookup table
int jumpmap[MAX_PROGRAM_LENGTH] = {-1};


// Program storage
char program[MAX_PROGRAM_LENGTH] = {0};
unsigned long long program_length = 0;  // length of loaded program

char input_buffer[MAX_INPUT_BUFFER_SIZE] = {0}; 
unsigned long long input_buffer_available = 0; // input bytes available to bf
char output_buffer[MAX_OUTPUT_BUFFER_SIZE] = {0}; 

// Char Memory
char memory_char[MAX_MEMORY_SIZE] = {0};

// Execution options
unsigned long long max_memory_usage = 0; // limit mem usage for run
unsigned long long max_program_steps = 0; // limit max steps for run
char output_memory_after_finish = 0; // print memory content after run
  
// Execution tracking
unsigned long long memory_usage = 0;  // track memory usage during run
unsigned long long max_memory_usage_since_last_clear = 0;  // max track memory since last clear
unsigned long long program_steps = 0;  // track program steps usage during run
unsigned long long inputbuffer_usage = 0; // input bytes read by bf
unsigned long long output_buffer_used = 0; // output bytes created by bf

struct timeval  execution_starttime, execution_endtime;
unsigned long long execution_time = 0;

int read_bytes(int fd, char* target_buffer, int toread){
    ssize_t readcnt = 0;
    ssize_t ret = read(fd, target_buffer, toread);
    readcnt += ret;
    while (ret && readcnt != toread) {
        toread -= ret;
        readcnt += ret;
        target_buffer += ret;
        ret = read(fd, target_buffer, toread);
    }
    return readcnt;
}


void run_loaded_program(){
    memory_usage = 1;  
    program_steps = 0;
    output_buffer_used = 0;
    inputbuffer_usage = 0;
    
    int count = 0; // track [ ]
    int program_position = 0; // current position in program
    int new_program_position = 0; // current position in program
    int memory_position = 0;  // current position in memory

    gettimeofday(&execution_starttime, NULL);
    while (program_position < program_length && program_steps < max_program_steps) {
        program_steps += 1;
        if (DEBUG) fprintf(stderr, "Step %llu \n", program_steps);
        switch(program[program_position]) {
            case '>': 
                if (memory_position < max_memory_usage-1){
                    memory_position += 1; 
                    if(memory_position >= memory_usage){
                        memory_usage = memory_position+1;
                    }
                }else{
                    memory_position = 0;
                }
                break;
            case '<': 
                if (memory_position != 0){
                    memory_position -= 1; 
                }
                break;
            case '+': 
                memory_char[memory_position] += 1; 
                break;
            case '-': 
                memory_char[memory_position] -= 1; 
                break;
            case '.': 
                if(output_buffer_used < MAX_OUTPUT_BUFFER_SIZE){
                    output_buffer[output_buffer_used] = memory_char[memory_position]; 
                    output_buffer_used += 1;
                }
                break;
            case ',': 
                if (inputbuffer_usage >= input_buffer_available){
                    memory_char[memory_position] = 0;
                }else{
                    memory_char[memory_position] = input_buffer[inputbuffer_usage]; 
                    inputbuffer_usage += 1;
                }
                break;
            case '[':
                if (DEBUG) fprintf(stderr, "Found [ on %llu \n", program_position);
                if (!memory_char[memory_position]) {
                    if(jumpmap[program_position] == -1){ 
                        new_program_position = program_position;
                        count = 1;                        
                        while (count != 0 && new_program_position < program_length-1) {
                            new_program_position += 1;
                            if (program[new_program_position] == '[') count += 1;
                            if (program[new_program_position] == ']') count -= 1;
                        }
                        if(count == 0){
                            jumpmap[program_position] = new_program_position;
                            program_position = new_program_position;
                        }else{
                            jumpmap[program_position] = program_position;
                        }
                    }else{
                        program_position = jumpmap[program_position];
                    }
                }
                break;
            case ']':
                if (DEBUG) fprintf(stderr, "Found ] on %llu \n", program_position);
                if (memory_char[memory_position]) {
                    if(jumpmap[program_position] == -1){
                        new_program_position = program_position;
                        count = 1;
                        while (count && new_program_position >= 0) {
                            new_program_position -= 1;
                            if (program[new_program_position] == ']') count += 1;
                            if (program[new_program_position] == '[') count -= 1;
                        }
                        if(count == 0){
                            jumpmap[program_position] = new_program_position; 
                            program_position = new_program_position;
                        }else{
                            jumpmap[program_position] = program_position;
                        }
                    }else{
                        program_position = jumpmap[program_position];
                    }
                }
                break;
           default:
                break;
        }
        program_position += 1;
        //if (DEBUG) fprintf(stderr, "%i steps executed!\n", program_steps);
    }
    gettimeofday(&execution_endtime, NULL);
    
    execution_time = (execution_endtime.tv_sec - execution_starttime.tv_sec) * 1000 * 1000; // seconds to microseconds
    execution_time += (execution_endtime.tv_usec - execution_starttime.tv_usec); 
    
    if(memory_usage > max_memory_usage_since_last_clear){
        max_memory_usage_since_last_clear = memory_usage;
    }
    
    if (DEBUG) fprintf(stderr, "%llu steps executed!\n", program_steps);
    if (DEBUG) fprintf(stderr, "'%s' output generated!\n", output_buffer);
    if (DEBUG) fprintf(stderr, "'%llu' memory_usage!\n", memory_usage);
    if (DEBUG) fprintf(stderr, "'%llu' execution_time!\n", execution_time);
    
    fwrite("s", sizeof(char), 1, stdout);
    fwrite((const void*) & program_steps, sizeof(unsigned long long), 1, stdout); 
    
    fwrite("m", sizeof(char), 1, stdout);
    fwrite((const void*) & memory_usage, sizeof(unsigned long long), 1, stdout); 
    
    fwrite("i", sizeof(char), 1, stdout);
    fwrite((const void*) & inputbuffer_usage, sizeof(unsigned long long), 1, stdout); 
       
    fwrite("o", sizeof(char), 1, stdout);
    fwrite((const void*) & output_buffer_used, sizeof(unsigned long long), 1, stdout);
    fwrite((const void*) & output_buffer, output_buffer_used, 1, stdout);
    
    if(output_memory_after_finish != 0){
        fwrite("c", sizeof(char), 1, stdout);
        fwrite((const void*) & memory_usage, sizeof(unsigned long long), 1, stdout);
        fwrite((const void*) & memory_char, memory_usage, 1, stdout);
    }
    fwrite("x", sizeof(char), 1, stdout); // finished
    fwrite((const void*) & execution_time, sizeof(unsigned long long), 1, stdout);

    fflush(stdout);
    
    if (DEBUG) fprintf(stderr, "brainfuck.c exiting\n");
        
}


void process(int stdin_fd){
    ssize_t ret = 0;
    char parameter_buffer[64];
    
    memset(jumpmap, -1, sizeof jumpmap);
    memset(memory_char, 0, sizeof memory_char);
    
    
    while(1){
        ret = read_bytes(stdin_fd, parameter_buffer, 1);
        
        if(ret == 0){ return; }
        
        switch(parameter_buffer[0]) {
            
            case 'x': 
                fwrite("x", sizeof(char), 1, stdout); // finished
                fwrite((const void*) &  execution_time, sizeof(unsigned long long), 1, stdout);
                fflush(stdout);
                break;
                
            case 's': // max steps
                ret = read_bytes(stdin_fd, parameter_buffer, 8);
                if(ret != 8){ return; }
                max_program_steps = *((unsigned long long*) parameter_buffer);
                if (DEBUG) fprintf(stderr, "max_program_steps %llu loaded\n", max_program_steps);
                break;
                
            case 'm': // max memory
                ret = read_bytes(stdin_fd, parameter_buffer, 8);
                if(ret != 8){ return; }
                max_memory_usage = *((unsigned long long*) parameter_buffer);
                if (DEBUG) fprintf(stderr, "max_memory_usage %llu loaded\n", max_memory_usage);
                break;
                
            case 'l': // clear memory
                memset(memory_char, 0, max_memory_usage_since_last_clear * sizeof(*memory_char)); // clear only memory used by last program run
                if (DEBUG) fprintf(stderr, "clearing %llu memory bytes\n", max_memory_usage_since_last_clear);
                max_memory_usage_since_last_clear = 0;
                break;
                
            case 'o': // output memory
                ret = read_bytes(stdin_fd, parameter_buffer, 1);
                if(ret != 1){ return; }            
                output_memory_after_finish = *((char*) (parameter_buffer));
                if (DEBUG) fprintf(stderr, "output_memory_after_finish %llu loaded\n", output_memory_after_finish);
                break;
                
            case 'c':  // code
                memset(jumpmap, -1,  program_length * sizeof(*jumpmap)); // clear jumpmap for next program, clear only what was used by last program run
                ret = read_bytes(stdin_fd, parameter_buffer, 8);
                if(ret != 8){ return; }
                program_length = *((unsigned long long*) parameter_buffer);
                ret = read_bytes(stdin_fd, program, program_length);
                if(ret != program_length){ return; }
                if (DEBUG) fprintf(stderr, "program_length %llu loaded\n", program_length);
                break;
                
            case 'p': // preload memory
                ret = read_bytes(stdin_fd, parameter_buffer, 8);
                if(ret != 8){ return; }
                unsigned long long memorysize = *((unsigned long long*) parameter_buffer);
                ret = read_bytes(stdin_fd, memory_char, memorysize);
                if(ret != memorysize){ return; }
                if (DEBUG) fprintf(stderr, "preload memorysize %llu loaded\n", memorysize);
                break;                
                
            case 'e': // execute loaded program with optional input
                ret = read_bytes(stdin_fd, parameter_buffer, 8);
                if(ret != 8){ return; }
                input_buffer_available = *((unsigned long long*) parameter_buffer);
                if(input_buffer_available > 0){
                    ret = read_bytes(stdin_fd, input_buffer, input_buffer_available);
                    if(ret != input_buffer_available){ return; }
                }
                if (DEBUG) fprintf(stderr, "execute with input of  length %llu\n", input_buffer_available);                
                run_loaded_program();
                break;
                                
            default:
                break;
        }
    }
}


int main(int argc, char *argv[])
{
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
    process( fd);
    return 0;
}
