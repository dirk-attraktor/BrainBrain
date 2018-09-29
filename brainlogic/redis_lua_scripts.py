import redis
import time

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)


'''
Dataset Available in redis:

stats.
    death.
        global.<timestamp>
    individuals_created.
        global.<timestamp>
        species.<id>.<timestamp>
        population.<id>.<timestamp>
        
    fitness_evaluations.
        global.<timestamp>
        species.<id>.<timestamp>
        population.<id>.<timestamp>
        
    executions.
        global.<timestamp>
        species.<id>.<timestamp>
        population.<id>.<timestamp>
    fitness.  # fitness 
        global.<timestamp>
        species.<id>.<timestamp>
        population.<id>.<timestamp>
    fitness_max.  # fitness 
        species.<id>.<timestamp>
        population.<id>.<timestamp>

species.
    <species_id>.
        min_populationsize
        max_populationsize
        min_code_length
        max_code_length
        max_memory
        max_permanent_memory
        populations.
            byTimespend     # 
            byBestFitness   # 

population.
    <population_id>.
        best_individual_id
        best_individual_fitness
        individuals_created
        timespend
        timespend_total
        fitness_relative
        fitness_evaluations
        fitness_evaluations_total
        individuals.
            allByFitness      # all inds by fitness
            allByTimespend    # all inds by time spend
            allByFitnessEvaluations  # all inds by nr of fitness evals
            adultsByFitness   # all inds where nr_of_evals >= min_fitness_evaluations and fitness > 0
            
individual.
    <individual_id>.
        alive
        species
        population
        code
        code_compiled
        compiler
        memory
        fitness
        fitness_sum
        fitness_relative_all
        fitness_relative_adult
        fitness_evaluations
        executions
        program_steps
        memory_usage
        execution_time      
      
'''

'''
redis key

    stats.death.global.' .. timestam
    stats.individuals_created.global.' .. timestamp
   
    stats.fitness_evaluations.global.' .. timestamp
    
    stats.executions.global.' .. timestamp  # updated in c 
    
    stats.fitness.global.' .. timestamp # gobal average fitness of all populations

    species.%s.min_populationsize
    species.%s.max_populationsize
    species.%s.min_code_length
    species.%s.max_code_length
    species.%s.max_memory
    species.%s.max_permanent_memory
    species.%s.populations.byTimespend
    species.%s.populations.byBestFitness
    
    population.%s.fitness_relative
    population.%s.best_individual_id
    population.%s.best_individual_fitness
    population.%s.individuals_created
    population.%s.timespend             # timespend for living inds
    population.%s.timespend_total       # total  timespend
    population.%s.fitness_evaluations   # total number of eval for living inds
    population.%s.fitness_evaluations_total   # total number of eval for living inds
    population.%s.individuals.allByFitness
    population.%s.individuals.adultsByFitness
    population.%s.individuals.allByTimespend
    
    individual.%s.alive
    individual.%s.species
    individual.%s.population
    individual.%s.code
    individual.%s.code_compiled
    individual.%s.compiler
    individual.%s.memory
    individual.%s.fitness
    individual.%s.fitness_sum
    individual.%s.fitness_relative_all
    individual.%s.fitness_relative_adult
    individual.%s.fitness_evaluations
    individual.%s.executions
    individual.%s.program_steps
    individual.%s.memory_usage
    individual.%s.execution_time
''' 


createIndividual_lua_script = redisconnection.register_script("""
    local species_id    = ARGV[1]
    local population_id = ARGV[2]
    local individual_id = ARGV[3]
    local matemutator_id = ARGV[4]
    local code    = ARGV[5]
    local timestamp    = ARGV[6]
    
    local individualid = "individual." .. individual_id
    
    redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByFitness',   0, individual_id) 
    redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByTimespend', 0, individual_id) 
    redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByFitnessEvaluations', 0, individual_id) 
    
    redis.call('SET', individualid .. '.matemutator', matemutator_id) 
    redis.call('SET', individualid .. '.species'    , species_id) 
    redis.call('SET', individualid .. '.population' , population_id) 
    redis.call('SET', individualid .. '.code'       , code) 
    redis.call('SET', individualid .. '.alive'      , 1) 
    
    redis.call('INCR', 'species.'    ..  species_id .. '.individuals_created')  
    redis.call('INCR', 'population.' .. population_id .. '.individuals_created')  
    
    redis.call('INCR',   'stats.individuals_created.global.' .. timestamp)
    redis.call('EXPIRE', 'stats.individuals_created.global.' .. timestamp, 3600*72)  
    redis.call('INCR',   'stats.individuals_created.species.' .. species_id .. '.' .. timestamp)
    redis.call('EXPIRE', 'stats.individuals_created.species.' .. species_id .. '.' .. timestamp, 3600*72)  
    redis.call('INCR',   'stats.individuals_created.population.' .. population_id .. '.' .. timestamp)
    redis.call('EXPIRE', 'stats.individuals_created.population.' .. population_id .. '.' .. timestamp, 3600*72)  

    
    
    local individuals_created_species    = tonumber(redis.call('GET','species.' .. species_id .. '.individuals_created'))
    local individuals_created_population = tonumber(redis.call('GET','population.' .. population_id .. '.individuals_created'))
    
    return { 
            tostring(individuals_created_species),
            tostring(individuals_created_population),
        }
""")


