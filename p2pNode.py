import os, sys
import random
import time
import threading
import json
from datetime import datetime
from datetime import datetime, timedelta

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from websocket import create_connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brainweb.settings")
import django
django.setup()
from django.db.models import Q

from brainweb.models import Peer
from brainweb.models import Problem
from brainweb.models import Population
from brainweb.models import Individual



supernode_clients = []
supernode_connection_threads = {}

class p2pNodeHandler(WebSocket):
    def handleMessage(self):
        try:
            print("handleMessage")
            print(self.data)
            try:
                self.parseCommand(json.loads(self.data))
            except Exception as e:
                print("failed to parse received p2pNodeHandler data: '%s'" % e)
        except Exception as e:
            print("handleMessage failed %s" % e)            
            print(data)

    def parseCommand(self,data):
        if data["command"] == "registerSuperNode":
            try:
                peer = Peer.objects.get(host=data["args"]["ip"],port=data["args"]["port"])
                print(" is a known peer")
            except Exception as e:
                print(e)
                print(" is a new peer")
                peer = Peer()
                peer.host =  data["args"]["ip"]
                peer.port = data["args"]["port"]
            peer.supernode = True
            self.supernode = True
            peer.save()
            
        if data["command"] == "publishKnownProblems":
            self.knownProblems = data["args"]["problems"]
            print("known problems received")
            print(self.knownProblems)
            
        if data["command"] == "getIndividuals":
            print(supernode_clients)
            clients = [c for c in supernode_clients if c != self and c.address[0] != self.address[0] and data["args"]["problem_name"] in c.knownProblems]
            if len(clients ) > 0:
                print("some clients found")
                client = random.choice(clients)
                client.sendMessage(json.dumps({
                    "command" : data["command"],
                    "args" : {
                        "problem_name" : data["args"]["problem_name"],
                        "callback" : "%s" % self.id
                    }
                }))
            else:
                print("no clients found")
                self.sendMessage(json.dumps({
                    "command" : "getIndividualsResponse", 
                    "args" : {
                        "individuals" : []
                    }
                }))
                
        if data["command"] == "getIndividualsResponse":
            print("p2pNodeHandler getIndividualsResponse received")
            try:
                sourceClient = [c for c in supernode_clients if c.id == data["args"]["callback"]][0]
            except Exception as e:
                print("failed to get source client : %s" % e)
                return 
            sourceClient.sendMessage(json.dumps({
                "command" : "getIndividualsResponse", 
                "args" : {
                    "individuals" : data["args"]["individuals"] 
                }
            }))
            print("p2pNodeHandler getIndividualsResponse done")
    
        if data["command"] == "getSuperNodes":
            print("getSuperNodes received")
            peers = []
            try:
                peers = [[x.host,x.port] for x in Peer.objects.filter(supernode=True)]
                print(" %s supernodes known to superNode" % len(peers))
            except Exception as e:
                print(e)
            self.sendMessage( json.dumps({
                "command": "getSuperNodesResponse",
                "args" : {
                    "data" : peers,
                }
            }))
            print("getSuperNodes received send")

    def handleConnected(self):
        try:
            print(self.address, 'client "%s" connected to supernode' % self.address[0])
            self.knownProblems = []
            self.supernode = False
            self.id = "%s_%s" % (self.address[0],self.address[1])
            supernode_clients.append(self)
        except Exception as e:
            print("handleConnected failed %s" % e)
            
    def handleClose(self):
        print(self.address, 'disconnected from supernode')    
        supernode_clients.remove(self)

        
        
