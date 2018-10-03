import os, sys
sys.dont_write_bytecode = True

import random
import json
import bson
import string
import threading
import time
from difflib import SequenceMatcher
import gym
import numpy
import hashlib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
django.setup()

from libs import reward

from brainweb.models import Species

from braintrain import google_testcases
from braintrain import simple_testcases
from braintrain import data2data_testcases

import brainlogic.EvolutionApi
from brainlogic.EvolutionApi import Evolution
from brainlogic.EvolutionApi import EvolutionTraining
from brainlogic.EvolutionApi import EvolutionReplacement

DEFAULT_TRAIN_STEPS = 12000

def trainMemory(species_name, problemdefinition):
    evolution = EvolutionTraining(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 8 , # max number of parallel populations
        min_populationsize = 200, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 300, #
        max_compiled_code_length = 300, #
        min_fitness_evaluations = 3, #
        max_fitness_evaluations = 14, #          
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 100, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        useP2P = True,
        warmup = False,
        sync_cross_population_at =   80000,
        sync_cross_p2p_at        =  170000,
    )
    nrof_bytes_to_remember = problemdefinition["bytes_to_remember"]
    for _ in range(0,DEFAULT_TRAIN_STEPS):
        selected_individual = evolution.get_random_individual()
        fitness = 0
        count = 0
        for _ in range(0,1):
            # -> in [0 , byte0, byte1, ..] -> out ""
            # -> in [1 , index,index]  -> out  in[index,index]
            bytes_to_remember = bytes([0] + [random.randint(0,255) for _ in range(0,nrof_bytes_to_remember)])
            selected_individual.execute(bytes_to_remember)
            indexes_to_recall = [random.randint(0,nrof_bytes_to_remember-1) for _ in range(0,nrof_bytes_to_remember)]
            target_output_bytes = bytes([bytes_to_remember[indexes_to_recall[index]+1] for index in range(0,nrof_bytes_to_remember)])
            #print(bytes_to_remember)
            #print(indexes_to_recall)
            #print(target_output_bytes)
            recalled_bytes = selected_individual.execute(bytes([1] + indexes_to_recall))[0:nrof_bytes_to_remember*5]
            fitness += SequenceMatcher(None, recalled_bytes, target_output_bytes).ratio()
            fitness += reward.absolute_distance_reward(recalled_bytes,target_output_bytes,256)
            count += 2
        fitness /= count
        selected_individual.addFitness(fitness)     

    evolution.save()
    evolution.close()

def trainByExample(species_name, problemdefinition):
    evolution = EvolutionTraining(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 8 , # max number of parallel populations
        min_populationsize = 200, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 400, #
        max_compiled_code_length = 300, #
        min_fitness_evaluations = 3, #
        max_fitness_evaluations = 14, #          
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 0, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        useP2P = True,
        warmup = False,
        sync_cross_population_at =   30000,
        sync_cross_p2p_at        =   80000,
    )
    evolution.trainByExample(problemdefinition["examplesource"], maxsteps = DEFAULT_TRAIN_STEPS)
    evolution.save()
    evolution.close()
    

    
training_problems = []   
'''
# GOOGLE TESTPROBLEMS
for google_testcase_name in google_testcases.task_mapping.keys():
    n = "google-testcase %s" % google_testcase_name 
    training_problems.append({
        "species_name" : n,
        "problemdefinitions" : [
            {
                "problem_name" : n,
                "problem_description" : n,
                "examplesource" : google_testcases.get_examplesource(google_testcase_name),
                "trainingfunction" : trainByExample,
            },
        ],
    })
'''
# SIMPLE PER EXAMPLE TAINING  
for simple_testcase_name in simple_testcases.task_mapping.keys():
    training_problems.append({
        "species_name" : simple_testcase_name,
        "problemdefinitions" : [
            {
                "problem_name" : simple_testcase_name,
                "problem_description" : simple_testcase_name,
                "examplesource" : simple_testcases.get_examplesource(simple_testcase_name),
                "trainingfunction" : trainByExample,
            },
        ],
    })
    
# data2data PER EXAMPLE TAINING  
for data2data_testcase in data2data_testcases.task_mapping.keys():
    training_problems.append({
        "species_name" : data2data_testcase,
        "problemdefinitions" : [
            {
                "problem_name" : data2data_testcase,
                "problem_description" : data2data_testcase,
                "examplesource" : data2data_testcases.get_examplesource(data2data_testcase),
                "trainingfunction" : trainByExample,
            },
        ],
    })    
    
