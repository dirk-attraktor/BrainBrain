import random
from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Individual
from brainweb.models import Population
from brainweb.models import ReferenceFunction
import numpy as np
import reward
import p2pClient
import re

GENES = [
    '>', # inkrementiert den Zeiger
    '<', # dekrementiert den Zeiger
    '+', # inkrementiert den aktuellen Zellenwert
    '-', # dekrementiert den aktuellen Zellenwert
    '[', # Springt nach vorne, hinter den passenden ]-Befehl, wenn der aktuelle Zellenwert 0 ist	
    ']', # Springt nach vorne, hinter den passenden ]-Befehl, wenn der aktuelle Zellenwert 0 ist
    '.', # Gibt den aktuellen Zellenwert als ASCII-Zeichen auf der Standardausgabe aus
    ',', # Liest ein Zeichen von der Standardeingabe und speichert dessen ASCII-Wert in der aktuellen Zelle
    'N', # NoOp
    'A', # NoOp
    'B', # NoOp
]
GENES_STRING = '\\'.join(GENES)
GENES_REGEX = "[^%s]+" % GENES_STRING

   
def create_first_individual():
    return "".join([random.choice(GENES) for _ in range(0,10)])
    

class Evolution():
    
    def __init__(self,
            name, 
            description = "",
            referenceFunctionRate = 1, 
            max_generations = -1, 
            max_individuals = 10,
            max_populationsize = 10000, 
            max_code_length = 100, 
            min_code_length = 10,
            max_steps = 1000,
            min_fitness_evaluation_per_individual = 1,
            usePriorKnowledge = True,
            useP2P = True,
            warmup = False,
            sync_to_database = False, # set True for evolutions that are multiprocessed and need db sync
        ):
        
        self.problem = None
        self.selected_population = None    
        self.selected_individual = None    
        self.loaded_referenceFunctions = {}
        
        print("initializeProblem %s" % name)
        try:
            return ProblemInstances[name]
        except:
            None
        new = False
        try:
            problem = Problem.objects.get(name=name)
        except:
            problem = Problem()
            new = True
        self.referenceFunctionRate = referenceFunctionRate

        problem.name = name
        problem.usePriorKnowledge = usePriorKnowledge
        problem.useP2P = useP2P
        
        problem.description = description
        problem.sync_to_database = sync_to_database
        problem.default_max_populationsize = max_populationsize
        problem.default_max_individuals = max_individuals
        problem.default_max_generations = max_generations
        problem.default_max_code_length = max_code_length
        problem.default_min_code_length = min_code_length
        problem.default_max_steps = max_steps
        problem.default_min_fitness_evaluation_per_individual = min_fitness_evaluation_per_individual
        
        problem.save()
        self.problem = problem
        if self.problem.populations.count() == 0 and self.problem.default_max_populationsize != 0:
            self.problem.addPopulation()
            
        self.selected_population = self.problem.populations.all()[0]  
        
        self.selected_population.max_populationsize = problem.default_max_populationsize
        self.selected_population.max_individuals = problem.default_max_individuals
        self.selected_population.max_generations = problem.default_max_generations
        self.selected_population.max_code_length = problem.default_max_code_length
        self.selected_population.min_code_length = problem.default_min_code_length
        # self.selected_population.max_steps = problem.default_max_steps TODO
        self.selected_population.min_fitness_evaluation_per_individual = problem.default_min_fitness_evaluation_per_individual        
        self.selected_population.initializeIndividuals()
        self.selected_population.save()
        
        for individual in self.selected_population.getIndividuals():
            if len(individual.code) < 5:
                #print("need to init code")
                individual.code = create_first_individual()
                individual.save()
        self.warmup = warmup
          
    def evolve(self,function): 
        if self.problem.populations.count() == 0 and self.problem.default_max_populationsize != 0:
            self.problem.addPopulation()
        name = function.__name__
        if name not in self.loaded_referenceFunctions:
            referenceFunction = self.problem.getReferenceFunction(name)
            if referenceFunction == None:
                referenceFunction = ReferenceFunction()
                referenceFunction.name = name
                referenceFunction.problem = self.problem
                referenceFunction.save()
            referenceFunction.function = function            
            self.loaded_referenceFunctions[name] = referenceFunction

        
        def replacementFunction(*args,**kwargs):
            #print("replacementFunction")
            #print(self.id)
            if self.selected_individual == None:
                #print(" selecting individual")
                if random.random() < self.referenceFunctionRate or self.problem.default_max_populationsize == 0:
                    self.selected_individual = self.loaded_referenceFunctions[random.choice(list(self.loaded_referenceFunctions.keys()))]
                else:
                    self.selected_individual = self.selected_population.getUnratedIndividual()
                    if self.selected_individual == None:
                        self.selected_individual = random.choice(self.selected_population.getIndividuals())
                            
            if type(self.selected_individual) == ReferenceFunction:
                result = self.selected_individual.execute(args[0])
                
            if type(self.selected_individual) == Individual:
                result = ''.join(chr(i) for i in self.selected_individual.execute(args[0]).output )
                if self.warmup == True:
                    ref_function = self.loaded_referenceFunctions[random.choice(list(self.loaded_referenceFunctions.keys()))]
                    result_ref = ref_function.execute(args[0])
                    try:
                        r = reward.absolute_distance_reward(bytearray(result_ref,"ASCII"),bytearray(result,"ASCII") , 256)
                    except Exception as e:
                        #print("failed to do warmup reward %s" % e)
                        r = -100
                    #print("warmup reward for %s : %s"  % (self.problem.name,r))
                    self.reward(r,rewardWarmup = True)
                    result = result_ref
            return result
                
        return replacementFunction       
    

    
    def reward(self,value,count = 1,rewardWarmup = False):
        if self.warmup == True and rewardWarmup == False:
            #print("warmup reward not happending")
            return
        #print("REWARD")
        if type(self.selected_individual) == ReferenceFunction and count != 1:
            print("ref: %s" % count)
        if self.selected_individual != None:
            for _ in range(0,count):
                self.selected_individual.addFitness(value)
        self.selected_individual = None
        individuals = self.selected_population.getIndividuals() 
        
        minEvals = self.selected_population.min_fitness_evaluation_per_individual
        if self.warmup == True and minEvals > 100 :
            minEvals = minEvals / 10
        
        underrated = [i for i in individuals if i.fitness_evalcount  < minEvals]
        if len(underrated) == 0:
            #print("REWARD GA STEP1")
            ga_step(self.selected_population)
    
    def save(self):
        self.selected_population.save()
        for key in self.loaded_referenceFunctions:
            self.loaded_referenceFunctions[key].save()   
        self.problem.save()
    
