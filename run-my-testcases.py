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

from brainlogic.EvolutionApi import Evolution
from brainlogic.EvolutionApi import EvolutionTraining
from brainlogic.EvolutionApi import EvolutionReplacement


DEFAULT_TRAIN_STEPS = 25000


def trainMutation(species_name, problemdefinition):
    mutationevolution = Evolution(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 10 , # max number of parallel populations
        min_populationsize = 50, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 100, #
        min_fitness_evaluations = 1, #
        max_fitness_evaluations = 5, #        
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        usePriorKnowledge = False,
        useP2P = False,
        warmup = False,
    )

    for _ in range(0,DEFAULT_TRAIN_STEPS):
        selected_individual = mutationevolution.species.getRandomIndividual()
        my_code = selected_individual.get_value("code", default = None)
        result = selected_individual.execute("mutate", { "my code" : my_code})[0:max([len(my_code) * 5, 100])]
        fitness = reward.absolute_distance_reward(result, my_code, 256)
        #print(fitness)
        if fitness > 0.9:
            fitness = 0.9 - (fitness - 0.9)
        #print(fitness)
        selected_individual.addFitness(fitness)     

    mutationevolution.save()
    mutationevolution.close() 

def trainMate(species_name, problemdefinition):
    mutationevolution = Evolution(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 10 , # max number of parallel populations
        min_populationsize = 50, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 100, #
        min_fitness_evaluations = 1, #
        max_fitness_evaluations = 5, #        
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        usePriorKnowledge = False,
        useP2P = False,
        warmup = False,
    )

    for _ in range(0,DEFAULT_TRAIN_STEPS):
        selected_individual = mutationevolution.species.getRandomIndividual()
        other_individual = mutationevolution.species.getRandomIndividual()
        my_code = selected_individual.get_value("code", default = None)
        other_code = other_individual.get_value("code", default = None)
        other_memory = other_individual.get_value("memory", default = None)
        result = selected_individual.execute("mate", { "other code" : other_code, "other memory" : other_memory , "my code" : my_code})[0:max([len(other_code) * 4, 100, len(my_code) * 4])]
        fitness =  reward.absolute_distance_reward(result, my_code   , 256)
        fitness += reward.absolute_distance_reward(result, other_code, 256)
        fitness += SequenceMatcher(None, result, my_code).ratio()
        fitness += SequenceMatcher(None, result, other_code).ratio()
        fitness /= 4.0
        #print(fitness)
        if fitness > 0.9:
            fitness = 0.9 - (fitness - 0.9)
        #print(fitness)
        selected_individual.addFitness(fitness)     

    mutationevolution.save()
    mutationevolution.close()     
    
def trainSelfAware(species_name, problemdefinition):
    selffitnessevolution = Evolution(
        species_name = species_name, 
        problem_name =   problemdefinition["problem_name"], 
        problem_description =  problemdefinition["problem_description"],
        
        max_populations = 10 , # max number of parallel populations
        min_populationsize = 50, # min number of living individuals per population, create random inds if lower
        max_populationsize = 250, # max number of living individuals per population
        min_code_length = 10, #
        max_code_length = 100, #
        min_fitness_evaluations = 1, #
        max_fitness_evaluations = 5, #        
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        usePriorKnowledge = False,
        useP2P = False,
        warmup = False,
    )

    for _ in range(0,DEFAULT_TRAIN_STEPS):
        selected_individual = selffitnessevolution.species.getRandomIndividual()
        value = selected_individual.get_value(problemdefinition["redis_key"], default = problemdefinition["redis_key_default_value"])
        result = selected_individual.execute(problemdefinition["name"], "")[0:max([len(value) * 4, 100])]
        fitness = (reward.absolute_distance_reward(result, value, 256) + SequenceMatcher(None, result, value).ratio()) / 2.0
        selected_individual.addFitness(fitness)     

    selffitnessevolution.save()
    selffitnessevolution.close() 
    
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
        min_fitness_evaluations = 2, #
        max_fitness_evaluations = 15, #          
        max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
        max_permanent_memory = 1000, # max perm memory stored in             
        max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
        usePriorKnowledge = False,
        useP2P = False,
        warmup = False,
    )
    
    evolution.trainByExample(problemdefinition["examplesource"], maxsteps = DEFAULT_TRAIN_STEPS)
    evolution.save()
    evolution.close()
    

