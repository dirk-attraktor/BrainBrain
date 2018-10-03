

import redis
import random
import re
import sys
import bson

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)
   
class ByteFuckHelpers():
        
        '''
            Memory                          |       Action      |   ,   |   .   |   <   |   >   |   +   |   -   |   [   |   ]   |
                                            |
        memory_char                         |       read        |           x                       x       x
        memory_char                         |       write       |   x                               x       x
        memory_char_position                |       read        |   x       x       x       x       x       x
        memory_char_position                |       write       |                   x       x
        
        memory_char_permanent               |       read        |
        memory_char_permanent               |       write       |
        memory_char_permanent_position      |       read        |
        memory_char_permanent_position      |       write       |
        
        inputbuffer                         |       read        |   x
        inputbuffer                         |       write       |
        inputbuffer_position                |       read        |   x
        inputbuffer_position                |       write       |   x
        
        outputbuffer                        |       read        |
        outputbuffer                        |       write       |           x
        outputbuffer_position               |       read        |           x
        outputbuffer_position               |       write       |           x
        
        storage_cell                        |       read        |
        storage_cell                        |       write       |
        
        
        bytefuck change groups
         input memory  (im) 0
         output memory (om) 1
         perm memory (pm)   2
         char memory (cm)   3
         
        ,  1001 (im, cm) # read input memory to char memory, move 1 memory position right
        .  1010 (cm, om) # write char memory to output memory
        <  1000 (cm) # move left in char memory
        >  1000 (cm) # move right in char memory
        +  1000 (cm) # char memory +1
        -  1000 (cm) # char memory -1
        [  1111 (*) # loop char
        ]  1111 (*) # loop char end
        p  0100 (pm) # move left in perm memory
        P  0100 (pm) # move right in perm memory
        s  1100 (cm, pm) # save char memory to perm memory
        l  1100 (cm, pm) # local perm memory to char memory
        r  1000 (cm) # random char to char memory
        i  0001 (im) # move left in input memory
        0  set cell to 0
        1  set cell to 64
        2  set cell to 256
        
        M Marks the current cell as the cell to use as the 'storage' cell defined in extended type I.
        m // Resets the storage cell to the initial storage cell.

        '$': // Overwrites the byte in storage with the byte at the pointer.
        '!': // Overwrites the byte at the pointer with the byte in storage.
        '~': // Performs a bitwise NOT operation on the byte at the pointer (all 1's and 0's are swapped).
        '^': // Performs a bitwise XOR operation on the byte at the pointer and the byte in storage, storing its result in the byte at the pointer.
        '&': // Performs a bitwise AND operation on the byte at the pointer and the byte in storage, storing its result in the byte at the pointer.
        '|': // Performs a bitwise OR operation on the byte at the pointer and the byte in storage, storing its result in the byte at the pointer.
        '*': // Multiplies the byte at the pointer with the byte in storage, storing its result in the byte at the pointer.
        '/': // Divides the byte at the pointer with the byte in storage, storing its result in the byte at the pointer.
        '=': // Adds the byte at the pointer with the byte in storage, storing its result in the byte at the pointer.
        '_': // Subtracts the byte at the pointer with the byte in storage, storing its result in the byte at the pointer.
        '%': // Preforms a Modulo operation on the byte at the pointer and the byte in storage, storing its result in the byte at the pointer.
        ':': // Moves the pointer forward or back by the signed number at the current cell. So a cell value of 5, moves the pointer ahead 5 places, where as 251 (signed -5) would move the pointer back 5 places. This is useful for simple variable determining pointer movement.
         'o':  // outputbuffer 1 to left
        'N' // No OP
        '''
        def __init__(self):
            self.bytefuckchars = b",.<>+-[]pPslri0123456789"
            self.bytefuckchars_re = re.compile(b'[^\,\.\<\>\+\-\[\]pPslri]')
            
            self.bytefuckchars = b",.<>+-[]pPslri012MmNxyXY$!~^&|*/=_%:o"
            self.bytefuckchars_re = re.compile(b'[^\,\.\<\>\+\-\[\]pPslri012MmoNxyXY\$\!\~\^\&\|\*\/\=\_\%\:]')
            
            self.toremoves = [
                [  
                    re.compile(b"|".join([
                            b'pP'  , # left/right in perm memory
                            b'Pp'  , # right/left in perm memory
                            b'\+\-', # +1 -1  in char memory
                            b'\-\+', # -1 +1  in char memory
                            b'\<\>', # left/right in char memory
                            b'\>\<', # right/left in char memory
                            b'\[\]', # empty loop
                    ])) , b''
                ],[  
                    re.compile(b"|".join([
                        b',i,' , # double input buffer read
                        b'\+,' , # add then overwrite with input read 
                        b'\-,' , # sub then overwrite with input read
                        b'r,'  , # random then overwrite with input read
                        b'l,'  , # load then overwrite with input read
                    ])) , b','
                ],[  
                    re.compile(b"|".join([
                        b'ls'  , # double load
                        b'rl'  , # load then save again
                        b'll'  , # random then overwrite with load
                        b'\+l' , # add then overwrite with load    
                        b'\-l' , # sub then overwrite with load
                    ])) , b'l'
                ],[  
                    re.compile(b"|".join([
                        b'rr'  , # double random char
                        b'lr'  , # load then overwrite with random
                        b'\+r' , # add then overwrite with random
                        b'\-r' , # sub then overwrite with random
                    ])) , b'r'
                ],[  
                    re.compile(b"|".join([
                        b'ss' , # double save
                        b'sl' , # save then load again
                    ])) , b's'
                ]
            ]
            
        def get_random_byte(self):
            return random.choice(self.bytefuckchars)
            
        def clean_bytefuck(self, binary):
            bytefuck = re.sub(self.bytefuckchars_re, b'', binary)
            olength = len(bytefuck)
            matched = True
            while matched == True:
                matched = False
                for toremove in self.toremoves:
                    bytefuck = re.sub(toremove[0], toremove[1], bytefuck)
                    newlength = len(bytefuck)
                    if newlength != olength:
                        matched = True
                    olength = newlength
                    
            return bytefuck