class Regression():

    def __init__(self, 
            name, 
            description = "", 
            max_generations = -1, 
            max_individuals = 10,
            max_populationsize = 100, 
            max_code_length = 100, 
            min_code_length = 100,
            max_steps = 5000,
            min_fitness_evaluation_per_individual = 1,
            usePriorKnowledge = True,
            useP2P = True,
        ):
        
        self.problem = None
        self.selected_population = None    
        self.selected_individual = None    
        self.loaded_referenceFunctions = {}
    
        print("initializeProblem %s" % name)
        try:
            return ProblemInstances[name]
        except:
            None
        new = False
        try:
            problem = Problem.objects.get(name=name)
        except:
            problem = Problem()
            new = True

        problem.name = name
        problem.description = description
        problem.usePriorKnowledge = usePriorKnowledge
        problem.useP2P = useP2P
        problem.default_max_populationsize = max_populationsize
        problem.default_max_individuals = max_individuals
        problem.default_max_generations = max_generations
        problem.default_max_code_length = max_code_length
        problem.default_min_code_length = min_code_length
        problem.default_max_steps = max_steps
        problem.default_min_fitness_evaluation_per_individual = min_fitness_evaluation_per_individual
        
        problem.save()
        self.problem = problem
        if self.problem.populations.count() == 0 and self.problem.default_max_populationsize != 0:
            self.problem.addPopulation()
        self.selected_population = self.problem.populations.all()[0]    
        self.selected_population.initializeIndividuals()
        for individual in self.selected_population.getIndividuals():
            if len(individual.code) < 5:
                #print("need to init code")
                individual.code = create_first_individual()
                individual.save()
        
        
    def regress(self, coderatingfunction,addpopulation = True, maxsteps = -1):
        if addpopulation == True:
            self.selected_population = self.problem.addPopulation()
        for individual in self.selected_population.getIndividuals():
            if len(individual.code) < 5:
                #print("need to init code")
                individual.code = create_first_individual()
                individual.save()
        step = 0
        while step < maxsteps or maxsteps == -1:
            step += 1
            #if step % 1000 == 0:
            #    print("Regress step '%s'  for '%s'" % (step,self.problem ))
            self.selected_individual = self.selected_population.getUnratedIndividual()
            if self.selected_individual == None:
                 if ga_step(self.selected_population) == False:
                    print("regression finised, ga_step returned false")
                    break 
                 #else:
                 #   print("GA step doned")
                 self.selected_individual = self.selected_population.getUnratedIndividual()
            #self.selected_individual.execution_counter += 1 # dummy bcs we dont know what external function does
            fitness = coderatingfunction(self.selected_individual)
            #print("codef")
            self.selected_individual.addFitness(fitness)     
            if fitness == 1:
                print("Fitness 1 reached! regress %s Solved!" % self.problem.name)
                #print(brainfuck.evaluate(self.selected_individual.code,"hallo"))
                break            
        self.selected_population.updateStats()
        
        
    def save(self):
        self.selected_population.save()
        for key in self.loaded_referenceFunctions:
            self.loaded_referenceFunctions[key].save()
        self.problem.save()
    
   
