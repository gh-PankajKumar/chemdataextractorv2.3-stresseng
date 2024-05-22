# A Database of Stress-Strain Properties Auto-generated from the Scientific Literature using ChemDataExtractor

This directory contains the code and results for the paper: "A Database of Stress-Strain Properties Auto-generated from the Scientific Literature using ChemDataExtractor". The structure of this directory is given below

```tree
.
|_cdedatabase
    |_ Package for CDEDatabase structure developed by Taketomo Isazawa (ti250) (used for extraction only)
|
|_ chemdataextractor2-2.3.2-stresseng
    |_ Latest release of ChemDataExtractor
    |_ Modifications from ChemDataExtractorStressEng have been integrated and can be found specfically in `model/stresseng_models.py`
|    
|_ Evaluation
    |_ Automatically extracted evaluation records in CDEDatabase format
    |_ Excel spreadsheets that contain the manually curated evaluation dataset and manual labelling that was used for technical validation
|
|_ Extraction
    |_ Contains `extractor.py` which extracts data from documents and manages storage in a cdedatabase
    |_ `extract_stresseng.py` is an example implementation to use the extractor code for mechanical properties
|
|_ Postprocessing
    |_ Postprocessing code converting from CDEDatabase to CSV and Json
    |_ Includes getting metadata from DOIs
|
|_ Scrapers
    |_ Webscrapers for Elsevier and Springer Nature
```
