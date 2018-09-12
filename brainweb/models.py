from django.db import models
import random
from django.db.models import F, Q
import time
import requests
import json
from django.db import connection
import datetime
from django.utils import timezone
import traceback
from django.utils import timezone
import redis
from django.db import transaction
import binascii

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)



class Peer(models.Model):
    id       = models.BigAutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    lastfail  = models.DateTimeField(null=True,blank=True,default=None)  
    host     = models.CharField( max_length=200,default="")
    port     = models.BigIntegerField(default=4141)
    supernode = models.BooleanField(default=False)
    failcount = models.BigIntegerField(default=0)
    def __str__(self):
        return "Peer %s:%s supernode:%s" %(self.host,self.port,self.supernode) 

        
class Problem(models.Model):
    id       = models.BigAutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    name     = models.CharField( max_length=200,default="", unique=True)
    description = models.CharField( max_length=200,default="")        
    # -> species
    def __str__(self):
        return "Problem %s" %(self.name) 
        
    def getP2PIndividuals(self,limit = 1):
        species_ids =  self.species.all().values_list('id', flat=True)
        #print(species_ids)
        population_ids = Population.objects.filter(species__in=list(species_ids)).filter(fitness_relative__gt=0.75).values_list('id', flat=True)
        #print(population_ids)
        individual_ids = Individual.objects.filter(population__in=list(population_ids)).filter(fitness_relative_adult__gt=0.75).values_list('id', flat=True)
        individual_ids = [i for i in individual_ids]
        count = len(individual_ids)
        if count == 0:
            return []
        random_ids = random.sample(individual_ids, min(count, limit))
        #print(random_ids)
        individuals = Individual.objects.filter(population__in=list(population_ids)).filter(id__in=random_ids)
        #print(individuals)
        return individuals   

# a species may learn to solve one or more problems by creating populations that contain individuals    