def score_individual(individual, io_seqs):
    r = 0.0
    for input_seq, output_seq in io_seqs:
        result = individual.execute(input_seq)
        try:
            x = bytearray(output_seq,"UTF-8")
        except:
            x = bytearray(output_seq)
        r += reward.absolute_distance_reward(result.output,x,256)
    r /= len(io_seqs)
    return r   
   
def ga_step(population):
    #print("ga step %s" % population)
    #print(population.problem.name)

    if population.problem.sync_to_database == True:
        population.refresh_from_db()
       
    if population.garunning == True:
        print("No step for population %s" % population)
        return
    population.garunning = True
    
    if population.max_generations != -1 and population.generation_count >= population.max_generations:
        print("Max generations reached for population %s" % population)
        print("saving stats")
        population.updateStats()       
        return False
    if population.max_individuals != -1 and population.individual_count >= population.max_individuals:
        print("Max individuals reached for population %s" % population)
        print("saving stats")
        population.updateStats()               
        return False

    if population.problem.sync_to_database == True:
        print("SYNC population %s" % population)
        if population.lock() == False:
            print("no ga step, population %s is locked" % population)
            return
    changecnt = mutate_and_crossover(population)
    population.individual_count += changecnt   
    population.generation_count += 1
    population.wasChanged = True
    if population.problem.sync_to_database == True:
        population.unlock()
        population.save()
    population.garunning = False
    #print("ga step finished %s" % population)
    return True   

    
    
