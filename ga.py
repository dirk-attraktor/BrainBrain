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
   
   

class Evolution():
    
    def __init__(self,
            name, 
            description = "",
            referenceFunctionRate = 1, 
            max_generations = -1, 
            max_individuals = 10,
            max_populationsize = 10000, 
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
        self.referenceFunctionRate = referenceFunctionRate
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
        self.selected_population.initializeIndividuals()
                   

          
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
                x = self.selected_individual.execute(args[0])
                #print(x)
                return  x
            if type(self.selected_individual) == Individual:
                #print("  selected_individual calling")
                x = ''.join(chr(i) for i in self.selected_individual.execute(args[0]).output )
                #print(x)
                return x
                
        return replacementFunction       
    

    
    def reward(self,value):
        #print("REWARD")
        self.selected_individual.addFitness(value)
        self.selected_individual = None
        individuals = self.selected_population.getIndividuals() 
        
        underrated = [i for i in individuals if i.fitness_evalcount < self.selected_population.min_fitness_evaluation_per_individual]
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
        
    def regress(self, coderatingfunction,addpopulation = True, maxsteps = -1):
        if addpopulation == True:
            self.selected_population = self.problem.addPopulation(self.usePriorKnowledge,self.useP2P)

        step = 0
        while step < maxsteps or maxsteps == -1:
            step += 1
            if step % 100 == 0:
                print("Regess step %s" % step)
            self.selected_individual = self.selected_population.getUnratedIndividual()
            if self.selected_individual == None:
                 if ga_step(self.selected_population) == False:
                    print("regression finised, ga_step returned false")
                    return 
                 else:
                    print("GA step doned")
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
    print("GA_STEP")
    print(population.problem.name)
    if population.garunning == True:
        print("No step")
        return
    population.garunning = True
    if population.max_generations != -1 and population.generation_count >= population.max_generations:
        print("Max generations reached")
        return False
    changecnt = mutate_and_crossover(population)
    if changecnt == 0:
        print("Max individuals reached")
        return False
    population.individual_count += changecnt   
    population.generation_count += 1
    population.garunning = False
    return True   

def mutate_code_base(code_tokens, mutation_rate):
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
   
    
mutate_code_evolution = Evolution("mutate_code", max_generations = -1, max_individuals = -1,max_populationsize = 100,referenceFunctionRate=0.1)
@mutate_code_evolution.evolve   
def mutate_code(code_tokens):
    return mutate_code_base(code_tokens, mutation_rate=0.1)
    
def crossover_code(parent1, parent2):
  """Performs crossover mating between two code strings.
  Crossover mating is where a random position is selected, and the chars
  after that point are swapped. The resulting new code strings are returned.
  Args:
    parent1: First code string.
    parent2: Second code string.
  Returns:
    A 2-tuple of children, i.e. the resulting code strings after swapping.
  """
  max_parent, min_parent = (
      (parent1, parent2) if len(parent1) > len(parent2)
      else (parent2, parent1))
  pos = random.randrange(len(max_parent))
  if pos >= len(min_parent):
    child1 = max_parent[:pos]
    child2 = min_parent + max_parent[pos:]
  else:
    child1 = max_parent[:pos] + min_parent[pos:]
    child2 = min_parent[:pos] + max_parent[pos:]
  return child1, child2

def _make_even(n):
  """Return largest even integer less than or equal to `n`."""
  return (n >> 1) << 1

# FIRST item has factor x times the propability of being picked
def randomchoiceLinear(listlength, factor):
    while True: 
        index = random.randint(0, listlength - 1)        
        factorForIndex =  1+((index) * ( (float(factor)-1) / (listlength) ) )
        prop = float(factorForIndex) / float(factor)
        if random.random() < prop:
            continue
        return index  
        
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
             
def adjust_max_codelength(population,individuals):
    #print("adjust_max_codelength")
    icodelength = [len(i.code) for i in individuals[0:int(len(individuals)/10)]]
    avg_codelength = sum(icodelength) /  len(icodelength)
    max_codelength = max(icodelength)
    min_codelength = min(icodelength)
    print("avg_codelength: %s" % avg_codelength)
    #print("max_codelength: %s" % max_codelength)
    #print("min_codelength: %s" % min_codelength)
    if avg_codelength * 3 > max_codelength :
        if population.max_code_length < max_codelength *2:
            if population.max_steps * 2 > population.max_code_length:
                population.max_code_length = int(population.max_code_length + 1)
    else:
        population.max_code_length = int(population.max_code_length - 1 )
    if population.max_code_length < 30:
        population.max_code_length = 30
    if population.max_code_length > 1000:
        print("1k lines?")
        population.max_code_length = 1000
        
    print("pop max_code_length %s " % population.max_code_length)  
     
def adjust_max_steps(population,individuals):
    #print("adjust_max_steps, select only best")
    isteps = [i.step_counter / i.execution_counter for i in individuals[0:int(len(individuals)/5)]]
    #print(isteps)
    avg_steps = sum(isteps) / len(isteps)
    max_steps = max(isteps)
    min_steps = min(isteps)
    print("avg_steps: %s" % avg_steps)
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
        
    print("pop maxsteps %s " % population.max_steps)  
    
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
            print("change to min codelength")
            while len(code) < individual.population.min_code_length:
                pos = random.randint(0,(len(code )-1))
                newcode = code[:pos] +  random.choice(GENES) + code[pos:]
                code = newcode
            individual.setCode( code)
            
        if len(individual.code) < individual.population.max_code_length:
            pos = random.randint(0,(len(individual.code )-1))
            newcode = individual.code[:pos] +  random.choice(GENES) + individual.code[pos:]
            individual.setCode( newcode)
        
def mutate_and_crossover(population):
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

    try:
        diff = avgFitness - population.lastAvgFitness  
        mutate_code_evolution.reward(diff)
        mutate_code_evolution.save()
        print("delta gFitness: %s" % diff)
    except Exception as e:
        print("no last avg fitness")
        population.lastAvgFitness  = avgFitness
        
    #print("bere")
    #print(individuals[0].fitness)
    #print(individuals[1].fitness)
    #print(individuals[2].fitness)
    #print(individuals[3].fitness)
    best = individuals[0].code
    #best1 = individuals[1].code
    #best2 = individuals[3].code
    print("Best: %s" % bytearray(best,"UTF-8"))
    print("BestFitness: %s" % individuals[0].fitness)
    print("avgFitness: %s" % avgFitness)
    
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
    for i in range(0, _make_even(len(individuals)), 2):
        if population.max_individuals > -1:
            if population.individual_count + updatecnt + 2  > population.max_individuals:
                break
        #print(i)
        p1 = individuals[i].code
        p2 = individuals[i + 1].code

        if random.random() < crossover_rate:
            p1, p2 = crossover_code(p1, p2)
        c1 = mutate_code(p1)
        c2 = mutate_code(p2)
        c1 = ''.join([i if ord(i) < 128 else '' for i in c1])
        c2 = ''.join([i if ord(i) < 128 else '' for i in c2])
        
        if len(c1) < 5 or len(c2) < 5:
            #print("out of bound bad reward")
            mutate_code_evolution.reward(-99)
            mutate_code_evolution.save()
        
        while len(c1) < individuals[i].population.min_code_length: 
            c1 += random.choice(GENES)
        while len(c2) < individuals[i+1].population.min_code_length: 
            c2 += random.choice(GENES)        
        
            
        individuals[i].setCode(c1)
        mutate_codelength(individuals[i])
        individuals[i + 1].setCode(c2)
        updatecnt += 2
        #print("here")
        #print(individuals[i])
    individuals[0].setCode(best)
    #individuals[20].setCode(best1)
    #individuals[30].setCode(best2)
    return  updatecnt
    
    