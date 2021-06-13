from bs4 import BeautifulSoup
import requests
import time
<<<<<<< HEAD
from urllib.parse import urlparse, urljoin
import hashlib
from tools import *
import tldextract as tld

class Scrapper:
    def __init__(self,url,profundidad=0,max_depth=0):
        self.url = url
        self.profundidad = profundidad
        self.max_depth = max_depth
        dicionario = dict()
        self.taskQ = []
        self.depthQ = []
        self.text = ""
    
    def getLink(self, html):
        d = tld.extract(self.url)
        dominio = d.domain
        baseUrl = self.url
        if html != None and int(self.max_depth) - int(self.profundidad) > 0:
            soup = BeautifulSoup(html, 'lxml')
            soupTag = soup.find_all(self.validTags)   

            for key in range(len(soupTag)):
                if soupTag[key].has_attr('href'):
                    url_link = urljoin(baseUrl, soupTag[key]['href'])
                    dominio_link = tld.extract(url_link).domain
                    if dominio_link in dominio and not url_link.endswith('.ico') and self.Valid(url_link):
                        self.taskQ.append(url_link)
                        self.depthQ.append(self.profundidad+1)

                if soupTag[key].has_attr('src'):
                    url_link = urljoin(baseUrl, soupTag[key]['src'])  
                    dominio_link = tld.extract(url_link).domain                
                    if dominio_link in dominio and not url_link.endswith('.ico') and self.Valid(url_link):
                        self.taskQ.append(url_link)
                        self.depthQ.append(self.profundidad+1)

    def scrapping(self):
        d = tld.extract(self.url)
        dominio = d.domain
        baseUrl = self.url
        if self.Valid(self.url):
            html = self.getHTML(self.url)
            self.text = html

            if html != None and int(self.max_depth) - int(self.profundidad) > 0:
                soup = BeautifulSoup(html, 'lxml')
                soupTag = soup.find_all(self.validTags)   

                for key in range(len(soupTag)):
                    if soupTag[key].has_attr('href'):
                        url_link = urljoin(baseUrl, soupTag[key]['href'])
                        dominio_link = tld.extract(url_link).domain
                        if dominio_link in dominio and not url_link.endswith('.ico') and self.Valid(url_link):
                            self.taskQ.append(url_link)
                            self.depthQ.append(self.profundidad+1)

                    if soupTag[key].has_attr('src'):
                        url_link = urljoin(baseUrl, soupTag[key]['src'])  
                        dominio_link = tld.extract(url_link).domain                
                        if dominio_link in dominio and not url_link.endswith('.ico') and self.Valid(url_link):
                            self.taskQ.append(url_link)
                            self.depthQ.append(self.profundidad+1)
 
        else:
            print('Invalid URL ' + self.url)   

    def getHTML(self, url:str):
        wait = 0
        while True:
            try:
                with requests.get(url) as response:
                    html = response.text
                break
            except requests.exceptions.ConnectionError as exc:
                if wait == 2:
                    return

                time.sleep(2 ** wait)
                wait = wait + 1
        return html
=======
from urllib.parse import urlparse
import hashlib
from tools import *

class Scrapper:
    def __init__(self,url,profundidad=0):
        self.url = url
        self.profundidad = profundidad
        dicionario = dict()
        self.text = ""
        
    def scrapping(self):
        if self.Valid(self.url):
            peticion = requests.get(self.url)
            self.text = peticion.text
        else:
            print('Invalid URL ' + url)   

    def Valid(self,url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False     

    def Save(self):
        filename = getHash(self.url)
        file = open("./www/"+str(filename), "w")
        file.write(self.text)
        file.close()


if __name__ == "__main__":
    print("Escriba URL")
    url = input()
    scrapy = Scrapper(url)
    scrapy.scrapping(url)
    print(scrapy.text)
    scrapy.Save()
    
>>>>>>> 6d9712f (start)
