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
            useP2P = True,
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