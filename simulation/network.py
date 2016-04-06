import collections, random, Queue
from constants import *
from node import Node

event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

class Network(object):
    def __init__(self, numInitNodes = NUM_INIT_NODES, totalNodes = NUM_NODES, 
                        latencyInfo = None, darkNodeProb = 0.5):
        self.eventQueue = Queue.PriorityQueue()
        self.globalTime = 0.0

        self.seederNodes = []
        self.initNodes = []
        self.nodes = []
        self.ipToNodes = {}
        self.ipToNonDarkNodes = {}

        self.IPs = [] # Currently taken IP addresses by nodes in network

        self.initializeNodes(numInitNodes)
        self.hardcodedIPs = [node.ipV4Addr for node in self.initNodes]

        self.generateAllNodes(totalNodes - numInitNodes)

    def assignIP(self):
        ipTaken = True
        while ipTaken:
            newIP = '.'.join([str(random.randint(0, 255)) for _ in range(4)])
            ipTaken = newIP in self.IPs
        self.IPs.append(newIP)
        return newIP

    def getRestartTime(self):
        return random.randint(1, 80000) # Arbitrary placeholder; change later

    def initializeNodes(self, numInitNodes):
        # Create initial nodes
        for i in range(numInitNodes):
            newNode = Node(self.assignIP())
            self.ipToNodes[newNode.ipV4Addr] = newNode
            if newNode.nodeType != DARK:
                self.ipToNonDarkNodes[newNode.ipV4Addr] = newNode
            self.initNodes.append(newNode)
            self.eventQueue.put((self.getRestartTime(), event(srcNode = newNode,    
                                                              destNode = None, 
                                                              eventType = JOIN, 
                                                              info = None)))

        # Create seeder nodes
        for i in range(NUM_SEEDERS):
            seederNode = Node(self.assignIP(), nodeType = SEEDER)
            ipToNodes[seederNode.ipV4Addr] = seederNode
            self.seederNodes.append(seederNode)

        # Setup connections for initial nodes
        for i in range(numInitNodes):
            connections = self.initNodes[:i] + self.initNodes[i+1:]
            outgoingCnxs = [n.ipV4Addr for n in random.sample(connections, MAX_OUTGOING)]
            self.initNodes[i].outgoingCnxs = outgoingCnxs
            for ip in outgoingCnxs:
                self.ipToNodes[ip].incomingCnxs.append(self.initNodes[i].ipV4Addr)


    def getWakeTime(self, node):
        return 500 # Change later


    def generateAllNodes(self, numNodes):
        for i in range(numNodes):
            newNode = Node(self.assignIP())
            self.nodes.append(newNode)
            ipToNodes[newNode.ipV4Addr] = newNode

            wakeTime = self.getWakeTime(newNode)
            self.eventQueue.put((wakeTime, event(srcNode = newNode, 
                                                 destNode = None, 
                                                 eventType = JOIN, 
                                                 info = None)))

    def generateLatency(self):
        return random.random() / 2 # Change later

    def processNextEvent(self):
        self.globalTime, eventEntry = self.eventQueue.get()
        latency = self.generateLatency()

        scheduledTime = self.globalTime + latency

        src = eventEntry.srcNode
        dest = eventEntry.destNode

        # RESTART: A node is restarting. Notifies its connections of its drop.
        #
        # src = node that is restarting
        if eventEntry.eventType == RESTART:
            for ip in src.incomingCnxs:
                self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                          destNode = self.ipToNodes[ip], 
                                                          eventType = DROP, 
                                                          info = "outgoing")))
            for ip in eventEntry.srcNode.outgoingCnxs:
                self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                          destNode = self.ipToNodes[ip],
                                                          eventType = DROP, 
                                                          info = "incoming")))

        # DROP: A node is notified that one of its connections was dropped 
        #        and updates its list of connections accordingly.
        #
        # src = node that was dropped
        # dest = node that was notified to update its connections from the drop
        # info = "incoming" if src was in dest's incoming connections, 
        #           else "outgoing"
        elif eventEntry.eventType == DROP:
            ipToRemove = src.ipV4Addr
            bucket = dest.mapToTriedBucket(ipToRemove)
            del dest.triedTable[bucket][ipToRemove]

            if eventEntry.info == "incoming":
                dest.incomingCnxs.remove(ipToRemove)
            else:
                dest.outgoingCnxs.remove(ipToRemove)

            numTriedEntries = sum([len(bucket) for bucket in dest.triedTable])
            numNewEntries = sum([len(bucket) for bucket in dest.newTable])

            rho = float(numTriedEntries) / numNewEntries
            omega = len(dest.outgoingCnxs)
            numRejects = 0
            accepted = False

            PrTried = (rho**0.5) * (9 - omega) 
            PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 

            table = src.triedTable if random.random() < PrTried else src.newTable
            ip = None
            while not accepted:
                bucketNum = random.randint(0, len(table) - 1)
                bucketPos = random.randint(0, len(table[bucketNum]) - 1)
                ip = table[bucketNum].keys()[bucketPos]
                timestamp = table[bucketNum][ip]
                t = ((self.globalTime - timestamp) / 600) * 10
                probAccept = min(1, (1.2**numRejects) / float(1 + t))
                accepted = random.random() < probAccept
                numRejects += 1
            self.eventQueue.put((scheduledTime, event(srcNode = dest, 
                                                      destNode = self.ipToNodes[ip],
                                                      eventType = CONNECT, 
                                                      info = None)))

        # JOIN: A node is requesting to join the network. 
        #        Randomly choose a seeder to contact for connection information.
        #
        # src = node that is requesting to join
        elif eventEntry.eventType == JOIN:
            seeder = self.seederNodes[random.randint(0, NUM_SEEDERS - 1)]
            self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                      destNode = seeder, 
                                                      eventType = REQUEST_CONNECTION_INFO, 
                                                      info = None)))

        # CONNECT: A node is requesting to connect to another node.
        # 
        # src = node that is requesting the connection
        # dest = node that is receiving this request
        elif eventEntry.eventType == CONNECT:
            if len(dest.incomingCnxs) <= MAX_INCOMING:
                src.addToTried(dest.ipV4Addr, self.globalTime)
                dest.addToTried(src.ipV4Addr, self.globalTime)
                src.outgoingCnxs.append(dest.ipV4Addr)
                dest.incomingCnxs.append(src.ipV4Addr)
            else:
                self.eventQueue.put((scheduledTime, event(srcNode = dest,
                                                          destNode = src,
                                                          eventType = CONNECTION_FAILURE,
                                                          info = None)))

        # CONNECTION_FAILURE: Notifies a node that its connection request failed.
        # 
        # src = the node that rejected the connection request
        # dest = the node whose request failed
        elif eventEntry.eventType == CONNECTION_FAILURE:
            numTriedEntries = sum([len(bucket) for bucket in dest.triedTable])
            numNewEntries = sum([len(bucket) for bucket in dest.newTable])
            rho = float(numTriedEntries) / numNewEntries
            omega = len(dest.outgoingCnxs)
            numRejects = 0
            accepted = False
            PrTried = (rho**0.5) * (9 - omega) 
            PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
            table = src.triedTable if random.random() < PrTried else src.newTable
            ip = None
            while not accepted:
                bucketNum = random.randint(0, len(table) - 1)
                bucketPos = random.randint(0, len(table[bucketNum]) - 1)
                ip = table[bucketNum].keys()[bucketPos]
                timestamp = table[bucketNum][ip]
                t = ((globalTime - timestamp) / 600) * 10
                probAccept = min(1, (1.2**numRejects) / float(1+t))
                accepted = random.random() < probAccept
                numRejects += 1
            self.eventQueue.put((scheduledTime, event(srcNode = dest,
                                                      destNode = self.ipToNodes[ip],
                                                      eventType = CONNECT,
                                                      info = None)))

        # REQUEST_CONNECTION_INFO: A node is requesting information about nodes 
        #                           to connect to
        # 
        # src = the requesting node
        # dest = seeder node that will answer the request
        elif eventEntry.eventType == REQUEST_CONNECTION_INFO:
            self.eventQueue.put((scheduledTime, event(srcNode = dest, 
                                                      destNode = src, 
                                                      eventType = CONNECTION_INFO, 
                                                      info = self.hardcodedIPs[:])))

        # CONNECTION_INFO: A node is receiving information about nodes to connect to.
        # 
        # src = seeder node that sent the connection info
        # dest = node that is receiving the connection info
        # info = list of IP addresses to connect to
        elif eventEntry.eventType == CONNECTION_INFO:
            connections = eventEntry.info[:]
            random.shuffle(connections)
            for ip in connections[:MAX_OUTGOING]:
                self.eventQueue.put((scheduledTime, event(srcNode = dest, 
                                                          destNode = self.ipToNodes[ip], 
                                                          eventType = CONNECT, 
                                                          info = None)))
            for ip in connections[MAX_OUTGOING:]:
                dest.addToNew(ip, self.globalTime, src.ipV4Addr)
        else:
            raise Exception("Invalid event type")