# for debug/dev stuff and know bf testcases
class Bytefuck():
    
    def execute(self, code, inputbytes):
        instance_id = random.randint(0,100*1000*1000*1000)
        
        individual_id = self._create_individual(code)
        redisconnection.set("individual.%s.memory" % individual_id, inputbytes)

        redisconnection.set("instance.%s.individual_id" % instance_id, individual_id)
        redisconnection.set("instance.%s.nolog" % instance_id,"1")
        redisconnection.set("instance.%s.input" % instance_id, inputbytes)
        
        redisconnection.rpush("execute.queue", instance_id)
        # ASYNC EXECUTIONS HAPPENS HERE .. 
        done = redisconnection.blpop("instance.%s.done" %  instance_id)
        
        output = redisconnection.get("instance.%s.output" % instance_id)
        memory = redisconnection.get("instance.%s.memory" % instance_id)
        program_steps = redisconnection.get("instance.%s.program_steps" % instance_id)
        memory_usage = redisconnection.get("instance.%s.memory_usage" % instance_id)
        execution_time = redisconnection.get("instance.%s.execution_time" % instance_id)

        redisconnection.delete("instance.%s.nolog" % instance_id)
        redisconnection.delete("instance.%s.individual_id" % instance_id)
        redisconnection.delete("instance.%s.input" % instance_id)
        redisconnection.delete("instance.%s.done" % instance_id)
        redisconnection.delete("instance.%s.output" % instance_id)
        redisconnection.delete("instance.%s.memory" % instance_id)
        redisconnection.delete("instance.%s.program_steps" % instance_id)
        redisconnection.delete("instance.%s.memory_usage" % instance_id)
        redisconnection.delete("instance.%s.execution_time" % instance_id)
        
        self._delete_individual(individual_id)
        return output        
        
    def _create_individual(self, code):
        individual_id = random.randint(0,100*1000*1000*1000)
        redisconnection.set("individual.%s.code_compiled" % individual_id, code)
        redisconnection.set("individual.%s.memory" % individual_id, "")
        redisconnection.set("individual.%s.species" % individual_id, individual_id)  # random, ignore
        redisconnection.set("individual.%s.population" % individual_id, individual_id)# random, ignore
        redisconnection.set("species.%s.max_steps" % individual_id, 1000*1000*1000)
        redisconnection.set("species.%s.max_memory" % individual_id, "500000")
        redisconnection.set("species.%s.max_permanent_memory" % individual_id, "50000")
        redisconnection.set("species.%s.max_permanent_memory" % individual_id, "50000")
        return individual_id
        
    def _delete_individual(self, individual_id):
        redisconnection.delete("individual.%s.code_compiled" % individual_id)
        redisconnection.delete("individual.%s.memory" % individual_id)
        redisconnection.delete("individual.%s.species" % individual_id)
        redisconnection.delete("individual.%s.population" % individual_id)
        redisconnection.delete("individual.%s.max_memory" % individual_id)
        redisconnection.delete("individual.%s.max_permanent_memory" % individual_id)