def createIndividual(species_id, population_id, individual_id, matemutator_id, code):
    timestamp = time.time()
    timestamp = int(timestamp - (timestamp % 60))
    r = createIndividual_lua_script(
        keys=[], 
        args=[
            species_id,    # 1
            population_id, # 2 
            individual_id, # 3
            matemutator_id, # 4
            code,    # 5
            timestamp,    # 6
        ]
    )     
    return r
    
setIndividualCompiledCode_lua_script = redisconnection.register_script("""
    local individual_id = ARGV[1]
    local code_compiled = ARGV[2]
    local compiler = ARGV[3]
    local isAlive = redis.call('GET','individual.' .. individual_id .. '.alive') 
    if (isAlive) then
        if code_compiled == "" then
            redis.call('DEL','individual.' .. individual_id .. '.code_compiled'  ) 
        else
            redis.call('SET','individual.' .. individual_id .. '.code_compiled' , code_compiled ) 
        end
        redis.call('SET','individual.' .. individual_id .. '.compiler' , compiler )         
    end
""")     
def setIndividualCompiledCode(individual_id, compiled_code, compiler):
    return setIndividualCompiledCode_lua_script(
        keys=[], 
        args=[
            individual_id, # 1
            compiled_code, # 2
            compiler,    # 3
        ]
    ) 
    
    
    

processExecutionInstance_lua_script = redisconnection.register_script("""
    local instance_id   = ARGV[1]
    local individual_id = ARGV[2]
    local population_id = ARGV[3]
    local species_id    = ARGV[4]
    local instanceid = 'instance.' .. instance_id
    local individualid = 'individual.' .. individual_id
    local populationid = 'population.' .. population_id

    local isAlive = redis.call('GET', individualid .. '.alive') 
    if (isAlive) then
        redis.call('RENAME', instanceid .. '.memory' ,  individualid .. '.memory' ) 
        
        redis.call('INCR', individualid .. '.executions' ) 
        
        local program_steps  = redis.call('GET', instanceid .. '.program_steps') 
        redis.call('INCRBY', individualid .. '.program_steps', program_steps ) 
        
        local execution_time = redis.call('GET', instanceid .. '.execution_time') 
        redis.call('INCRBYFLOAT', individualid .. '.execution_time', execution_time ) 
        redis.call('INCRBYFLOAT', populationid .. '.timespend', execution_time ) 
        redis.call('INCRBYFLOAT', populationid .. '.timespend_total', execution_time ) 
        
        local memory_usage = redis.call('GET', instanceid .. '.memory_usage') 
        redis.call('INCRBY', individualid .. '.memory_usage', memory_usage ) 
        
        local execution_time_population =  redis.call('GET', populationid .. '.timespend_total')
        local execution_time_individual = redis.call('GET', individualid .. '.execution_time')         
        redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByTimespend', execution_time_individual, individual_id )
        redis.call('ZADD', 'species.' .. species_id .. '.populations.byTimespend', execution_time_population, population_id ) 
        
    end           
    local output = redis.call('GET', instanceid .. '.output')
    redis.call('DEL', instanceid .. '.individual_id')
    redis.call('DEL', instanceid .. '.input')
    redis.call('DEL', instanceid .. '.output')
    redis.call('DEL', instanceid .. '.memory')
    redis.call('DEL', instanceid .. '.program_steps')
    redis.call('DEL', instanceid .. '.memory_usage')
    redis.call('DEL', instanceid .. '.execution_time')
    redis.call('DEL', instanceid .. '.done')
    return output

""")  
    
