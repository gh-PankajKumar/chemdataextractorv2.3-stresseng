from extractor import CDEDatabaseExtractor
from allennlp.data.token_indexers import PretrainedBertIndexer
from chemdataextractor.models.stresseng_models import (
    YieldStrength, UltimateTensileStrength, FractureStrength, Ductility, YoungsModulus,
    TableYieldStrength, TableUltimateTensileStrength, TableFractureStrength, TableDuctility, TableYoungsModulus
)
from chemdataextractor.doc.text import Sentence, Citation, Footnote, Caption
from chemdataextractor.nlp.subsentence import NoneSubsentenceExtractor
from chemdataextractor.nlp.allennlpwrapper import _AllenNlpTokenTagger, ProcessedTextTagger, AllenNlpWrapperTagger
from chemdataextractor.data import Package, PACKAGES, find_data

import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)

Sentence.subsentence_extractor = NoneSubsentenceExtractor()

document_dir = os.getenv("DOCUMENT_DIR")
save_root_dir = os.getenv("OUTPUT_DIR")
use_wandb = os.getenv("CDE_USE_WANDB")
wandb_project = "CDE_Extract"
wandb_run_name = os.getenv("WANDB_RUN_NAME")
cache_dir = document_dir + "_cache"
use_mpi = bool(int(os.getenv("USE_MPI"))) if os.getenv("USE_MPI") is not None else True


# Extraction: 
extractor = CDEDatabaseExtractor(
    models=[YieldStrength, FractureStrength, UltimateTensileStrength, Ductility, YoungsModulus],
    #models=[TableYieldStrength, TableUltimateTensileStrength, TableFractureStrength, TableDuctility, TableYoungsModulus],

    save_root_dir=save_root_dir,
    document_args={
        "skip_elements": [Citation, Footnote, Caption],
        "_should_remove_subrecord_if_merged_in": SHOULD_REMOVE_SUBRECORDS_IF_USED
    },
    cache_dir=cache_dir,
    use_mpi=use_mpi,
    use_wandb=use_wandb,
    wandb_project=wandb_project,
    wandb_run_name=wandb_run_name
)
all_start_time = datetime.datetime.now()
extractor.extract(document_dir)

logging.info(f"Extraction as a whole took: {datetime.datetime.now() - all_start_time}")
