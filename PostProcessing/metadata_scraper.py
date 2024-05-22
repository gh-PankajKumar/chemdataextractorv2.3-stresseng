import json
import requests
import pandas as pd
import csv
from yaspin import yaspin

def fetch_metadata(doi):
    """
    Fetches BibTeX metadata for a given DOI using the dx.doi.org service.

    Args:
        doi (str): The DOI (Digital Object Identifier) of the publication.

    Returns:
        requests.Response or None: The response object containing JSON metadata if successful, None if the request fails.
    """
    url = "http://dx.doi.org/" + doi
    headers = {"accept": "application/citeproc+json"}

    try:
        response = requests.get(url, headers=headers)
        return response
    except requests.RequestException as e:
        print(f"Error fetching metadata for DOI {doi}: {e}")
        return None

def extract_metadata(metadata_json):
    """
    Extracts relevant BibTeX fields from the JSON metadata.

    Args:
        metadata_json (dict): The JSON metadata obtained from dx.doi.org.

    Returns:
        dict: A dictionary containing the extracted BibTeX fields, with "-" as a placeholder for missing values.
    """
    return {
        "DOI": metadata_json.get('DOI', '-'),
        "Title": metadata_json.get('title', '-'),
        "Abstract": metadata_json.get('abstract', '-'),
        "Journal": metadata_json.get('container-title', '-'),
        "Publisher": metadata_json.get('publisher', '-')
    }

"""Example Usage:

Using the `SpringerTableOpen` records as an exmaple, the DOIs of these records are loaded. The DOIs are input into the fetch_metadata function to find the corresponding metadata for each article. These are extracted and written to a separate file for post-processing. 

Te metadata can be extracted from any list of DOI so it can be used during the article retrieval stage. To mimise the number of calls made, fetching the metadata of articles that have a record can help to save time.

"""

def main():
    data_source_name = "SpringerTableOpen"
    input_file_path = f"FinalRecords/{data_source_name}.csv"
    output_file_path = f"{data_source_name}_dois.csv"
    already_processed_dois = []  # Replace with actual list if needed

    # Load DOIs from input CSV
    input_data = pd.read_csv(input_file_path)
    input_data['dois'] = input_data['Article'].str[:7] + '/' + input_data['Article'].str[8:]
    dois_to_process = list(input_data['dois'].unique())
    dois_to_process = [doi for doi in dois_to_process if doi not in already_processed_dois]

    print(f"{len(already_processed_dois)} DOIs already processed")
    print(f"{len(dois_to_process)} DOIs left to process")

    # Extract and save metadata
    with open(output_file_path, "a+", newline='') as output_file:
        fieldnames = ["DOI", "Title", "Abstract", "Journal", "Publisher"]
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)

        with yaspin(text="Starting", side="right") as spinner:
            for index, doi in enumerate(dois_to_process):
                spinner.text = f"{data_source_name}: {index+1}/{len(dois_to_process)} processed"
                metadata_response = fetch_metadata(doi)
                if metadata_response:
                    try:
                        metadata_json = json.loads(metadata_response.text)
                        bibtex_data = extract_metadata(metadata_json)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON for DOI {doi}: {e}")
                        bibtex_data = extract_metadata({})  # Use default values if decoding fails
                else:
                    bibtex_data = extract_metadata({})  # Use default values if fetching fails

                writer.writerow(bibtex_data)

if __name__ == "__main__":
    main()
