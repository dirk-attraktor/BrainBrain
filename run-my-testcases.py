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

from libs import reward
from braintrain import google_testcases
from braintrain import simple_testcases

import brainlogic.EvolutionApi
from brainlogic.EvolutionApi import Evolution
from brainlogic.EvolutionApi import EvolutionTraining
from brainlogic.EvolutionApi import EvolutionReplacement

DEFAULT_TRAIN_STEPS = 25000

def trainByExample(species_name, problemdefinition):
    evolution = EvolutionTraining(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 10 , # max number of parallel populations
        min_populationsize = 150, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 300, #
        max_compiled_code_length = 300, #
        min_fitness_evaluations = 2, #
        max_fitness_evaluations = 15, #          
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        useP2P = True,
        warmup = False,
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

def run_training_problem(training_problem):
    species_name = training_problem["species_name"]
    selected_problemdefinition = random.choice(training_problem["problemdefinitions"])
    trainingfunction = selected_problemdefinition["trainingfunction"]
    trainingfunction(species_name, selected_problemdefinition)
  

[print("%s"% x)  for x in training_problems]
print("%s Problems known" % len(training_problems))

def training_thread(nrOfTrainingRuns):
    while nrOfTrainingRuns > 0:
        selected_problem = random.choice(training_problems)
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
