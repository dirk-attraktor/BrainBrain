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
    

try:
    postfix = sys.argv[1]
except:
    postfix = ""

for max_crossover_inds in range(1, 8):
    cnt = 0
    cnt1 = 0
    #max_crossover_inds = 6
    percent_diff = 30
    outfile = open("traindata_crossover_%s_inds_%s_percentdiff_%s" % (max_crossover_inds, percent_diff, postfix),"w")
    for population in populations:
        if population.individual_count > 5000:
            individuals = population.individuals.filter(~Q(fitness=None)).filter(~Q(fitness=0))
            if individuals.count() > 10:
                individuals = [i for i in individuals]
                
                for i1 in range(0,len(individuals)):
                    crossover_inds_code = []
                    cnt1 += 1
                    l1 = len(individuals[i1].code)
                    if l1 == 0 or l1 > 1000:
                        continue
                    for i2 in range(i1+1,len(individuals)):
                        l2 = len(individuals[i2].code)
                        if l2 == 0 or l2 > 1000:
                            continue                    
                        
                        eds = [compare(individuals[i1].code,crossover_ind_code) for crossover_ind_code in crossover_inds_code] # compare to crossover_inds_code
                        eds.append(compare(individuals[i1].code,individuals[i2].code))
                        min_eds = min(eds)
                        #print(eds)
                        if min_eds > 0 and min_eds <= percent_diff:
                            if individuals[i1].fitness > individuals[i2].fitness:
                                if individuals[i2].code in crossover_inds_code:
                                    continue
                                crossover_inds_code.append(individuals[i2].code)
                                if len(crossover_inds_code) == max_crossover_inds:
                                    #print("reached")
                                    line = "%s\t%s\n" % ("\t".join(crossover_inds_code),individuals[i1].code)
                                    #print(line)
                                    outfile.write(line)
                                    crossover_inds_code = []
                                    cnt += 1
                                    if cnt % 100 == 0:
                                        print(cnt, cnt1)
                        #else:
                        #    print("%s\t%s" % (individuals[i1].code,individuals[i2].code))
                            
    outfile.close()                        

    print(cnt)