helloworld1 = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."
helloworld2 = ">++++++++[-<+++++++++>]<.>>+>-[+]++>++>+++[>[->+++<<+++>]<<]>-----.>->+++..+++.>-.<<+[>[+>+]>>]<--------------.>>.+++.------.--------.>+.>+."
helloworld3 = "+[>>>->-[>->----<<<]>>]>.---.>+..+++.>>.<.>>---.<<<.+++.------.<-.>>+."   
helloworld4 = ",<[]<-]>]+[-]>,<,,>,][+>,]+>,+>[+<.[-]]<]>>,[>]>,,,,,,>+<[+>,]+>,+>[++.[-<-]]<]],,[>]>,,,,<<,,,>,,,,]>,,],[.,][,],<[>,->->]>,<,,,],,,,<,]>,],[<,][,],,>]>,<,[>[>],,,>>>>,,,[<,]<,+]>]]>,][>,[.,][,],,],,,"

mandelbrot = '''+++++++++++++[->++>>>+++++>++>+<<<<<<]>>>>>++++++>--->>>>>>>>>>+++++++++++++++[[
>>>>>>>>>]+[<<<<<<<<<]>>>>>>>>>-]+[>>>>>>>>[-]>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>[-]+
<<<<<<<+++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>>>>+>>>>>>>>>>>>>>>>>>>>>>>>>>
>+<<<<<<<<<<<<<<<<<[<<<<<<<<<]>>>[-]+[>>>>>>[>>>>>>>[-]>>]<<<<<<<<<[<<<<<<<<<]>>
>>>>>[-]+<<<<<<++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>>>+<<<<<<+++++++[-[->>>
>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>>>+<<<<<<<<<<<<<<<<[<<<<<<<<<]>>>[[-]>>>>>>[>>>>>
>>[-<<<<<<+>>>>>>]<<<<<<[->>>>>>+<<+<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>
[>>>>>>>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+<<+<<<+<<]>>>>>>>>]<<<<<<<<<[<<<<<<<
<<]>>>>>>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+<<+<<<<<]>>>>>>>>>+++++++++++++++[[
>>>>>>>>>]+>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+[
>+>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>[-<<<<+>>>>]<<<<[->>>>+<<<<<[->>[
-<<+>>]<<[->>+>>+<<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>>>>]<<<<<<<
<<[>[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<]>[->>>>>>>>>+<<<<<<<<<]<+>>>>>>>>]<<<<<<<<<
[>[-]<->>>>[-<<<<+>[<->-<<<<<<+>>>>>>]<[->+<]>>>>]<<<[->>>+<<<]<+<<<<<<<<<]>>>>>
>>>>[>+>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>>[-<<<<<+>>>>>]<<<<<[->>>>>+
<<<<<<[->>>[-<<<+>>>]<<<[->>>+>+<<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>
>>>>>>>]<<<<<<<<<[>>[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<<]>>[->>>>>>>>>+<<<<<<<<<]<<
+>>>>>>>>]<<<<<<<<<[>[-]<->>>>[-<<<<+>[<->-<<<<<<+>>>>>>]<[->+<]>>>>]<<<[->>>+<<
<]<+<<<<<<<<<]>>>>>>>>>[>>>>[-<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<+>>>>>>>>>>>>>
>>>>>>>>>>>>>>>>>>>>>>>]>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>+++++++++++++++[[>>>>
>>>>>]<<<<<<<<<-<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+>>>>>>>>>>>>>>>>>>>>>+<<<[<<<<<<
<<<]>>>>>>>>>[>>>[-<<<->>>]+<<<[->>>->[-<<<<+>>>>]<<<<[->>>>+<<<<<<<<<<<<<[<<<<<
<<<<]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>>>[-<<<<->>>>]+<<<<[->>>>-<[-<<<+>>>]<<<[->
>>+<<<<<<<<<<<<[<<<<<<<<<]>>>[-]+>>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>>>>>>>>]<<<<<<
<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]<<<<<<<[->+>>>-<<<<]>>>>>>>>>+++++++++++++++++++
+++++++>>[-<<<<+>>>>]<<<<[->>>>+<<[-]<<]>>[<<<<<<<+<[-<+>>>>+<<[-]]>[-<<[->+>>>-
<<<<]>>>]>>>>>>>>>>>>>[>>[-]>[-]>[-]>>>>>]<<<<<<<<<[<<<<<<<<<]>>>[-]>>>>>>[>>>>>
[-<<<<+>>>>]<<<<[->>>>+<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>[-<<<<<<<<
<+>>>>>>>>>]>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>+++++++++++++++[[>>>>>>>>>]+>[-
]>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+[>+>>>>>>>>]<<<
<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>>[-<<<<<+>>>>>]<<<<<[->>>>>+<<<<<<[->>[-<<+>>]<
<[->>+>+<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>>>>]<<<<<<<<<[>[->>>>
>>>>>+<<<<<<<<<]<<<<<<<<<<]>[->>>>>>>>>+<<<<<<<<<]<+>>>>>>>>]<<<<<<<<<[>[-]<->>>
[-<<<+>[<->-<<<<<<<+>>>>>>>]<[->+<]>>>]<<[->>+<<]<+<<<<<<<<<]>>>>>>>>>[>>>>>>[-<
<<<<+>>>>>]<<<<<[->>>>>+<<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>+>>>>>>>>
]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>>[-<<<<<+>>>>>]<<<<<[->>>>>+<<<<<<[->>[-<<+
>>]<<[->>+>>+<<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>>>>]<<<<<<<<<[>
[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<]>[->>>>>>>>>+<<<<<<<<<]<+>>>>>>>>]<<<<<<<<<[>[-
]<->>>>[-<<<<+>[<->-<<<<<<+>>>>>>]<[->+<]>>>>]<<<[->>>+<<<]<+<<<<<<<<<]>>>>>>>>>
[>>>>[-<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<+>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
]>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>[-<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<+>
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>]>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>++++++++
+++++++[[>>>>>>>>>]<<<<<<<<<-<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+[>>>>>>>>[-<<<<<<<+
>>>>>>>]<<<<<<<[->>>>>>>+<<<<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>>>>[
-]>>>]<<<<<<<<<[<<<<<<<<<]>>>>+>[-<-<<<<+>>>>>]>[-<<<<<<[->>>>>+<++<<<<]>>>>>[-<
<<<<+>>>>>]<->+>]<[->+<]<<<<<[->>>>>+<<<<<]>>>>>>[-]<<<<<<+>>>>[-<<<<->>>>]+<<<<
[->>>>->>>>>[>>[-<<->>]+<<[->>->[-<<<+>>>]<<<[->>>+<<<<<<<<<<<<[<<<<<<<<<]>>>[-]
+>>>>>>[>>>>>>>>>]>+<]]+>>>[-<<<->>>]+<<<[->>>-<[-<<+>>]<<[->>+<<<<<<<<<<<[<<<<<
<<<<]>>>>[-]+>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>>>>>>>>]<<<<<<<<]>>>>>>>>]<<<<<<<<<
[<<<<<<<<<]>>>>[-<<<<+>>>>]<<<<[->>>>+>>>>>[>+>>[-<<->>]<<[->>+<<]>>>>>>>>]<<<<<
<<<+<[>[->>>>>+<<<<[->>>>-<<<<<<<<<<<<<<+>>>>>>>>>>>[->>>+<<<]<]>[->>>-<<<<<<<<<
<<<<<+>>>>>>>>>>>]<<]>[->>>>+<<<[->>>-<<<<<<<<<<<<<<+>>>>>>>>>>>]<]>[->>>+<<<]<<
<<<<<<<<<<]>>>>[-]<<<<]>>>[-<<<+>>>]<<<[->>>+>>>>>>[>+>[-<->]<[->+<]>>>>>>>>]<<<
<<<<<+<[>[->>>>>+<<<[->>>-<<<<<<<<<<<<<<+>>>>>>>>>>[->>>>+<<<<]>]<[->>>>-<<<<<<<
<<<<<<<+>>>>>>>>>>]<]>>[->>>+<<<<[->>>>-<<<<<<<<<<<<<<+>>>>>>>>>>]>]<[->>>>+<<<<
]<<<<<<<<<<<]>>>>>>+<<<<<<]]>>>>[-<<<<+>>>>]<<<<[->>>>+>>>>>[>>>>>>>>>]<<<<<<<<<
[>[->>>>>+<<<<[->>>>-<<<<<<<<<<<<<<+>>>>>>>>>>>[->>>+<<<]<]>[->>>-<<<<<<<<<<<<<<
+>>>>>>>>>>>]<<]>[->>>>+<<<[->>>-<<<<<<<<<<<<<<+>>>>>>>>>>>]<]>[->>>+<<<]<<<<<<<
<<<<<]]>[-]>>[-]>[-]>>>>>[>>[-]>[-]>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>>>[-<
<<<+>>>>]<<<<[->>>>+<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>+++++++++++++++[
[>>>>>>>>>]+>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+
[>+>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>[-<<<<+>>>>]<<<<[->>>>+<<<<<[->>
[-<<+>>]<<[->>+>+<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>>>>]<<<<<<<<
<[>[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<]>[->>>>>>>>>+<<<<<<<<<]<+>>>>>>>>]<<<<<<<<<[
>[-]<->>>[-<<<+>[<->-<<<<<<<+>>>>>>>]<[->+<]>>>]<<[->>+<<]<+<<<<<<<<<]>>>>>>>>>[
>>>[-<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<+>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>]>
>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>[-]>>>>+++++++++++++++[[>>>>>>>>>]<<<<<<<<<-<<<<<
<<<<[<<<<<<<<<]>>>>>>>>>-]+[>>>[-<<<->>>]+<<<[->>>->[-<<<<+>>>>]<<<<[->>>>+<<<<<
<<<<<<<<[<<<<<<<<<]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>>>[-<<<<->>>>]+<<<<[->>>>-<[-
<<<+>>>]<<<[->>>+<<<<<<<<<<<<[<<<<<<<<<]>>>[-]+>>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>
>>>>>>>]<<<<<<<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>[-<<<+>>>]<<<[->>>+>>>>>>[>+>>>
[-<<<->>>]<<<[->>>+<<<]>>>>>>>>]<<<<<<<<+<[>[->+>[-<-<<<<<<<<<<+>>>>>>>>>>>>[-<<
+>>]<]>[-<<-<<<<<<<<<<+>>>>>>>>>>>>]<<<]>>[-<+>>[-<<-<<<<<<<<<<+>>>>>>>>>>>>]<]>
[-<<+>>]<<<<<<<<<<<<<]]>>>>[-<<<<+>>>>]<<<<[->>>>+>>>>>[>+>>[-<<->>]<<[->>+<<]>>
>>>>>>]<<<<<<<<+<[>[->+>>[-<<-<<<<<<<<<<+>>>>>>>>>>>[-<+>]>]<[-<-<<<<<<<<<<+>>>>
>>>>>>>]<<]>>>[-<<+>[-<-<<<<<<<<<<+>>>>>>>>>>>]>]<[-<+>]<<<<<<<<<<<<]>>>>>+<<<<<
]>>>>>>>>>[>>>[-]>[-]>[-]>>>>]<<<<<<<<<[<<<<<<<<<]>>>[-]>[-]>>>>>[>>>>>>>[-<<<<<
<+>>>>>>]<<<<<<[->>>>>>+<<<<+<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>+>[-<-<<<<+>>>>
>]>>[-<<<<<<<[->>>>>+<++<<<<]>>>>>[-<<<<<+>>>>>]<->+>>]<<[->>+<<]<<<<<[->>>>>+<<
<<<]+>>>>[-<<<<->>>>]+<<<<[->>>>->>>>>[>>>[-<<<->>>]+<<<[->>>-<[-<<+>>]<<[->>+<<
<<<<<<<<<[<<<<<<<<<]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>[-<<->>]+<<[->>->[-<<<+>>>]<
<<[->>>+<<<<<<<<<<<<[<<<<<<<<<]>>>[-]+>>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>>>>>>>>]<
<<<<<<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>[-<<<+>>>]<<<[->>>+>>>>>>[>+>[-<->]<[->+
<]>>>>>>>>]<<<<<<<<+<[>[->>>>+<<[->>-<<<<<<<<<<<<<+>>>>>>>>>>[->>>+<<<]>]<[->>>-
<<<<<<<<<<<<<+>>>>>>>>>>]<]>>[->>+<<<[->>>-<<<<<<<<<<<<<+>>>>>>>>>>]>]<[->>>+<<<
]<<<<<<<<<<<]>>>>>[-]>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+<<+<<<<<]]>>>>[-<<<<+>
>>>]<<<<[->>>>+>>>>>[>+>>[-<<->>]<<[->>+<<]>>>>>>>>]<<<<<<<<+<[>[->>>>+<<<[->>>-
<<<<<<<<<<<<<+>>>>>>>>>>>[->>+<<]<]>[->>-<<<<<<<<<<<<<+>>>>>>>>>>>]<<]>[->>>+<<[
->>-<<<<<<<<<<<<<+>>>>>>>>>>>]<]>[->>+<<]<<<<<<<<<<<<]]>>>>[-]<<<<]>>>>[-<<<<+>>
>>]<<<<[->>>>+>[-]>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+<<+<<<<<]>>>>>>>>>[>>>>>>
>>>]<<<<<<<<<[>[->>>>+<<<[->>>-<<<<<<<<<<<<<+>>>>>>>>>>>[->>+<<]<]>[->>-<<<<<<<<
<<<<<+>>>>>>>>>>>]<<]>[->>>+<<[->>-<<<<<<<<<<<<<+>>>>>>>>>>>]<]>[->>+<<]<<<<<<<<
<<<<]]>>>>>>>>>[>>[-]>[-]>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>[-]>[-]>>>>>[>>>>>[-<<<<+
>>>>]<<<<[->>>>+<<<+<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>>>>[-<<<<<+>>>>>
]<<<<<[->>>>>+<<<+<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>+++++++++++++++[[>>>>
>>>>>]+>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]>[-]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+[>+>>
>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>[-<<<<+>>>>]<<<<[->>>>+<<<<<[->>[-<<+
>>]<<[->>+>>+<<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>>>>]<<<<<<<<<[>
[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<]>[->>>>>>>>>+<<<<<<<<<]<+>>>>>>>>]<<<<<<<<<[>[-
]<->>>>[-<<<<+>[<->-<<<<<<+>>>>>>]<[->+<]>>>>]<<<[->>>+<<<]<+<<<<<<<<<]>>>>>>>>>
[>+>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>->>>>>[-<<<<<+>>>>>]<<<<<[->>>>>+<<<<
<<[->>>[-<<<+>>>]<<<[->>>+>+<<<<]+>>>>>>>>>]<<<<<<<<[<<<<<<<<<]]>>>>>>>>>[>>>>>>
>>>]<<<<<<<<<[>>[->>>>>>>>>+<<<<<<<<<]<<<<<<<<<<<]>>[->>>>>>>>>+<<<<<<<<<]<<+>>>
>>>>>]<<<<<<<<<[>[-]<->>>>[-<<<<+>[<->-<<<<<<+>>>>>>]<[->+<]>>>>]<<<[->>>+<<<]<+
<<<<<<<<<]>>>>>>>>>[>>>>[-<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<+>>>>>>>>>>>>>>>>>
>>>>>>>>>>>>>>>>>>>]>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>+++++++++++++++[[>>>>>>>>
>]<<<<<<<<<-<<<<<<<<<[<<<<<<<<<]>>>>>>>>>-]+>>>>>>>>>>>>>>>>>>>>>+<<<[<<<<<<<<<]
>>>>>>>>>[>>>[-<<<->>>]+<<<[->>>->[-<<<<+>>>>]<<<<[->>>>+<<<<<<<<<<<<<[<<<<<<<<<
]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>>>[-<<<<->>>>]+<<<<[->>>>-<[-<<<+>>>]<<<[->>>+<
<<<<<<<<<<<[<<<<<<<<<]>>>[-]+>>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>>>>>>>>]<<<<<<<<]>
>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>->>[-<<<<+>>>>]<<<<[->>>>+<<[-]<<]>>]<<+>>>>[-<<<<
->>>>]+<<<<[->>>>-<<<<<<.>>]>>>>[-<<<<<<<.>>>>>>>]<<<[-]>[-]>[-]>[-]>[-]>[-]>>>[
>[-]>[-]>[-]>[-]>[-]>[-]>>>]<<<<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>>>[-]>>>>]<<<<<<<<<
[<<<<<<<<<]>+++++++++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>+>>>>>>>>>+<<<<<<<<
<<<<<<[<<<<<<<<<]>>>>>>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+[-]>>[>>>>>>>>>]<<<<<
<<<<[>>>>>>>[-<<<<<<+>>>>>>]<<<<<<[->>>>>>+<<<<<<<[<<<<<<<<<]>>>>>>>[-]+>>>]<<<<
<<<<<<]]>>>>>>>[-<<<<<<<+>>>>>>>]<<<<<<<[->>>>>>>+>>[>+>>>>[-<<<<->>>>]<<<<[->>>
>+<<<<]>>>>>>>>]<<+<<<<<<<[>>>>>[->>+<<]<<<<<<<<<<<<<<]>>>>>>>>>[>>>>>>>>>]<<<<<
<<<<[>[-]<->>>>>>>[-<<<<<<<+>[<->-<<<+>>>]<[->+<]>>>>>>>]<<<<<<[->>>>>>+<<<<<<]<
+<<<<<<<<<]>>>>>>>-<<<<[-]+<<<]+>>>>>>>[-<<<<<<<->>>>>>>]+<<<<<<<[->>>>>>>->>[>>
>>>[->>+<<]>>>>]<<<<<<<<<[>[-]<->>>>>>>[-<<<<<<<+>[<->-<<<+>>>]<[->+<]>>>>>>>]<<
<<<<[->>>>>>+<<<<<<]<+<<<<<<<<<]>+++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>+<<<
<<[<<<<<<<<<]>>>>>>>>>[>>>>>[-<<<<<->>>>>]+<<<<<[->>>>>->>[-<<<<<<<+>>>>>>>]<<<<
<<<[->>>>>>>+<<<<<<<<<<<<<<<<[<<<<<<<<<]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>>>>>>[-<
<<<<<<->>>>>>>]+<<<<<<<[->>>>>>>-<<[-<<<<<+>>>>>]<<<<<[->>>>>+<<<<<<<<<<<<<<[<<<
<<<<<<]>>>[-]+>>>>>>[>>>>>>>>>]>[-]+<]]+>[-<[>>>>>>>>>]<<<<<<<<]>>>>>>>>]<<<<<<<
<<[<<<<<<<<<]>>>>[-]<<<+++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>-<<<<<[<<<<<<<
<<]]>>>]<<<<.>>>>>>>>>>[>>>>>>[-]>>>]<<<<<<<<<[<<<<<<<<<]>++++++++++[-[->>>>>>>>
>+<<<<<<<<<]>>>>>>>>>]>>>>>+>>>>>>>>>+<<<<<<<<<<<<<<<[<<<<<<<<<]>>>>>>>>[-<<<<<<
<<+>>>>>>>>]<<<<<<<<[->>>>>>>>+[-]>[>>>>>>>>>]<<<<<<<<<[>>>>>>>>[-<<<<<<<+>>>>>>
>]<<<<<<<[->>>>>>>+<<<<<<<<[<<<<<<<<<]>>>>>>>>[-]+>>]<<<<<<<<<<]]>>>>>>>>[-<<<<<
<<<+>>>>>>>>]<<<<<<<<[->>>>>>>>+>[>+>>>>>[-<<<<<->>>>>]<<<<<[->>>>>+<<<<<]>>>>>>
>>]<+<<<<<<<<[>>>>>>[->>+<<]<<<<<<<<<<<<<<<]>>>>>>>>>[>>>>>>>>>]<<<<<<<<<[>[-]<-
>>>>>>>>[-<<<<<<<<+>[<->-<<+>>]<[->+<]>>>>>>>>]<<<<<<<[->>>>>>>+<<<<<<<]<+<<<<<<
<<<]>>>>>>>>-<<<<<[-]+<<<]+>>>>>>>>[-<<<<<<<<->>>>>>>>]+<<<<<<<<[->>>>>>>>->[>>>
>>>[->>+<<]>>>]<<<<<<<<<[>[-]<->>>>>>>>[-<<<<<<<<+>[<->-<<+>>]<[->+<]>>>>>>>>]<<
<<<<<[->>>>>>>+<<<<<<<]<+<<<<<<<<<]>+++++[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>>
+>>>>>>>>>>>>>>>>>>>>>>>>>>>+<<<<<<[<<<<<<<<<]>>>>>>>>>[>>>>>>[-<<<<<<->>>>>>]+<
<<<<<[->>>>>>->>[-<<<<<<<<+>>>>>>>>]<<<<<<<<[->>>>>>>>+<<<<<<<<<<<<<<<<<[<<<<<<<
<<]>>>>[-]+>>>>>[>>>>>>>>>]>+<]]+>>>>>>>>[-<<<<<<<<->>>>>>>>]+<<<<<<<<[->>>>>>>>
-<<[-<<<<<<+>>>>>>]<<<<<<[->>>>>>+<<<<<<<<<<<<<<<[<<<<<<<<<]>>>[-]+>>>>>>[>>>>>>
>>>]>[-]+<]]+>[-<[>>>>>>>>>]<<<<<<<<]>>>>>>>>]<<<<<<<<<[<<<<<<<<<]>>>>[-]<<<++++
+[-[->>>>>>>>>+<<<<<<<<<]>>>>>>>>>]>>>>>->>>>>>>>>>>>>>>>>>>>>>>>>>>-<<<<<<[<<<<
<<<<<]]>>>]'''