class Species(models.Model ):
    id       = models.BigAutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    name     = models.CharField( max_length=200,default="", unique=True)
    problems = models.ManyToManyField(Problem, related_name='species',db_index=True)
    
    useP2P = models.BooleanField(default=False)

    max_populations =  models.BigIntegerField(default = 10)  # max number of parallel populations
    max_populationsize =  models.BigIntegerField(default = 100)  # max number of living individuals per population
    min_populationsize =  models.BigIntegerField(default = 50)  # max number of living individuals per population
    max_code_length =  models.BigIntegerField(default = 20) #
    min_code_length =  models.BigIntegerField(default = 20) #

    max_fitness_evaluations =  models.BigIntegerField(default = 100) 
    min_fitness_evaluations =  models.BigIntegerField(default =  10)
    
    
    max_memory =  models.BigIntegerField(default = 20) #
    max_permanent_memory =  models.BigIntegerField(default = 20) #
    
    max_steps =  models.BigIntegerField(default = -1) 
 
    individuals_created =  models.BigIntegerField(default = 0) 

    reference_function_rate =  models.FloatField(default =  0)
    # -> populations
    # -> referencefunctions
      
    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return "Species: %s" % self.name

    def to_redis(self):
        pipe = redisconnection.pipeline()
        for param in [
            "max_populations",
            "max_populationsize",
            "min_populationsize",
            "max_code_length",
            "min_code_length",
            "max_fitness_evaluations", # individuals with evals == max_fitness_evaluations die
            "min_fitness_evaluations", # individuals with eval >= min_fitness_evaluations -> fitness == 0 die. ,  fitness != 0 go to adultsByFitness. 
            "max_memory",
            "max_permanent_memory",
            "max_steps",
            "individuals_created",
            ]:
            key = "species.%s.%s" % (self.id, param)
            value = getattr(self, param)
            pipe.set(key, value)
            
        for population in self.populations.all():
            population.to_redis()
            pipe.zadd("species.%s.populations.byTimespend"   % self.id, population.timespend_total, population.id)
            pipe.zadd("species.%s.populations.byBestFitness" % self.id, population.best_individual_fitness, population.id)
        pipe.execute()
            
    def from_redis(self):
        self.individuals_created = int(redisconnection.get("species.%s.individuals_created" % self.id))
        self.save()
        cnt = 0
        s = 0
        max_pop_fitnesses = []
        for population in self.populations.all():
            population.from_redis()
            ids_scores = redisconnection.zrange("population.%s.individuals.adultsByFitness" % population.id, 0, -1, withscores = True)
            fitnesses = [ float(x[1]) for x in ids_scores]
            try:
                max_pop_fitness = max(fitnesses)
            except:
                max_pop_fitness = 0
            max_pop_fitnesses.append(max_pop_fitness)
            len_fitness = len(fitnesses)
            if len_fitness > 0:
                avg_pop_fitness = sum(fitnesses) / len_fitness
            else:
                avg_pop_fitness = 0
            ti = time.time()
            now = int(ti - ti%60)
            redisconnection.set("stats.fitness.population.%s.%s" % ( population.id, now,  ), avg_pop_fitness )
            redisconnection.expire("stats.fitness.population.%s.%s" % (  population.id, now, ), 3600*72 )
            redisconnection.set("stats.fitness_max.population.%s.%s" % ( population.id, now,  ), max_pop_fitness )
            redisconnection.expire("stats.fitness_max.population.%s.%s" % (  population.id, now, ), 3600*72 )
            
            cnt += 1
            s += avg_pop_fitness
        ti = time.time()
        now = int(ti - ti%60)
        redisconnection.set(   "stats.fitness.species.%s.%s" % ( self.id, now ), ( s / cnt ) )
        redisconnection.expire("stats.fitness.species.%s.%s" % ( self.id, now ), 3600*72 )
        redisconnection.set(   "stats.fitness_max.species.%s.%s" % ( self.id, now ), max(max_pop_fitnesses))
        redisconnection.expire("stats.fitness_max.species.%s.%s" % ( self.id, now ), 3600*72 )
        
        
    @staticmethod
    def clear_redis(species_id):
        pipe = redisconnection.pipeline()

        for param in [
            "max_populations",
            "max_populationsize",
            "min_populationsize",
            "max_code_length",
            "min_code_length",
            "max_fitness_evaluations",
            "min_fitness_evaluations",
            "max_memory",
            "max_permanent_memory",
            "max_steps",
            "individuals_created",
            ]:
            pipe.delete("species.%s.%s" % (species_id, param))
        pipe.execute()
   
        population_ids = redisconnection.zrange("species.%s.populations.byTimespend" % species_id, 0, -1)
        population_ids =[int(float(x)) for x in population_ids]     
        for population_id in population_ids:
            Population.clear_redis(population_id)
            
        redisconnection.delete("species.%s.populations.byTimespend" % species_id)
        redisconnection.delete("species.%s.populations.byBestFitness" % species_id)


