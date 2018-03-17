#!/usr/bin/env python
import os
import sys
import time
import threading
sys.dont_write_bytecode = True


def runserver():
    os.system("python3 manage.py runserver 192.168.6.241:12345")
    #os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
    #from django.core.management import execute_from_command_line
    #execute_from_command_line(["foobar","runserver","192.168.6.241:12345"])

if __name__ == "__main__":
    t = threading.Thread(target=runserver,args=[])
    t.daemon = True
    t.start()
    for i in range(0,30):
        time.sleep(1)
        print(i)