a='^<M!*!/sM+[2:.2[.2mr%N=.2],%+<!&$[2<,>==1].2=ir.|1^>[-2pr^X2/2<[l.|+%%>-<_m%p~*=%$xMr^-$2+Ml=.+>]<[s]i[x:__[2=/%N=.2]|*%+!1$$MNP_m%1:$~or/lm+!^2]r%1,p~^=%ix1r&%~.>oN[!yN1p-N-ii$!-*x0,i.*>*0.x-$+|ol!*l[^]o[/,&]2or|yYX2%+],rM]N%.:$*N=i<ry*%2[[!^%y'
b='$[~o]^_<21y%PP/X<.&1$lp~r-|1o_Y!~Xx$sY%2o!>o~YMl2p%p.2x&.&>.om%&_0~p*o1N,1=%m:/rp:|~sNlomY|*x0Y+|-P=+%~P1mPm2~%Y_!1]+<pM-M..-2N|2/l1!>!r0P<*y/|-s<,0%+|0^oro=si|:%/Nl2iso+xxp$<*XsMi[py::/P]l+Py%r<%r+Mm[.lMY--.:pM&:2p0]+>,.:=<-|]|*:>%i:_<]/<+p:/y+/</_0|Nm*P^!.[$YM<!M_<[:s!,!$%&*,-./012:<=>MNPXY^_ilmoprsxy|~!$%&*,-./012:<=>MNP'
c='Pi|[/y:N~1r[<m.[imr!sr_l=s-~$=1i+>P>p,Yy]P_P<:]&$|<Yoropy_i~_*0-:0x2x*!>-/~~+=+xYom=|N:[X+|i-o:p.=&l&m<y&+~r/sp/!r^Msp&*y!]m!-$No2:x!|p&:2=!Y/,_1i>,|_^:^!%MN!si![==~o0&o]p_1.rPmyxM:Nm1=_m]>_|&.$s0s:0p<[r<ym:.M=Xy!^YM|02N/ri*,<i<X/_,~>%r!&.r*-xli~.!XMpYx2.p=.,_xm1!p!&P1|s>=]]/&yy2'
d='^<M!*!/sM+[2:.2[.2mr%N=.2],%+<!&$[2<,>==1].2=ir.|1^>[-2pr^X2/2<[l.|+%%>-<_m%p~*=%$xMr^-$2+Ml=.+>]<[s]i[x:__[2=/%N=.2]|*%+!1$$MNP_m%1:$~or/lm+!^2]r%1,p~^=%ix1r&%~.>oN[!yN1p-N-ii$!-*x0,i.*>*0.x-$+|ol!*l[^]o[/,&]2or|yYX2%+],rM]N%.:$*N=i<ry*%2[[!^%y'

