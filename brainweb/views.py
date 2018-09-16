from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.http import JsonResponse
import random
import redis
import json
import time
import datetime
# Create your views here.

from django.http import HttpResponse

from . import models

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

stats_keys = ["executions", "fitness_evaluations", "death", "individuals_created", "fitness", "fitness_max"]
def merge_stats(datas):
    datas_merged = [datas[-1][0],0,0,0,0,0,0]
    for index in range(1,len(stats_keys)+1):
        s = 0
        c = 0
        a = None
        for data in datas:
            if data[index] != None:
                s += data[index]
                c += 1
        if c != 0:
            a = s / c
        datas_merged[index] = a
    for x in range(-1,-3,-1):
        if datas_merged[x] != None:
            datas_merged[x] = ( datas_merged[x] * 100 )   # correct for fitness scale from 0..1 to log 1..100
    return datas_merged
   
def getStats(keyname):
    ti = time.time()
    now = int(ti - ti%60)
    start = now - (3600*72) # last 72 hour
    datas = []
    for t in range(start,now,60): 
        pipe = redisconnection.pipeline()
        for key in stats_keys:
            pipe.get("stats.%s.%s.%s" %  (key,keyname ,t))
        results = pipe.execute()
        data = [ datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S'), ]
        for result in results:
            if result != None:
                result = float(result)
            data.append(result)
        datas.append(data)
        
    merged_stats = []
    minutes_to_merge = 10
    for i in range(0,len(datas), minutes_to_merge): 
        merged_stat = merge_stats(datas[i:i+minutes_to_merge])
        if len([x for x in merged_stat[1:] if x != None]) > 0:
            merged_stats.append(merged_stat)
        
    stats = { 
        "labels" : [],
    }
    for key in stats_keys:
        stats[key] = []
    
    for data in merged_stats:        
        stats["labels"].append(data[0])
        for index, key in enumerate(stats_keys):
            stats[key].append(data[index+1])     
    return stats    
    
    
def dashboard(request):
    problems = models.Problem.objects.all()
    template = loader.get_template('dashboard.html')
    stats = getStats("global")
    context = {
        'problems': problems,
        'stats': json.dumps(stats),
    }
    return HttpResponse(template.render(context, request))
  


        
def p2p_getIndividuals(request,problem_name):
    data = []
    problem = models.Problem.objects.get(name=problem_name)
    individuals = problem.getP2PIndividuals()
    for individual in individuals:
        data.append({
            "fitness_sum" : individual.fitness_sum,
            "fitness_evalcount" : individual.fitness_evalcount,
            "code" : individual.code,
        })
    
    return JsonResponse(data,safe=False)   

    
def problem_index(request):
    problems = models.Problem.objects.all()
    template = loader.get_template('problem/index.html')
    context = {
        'problems': problems,
    }
    return HttpResponse(template.render(context, request))    
    
def problem_show(request,pk):
    problem = models.Problem.objects.get(pk=pk)
    template = loader.get_template('problem/show.html')
    context = {
        'problem': problem,
    }
    return HttpResponse(template.render(context, request))        
    
def problem_cleanup(request,pk):
    problem = models.Problem.objects.get(pk=pk)
    for population in problem.populations.all()[5:]:
        if population.individual_count == 0:
            print("delete")
            population.delete()
    return HttpResponseRedirect(reverse('problem_show', args=(problem.id,)))     
 
        
def species_show(request,pk):
    species = models.Species.objects.get(pk=pk)
    template = loader.get_template('species/show.html')
    stats = getStats("species.%s" % species.id)
    context = {
        'species': species,
        'stats': json.dumps(stats),
    }
    return HttpResponse(template.render(context, request))        
    
def individual_show(request,pk):
    individual = models.Individual.objects.get(pk=pk)
    template = loader.get_template('individual/show.html')
    context = {
        'individual': individual,
    }
    return HttpResponse(template.render(context, request))        
    

def population_show(request,pk):
    population = models.Population.objects.get(pk=pk)
    template = loader.get_template('population/show.html')
    
    stats = getStats("population.%s" % population.id)
    context = {
        'population': population,
        'population_stats': population.stats(),
        'stats': json.dumps(stats),
    }
    return HttpResponse(template.render(context, request))            
    
def population_delete(request,pk):
    population = models.Population.objects.get(pk=pk)
    problem = population.problem
    population.delete()
    return HttpResponseRedirect(reverse('problem_show', args=(problem.id,)))     
 
 

def referencefunction_show(request,pk):
    referenceFunction = models.ReferenceFunction.objects.get(pk=pk)
    template = loader.get_template('referencefunction/show.html')
    
    stats = getStats("referenceFunction.%s" % referenceFunction.id)
    context = {
        'referencefunction': referenceFunction,
        'stats': json.dumps(stats),
    }
    return HttpResponse(template.render(context, request))            
    
def referencefunction_reset(request,pk):
    referenceFunction = models.ReferenceFunction.objects.get(pk=pk)
    problem = referenceFunction.problem
    referenceFunction.reset()
    referenceFunction.save()
    return HttpResponseRedirect(reverse('problem_show', args=(problem.id,)))     
     