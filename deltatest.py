import pprint

lines = open("/tmp/deltafitness","r").read().split("\n")

parts = [l.split("\t") for l in lines]

lookuptable = {}
for  x in parts:
    try:    
        input,output = x
    except:
        continue
    #print("in: %s\t\tout: %s" % (input,output))
    for i in range(6,10): # for every 1 to 4 char pattern
        #print("i:%s" % i)
        start = 0
        while start + i < len(input):
            inputpart = input[start:start+i]
            outpart = output[start:start+i]
            start += i            
            
            if inputpart != outpart and len(inputpart) == len(outpart):
                print("%s\t%s" % (inputpart,outpart))
                try:
                    lookuptable[inputpart]
                except:
                    lookuptable[inputpart] = {}
                try:
                    lookuptable[inputpart][outpart] += 1
                except:
                    lookuptable[inputpart][outpart] = 1
                    
                    
pprint.pprint(lookuptable)                    
