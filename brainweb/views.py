from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.http import JsonResponse
import random
# Create your views here.

from django.http import HttpResponse

from . import models

def dashboard(request):
    problems = models.Problem.objects.all()
    template = loader.get_template('dashboard.html')
    context = {
        'problems': problems,
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
 
        
    
def population_show(request,pk):
    population = models.Population.objects.get(pk=pk)
    template = loader.get_template('population/show.html')
    context = {
        'population': population,
    }
    return HttpResponse(template.render(context, request))            
    
def population_delete(request,pk):
    population = models.Population.objects.get(pk=pk)
    problem = population.problem
    population.delete()
    return HttpResponseRedirect(reverse('problem_show', args=(problem.id,)))     
 
 

def referencefunction_reset(request,pk):
    referenceFunction = models.ReferenceFunction.objects.get(pk=pk)
    problem = referenceFunction.problem
    referenceFunction.fitness = None
    referenceFunction.fitness_sum = 0
    referenceFunction.fitness_evalcount = 0
    referenceFunction.execution_counter = 0
    referenceFunction.execution_time = 0
    referenceFunction.save()
    return HttpResponseRedirect(reverse('problem_show', args=(problem.id,)))     
     