mutate_code_evolution = Evolution(
    "mutate_code", 
    max_generations = -1,
    max_individuals = -1,
    max_populationsize = 100,
    referenceFunctionRate=0.7,
    max_code_length = 2000, 
    min_code_length = 50,
    max_steps = 1000,
    min_fitness_evaluation_per_individual = 1500,
    usePriorKnowledge = True,
    useP2P = True,  #warmup = True,
    sync_to_database = True,
)
@mutate_code_evolution.evolve      
def mutate_code_base(code_tokens):
  """Mutate a single code string.
  Args:
    code_tokens: A string/list/Individual of BF code chars. Must end with EOS
        symbol '_'.
    mutation_rate: Float between 0 and 1 which sets the probability of each char
        being mutated.
  Returns:
    An Individual instance containing the mutated code string.
  Raises:
    ValueError: If `code_tokens` does not end with EOS symbol.
  """
  #print("mutate_code_base")
  mutation_rate = 0.1
  cs = list(code_tokens)
  mutated = False
  
  for pos in range(len(cs)):
    if random.random() < mutation_rate:
      mutated = True
      new_char = random.choice(GENES)
      x = random.random()
      if x < 0.25 and pos != 0 and pos != len(cs) - 1:
        # Insertion mutation.
        if random.random() < 0.50:
          # Shift up.
          cs = cs[:pos] + [new_char] + cs[pos:-1]
        else:
          # Shift down.
          cs = cs[1:pos] + [new_char] + cs[pos:]
      elif x < 0.50:
        # Deletion mutation.
        if random.random() < 0.50:
          # Shift down.
          cs = cs[:pos] + cs[pos + 1:] + [new_char]
        else:
          # Shift up.
          cs = [new_char] + cs[:pos] + cs[pos + 1:]
      elif x < 0.75:
        # Shift rotate mutation (position invariant).
        if random.random() < 0.50:
          # Shift down.
          cs = cs[1:] + [cs[0]]
        else:
          # Shift up.
          cs = [cs[-1]] + cs[:-1]
      else:
        # Replacement mutation.
        cs = cs[:pos] + [new_char] + cs[pos + 1:]
  #print(len(code_tokens))
  #print(code_tokens)
  #print(len(cs))
  #print(cs)
  
  assert len(cs) == len(code_tokens)
  if mutated:
    #print("Mutated")
    return "".join(cs)
  else:
    return code_tokens

def mutate_code(code_tokens):
    tries = 10
    result = code_tokens
    while tries > 0:
        tries -= 1
        result =  mutate_code_base(code_tokens)
        #result = ''.join([i if ord(i) < 128 else '' for i in result])
        result = re.sub(GENES_REGEX,'',result)
        len_code_tokens = len(code_tokens)
        len_result = len(result)
        if (len_result <  (len_code_tokens/2)) or (len_result > (len_code_tokens*2)):
            #print("mutate_code bad result")
            mutate_code_evolution.reward(-100,100)
            mutate_code_evolution.save()
            continue
        break
    if len(result) < 3:
        return code_tokens
    return result
  

  
crossover_code_evolution = Evolution(
    "crossover_code", 
    max_generations = -1, 
    max_individuals = -1,
    max_populationsize = 100,
    referenceFunctionRate=0.7,    
    max_code_length = 2000, 
    min_code_length = 50,
    max_steps = 10000,
    min_fitness_evaluation_per_individual = 1500,
    usePriorKnowledge = True,
    useP2P = True, #warmup = True,
    sync_to_database = True,    
)
@crossover_code_evolution.evolve      
def crossover_code_base(parent1_parent2):
    #print("crossover_code_base")
    parent1, parent2 = parent1_parent2.split("_",1)
    max_parent, min_parent = ((parent1, parent2) if len(parent1) > len(parent2) else (parent2, parent1))
    pos = random.randrange(len(max_parent))
    #print("pos: %s " % pos)
    #print("max_parent len: %s " % len(max_parent))
    #print("min_parent len: %s " % len(min_parent))
    
    if pos >= len(min_parent):
        child1 = max_parent[:pos] + min_parent
        child2 = min_parent + max_parent[pos:]
    else:
        child1 = max_parent[:pos] + min_parent[pos:]
        child2 = min_parent[:pos] + max_parent[pos:]
    children = [x for x in [ child1, child2 ] if len(x) > 3]
    if len(children) == 0:
        return random.choice([ child1, child2 ])
        
    return random.choice(children)
   
