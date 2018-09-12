import os, sys
import random
import time
import threading
import json
from datetime import datetime
from datetime import datetime, timedelta
from django.utils import timezone
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from websocket import create_connection


import django
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Species
from brainweb.models import Population
from brainweb.models import Individual
from brainweb.models import ReferenceFunction      
      
class BrainP2Pclient():        
    
    def __init__(self):
        self.supernode_connection = None    
        self.results = []

    def getIndividuals(self, problem_name, requests = 1, limit_per_node = 1):

        if not self.connect():
            return []
            
        t = threading.Thread(target=self._receiveMessagesThread, args=[])
        t.daemon = True
        t.start()   
        
        for i in range(0,requests):
            request = {
                "id" : "%s" % uuid.uuid4(),
                "type" : "request",
                "command" : "getIndividuals",
                "arguments" : { "problem_name": problem_name, "limit": limit_per_node},
            }
            self.supernode_connection.send(json.dumps(request))
            
        timeout = 30
        while len(self.results) < requests and timeout > 0:
            time.sleep(1)
            timeout -= 1
        self.supernode_connection.close()
        individuals = []
        [individuals.extend(r) for r in self.results]
        return individuals

    def _receiveMessagesThread(self):
        while True:
            try:
                result = self.supernode_connection.recv()
            except Exception as e:
                return
            if result == '':
                continue
            try:
                self.handleMessage(json.loads(result))
            except Exception as e:
                print("failed to parse received data: '%s'" % e)
        self.supernode_connection.close()
        
    def handleMessage(self, p2pdatagram):
        if p2pdatagram["type"] == "response":
            if p2pdatagram["command"] == "getIndividuals":
                self.handleMessageResponseGetIndividuals(p2pdatagram)
     
    def handleMessageResponseGetIndividuals(self,p2pdatagram):
        self.results.append(p2pdatagram["arguments"]["individuals"])
        
    def connect(self):
        from brainweb.models import Peer
        for trie in range(0,5):
            peers = [p for p in Peer.objects.filter(supernode=True).filter(Q( lastfail__lt=(timezone.now() - timedelta(minutes=10))) | Q(lastfail__isnull=True))]
            if len(peers) == 0:
                print("p2pClient could not find supernodes")
                return False
            peer = random.choice(peers)
            try:
                self.supernode_connection = create_connection("ws://%s:%s" % (peer.host, peer.port))
            except Exception as e: 
                print("p2pClient superNode connection failed %s" % e)
                peer.failcount += 1
                peer.lastfail = timezone.now()
                peer.save()
                time.sleep(5)
                
                continue
            peer.failcount = 0
            peer.save()
            print("connected to %s" % peer)
            return True
            
        return False
       
       
if __name__ == "__main__":
    p = BrainP2Pclient()
    x = p.getIndividuals("MateMutate", requests = 10, limit_per_node = 5)
    print(x)