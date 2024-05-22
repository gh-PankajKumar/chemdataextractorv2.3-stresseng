"""Elsevier Webscraper
Elsevier webscraper to search and download articles from the publisher. 
Makes use of the Elsevier API and a ScienceDirect API key is required for full functionality.


:code author: Pankaj Kumar (pk503@cam.ac.uk)
"""

import sys
import os
import requests

class ElsevierScraper:
    """Elsevier download and search

    Attributes:
        api (str): Elsevier ScienceDirect API key 
        dois (list): List of unique article DOIs matching search criteria
    """    

    def __init__(self, api):
        """Initialise Class

        Args:
            api (str): Elsevier ScienceDirect API key 
        """        
     
        self.api = api
        self.dois = []        

    def search(self, params):
        """Search for articles on ScienceDirect

        Args:
            params (dict): Search parameters

        Returns:
            response (dict): Response body from search request
        """
        url = "https://api.elsevier.com/content/search/sciencedirect"
        response = requests.put(
            url,
            json=params,
            headers={"X-ELS-APIkey": self.api}
            ).json()
        self._extract_doi(response)            
        return response


    def download(self, doi, save_dir):
        """Save article locally

        Args:
            doi (str): Unique DOI of article
            save_dir (str): Path to parent save directory
        """              
        self._check_dirs(save_dir)        
        
        article = self._get_article(doi)
        if not self._is_complete(article) and self._is_article_type(article):
            if self._is_openaccess(article):
                with open(self.open_dir + doi.replace("/", "-"), "w+", encoding="utf-8") as save_file:
                    save_file.write(article)
            elif not self._is_openaccess(article):
                with open(self.sub_dir + doi.replace("/", "-"), "w+", encoding="utf-8") as save_file:
                    save_file.write(article)                                    
        else:
            with open(self.other_dir + doi.replace("/", "-"), "w+", encoding="utf-8") as save_file:
                save_file.write(article)                   

    def _extract_doi(self, response):
        """Extract DOIs from response body.

        Scan response body, extract all article DOIs and append to DOI list.

        Args:
            response (json): Response body from search request
        """
        for article in response["results"]:
            doi = article["doi"]
            self.dois.append(doi)

    def _is_complete(self, article_content):
        """Check if article is complete

        Args:
            article_content (str): Article text body

        Returns:
            Boolean: True if complete article. False if incomplete.
        """
        if "<xocs:rawtext>" in article_content:
            return True
        return False


    def _is_openaccess(self, article_content):
        """Check if article is open access

        Args:
            article_content (str): Article text body

        Returns:
            Boolean: True if open access. False if sub access.
        """
        if "<openaccess>1</openaccess>" in article_content:
            return True
        elif "<openaccess>0</openaccess>" in article_content:
            return False
        return "Error"


    def _is_article_type(self, article_content):
        """Check article type

        Args:
            article_content (str): Article text body

        Returns:
            Boolean: True if article. False if "other" e.g. book.
        """
        if "<xocs:document-subtype>fla</xocs:document-subtype>" in article_content:
            return True

        return False

    def _check_dirs(self, save_dir):    
        """Make save directories for articles.

        Args:
            save_dir (str): Path to article save directory 
        """            
        self.open_dir = save_dir + "OpenAccess/"
        self.sub_dir = save_dir + "SubAccess/"
        self.other_dir = save_dir + "NotArticles/"

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

        if not os.path.exists(self.other_dir):
            print(
                f"{self.other_dir} directory does not exists.\nCreating directory {self.other_dir}"
            )
            os.makedirs(self.other_dir)        

    def _get_article(self, doi):
        """Get article XML

        Args:
            doi (str): Unique DOI of article

        Returns:
            article (str): Text of article XML content
        """        
        url = "https://api.elsevier.com/content/article/doi/" + doi
        article = requests.get(
            url,
            headers={                
                "x-els-apikey": self.api,
                "Content-Type": "application/json",                
            }
        ).text
        print(requests.get(
            url,
            headers={                
                "x-els-apikey": self.api,
                "Content-Type": "application/json",                
            }).url)

        return article


 


    