def crossover_code(parent1, parent2):  
    tries = 10
    result = parent1
    while tries > 0:
        tries -= 1 
        parent1_parent2 ="%s_%s" % (parent1, parent2 )
        result = crossover_code_base(parent1_parent2)
        #result = ''.join([i if ord(i) < 128 else '' for i in result])
        result = re.sub(GENES_REGEX,'',result)
        len_min_parent = min([ len(parent1), len(parent2)])
        len_max_parent = max([ len(parent1), len(parent2)])
        len_result = len(result)
        if len_result <  len_min_parent/3 or len_result > len_max_parent*3:
            print("crossover_code_base bad result")
            #print("len_min_parent %s" % len_min_parent)
            #print("len_max_parent %s" % len_max_parent)
            #print("len_result %s" % len_result)
            crossover_code_evolution.reward(-100,100)
            crossover_code_evolution.save()
            continue
        break 
    if len(result) < 3:
        return parent2        
    return result
  
def adjust_max_codelength(population,individuals):
    #print("adjust_max_codelength")
    icodelength = [len(i.code) for i in individuals[0:int(len(individuals)/10)]]
    avg_codelength = sum(icodelength) /  len(icodelength)
    max_codelength = max(icodelength)
    min_codelength = min(icodelength)
    if  population.max_code_length ==  population.min_code_length:
        return 
    if avg_codelength * 3 > max_codelength :
        if population.evolved_max_code_length < max_codelength *2:
            if population.max_steps * 2 > population.evolved_max_code_length:
                population.evolved_max_code_length = int(population.evolved_max_code_length + 3)
                population.wasChanged = True
    else:
        population.evolved_max_code_length = int(population.evolved_max_code_length - 3 )
        population.wasChanged = True
        
    if population.evolved_max_code_length < population.min_code_length:
        print("evolution understepped min_code_length for pop %s" % population)
        population.evolved_max_code_length = population.min_code_length
        population.wasChanged = True
        
    if population.evolved_max_code_length > population.max_code_length:
        print("evolution overstepped max_code_length for pop %s" % population)
        population.evolved_max_code_length = population.max_code_length
        population.wasChanged = True
        
    if population.generation_count % 20 == 0:
        print("avg_codelength: %s" % avg_codelength)
        print("max_codelength: %s" % max_codelength)
        print("min_codelength: %s" % min_codelength)
        print("pop evolved_max_code_length %s " % population.evolved_max_code_length)  

def adjust_max_steps(population,individuals):
    #print("adjust_max_steps, select only best")
    isteps = [i.program_steps / i.execution_counter for i in individuals[0:int(len(individuals)/5)] if i.execution_counter != 0]
    #print(isteps)
    if len(isteps) ==0:
        print("not adjusting max steps, no ind has execution_counter")
        print(population)
        return
    avg_steps = sum(isteps) / len(isteps)
    max_steps = max(isteps)
    min_steps = min(isteps)
    #print("max_steps: %s" % max_steps)
    #print("min_steps: %s" % min_steps)
    #print("pop maxsteps %s " % population.max_steps)  
    if avg_steps * 3 > max_steps:
        if population.max_steps < max_steps * 2:
            population.max_steps = int(population.max_steps + 100)
            population.wasChanged = True
    else:
        population.max_steps = int(population.max_steps - 100 )
        population.wasChanged = True
    if population.max_steps < 1000:
        population.max_steps = 1000
    if population.max_steps > 100000:
        print("100k steps for %s" % population)
        population.max_steps = 100000
        
    if population.generation_count % 20 == 0:
        print("pop maxsteps %s " % population.max_steps)  
        print("avg_steps: %s" % avg_steps)

