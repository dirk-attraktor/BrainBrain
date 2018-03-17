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

            
training_problem = Evolution("create_training_problem", max_generations = -1, max_individuals = -1,max_populationsize = 100,referenceFunctionRate=0,min_fitness_evaluation_per_individual=1,max_code_length = 100, min_code_length = 10,)
@training_problem.evolve   
def default_training_problem(input):
    return input

def advtain():
    None
    inputs = ["".join([random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(0,random.randint(1,10))]) for _ in range(0,20)]
    try:
        [bytearray(default_training_problem(x),"ASCII") for x in inputs ]
        io_seqs = [[x,default_training_problem(x)] for x in inputs ]#)
    except Exception as e:
        training_problem.reward(-1) 
        training_problem.save()
        print("GENERATOR FAILED %s " % e)
        return 
        
    def fitnessF(individual):
        try:
            f =  ga.score_individual(individual,io_seqs)
            return f
        except Exception as e:
            #print("fitnessF FAILED %s " % e)
            return -1
            
    solvecount = 0    
    tries = 5
    for _ in range(0,tries):
        problem = Regression("solve_training_problem" , max_generations = -1, max_individuals = 1000,max_populationsize = 100, max_code_length=20,min_code_length=20,max_steps = 500, usePriorKnowledge = False,useP2P = False)    
        problem.regress(fitnessF)
        problem.save()
        endfitness = problem.selected_population.getFitnessStats()   
        if endfitness["max"] == 1:
            solvecount +=1
    solverate = (1.0 / tries ) * solvecount
    training_problem_reward = solverate
    print("solverate : %s" % solverate)
    # optimal rate is 0.75, everything above gets punished
    if training_problem_reward >= 0.75:
        rest = training_problem_reward - 0.75
        training_problem_reward = 0.75 - rest
    training_problem.reward(training_problem_reward) 
    training_problem.save()
    # select random generator individual
    # create solver propulation
    # regress genator with solver population for 50k steps
    
for i in range(0,100): 
    advtain()
