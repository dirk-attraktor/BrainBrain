import os,sys,threading
import p2pNode

import time

print("# USAGE: ")
print("")
print(" node = p2pNode('yourip',False)")
print(" node.start()")


from brainweb.models import Individual
from django.db import connection

def updateThread():
    while True:
        os.system("git pull")
        os.system("python3 manage.py migrate")
        print("thread '%s' exited " % cmd)
        time.sleep(3600)


def runThread(cmd):
    while True:
        os.system(cmd)
        print("thread '%s' exited " % cmd)
        time.sleep(5)
        
def work(nrOfthread):
    t = threading.Thread(target=updateThread)
    t.daemon = True
    t.start()

    for _ in range(0,nrOfthread-1):
        cmd = "python3 run-google-testcases.py run random"
        t = threading.Thread(target=runThread,args=[cmd])
        t.daemon = True
        t.start()
    for _ in range(0,1):
        cmd = "python3 advtain.py"    
        t = threading.Thread(target=runThread,args=[cmd])
        t.daemon = True
        t.start()

import IPython
IPython.embed()
