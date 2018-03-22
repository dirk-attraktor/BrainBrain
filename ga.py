import random
from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Individual
from brainweb.models import Population
from brainweb.models import ReferenceFunction
import numpy as np
import reward

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
    'C', # NoOp
    'D', # NoOp
]
   
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
        self.usePriorKnowledge = usePriorKnowledge
        self.useP2P = useP2P

        problem.name = name
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
            self.problem.addPopulation(usePriorKnowledge,useP2P)
        self.selected_population = self.problem.populations.all()[0]    
        self.selected_population.min_fitness_evaluation_per_individual = min_fitness_evaluation_per_individual
        self.selected_population.initializeIndividuals(usePriorKnowledge, useP2P)
        self.selected_population.save()
        for individual in self.selected_population.getIndividuals():
            if len(individual.code) < 5:
                #print("need to init code")
                individual.code = create_first_individual()
                individual.save()
        self.warmup = warmup
          
    def evolve(self,function): 
        if self.problem.populations.count() == 0 and self.problem.default_max_populationsize != 0:
            self.problem.addPopulation(usePriorKnowledge,useP2P)
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
                #print("  referenceFunction calling")
                result = self.selected_individual.execute(args[0])
                
            if type(self.selected_individual) == Individual:
                #print("  selected_individual calling")
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
        self.usePriorKnowledge = usePriorKnowledge
        self.useP2P = useP2P
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
            self.problem.addPopulation(usePriorKnowledge,useP2P)
        self.selected_population = self.problem.populations.all()[0]    
        self.selected_population.initializeIndividuals(usePriorKnowledge,useP2P)
        for individual in self.selected_population.getIndividuals():
            if len(individual.code) < 5:
                #print("need to init code")
                individual.code = create_first_individual()
                individual.save()
        
        
    def regress(self, coderatingfunction,addpopulation = True, maxsteps = -1):
        if addpopulation == True:
            self.selected_population = self.problem.addPopulation(self.usePriorKnowledge,self.useP2P)
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
                    return 
                 #else:
                 #   print("GA step doned")
                 self.selected_individual = self.selected_population.getUnratedIndividual()
            self.selected_individual.execution_counter += 1 # dummy bcs we dont know what external function does
            fitness = coderatingfunction(self.selected_individual)
            self.selected_individual.addFitness(fitness)     
            if fitness == 1:
                print("Fitness 1 reached! regress %s Solved!" % self.problem.name)
                #print(brainfuck.evaluate(self.selected_individual.code,"hallo"))
                break            

    def save(self):
        self.selected_population.save()
        for key in self.loaded_referenceFunctions:
            self.loaded_referenceFunctions[key].save()
        self.problem.save()
    
   
def score_individual(individual,io_seqs):
   
    terminal_reward = 0.0
    reason = 'correct'
    lastoutout = ""
    for input_seq, output_seq in io_seqs:
      if input_seq == "" or output_seq == "":
        continue
      eval_result = individual.execute(bytearray(input_seq,"ASCII"))
      result, success = eval_result.output, eval_result.success
      if not success:
        print("NOT SUCCESSFULL")
        terminal_reward = -1
        reason = eval_result.failure_reason
        break
      else:
        terminal_reward += reward.absolute_distance_reward(result, bytearray(output_seq,"ASCII"), 256)
        if result == output_seq:
          None
          print("correct")
          #terminal_reward += self.correct_bonus  # Bonus for correct answer.
        elif reason == 'correct':
          reason = 'wrong'
    terminal_reward /= len(io_seqs)
    return terminal_reward   
   
def ga_step(population):
    #print("GA_STEP")
    #print(population.problem.name)

    if population.garunning == True:
        print("No step")
        return
    population.garunning = True
    if population.max_generations != -1 and population.generation_count >= population.max_generations:
        print("Max generations reached")
        return False
    if population.max_individuals != -1 and population.individual_count >= population.max_individuals:
        print("Max individuals reached")
        return False     

    if population.problem.sync_to_database == True:
        print("SYNC POP")
        if population.lock() == False:
            print("no ga step, population is locked")
            return         
    changecnt = mutate_and_crossover(population)
    population.individual_count += changecnt   
    population.generation_count += 1
    population.garunning = False
    if population.problem.sync_to_database == True:
        population.unlock()
  
    return True   

    
    
