import random
import abc
import copy
import itertools
import random
import string
import json
import bson
import struct

def get_examplesource(taskname):
    max_cachesize = 4000
    cache_hitrate = 0.999
    examplecache = {}
    
    def f():
        task = task_mapping[taskname]
        while True:
            iogenerator = iter(task())
            while True:
                random_index = random.randint(0,max_cachesize)
                if random.random() < cache_hitrate:
                    try:
                        r = examplecache[random_index]
                        yield r
                        continue
                    except:
                        pass
                i, o = next(iogenerator)
                r = [bytes(i),bytes(o)]
                examplecache[random_index] = r
                yield r 
    return f
   
def _randomkey(length):
   return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def data2data_byte_at_index():
    while True:
        str = _randomkey(random.randint(1,50))
        index = random.randint(0,len(str)-1)
        src = struct.pack('I', index) + bytes(str,"ASCII")
        x = [ src , bytes(str[index],"ASCII") ]
        #print(x)
        yield x
        
def data2data_byte_from_bson_dict():
    while True:
        data = {}
        for _ in range(0,random.randint(1,5)):
            data[_randomkey(random.randint(1,5))] = random.randint(0,255)
        toget = random.choice(list(data.keys()))
        src = bytes(toget,"ASCII") + b"\0" + bson.dumps(data) 
        x = [ src, bytes([data[toget]]) ]
        #print(x)
        yield x
        
def data2data_bytes_from_bson_dict():
    while True:
        data = {}
        for _ in range(0,random.randint(1,5)):
            data[_randomkey(random.randint(1,5))] = bytes(_randomkey(random.randint(1,5)),"ASCII")
        toget = random.choice(list(data.keys()))
        src = bytes(toget,"ASCII") + b"\0" + bson.dumps(data) 
        x = [ src, data[toget] ]
        #print(x)
        yield x
           
      
task_mapping =  {
    "data2data byte at index": data2data_byte_at_index,
    "data2data byte from bson dict": data2data_byte_from_bson_dict,
    "data2data bytes from bson dict": data2data_bytes_from_bson_dict,
    
}
    