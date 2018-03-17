from django.db import models
import random
from . import brainfuck
from django.db.models import F, Q
import time
import requests
import json
import p2pClient

def lock(modelobject):
    lockid = random.randint(0,9999999)
    updated = modelobject.objects.filter(pk=modelobject.id,lock="").update(lock = lockid)
    if updated == 1:
        return lockid
    return None

 
class Peer(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    lastfail  = models.DateTimeField(null=True,blank=True,default=None)  
    host     = models.CharField( max_length=200,default="")
    port     = models.IntegerField(default=4141)
    supernode = models.BooleanField(default=False)
    failcount = models.IntegerField(default=0)
    
    def getIndividuals(self,problem_name):
        url = "http://%s:%s/p2p/getIndividuals/%s" % (self.host, self.port, problem_name)        
        data = []
        try:
            r = requests.get(url,timeout = 2000)
            print(r.text)            
            data = json.loads(r.text)
        except Exception as e:
            print("failed to load data from peer: %s" % e)
        return data
        
    def __str__(self):
        return "Peer %s:%s supernode:%s" %(self.host,self.port,self.supernode) 
        
class Problem(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    name     = models.CharField( max_length=200,default="", unique=True)
    description = models.CharField( max_length=200,default="")

    default_max_populationsize =  models.IntegerField(default = 100)  # max number of living individuals
    default_max_individuals  = models.IntegerField(default = -1)  # total number of individuals to generate during evolution, or -1 for unlimited, evolution will stop and return null for new unrated individuals at this point
    default_max_generations =  models.IntegerField(default = -1) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_max_code_length =  models.IntegerField(default = 20) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_min_code_length =  models.IntegerField(default = 20) # total number of evolutionary steps during evolution, or -1 for unlimited
    default_max_steps =  models.IntegerField(default = -1) 
    default_min_fitness_evaluation_per_individual =  models.IntegerField(default = -1) 
 
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
       
    def addPopulation(self,usePriorKnowledge,useP2P):
        cnt = self.populations.count()
        while cnt > 100:
            self.populations.all()[cnt-1:cnt][0].delete()
            
            cnt = self.populations.count()
            
        population = Population()
        population.problem = self
        population.max_populationsize = self.default_max_populationsize
        population.max_individuals = self.default_max_individuals
        population.max_generations = self.default_max_generations
        population.max_code_length = self.default_max_code_length
        population.min_code_length = self.default_min_code_length
        population.max_steps = self.default_max_steps
        population.min_fitness_evaluation_per_individual = self.default_min_fitness_evaluation_per_individual
        population.save()
        population.initializeIndividuals(usePriorKnowledge,useP2P)
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
        print("save called in Problem")
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
    generation_count =  models.IntegerField(default = 0)
    individual_count =  models.IntegerField(default = 0)
    max_code_length =  models.IntegerField(default = 20)
    min_code_length =  models.IntegerField(default = 20)
    max_steps  =  models.IntegerField(default = 20)
    min_fitness_evaluation_per_individual  =  models.IntegerField(default = 1)
    # -> individuals
       
    garunning = False
       
    individual_cache = None
    class Meta:
        ordering = ["-created"]
        
    def initializeIndividuals(self,usePriorKnowledge = True, useP2P = True):
        diff =  self.max_populationsize - self.individuals.count()
        if diff > 0 and  usePriorKnowledge == True:
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
                    
        if useP2P == True:
            individual_datas = p2pClient.p2pClient().getIndividuals(self.problem.name,2)
            print("individuals received from p2p for problem %s" % self.problem)
            indsToReplace = 1
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
                    c = individuals.count()
                    if indsToReplace ==0 or c < 20:
                        individual = Individual()
                        individual.population = self
                        individual.code = individual_data["code"] # ?? should be 0 ?
                        individual.fitness_evalcount = 0 # individual_data["fitness_evalcount"]
                        individual.fitness_sum = 0       # individual_data["fitness_sum"]
                        individual.save()
                        diff -= 1
                        if diff == 0:
                            break
                    else:
                        individuals[c-10+indsToReplace].code = individual_data["code"]
                        individuals[c-10+indsToReplace].code = individual_data["fitness_evalcount"]
                        individuals[c-10+indsToReplace].code = individual_data["fitness_sum"]
                        indsToReplace -=1
        while diff > 0:
            individual = Individual()
            individual.population = self
            individual.save()
            self.individual_count += 1
            diff -= 1
    
    def getIndividuals(self):
        if self.individual_cache == None:
            self.individual_cache = [i for i in self.individuals.all()]
        try:
            return [i for i in self.individual_cache]
        except Exception as e:
            return None
        return None         
        
    def getUnratedIndividual(self):
        try:
            return random.choice([i for i in self.getIndividuals() if i.fitness == None or i.fitness_evalcount < self.min_fitness_evaluation_per_individual ])
        except:
            return None 
            
    def getBestIndividual(self):
        if self.individual_cache == None:
            self.individual_cache = [i for i in self.individuals.all()]
        try:
            return [i for i in self.individual_cache if i.fitness != None][0]
        except:
            return None
   
    def getFitnessStats(self):
        individuals = self.individuals.filter(~Q(fitness = None))
        fitsum = 0
        fitavg = 0
        fitmax = 0
        exetimeavg = 0
        if individuals.count()>0:
            fitsum = sum([i.fitness for i in individuals])
            fitmax = max([i.fitness for i in individuals])
            exetimesum = sum([i.execution_time for i in individuals])
            fitavg = fitsum / len(individuals)
            exetimeavg = exetimesum / len(individuals)
        return {
            "sum" : fitsum,
            "avg" : fitavg,
            "max" : fitmax,
            "execution_time" : exetimeavg
        }
     
    def save(self):
        #print("Save on Population for problem %s" % self.problem)
        if self.individual_cache != None:
            for i in self.individual_cache:
                i.save()
        super(type(self), self).save()

    def __str__(self):
        return "Population: %s" % self.id
    
    
        
class Individual(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    population = models.ForeignKey(Population, on_delete=models.CASCADE, related_name='individuals')

    code     = models.CharField( max_length=20000,default=".")
    code_length =  models.FloatField(default = 10)

    
    fitness =  models.FloatField(default = None,blank=True,null=True)
    fitness_sum =  models.FloatField(default = 0)
    fitness_evalcount =  models.FloatField(default = 0)
    step_counter = models.FloatField(default = 0) # nr of executions of this code version
    execution_counter = models.FloatField(default = 0) # nr of executions of this code version
    execution_time = models.FloatField(default = 0) 

    class Meta:
        ordering = ["-fitness","code_length"]
        
    def addFitness(self, value,):
        self.fitness_sum += value
        self.fitness_evalcount += 1
        self.fitness = self.fitness_sum / self.fitness_evalcount
      
    def execute(self, input):
        start = time.time()    
        x = brainfuck.evaluate(self.code, input_buffer=input, max_steps=self.population.max_steps)
        self.execution_counter += 1
        self.step_counter += x.steps 
        self.execution_time += (time.time() - start)
        return x
        
    def setCode(self, newcode):         
        if newcode == self.code:
            #print("dont set same code")
            return False
        self.fitness_sum = 0
        self.fitness_evalcount = 0
        self.fitness = None
        self.execution_counter = 0
        self.step_counter = 0
        self.execution_time = 0
        self.code = newcode
        self.code_length = len(newcode)
        return True
        
    def __str__(self):
        return "Problem: %s Population: %s Individual: %s Fitness: %s  '%s'" % (self.population.problem.name,self.population.id,self.id,self.fitness, self.code)
            
class ReferenceFunction(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='referencefunctions')

    name     = models.CharField( max_length=200,default="", unique=True)
    step_counter = models.FloatField(default = 0) # nr of executions of this code version

    fitness =  models.FloatField(default = None,blank=True,null=True)
    fitness_sum =  models.FloatField(default = 0)
    fitness_evalcount =  models.FloatField(default = 0)
    execution_counter = models.FloatField(default = 0)
    execution_time = models.FloatField(default = 0) # total execution time

    function = None # function supplyed externally in problem init
    
    class Meta:
        ordering = ["fitness"]
        
    def addFitness(self,value):
        self.fitness_sum += value
        self.fitness_evalcount += 1
        self.fitness = self.fitness_sum / self.fitness_evalcount

    def execute(self,input):   
        self.execution_counter += 1    
        start = time.time()
        r = self.function(input) 
        self.execution_time += (time.time() - start)  
        return r
        