# train permanent memory
for bytes_to_remember in range(1,4):
    pname = "remember %s bytes" % bytes_to_remember
    training_problems.append({
        "species_name" : pname,
        "problemdefinitions" : [
            {
                "problem_name" : pname,
                "problem_description" : pname,
                "bytes_to_remember" : bytes_to_remember,
                "trainingfunction" : trainMemory,
            },
        ],
    }) 
      
    
'''
training_problems.append({
    "species_name" : "my-testcase add/sub 2 integer",
    "problemdefinitions" : [
        {
            "problem_name" : "my-testcase add 2 integer",
            "problem_description" : "my-testcase add 2 integer",
            "examplesource" : simple_testcases.get_examplesource("my-testcase add 2 integer"),
            "trainingfunction" : trainByExample,
        },
        {
            "problem_name" : "my-testcase sub 2 integer",
            "problem_description" : "my-testcase sub 2 integer",
            "examplesource" : simple_testcases.get_examplesource("my-testcase add 2 integer"),
            "trainingfunction" : trainByExample,
        },        
    ],
})  
  '''

training_problems = sorted(training_problems, key=lambda k: k['species_name']) 
print("%s Problems known" % len(training_problems))
for training_problem in training_problems:
    print(training_problem["species_name"])
time.sleep(2)


def run_training_problem(training_problem):
    species_name = training_problem["species_name"]
    selected_problemdefinition = random.choice(training_problem["problemdefinitions"])
    trainingfunction = selected_problemdefinition["trainingfunction"]
    trainingfunction(species_name, selected_problemdefinition)
  


#p = [x for x in training_problems if x["species_name"] == "data2data byte from bson dict"][0]
#p = [x for x in training_problems if x["species_name"] ==  "data2data byte at index"][0]
#p = [x for x in training_problems if x["species_name"] ==  "data2data byte from bson dict"][0]
#p = [x for x in training_problems if x["species_name"] ==  "data2data bytes from bson dict"][0]
#print(p)
#run_training_problem(p)
#exit(0)

max_parallel_unsolved_problems = 100
def training_thread(nrOfTrainingRuns):
    mtraining_problems = sorted(training_problems, key=lambda k: hashlib.md5(k['species_name'].encode()).hexdigest()) 
    while nrOfTrainingRuns > 0:
        unsolved_training_problems = []
        solved_training_problems = []
        for training_problem in mtraining_problems:
            try:
                species = Species.objects.get(name=training_problem["species_name"])
            except:
                species = None
            if species == None or species.solved == False:
                unsolved_training_problems.append(training_problem)
            else:
                solved_training_problems.append(training_problem)
            if len(unsolved_training_problems) >= max_parallel_unsolved_problems * 0.9:
                break
                
        if len(solved_training_problems) >  int(max_parallel_unsolved_problems * 0.1):
            solved_training_problems = random.sample(solved_training_problems, int(max_parallel_unsolved_problems * 0.1))
            
        selected_problem = random.choice(unsolved_training_problems + solved_training_problems)
        print("selected_problem: %s" % selected_problem)
        run_training_problem(selected_problem)
        nrOfTrainingRuns -= 1
        
def profile():
    selected_problem = random.choice(training_problems)
    run_training_problem(selected_problem)
    
def main():
       
    nrofThreads = 1
    try:
        nrofThreads = int(sys.argv[1])
    except:
        None
    nrOfTrainingRuns = 1
    try:
        nrOfTrainingRuns = int(sys.argv[2])
    except:
        None
    print("Starting %s threads a %s runs" % (nrofThreads, nrOfTrainingRuns))
    time.sleep(3)
    ts = []
    for _ in range(0,nrofThreads):
        time.sleep(3)
        t = threading.Thread(target=training_thread,args = [nrOfTrainingRuns])
        t.start()   
        ts.append(t)
    for t in ts:
        t.join()
main()    

#ugly hack to cleanup
brainlogic.EvolutionApi.evolutionMateMutate.close()
brainlogic.EvolutionApi.evolutionCompiler.close()

#import cProfile
#import re
#cProfile.run('profile()')
