import os, sys
sys.dont_write_bytecode = True

import random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django

django.setup()
from django.db.models import F
from brainweb import models
from brainweb.models import Problem
from brainweb.models import Population
from brainweb.models import Individual
import reward
import google_testcases

import misc
import ga 
from ga import Regression
from ga import Evolution

import cProfile


def train(taskname):
    print("Running Task '%s'" % taskname)
    
    if taskname not in google_testcases.task_mapping:
        print("Task %s not found" % taskname)
        return 
        
    task_cls, kwargs = google_testcases.task_mapping[taskname]
    task = task_cls(**kwargs)    

    def fitnessF(individual):
        io_seqs = task.make_io_set()
        score = ga.score_individual(individual, io_seqs)
        return score
        
    problem_regression = Regression("google_testcases-%s" % taskname, max_generations = -1, max_individuals = 100000,max_populationsize = 100, max_code_length=100,min_code_length=100,max_steps = 5000,usePriorKnowledge=False)
    #problem_regression.problem.sync_to_database = True
    problem_regression.regress(fitnessF)
    problem_regression.save()
    avg_endfitness = problem_regression.selected_population.average_fitness
    max_endfitness = problem_regression.selected_population.best_fitness
    
   
    print("%s Individuals created" % problem_regression.selected_population.individual_count)
    print("max fit for population: %s" % max_endfitness)
    print("avg_endfitness: %s" % avg_endfitness)
    
    
if __name__ == "__main__":
    try:
        cmd = sys.argv[1]
    except:
        cmd = "show"
    
    if cmd == "show":
        print("Available Google Testcases")
        print(google_testcases.task_mapping.keys())
        print("Usage:")
        print(" run        # run random task")
        print(" run all    # run all tasks")
        print(" run <name> # run taskname")
    if cmd == "warmup":
        warmup()
    if cmd == "run":
        print("running")
        try:
            testname = sys.argv[2]
        except:
            testname = "random"
            
        if testname == "all":
            for taskname in list(google_testcases.task_mapping.keys()):
                train(taskname)
        else:    
            if testname == "random":
                testname = random.choice(list(google_testcases.task_mapping.keys()))
            if testname == "doit":
                for i in range(0,10000):
                    testname = random.choice(list(google_testcases.task_mapping.keys()))
                    train(testname)
                    
            #cProfile.run("train(testname)")
            train(testname)



