import struct
import sys
from subprocess import Popen, PIPE
import subprocess
import errno
import time
import queue
import threading
from collections import namedtuple
import os

ExecutionResult = namedtuple('ExecutionResult',[
    "program_steps", 
    "memory_usage",
    "inputbuffer_usage",
    "output_size",
    "output",
    "memory_size",
    "memory",
    "execution_time",
])

class BrainfuckC():
    def __init__(self):
        self.queue_stdout = queue.Queue()
        self.queue_stdin = queue.Queue()
        self.thread = None
        
    def start(self):   
        if self.thread == None:
            self.thread = threading.Thread(target=self._start)
            self.thread.daemon = True
            self.thread.start()
    
    def load(self, code = "", max_steps = 1000, max_memory = 100000, clear_memory = True, output_memory = False, preload_memory = ""):
        self.start()
        bytecode = bytearray(code,"UTF-8")
        optionheader = [
            struct.pack("c", bytes('c',"ASCII")),  # code
            struct.pack("Q", len(bytecode)),
            bytecode,
            
            struct.pack("c", bytes('s',"ASCII")), # max steps
            struct.pack("Q", max_steps),

            struct.pack("c", bytes('m',"ASCII")), # max memory
            struct.pack("Q", max_memory),
            
            struct.pack("c", bytes('o',"ASCII")), # output memory mode
            struct.pack("c", bytes(chr(1),"ASCII")) if output_memory else struct.pack("c", bytes(chr(0),"ASCII")),
        ]
        if clear_memory:    
            optionheader.append( struct.pack("c", bytes('l',"ASCII"))) # clear memory
            
        if preload_memory != "":
            byte_preload_memory = bytearray(preload_memory,"UTF-8")
            optionheader.extend([
                struct.pack("c", bytes('p',"ASCII")),
                struct.pack("Q", len(byte_preload_memory)),
                byte_preload_memory,
            ])
        
        optionheader.append( struct.pack("c", bytes('x',"ASCII"))) # x is end char    
        self.queue_stdin.put(b''.join(optionheader))
        result = self.queue_stdout.get()
        self.queue_stdout.task_done()        
                
    def run(self, input, clear_memory = True):
        executionheader = []
        
        if clear_memory:    
            executionheader.append( struct.pack("c", bytes('l',"ASCII"))) # clear memory
                
        try:
            byteinput = bytearray(input)
        except:
            byteinput = bytearray(input,"UTF-8")
            
        executionheader.extend([
            struct.pack("c", bytes('e',"ASCII")), # execute on input
            struct.pack("Q", len(byteinput)),
            byteinput,
        ])
        
        #executionheader.append( struct.pack("c", bytes('x',"ASCII"))) # x is end char    

        self.queue_stdin.put(b''.join(executionheader))
        
        result = self.queue_stdout.get()
        self.queue_stdout.task_done()
        return result 

    def stop(self):
        print("stop")
        self.queue_stdin.put(False)
        self.queue_stdout.put(False)
        time.sleep(2)
            
    def _start(self):
        
        p = Popen('%s/brainfuck' % os.path.dirname(os.path.abspath(__file__)), stdin=PIPE,stdout=PIPE)#,stderr = subprocess.DEVNULL)
        print("start thread")
        while True:
            try:
                tosend = self.queue_stdin.get()
                self.queue_stdin.task_done()                
                if tosend == False:
                    print("existing thread")
                    self.queue_stdout.put(None)        
                    return 
                p.stdin.write(tosend)
                p.stdin.flush()

                result = self._parse_output(p.stdout)
                self.queue_stdout.put(result)
                
            except Exception as e:
                self.queue_stdout.put(None)       
        print("THREAD EXIT")                    
        try:
            p.stdin.close()
        except:
            print("failed to close stdin")
        
        p.wait()
         
    def _parse_output(self, process_stdout):
        program_steps = -1
        memory_usage = -1
        inputbuffer_usage = -1
        output_size = -1
        output = b''
        memory_size = -1
        memory = b''
        execution_time = 0
                
        while True:
            c = chr(ord(struct.unpack("c",process_stdout.read(1))[0]))
            if c == 's':
                program_steps = struct.unpack("Q",process_stdout.read(8))[0]
                #print("program_steps %s" % program_steps)
            elif c == 'm':
                memory_usage = struct.unpack("Q",process_stdout.read(8))[0]
                #print("memory_usage %s" % memory_usage)
            elif c == 'i':
                inputbuffer_usage = struct.unpack("Q",process_stdout.read(8))[0]
                #print("inputbuffer_usage %s" % inputbuffer_usage)
            elif c == 'o':
                output_size = struct.unpack("Q",process_stdout.read(8))[0]
                output = process_stdout.read(output_size)
                #print("output_size %s" % output_size)
            elif c == 'c':
                memory_size = struct.unpack("Q",process_stdout.read(8))[0]
                memory = process_stdout.read(memory_size)
                #print("memory_size %s" % memory_size)
            elif c == 'x':
                execution_time = struct.unpack("Q",process_stdout.read(8))[0]
                break
            else:
                print("unknown output '%s'" % c)
                break
        return ExecutionResult(
            program_steps = program_steps,
            memory_usage = memory_usage,
            inputbuffer_usage = inputbuffer_usage,
            output_size = output_size,
            output = output,
            memory_size = memory_size,
            memory = memory,
            execution_time = execution_time,
        )            

def loop():
    brain = BrainfuckC()
    brain.start()
    for _ in range(0,100000):
        result = brain.run("+[----->+++<]>+.+.","hallo") 
        
    brain.stop()        
    
    
def test():
    brain = BrainfuckC()
    brain.start()
    r = brain.run(',,[[N+',bytearray([255,1]),1000) 
    
    if r != None:
        steps,outputlength,outputdata = r 
        print("steps: %s"  % steps ) 
        print("OutLen: %s"  %  outputlength ) 
        print("Outputdata: %s"  %  outputdata ) 
        print("Executed")
    brain.stop()
        
        
def test2():
    brain = BrainfuckC()
    brain.start()
    h = "++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++.>++.<<+++++++++++++++.>.+++.------.--------.>+.>."
    #h = "+[----->+++<]>+.+."
    brain.load(code = h, max_steps = 10000, max_memory = 100000, clear_memory = True, output_memory = True, preload_memory = "")
    time.sleep(1)
    for _ in range(0,20):
        result = brain.run("test", clear_memory = True)
        print(result)
    
    brain.stop()
    
if __name__ == "__main__":        
    test2()

    
    
    
    