class Population(models.Model):
    id       = models.BigAutoField(primary_key=True,db_index=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='populations',db_index=True)
   
    best_individual_id      = models.CharField( max_length=200,default="")
    best_individual_fitness = models.FloatField(default = 0)
    
    individuals_created =  models.BigIntegerField(default = 0)
    timespend =  models.BigIntegerField(default = 0)
    timespend_total =  models.BigIntegerField(default = 0)
    fitness_relative =  models.FloatField(default = 1)
    fitness_evaluations =  models.BigIntegerField(default = 0)
    fitness_evaluations_total =  models.BigIntegerField(default = 0)
    
    # -> individuals
     
    class Meta:
        ordering = ["-best_individual_fitness"]

        
    def getTimespendSeconds(self):
        return int(self.timespend/1000000)
        
    def __str__(self):
        return "Population: %s for species %s, BestFitness: %s" % (self.id, self.species.name, self.best_individual_fitness)
        
    def stats(self):
        individuals_count = self.individuals.count()
        individuals = self.individuals.all()
        if individuals_count == 0:
            return 0
        return {
            "avg_code_size" :           sum([x.code_size                    for x in individuals]) / individuals_count, 
            "avg_memory_size" :         sum([x.memory_size                  for x in individuals]) / individuals_count , # permanent memory
            "avg_fitness" :             sum([x.fitness                      for x in individuals]) / individuals_count , 
            "max_fitness" :             max([x.fitness                      for x in individuals]) , 
            "avg_fitness_evaluations" : sum([x.fitness_evaluations          for x in individuals]) / individuals_count , 
            "avg_executions" :          sum([x.executions                   for x in individuals]) / individuals_count , 
            "avg_program_steps" :       sum([x.get_program_steps_avg()      for x in individuals]) / individuals_count , 
            "avg_memory_usage" :        sum([x.get_memory_usage_avg()       for x in individuals]) / individuals_count , 
            "avg_execution_time" :      sum([x.get_execution_time_avg()  for x in individuals]) / individuals_count , 
        }

    def to_redis(self):
        pipe = redisconnection.pipeline()
        for param in [
            "best_individual_id",
            "best_individual_fitness",
            "individuals_created",
            "timespend",
            "timespend_total",
            "fitness_relative",
            "fitness_evaluations",
            "fitness_evaluations_total",
            ]:
            key = "population.%s.%s" % (self.id, param)
            value = getattr(self, param)
            pipe.set(key, value)
        
        for individual in self.individuals.all():
            individual.to_redis()
            pipe.zadd("population.%s.individuals.allByFitness"   %  self.id, individual.fitness, individual.id)
            pipe.zadd("population.%s.individuals.allByTimespend" %  self.id, individual.execution_time, individual.id)
            if individual.fitness_evaluations >= self.species.min_fitness_evaluations and individual.fitness > 0:
                pipe.zadd('population.%s.individuals.adultsByFitness' % self.id, individual.fitness, individual.id  ) 
            pipe.zadd('population.%s.individuals.allByFitnessEvaluations' % self.id, individual.fitness_evaluations, individual.id  ) 
        pipe.execute()
           
    def from_redis(self ):
        #print("1: %s" % time.time())
        try:
            best_individual_id = int(redisconnection.get("population.%s.best_individual_id" % self.id))
            best_individual_fitness = float(redisconnection.get("population.%s.best_individual_fitness" % self.id))
        except:
            best_individual_id = ""
            best_individual_fitness = 0
        #print("from_redis %s " % self.id)
        self.best_individual_id = best_individual_id
        self.best_individual_fitness = best_individual_fitness
        self.individuals_created = int(redisconnection.get("population.%s.individuals_created" % self.id))
        #self.timespend = int(redisconnection.get("population.%s.timespend" % self.id))
        self.timespend_total = int(redisconnection.get("population.%s.timespend_total" % self.id))
        self.fitness_relative = float(redisconnection.get("population.%s.fitness_relative" % self.id))
        #self.fitness_evaluations = int(redisconnection.get("population.%s.fitness_evaluations" % self.id))
        self.fitness_evaluations_total = int(redisconnection.get("population.%s.fitness_evaluations_total" % self.id))
        
        individual_ids =[int(float(x)) for x in redisconnection.zrange("population.%s.individuals.allByFitness" % self.id, 0, -1)]
        individuals = []
        #print("2: %s" % time.time())
        #print("s: %s" % time.time())
        
        for individual_id in individual_ids:
            individual, created  = Individual.objects.get_or_create(id=individual_id,population=self)
            success = individual.from_redis(self.id, individual_id)
            if success == True:
                individuals.append(individual)
        #print("3: %s" % time.time())                
        #print("e: %s" % time.time())                
        with transaction.atomic():    
            for individual in individuals:
                individual.save()
                
        self.timespend = sum([i.execution_time for i in individuals])
        self.fitness_evaluations = sum([i.fitness_evaluations for i in individuals])
        self.save()      
        #print("4: %s" % time.time())
        todel = []
        for individual_id in Individual.objects.filter(population=self.id).values_list('id', flat=True):
            if individual_id not in individual_ids:  
                todel.append(individual_id)
        #print("5: %s" % time.time())                
        Individual.objects.filter(Q(id__in = todel) & Q(population=self.id)).delete()
        #print("6: %s" % time.time())
        #print("%s removed" % len(todel))  
  
 
  
    @staticmethod
    def clear_redis(population_id): 
        print("clearing pop %s from redis" % population_id)
        pipe = redisconnection.pipeline()
        for param in [
            "best_individual_id",
            "best_individual_fitness",
            "individuals_created",
            "timespend",
            "timespend_total",
            "fitness_relative",
            "fitness_evaluations",
            "fitness_evaluations_total",
            ]:
            pipe.delete("population.%s.%s" % (population_id, param))
        pipe.execute()
        
        individual_ids = redisconnection.zrange("population.%s.individuals.allByFitness" % population_id, 0, -1)
        individual_ids = [ int(float(x)) for x in individual_ids ]
        for individual_id in individual_ids:
            Individual.clear_redis(individual_id)
            
        redisconnection.delete("population.%s.individuals.allByFitness" % population_id)
        redisconnection.delete("population.%s.individuals.allByTimespend" % population_id)
        redisconnection.delete("population.%s.individuals.allByFitnessEvaluations" % population_id)
        redisconnection.delete("population.%s.individuals.adultsByFitness" % population_id)
    
   
