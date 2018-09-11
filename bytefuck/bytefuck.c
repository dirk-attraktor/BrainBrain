#include <stdio.h>
#include <stdlib.h>

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <sys/time.h>
#include <strings.h>
#include <signal.h>
#include <errno.h>
#include <limits.h>
#include <time.h>
#include <pthread.h>
#include <sched.h>
#include <hiredis/hiredis.h>
#include <sys/resource.h>

#define DEBUG 0

#define MAX_MEMORY_SIZE       1*1000*1000
#define MAX_CODE_SIZE         1*1000*1000
#define MAX_INPUTBUFFER_SIZE  2*1000*1000
#define MAX_OUTPUTBUFFER_SIZE 2*1000*1000

#define MAX_THREADS 32  
#define DEFAULT_THREADS 8 



const char *unixsocketpath = "/var/run/redis/redis.sock";

void process( ){

    redisContext *redis_context;
    redisReply *reply;
    struct timeval timeout = { 1, 500000 }; // 1.5 seconds
    redis_context = redisConnectUnixWithTimeout(unixsocketpath, timeout);
    //c = redisConnectWithTimeout(hostname, port, timeout);
    if (redis_context == NULL || redis_context->err) {
        if (redis_context) {
            printf("Connection error: %s\n", redis_context->errstr);
            redisFree(redis_context);
        } else {
            printf("Connection error: can't allocate redis context\n");
        }
        exit(1);
    }   
    reply = redisCommand(redis_context,"SELECT 8");
    freeReplyObject(reply);

    char instance_id    [64]    = {0};
    char individual_id  [64]    = {0};
    char species_id     [64]    = {0};
    char population_id  [64]    = {0};
    
    // CODE
    char code                [MAX_CODE_SIZE] = {0}; // code loaded via redis
    int  code_loaded   = 0;  // code bytes loaded from redis    
    int  code_position = 0;  //  position in current code    
    unsigned long long code_steps_max  = 0; // limit max steps for run // Limits loaded via redis 
    unsigned long long code_steps_executed = 0; // Exection stats tracking
    
    // MEMORY
    char memory_char        [MAX_MEMORY_SIZE] = {0};
    int  memory_char_position = 0;  // current position in memory       
    int  memory_char_used = 0;  // max memory used   

    //int memory_int         [MAX_MEMORY_SIZE] = {0};
    //int memory_int_position = 0;  // current position in memory       
    //int memory_int_used = 0;  // max memory used   

    //float memory_float       [MAX_MEMORY_SIZE] = {0};
    //int   memory_float_position = 0;  // current position in memory       
    //int   memory_float_used = 0;  // max memory used   

    char memory_char_permanent         [MAX_MEMORY_SIZE] = {0};
    int  memory_char_permanent_loaded   = 0;  // memory size loaded from redis     
    int  memory_char_permanent_position = 0;  // current position in memory       
    int  memory_char_permanent_used     = 0;  // max memory used   

    int  memory_max = 0; //  // max memory. loaded via redis
    int  memory_char_permanent_max = 0; // max permanent memory. loaded via redis
    
    // INPUT
    char inputbuffer         [MAX_INPUTBUFFER_SIZE] = {0};
    int  inputbuffer_loaded   = 0;  // input bytes loaded from redis    
    int  inputbuffer_position = 0;  // current position in input data         
        
    // OUTPUT
    char outputbuffer[MAX_OUTPUTBUFFER_SIZE] = {0}; 
    int  outputbuffer_position = 0;  // current position in input data         

    // parenthesis tracking
    int parenthesis_counter = 0; // track [ ]
    int parenthesis_tmp_position = 0; // new jump position

    // Track execution time
    unsigned long long execution_time = 0;
    struct timeval  execution_starttime, execution_endtime;
    
    int jumpmap[MAX_CODE_SIZE] = {-1};
    unsigned char looplimitmap[MAX_CODE_SIZE] = {0};
  
    char nolog = 0; // dont log output stats to redis
    
    memset(jumpmap,     -1, sizeof(int) * MAX_CODE_SIZE );
    memset(looplimitmap, 0, sizeof(unsigned char) * MAX_CODE_SIZE );
    memset(memory_char,  0, sizeof(char) * MAX_MEMORY_SIZE );
  
    while(1){
        memset(jumpmap,     -1, sizeof(int) * code_loaded + 1);
        memset(looplimitmap, 0, sizeof(unsigned char) * code_loaded + 1);
        memset(memory_char,  0, sizeof(char) * memory_char_used + 1);

        
        // BLPOP instance_id 
        reply = redisCommand(redis_context,"BLPOP execute.queue 0");
        if (reply->type == REDIS_REPLY_ARRAY) { 
            if(reply->elements == 2){
                sprintf(instance_id ,"%s", reply->element[1]->str);
            }
        }
        freeReplyObject(reply);
            
        gettimeofday(&execution_starttime, NULL);
                      

        // GET nolog parameter
        reply = redisCommand(redis_context,"GET instance.%s.nolog", instance_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            nolog = 1;    
        }else{
            nolog = 0;
        }  
        freeReplyObject(reply);
                      
        // GET individual_id from instance_id
        reply = redisCommand(redis_context,"GET instance.%s.individual_id", instance_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            sprintf(individual_id ,"%s", reply->str);    
        }    
        freeReplyObject(reply);
        
        // GET inputbuffer and inputbuffer_loaded from instance_id
        reply = redisCommand(redis_context,"GET instance.%s.input", instance_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            inputbuffer_loaded = reply->len;
            if(inputbuffer_loaded > MAX_INPUTBUFFER_SIZE){ inputbuffer_loaded = MAX_INPUTBUFFER_SIZE; }
            memcpy( inputbuffer, reply->str, inputbuffer_loaded );
        }    
        freeReplyObject(reply);
       
        // GET code and code_loaded from individual
        reply = redisCommand(redis_context,"GET individual.%s.code_compiled", individual_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            code_loaded = reply->len;
            if(code_loaded > MAX_CODE_SIZE){ code_loaded = MAX_CODE_SIZE; }
            memcpy( code, reply->str, code_loaded );
        }    
        freeReplyObject(reply);
        
        // GET memory_char_permanent and memory_char_permanent_loaded from individual
        reply = redisCommand(redis_context,"GET individual.%s.memory", individual_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            memory_char_permanent_loaded = reply->len;
            if(memory_char_permanent_loaded > MAX_MEMORY_SIZE){ memory_char_permanent_loaded = MAX_MEMORY_SIZE; }
            memcpy( memory_char_permanent, reply->str, memory_char_permanent_loaded );
        }    
        freeReplyObject(reply);        
        
        // GET species_id from individual_id
        reply = redisCommand(redis_context,"GET individual.%s.species", individual_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            sprintf(species_id ,"%s", reply->str);    
        }    
        freeReplyObject(reply);
        
        // GET population_id from individual_id
        reply = redisCommand(redis_context,"GET individual.%s.population", individual_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            sprintf(population_id ,"%s", reply->str);    
        }    
        freeReplyObject(reply);        
        
        // GET code_steps_max from species
        reply = redisCommand(redis_context,"GET species.%s.max_steps", species_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            code_steps_max = strtoul(reply->str,NULL,10);
        }    
        freeReplyObject(reply);   

        // GET max_memory from species
        reply = redisCommand(redis_context,"GET species.%s.max_memory", species_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            memory_max = strtoul(reply->str,NULL,10);
            if(memory_max > MAX_MEMORY_SIZE){
                memory_max = MAX_MEMORY_SIZE;
            }
        }    
        freeReplyObject(reply);   

        // GET max_permanent_memory from species
        reply = redisCommand(redis_context,"GET species.%s.max_permanent_memory", species_id );
        if (reply->type == REDIS_REPLY_STRING) { 
            memory_char_permanent_max = strtoul(reply->str,NULL,10);
            if(memory_char_permanent_max > MAX_MEMORY_SIZE){
                memory_char_permanent_max = MAX_MEMORY_SIZE;
            }            
        }    
        freeReplyObject(reply);   
        

        if (DEBUG){
            printf("instance_id %s\n", instance_id);
            printf("individual_id %s\n", individual_id);
            printf("inputbuffer %s\n", inputbuffer);
            printf("code %s\n", code);
            printf("memory_char %s\n", memory_char);
            
            printf("memory_char_permanent_loaded %zu\n", memory_char_permanent_loaded);
            printf("code_loaded %zu\n", code_loaded);
            printf("memory_char_permanent_loaded %zu\n", memory_char_permanent_loaded);
            printf("code_steps_max %llu\n", code_steps_max);
       }  
        
        code_position = 0; // current position in progra
        code_steps_executed = 0;
        
        memory_char_used = 0;
        memory_char_position = 0;  // current position in memory       
        
        memory_char_permanent_used = 0;
        memory_char_permanent_position = 0;
         
        inputbuffer_position = 0;
        outputbuffer_position = 0;
        
        execution_time = 0;
        
        parenthesis_counter = 0; // track [ ]
        parenthesis_tmp_position = 0; // new jump position
        
        int i = 0;
        for(i=0;i<code_loaded;i++){
            if(code[i] == '[' && jumpmap[i] == -1){ 
                parenthesis_tmp_position = i;
                parenthesis_counter = 1;                        
                while (parenthesis_counter != 0 && parenthesis_tmp_position < code_loaded-1) {
                    parenthesis_tmp_position += 1;
                    if (code[parenthesis_tmp_position] == '[') parenthesis_counter += 1;
                    if (code[parenthesis_tmp_position] == ']') parenthesis_counter -= 1;
                }
                if(parenthesis_counter == 0){
                    jumpmap[i] = parenthesis_tmp_position;
                }else{
                    jumpmap[i] = i;
                }       
            }
            if(code[i] == ']' && jumpmap[i] == -1){                
                parenthesis_tmp_position = i;
                parenthesis_counter = 1;
                while (parenthesis_counter && parenthesis_tmp_position > 0) {
                    parenthesis_tmp_position -= 1;
                    if (code[parenthesis_tmp_position] == ']') parenthesis_counter += 1;
                    if (code[parenthesis_tmp_position] == '[') parenthesis_counter -= 1;
                }
                if(parenthesis_counter == 0){
                    jumpmap[i] = parenthesis_tmp_position; 
                }else{
                    jumpmap[i] = i;
                } 
            }
        }
        
        while (code_position < code_loaded && code_steps_executed < code_steps_max) {
            code_steps_executed += 1;
            if (DEBUG) fprintf(stderr, "Step %llu pos %llu \n", code_steps_executed, code_position);
            switch(code[code_position]) {
                case 'r' : // create random char in char memory
                    memory_char[memory_char_position] =  rand() % 256;
                    break;
                 
                case 'p': // char permanent memory 1 to left
                    if (memory_char_permanent_position != 0){
                        memory_char_permanent_position -= 1; 
                    }
                    break;
                 
                case 'P': // char permanent memory 1 to right
                    if (memory_char_permanent_position < memory_char_permanent_max -1){
                        memory_char_permanent_position += 1; 
                        if(memory_char_permanent_position > memory_char_permanent_used){
                            memory_char_permanent_used = memory_char_permanent_position+1;
                        }
                    }else{
                        memory_char_permanent_position = 0;
                    }
                    break;
                    
                case 'l': // load memory_char from memory_char_permanent
                    memory_char[memory_char_position] = memory_char_permanent[memory_char_permanent_position];
                    break;                    
                case 's': // save memory_char to memory_char_permanent
                    memory_char_permanent[memory_char_permanent_position] = memory_char[memory_char_position];
                    break;                    
                    
                case 'i':  // inputbuffer 1 to left
                    if(inputbuffer_position > 0){
                        inputbuffer_position -= 1;
                    }
                    break;                    
                    
                case '>':  
                    if (memory_char_position < memory_max-1){
                        memory_char_position += 1; 
                        if(memory_char_position > memory_char_used){
                            memory_char_used = memory_char_position+1;
                        }
                    }else{
                        memory_char_position = 0;
                    }
                    break;
                case '<': 
                    if (memory_char_position != 0){
                        memory_char_position -= 1; 
                    }
                    break;
                case '+': 
                    memory_char[memory_char_position] += 1; 
                    break;
                case '-': 
                    memory_char[memory_char_position] -= 1; 
                    break;
                case '.': 
                    if(outputbuffer_position < MAX_OUTPUTBUFFER_SIZE){
                        outputbuffer[outputbuffer_position] = memory_char[memory_char_position]; 
                        outputbuffer_position += 1;
                    }
                    break;
                case ',': 
                    if (inputbuffer_position >= inputbuffer_loaded){
                        memory_char[memory_char_position] = 0;
                    }else{
                        memory_char[memory_char_position] = inputbuffer[inputbuffer_position]; 
                        inputbuffer_position += 1;
                    }
                    break;
                case '[':
                    looplimitmap[code_position] += 1;
                    if (memory_char[memory_char_position] == 0 || looplimitmap[code_position] == 0) {
                        code_position = jumpmap[code_position];
                    }
                    break;
                case ']':
                    looplimitmap[code_position] += 1;
                    if (memory_char[memory_char_position] != 0 && looplimitmap[code_position] != 0) {
                        code_position = jumpmap[code_position];
                    }
                    break;
               default:
                    break;
            }
            code_position += 1;
            //if (DEBUG) fprintf(stderr, "%i steps executed!\n", code_steps_executed);
        }           

        gettimeofday(&execution_endtime, NULL);
        execution_time = (execution_endtime.tv_sec - execution_starttime.tv_sec) * 1000 * 1000; // seconds to microseconds
        execution_time += (execution_endtime.tv_usec - execution_starttime.tv_usec); 
        
        
        if(nolog != 1){
            unsigned long timekey = (unsigned long)time(NULL) ;
            timekey = timekey - (timekey%60);
        
            reply = redisCommand(redis_context,"INCR stats.executions.global.%lu", timekey );
            freeReplyObject(reply);  
            reply = redisCommand(redis_context,"EXPIRE stats.executions.global.%lu %u", timekey,3600*72 );
            freeReplyObject(reply);  
            
            reply = redisCommand(redis_context,"INCR stats.executions.species.%s.%lu", species_id, timekey);
            freeReplyObject(reply);  
            reply = redisCommand(redis_context,"EXPIRE stats.executions.species.%s.%lu %u", species_id, timekey, 3600*72);
            freeReplyObject(reply);    
     
            reply = redisCommand(redis_context,"INCR stats.executions.population.%s.%lu", population_id, timekey);
            freeReplyObject(reply);  
            reply = redisCommand(redis_context,"EXPIRE stats.executions.population.%s.%lu %u", population_id, timekey, 3600*72);
            freeReplyObject(reply);    
        }

        
        reply = redisCommand(redis_context,"SET instance.%s.output %b", instance_id, outputbuffer, (size_t) outputbuffer_position);
        freeReplyObject(reply);
        reply = redisCommand(redis_context,"SET instance.%s.memory %b", instance_id, memory_char_permanent, (size_t) memory_char_permanent_used);
        freeReplyObject(reply);
        reply = redisCommand(redis_context,"SET instance.%s.program_steps %u", instance_id, code_steps_executed);
        freeReplyObject(reply);
        reply = redisCommand(redis_context,"SET instance.%s.memory_usage %u", instance_id, memory_char_used);
        freeReplyObject(reply);
        reply = redisCommand(redis_context,"SET instance.%s.execution_time %u", instance_id, execution_time);
        freeReplyObject(reply);
        
        reply = redisCommand(redis_context,"RPUSH instance.%s.done 1", instance_id);
        freeReplyObject(reply);
        
        if(DEBUG){
            printf("instance_id %s\n", instance_id);
            printf("individual_id %s\n", individual_id);            
            printf("code_loaded %zu\n", code_loaded);
            printf("code_steps_max %u\n", code_steps_max);
            
            printf("%llu code_steps_executed\n", code_steps_executed);
            printf("%u memory_char_used\n", memory_char_used);
            printf("%u execution_time\n", execution_time);
        }
        
    }
}


