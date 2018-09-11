import random
import numpy as np
import re
import sys
import itertools
import pickle
import os
import time
import math
import threading
import json
import math
import binascii
import redis
import bson
from difflib import SequenceMatcher


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
django.setup()

from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Species
from brainweb.models import Population
from brainweb.models import Individual
from brainweb.models import ReferenceFunction

from libs import reward
from libs.redisLock import RedisLock
from libs.brainP2Pclient import BrainP2Pclient
import libs.randomchoice as randomchoice

from bytefuck.bytefuck import ByteFuckHelpers

import brainlogic
import brainlogic.redis_models

from brainlogic import redis_lua_scripts

from brainlogic.redis_models import RedisSpecies
from brainlogic.redis_models import RedisPopulation
from brainlogic.redis_models import RedisIndividual
from brainlogic.redis_models import RedisReferenceFunction


redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)
   
evolutionMateMutate = None
evolutionCompiler = None

individual_id_range = 1000*1000*1000*1000

byteFuckHelper = ByteFuckHelpers()
brainP2Pclient = BrainP2Pclient()

max_stack_depth = 30
def stackdepth_limit_hit():
    size = 2  # current frame and caller's frame always exist
    while True:
        try:
            sys._getframe(size)
            size += 1
        except ValueError:
            return (size - 1) > max_stack_depth
   
   
class Evolution():
    def __init__(self,
            species_name, 
            problem_name, 
            problem_description,
            
            max_populations , # max number of parallel populations
            max_populationsize, # max number of living individuals per population
            min_populationsize, # min number of living individuals per population, create random inds if lower
            max_code_length, #
            min_code_length, #
            
            max_fitness_evaluations,
            min_fitness_evaluations,
            
            max_memory,
            max_permanent_memory,
            max_steps, # executed steps of code per individual 
                         
            usePriorKnowledge = True,
            useP2P = True,
            
            warmup = False,
            
            reference_functions = [],
            reference_function_rate = 0,
            
        ):
                
        try:
            self.djangospecies = Species.objects.get(name = species_name)
            print("special loaded")
        except Exception as e:
            print(e)
            self.djangospecies = Species()
            
        self.djangospecies.name = species_name
        self.djangospecies.max_populations = max_populations
        self.djangospecies.max_populationsize = max_populationsize
        self.djangospecies.min_populationsize = min_populationsize
        self.djangospecies.max_code_length =  max_code_length
        self.djangospecies.min_code_length =  min_code_length
        self.djangospecies.max_fitness_evaluations =  max_fitness_evaluations
        self.djangospecies.min_fitness_evaluations =  min_fitness_evaluations
        
        self.djangospecies.max_memory =  max_memory
        self.djangospecies.max_permanent_memory =  max_permanent_memory
        
        self.djangospecies.max_steps =  max_steps
        
        self.djangospecies.reference_function_rate =  reference_function_rate
       
        self.djangospecies.save()
        while self.djangospecies.populations.count() < max_populations:
            print("Create Population")
            pop = Population()
            pop.species = self.djangospecies
            pop.save()
            
        try:
            self.problem = Problem.objects.get(name = problem_name)
            print("found problem %s" % self.problem)
        except:
            self.problem = Problem()
            self.problem.name = problem_name
            self.problem.description = problem_description
            self.problem.save()
            print("create problem %s" % self.problem)
        self.djangospecies.problems.add(self.problem)
        self.djangospecies.save()
        print("LOADING django species")
        print(self.djangospecies.id)
        self.species = RedisSpecies(self.djangospecies.id)
        self.species.load_from_django()
        
        self.reference_functions = []
        for reference_function in reference_functions:
            try:
                referenceFunction = ReferenceFunction.objects.get(name=reference_function["name"])
            except Exception as e:
                referenceFunction = ReferenceFunction()
            referenceFunction.name = reference_function["name"]
            referenceFunction.problem = self.problem
            referenceFunction.function = reference_function["function"]
            referenceFunction.save()
            
            redisReferenceFunction = RedisReferenceFunction( referenceFunction, referenceFunction.function)
            redisReferenceFunction.load_from_django()
            self.reference_functions.append(redisReferenceFunction)
            
        # runtime stuff
        self.selected_individual = None
        #print(warmup)
        self.warmup = warmup

    def get_random_individual(self):
        if random.random() < self.djangospecies.reference_function_rate:
            return random.choice(self.reference_functions)
        else:
            return self.species.get_random_individual()
                
    def save(self):
        if self != evolutionCompiler and self != evolutionMateMutate:
            evolutionCompiler.save()
            evolutionMateMutate.save()            
        self.species.save_to_django()
        for reference_function in self.reference_functions:
            reference_function.save_to_django()
            
    def close(self):
        self.species.dispose()
    
    
