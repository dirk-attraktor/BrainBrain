import re
import sys
import itertools
import pickle
import os
import time
import threading
import json
import math
import binascii
import random
import numpy as np
import redis
import bson

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
django.setup()
from django.db import transaction
from django.utils import timezone

from libs.redisLock import RedisLock
import libs.randomchoice as randomchoice
from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Species
from brainweb.models import Population
from brainweb.models import Individual
from brainweb.models import ReferenceFunction

from brainlogic import redis_lua_scripts

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

evolutionaryMethods = None  # set externally! 

'''
cachecontrol.
    instances  = [parent_id]
    instances.<parent_id>  = [instance_id, ]
    instance.<id>.alive = parent_id # expire this key
    instance.<id>.parent = parent_id # expire this key
'''     

class CacheController():
    def __init__(self):
        self._remove_inactive_instances()
        self._remove_inactive_parents()
        
        self._watchdogThread = threading.Thread(target=self._watchdog)
        self._watchdogThread.daemon = True
        self._watchdogThread.start()     
        
    def keepalive(self, instance_id):
        redisconnection.expire("cachecontrol.instance.%s.alive" % instance_id, 180)
    
    def add_instance(self, parent_id, instance_id):
        print("add_instance  %s  %s" % ( parent_id, instance_id))
        redisconnection.sadd("cachecontrol.instances", parent_id)
        redisconnection.sadd("cachecontrol.instances.%s" % parent_id, instance_id)
        redisconnection.set ("cachecontrol.instance.%s.alive" % instance_id, 1)
        redisconnection.set ("cachecontrol.instance.%s.parent" % instance_id, parent_id)
        redisconnection.expire("cachecontrol.instance.%s.alive" % instance_id, 180)        
        
    def remove_instance(self, instance_id):
        parent_id = redisconnection.get("cachecontrol.instance.%s.parent" % instance_id)
        print("remove_instance %s %s" % (instance_id, parent_id))
        if parent_id != None:
            redisconnection.srem("cachecontrol.instances.%s" % parent_id.decode("ASCII"), instance_id)
        redisconnection.delete("cachecontrol.instance.%s.alive" % instance_id)
        redisconnection.delete("cachecontrol.instance.%s.parent" % instance_id)
        self._remove_inactive_parents()        
        
    def instance_exists(self, instance_id):
        return redisconnection.exists("cachecontrol.instance.%s.alive" % instance_id)
        
    def has_instances(self, parent_id):
        active_ids = self._get_instances_by_parent(parent_id)
        return len(active_ids) != 0
        
    def _get_instances_by_parent(self, parent_id):
        return [x.decode("ASCII") for x in redisconnection.smembers("cachecontrol.instances.%s" % parent_id)]
    
    def _get_parents(self):
        return [x.decode("ASCII") for x in redisconnection.smembers("cachecontrol.instances")]
        
    def _remove_parent(self,parent_id):    
        print("_remove_parent %s" % parent_id)
        redisconnection.srem("cachecontrol.instances" , parent_id)
        redisconnection.delete("cachecontrol.instances.%s" % parent_id)
        
    def _remove_inactive_instances(self):
        parent_ids = self._get_parents()
        for parent_id in parent_ids:
            instance_ids = self._get_instances_by_parent(parent_id)
            for instance_id in instance_ids:
                if not self.instance_exists(instance_id):
                    print("_remove_inactive_instance")
                    self.remove_instance(instance_id)
                    
    def _remove_inactive_parents(self):
        parent_ids = self._get_parents()
        for parent_id in parent_ids:
            #RedisLock.lock(parent_id)
            with RedisLock(parent_id) as lock:
                instance_ids = self._get_instances_by_parent(parent_id)
                if len(instance_ids) == 0:
                    print("_remove_inactive_parent %s" % parent_id)
                    self._remove_parent(parent_id)
                    if parent_id.startswith("RedisSpecies: "):
                        species_id = parent_id.split(" ")[1]
                        Species.clear_redis(species_id)
                    if parent_id.startswith("RedisReferenceFunction: "):
                        reference_function_id = parent_id.split(" ")[1]
                        ReferenceFunction.clear_redis(reference_function_id)
            #RedisLock.unlock(parent_id)
         
    def _watchdog(self):
        while True:
            time.sleep(90)
            self._remove_inactive_instances()
            self._remove_inactive_parents()
          
     
cacheController = CacheController()

