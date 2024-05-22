"""
Converter from cdedatabase json objects to a single csv file. Requires ChemDataExtractor and cdedatabase to be installed.


"""


import os
import csv
import json
from yaspin import yaspin
from cdedatabase import CDEDatabase, JSONCoder
from chemdataextractor.model.stresseng_models import (
    YieldStrength, UltimateTensileStrength, FractureStrength, Ductility, YoungsModulus,
    TableYieldStrength, TableUltimateTensileStrength, TableFractureStrength, TableDuctility, TableYoungsModulus
)

class CDERecordConverter:
    """Converts CDE database records into CSV format."""

    def __init__(self, origin_dir, destination_dir, save_name, models, field_names_map):
        """
        Args:
            origin_dir (str): Directory containing CDE database files.
            destination_dir (str): Directory to save the CSV file.
            save_name (str): Name of the output CSV file.
            models (list): List of CDE model classes to extract.
            field_names_map (dict): Mapping of record key paths to CSV field names.
        """
        self.origin_dir = origin_dir
        self.destination_dir = destination_dir
        self.save_name = save_name
        self.models = models
        self.field_names_map = field_names_map
        self.coder = JSONCoder()

    def list_article_directories(self):
        """Lists subdirectories (representing article) in the origin cdedatabase directory.
        
         Returns:
            list: A list of subdirectory names.        
        """
        return [d for d in os.listdir(self.origin_dir) if os.path.isdir(os.path.join(self.origin_dir, d))]

    def convert_record_to_dict(self, record):
        """Converts a CDE record object into a dictionary for CSV output.

        Args:
            record: A CDE record object.

        Returns:
            dict: A dictionary mapping CSV column names to record field values.
        
        """
        converted_record = {}
        for keypath, field_name in self.field_names_map.items():
            try:
                field_value = type(record).__name__ if keypath == "__type__" else record[keypath]
            except (TypeError, IndexError):
                field_value = None
            converted_record[field_name] = field_value
        return converted_record

    def get_normalized_records(self, db_name):
        """Retrieves and normalizes records from a CDE database.
        
        
        Args:
            db_name (str): Path to the CDE database file.

        Returns:
            list: A list of normalized CDE record objects.
        
        
        """
        db = CDEDatabase(db_name, coder=self.coder)
        normalized_records = []
        for model in self.models:
            normalized_records.extend(db.records(model))
        return normalized_records

    def export_records_to_csv(self, output_file, records, paper_name=None):
        """Exports records to a CSV file, optionally adding a paper name column.
        
        Args:
            output_file (file object): An open file object in write mode to write the CSV data to.
            records (list): A list of dictionaries representing the records to export.
            paper_name (str, optional): The name of the paper associated with the records (default is None).
        
        """
        headers = list(self.field_names_map.values())
        if paper_name:
            headers.append("Article")

        writer = csv.DictWriter(output_file, fieldnames=headers)
        for record in records:
            if paper_name:
                record["Article"] = paper_name
            writer.writerow(record)

    def convert_all(self):
        """Converts all records from CDE databases to a single CSV file."""
        os.makedirs(self.destination_dir, exist_ok=True)
        output_path = os.path.join(self.destination_dir, self.save_name)

        with open(output_path, "w+", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.field_names_map.values()) + ["Article"])
            writer.writeheader()

            with yaspin(text="Starting", side="right").simpleDots as sp:
                for i, paper_dir in enumerate(self.list_article_directories()):
                    sp.text = f"{i+1}/{len(self.list_article_directories())} processed"
                    db_name = os.path.join(self.origin_dir, paper_dir)
                    records = self.get_normalized_records(db_name)
                    csv_records = [self.convert_record_to_dict(r) for r in records]
                    self.export_records_to_csv(f, csv_records, paper_name=paper_dir)

        print("DONE")

    def csv_to_json(self):
        """Converts the generated CSV file to JSON format.

        Reads the CSV file created by `convert_all()`, converts each row into 
        a dictionary, and writes the resulting list of dictionaries to a JSON file.
        """
        csv_path = os.path.join(self.destination_dir, self.save_name)
        json_file_path = os.path.join(self.destination_dir, f"{os.path.splitext(self.save_name)[0]}.json")

        with open(csv_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            records = list(reader)

        with open(json_file_path, "w") as jsonfile:
            json.dump(records, jsonfile, indent=4)
        
        print(f"JSON data saved to {json_file_path}")