class EvolutionTraining(Evolution):
    def trainByExample(self, examplesource, maxsteps = -1):
        print("EvolutionTraining.trainByExample")
        step = 0
    
        example_iterator = iter(examplesource())
        while step < maxsteps or maxsteps == -1:
            step += 1
            if step % 1000 == 0:
                print("Regress step '%s'  for '%s'" % (step,self.problem ))
            selected_individual = self.species.get_random_individual()
            fitness = 0
            count = 0
            data = []
            _input, _output = next(example_iterator)
            result = selected_individual.execute(_input)[0:len(_output)*4]
            data.append([_input, _output , result, ])
            fitness += SequenceMatcher(None, result, _output).ratio()
            fitness += reward.absolute_distance_reward(result,_output,256)
            count += 2
            fitness /= count
            selected_individual.addFitness(fitness)     
            if fitness == 1:
                print("Fitness 1 reached! regress %s Solved!" % self.problem.name)
                print(data)
            
            
class EvolutionReplacement(Evolution):
    def replace(self, function): 
        print("EvolutionReplacement.replace")
        name = function.__name__
        if name not in self.loaded_referenceFunctions:
            #print("name: %s" % name)
            #print(self.problem)
            #print(self.problem.referencefunctions.all())
            try:
                referenceFunction = ReferenceFunction.objects.get(name=name)
            except Exception as e:
                print("ReferenceFunction not found in db: %s" % e)
                referenceFunction = None
            if referenceFunction == None:
                referenceFunction = ReferenceFunction()
                referenceFunction.name = name
                referenceFunction.problem = self.problem
                referenceFunction.save()
            referenceFunction.function = function            
            self.loaded_referenceFunctions[name] = referenceFunction

        
        def replacementFunction(argument):
            print("called replacementFunction")
            selected_reference_function = random.choice([x[1] for x in self.loaded_referenceFunctions.items()])

            reference_result = None            
            referenceFunction_rate = 0.2
            use_reference_function = self.warmup
            if random.random() < referenceFunction_rate:
                use_reference_function = True
            
            if use_reference_function == True:
                reference_result = selected_reference_function.function(argument)
            
            if use_reference_function == True and self.warmup == False:
                return reference_result    
            
            if self.selected_individual == None:
                self.selected_individual = self.species.get_random_individual()
                            
            evolution_result = self.selected_individual.execute(argument) 
                
            if self.warmup == False:
                return evolution_result
               
            try:
                fitness = (
                    reward.absolute_distance_reward(reference_result, evolution_result[0:len(reference_result) * 2] , 256) 
                    + 
                    SequenceMatcher(None, evolution_result[0:len(reference_result) * 2], reference_result).ratio()
                ) / 2.0
            except Exception as e:
                print("failed to do warmup reward %s" % e)
                fitness = 0
            print("warmup reward for %s : %s"  % (self.problem.name, fitness))
            if self.selected_individual.addFitness(fitness) == False:
                self.selected_individual = None  # most likely died
                print("individual died")
            return reference_result
                
        return replacementFunction       
    
    def reward(self, value, selectNewIndividual = True):
        if self.selected_individual != None and self.warmup != True:
            self.selected_individual.addFitness(value)
        if selectNewIndividual == True:
            self.selected_individual = None

            

def evolutionMateMutateReference(data):
    data = bson.loads(data)
    l1  = len(data["0"]["code"])
    l2  = len(data["1"]["code"])
    r1 = random.randint(0,l1)
    r2 = random.randint(0,l2)
    p1 = data["0"]["code"][:r1]
    p2 = data["1"]["code"][r2:]
    n = list(p1 + p2)
    l = len(n)
    rate = random.randint(10,100)
    for _ in range(0, math.ceil(l / rate)):
        random_index = random.randint(0, l-1)
        n[random_index] = byteFuckHelper.get_random_byte()
    
    return bytes(n)
            
