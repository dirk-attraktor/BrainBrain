import os, sys
import random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django

django.setup()
from brainweb import brainfuck
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
    task = google_testcases.make_task(
        taskname, override_kwargs = None, 
        max_code_length = 50, 
        require_correct_syntax = False,
        do_code_simplification = False, 
        correct_bonus = 0.0, 
        code_length_bonus = 0.0
    )
                  
    def fitnessF(individual):
        return sum(task._score_individual(individual).episode_rewards)
    
    problem_regression = Regression("google_testcases-%s" % taskname, max_generations = -1, max_individuals = 100000,max_populationsize = 100, max_code_length=20,min_code_length=20,max_steps = 500,usePriorKnowledge=False)
    #problem_regression.problem.sync_to_database = True
    startfitness = problem_regression.selected_population.getFitnessStats()
    problem_regression.regress(fitnessF)
    problem_regression.save()
    endfitness = problem_regression.selected_population.getFitnessStats()
    
    print("%s Individuals created" % problem_regression.selected_population.individual_count)
    print("max fit for population: %s" % endfitness["max"])
    if problem_regression.selected_population.individual_count > 0:
        fpi = endfitness["max"] / float(problem_regression.selected_population.individual_count)
    else:
        fpi = -1
    maxDiffFitness = endfitness["max"] - startfitness["max"]
    avgDiffFitness = endfitness["avg"] - startfitness["avg"]
    print("startfitness: %s" % startfitness)
    print("endfitness: %s" % endfitness)
    print("maxDiffFitness: %s" % maxDiffFitness)
    print("avgDiffFitness: %s" % avgDiffFitness)
    print("fitness per individual %s" % fpi)
    
    
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