int main(int argc, char *argv[])
{
    const rlim_t kStackSize = 100 * 1024 * 1024;   // min stack size = 100 MB
    struct rlimit rl;
    int result;

    pid_t pids[MAX_THREADS];
    int i;
    int numThreads = DEFAULT_THREADS;    


    if (argc == 2) {
        numThreads = atoi(argv[1]);
        if (numThreads < 0 || numThreads > MAX_THREADS) {
            fprintf(stderr,"ERROR: invalid numThreads=%d\n", numThreads);
            return 2;
        }
    }

    
    result = getrlimit(RLIMIT_STACK, &rl);
    if (result == 0){
        if (rl.rlim_cur < kStackSize){
            rl.rlim_cur = kStackSize;
            result = setrlimit(RLIMIT_STACK, &rl);
            if (result != 0){fprintf(stderr, "setrlimit returned result = %d\n", result);}
        }
    }


    /* Start children. */
    for (i = 0; i < numThreads; ++i) {
        if ((pids[i] = fork()) < 0) {
            perror("fork");
            abort();
        } else if (pids[i] == 0) {
            process();
            exit(0);
        }
    }

    /* Wait for children to exit. */
    int status;
    pid_t pid;
    while (numThreads > 0) {
        pid = wait(&status);
        printf("Child with PID %ld exited with status 0x%x.\n", (long)pid, status);
        --numThreads;  // TODO(pts): Remove pid from the pids array.
    }
    return 0;
}
