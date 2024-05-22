# Post Processing

For post-processing, the CDEDatabase objects are converted into a single CSV and JSON file containing all the records. Also, the metadata of each DOI is extracted and added to each record.

## Metadata Scraper

Article metadata are scraped after the records have been extracted to avoid excess calls and scraping metadata for articles that return no records. The same code can be used during article retrieval if front loaded metadata are required. The code in `metadata_scraper.py` can be used to source the metadata to add to each record.

## CDEDatabase Conversion

During extraction, the `cdedatabase` package is used for its efficiency. However, the records are not immediately usable in data-driven pipelines. The `cdedatabase_converter.py` is a simple module that handles the conversion to CSV and JSON formats. Example usage is given below:

```python
field_names_map = {
    "__type__": "Record Type",
    "specifier": "Specifier",
    "compound.names": "Compound",
    "raw_value": "Raw Value",
    "raw_units": "Raw Units",
    "value": "Normalised Value",
    "units": "Normalised Units"
}
origin_dir = CDEDATABASE_RECORD_PATH
destination_dir = OUTPUT_PATH
save_name = OUTPUT_FILENAME 
models = [TableYieldStrength,TableUltimateTensileStrength, TableFractureStrength, TableDuctility, TableYoungsModulus]
x = CDERecordConverter(origin_dir, destination_dir, save_name, models, field_names_map)
x.convert_all()
```
