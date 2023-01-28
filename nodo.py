from genericpath import exists
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
        self.succesorDelSuccesor = (ip, port)
        self.fingerTable = OrderedDict()
        self.UrlList = []
        self.DepthList = []
        try:
            self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ServerSocket.bind((IP, PORT))
            self.ServerSocket.listen()
        except socket.error:
            print('Socket not opened')

    def Cliente(self):
        self.menu()
        userChoice = input()
        if userChoice == '1':
            ip = input('Enter IP to connect: ')
            port = input('Enter port: ')
            self.sendJoinRequest(ip, int(port))
        elif userChoice == '2':
            URL = input('Enter the URL: ')
            profundidad = input('Depth level: ')
            self.sendScrappingRequest(URL, profundidad)
        elif userChoice == '3':
            self.printFingerTable()
        elif userChoice == '4':
            print(f'My ID: {self.id}')
            print(f'Predecessor: {self.predID}')
            print(f'Successor: {self.succID}')
            succsuccID = getHash(f'{self.succesorDelSuccesor[0]}:{str(self.succesorDelSuccesor[1])}')
            print(f'Successor of my successor: {succsuccID}')       

    def printFingerTable(self):
        print('Printing Finger Table')
        for key, value in self.fingerTable.items(): 
            print(f'KeyID: {key}, Value: {value}')

    def menu(self):        
        print("1- Connect to the network\n2- URL to Scrapp\n3- Print Finger Table\n4- Node Information")     
    
    def start(self):
        '''
        Accepting connections from other threads.
        '''
        threading.Thread(target=self.listenThread, args=()).start()
        threading.Thread(target=self.pingSucc, args=()).start()
        # In case of connecting to other clients
        while True:
            print('Listening to other clients')
            self.Cliente()

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
            if datos[1] == 0:
                connection.sendall(pickle.dumps(self.pred))
            else:
                connection.sendall(pickle.dumps([2,1,self.succ]))
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
        elif connectionType == 6:
            self.RecibirArchivo(connection, datos[1], 1)
            pass
        elif connectionType == 7:
            self.updateSucc2(datos)
        elif connectionType == 8:
            self.ActualizarSuccSucc()
        elif connectionType == 9:
            self.ReplicateAll()     
        else:
            print('Problem with connection type')

    def sendJoinRequest(self, ip, port):
        try:
            recvAddress = self.getSuccessor((ip, port), self.id)
            #print("mi sucesor es "+ str(recvAddress[1]))
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect(recvAddress)
            #print("me conecto a mi sucesor")
            # 0 para que sepa que me quiero unir y le mando mi ip,puerto
            datos = [0, self.address]
            peerSocket.sendall(pickle.dumps(datos))
            #print("le envio mi direccion que es "+str(self.address[1]))
            #recibo en datos quien es mi antecesor
            datos = pickle.loads(peerSocket.recv(BUFFER)) 
                      
            self.pred = datos[0]
            self.predID = getHash(f'{self.pred[0]}:{str(self.pred[1])}')
            #print("recibo mi antecesor "+ str(self.predID)) 
            self.succ = recvAddress
            
            self.succID = getHash(f'{self.succ[0]}:{str(self.succ[1])}')
            #print("actualizo mi sucesor con "+str(self.succID))
            datos = [4, 1, self.address]
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #entra al antecesor para que actualice su sucesor conmigo
            pSocket2.connect(self.pred)
            pSocket2.sendall(pickle.dumps(datos))
            #print("Actualizo el sucesor de mi antecesor")
            pSocket2.close()
            peerSocket.close()
            #entra al antecesor para que actualice el sucesor de su sucesor
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket2.connect(self.pred)
            pSocket2.sendall(pickle.dumps([7,1,self.succ]))
            pSocket2.close()
            time.sleep(0.1)
            self.ActualizarSuccSucc()
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket2.connect(self.succ)
            pSocket2.sendall(pickle.dumps([8]))
            pSocket2.close()   
            #entro a mi predecesor para que se replique en mi
            pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket2.connect(self.pred)
            pSocket2.sendall(pickle.dumps([9]))
            pSocket2.close()   
            
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
            #print("llego "+str(peerID))
            
            oldPred= self.pred
            self.pred = peerAddr
            self.predID = peerID
            #print("Actualizo mi predecesor con "+ str(self.predID))
            datos = [oldPred]
            #le envio a su antecesor
            #print("Le envio su predecesor que es "+str(datos))
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

    def updateSucc2(self, datos):
        newSucc2 = datos[2]
        self.succesorDelSuccesor = newSucc2

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
    
    def sendScrappingRequest(self, URL, profundidad=0):
        self.UrlList.append(URL)
        self.DepthList.append(0)
        while len(self.UrlList) > 0:
            url = self.UrlList.pop(0)
            depth = self.DepthList.pop(0)
            #print(len(self.UrlList))
            urlID = getHash(url)
            recvAddress = self.getSuccessor(self.succ,urlID)
            #name = url.split('/')[-1]
            filename = self.changeFilename(url)
            
            #lo debo tener yo mismo
            if recvAddress[0] == self.address[0] and recvAddress[1] == self.address[1]:

                if not os.path.exists("./Almacen/"+str(urlID)):
                    print('URL not found... scrapping')
                    scrapy = Scrapper(url,depth,profundidad)
                    scrapy.scrapping()
                    scrapy.Save()
                    print("Scrapped url... ")
                    #replicar el archivo en mi sucesor
                    self.Replicate(urlID)
                    file = open("./Almacen/"+str(urlID),"rb")
                    file1 = open("./www/"+filename,"wb")
                    text = file.read()
                    file1.write(text)
                    file.close()
                    file1.close()
                    #Agrego a la cola las url a scrapear en profundidad
                    self.UrlList.extend(scrapy.taskQ)
                    self.DepthList.extend(scrapy.depthQ)
                else:
                    print("Url found... : "+str(url))
                    scrapy = Scrapper(url,depth,profundidad)
                    file = open("./Almacen/"+str(urlID),"rb")
                    text = file.read()
                    scrapy.getLink(text)
                    file1 = open("./www/"+filename,"wb")
                    file1.write(text)
                    file.close()
                    file1.close()
                    self.Replicate(urlID)
                    self.UrlList.extend(scrapy.taskQ)
                    self.DepthList.extend(scrapy.depthQ)
            else:
                print('Sending scrapping:', url)
                peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peerSocket.connect(recvAddress)
                datos = [1,url,depth,profundidad]
                #Envio la url a scrapear con su profundidad y la profundidad maxima
                peerSocket.sendall(pickle.dumps(datos))
                #recibo todo el scrapping en profundidad +1 de la Url y sus profundidades
                datos = pickle.loads(peerSocket.recv(BUFFER)) 
                self.UrlList.extend(datos[0])
                self.DepthList.extend(datos[1])
                self.RecibirArchivo(peerSocket,filename)   

    def Scrapping(self,connection, address, datos):
        URL = datos[1]
        urlID = getHash(URL)
        depth = int(datos[2])
        max_depth = int(datos[3])

        if not os.path.exists("./Almacen/"+str(urlID)):
            print('URL not found... scrapping')
            scrapy = Scrapper(URL,depth,max_depth)
            scrapy.scrapping()
            scrapy.Save()
            print('Scrapped: '+str(URL))
            connection.sendall(pickle.dumps([scrapy.taskQ, scrapy.depthQ]))
            time.sleep(0.1)  
        else:
            print("Url found... : ")
            scrapy = Scrapper(URL,depth,max_depth)
            file = open("./Almacen/"+str(urlID),"rb")
            text = file.read()
            scrapy.getLink(text)
            connection.sendall(pickle.dumps([scrapy.taskQ, scrapy.depthQ]))
            time.sleep(0.1)  

        self.EnviarArchivo(connection, urlID)
        #replicar el archivo en mi sucesor
        self.Replicate(urlID)

    def EnviarArchivo(self, connection, fileID):
        file_open=0
        try:
            file = open("./Almacen/"+str(fileID),"rb")
            file_open=1
            fileData = file.read(BUFFER)
            while fileData:                
                connection.send(fileData)
                fileData = file.read(BUFFER)
        except:
            if file_open:
                file.close()
            connection.close()
            print("The file has not been sent")
            return
        
        # Se utiliza el caracter de código 1 para indicar
        # al cliente que ya se ha enviado todo el contenido.
        try:
            connection.send(chr(1))
        except TypeError:
            # Compatibilidad con Python 3.
            connection.send(bytes(chr(1), "utf-8"))

        # Cerrar conexión y archivo.
        connection.close()
        file.close()
        
        #pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #pSocket.connect(self.succ)
        #pSocket.sendall(pickle.dumps([6,fileID]))
        #state = pSocket.recv(BUFFER)
        #if state == 'notfound':
        #    try:
        #        file = open("./Almacen/"+str(fileID),"rb")
        #        file_open=1
        #        fileData = file.read(BUFFER)
        #        while fileData:                
        #            connection.send(fileData)
        #            fileData = file.read(BUFFER)
        #    except:
        #        if file_open:
        #            file.close()
        #        connection.close()
        #        print("No se mando ni carajo")
        #        return
        #try:
        #    connection.send(chr(1))
        #except TypeError:
        #    # Compatibilidad con Python 3.
        #    connection.send(bytes(chr(1), "utf-8"))
        #
        #connection.close()
        #file.close()

        print("The file has been sent successfully.")

    def RecibirArchivo(self,connection,filename, flag = 0):
        try:
            file=0
            if  flag:
                print("Replicating files from its predecessor...")
                file = open("./Almacen/"+str(filename), "wb")
            else:
                file = open("./www/"+str(filename), "wb")
            while True:                
                fileData = connection.recv(BUFFER)
                if fileData:                    
                    if isinstance(fileData, bytes):
                        end = fileData[0] == 1
                    else:
                        end = fileData == chr(1)
                    if not end:
                        # Almacenar datos.
                        file.write(fileData)
                    else:
                        break
                else:
                    break
            file.close()
            connection.close()
            print("All written on file")
        except ConnectionResetError:
            print('Interrupted data transfer')
            print('Waiting for the system to stabilize')
            print('Try again in 10 seconds')
            os.remove(filename)

    def pingSucc(self):
        while True:
            # Ping every 5 seconds
            time.sleep(5)
            if self.address == self.succ:
            # If only one node, no need to ping
                continue
            try:
                pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                #print("abri el socket")
                pSocket.connect(self.succ)
                #print("me conecte")
                pSocket.sendall(pickle.dumps([2,0]))
                #print("envie ping")
                recvPred = pickle.loads(pSocket.recv(BUFFER))
                
            except:
                print('\nNode offline detected \nStabilizing...')
                
                if not self.succ == self.pred:
                    # Search for the next succ
                    self.succ = self.succesorDelSuccesor
                    self.succID = getHash(f'{self.succ[0]}:{str(self.succ[1])}')

                    # Informa al nuevo sucesor para que actualice su predecesor conmigo
                    pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pSocket.connect(self.succ)
                    pSocket.sendall(pickle.dumps([4, 0, self.address]))
                    pSocket.close()

                    #entra al antecesor para que actualice el sucesor de su sucesor
                    pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pSocket2.connect(self.pred)
                    pSocket2.sendall(pickle.dumps([7,1,self.succ]))
                    pSocket2.close()
                    time.sleep(0.1)

                    #actualiza mi sucesor sucesor
                    self.ActualizarSuccSucc()

                    #entra a mi sucesor para que actualice el sucesor de su sucesor
                    pSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pSocket2.connect(self.succ)
                    pSocket2.sendall(pickle.dumps([8]))
                    pSocket2.close()

                    self.ReplicateAll()
                else:
                    self.pred = self.address
                    self.predID = self.id
                    self.succ = self.address
                    self.succID = self.id
                    
                self.updateFingerTable()
                self.updateOtherFingerTables()
                self.menu()
    
    def ReplicateAll(self):
        for fileName in os.listdir("./Almacen/"):
            pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pSocket.connect(self.succ)
            pSocket.sendall(pickle.dumps([6, fileName]))
            self.EnviarArchivo(pSocket, fileName)
            print('Replicated file: '+str(fileName)) 
    
    def Replicate(self, KeyID):
        pSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pSocket.connect(self.succ)
        pSocket.sendall(pickle.dumps([6, KeyID]))
        self.EnviarArchivo(pSocket, KeyID)
        print('Replicated file: '+str(KeyID))

    def ActualizarSuccSucc(self):
        psocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        psocket.connect(self.succ)
        psocket.sendall(pickle.dumps([2,1]))
        datos = pickle.loads(psocket.recv(BUFFER))
        self.updateSucc2(datos)
        psocket.close()

    def changeFilename(self, name):
        splitName = name.replace(':', '-').replace('?', '+').replace('=', '$').split('/')
        #splitName = splitName[max(0, len(splitName) - 4):]
        return '@'.join(splitName)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Arguments not supplied (defaults used)')
    else:
        IP = sys.argv[1]
        PORT = int(sys.argv[2])

    node = Node(IP, PORT)
    print(f'My ID is: {node.id}')
    node.start()