def processExecutionInstance(species_id, population_id, individual_id, instanceid):
    return processExecutionInstance_lua_script(
        keys=[], 
        args=[
            instanceid,    # 1
            individual_id, # 2
            population_id, # 3 
            species_id,    # 4 
        ]
    ) 
    
    

addFitness_lua_script = redisconnection.register_script("""
    local species_id = ARGV[1]
    local population_id = ARGV[2]
    local individual_id = ARGV[3]
    local fitness_value = tonumber(ARGV[4])
    local timestamp = ARGV[5]
    
    local isAlive = redis.call('GET','individual.' .. individual_id .. '.alive') 
    if (isAlive) then
        redis.call('INCR',   'stats.fitness_evaluations.global.' .. timestamp)
        redis.call('EXPIRE', 'stats.fitness_evaluations.global.' .. timestamp, 3600*72)  
        redis.call('INCR',   'stats.fitness_evaluations.species.' .. species_id .. '.' .. timestamp)
        redis.call('EXPIRE', 'stats.fitness_evaluations.species.' .. species_id .. '.' .. timestamp, 3600*72)  
        redis.call('INCR',   'stats.fitness_evaluations.population.' .. population_id .. '.' .. timestamp)
        redis.call('EXPIRE', 'stats.fitness_evaluations.population.' .. population_id .. '.' .. timestamp, 3600*72)  

        redis.call('INCR', 'individual.' .. individual_id .. '.fitness_evaluations') 
        redis.call('INCR', 'population.' .. population_id .. '.fitness_evaluations' ) 
        redis.call('INCR', 'population.' .. population_id .. '.fitness_evaluations_total' )         
        redis.call('INCRBYFLOAT', 'individual.' .. individual_id .. '.fitness_sum', fitness_value) 
      
      
        local ind_fitness_relative_all = 0 
        local ind_fitness_relative_adult = 0 
        
        local max_fitness_evaluations = tonumber(redis.call('GET','species.' .. species_id .. '.max_fitness_evaluations'))
        local min_fitness_evaluations = tonumber(redis.call('GET','species.' .. species_id .. '.min_fitness_evaluations'))
        
        local ind_fitness             = tonumber(redis.call('GET','individual.' .. individual_id .. '.fitness_sum'))
        local ind_fitness_evaluations = tonumber(redis.call('GET','individual.' .. individual_id .. '.fitness_evaluations'))
        local ind_fitness_absolute = ind_fitness / ind_fitness_evaluations
        redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByFitness', ind_fitness_absolute, individual_id  ) 
        redis.call('ZADD', 'population.' .. population_id .. '.individuals.allByFitnessEvaluations', ind_fitness_evaluations, individual_id  ) 
        redis.call('SET', 'individual.' .. individual_id .. '.fitness', ind_fitness_absolute ) 
        
        if ind_fitness_evaluations >= min_fitness_evaluations and ind_fitness_absolute > 0 then
            redis.call('ZADD', 'population.' .. population_id .. '.individuals.adultsByFitness', ind_fitness_absolute, individual_id  )
            local nr_of_individuals_adult = tonumber(redis.call('ZCOUNT', 'population.' .. population_id .. '.individuals.adultsByFitness', '-inf', 'inf')) 
            local relative_fitness_index_adult =  tonumber(redis.call('ZRANK', 'population.' .. population_id .. '.individuals.adultsByFitness', individual_id) )
            ind_fitness_relative_adult = (1.0 / nr_of_individuals_adult) * ( relative_fitness_index_adult + 1 )
        else    
            redis.call('ZREM', 'population.' .. population_id .. '.individuals.adultsByFitness', individual_id  ) 
        end
                
        local nr_of_individuals_all   = tonumber(redis.call('ZCOUNT', 'population.' .. population_id .. '.individuals.allByFitness', '-inf', 'inf'))         
        local relative_fitness_index_all =  tonumber(redis.call('ZRANK', 'population.' .. population_id .. '.individuals.allByFitness', individual_id) )
        local ind_fitness_relative_all = (1.0 / nr_of_individuals_all) * ( relative_fitness_index_all + 1 )
        redis.call('SET', 'individual.' .. individual_id .. '.fitness_relative_all', ind_fitness_relative_all ) 
        redis.call('SET', 'individual.' .. individual_id .. '.fitness_relative_adult', ind_fitness_relative_adult ) 
        
        -- Calc pop best
        local nr_of_populations = tonumber(redis.call('ZCOUNT', 'species.' .. species_id .. '.populations.byTimespend', '-inf', 'inf'))
        local best_individual_id =  tonumber(redis.call('ZRANGE', 'population.' .. population_id .. '.individuals.adultsByFitness', -1, -1 )[1])
        local relative_population_fitness = 1
        if not (best_individual_id == nil) then
            local  best_individual_fitness = redis.call('GET', 'individual.' .. best_individual_id .. '.fitness')
            redis.call('ZADD', 'species.' .. species_id .. '.populations.byBestFitness', best_individual_fitness, population_id)
            local relative_population_fitness_index =  tonumber(redis.call('ZRANK', 'species.' .. species_id .. '.populations.byBestFitness', population_id) )
            relative_population_fitness = (1.0 / ( nr_of_populations - 1 ) ) * ( relative_population_fitness_index )
            redis.call('SET', 'population.' .. population_id .. '.best_individual_id'     , best_individual_id ) 
            redis.call('SET', 'population.' .. population_id .. '.best_individual_fitness', best_individual_fitness ) 
            redis.call('SET', 'population.' .. population_id .. '.fitness_relative', relative_population_fitness ) 
        end
        -- / Calc pop best
        
  
        return { 
            tostring(ind_fitness_relative_all),
            tostring(ind_fitness_relative_adult),
            tostring(ind_fitness_absolute),
            tostring(ind_fitness_evaluations),
            tostring(min_fitness_evaluations),
            tostring(max_fitness_evaluations),
            tostring(relative_population_fitness),
        }
    end
    return {}
""")   