class RedisSpecies():
    def __init__(self, species_id): 
        self.species_id = species_id
        self.instance_id = random.randint(1000,1000000000)
        self.keepaliveThread = None
        self.identifier = "RedisSpecies: %s" % species_id
        
    def load_from_django(self):
        print("species_django_to_redis %s" % self.species_id)

        #RedisLock.lock(self.identifier) 
        with RedisLock(self.identifier) as lock:

            if not cacheController.has_instances(self.identifier):
                cacheController.add_instance( self.identifier, self.instance_id)
                djangospecies = Species.objects.get(id=self.species_id)
                djangospecies.to_redis()                    
                print("species_django_to_redis %s loaded from django" % self.species_id)
            else:
                cacheController.add_instance( self.identifier, self.instance_id)
        #RedisLock.unlock(self.identifier) 
        self.isLoaded = True
        if self.keepaliveThread == None:
            self.keepaliveThread = threading.Thread(target=self._keepalive)
            self.keepaliveThread.daemon = True
            self.keepaliveThread.start()        
      
    def save_to_django(self):
        print("species_redis_to_django %s" % self.species_id)
        with RedisLock(self.identifier) as lock:
            djangospecies = Species.objects.get(id=self.species_id)
            djangospecies.from_redis()   
        
        best_individual_fitnesses = Population.objects.all().values_list('best_individual_fitness', flat=True)
        avg = sum(best_individual_fitnesses) / len(best_individual_fitnesses)
        ti = time.time()
        now = int(ti - ti%60)
        redisconnection.set("stats.fitness.global.%s" % now, avg )
        redisconnection.expire("stats.fitness.global.%s" % now, 3600*72 )

    # disable this instance, unload from redis if needed, will not unload of other instance of species is loaded on redis server     
    def dispose(self):
        print("Dispose species %s" % self.species_id)
        cacheController.remove_instance( self.instance_id)        
        self.isLoaded = False 
    
    def get_random_individual( self, population_id = None, biased = True):
        if population_id == None:
            population = self._get_random_population(biased)
        else:    
            population = RedisPopulation(self.species_id, population_id)
        return population.get_random_individual(biased)
        
    def _get_random_population(self, biased = True):
        nr_of_populations = redisconnection.zcount("species.%s.populations.byTimespend" % self.species_id,"-inf","inf")
        bias = 1 
        if biased == True:
            bias = 5 # prefere population that spend less time
        population_index = randomchoice.selectLinear(nr_of_populations, bias)  
        population_id = int(redisconnection.zrange("species.%s.populations.byTimespend" % self.species_id,population_index,population_index)[0])
        return RedisPopulation(self.species_id, population_id)
        
    def _keepalive(self):   
        while self.isLoaded:
            cacheController.keepalive(self.instance_id)
            time.sleep(30)
            
    
class RedisPopulation():
    
    def __init__(self, species_id, population_id):
        self.species_id = species_id
        self.population_id = population_id         

    def get_random_individual( self, biased = True):
        self.check_populationsize_limits()
        
        bias = 1 
        if biased == True:
            bias = 5 # prefere inds with less evalutions
        for _ in range(0,5):
            nr_of_individuals = int(redisconnection.zcount("population.%s.individuals.allByFitnessEvaluations" % self.population_id,"-inf","inf"))
            individual_index = randomchoice.selectLinear(nr_of_individuals, bias)  
            try:
                individual_id = int(float(redisconnection.zrange("population.%s.individuals.allByFitnessEvaluations" % self.population_id, individual_index, individual_index)[0]))
                return RedisIndividual(self.species_id, self.population_id, individual_id)
            except:
                print("failed: %s" % individual_index)
                pass

    def check_populationsize_limits(self):
        max_populationsize = int(redisconnection.get("species.%s.max_populationsize" % self.species_id))
        min_populationsize = int(redisconnection.get("species.%s.min_populationsize" % self.species_id))
        nr_of_individuals = int(redisconnection.zcount("population.%s.individuals.allByFitness" % self.population_id,"-inf","inf"))        
        
        if nr_of_individuals > max_populationsize:
            evolutionaryMethods.onPopulationsizeOverflow(self)
        elif nr_of_individuals < min_populationsize:
            evolutionaryMethods.onPopulationsizeUnderflow(self)
    
# bytes -> <e bf_compiler> -> bf_c -> <c bf execute>
#                                  -> <c bf_2_c_2_webasm> -> webasmbytecode -> <c webasm execute>
#       -> <e webasm_compiler>                            -> webasmbytecode -> <c webasm execute>

