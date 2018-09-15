bytefuckcode = ">[,-].-<]-[[<[,[[[.,,],++<->>[[<+]+>]]],]-[-[---[+[[[[,-]-]]]-.>++[<,<,->++],-<->]<,,]-[+<-[+[+[[---[<[+[<,[[,-<<[[[>.+.->-[>>.<,,][+<]-.++]-[.[,,]-->+<,,]-[-----[,[,-<.-]>>,+[+[>[,,]]<],]-[<]>>,+[+[,[<--]<]],.,."

codetemplate = '''
    #include <stdio.h>
    #include <stdlib.h>
    
    int main(int argc, char **argv){
        unsigned char *cell = calloc(30000, 1);
        unsigned char *cells = cell;
        unsigned long long maxsteps = 10000000;
        unsigned long long steps = 0;
        if (!cell) {
            fprintf(stderr, "Error allocating memory.\\n");
            return 1;
        }
    
        %(code)s
    
        free(cells);
        return 0;
    }
'''

def cleanbrackets(code):
    codelist = list(code)
    jumpmap = [0]*len(codelist)
    lencode = len(codelist)
    for index, codechar in enumerate(codelist):
        if codechar == '[':
            parenthesis_tmp_position = index;
            parenthesis_counter = 1;  
            while parenthesis_counter != 0 and parenthesis_tmp_position < lencode-1:
                parenthesis_tmp_position += 1;
                if (codelist[parenthesis_tmp_position] == '['):
                    parenthesis_counter += 1;
                if (codelist[parenthesis_tmp_position] == ']'):
                    parenthesis_counter -= 1;
            if parenthesis_counter != 0:
                codelist[index] = ""
                
        if codechar == ']':
            parenthesis_tmp_position = index;
            parenthesis_counter = 1;
            while parenthesis_counter != 0 and parenthesis_tmp_position > 0:
                parenthesis_tmp_position -= 1;
                if codelist[parenthesis_tmp_position] == ']':
                    parenthesis_counter += 1;
                if codelist[parenthesis_tmp_position] == '[':
                    parenthesis_counter -= 1;
            if parenthesis_counter != 0:
                codelist[index] = ""

    return "".join(codelist)
 
bytefuckcode = cleanbrackets(bytefuckcode)
print(bytefuckcode)

def toC(code):
    maxsteps = 10 * 1000 * 1000
    loopandsubloopcount = 0
    c_code = []
    identlevel = 2
    instructioncnt = 0
    countperlevel = {}
    for char in code:
        instructioncnt += 1 
        if   char == ">":
            c_code.append(" " * (4*identlevel) + "++cell;")
        elif char == "<":
            c_code.append(" " * (4*identlevel) + "--cell;")
        elif char == "+":
            c_code.append(" " * (4*identlevel) + "++*cell;")
        elif char == "-":
            c_code.append(" " * (4*identlevel) + "--*cell;")
        elif char == ".":
            c_code.append(" " * (4*identlevel) + "putchar(*cell);")
        elif char == ",":
            c_code.append(" " * (4*identlevel) + "*cell = getchar();")
        elif char == "[":
            c_code.append(" " * (4*identlevel) + "steps += %s;" % ( instructioncnt - 1 ) )
            c_code.append(" " * (4*identlevel) + "while (*cell) {") 
            countperlevel[identlevel] = 0
            for i in range(identlevel, 1, -1):
                countperlevel[i] += 1
            instructioncnt = 0
            identlevel += 1
        elif char == "]":
            c_code.append(" " * (4*identlevel) + "steps += %s;" % ( instructioncnt - 1 ) )
            c_code.append(" " * (4*identlevel) + "cpl:%s"%countperlevel[identlevel-1])
            identlevel -= 1
            c_code.append(" " * (4*identlevel) + "};")
            loopandsubloopcount += countperlevel[identlevel]
            instructioncnt = 1
        else:
            print("Unknown char '%s'" % char)
          
    print(loopandsubloopcount)   
    stepsperloop = int(maxsteps / loopandsubloopcount)
    for index, line in enumerate(c_code):
        if line.strip().startswith("cpl:"):
            nrofsubloops = int(line.split(":")[1])
            steps = stepsperloop * nrofsubloops
            c_code[index] =  c_code[index] + ":%s" % steps
    steplimit = 0
    for index, line in enumerate(c_code):
        if line.strip().startswith("cpl:"):
            nrofsubsteps = int(line.split(":")[2])
            steplimit += nrofsubsteps
            c_code[index] =  c_code[index] + ":%s" % steplimit
            c_code[index] = line.split("cpl")[0] + "if(steps > %s){ break; }" % steplimit
            
    print(stepsperloop)   

    return "\n".join(c_code)
        
print(codetemplate % {
    "code": toC(bytefuckcode),
})        