class Individual(models.Model):
    id       = models.BigAutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    population = models.ForeignKey(Population, on_delete=models.CASCADE, related_name='individuals',db_index=True)

    compiler      = models.CharField( max_length=100, default="")
    matemutator = models.CharField( max_length=100, default="")
    
    code          = models.TextField( max_length=10*1000*1000, default=".")
    code_compiled = models.TextField( max_length=10*1000*1000, default=".")
    code_size =  models.BigIntegerField(default = 0)
    memory        = models.TextField( max_length=10*1000*1000, default="")
    memory_size =  models.BigIntegerField(default = 0)

    fitness =  models.FloatField(default = 0)
    fitness_sum = models.FloatField(default = 0)
    fitness_relative_all =  models.FloatField(default = 0)
    fitness_relative_adult =  models.FloatField(default = 0)
    fitness_evaluations =  models.BigIntegerField(default = 0)
    executions = models.BigIntegerField(default = 0) 
    program_steps = models.BigIntegerField(default = 0)     
    memory_usage = models.BigIntegerField(default = 0)    
    execution_time = models.FloatField(default = 0)   
    
    class Meta:
        ordering = ["-fitness"]
   
    def __str__(self):
        return "Species: %s Population: %s Individual: %s Fitness: %s  " % (self.population.species.name,self.population.id,self.id,self.fitness)

    def get_program_steps_avg(self):
        if self.executions > 0:
            return self.program_steps / self.executions
        else:
            return 0
    def get_memory_usage_avg(self):
        if self.executions > 0:
            return self.memory_usage / self.executions
        else:
            return 0
    def get_execution_time_avg(self):
        if self.executions > 0:
            return (self.execution_time / self.executions)
        else:
            return 0
    
    def _encode_binary(self, binary):
        return binascii.b2a_qp(bytes(binary),istext=False).decode().replace("=\n","")
        
    def _decode_binary(self, ascii):
        return binascii.a2b_qp(ascii)

    def to_redis(self):
        pipe = redisconnection.pipeline()
        pipe.set("individual.%s.species" % self.id, self.population.species.id)
        pipe.set("individual.%s.population" % self.id, self.population.id)
        pipe.set("individual.%s.alive" % self.id, 1)
        
        pipe.set("individual.%s.memory"          %  self.id, self._decode_binary(self.memory))
        pipe.set("individual.%s.code" % self.id, self._decode_binary(self.code))
        if self.code_compiled != "":
            pipe.set("individual.%s.code_compiled"   %  self.id, self._decode_binary(self.code_compiled))
        
        for param in [
            "compiler",
            "matemutator",
            "fitness",
            "fitness_sum",
            "fitness_relative_all",
            "fitness_relative_adult",
            "fitness_evaluations",
            "executions",
            "program_steps",
            "memory_usage",
            "execution_time",
            ]:
            key = "individual.%s.%s" % (self.id, param)
            value = getattr(self, param)
            pipe.set(key, value)
        pipe.execute()
    
    def from_redis(self, population_id, individual_id):
        self.population_id = population_id
        self.id = individual_id
        
        params = [
            ["fitness", "float"],
            ["fitness_sum", "float"],
            ["fitness_relative_all", "float"],
            ["fitness_relative_adult", "float"],
            ["execution_time", "float"],
            ["fitness_evaluations", "int"],
            ["executions", "int"],
            ["program_steps", "int"],
            ["memory_usage", "int"],
            ["compiler", "individualid"],
            ["matemutator", "individualid"],
            ["code", "bin"],
            ["code_compiled", "bin"],
            ["memory", "bin"],
        ]
        
        pipe = redisconnection.pipeline()
        for param in params:
            pipe.get("individual.%s.%s" % (self.id, param[0]))
        results = pipe.execute()
        for index, param in enumerate(params):
            value = results[index]
            if param[1] == "int":
                value = int(value) if value != None else 0
            if param[1] == "float":
                value = float(value) if value != None else 0
            if param[1] == "individualid":
                value = value.decode("ASCII") if value != None and value != b'' else ""
            if param[1] == "bin":
                value = self._encode_binary(value) if value != None else ""
            setattr(self, param[0], value)    
        
        self.memory_size = len(self.memory)                      
        self.code_size = len(self.code)                      
        self.created = timezone.now()
        return redisconnection.exists("individual.%s.alive" % individual_id)  # if not exists return false, because ind died
    
    @staticmethod
    def clear_redis(individual_id): 
        pipe = redisconnection.pipeline()
        for param in [
            "species",
            "population",
            "alive",
            "memory",
            "code",
            "code_compiled",
            "compiler",
            "matemutator",
            "fitness",
            "fitness_sum",
            "fitness_relative_all",
            "fitness_relative_adult",
            "fitness_evaluations",
            "executions",
            "program_steps",
            "memory_usage",
            "execution_time",
            ]:
            pipe.delete("individual.%s.%s" % (individual_id, param))
        pipe.execute()
       
    