evolutionMateMutate = Evolution(
    species_name = "MateMutate",
    problem_name = "MateMutate", 
    problem_description = "MateMutate",
    
    max_populations = 10 , # max number of parallel populations
    min_populationsize = 250, # min number of living individuals per population, create random inds if lower
    max_populationsize = 350, # max number of living individuals per population
    min_code_length = 100, #
    max_code_length = 500, #
    
    min_fitness_evaluations = 4, #
    max_fitness_evaluations = 20, #
    
    max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
    max_permanent_memory = 1000, # max perm memory stored in 
    max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
    usePriorKnowledge = False,
    useP2P = False,
    warmup = False,
    reference_functions = [
        { "name" : "evolutionMateMutateReference" , "function" : evolutionMateMutateReference },
    ],
    reference_function_rate = 0.8,
)

def evolutionCompilerReference(code):
    code_compiled = byteFuckHelper.clean_bytefuck(code)
    return code_compiled
        
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
    max_fitness_evaluations = 20, #
    
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
            
class EvolutionaryMethods():
    @staticmethod
    def onIndividualMustCompile(individual):
        code = redisconnection.get("individual.%s.code" % individual.individual_id)
        if code == None:
            print("individual has died, return")
            return False   
            
        if stackdepth_limit_hit() == True: 
            #print("just keep copy source")                 
            code_compiled = byteFuckHelper.clean_bytefuck(code)
            redis_lua_scripts.setIndividualCompiledCode(individual.individual_id, code_compiled, "")                
        else:    
            max_code_length = int(redisconnection.get("species.%s.max_code_length" %  individual.species_id))
            for i in range(0,10):
                selected_compiler = evolutionCompiler.get_random_individual()
                #print(selected_compiler.individual_id)
                code_compiled = selected_compiler.execute(code)
                if len(code_compiled) > max_code_length:
                    code_compiled = code_compiled[0:max_code_length]
                code_compiled = byteFuckHelper.clean_bytefuck(code_compiled)
                if len(code_compiled) > 3:
                    redis_lua_scripts.setIndividualCompiledCode(individual.individual_id, code_compiled,  selected_compiler.getIdentifier())
                    return 
                else:
                    #print("add compiler fitness 0")
                    selected_compiler.addFitness(0)    
    
    @staticmethod
    def afterIndividualAddFitness(individual):
        p = 0.2 # dont reward compiler/matemutator to often  
        if individual.species_id == evolutionMateMutate.species.species_id or individual.species_id == evolutionCompiler.species.species_id:
            p = 0.02 # dont recursive reward  compiler/matemutator to often  
            
        subreward = ( 0.2 * individual._fitness_relative_all ) + ( 0.8 * individual._fitness_relative_adult )
            
        if random.random() <= p:       
            individual.reward_subitem("individual.%s.compiler" % individual.individual_id, subreward)
        if random.random() <= p:      
            individual.reward_subitem("individual.%s.matemutator" % individual.individual_id, subreward)
        
        if individual._fitness_evaluations >= individual._fitness_evaluations_min and individual._fitness_absolute == 0:
            individual.die()
            return
            
        max_ind_evals = individual._fitness_evaluations_min 
        max_ind_evals += ( individual._fitness_evaluations_max - individual._fitness_evaluations_min ) * ( individual._fitness_relative_adult**2.718281 )
        if individual._fitness_evaluations >= max_ind_evals:
            individual.die()
                        
    @staticmethod
    def afterIndividualDeath(individual):   
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.max_populationsize" % individual.species_id)
        pipe.zcount("population.%s.individuals.allByFitness" % individual.population_id,"-inf","inf")
        max_populationsize, nr_of_individuals = [int(r) for r in pipe.execute()]    
        if nr_of_individuals < max_populationsize - 5: # keep some air
            population = RedisPopulation(individual.species_id, individual.population_id)
            EvolutionaryMethods.create_new_individual(population)
    
    @staticmethod
    def onIndividualCreated(population, species_individuals_created, population_individuals_created):
        if species_individuals_created % 10000 == 0: 
            print("species %s %s inds created" % (population.species_id, species_individuals_created))
        if population_individuals_created % 10000 == 0: 
            print("population %s %s inds created" % ( population.population_id, population_individuals_created))
        
        if species_individuals_created % (500*1000) == 0:   # on every x th ind created in species kill/recreate worst population from local species
            species = RedisSpecies(population.species_id)
            worst_population_id = int(redisconnection.zrange("species.%s.populations.byBestFitness" % population.species_id, 0, 0)[0])
            worst_population = RedisPopulation(population.species_id, worst_population_id)
            max_populationsize = int(redisconnection.get("species.%s.max_populationsize" % population.species_id))
            min_populationsize = int(redisconnection.get("species.%s.max_populationsize" % population.species_id))
            print("Mass killing worst population %s from species %s " % (worst_population_id, population.species_id))
            new_individual_ids = []
            for i in range(0, max_populationsize ):
                for tries in range(0,10):
                    individual_to_kill = worst_population.get_random_individual(biased=False)
                    if individual_to_kill not in new_individual_ids:
                        redis_lua_scripts.die(individual_to_kill.species_id, individual_to_kill.population_id, individual_to_kill.individual_id) #use diretct method here to not tigger afterIndividualDeath()
                        break
                individual1 = species.get_random_individual(biased=False)
                individual2 = species.get_random_individual(biased=False)
                new_individual_id = EvolutionaryMethods._mate_mutate_indivials(worst_population, [ individual1.individual_id, individual2.individual_id])
                new_individual_ids.append(new_individual_id)
                
        if species_individuals_created % (1*1000*1000) == 0:   # on every x th ind created in species kill/recreate worst population from p2p 
            max_populationsize = int(redisconnection.get("species.%s.max_populationsize" % population.species_id))
            problem_names = [n for n in Species.objects.get(id = population.species_id).problems.all().values_list('name', flat=True)]
            problem_names = random.sample(problem_names, min([len(problem_names), 5]))
            requests = min([int(max_populationsize / 2 / len(problem_names) / 5), 20])
            inds = []
            for problem_name in problem_names:
                inds.extend(brainP2Pclient.getIndividuals( problem_name, requests = requests, limit_per_node = 5))
            print("%s individuals received from p2p " % len(inds))
            
            worst_population_id = int(redisconnection.zrange("species.%s.populations.byBestFitness" % population.species_id, 0, 0)[0])
            worst_population = RedisPopulation(population.species_id, worst_population_id)
            new_individual_ids = []
            for ind in inds:
                for tries in range(0,10):
                    individual_to_kill = worst_population.get_random_individual(biased=False)
                    if individual_to_kill not in new_individual_ids:
                        redis_lua_scripts.die(individual_to_kill.species_id, individual_to_kill.population_id, individual_to_kill.individual_id) #use diretct method here to not tigger afterIndividualDeath()
                        break
                individual_id = random.randint(1000,individual_id_range)  
                new_individual_ids.append(individual_id)                
                redis_lua_scripts.createIndividual( worst_population.species_id, worst_population.population_id, individual_id, "", ind["code"])
            
            
    @staticmethod
    def onPopulationsizeUnderflow(population):
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.max_populationsize" % population.species_id)
        pipe.zcount("population.%s.individuals.allByFitness" % population.population_id,"-inf","inf")
        max_populationsize, nr_of_individuals = [int(r) for r in pipe.execute()]
        while nr_of_individuals < max_populationsize - 5:
            EvolutionaryMethods.create_new_individual(population)
            nr_of_individuals = redisconnection.zcount("population.%s.individuals.allByFitness" % population.population_id,"-inf","inf")

        
    @staticmethod
    def onPopulationsizeOverflow(population):
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.max_populationsize" % population.species_id)
        pipe.zcount("population.%s.individuals.allByFitness" % population.population_id,"-inf","inf")
        max_populationsize, nr_of_individuals = [int(r) for r in pipe.execute()]
        while nr_of_individuals > max_populationsize:
            print("must kill")
            individual_index = randomchoice.selectLinear(nr_of_individuals, 30)
            try:
                individual_id = int(float(redisconnection.zrange("population.%s.individuals.allByFitness" % population.population_id, individual_index, individual_index)[0]))
                RedisIndividual(population.species_id, population.population_id, individual_id).die()
                nr_of_individuals = redisconnection.zcount("population.%s.individuals.allByFitness" % population.population_id,"-inf","inf")
            except:
                print("kill failed")
                
    @staticmethod     
    def create_new_individual(population):
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.min_populationsize" % population.species_id)
        pipe.zcount("population.%s.individuals.allByFitness"    % population.population_id,"-inf","inf")
        pipe.zcount("population.%s.individuals.adultsByFitness" % population.population_id,"-inf","inf")
        min_populationsize, nr_of_individuals, nr_of_adults = [int(r) for r in pipe.execute()]
        
        if random.random() < 0.01 or nr_of_individuals <  min_populationsize or nr_of_adults < 10 or stackdepth_limit_hit() == True:
            EvolutionaryMethods.create_new_random_individual(population )
        else:
            EvolutionaryMethods.create_new_mate_individual(population)

    @staticmethod     
    def create_new_random_individual(population):
        #print("create_new_random_individual")
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.max_code_length" % population.species_id)
        pipe.get("species.%s.min_code_length" % population.species_id)
        max_code_length, min_code_length = [int(r) for r in pipe.execute()]
        
        length = random.randint(min_code_length, max_code_length)
        code = bytes([byteFuckHelper.get_random_byte() for _ in range(0,length)])
        EvolutionaryMethods._save_new_individual(population, "", code)
        
        
    @staticmethod     
    def create_new_mate_individual(population):
        #print("create_new_mate_individual")
        nr_of_individuals = int(redisconnection.zcount("population.%s.individuals.adultsByFitness" % population.population_id,"-inf","inf"))        
        if nr_of_individuals <= 10:
            return 
        
        individual_ids = []
        for i in range(0,2):
            try:
                individual_index = randomchoice.selectLinear(nr_of_individuals, 23, reverse = True)
                individual_id = int(float(redisconnection.zrange("population.%s.individuals.adultsByFitness" % population.population_id, individual_index, individual_index)[0]))
                individual_ids.append(individual_id)
            except Exception as e:
                print("mate fail")
                return
        EvolutionaryMethods._mate_mutate_indivials(population, individual_ids)
            

    @staticmethod     
    def _mate_mutate_indivials(population, individual_ids):       
        data = {}
        for index, individual_id in enumerate(individual_ids):
            index = "%s" % index
            data[index] = {}
            data[index]["code"] = redisconnection.get("individual.%s.code" % individual_id)
            data[index]["fitness_relative"] = redisconnection.get("individual.%s.fitness_relative_adult" % individual_id)
            if data[index]["code"] == None or data[index]["fitness_relative"] == None:
                print("mate fail1")
                return
        pipe = redisconnection.pipeline()
        pipe.get("species.%s.max_code_length" % population.species_id)
        pipe.get("species.%s.min_code_length" % population.species_id)
        max_code_length, min_code_length = [int(r) for r in pipe.execute()]
                        
        for i in range(0,10):
            selected_matemutator = evolutionMateMutate.get_random_individual()
            new_code = selected_matemutator.execute(bson.dumps(data))
            if len(new_code) > max_code_length:
                new_code = new_code[0:max_code_length]
            if len(new_code) > 3:
                return EvolutionaryMethods._save_new_individual(population, selected_matemutator.getIdentifier(), new_code)
                 
            else:
                selected_matemutator.addFitness(0)
       
    @staticmethod     
    def _save_new_individual( population, matemutator_id, code):
        individual_id = random.randint(1000,individual_id_range)            
        individuals_created_species, individuals_created_pop  = redis_lua_scripts.createIndividual( population.species_id, population.population_id, individual_id, matemutator_id, code)
        EvolutionaryMethods.onIndividualCreated(population, int(individuals_created_species), int(individuals_created_pop))
        return individual_id
        
brainlogic.redis_models.evolutionaryMethods = EvolutionaryMethods

  
     
     