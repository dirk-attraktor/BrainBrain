import os, sys
import random
import time
import threading
import json
import uuid
from datetime import datetime
from datetime import datetime, timedelta
from django.utils import timezone

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

import redis
redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

p2pClientConnectionHandlers = []
p2pSuperNodeConnections = []

def create_datagram_request( command, arguments = {}):
    return {
        "id" : "%s" % uuid.uuid4(),
        "type" : "request",
        "command" : command,
        "arguments" : arguments,
    }
    
def create_datagram_response(identifier, command, arguments = {}):
    return {
        "id" : identifier,
        "type" : "response",
        "command" : command,
        "arguments" : arguments,
    }   
    
# connection from any node type to supernode, supernode side
class P2PClientConnectionHandler(WebSocket):

    def handleMessage(self):
        try:
            p2pdatagram = json.loads(self.data)
            if p2pdatagram["type"] == "request":
                if p2pdatagram["command"] == "registerSuperNode":
                    self.handleMessageRequestRegisterSuperNode(p2pdatagram)
                
                if p2pdatagram["command"] == "publishKnownProblems":
                    self.handleMessageRequestPublishKnownProblems(p2pdatagram)

                if p2pdatagram["command"] == "getIndividuals":
                    self.handleMessageRequestGetIndividuals(p2pdatagram)
                                            
                if p2pdatagram["command"] == "getSuperNodes":
                    self.handleMessageRequestGetSuperNodes(p2pdatagram)
              
            if p2pdatagram["type"] == "response":
                if p2pdatagram["command"] == "getIndividuals":
                    self.handleMessageResponseGetIndividuals(p2pdatagram)
        except Exception as e:
            print("failed to handle received p2pNodeHandler data: '%s'" % e)
            try:
                self.close()
            except:
                pass
            
    def handleMessageRequestRegisterSuperNode(self, p2pdatagram):
        try:
            peer = Peer.objects.get(host=p2pdatagram["arguments"]["ip"],port=p2pdatagram["arguments"]["port"])
        except Exception as e:
            peer = Peer()
            peer.host =  p2pdatagram["arguments"]["ip"]
            peer.port = p2pdatagram["arguments"]["port"]
        peer.supernode = True
        peer.save()
        print("%s registered as supernode" % peer )
                
    def handleMessageRequestPublishKnownProblems(self, p2pdatagram):
        self.knownProblems = p2pdatagram["arguments"]["problems"]
        
    def handleMessageRequestGetIndividuals(self, p2pdatagram):       
        clients = [c for c in p2pClientConnectionHandlers if c != self and c.address[0] != self.address[0] and p2pdatagram["arguments"]["problem_name"] in c.knownProblems]
        #clients = [c for c in p2pClientConnectionHandlers if c != self and p2pdatagram["arguments"]["problem_name"] in c.knownProblems]
        if len(clients ) > 0:
            client = random.choice(clients)
            request = create_datagram_request("getIndividuals", { "problem_name": p2pdatagram["arguments"]["problem_name"], "limit": p2pdatagram["arguments"]["limit"]})
            redisconnection.set("P2PClientConnectionHandler Callback: %s sourceclientid"     % request["id"], self.cid)
            redisconnection.set("P2PClientConnectionHandler Callback: %s sourcerequestid"    % request["id"], p2pdatagram["id"])
            redisconnection.expire("P2PClientConnectionHandler Callback: %s sourceclientid"  % request["id"] ,180)
            redisconnection.expire("P2PClientConnectionHandler Callback: %s sourcerequestid" % request["id"] ,180)
            client.sendMessage(json.dumps(request))
            
            print("getIndividuals request from %s forwarded to %s with id %s" % (self.cid, client.cid, request["id"]))
        else:
            print("no clients found for problem %s" % p2pdatagram["arguments"]["problem_name"])
            self.sendMessage(json.dumps(create_datagram_response(p2pdatagram["id"], "getIndividuals", {"individuals" : []})))
        
    def handleMessageRequestGetSuperNodes(self, p2pdatagram):
        peers = []
        try:
            peers = [[x.host,x.port] for x in Peer.objects.filter(supernode=True)]
        except Exception as e:
            print(e)
        self.sendMessage(json.dumps(create_datagram_response(p2pdatagram["id"], "getSuperNodes", {"nodes" : peers})))

    def handleMessageResponseGetIndividuals(self, p2pdatagram):
        try:
            source_client_id  = redisconnection.get("P2PClientConnectionHandler Callback: %s sourceclientid"  % p2pdatagram["id"]).decode("ASCII")
            source_request_id = redisconnection.get("P2PClientConnectionHandler Callback: %s sourcerequestid" % p2pdatagram["id"]).decode("ASCII")
            sourceClient = [c for c in p2pClientConnectionHandlers if c.cid == source_client_id][0]
        except Exception as e:
            print("failed to get source client : %s" % e)
            print(p2pdatagram)
            return 
        print("getIndividuals response from %s forwarded to %s with id %s" % (self.cid, sourceClient.cid, source_request_id))
        try:
            sourceClient.sendMessage(json.dumps(create_datagram_response(source_request_id, "getIndividuals", {"individuals" : p2pdatagram["arguments"]["individuals"] })))
        except Exception as e:
            print(e)
            
    def handleConnected(self):
        try:
            print(self.address, 'client "%s" connected to supernode' % self.address[0])
            self.knownProblems = []
            self.cid = "%s_%s" % (self.address[0], self.address[1])
            p2pClientConnectionHandlers.append(self)
        except Exception as e:
            print("handleConnected failed %s" % e)
            
    def handleClose(self):
        print(self.address, 'disconnected from supernode')    
        p2pClientConnectionHandlers.remove(self)

        
