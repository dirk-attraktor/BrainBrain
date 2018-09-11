import random
        
# FIRST item has factor x times the propability of being picked
def selectLinear(listlength, factor, reverse = False):
    factor = float(factor)
    while True:
        index = float(random.randint(0, listlength - 1))
        factordiff = factor - 1
        stepsPerIndex = factordiff / float(listlength-1)
        factorForIndex = 1 + (index * stepsPerIndex)
        prop = factorForIndex / factor
        if random.random() < prop:
            if reverse:
                return int(index)    
            else:
                return int(listlength - 1 - index)

      