class GymTrainer():

    def run(self, species_name, problemdefinition):
        gymvolution = EvolutionReplacement(
            species_name = species_name, 
            problem_name =   problemdefinition["problem_name"], 
            problem_description =  problemdefinition["problem_description"],
            
            max_populations = 10 , # max number of parallel populations
            min_populationsize = 50, # min number of living individuals per population, create random inds if lower
            max_populationsize = 250, # max number of living individuals per population
            min_code_length = 10, #
            max_code_length = 200, #
            min_fitness_evaluations = 1, #
            max_fitness_evaluations = 5, #              
            max_memory = 1000 * 1000, # max memory positions per memory type (char, int, float)
            max_permanent_memory = 1000, # max perm memory stored in             
            max_steps = 10 * 1000 * 1000, # executed steps of code per individual 
            usePriorKnowledge = False,
            useP2P = False,
            warmup = problemdefinition["warmup"],
        )
        @gymvolution.replace
        def dummyagent(observation):
            output = self.action_to_bson(env.action_space.sample())
            return output
        env = gym.make(problemdefinition["env_name"]) 

        for i_episode in range(DEFAULT_TRAIN_STEPS):
            observation = env.reset()
            lastreward = 0
            for t in range(5):
                observation_bjson = self.observation_to_bson(observation)
                action_bson = dummyagent(observation_bjson)
                try:
                    action = self.bson_to_action(action_bson)
                except Exception as e:
                    print("Failed to load action : %s" % e)
                    lastreward = 0
                    break
                observation, reward, done, info = env.step(action)
                lastreward = reward
                if done:
                    #print("Episode finished after {} timesteps".format(t+1))
                    break
            gymvolution.replaceReward(lastreward)

        gymvolution.save()
        gymvolution.close()
                 
    def convertToPy(self,value):
        if type(value) == numpy.ndarray:
            return {"ndarray"  : value.tolist()}
        if type(value) == numpy.int64:
            return {"npint64"  :  value.item() }
        if type(value) == numpy.int32:
            return {"npint32"  : value.item() }
        if type(value) == int:
            return {"int"  : value}
        if type(value) == float:
            return {"float"  :  value}
        if type(value) == bool:
            return {"bool"  :  value}
        if type(value) == tuple:
            return {"tuple"  :  [self.convertToPy(item) for item in value]}
        raise Exception("no converter to py found for type %s" % (type(value)))
        
    def convertToEnv(self,value):
        if type(value) == dict:
            key = list(value.keys())[0]
            if key == "ndarray":
                return numpy.array(value[key])
            if key == "npint64":       
                return numpy.int64(value[key])
            if key == "int":       
                return value[key]
            if key == "float":       
                return value[key]
            if key == "bool":       
                return value[key]               
            if key == "tuple":       
                return [self.convertToEnv(item) for item in value[key]]
        raise Exception("no converter to env found for type %s" % (type(value)))
      
    def observation_to_bson(self,observation): 
        converted_observation = self.convertToPy(observation)
        return bson.dumps({"observation" : converted_observation })
        
    def action_to_bson(self,action): 
        converted_action = self.convertToPy(action)
        return bson.dumps({"action" : converted_action })
        
    def bson_to_action(self,actionbson): 
        action = bson.loads(actionbson)["action"]
        return self.convertToEnv(action)
             

    
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
  
'''
## Selfawareness, report own fitness and more
problems["selfawareness get fitness"] = {
    "name" : "selfawareness get fitness",
    "description" : "selfawareness get fitness",
    "redis_key" : "fitness",
    "redis_key_default_value" : b"0.0",
    "trainingfunction" : trainSelfAware
}
problems["selfawareness get fitness evaluations"] = {
    "name" : "selfawareness get fitness evaluations",
    "description" : "selfawareness get fitness evaluations",
    "redis_key" : "fitness_evaluations",
    "redis_key_default_value" : b"0",
    "trainingfunction" : trainSelfAware
}
problems["selfawareness get relative fitness"] = {
    "name" : "selfawareness get relative fitness",
    "description" : "selfawareness get relative fitness",
    "redis_key" : "fitness_relative",
    "redis_key_default_value" : b"0.0",
    "trainingfunction" : trainSelfAware
}
problems["selfawareness get executions"] = {
    "name" : "selfawareness get executions",
    "description" : "selfawareness get executions",
    "redis_key" : "executions",
    "redis_key_default_value" : b"0",
    "trainingfunction" : trainSelfAware
}
problems["selfawareness get code"] = {
    "name" : "selfawareness get code",
    "description" : "selfawareness get code",
    "redis_key" : "code",
    "redis_key_default_value" : b"",
    "trainingfunction" : trainSelfAware
}
'''