mutate_code_evolution = Evolution(
    "mutate_code", 
    max_generations = -1,
    max_individuals = -1,
    max_populationsize = 100,
    referenceFunctionRate=0.7,
    max_code_length = 100, 
    min_code_length = 10,
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
        result = ''.join([i if ord(i) < 128 else '' for i in result])
        len_code_tokens = len(code_tokens)
        len_result = len(result)
        if len_result <  len_code_tokens/2 or len_result > len_code_tokens*2:
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
    max_code_length = 100, 
    min_code_length = 10,
    max_steps = 1000,
    min_fitness_evaluation_per_individual = 1500,
    usePriorKnowledge = True,
    useP2P = True, #warmup = True,
    sync_to_database = True,    
)
@crossover_code_evolution.evolve      
def crossover_code_base(parent1_parent2):
    parent1, parent2 = parent1_parent2.split("_",1)
    max_parent, min_parent = ((parent1, parent2) if len(parent1) > len(parent2) else (parent2, parent1))
    pos = random.randrange(len(max_parent))
    if pos >= len(min_parent):
        child1 = max_parent[:pos]
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
        result = ''.join([i if ord(i) < 128 else '' for i in result])
        len_min_parent = min([ len(parent1), len(parent2)])
        len_max_parent = max([ len(parent1), len(parent2)])
        len_result = len(result)
        if len_result <  1 or len_result > len_max_parent*2:
            print("crossover_code_base bad result")
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

    if avg_codelength * 3 > max_codelength :
        if population.max_code_length < max_codelength *2:
            if population.max_steps * 2 > population.max_code_length:
                population.max_code_length = int(population.max_code_length + 3)
    else:
        population.max_code_length = int(population.max_code_length - 3 )
    if population.max_code_length < 30:
        population.max_code_length = 30
    if population.max_code_length > 1000:
        print("1k lines?")
        population.max_code_length = 1000
        
    if population.generation_count % 20 == 0:
        print("avg_codelength: %s" % avg_codelength)
        print("max_codelength: %s" % max_codelength)
        print("min_codelength: %s" % min_codelength)
        print("pop max_code_length %s " % population.max_code_length)  

def adjust_max_steps(population,individuals):
    #print("adjust_max_steps, select only best")
    isteps = [i.step_counter / i.execution_counter for i in individuals[0:int(len(individuals)/5)]]
    #print(isteps)
    avg_steps = sum(isteps) / len(isteps)
    max_steps = max(isteps)
    min_steps = min(isteps)
    #print("max_steps: %s" % max_steps)
    #print("min_steps: %s" % min_steps)
    #print("pop maxsteps %s " % population.max_steps)  
    if avg_steps * 3 > max_steps:
        if population.max_steps < max_steps * 2:
            population.max_steps = int(population.max_steps + 10)
    else:
        population.max_steps = int(population.max_steps - 10 )
    if population.max_steps < 500:
        population.max_steps = 500
    if population.max_steps > 100000:
        print("100k steps?")
        population.max_steps = 100000
        
    if population.generation_count % 20 == 0:
        print("pop maxsteps %s " % population.max_steps)  
        print("avg_steps: %s" % avg_steps)

def mutate_and_crossover(population):

    individuals = population.getIndividuals()
    individuals.sort(key=lambda x:x.code_length,reverse = False)
    individuals.sort(key=lambda x:x.step_counter,reverse = False)
    individuals.sort(key=lambda x:x.fitness,reverse = True)
    average_fitness = sum([i.fitness for i in individuals]) / len(individuals)
    
    last_best_fitness = population.best_fitness
    last_best_code = population.best_code
    last_average_fitness =  population.average_fitness
    
    best_individual = individuals[0]
    
    mutate_code_evolution_reward = 0
    crossover_code_evolution_reward = 0
    
    if best_individual.code != last_best_code:
        if last_best_fitness != None:
            if best_individual.fitness > last_best_fitness:
                print("new is better")
                f=open("track_top_individuals.csv","ab")
                f.write(("%s_%s__" % (last_best_code,best_individual.code)).encode('utf-8'))
                f.flush()
                f.close()
                mutate_code_evolution_reward += 1
            
        population.best_fitness = best_individual.fitness
        population.best_code = best_individual.code
     
    if last_average_fitness != None:
        if average_fitness > last_average_fitness:
            #print("better is better")
            crossover_code_evolution_reward += 1
            mutate_code_evolution_reward += 1
            
    population.average_fitness = average_fitness
    
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
        print("avg Fitness: %s" % average_fitness)
        #print("mutate_code_evolution_reward: %s" % mutate_code_evolution_reward)
        #print("crossover_code_evolution_reward: %s" % crossover_code_evolution_reward)
        x = bytearray(best_individual.code,"UTF-8")
        if len(x) > 50:
            print("Best: %s" % x[:100])
        else:
            print("Best: %s" % x)
         
    l = len(individuals)
    for i in range(l-1,0,-1):
        individual = individuals[i]
        mutation_propability = 1.0 / l * i  # prop is reverse to fitness
        #print("mutation_propability %s" % mutation_propability)
        if random.random() < mutation_propability:
            #print("mutate")
            newcode = mutate_code(individual.code)
            individual.setCode(newcode)
            
    for i in range(1, l):
        crossover_propability = 1.0 / l * (l-i) # prop is fitness
        #print("crossover_propability %s" % crossover_propability)
        if random.random() < crossover_propability:
            #print("crossover")
            individual1 = individuals[i]
            j = random.randint(1,l-1)
            individual2 = individuals[j]
            newcode = crossover_code(individual1.code, individual2.code) 
            individuals[j].setCode(newcode)
           
    for i in range(1, l):
        individual = individuals[i]
        insert_delete_propability = 0.1
        if len(individual.code) > individual.population.max_code_length or random.random() < insert_delete_propability:
            pos = random.randint(0,(len(individual.code )-2))
            newcode = individual.code[:pos] + individual.code[pos+1:]
            individual.setCode( newcode)
            
        if len(individual.code) < individual.population.min_code_length or random.random() < insert_delete_propability:
            pos = random.randint(0,(len(individual.code )-1))
            newcode = individual.code[:pos] +  random.choice(GENES) + individual.code[pos:]
            individual.setCode( newcode)
           
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
   