type3 = ">5--------.7-----------.+++++++..+++.<2.5+++++++.>.+++.------.--------.2+."
sub_ = "+>+++_<.>."  # [1, 3] > [1, 2] 
add_ = "+>+++=<.>."  # [1, 3] > [1, 4] 
not_ = "+~."  # [1] > fe
mod_ = ">+++%."  # [1] > fe
test1 = "$!42*8l<!P|D[-/8oD>BF9=pr*7lDFE[Cl6A,$6]i/&0s&E-5!-|6i8,o|D$mF^73o+F4F=*~4BsD.]BMpm[+F<CEr%F7:9*r11MC|6*sp-.0!BF8s9<^77.1|$m&66,*2,CF~^lm!9F=0<.PFB4!4C%10A%1BCCEE/*92$4$<472|7B[ir_[/PB23:23/:4|$_B.F4|CPr9*!MlC3$P|8Erm1D59=p+A.!l:l|![i,^op9Ms.=4~[[F,,*7DA[+/5*.&,FM,Fp$>$]i_&^48,mr"
test2 = "E~s3|6F]%6>7<7^901+>&p,s+$<9_-<+M//8pi668|<+57!_D33+25!8_%As:,0-2m*sCpsp0m:Fs&r9%|7!-|_l6E7D0$4*>9+M3mAB/8.15<Ail~.>/,&%Dr6$D|,[!/9!5>3i07$71|s_7l.!imlmP!E-|AC5s->:05$*_87C:s!-_A2p4o$0o!]oD1p=E/]Ap3$6iE6&2E|Am91]$B$/[7l5*&FPi4.>:D/i:_2PA.Ps*]%-C!*+!l/p*DA10*P|/+[2%E[8MP<M9so<+~0FM<M0-|/%94=C:+M|$8/*,l&-B55[C8l-_*6l4-MmM"

