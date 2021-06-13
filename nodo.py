import os
import sys
import time
import pickle
import socket
import random
import hashlib
import threading
from scraping import Scrapper

from tools import *
from collections import OrderedDict

class Node:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.address = (ip, port)
        self.id = getHash(f'{ip}:{str(port)}')
        self.pred = (ip, port)
        self.predID = self.id
        self.succ = (ip, port)
        self.succID = self.id
        self.fingerTable = OrderedDict()
        self.filenameList = []
        try:
            self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ServerSocket.bind((IP, PORT))
            self.ServerSocket.listen()
        except socket.error:
            print('Socket not opened')

    def start(self):
        '''
        Accepting connections from other threads.
        '''
        threading.Thread(target=self.listenThread, args=()).start()
        threading.Thread(target=self.pingSucc, args=()).start()
        # In case of connecting to other clients
        while True:
            print('Listening to other clients')

    def listenThread(self):
        '''
        Storing the IP and port in address and saving 
        the connection and threading.
        '''
        while True:
            try:
                connection, address = self.ServerSocket.accept()
                connection.settimeout(120)
                threading.Thread(target=self.connectionThread, args=(connection, address)).start()
            except socket.error:
                pass

    def connectionThread(self, connection, address):
        '''
        datos[0] da el tipo de conexion
        Tipos de conecciones 0 : nodo nuevo
        '''
        datos = pickle.loads(connection.recv(BUFFER))
        connectionType = datos[0]
        if connectionType == 0:
            print(f'Connection with: {address[0]} : {address[1]}')
            print('Join network request recevied')
            self.joinNode(connection, address, datos)
        elif connectionType == 1:
            self.Scrapping(connection,address,datos)
        elif connectionType == 2:
            connection.sendall(pickle.dumps(self.pred))
        elif connectionType == 3:
            self.SearchID(connection, address, datos)
        elif connectionType == 4:
            if datos[1] == 1:
                self.updateSucc(datos)
            else:
                self.updatePred(datos)
        elif connectionType == 5:
            self.updateFingerTable()
            connection.sendall(pickle.dumps(self.succ))
        else:
            print('Problem with connection type')

    def sendJoinRequest(self, ip, port):
        try:
            recvAddress = self.getSuccessor((ip, port), self.id)
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect(recvAddress)
            # 0 para que sepa que me quiero unir y le mando mi ip,puerto
            datos = [0, self.address]
            peerSocket.sendall(pickle.dumps(datos))
            #recibo en datos quien es mi antecesor
            datos = pickle.loads(peerSocket.recv(BUFFER))            
            self.pred = datos[0]
            self.predID = getHash(f'{self.pred[0]}:{str(self.pred[1])}')
            self.succ = recvAddress
            self.succID = getHash(f'{self.succ[0]}:{str(self.succ[1])}')
            datos = [4, 1, self.address]
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #entra al antecesor para que actualice su succesor conmigo
            pSocket2.connect(self.pred)
            pSocket2.sendall(pickle.dumps(datos))
            pSocket2.close()
            peerSocket.close()
        except socket.error:
            print('Socket error. Recheck IP/Port.')

    def joinNode(self, connection, address, datos):
        '''
        Recibe la request del nodo nuevo
        '''
        if datos:
            #recibo la direccion del nodo
            peerAddr = datos[1]
            peerID = getHash(f'{peerAddr[0]}:{str(peerAddr[1])}')
            oldPred = self.pred
            self.pred = peerAddr
            self.predID = peerID
            datos = [oldPred]
            #le envio a su antecesor
            connection.sendall(pickle.dumps(datos))
            time.sleep(0.1)
            self.updateFingerTable()
            self.updateOtherFingerTables()
            
    def getSuccessor(self, address, keyID):
        datos = [1, address]
        recvAddress = address
        while datos[0] == 1:
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                peerSocket.connect(recvAddress)
                #Buscar id
                datos = [3, keyID]
                peerSocket.sendall(pickle.dumps(datos))
                datos = pickle.loads(peerSocket.recv(BUFFER))
                recvAddress = datos[1]
                peerSocket.close()
            except socket.error:
                print('Connection denied while getting Successor')
        return recvAddress

    def updateFingerTable(self):
        for i in range(MAX_BITS):
            entryId = (self.id + (2 ** i)) % MAX_NODES
            if self.succ == self.address:
                self.fingerTable[entryId] = (self.id, self.address)
                continue
            recvAddr = self.getSuccessor(self.succ, entryId)
            recvId = getHash(f'{recvAddr[0]}:{str(recvAddr[1])}')
            self.fingerTable[entryId] = (recvId, recvAddr)

    def updateOtherFingerTables(self):
        here = self.succ
        while True:
            if here == self.address:
                break
            pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                pSocket.connect(here)
                pSocket.sendall(pickle.dumps([5]))
                here = pickle.loads(pSocket.recv(BUFFER))
                pSocket.close()
                if here == self.succ:
                    break
            except socket.error:
                print('Connection denied')

    def updateSucc(self, datos):
        newSucc = datos[2]
        self.succ = newSucc
        self.succID = getHash(f'{newSucc[0]}:{str(newSucc[1])}')

    def updatePred(self, datos):
        newPred = datos[2]
        self.pred = newPred
        self.predID = getHash(f'{newPred[0]}:{str(newPred[1])}')

    def SearchID(self, connection, address, datos):
        keyID = datos[1]
        datos = []

        # Caso 0: si soy yo
        if self.id == keyID:
            datos = [0, self.address]
        # Caso 1: si nada mas existe 1 nodo
        elif self.succID == self.id:
            datos = [0, self.address]
        # Caso 2: si mi id es mayor que el keyID, preguntar al antecesor
        elif self.id > keyID:
            if self.predID < keyID:
                datos = [0, self.address]
            elif self.predID > self.id:
                datos = [0, self.address]
            else:
                datos = [1, self.pred]
        # Case 3: si mi id es menor que el keyID, usar la fingertable para buscar al mas cercano
        else:
            if self.id > self.succID:
                datos = [0, self.succ]
            else:
                value = ()
                for key, value in self.fingerTable.items():
                    if key >= keyID:
                        break
                value = self.succ
                datos = [1, value]
        connection.sendall(pickle.dumps(datos))
    
    def sendScrappingRequest(self, ip, puerto, URL, profundidad=0):
        urlID = getHash(URL)
        recvAddress = self.getSuccessor((ip,puerto),urlID)
        peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peerSocket.connect(recvAddress)
        datos = [1,URL]
        #Envio la url a scrapear
        peerSocket.sendall(pickle.dumps(datos))
        #recibo todo el scrapping de la URL
        datos = pickle.loads(peerSocket.recv(BUFFER)) 
        filename = URL.split('/')[-1]
        fileAlready = False
        try:
            file = open("./www/"+str(filename), "w")
            data = file.read()
            size = len(data)
            if size == 0:
                print('Retransmission request sent')
                fileAlready = False
            else:
                print('File already present')
                fileAlready = True
            return
        except FileNotFoundError:
            pass

        if not fileAlready:
            totalData = b''
            try:
                file = open("./www/"+str(filename), "w")
                while True:
                    fileData = connection.recv(BUFFER)
                    if not fileData:
                        break
                    totalData += fileData
                file.write(totalData)
            except ConnectionResetError:
                print('Data transfer interupted')
                print('Waiting for system to stabilize')
                print('Trying again in 10 seconds')
                os.remove(filename)
                

        

    def Scrapping(self,connection, URL,datos):
        urlID = getHash(URL)
        print('Sending scrapping:', URL)
        try:
            file = ("./Almacen/"+str(urlID), "r")
            file.close()            
        except:
            print('File not found...scrapping')
            scrapy = Scrapper(URL)
            scrapy.scrapping()
            scrapy.Save()
        try:
            file = open("./Almacen/"+str(urlID),"r")
                while True:
                    fileData = file.read(BUFFER)
                    time.sleep(0.001)
                    if not fileData:
                        break
                    connection.sendall(fileData)
        except:
            pass
        print('File sent')

        
    
    

    
    
if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Arguments not supplied (defaults used)')
    else:
        IP = sys.argv[1]
        PORT = int(sys.argv[2])

    node = Node(IP, PORT)
    print(f'My ID is: {node.id}')
    node.start()