def addFitness(species_id, population_id, individual_id, value):
    timestamp = time.time()
    timestamp = int(timestamp - (timestamp % 60))
    try:
        return addFitness_lua_script(
            keys=[], 
            args=[
                species_id,    # 1
                population_id, # 2 
                individual_id, # 3
                value,    # 4
                timestamp,    # 5
            ]
        )   
    except Exception as e:
        print(e)
        print("af:",species_id,population_id,individual_id ,value )
        exit(1)
  




addFitnessToReferenceFunction_lua_script = redisconnection.register_script("""
    local reference_function_id = ARGV[1]
    local fitness_value = tonumber(ARGV[2])
    local timestamp = ARGV[3]
    
    redis.call('INCR', 'referenceFunction.' .. reference_function_id .. '.fitness_evaluations') 
    redis.call('INCRBYFLOAT', 'referenceFunction.' .. reference_function_id .. '.fitness_sum', fitness_value) 
    
    local fitness_sum = tonumber(redis.call('GET','referenceFunction.' .. reference_function_id .. '.fitness_sum'))
    local fitness_evaluations = tonumber(redis.call('GET','referenceFunction.' .. reference_function_id .. '.fitness_evaluations'))
    
    local fitness = fitness_sum / fitness_evaluations
    
    redis.call('SET', 'referenceFunction.' .. reference_function_id .. '.fitness', fitness ) 
    
    redis.call('INCR',   'stats.fitness_evaluations.referenceFunction.' .. reference_function_id .. '.' .. timestamp)
    redis.call('EXPIRE', 'stats.fitness_evaluations.referenceFunction.' .. reference_function_id .. '.' .. timestamp, 3600*72)  

    return {}
""")   
def addFitnessToReferenceFunction(reference_function_id, value):
    timestamp = time.time()
    timestamp = int(timestamp - (timestamp % 60))
    try:
        return addFitnessToReferenceFunction_lua_script(
            keys=[], 
            args=[
                reference_function_id,    # 1
                value, # 2 
                timestamp,# 3
            ]
        )   
    except Exception as e:
        print(e)
        exit(1)
    






  
    
