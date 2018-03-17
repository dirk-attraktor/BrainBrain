import os
import random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
django.setup()
from brainweb import brainfuck
from django.db.models import F
from brainweb import models
from brainweb.models import Evolution
from brainweb.models import Problem
from brainweb.models import Population
from brainweb.models import Individual

import google_testcases

    
problem = Evolution.initializeProblem("dafunction")
@problem.evolve
def dafunction(input):
    return "%s" % (input+1)

def runtestfoo():
    for i in range(0,5):
        print(i)
        r = dafunction(i)
        
        print(r)
        problem.reward(len(r))
    for i in range(0,5):
        print(i)
        r = dafunction(i)
        problem.reward(len(r))
runtestfoo()


data =  [
    ([1, 20, 6], [1, 6, 20]),
    ([13, 6, 7], [6, 7, 13]),
    ([24, 2, 23], [2, 23, 24]),
    ([16, 12, 3], [3, 12, 16]),
    ([11, 24, 4], [4, 11, 24]),
    ([10, 1, 19], [1, 10, 19])
    ]
problem1 = Evolution.initializeProblem("regress")