# connection from any node type to supernode, client side
class P2PSuperNodeConnection():        
    def __init__(self, peer, onConnected, onDisconnected):
        self.peer = peer
        self.onConnected = onConnected
        self.onDisconnected = onDisconnected
        self.supernodeConnection = None
        self.starttime = int(time.time())
        print("Connecting to superNode %s" % peer)
        try:
            self.supernodeConnection = create_connection("ws://%s:%s" % (peer.host, peer.port))
            self.onConnected(self)
            print("Connected to superNode %s" % peer)
        except Exception as e: 
            print("Connection to superNode %s failed" % peer)
            peer.failcount += 1
            peer.lastfail = timezone.now()
            peer.save()
            self.close()
            return 
        t = threading.Thread(target=self._receiveMessagesThread, args=[])
        t.daemon = True
        t.start()               
        peer.failcount = 0
        peer.save() 
      
    def send(self, message):
        try:
            self.supernodeConnection.send(message)
            return True
        except Exception as e:
            print("failed to send to supernodeConnection: %s" % e)
            self.close()
        return False
        
    def close(self):
        try:
            self.supernodeConnection.close()
        except Exception as e:
            print(e)
        self.onDisconnected(self)
            
        
    def registerSuperNode(self, ip, port):
        self.send(json.dumps(create_datagram_request("registerSuperNode", {"ip": ip,"port": "%s" % port})))
                    
    def publishKnownProblems(self, problems):
        self.send(json.dumps(create_datagram_request("publishKnownProblems", {"problems":problems})))
  
    def getSuperNodes(self):
        request = create_datagram_request("getSuperNodes")
        redisconnection.set("P2PSuperNodeConnection Callback: %s" % request["id"], self.peer.id)
        redisconnection.expire("P2PSuperNodeConnection Callback: %s" % request["id"] ,180)
        self.send(json.dumps(request))
 
    def _receiveMessagesThread(self):
        while True:
            try:
                result =  self.supernodeConnection.recv()
            except Exception as e:
                print("failed to received data: '%s'" % e)
                break
            data = {}
            try:
                self.handleMessage(json.loads(result))
            except Exception as e:
                print("failed to parse received data: '%s'" % e)
        self.close()
        
    def handleMessage(self, p2pdatagram):
        if p2pdatagram["type"] == "response":
            try:
                peer_id = int(redisconnection.get("P2PSuperNodeConnection Callback: %s" % p2pdatagram["id"]))
                if peer_id != self.peer.id:
                    print("foobar error")
            except Exception as e: 
                print("fail foo %s" % e)
                return
            if p2pdatagram["command"] == "getSuperNodes":
                self.handleMessageResponseGetSupernodes(p2pdatagram)
                
        if p2pdatagram["type"] == "request":
            if p2pdatagram["command"] == "getIndividuals":
                self.handleMessageRequestGetIndividuals(p2pdatagram)
     
    def handleMessageRequestGetIndividuals(self, p2pdatagram):         
        data = []
        problem = Problem.objects.get(name=p2pdatagram["arguments"]["problem_name"])        
        individuals = problem.getP2PIndividuals(p2pdatagram["arguments"]["limit"])
        for individual in individuals:
            data.append({
                "code" : individual.code,
            })
        self.supernodeConnection.send(json.dumps(create_datagram_response(p2pdatagram["id"],"getIndividuals", {"individuals": data})))
           
    def handleMessageResponseGetSupernodes(self, p2pdatagram):
        nodes = p2pdatagram["arguments"]["nodes"]    
        for host, port in nodes:
            try:
                peer = Peer.objects.get(host=host,port=port)
                peer.supernode = True
                peer.save()
                print("supernode %s is already known" % (host))
            except Exception as e: 
                print("superNode %s is unknown : %s"% (host,e))
                p = Peer()
                p.host = host
                p.port = port
                p.supernode = True
                p.save()
                print("new supernode saved")
                
    def __repr__(self):
        return "Connection to Supernode %s" % self.peer.host
        
