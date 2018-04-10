from django.db import models
import random
from django.db.models import F, Q
import time
import requests
import json
import p2pClient
from django.db import connection
import datetime
from django.utils import timezone
import traceback
from .brainfuckC import BrainfuckC
REFRESH_REFERENCE_FUNCTION_FROM_DB = True

brainfuckCinstance = BrainfuckC.BrainfuckC()

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


def lock(modelobject):
    lockid = random.randint(0,9999999)
    updated = modelobject.objects.filter(pk=modelobject.id,lock="").update(lock = lockid)
    if updated == 1:
        return lockid
    return None

class Lock(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    population_id = models.CharField( max_length=200,default="")

    
class Peer(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    lastfail  = models.DateTimeField(null=True,blank=True,default=None)  
    host     = models.CharField( max_length=200,default="")
    port     = models.IntegerField(default=4141)
    supernode = models.BooleanField(default=False)
    failcount = models.IntegerField(default=0)
    
    def __str__(self):
        return "Peer %s:%s supernode:%s" %(self.host,self.port,self.supernode) 
        
class Problem(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    name     = models.CharField( max_length=200,default="", unique=True)
    description = models.CharField( max_length=200,default="")

    usePriorKnowledge = models.BooleanField(default=False)
    useP2P = models.BooleanField(default=False)

    default_max_populationsize =  models.IntegerField(default = 100)  # max number of living individuals
    default_max_individuals  = models.IntegerField(default = -1)  # total number of individuals to generate during evolution, or -1 for unlimited, evolution will stop and return null for new unrated individuals at this point
    default_max_generations =  models.IntegerField(default = -1) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_max_code_length =  models.IntegerField(default = 20) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_min_code_length =  models.IntegerField(default = 20) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_max_steps =  models.IntegerField(default = -1) 
    default_min_fitness_evaluation_per_individual =  models.IntegerField(default = -1) 
 
    sync_to_database = models.BooleanField(default=False)

    # -> populations
    # -> referencefunctions
      
    class Meta:
        ordering = ["-updated"]

    def getReferenceFunction(self,name):
        try:
            return self.referencefunctions.get(name=name)
        except Exception as e:
            print("ReferenceFunction Exception")
            print(e)
            return None
        
    def getTopIndividuals(self,limit = 10):
        r = []
        for p in self.populations.all():    
            i = p.individuals.filter(~Q(fitness = None))[0:limit]
            if i.count() > 0:
                [r.append(x) for x in i]
        return sorted(r,key= lambda x:x.fitness,reverse = True)[0:limit]
       
    def addPopulation(self):
        cnt = self.populations.count()
        while cnt > 200:
            self.populations.all()[cnt-1:cnt][0].delete()
            
            cnt = self.populations.count()
            
        population = Population()
        population.problem = self
        population.max_populationsize = self.default_max_populationsize
        population.max_individuals = self.default_max_individuals
        population.max_generations = self.default_max_generations
        population.max_code_length = self.default_max_code_length
        population.evolved_max_code_length = self.default_min_code_length
        population.min_code_length = self.default_min_code_length
        population.max_steps = self.default_max_steps
        population.min_fitness_evaluation_per_individual = self.default_min_fitness_evaluation_per_individual
        population.save()
        population.initializeIndividuals()
        return population
        
            
    # FIRST item has factor x times the propability of being picked
    def randomchoiceLinear(self,listlength, factor):
        while True: 
            index = random.randint(0, listlength - 1)        
            factorForIndex =  1+((index) * ( (float(factor)-1) / (listlength) ) )
            prop = float(factorForIndex) / float(factor)
            if random.random() < prop:
                continue
            return index    
            
    def getP2PIndividuals(self,limit = 9,depth=3):
        if limit < 2:
            limit = 2
        result = []
        for p in self.populations.all()[0:depth]:
            individuals = p.individuals.all()
            l = len(individuals)
            if l == 0:
                continue
            tmpresult = [individuals[0]]
            tries = 0
            while len(tmpresult) < int(limit/depth) and tries < limit:
                tries += 1
                index = self.randomchoiceLinear(l,30)
                individual = individuals[index]
                if individual not in tmpresult and individual.fitness_evalcount > 0:
                    tmpresult.append(individual)
            result.extend(tmpresult)        
        return result 
   
    def save(self):  
        #print("save called in Problem")
        super(type(self), self).save()
       
    def __str__(self):
        return "Problem: %s" % self.name
    
    
    
class Population(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='populations')
    
    max_populationsize =  models.IntegerField(default = 100)  # max number of living individuals
    max_individuals  = models.IntegerField(default = -1)  # total number of individuals to generate during evolution, or -1 for unlimited, evolution will stop and return null for new unrated individuals at this point
    max_generations =  models.IntegerField(default = -1) # total number of evolutionary steps during evolution, or -1 for unlimited

    min_code_length =  models.IntegerField(default = 20) #unchangeable limits
    max_code_length =  models.IntegerField(default = 20)
    max_steps  =  models.IntegerField(default = 20) # TODO
    min_fitness_evaluation_per_individual  =  models.IntegerField(default = 1)
    
    # evolable limits
    evolved_max_code_length =  models.IntegerField(default = 20)
    
    
    # stats
    generation_count =  models.IntegerField(default = 0)
    individual_count =  models.IntegerField(default = 0)
    
    # set right before ga_step in mutate_and_crossover, after all inds are evaluated, via self.updateStats()
    best_fitness =  models.FloatField(default = None,blank=True,null=True)
    best_code    = models.CharField( max_length=200000,default="")
    average_fitness = models.FloatField(default = None,blank=True,null=True)
    average_program_steps = models.FloatField(default = 0)
    average_memory_usage = models.FloatField(default = 0)
    average_inputbuffer_usage = models.FloatField(default = 0)
    average_execution_time = models.FloatField(default = 0)
        
    # -> individuals
     
    class Meta:
        ordering = ["-created"]
   
    def __init__(self,*args,**kwargs):
        self.wasChanged = False
        self.individual_cache = None#
        self.garunning = False
        super(type(self), self).__init__(*args,**kwargs)
 
   
    def lock(self):
        try:
            lock = Lock.objects.get(population_id = self.id)
            if lock.updated <  timezone.now()-datetime.timedelta(minutes=10):
                print("%s lock has expired")
                lock.save()
                return True
            print("%s is locked, not locking again" % self)
            return False
        except Exception as e:
            print("%s not locked, locking: %s" % (self,e))
            l = Lock()
            l.population_id = self.id
            l.save()
            return True
            
    def unlock(self):
        try:
            locks = Lock.objects.filter(population_id = self.id)
            if len(locks)> 0:
                for lock in locks:
                    lock.delete()
                print("%s unlocked" % self)
            else:
                print("%s not locked, not unlocking" % (self))
        except Exception as e:
            print("%s not locked, not unlocking: %s" % (self,e))
            
    def isLocked(self):
        try:
            lock = Lock.objects.get(population_id = self.id)
            return True
        except Exception as e:
            print("%s is not locked: %s" % (self,e))
            return False
            
    def initializeIndividuals(self):
        diff =  self.max_populationsize - self.individuals.count()
        while diff < 0: 
            print("To many individuals found, killing")
            random.choice(self.individuals.all()).delete()
            diff =  self.max_populationsize - self.individuals.count()  
            
            
        if diff > 0 and  self.problem.usePriorKnowledge == True:
            individuals = self.problem.getP2PIndividuals(16,4)
            for oldindividual in individuals:
                individual = Individual()
                individual.population = self
                individual.code = oldindividual.code
                individual.code_length = oldindividual.code_length
                individual.save()
                print("FROM OLD IND")
                self.individual_count += 1
                diff -= 1
                if diff == 0:
                    break
                    
        if diff > 0 and self.problem.usePriorKnowledge == True and self.problem.useP2P == True:
            individual_datas = p2pClient.p2pClient().getIndividuals(self.problem.name,2)
            print("individuals received from p2p for problem %s" % self.problem)
            #indsToReplace = 1
            for individual_data in individual_datas:
                localindividuals = self.individuals.filter(code=individual_data["code"])
                if localindividuals.count() > 0:
                    print("exists local")
                    localindividual = random.choice(localindividuals)
                    localindividual.fitness_evalcount = (localindividual.fitness_evalcount + individual_data["fitness_evalcount"]) /2
                    localindividual.fitness_sum = ( localindividual.fitness_sum + individual_data["fitness_sum"] ) / 2 
                else:
                    print("does not exist local")
                    individuals = self.individuals.all()
                    if diff > 0:
                        individual = Individual()
                        individual.population = self
                        individual.code = individual_data["code"] # 
                        individual.fitness_evalcount = 0 # individual_data["fitness_evalcount"]
                        individual.fitness_sum = 0       # individual_data["fitness_sum"]
                        individual.save()
                        diff -= 1
                        if diff == 0:
                            break

        while diff > 0:
            individual = Individual()
            individual.population = self
            individual.setCode("".join([random.choice(GENES) for _ in range(0,self.min_code_length)]))
            individual.save()
            self.individual_count += 1
            diff -= 1
        self.wasChanged = True 
        
    def getIndividuals(self, sorted = False):
        #print("getIndividuals")
        if self.individual_cache == None or self.problem.sync_to_database == True:
            self.individual_cache = [i for i in self.individuals.all()]#
        if sorted == True:
            self.individual_cache.sort(key=lambda x:( float("-inf") if x.fitness is None else x.fitness, x.average_inputbuffer_usage,  -x.code_length, -x.average_execution_time  ), reverse = True)
        return self.individual_cache
        
    def getUnratedIndividual(self):
        #print("getUnratedIndividual")
        if self.problem.sync_to_database == True:
            unfit = self.individuals.filter(Q(fitness = None) | Q(fitness_evalcount__lt = self.min_fitness_evaluation_per_individual))
            c = unfit.count()
            if c > 0:
                try:
                    i = unfit[random.randint(0,c-1)]
                    #print("quickr")
                    return i
                except:
                    print("errror")
        else: # local search
            inds = self.getIndividuals()
            len_inds = len(inds)
            startposition = random.randint(0,len_inds-1)
            position = startposition
            while True:
                ind = inds[position]
                if ind.fitness == None or ind.fitness_evalcount < self.min_fitness_evaluation_per_individual:
                    return ind           
                position = (position + 1) % len_inds
                if position == startposition:
                    break
        return None 
            
    def hasUnratedIndividual(self):
        #print("hasUnratedIndividual")
        if self.problem.sync_to_database == True:
            unfit = self.individuals.filter(Q(fitness = None) | Q(fitness_evalcount__lt = self.min_fitness_evaluation_per_individual))
            c = unfit.count()
            if c > 0:
                return True
        else: # local search
            inds = self.getIndividuals()
            len_inds = len(inds)
            startposition = random.randint(0,len_inds-1)
            position = startposition
            while True:
                ind = inds[position]
                if ind.fitness == None or ind.fitness_evalcount < self.min_fitness_evaluation_per_individual:
                    return True
                position = (position + 1) % len_inds
                if position == startposition:
                    break
        return False             
            
    def getBestIndividual(self):
        if self.individual_cache == None or self.problem.sync_to_database == True:
            self.individual_cache = [i for i in self.individuals.all()]
        try:
            return [i for i in self.individual_cache if i.fitness != None][0]
        except:
            return None
            
    def updateStats(self):
        self.wasChanged = True
        individuals = self.getIndividuals(sorted=True)
        self.best_fitness = individuals[0].fitness
        self.best_code = individuals[0].code
            
        sum_average_fitness = 0
        sum_average_program_steps = 0
        sum_average_memory_usage = 0
        sum_average_inputbuffer_usage = 0
        sum_average_execution_time = 0
        
        l = len(individuals)
        
        if l > 0:   
            fitcnt = 0
            for i in individuals:
                if i.fitness != None:
                    sum_average_fitness += i.fitness
                    fitcnt += 1
                sum_average_program_steps += i.average_program_steps 
                sum_average_memory_usage += i.average_memory_usage 
                sum_average_inputbuffer_usage += i.average_inputbuffer_usage 
                sum_average_execution_time += i.average_execution_time 
            
            self.average_fitness = sum_average_fitness / fitcnt
            self.average_program_steps = sum_average_program_steps / l
            self.average_memory_usage = sum_average_memory_usage / l
            self.average_inputbuffer_usage = sum_average_inputbuffer_usage / l
            self.average_execution_time = sum_average_execution_time / l
        else:
            self.average_fitness = 0
            self.average_program_steps = 0
            self.average_memory_usage = 0
            self.average_inputbuffer_usage = 0
            self.average_execution_time = 0
        if self.problem.sync_to_database == True:
            self.save()
     
    def save(self):
        #print("Save on Population for problem %s" % self.problem)
        if self.individual_cache != None:
            for i in self.individual_cache:
                i.save()
        if self.wasChanged == True or self.id == None:
            super(type(self), self).save()
            self.wasChanged = False
        
    def __str__(self):
        return "Population: %s" % self.id
    
    
        
class Individual(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    population = models.ForeignKey(Population, on_delete=models.CASCADE, related_name='individuals')

    code     = models.CharField( max_length=200000,default=".")
    code_length =  models.FloatField(default = 10)

    execution_counter = models.FloatField(default = 0) # nr of executions of this code version
    
    fitness =  models.FloatField(default = None,blank=True,null=True)
    fitness_sum =  models.FloatField(default = 0)
    fitness_evalcount =  models.FloatField(default = 0)
    
    program_steps = models.FloatField(default = 0) # nr of executions of this code version
    memory_usage = models.FloatField(default = 0) # nr of executions of this code version
    inputbuffer_usage = models.FloatField(default = 0) # 0 to 1 percent of input bytes used
    execution_time = models.FloatField(default = 0) # total execution time
    output_size = models.FloatField(default = 0) # total execution time
    input_size = models.FloatField(default = 0) # total execution time
    
    average_program_steps = models.FloatField(default = 0) 
    average_memory_usage = models.FloatField(default = 0) 
    average_inputbuffer_usage = models.FloatField(default = 0) 
    average_execution_time = models.FloatField(default = 0) 
    average_output_size = models.FloatField(default = 0) 
    average_input_size = models.FloatField(default = 0) 
    
    parent_fitness =  models.FloatField(default = None,blank=True,null=True) # in case of crossover, set this to max parent fitness, used to track crossover quality
    
    def __init__(self,*args,**kwargs):
        self.wasChanged = False
        super(type(self), self).__init__(*args,**kwargs)

    
    class Meta:
        ordering = ["-fitness", "-average_inputbuffer_usage","code_length","average_execution_time"]
        
    def addFitness(self, value, evaluations = 1):
        self.wasChanged = True
        self.fitness_sum += value
        self.fitness_evalcount += evaluations
        self.fitness = self.fitness_sum / self.fitness_evalcount
        if self.population.problem.sync_to_database == True:
            #print("Individual.addFitness")
            self.save()
      
    def execute(self, input):
        #print("execute ind")
        brainfuckCinstance.load(code = self.code, max_steps = self.population.max_steps, max_memory = 100000, clear_memory = True, output_memory = False, preload_memory = "")
        result = brainfuckCinstance.run(input, clear_memory = True)
        #print(input)
        #print(result.output)
        
        #ExecutionResult = namedtuple('ExecutionResult',[
        #    "program_steps", 
        #    "memory_usage",
        #    "inputbuffer_usage",
        #    "output_size",
        #    "output",
        #    "memory_size",
        #    "memory",
        #    "execution_time",
        #])
        
        inputlength = len(input)
        self.execution_counter += 1
        
        self.program_steps += result.program_steps
        self.memory_usage += result.memory_usage
        if inputlength == 0:
            self.inputbuffer_usage = 1
        else:
            self.inputbuffer_usage += ((1.0 / inputlength ) * result.inputbuffer_usage)
        self.execution_time += result.execution_time
        self.input_size += inputlength
        self.output_size += result.output_size
        #print(self.input_size, self.execution_counter, (self.input_size  / self.execution_counter))
        
        self.average_program_steps = self.program_steps / self.execution_counter
        self.average_memory_usage =  self.memory_usage / self.execution_counter
        self.average_inputbuffer_usage = self.inputbuffer_usage / self.execution_counter
        self.average_execution_time =  self.execution_time / self.execution_counter
        self.average_input_size =  self.input_size / self.execution_counter
        self.average_output_size =  self.output_size / self.execution_counter
        
        self.wasChanged = True
        return result
        
    def setCode(self, newcode): 
        self.wasChanged = True    
        if newcode == self.code:
            #print("dont set same code")
            return False
        self.code = newcode
        self.code_length = len(newcode)
        self.reset()
        return True
        
    def reset(self):
        self.wasChanged = True    
        self.fitness_sum = 0
        self.fitness_evalcount = 0
        self.fitness = None
        self.execution_counter = 0
        #print("reset")
        #for line in traceback.format_stack():
        #    print(line.strip())
        
        self.program_steps = 0
        self.memory_usage = 0
        self.inputbuffer_usage = 0
        self.execution_time = 0
        self.input_size = 0
        self.output_size = 0
        
        self.average_program_steps = 0
        self.average_memory_usage = 0
        self.average_inputbuffer_usage = 0
        self.average_execution_time = 0
        self.average_input_size = 0
        self.average_output_size = 0
        if self.population.problem.sync_to_database == True:
            self.save()        
        
        
    def save(self):
        if self.wasChanged == True or self.id == None:
            self.wasChanged = False
            #print("save")
            #traceback.print_stack()
            super(type(self), self).save()
        #else:
        #    print("Individual.save not")
            #traceback.print_stack()
        
    def __str__(self):
        return "Problem: %s Population: %s Individual: %s Fitness: %s  '%s'" % (self.population.problem.name,self.population.id,self.id,self.fitness, self.code)
            
class ReferenceFunction(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='referencefunctions')

    name     = models.CharField( max_length=200,default="", unique=True)
    program_steps = models.FloatField(default = 0) # nr of executions of this code version

    fitness =  models.FloatField(default = None,blank=True,null=True)
    fitness_sum =  models.FloatField(default = 0)
    fitness_evalcount =  models.FloatField(default = 0)
    execution_counter = models.FloatField(default = 0)
    execution_time = models.FloatField(default = 0) # total execution time
    
    output_size = models.FloatField(default = 0) # total execution time
    input_size = models.FloatField(default = 0) # total execution time

    average_output_size = models.FloatField(default = 0) 
    average_input_size = models.FloatField(default = 0) 
    average_execution_time = models.FloatField(default = 0) 

    function = None # function supplyed externally in problem init
    
    class Meta:
        ordering = ["-fitness"]
    
    def __init__(self,*args,**kwargs):
        self.wasChanged = False
        super(type(self), self).__init__(*args,**kwargs)

    
    def addFitness(self, value, evaluations = 1):
        self.wasChanged = True  
        self.fitness_sum += value
        self.fitness_evalcount += evaluations
        self.fitness = self.fitness_sum / self.fitness_evalcount
        
    def reset(self):
        print("ReferenceFunction.reset")
        self.wasChanged = True    
        self.fitness_sum = 0
        self.fitness_evalcount = 0
        self.fitness = None
        self.execution_counter = 0
        
        self.program_steps = 0
        self.execution_time = 0
        self.average_execution_time = 0
        self.average_input_size = 0
        self.average_output_size = 0
        if self.problem.sync_to_database == True:
            self.save()        
        
    def save(self):
        if self.wasChanged == True or self.id == None:
            #print("reference function saved")
            self.wasChanged = False
            #if REFRESH_REFERENCE_FUNCTION_FROM_DB == True or self.id == None:
            super(type(self), self).save()
            
        
    def execute(self,input):   
        #print("execute ref")  
        self.wasChanged = True  
        self.input_size += len(input)
        
        start = time.time()
        r = self.function(input) 
        self.execution_time += ((time.time() - start)  * 1000000.0)
        
        self.execution_counter += 1 
              
        self.output_size += len(r)
        self.average_execution_time = (self.execution_time / self.execution_counter) 
        self.average_input_size =  self.input_size / self.execution_counter
        self.average_output_size =  self.output_size / self.execution_counter
                
        return r
    def __str__(self):
        return "ReferenceFunction: %s" % self.name
    
    