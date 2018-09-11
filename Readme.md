

#### What 
  
Assume we want to generate arbitary programms using evolutionary algorithms.

What programming language to choose to evolve?

C? Most likey not, its complex. Maybe brainfuck, seems more resonable because its way simpler. Many people came to that conclusion. (google brainfuck evolutionary algorithm)

Question: If C is bad, and brainfuck is better, whats good or best? And why? 

How would a programming language look that is generate by and for an evolutionary algorithm?

Since we 'know' brainfuck can be evolved, why not evolved a programming lanugage + compiler that compiles to brainfuck? 


#### Steps:  

Bytefuck:
    Bytefuck is compatible to brainfuck, but as some more functions.
    If Bytefuck/Brainfuck is good or bad as a seed language is an open question.
    
Model
    Everything is store in a database via django orm layer. Theres also a webinterface for stats.
    The evolution classes will load population, species and individuals into redis on instanciation.
    All atomic actions like adding fitness, removing individuals, updating liste sorted by fitness and so on happen in redis via redis_lua_script.


Evolution:
   create an evoltion instance:
    evolutionCompiler = Evolution(
        species_name = "Compiler",
        problem_name =  "Compiler", 
        problem_description = "Compile an individual from bytes to some brainfuck dialect",
        
        max_populations = 10 , # max number of parallel populations
        min_populationsize = 250, # min number of living individuals per population, create random inds if lower
        max_populationsize = 350, # max number of living individuals per population
        min_code_length = 100, #
        max_code_length = 500, #
        
        min_fitness_evaluations = 4, #
        max_fitness_evaluations = 16, #
        
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in 
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        usePriorKnowledge = False,
        useP2P = False,
        warmup = False,
        reference_functions = [
            { "name" : "evolutionCompilerReference" , "function" : evolutionCompilerReference },
        ],
        reference_function_rate = 1,
    )   
    # do your stuff:
    while whatever:
        selected_compiler = evolutionCompiler.get_random_individual()
        code_compiled = selected_compiler.execute("compile", code)
        selected_compiler.addFitness(23)
            
    Note that you dont have to explicitly trigger any mutation action, get get some individual and reward it however you like.
    The actual evoltion happens in EvolutionApi.py EvolutionaryMethods(). Its triggers on multiple events
        onIndividualMustCompile
        afterIndividualAddFitness
        afterIndividualDeath
        onPopulationsizeUnderflow
        onPopulationsizeOverflow
        
MetaEvolution:
    
            
#### Run

##### Run Webserver
```
python3 manager.py runserver 127.0.0.1:12345
```

##### Run P2P Node

Add first peer to join network:
```
python3 p2pNode addpeer 1.23.42.66
```

Run behind NAT:
```
python3 p2pNode
```

Run as pulic supernode
```
python3 p2pNode public 1.2.3.4
```
