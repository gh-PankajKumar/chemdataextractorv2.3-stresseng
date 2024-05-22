"""Springer Webscraper
Springer webscraper to search and download articles from the publisher. 

:code author: Pankaj Kumar (pk503@cam.ac.uk)
""" 

import os
import requests
import sys
from bs4 import BeautifulSoup


class SpringerScraper:
    """Springer article search, download and process 

    Attributes:
        api_key (str): Springer TDM API Key
    """    

    def __init__(self, api_key):
        """Initialise Class

        Args:
            api_key (str): Springer TDM API Key
        """        
        self.api = api_key

    def search(self, params):
        """Search for Springer articles

        Args:
            params (dict): Search parameters

        Returns:
            response (object): Response body from search request
        """        
    
        url = 'https://articles-api.springer.com/xmldata/jats'
        params['api_key'] = self.api
        response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        print(f'DEBUG: response url is {response.url}')
        if response:
            return response
        else:
            print(f"\nsearch error: {response}\nresponse url: {response.url}")
            sys.exit()

    def get_dois(self, response):
        """Get list of DOIs from Springer search response

        Args:
            response (object): Response body from search request

        Returns:
            dois (list): List of DOIs
        """
        response_content = response.content
        soup = BeautifulSoup(response_content, features="html.parser")
        doi = soup.find_all("article-id", attrs={"pub-id-type": "doi"})
        dois = [i.text for i in doi]
        return dois

    def get_total_results(self, response):
        """Gets total number of results from Springer search response

        Args:
            response (object): Response body from search request

        Returns:
            total_results (str): Total number of results 
            
        """
        soup = BeautifulSoup(response.content, "lxml")
        total_results = soup.find("total").get_text()
        # print(total_results)
        return total_results

    def download_doi(self, doi, save_dir):
        """Download article associated to DOI from Springer

        Args:
            doi (string): DOI of article
        """
        self._check_dirs(save_dir)
        url = f"https://articles-api.springer.com/xmldata/jats?q=doi:{doi}&p=1&api_key={self.api}"
        #print(f'DEBUG: download url is {url}')
        web_content = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).content
        soup = BeautifulSoup(web_content, features="html.parser")
        try:
            open_access = soup.find("meta-name", text = 'open-access').parent.find("meta-value").get_text()
            full_text = soup.find_all("sec")

            filename = doi.replace("/", "_")

            if not full_text:
                save_path = self.notfull_dir + filename + '.xml'

            elif open_access == "true":
                save_path = self.open_dir + filename + '.xml' 

            elif open_access == 'false':
                save_path = self.sub_dir + filename + '.xml' 

            else: 
                save_path = self.other_dir + filename + '.xml'
            
            with open(save_path, 'wb') as f:
                f.write(web_content)
                f.close()

        except:
            filename = doi.replace("/", "_")
            save_path = self.other_dir + filename + '.xml'
            print(f"Error is getting article with doi: {doi}\t Saving response content in {save_path}\n URL is: {url}")
        return

 
    def _check_dirs(self, save_dir):    
        """Make save directories for articles.

        Args:
            save_dir (str): Path to article save directory 
        """            
        self.open_dir = save_dir + "OpenAccess/"
        self.sub_dir = save_dir + "SubAccess/"
        self.notfull_dir = save_dir + "NotFullText/"
        self.other_dir = save_dir + "Other/"

        if not os.path.exists(self.open_dir):
            print(
                f"{self.open_dir} directory does not exists.\nCreating directory {self.open_dir}"
            )
            os.makedirs(self.open_dir)

        if not os.path.exists(self.sub_dir):
            print(
                f"{self.sub_dir} directory does not exists.\nCreating directory {self.sub_dir}"
            )
            os.makedirs(self.sub_dir)

        if not os.path.exists(self.notfull_dir):
            print(
                f"{self.notfull_dir} directory does not exists.\nCreating directory {self.notfull_dir}"
            )
            os.makedirs(self.notfull_dir)   
    

        if not os.path.exists(self.other_dir):
            print(
                f"{self.other_dir} directory does not exists.\nCreating directory {self.other_dir}"
            )
            os.makedirs(self.other_dir)   
    