def _make_even(n):
  """Return largest even integer less than or equal to `n`."""
  return (n >> 1) << 1
   
def reward_conversion(reward):
  """Convert real value into positive value."""
  if reward <= 0:
    return 0.05
  return reward + 0.05

def roulette_selection(individuals, k):
  """Select `k` individuals with prob proportional to fitness.
  Each of the `k` selections is independent.
  Warning:
    The roulette selection by definition cannot be used for minimization
    or when the fitness can be smaller or equal to 0.
  Args:
    population: A list of Individual objects to select from.
    k: The number of individuals to select.
  Returns:
    A list of selected individuals.
  """
  fitnesses = np.asarray(
      [reward_conversion(ind.fitness)
       for ind in individuals])
  assert np.all(fitnesses > 0)

  sum_fits = fitnesses.sum()
  chosen = [None] * k
  for i in range(k):
    u = random.random() * sum_fits
    sum_ = 0
    for ind, fitness in zip(individuals, fitnesses):
      sum_ += fitness
      if sum_ > u:
        chosen[i] = ind
        break
    if not chosen[i]:
      chosen[i] = individuals[-1]

  return chosen        
                
def mutate_codelength(individual):  
    
    if random.random() < 0.1:
        
        while len(individual.code) < 2:
            individual.code += random.choice(GENES)
            
        while len(individual.code) > individual.population.max_code_length:
            pos = random.randint(0,(len(individual.code )-2))
            newcode = individual.code[:pos] + individual.code[pos+1:]
            individual.setCode( newcode)
            
        if len(individual.code) < individual.population.min_code_length:
            code = individual.code
            #print("change to min codelength")
            while len(code) < individual.population.min_code_length:
                pos = random.randint(0,(len(code )-1))
                newcode = code[:pos] +  random.choice(GENES) + code[pos:]
                code = newcode
            individual.setCode( code)
            
        if len(individual.code) < individual.population.max_code_length:
            pos = random.randint(0,(len(individual.code )-1))
            newcode = individual.code[:pos] +  random.choice(GENES) + individual.code[pos:]
            individual.setCode( newcode)
      
