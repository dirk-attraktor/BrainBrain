import struct
import sys
from subprocess import Popen, PIPE
import subprocess
import errno
import time
import queue
import threading


class BrainC():
    def __init__(self):
        self.queue = queue.Queue()
        self.outqueue = queue.Queue()
        t = threading.Thread(target=self._start)
        t.daemon = True
        t.start()
    # returns [steps,outputlength,outputdata]
    def run(self,code,input,maxsteps):
        
        codesize = len(code)
        inputsize = len(input)
        memorysize = 0
        do_output_memory = bytes(chr(0),"ASCII")
        
        bytecode = bytearray(code,"UTF-8")
        header = struct.pack("QQQQc", len(bytecode), inputsize, memorysize, maxsteps, do_output_memory)
        tosend = header+bytecode+input
        #print("tosend")
        #print(tosend)
        #open("/tmp/inputdebug","wb").write(tosend)
        self.queue.put(tosend)
        #print("senbd")
        x = self.outqueue.get(timeout=1000)
        self.outqueue.task_done()
        #print("returning results")
        return x 
        
    def stop(self):
        print("stop")
        self.queue.put(False)
        self.outqueue.put(False)
        time.sleep(2)
        
    def _start(self):
        p = Popen('./brainfuck', stdin=PIPE,stdout=PIPE)#,stderr = subprocess.DEVNULL)
        print("start thread")
        while True:
            try:
                #print("FOOBAR")
                tosend = self.queue.get()
                self.queue.task_done()                
                if tosend == False:
                    print("existing thread")
                    self.outqueue.put(None)        
                    return 

                #print(tosend[33:])
                #print("sending to stdin")
                p.stdin.write(tosend)
                p.stdin.flush()
                x = p.stdout.read(12)
                #print("Outlength: %s" % len(x))
                steps, outputlength = struct.unpack("Qi",x)
                outputdata = p.stdout.read(outputlength)
                
                #print("Steps: '%s'    OutLen: '%s'" % (steps,outputlength))
                #print("Outputdata: '%s'" % outputdata)
                self.outqueue.put([steps,outputlength,outputdata])
                #print("output put done")
            except IOError as e:
                print(e)
                self.outqueue.put(None)       
                if e.errno == errno.EPIPE or e.errno == errno.EINVAL:
                    # Stop loop on "Invalid pipe" or "Invalid argument".
                    # No sense in continuing with broken pipe.
                    break
                else:
                    # Raise any other error.
                    raise
        print("THREAD EXIT")                    
        try:
            p.stdin.close()
        except:
            print("failed to close stdin")
        
        p.wait()


def loop():
    x = BrainC()
    for _ in range(0,100000):
        result = x.run("+[----->+++<]>+.+.","hallo") 
        if result != None:
            print("steps: %s"  % result[0] ) 
            print("OutLen: %s"  %  result[1] ) 
            #print("Outputdata: %s"  %  result[2] ) 
            print("Executed")
    x.stop()        
    
    
def test():
    x = BrainC()
    r = x.run(',,[[N+',bytearray([255,1]),1000) 
    
    if r != None:
        steps,outputlength,outputdata = r 
        print("steps: %s"  % steps ) 
        print("OutLen: %s"  %  outputlength ) 
        print("Outputdata: %s"  %  outputdata ) 
        print("Executed")
    x.stop()
        
if __name__ == "__main__":        
    test()
