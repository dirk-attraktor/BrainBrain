import os, sys
import random
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
import base64
django.setup()

from django.db.models import F,Q
from brainweb import models
import editdistance
from brainweb.models import Problem
from brainweb.models import Population
from brainweb.models import Individual

populations = Population.objects.all()
outputlines = []


 
def compare(item1, item2):
    
    m = max([len(item1),len(item2)])
    if m == 0:
        return 0
    if len(item1) > len(item2):
        return 100.0 / m  * editdistance.eval(item1, item2) 
    return 100.0 / m  * editdistance.eval(item2, item1) 
    
cnt = 0
cnt1 = 0
outfile = open("traindata_spellcorrection_0to30percentDifference","w")
for population in populations:
    if population.individual_count > 5000:
        individuals = population.individuals.filter(~Q(fitness=None)).filter(~Q(fitness=0))
        if individuals.count() > 10:
            individuals = [i for i in individuals]
            
            for i1 in range(0,len(individuals)):
                cnt1 += 1
                l1 = len(individuals[i1].code)
                if l1 == 0 or l1 > 1000:
                    continue
                for i2 in range(i1+1,len(individuals)):
                    l2 = len(individuals[i2].code)
                    if l2 == 0 or l2 > 1000:
                        continue                    
                    ed = compare(individuals[i1].code,individuals[i2].code)
                    if ed > 0 and ed <= 30:
                        if individuals[i1].fitness > individuals[i2].fitness:
                            outfile.write("%s\t%s\n" % (individuals[i2].code,individuals[i1].code))
                        if individuals[i1].fitness < individuals[i2].fitness:
                            outfile.write("%s\t%s\n" % (individuals[i1].code,individuals[i2].code))                            
                        cnt += 1
                        if cnt % 100 == 0:
                            print(cnt, cnt1)
                            
                        
outfile.close()                        

print(cnt)