class p2pNode():        
    
    def __init__(self,host, isPublicNode = False):
        if isPublicNode == True:
            print("starting Public Node on %s:4141" % host)
        else:
            print("starting Node on %s:4141" % host)

        self.isPublicNode = isPublicNode
        self.server = None
        self.superNodeIp = host 
            
    def runserver(self):
        self.server = SimpleWebSocketServer(self.superNodeIp, 4141, p2pNodeHandler)
        try:
            print("node starting")
            self.server.serveforever()
        except Exception as e:
            print("websocket server exited: %s" % e)
                
        
    def start(self):
        t = threading.Thread(target=self.runserver,args=[])
        t.daemon = True
        t.start()
    
        t = threading.Thread(target=self.watchdog,args=[])
        t.daemon = True
        t.start()
        
    def stop(self):  
        print("stopserver")
        if self.server != None:
            self.server.close()
        for key in supernode_connection_threads:
            if supernode_connection_threads[key].connection != None:
                supernode_connection_threads[key].connection.close()
                
    def clientthread(self,peer):
        print("connecting to peer %s" % peer)
        try:
            ws = create_connection("ws://%s:%s" % (peer.host,peer.port))
        except Exception as e: 
            print("websocket connection client to supernode %s failed %s" % (peer,e))
            peer.failcount += 1
            peer.lastfail = datetime.now()
            peer.save()
            return 
        peer.failcount = 0
        peer.save()
        mode = "node"
        if self.isPublicNode == True:
            mode = "supernode"
            ws.send(json.dumps({"command":"registerSuperNode","args":{"ip":self.superNodeIp,"port":"4141"}}))
   
        try:
            problems = [x.name for x in Problem.objects.all()]
            ws.send(json.dumps({"command":"publishKnownProblems","args":{"problems":problems}}))
        except Exception as e:
            print("failed to announce problem names: %s" % e)

        supernode_connection_threads[peer.host]["connection"] = ws
        print("WEBsocket connected")
        while True:
            result =  ws.recv()
            data = {}
            print("Client Received '%s'" % result)
            try:
                self.parseCommand(json.loads(result),peer)
            except Exception as e:
                print("failed to parse received data: '%s'" % e)
            print(data)
        print("connection to peer closing %s" % peer)   
        ws.close()
        
        supernode_connection_threads[peer.host]["connection"] = None
        supernode_connection_threads[peer.host]["thread"] = None
        supernode_connection_threads[peer.host]["peer"] = None
        del supernode_connection_threads[peer.host]
    
    def parseCommand(self,data,peer):
        if data["command"] == "getIndividuals":
            individuals = self.getIndividuals(data["args"]["problem_name"])
            supernode_connection_threads[peer.host]["connection"].send(
                json.dumps({"command":"getIndividualsResponse","args":{"individuals":individuals,"callback":data["args"]["callback"]}})
            )
            
            
        if data["command"] == "getSuperNodesResponse":  
            print("getSuperNodesResponse command parsed")
            self.getSuperNodesResponse(data["args"]["data"])
            
    def getSuperNodesResponse(self,nodelist):
        print("getSuperNodesResponse")
        print(nodelist)
        for host,port in nodelist:
            try:
                peer = Peer.objects.get(host=host,port=port)
                peer.supernode = True
                peer.save()
                print("superNode %s is known" % (host))
            except Exception as e: 
                print("superNode %s is unknown : %s"% (host,e))
                p = Peer()
                p.host = host
                p.port = port
                p.supernode = True
                p.save()
                print("new supernode saved")
                
        
    def getIndividuals(self,problem_name):
        data = []
        problem = Problem.objects.get(name=problem_name)
        individuals = problem.getP2PIndividuals()
        for individual in individuals:
            data.append({
                "fitness_sum" : individual.fitness_sum,
                "fitness_evalcount" : individual.fitness_evalcount,
                "code" : individual.code,
            })
        return data
    
    def watchdog(self):
        print("watchdog starting")
        max_supernode_connections = 1
        while True:
            if len(supernode_connection_threads) <  max_supernode_connections:
                peers = Peer.objects.filter(supernode=True).filter(Q( lastfail__lt=(datetime.now() - timedelta(minutes=10))) | Q(lastfail__isnull=True)).exclude(host__in=list(supernode_connection_threads.keys()))
                if peers.count() > 0: 
                    print("supernodes available,starting client thread")
                    peer = random.choice(peers)
                    t = threading.Thread(target=self.clientthread,args=[peer])
                    t.daemon = True
                    supernode_connection_threads[peer.host] = {
                        "peer" : peer,
                        "thread" : t,
                        "connection" : None,
                    }
                    t.start()
                    min_peers = 5
                    if self.isPublicNode == True:
                        min_peers = 5
                    if peers.count() < min_peers:
                        print("extend number of supernodes")
                        time.sleep(5)
                        for key in supernode_connection_threads:
                            print(key)
                            if supernode_connection_threads[key]["connection"] != None:
                                print("sending")
                                supernode_connection_threads[key]["connection"].send(json.dumps({
                                    "command" : "getSuperNodes"
                                }))
                    
                else:
                    print(" no supernodes available")
                    if len(supernode_connection_threads) == 0:  
                        print("no peer available, bootstrap not possible")
                    else:
                        None

            print("watchdog sleep 100")
            time.sleep(100)
     

 
            
if __name__ == "__main__":
    isPublicNode = False

    try:
        if sys.argv[1] == "public":
            isPublicNode = True
    except:
        None
    if isPublicNode == True:
        host = sys.argv[2]
    else:
        host = "127.0.0.1"
            
    node = p2pNode(host,isPublicNode)
    node.start()
    time.sleep(10000)
    
'''    
print("SERVER")            
server = p2pNode('192.168.6.241',True)
server.start()
time.sleep(5)

print("CLIENT 1")
client = p2pNode('192.168.6.243',False)
client.start()
time.sleep(5)

print("CLIENT 2")
client1 = p2pNode('192.168.6.242',False)
client1.start()
time.sleep(5)

localclient = localP2PClient()
localclient.getIndividuals("google_testcases-add")
#import IPython
#IPython.embed()

client.receiveIndividuals("google_testcases-add")


time.sleep(1000)
'''