try:    
    code = sys.argv[1]
except:
    code = None
import struct
    
if __name__ == "__main__":
    bytefuck = Bytefuck() 

    for _ in range(100):
        data = bytes([random.randint(0,255) for _ in range(0,1000000)])
        bytefuck.execute(b"[[[[[lP>][lP>][lP>][lP>][lP>]]]]]",data)
        bytefuck.execute(a,data)
        bytefuck.execute(b,data)
        bytefuck.execute(c,data)
        bytefuck.execute(d,data)


    for _ in range(0,99):
        print(bytefuck.execute("->!~~&[!1i]pY*%l~MsMMM>o~X^1<m.=,2+x=|&>X_%X^.|",struct.pack("IIIIIII",random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000))))
        print(bytefuck.execute('X^+1o//=mi==+Pmo-1^0Pxx-_l_i|r~]XP%,y,$$_-!.>/.[o.^ym=~2[X%!/]/Ns1y*!l%N,s$|0+>NxMi2|p.NoXP,!',struct.pack("IIIIIII",random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000),random.randint(0,4000000000))))
    print(bytefuck.execute("Xiiii>>>>Y<<<<<<<<yx",struct.pack("I",1278725465)))
    exit(0)
    print("1: %s" % bytefuck.execute(helloworld1,""))
    print("2: %s" % bytefuck.execute(helloworld2,""))
    print("3: %s" % bytefuck.execute(helloworld3,""))
    print("4: %s" % bytefuck.execute(helloworld4,""))
    print("mod_: %s" % bytefuck.execute(mod_,""))
    print("sub_: %s" % bytefuck.execute(sub_,""))
    print("add_: %s" % bytefuck.execute(add_,""))
    print("not_: %s" % bytefuck.execute(not_,""))
    print("test1: %s" % bytefuck.execute(test1,""))
    print("test2: %s" % bytefuck.execute(test2,""))
    if code != None:    
        print("code: %s" % bytefuck.execute(code,inputbytes))
    #print(bytefuck.execute(mandelbrot,""))

