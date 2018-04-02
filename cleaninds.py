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

import re

GENES = [
    '>', # inkrementiert den Zeiger
    '<', # dekrementiert den Zeiger
    '+', # inkrementiert den aktuellen Zellenwert
    '-', # dekrementiert den aktuellen Zellenwert
    '[', # Springt nach vorne, hinter den passenden ]-Befehl, wenn der aktuelle Zellenwert 0 ist	
    ']', # Springt nach vorne, hinter den passenden ]-Befehl, wenn der aktuelle Zellenwert 0 ist
    '.', # Gibt den aktuellen Zellenwert als ASCII-Zeichen auf der Standardausgabe aus
    ',', # Liest ein Zeichen von der Standardeingabe und speichert dessen ASCII-Wert in der aktuellen Zelle
    'N', # NoOp
    'A', # NoOp
    'B', # NoOp
]
GENES_STRING = '\\'.join(GENES)
GENES_REGEX = "[^%s]+" % GENES_STRING



populations = Population.objects.all()

cnt = 0
for population in populations:
    individuals = population.individuals.all()
    for i in individuals:
        c = i.code
        newc = re.sub(GENES_REGEX,'',c)
        if c != newc:
            cnt +=1
            if cnt%1000 == 0:
                print(cnt)
            i.code = newc
            i.wasChanged = True
            i.save()
                        
print(cnt)
