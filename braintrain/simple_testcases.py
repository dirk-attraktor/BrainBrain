import random
import abc
import copy
import itertools
import random
import string
import json
import bson
 
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
   
def examplesource_decimal2byte():
    while True:
        a = random.randint(0, 255)
        yield [bytes("%s" % a,"ASCII"), bytes([a]) ]
        
def examplesource_byte2decimal():
    while True:
        a = random.randint(0, 255)
        yield [bytes([a]) , bytes("%s" % a,"ASCII")]
         
def examplesource_add_2_bytes():
    while True:
        a = random.randint(0, 127)
        b = random.randint(0, 127)
        c = a + b
        yield [bytes([a,b]) , bytes([c])]
        
def examplesource_add_3_bytes():
    while True:
        a = random.randint(0, 80)
        b = random.randint(0, 80)
        c = random.randint(0, 80)
        d = a + b  + c 
        yield [bytes([a,b,c]) , bytes([d])]
        
def examplesource_sub_2_bytes():
    while True:
        a = random.randint(128, 255)
        b = random.randint(0, 128)
        c = a - b
        yield [bytes([a,b]) , bytes([c])]
  
def examplesource_add_3_integer_bson():
    while True:
        a = random.randint(0, 1000000000)
        b = random.randint(0, 1000000000)
        c = random.randint(0, 1000000000)
        d = a + b + c 
        yield [bson.dumps({0:a, 1:b, 2:c}) , bson.dumps({0:d})]
    
  
def examplesource_add_2_integer_bson():
    while True:
        a = random.randint(0, 2000000000)
        b = random.randint(0, 2000000000)
        c = a + b
        yield [bson.dumps({0:a,1:b}) , bson.dumps({0:c})]
    
def examplesource_sub_2_integer_bson():
    while True:
        a = random.randint(0, 2000000000)
        b = random.randint(0, 2000000000)
        c = a - b
        yield [bson.dumps({0:a,1:b}) , bson.dumps({0:c})]
      
    
def examplesource_add_2_integer():
    while True:
        a = random.randint(0, 2000000000)
        b = random.randint(0, 2000000000)
        c = a + b
        yield [bytes("%s\t%s" % (a, b),"ASCII") , bytes("%s" % c,"ASCII")]
    
def examplesource_sub_2_integer():
    while True:
        a = random.randint(0, 2000000000)
        b = random.randint(0, 2000000000)
        c = a - b
        yield [bytes("%s\t%s" % (a, b),"ASCII") , bytes("%s" % c,"ASCII")]
    
    
def examplesource_add_2_float():
    while True:
        a = random.random() * random.randint(0, 2000000000)
        b = random.random() * random.randint(0, 2000000000)
        c = a + b
        yield [bytes("%s\t%s" % (a, b),"ASCII") , bytes("%s" % c,"ASCII")]
    
def examplesource_sub_2_float():
    while True:
        a = random.random() * random.randint(0, 2000000000)
        b = random.random() * random.randint(0, 2000000000)
        c = a - b
        yield [bytes("%s\t%s" % (a, b),"ASCII") , bytes("%s" % c,"ASCII")]
      
def split_string_on_delimiter():
    while True:
        s = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(3,200)))
        delimiter = random.choice(s)
        output = s.split(delimiter)
        yield  [ bytes(json.dumps([delimiter, s ]),"ASCII") ,  bytes(json.dumps(output),"ASCII") ] 

def secret_string_1():
    while True:
        yield  [ bytes('',"ASCII") ,  bytes("hello world","ASCII") ] 
        
def secret_string_2():
    while True:
        yield  [ bytes('',"ASCII") ,  bytes("hello world ab76vfdaas456s","ASCII") ] 
          
       
task_mapping =  {
    "my-testcase decimal2bytes": examplesource_decimal2byte,
    "my-testcase byte2decimal": examplesource_byte2decimal,
    
    "my-testcase find secret string 1": secret_string_1,
    "my-testcase find secret string 2": secret_string_2,
    
    "my-testcase add 3 bytes": examplesource_add_3_bytes,
    
    "my-testcase add 2 bytes": examplesource_add_2_bytes,
    "my-testcase sub 2 bytes": examplesource_sub_2_bytes,
    
    "my-testcase add 2 integer bson": examplesource_add_2_integer_bson,
    "my-testcase sub 2 integer bson": examplesource_sub_2_integer_bson,
    
    "my-testcase add 3 integer bson": examplesource_add_3_integer_bson,
    
    "my-testcase add 2 integer": examplesource_add_2_integer,
    "my-testcase sub 2 integer": examplesource_sub_2_integer,
    
    "my-testcase add 2 float": examplesource_add_2_float,
    "my-testcase sub 2 float": examplesource_sub_2_float,
    
    "my-testcase split_string_on_delimiter": split_string_on_delimiter,
}
    