class ReferenceFunction(models.Model):
    id       = models.BigAutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='referencefunctions')
    name     = models.CharField( max_length=200, default="", unique=True)
        
    fitness =  models.FloatField(default = 0)
    fitness_sum = models.FloatField(default = 0)
    fitness_evaluations =  models.BigIntegerField(default = 0)
    executions = models.BigIntegerField(default = 0) 
    execution_time = models.FloatField(default = 0)   
    
    function = None # function supplyed externally in problem init
    
    class Meta:
        ordering = ["-fitness"]
   
    def __str__(self):
        return "ReferenceFunction: %s" % self.name

    def reset(self): 
        pipe = redisconnection.pipeline()
        for param in [
            "fitness",
            "fitness_sum",
            "fitness_evaluations",
            "executions",
            "execution_time",
            ]:
            pipe.set("referenceFunction.%s.%s" % (self.id, param),0)
            setattr(self, param, 0)  
        self.save()
        pipe.execute()
        
    def to_redis(self):
        pipe = redisconnection.pipeline()
        pipe.set("referenceFunction.%s.name" % self.id, self.name)
        pipe.set("referenceFunction.%s.fitness" % self.id, self.fitness)
        pipe.set("referenceFunction.%s.fitness_sum" % self.id, self.fitness_sum)
        pipe.set("referenceFunction.%s.fitness_evaluations" % self.id, self.fitness_evaluations)
        pipe.set("referenceFunction.%s.executions" % self.id, self.executions)
        pipe.set("referenceFunction.%s.execution_time" % self.id, self.execution_time)
        pipe.execute()
    
    def from_redis(self):
        params = [
            ["fitness", "float"],
            ["fitness_sum", "float"],
            ["fitness_evaluations", "int"],
            ["executions", "int"],
            ["execution_time", "float"],
        ]
        
        pipe = redisconnection.pipeline()
        for param in params:
            pipe.get("referenceFunction.%s.%s" % (self.id, param[0]))
        results = pipe.execute()
        for index, param in enumerate(params):
            value = results[index]
            if param[1] == "int":
                value = int(value) if value != None else 0
            if param[1] == "float":
                value = float(value) if value != None else 0
            setattr(self, param[0], value)    
        ti = time.time()
        now = int(ti - ti%60)            
        redisconnection.set("stats.fitness.referenceFunction.%s.%s" % ( self.id, now,  ), self.fitness )
        redisconnection.expire("stats.fitness.referenceFunction.%s.%s" % (  self.id, now, ), 3600*72 )
          
        self.save()
        
    @staticmethod
    def clear_redis(referenceFunction_id): 
        pipe = redisconnection.pipeline()
        for param in [
            "fitness",
            "fitness_sum",
            "fitness_evaluations",
            "executions",
            "execution_time",
            ]:
            pipe.delete("referenceFunction.%s.%s" % (referenceFunction_id, param))
        pipe.execute()
          
    