die_lua_script = redisconnection.register_script("""
    local species_id    = ARGV[1]
    local population_id = ARGV[2]
    local individual_id = ARGV[3]
    local timestamp = ARGV[4]
    local isAlive = redis.call('GET', 'individual.'..individual_id..'.alive')
    
    if (isAlive) then
        redis.call('INCR',   'stats.death.global.' .. timestamp)
        redis.call('EXPIRE', 'stats.death.global.' .. timestamp, 3600*72)
        redis.call('INCR',   'stats.death.species.' .. species_id .. '.' .. timestamp)
        redis.call('EXPIRE', 'stats.death.species.' .. species_id .. '.' .. timestamp, 3600*72)  
        redis.call('INCR',   'stats.death.population.' .. population_id .. '.' .. timestamp)
        redis.call('EXPIRE', 'stats.death.population.' .. population_id .. '.' .. timestamp, 3600*72)  

    
        local execution_time = tonumber(redis.call('GET', 'individual.' .. individual_id .. '.execution_time'))
        if execution_time == nil then
            execution_time = 0
        end
        if not (execution_time == 0) then
            execution_time = execution_time * -1
            redis.call('INCRBYFLOAT', 'population.' .. population_id .. '.timespend', execution_time) 
        end

        local fitness_evaluations = tonumber(redis.call('GET', 'individual.' .. individual_id .. '.fitness_evaluations'))
        if fitness_evaluations == nil then
            fitness_evaluations = 0
        end        
        if not (fitness_evaluations == 0) then
            fitness_evaluations = fitness_evaluations * -1
            redis.call('INCRBY', 'population.' .. population_id .. '.fitness_evaluations', fitness_evaluations)
        end
        
        
        redis.call('ZREM', 'population.' .. population_id .. '.individuals.adultsByFitness'  , individual_id)
        redis.call('ZREM', 'population.' .. population_id .. '.individuals.allByFitness'  , individual_id)
        redis.call('ZREM', 'population.' .. population_id .. '.individuals.allByTimespend', individual_id)
        redis.call('ZREM', 'population.' .. population_id .. '.individuals.allByFitnessEvaluations'  , individual_id)
        
        
    
        local population_timespend_total = redis.call('GET', 'population.' .. population_id .. '.timespend_total')
        redis.call('ZADD', 'species.' .. species_id .. '.populations.byTimespend', population_timespend_total, population_id)
        
        local id = 'individual.' .. individual_id
        redis.call('DEL', id .. '.alive')
        redis.call('DEL', id .. '.matemutator')
        redis.call('DEL', id .. '.species')
        redis.call('DEL', id .. '.population')
        redis.call('DEL', id .. '.code')
        redis.call('DEL', id .. '.code_compiled')
        redis.call('DEL', id .. '.compiler')
        redis.call('DEL', id .. '.memory')
        redis.call('DEL', id .. '.fitness')
        redis.call('DEL', id .. '.fitness_sum')
        redis.call('DEL', id .. '.fitness_relative_all')
        redis.call('DEL', id .. '.fitness_relative_adult')
        redis.call('DEL', id .. '.fitness_evaluations')
        redis.call('DEL', id .. '.executions')
        redis.call('DEL', id .. '.program_steps')
        redis.call('DEL', id .. '.memory_usage')
        redis.call('DEL', id .. '.execution_time')

        -- Calc pop best
        local nr_of_populations = redis.call('ZCOUNT', 'species.' .. species_id .. '.populations.byTimespend', '-inf', 'inf')
        local best_individual_id =  tonumber(redis.call('ZRANGE', 'population.' .. population_id .. '.individuals.adultsByFitness', -1, -1 )[1])
        local relative_population_fitness = 1
        if not (best_individual_id == nil) then
            local  best_individual_fitness = redis.call('GET', 'individual.' .. best_individual_id .. '.fitness')
            redis.call('ZADD', 'species.' .. species_id .. '.populations.byBestFitness', best_individual_fitness, population_id)
            local relative_population_fitness_index =  tonumber(redis.call('ZRANK', 'species.' .. species_id .. '.populations.byBestFitness', population_id) )
            relative_population_fitness = (1.0 / ( nr_of_populations - 1 ) ) * ( relative_population_fitness_index )
            redis.call('SET', 'population.' .. population_id .. '.best_individual_id'     , best_individual_id ) 
            redis.call('SET', 'population.' .. population_id .. '.best_individual_fitness', best_individual_fitness ) 
            redis.call('SET', 'population.' .. population_id .. '.fitness_relative', relative_population_fitness ) 
            
        end
        -- / Calc pop best        
        
    end 
    
""")  
def die(species_id, population_id, individual_id):
    timestamp = time.time()
    timestamp = int(timestamp - (timestamp % 60))
    r= die_lua_script(
        keys=[], 
        args=[
            species_id,    # 1
            population_id, # 2 
            individual_id, # 3
            timestamp, #4 
        ]
    )   
    return r
    
    
    
    
    
