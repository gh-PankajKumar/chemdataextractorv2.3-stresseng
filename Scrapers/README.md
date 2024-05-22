# Webscraper for Elsevier and Springer Articles

This project provides Python web scrapers to search and download scientific articles from Elsevier's ScienceDirect and Springer's platforms.

## Features

Search both Elsevier (ScienceDirect) and Springer for articles based on customizable parameters. Download articles as XML files, classifying them as Open Access, Subscription Access, Not Full Text, or Other. Automatically creates necessary directories for organized storage. Handles potential errors during article retrieval.

## Install Dependencies

```Bash

pip install requests beautifulsoup4 pyparsing
```

## Usage

Obtain API Keys:

- Elsevier: Get a ScienceDirect API key from Elsevier Developer Portal.
- Springer: Get a Springer Nature Text and Data Mining (TDM) API key.

### Elsevier Example

```Python

from elsevier_scraper import ElsevierScraper

scraper = ElsevierScraper(API_KEY)
search_params = {
    "qs": "yield strength", # Example search query
    "display": {"show": 100},        
    "content": {"openaccess": True}  # Only retrieve open access articles
}
search_result = scraper.search(search_params)
for doi in scraper.dois:
    scraper.download(doi, "path/to/save/directory/")
```

### Springer Example

```Python

from springer_scraper import SpringerScraper

scraper = SpringerScraper(API_KEY)
search_params = {
    "q": "tensile strength",    # Example search query
    "p": 100                           # Number of results per page
}
search_result = scraper.search(search_params)

dois = scraper.get_dois(search_result)  
total_results = scraper.get_total_results(search_result)

for doi in dois:
    scraper.download_doi(doi, "path/to/save/directory/")
```

## Licence

This project is licensed under the MIT Licence.

## Disclaimer

Web scraping should be done responsibly and in accordance with the terms of service of the target websites. Always check the text and data mining policies of the publisher before scraping and respect the rate limits.