def mutate_and_crossover(population):
    individuals = population.getIndividuals(sorted=True)

    last_best_fitness = population.best_fitness
    last_best_code = population.best_code
    last_average_fitness =  population.average_fitness
    
    population.updateStats()       
    
    mutate_code_evolution_reward = 0
    crossover_code_evolution_reward = 0
    
    if population.best_code != last_best_code:
        if last_best_fitness != None:
            if population.best_fitness > last_best_fitness:
                print("new is better")
                mutate_code_evolution_reward += 1
     
    if last_average_fitness != None:
        if population.average_fitness > last_average_fitness:
            #print("better is better")
            crossover_code_evolution_reward += 1
            mutate_code_evolution_reward += 1
            
    
    mutate_code_evolution.reward(mutate_code_evolution_reward)
    crossover_code_evolution.reward(crossover_code_evolution_reward)
    mutate_code_evolution.save()
    crossover_code_evolution.save()
    
    adjust_max_steps(population,individuals)
    adjust_max_codelength(population,individuals)    
    
    
    if population.generation_count % 20 == 0:
        print("Problem '%s'" % (population.problem.name ))
        print("Generation '%s'" % (population.generation_count ))
        print("Individual count '%s'" % (population.individual_count ))
        print("Best Fitness: %s" % individuals[0].fitness)
        print("avg Fitness: %s" % population.average_fitness)
        x = bytearray(population.best_code,"UTF-8")
        if len(x) > 50:
            print("Best: %s" % x[:100])
        else:
            print("Best: %s" % x)
         
    len_individuals = len(individuals)
    for i in range(len_individuals-1,0,-1):
        individual = individuals[i]
        mutation_propability = 1.0 / len_individuals * i  # prop is reverse to fitness
        #print("mutation_propability %s" % mutation_propability)
        if random.random() < mutation_propability:
            #print("mutate")
            newcode = mutate_code(individual.code)
            individual.setCode(newcode)
            
    for i in range(1, len_individuals):
        crossover_propability = 1.0 / len_individuals * (len_individuals-i) # prop is fitness
        #print("crossover_propability %s" % crossover_propability)
        if random.random() < crossover_propability:
            #print("crossover")
            individual1 = individuals[i]
            j = random.randint(1,len_individuals-1)
            individual2 = individuals[j]
            newcode = crossover_code(individual1.code, individual2.code) 
            individuals[j].setCode(newcode)
           
    for i in range(1, len_individuals):
        
        individual = individuals[i]
        insert_delete_propability = 0.1
        
        len_individual_code = len(individual.code)
        while len_individual_code < individual.population.min_code_length:  # to short, fill
            pos = random.randint(0,(len_individual_code-1))
            newcode = individual.code[:pos] +  random.choice(GENES) + individual.code[pos:]
            individual.setCode( newcode)
            len_individual_code = len(individual.code)
            #print("to long")
            
        while len_individual_code > individual.population.max_code_length: # to long
            pos = random.randint(0,(len_individual_code-2))
            newcode = individual.code[:pos] + individual.code[pos+1:]
            individual.setCode( newcode)            
            len_individual_code = len(individual.code)
            #print("to short")
            
        if len_individual_code > individual.population.min_code_length and len_individual_code < individual.population.max_code_length:
            len_individual_code = len(individual.code)
            if len_individual_code < individual.population.evolved_max_code_length or random.random() < insert_delete_propability:
                pos = random.randint(0,(len_individual_code-1))
                newcode = individual.code[:pos] +  random.choice(GENES) + individual.code[pos:]
                individual.setCode( newcode)
            if len_individual_code > individual.population.min_code_length or random.random() < insert_delete_propability:
                pos = random.randint(0,(len_individual_code-2))
                newcode = individual.code[:pos] + individual.code[pos+1:]
                individual.setCode( newcode)            
            
    individuals[0].reset() # always reeval best
    
    if population.problem.useP2P == True and population.problem.usePriorKnowledge == True:
        individual_datas = p2pClient.p2pClient().getIndividuals(population.problem.name,2)
        print("individuals received from p2p for problem %s" % population.problem)
        #indsToReplace = 1
        for individual_data in individual_datas:
            localindividuals = [i for i in individuals if i.code == individual_data["code"]]
            if len(localindividuals) > 0:
                print("exists local")
            else:
                print("does not exist local")
                individuals[len_individuals-1].setCode(individual_data["code"])
                break

    return len([i for i in individuals if i.fitness == None])

    
    
# FIRST item has factor x times the propability of being picked
def randomchoiceLinear(listlength, factor):
    while True: 
        index = random.randint(0, listlength - 1)        
        factorForIndex =  1+((index) * ( (float(factor)-1) / (listlength) ) )
        prop = float(factorForIndex) / float(factor)
        if random.random() < prop:
            continue
        return index  
   
      
    