'''
## OpenAI algorithms
problems['Copy-v0'] = {
    "name" : 'Copy-v0',
    "description" : 'Copy-v0',
    "env_name" : 'Copy-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['DuplicatedInput-v0'] = {
    "name" : 'DuplicatedInput-v0',
    "description" : 'DuplicatedInput-v0',
    "env_name" : 'DuplicatedInput-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['RepeatCopy-v0'] = {
    "name" : 'RepeatCopy-v0',
    "description" : 'RepeatCopy-v0',
    "env_name" : 'RepeatCopy-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['Reverse-v0'] = {
    "name" : 'Reverse-v0',
    "description" : 'Reverse-v0',
    "env_name" : 'Reverse-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['ReversedAddition-v0'] = {
    "name" : 'ReversedAddition-v0',
    "description" : 'ReversedAddition-v0',
    "env_name" : 'ReversedAddition-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['ReversedAddition3-v0'] = {
    "name" : 'ReversedAddition3-v0',
    "description" : 'ReversedAddition3-v0',
    "env_name" : 'ReversedAddition3-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}


## OpenAI classic control
problems['Acrobot-v1'] = {
    "name" : 'Acrobot-v1',
    "description" : 'Acrobot-v1',
    "env_name" : 'Acrobot-v1',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}

problems['CartPole-v0'] = {
    "name" : 'CartPole-v0',
    "description" : 'CartPole-v0',
    "env_name" : 'CartPole-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['MountainCar-v0'] = {
    "name" : 'MountainCar-v0',
    "description" : 'MountainCar-v0',
    "env_name" : 'MountainCar-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['MountainCarContinuous-v0'] = {
    "name" : 'MountainCarContinuous-v0',
    "description" : 'MountainCarContinuous-v0',
    "env_name" : 'MountainCarContinuous-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['Pendulum-v0'] = {
    "name" : 'Pendulum-v0',
    "description" : 'Pendulum-v0',
    "env_name" : 'Pendulum-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}

### OpenAI TOY TEXT
problems['Blackjack-v0'] = {
    "name" : 'Blackjack-v0',
    "description" : 'Blackjack-v0',
    "env_name" : 'Blackjack-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['FrozenLake-v0'] = {
    "name" : 'FrozenLake-v0',
    "description" : 'FrozenLake-v0',
    "env_name" : 'FrozenLake-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['FrozenLake8x8-v0'] = {
    "name" : 'FrozenLake8x8-v0',
    "description" : 'FrozenLake8x8-v0',
    "env_name" : 'FrozenLake8x8-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['GuessingGame-v0'] = {
    "name" : 'GuessingGame-v0',
    "description" : 'GuessingGame-v0',
    "env_name" : 'GuessingGame-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['HotterColder-v0'] = {
    "name" : 'HotterColder-v0',
    "description" : 'HotterColder-v0',
    "env_name" : 'HotterColder-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['NChain-v0'] = {
    "name" : 'NChain-v0',
    "description" : 'NChain-v0',
    "env_name" : 'NChain-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['Roulette-v0'] = {
    "name" : 'Roulette-v0',
    "description" : 'Roulette-v0',
    "env_name" : 'Roulette-v0',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['Taxi-v2'] = {
    "name" : 'Taxi-v2',
    "description" : 'Taxi-v2',
    "env_name" : 'Taxi-v2',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}


## OpenAI BOX 2d
problems['BipedalWalker-v2'] = {
    "name" : 'BipedalWalker-v2',
    "description" : 'BipedalWalker-v2',
    "env_name" : 'BipedalWalker-v2',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['BipedalWalkerHardcore-v2'] = {
    "name" : 'BipedalWalkerHardcore-v2',
    "description" : 'BipedalWalkerHardcore-v2',
    "env_name" : 'BipedalWalkerHardcore-v2',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
#problems['CarRacing-v0'] = { # requires display :(
#    "name" : 'CarRacing-v0',
#    "description" : 'CarRacing-v0',
#    "env_name" : 'CarRacing-v0',
#    "warmup" : True,
#    "trainingfunction" : GymTrainer().run
#}
problems['LunarLander-v2'] = {
    "name" : 'LunarLander-v2',
    "description" : 'LunarLander-v2',
    "env_name" : 'LunarLander-v2',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}
problems['LunarLanderContinuous-v2'] = {
    "name" : 'LunarLanderContinuous-v2',
    "description" : 'LunarLanderContinuous-v2',
    "env_name" : 'LunarLanderContinuous-v2',
    "warmup" : True,
    "trainingfunction" : GymTrainer().run
}


problems['mutation warmup'] = {
    "name" : 'mutation warmup',
    "description" : 'mutation',
    "trainingfunction" : trainMutation
}
problems['mate warmup'] = {
    "name" : 'mate warmup',
    "description" : 'mate',
    "trainingfunction" : trainMate
}
'''
[print("%s"% x)  for x in training_problems]
print("%s Problems known" % len(training_problems))

def training_thread(nrOfTrainingRuns):
    while nrOfTrainingRuns > 0:
        selected_problem = random.choice(training_problems)
        print("selected_problem: %s" % selected_problem)
        run_training_problem(selected_problem)
        nrOfTrainingRuns -= 1
   
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
    for _ in range(0,nrofThreads):
        time.sleep(3)
        t = threading.Thread(target=training_thread,args = [nrOfTrainingRuns])
        t.start()   
        
main()       
#import cProfile
#import re
#cProfile.run('main()')