def mutate_and_crossover_old(population):
    #print("mutate_and_crossover")
    """Take a generational step over a population.
      Transforms population of parents into population of children (of the same
      size) via crossover mating and then mutation on the resulting children.
      Args:
        population: Parent population. A list of Individual objects.
        mutation_rate: Probability of mutation. See `mutate_single`.
        crossover_rate: Probability that two parents will mate.
      Returns:
        Child population. A list of Individual objects.
      """
    mutation_rate = 0.3
    crossover_rate = 0.5

    individuals = population.getIndividuals()
    individuals.sort(key=lambda x:x.code_length,reverse = False)
    individuals.sort(key=lambda x:x.fitness,reverse = True)
    avgFitness = sum([i.fitness for i in individuals]) / len(individuals)
    mutate_code_evolution_reward = None
    crossover_code_evolution_reward = None
    try:
        mutate_code_evolution_reward = avgFitness - population.lastAvgFitness  
        mutate_code_evolution.reward(mutate_code_evolution_reward)
        mutate_code_evolution.save()
        #print("delta gFitness: %s" % diff)
    except Exception as e:
        #print("no last avg fitness")
        population.lastAvgFitness  = avgFitness
        
    parent_fitnesses = [i for i in individuals if i.parent_fitness != None and i.fitness != None]
    if len(parent_fitnesses) > 0:
        avg_parent_fitness = sum([i.parent_fitness for i in parent_fitnesses]) / len(parent_fitnesses)
        avg_current_fitness = sum([i.fitness for i in parent_fitnesses]) / len(parent_fitnesses)
        crossover_code_evolution_reward = avg_current_fitness - avg_parent_fitness
        if crossover_code_evolution_reward > 0:
            crossover_code_evolution.reward(crossover_code_evolution_reward)
        else:
            crossover_code_evolution.reward(0)
        crossover_code_evolution.save()        
            
    #print("bere")
    #print(individuals[0].fitness)
    #print(individuals[1].fitness)
    #print(individuals[2].fitness)
    #print(individuals[3].fitness)
    best = individuals[0].code
    #best1 = individuals[1].code
    #best2 = individuals[3].code
    if population.generation_count % 20 == 0:
        
        print("Problem '%s'" % (population.problem.name ))
        print("Generation '%s'" % (population.generation_count ))
        print("Individual count '%s'" % (population.individual_count ))
        print("Best Fitness: %s" % individuals[0].fitness)
        print("avg Fitness: %s" % avgFitness)
        print("mutate_code_evolution_reward: %s" % mutate_code_evolution_reward)
        print("crossover_code_evolution_reward: %s" % crossover_code_evolution_reward)
        x = bytearray(best,"UTF-8")
        if len(x) > 50:
            print("Best: %s" % x[:100])
        else:
            print("Best: %s" % x)
            
    adjust_max_steps(population,individuals)
    adjust_max_codelength(population,individuals)
    #mutate_code_problem.selected_individual = None # reset here
    
    
    individuals = roulette_selection(individuals,99)

    #print(individuals[2].fitness)
    #print(individuals[3].fitness)
    #print(individuals)
    #print(len(individuals))
    #print(_make_even(len(individuals)))
    #print(range(0, _make_even(len(individuals)), 2))
    #random.shuffle(individuals)
    updatecnt = 0
    mutatecnt = 0
    for i in range(0, _make_even(len(individuals)), 2):
        if population.max_individuals > -1:
            if population.individual_count + updatecnt + 2  > population.max_individuals:
                break
        p1 = individuals[i].code
        p2 = individuals[i + 1].code

        if random.random() < crossover_rate:
            if individuals[i].fitness != None and individuals[i+1].fitness != None:
                individuals[i].parent_fitness = sum([individuals[i].fitness,individuals[i+1].fitness]) / 2 
                individuals[i+1].parent_fitness = individuals[i].parent_fitness
            p1_p2 = crossover_code("%s_%s" % (p1, p2))
            p1_p2 = ''.join([i if ord(i) < 128 else '' for i in p1_p2])
            if p1_p2.find("_") == -1:   
                #print("crossover failed")
                crossover_code_evolution.reward(-100,100)
                crossover_code_evolution.save()
                individuals[i].parent_fitness = None
                individuals[i+1].parent_fitness = None
                #p1,p2 = p1_p2, p1_p2
                #keep old inds
            else:
                p1a,p2a = p1_p2.split("_",1)
        else:
            individuals[i].parent_fitness = None
            
        while len(p1) < individuals[i].population.min_code_length: 
            p1 += random.choice(GENES)
        while len(p2) < individuals[i+1].population.min_code_length: 
            p2 += random.choice(GENES) 
            
        c1 = mutate_code(p1)
        c2 = mutate_code(p2)
        c1 = ''.join([i if ord(i) < 128 else '' for i in c1])
        c2 = ''.join([i if ord(i) < 128 else '' for i in c2])
        
        if len(c1) < individuals[i].population.min_code_length or len(c2) < individuals[i+1].population.min_code_length:
            #print("out of bound bad reward")
            mutate_code_evolution.reward(-100,100)
            mutate_code_evolution.save()
        
        while len(c1) < individuals[i].population.min_code_length: 
            c1 += random.choice(GENES)
        while len(c2) < individuals[i+1].population.min_code_length: 
            c2 += random.choice(GENES)        
        
        
        if individuals[i].setCode(c1) == True:
            mutatecnt += 1
        if individuals[i + 1].setCode(c2) == True:
            mutatecnt += 1
            
        mutate_codelength(individuals[i])
        
        updatecnt += 2
        #print("here")
        #print(individuals[i])
    if mutatecnt == 0 and population.individual_count  <  population.max_individuals:
        print("no mutation happend, bad reward mutation function")
        mutate_code_evolution.reward(-100,50)
        mutate_code_evolution.save()
        
    individuals[0].setCode(best)
    #individuals[20].setCode(best1)
    #individuals[30].setCode(best2)
    return  updatecnt
    
    