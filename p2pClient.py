import os, sys
import random
import time
import threading
import json
from datetime import datetime
from datetime import datetime, timedelta

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from websocket import create_connection


from django.db.models import Q
      
class p2pClient():        
    
    def __init__(self):
        self.supernode_connection = None    
        self.individuals = []
        
    def getIndividuals(self,problem_name,limit = 2):
        successCount = 0
        for i in range(0,limit*2):
            if self._getIndividuals(problem_name) == True:
                successCount += 1
            if successCount >= limit:
                break
        return self.individuals
        
    def _getIndividuals(self,problem_name):
        success = self.connect()
        print("localP2PClient connected")
        if success == True:
            success = False
            print("localP2PClient connected")
            t = threading.Thread(target=self.receiveThread,args=[])
            t.daemon = True
            t.start()
            print("localP2PClient sending ocmmand")
            self.supernode_connection.send(
                json.dumps({"command":"getIndividuals","args":{"problem_name":problem_name}})
            )
            print("localP2PClient sending ocmmand done")
            self._individuals = None
            for i in range(0,60):
                if self._individuals != None:
                    print("juhu")
                    success = True
                    self.individuals.extend(self._individuals)
                    break
                time.sleep(0.3)
            print("sending close")
            self.supernode_connection.close()
            t.join()
        return success  
        
        
    def connect(self):
        from brainweb.models import Peer

        peers = Peer.objects.filter(supernode=True).filter(Q( lastfail__lt=(datetime.now() - timedelta(minutes=10))) | Q(lastfail__isnull=True))
        
        if peers.count() ==0:
            print("local client could not find supernodes")
            return False
        peer = random.choice(peers)
        try:
            self.supernode_connection = create_connection("ws://%s:%s" % (peer.host,peer.port))
        except Exception as e: 
            print("localP2PClient websocket connection client to supernode failed %s" % e)
            peer.failcount += 1
            peer.lastfail = datetime.now()
            peer.save()
            return False
        peer.failcount = 0
        peer.save()
        print("localP2PClient WEBsocket connected")
        return True
        
    def receiveThread(self,expectedDataCount = -1):
        while True:
            try:
                result =  self.supernode_connection.recv()
            except Exception as e:
                print("receive failed,exiting thread: %s" % e)
                return
            if result == '':    
                continue
            data = {}
            print("localP2PClient Received '%s'" % result)
            try:
                self.parseCommand(json.loads(result))
            except Exception as e:
                print("localP2PClient failed to parse received data: '%s'" % e)
        print("localP2PClient connection to peer closing")   
        self.supernode_connection.close()

    def parseCommand(self,data):
        if data["command"] == "getIndividualsResponse":
            print(data)
            self._individuals = data["args"]["individuals"]
            