class RedisIndividual():    
    def __init__(self, species_id = None, population_id = None, individual_id = None):
        if species_id == None:
            try:
                species_id = int(redisconnection.get("individual.%s.species" % individual_id))
            except:
                pass
        if population_id == None:
            try:
                population_id = int(redisconnection.get("individual.%s.population" % individual_id))
            except:
                pass
                        
        self.species_id = species_id
        self.population_id = population_id
        self.individual_id = individual_id
        is_valid = self.species_id != None and self.population_id != None and  self.individual_id != None
         
    def execute(self, inputbytes):
        if self._compile() == False:
            return b""
            
        instanceid = random.randint(0,100*1000*1000*1000)
        redisconnection.set("instance.%s.individual_id" % instanceid, self.individual_id)
        redisconnection.set("instance.%s.input" % instanceid, inputbytes)
        redisconnection.rpush("execute.queue", instanceid)
        # ASYNC EXECUTIONS HAPPENS HERE .. 
        done = redisconnection.blpop("instance.%s.done" %  instanceid)
        output = redis_lua_scripts.processExecutionInstance( self.species_id, self.population_id, self.individual_id, instanceid )
        return output        
          
    def addFitness(self, value):
        #print("addFitness to %s : %s" % (self.individual_id, value))
        result = redis_lua_scripts.addFitness(self.species_id, self.population_id, self.individual_id, value)
         
        if len(result) == 0:
            #print("add fitness to dead ind %s, species %s pop %s,  return" % (self.individual_id, self.species_id, self.population_id))
            return False
            
        self._fitness_relative_all    = float(result[0])
        self._fitness_relative_adult   = float(result[1])
        self._fitness_absolute        = float(result[2])
        self._fitness_evaluations     = int(result[3])
        self._fitness_evaluations_min = int(result[4])
        self._fitness_evaluations_max = int(result[5])
        self._pop_fitness_relative        = float(result[6])
              
        evolutionaryMethods.afterIndividualAddFitness(self)
     
    def _compile(self):
        if not redisconnection.exists("individual.%s.code_compiled" % self.individual_id):
            evolutionaryMethods.onIndividualMustCompile(self)

    def reward_subitem(self, key, value):
        try:
            sub_id = redisconnection.get(key).decode("ASCII")
            if sub_id[0] == 'i': 
                sub_id =  int(sub_id[1:])
                sub_species = int(redisconnection.get("individual.%s.species" % sub_id))
                sub_population = int( redisconnection.get("individual.%s.population" % sub_id))
                sub = RedisIndividual(sub_species, sub_population, sub_id)
                sub.addFitness(value)
            elif sub_id[0] == 'r': 
                sub_id =  int(sub_id[1:])
                result = redis_lua_scripts.addFitnessToReferenceFunction(sub_id, value)
            
        except Exception as e:
            #print("Could not reward %s: %s" % (key, e))
            pass
     
    def die(self):
        redis_lua_scripts.die(self.species_id, self.population_id, self.individual_id)
        evolutionaryMethods.afterIndividualDeath(self)
        
    def getIdentifier(self): 
        return "i%s" % self.individual_id
       
class RedisReferenceFunction():    
    def __init__(self, django_reference_function, reference_function):
        self.django_reference_function = django_reference_function
        self.reference_function = reference_function
        self.instance_id = random.randint(1000,1000000000)
        self.keepaliveThread = None
        self.identifier = "RedisReferenceFunction: %s" % self.django_reference_function.id

    def execute(self, data):
        s = time.time()
        result =  self.reference_function(data)
        ti = time.time()
        now = int(ti - ti%60)            
        
        pipe = redisconnection.pipeline()
        pipe.incrbyfloat("referenceFunction.%s.execution_time" % self.django_reference_function.id , ( time.time() - s ) )
        pipe.incr("referenceFunction.%s.executions" % self.django_reference_function.id  )
        pipe.incr("stats.executions.referenceFunction.%s.%s" % ( self.django_reference_function.id ,now ))
        pipe.expire("stats.executions.referenceFunction.%s.%s" % ( self.django_reference_function.id ,now ), 3600*72)
        pipe.execute()
        return result
        
        
    def addFitness(self, value):
        #print("addFitness %s to %s : %s" % (value, self.django_reference_function.id, self.reference_function))
        result = redis_lua_scripts.addFitnessToReferenceFunction(self.django_reference_function.id, value)
        
    def compile(self):
        pass
    
    def reward_subitem(self, key, value):
        pass
    
    def die(self):
        pass
        
    def getIdentifier(self): 
        return "r%s" % self.django_reference_function.id


    def load_from_django(self):
        #print("referenceFunction load_from_django %s" % self.django_reference_function.id )

        with RedisLock(self.identifier) as lock:
            if not cacheController.has_instances(self.identifier):
                cacheController.add_instance( self.identifier, self.instance_id)
                self.django_reference_function.to_redis()                    
                #print("referenceFunction _django_to_redis %s loaded from django" % self.django_reference_function.id)
            
        self.isLoaded = True
        if self.keepaliveThread == None:
            self.keepaliveThread = threading.Thread(target=self._keepalive)
            self.keepaliveThread.daemon = True
            self.keepaliveThread.start()        
      
    def save_to_django(self):
        with RedisLock(self.identifier) as lock:
            self.django_reference_function.from_redis()   
         
    def dispose(self):
        self.isLoaded = False 
        cacheController.remove_instance( self.instance_id)        
        
         
    def _keepalive(self):   
        while self.isLoaded:
            cacheController.keepalive(self.instance_id)
            time.sleep(30)
       