class p2pNode():        
    
    def __init__(self,host, isPublicNode = False):
        if isPublicNode == True:
            print("starting Public Node on %s:4141" % host)
        else:
            print("starting Node on %s:4141" % host)

        self.isPublicNode = isPublicNode
        self.server = None
        self.superNodeIp = host 
      
    def start(self):
        for f in [ self._runserver, self._watchdog ]:
            t = threading.Thread(target=f, args=[] )
            t.daemon = True
            t.start()
        
    def stop(self):  
        print("stopserver")
        if self.server != None:
            self.server.close()
        for p2pSuperNodeConnection in p2pSuperNodeConnections:
            p2pSuperNodeConnection.close()
                                 
    def onSuperNodeConnected(self, p2pSuperNodeConnection ):
        p2pSuperNodeConnections.append(p2pSuperNodeConnection)
        if self.isPublicNode == True:
            p2pSuperNodeConnection.registerSuperNode(self.superNodeIp, 4141)
        problems = [x.name for x in Problem.objects.all()]
        p2pSuperNodeConnection.publishKnownProblems(problems)
        p2pSuperNodeConnection.getSuperNodes()
                    
    def onSuperNodeDisconnected(self, p2pSuperNodeConnection ):
        if p2pSuperNodeConnection in p2pSuperNodeConnections:
            p2pSuperNodeConnections.remove(p2pSuperNodeConnection)
        
    def _watchdog(self):
        max_supernode_connections = 3
        
        while True:
            if len(p2pSuperNodeConnections) <  max_supernode_connections:
                peers = Peer.objects.filter(supernode=True).filter(Q( lastfail__lt=(timezone.now() - timedelta(minutes=10))) | Q(lastfail__isnull=True)).exclude(id__in=list([x.peer.id for x in p2pSuperNodeConnections]))
                #peers = [p for p in peers if p.host != self.superNodeIp] # allow selfconnnect
                if len(peers) > 0: 
                    peer = random.choice(peers)
                    p2pSuperNodeConnection = P2PSuperNodeConnection(peer, self.onSuperNodeConnected, self.onSuperNodeDisconnected)
                else:
                    print(" no supernodes available")
                    if len(p2pSuperNodeConnections) == 0:  
                        print("no peer available, bootstrap not possible")
                    else:
                        None
            time.sleep(120)                        
            for p2pSuperNodeConnection in p2pSuperNodeConnections:
                if p2pSuperNodeConnection.starttime + 3600 < int(time.time()): # close every hour
                    p2pSuperNodeConnection.close()
                    break
            
     
    def _runserver(self):
        self.server = SimpleWebSocketServer(self.superNodeIp, 4141, P2PClientConnectionHandler)
        try:
            print("node starting")
            self.server.serveforever()
        except Exception as e:
            print("websocket server exited: %s" % e)
    
    
if __name__ == "__main__":
    isPublicNode = False

    try:
        if sys.argv[1] == "addpeer":
            host = sys.argv[2]
            try:
                peer = Peer.objects.get(supernode=True,port=4141,host=host)
                print("Peer %s already exists" % host)
            except: 
                print("Creating Peer %s" % host)
                p = Peer()
                p.host = host
                p.port = "4141"
                p.supernode = True
                p.save()
            exit(0)
    except Exception as e:
        None
    
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
    from IPython import embed
    embed()