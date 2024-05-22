"""Extractor

Extractor class to generate database records from a corpus of research articles. Based on the extraction code written by Isazawa et al. [1], [2].

Code Author: 
Taketomo Isazawa, ti250@cam.ac.uk

Edited by:
Pankaj Kumar, pk503@cam.ac.uk


[1] Isazawa T, Cole JM. How Beneficial Is Pretraining on a Narrow Domain-Specific Corpus for Information Extraction about Photocatalytic Water Splitting? J Chem Inf Model. 2024 Apr 22;64(8):3205-3212. doi: 10.1021/acs.jcim.4c00063. Epub 2024 Mar 27. PMID: 38544337; PMCID: PMC11040717.
[2] Isazawa, T. (2023). Automatic construction of a photocatalytic materials database using natural language processing [Apollo - University of Cambridge Repository]. https://doi.org/10.17863/CAM.107966
"""

from cdedatabase import CDEDatabase, JSONCoder

from chemdataextractor import Document
from chemdataextractor.doc.text import Citation, Footnote
from chemdataextractor.model.base import ModelList
from chemdataextractor.doc.document_cacher import PlainTextCacher

import wandb
import datetime
import os
from pprint import pprint
import signal

print(wandb.__path__)

AWAITING_DATA_TAG = 111
RETURNING_DATA_TAG = 222


class DatabaseExtractor:
    """Extracts data from documents and manages storage in a cdedatabase.

    This class provides a framework for extracting information from documents using a set of specified models. It handles the configuration of the extraction process, caching, parallel processing (MPI), and logging (Weights & Biases).

    Attributes:
        models (list): A list of model objects used for extraction.
        save_root_dir (str): The root directory where extracted data will be saved.
        cache_dir (str, optional): Directory for caching intermediate results.
        use_mpi (bool, optional): Whether to use MPI for parallel processing (default: True).
        use_wandb (bool, optional): Whether to use Weights & Biases for logging (default: False).
        wandb_project (str, optional): Name of the Weights & Biases project.
        wandb_config (dict, optional): Configuration for Weights & Biases logging.
        wandb_run_name (str, optional): Name of the Weights & Biases run.
        wandb_save_files (list, optional): List of files to save in Weights & Biases.
        document_args (dict, optional): Additional arguments for configuring document objects.
        filter_results (callable, optional): A function to filter extracted records.
        is_valid_document (callable, optional): A function to validate document objects.

    """

    def __init__(
        self,
        models,  
        save_root_dir,  
        cache_dir=None,
        use_mpi=True,
        use_wandb=False,
        wandb_project=None,
        wandb_config=None,
        wandb_run_name=None,
        wandb_save_files=None,
        document_args=None,
        filter_results=None,
        is_valid_document=None,
    ):       

        self.models = models
        self.save_root_dir = save_root_dir

        self.cache_dir = cache_dir
        self.cacher = PlainTextCacher(cache_dir) if cache_dir else None

        self.use_mpi = use_mpi
        if use_mpi:
            from mpi4py import MPI

            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
            self.is_main_thread = self.rank == 0

        self.use_wandb = use_wandb
        self.wandb_project = wandb_project
        self.wandb_config = wandb_config
        self.wandb_run_name = wandb_run_name
        self.wandb_save_files = wandb_save_files or []  

        self.document_args = document_args or {}

        self.filter_results = filter_results
        self.is_valid_document = is_valid_document

    def will_start_extraction(self):
        """Performs pre-extraction setup tasks.

        This method ensures the output directory exists and, if Weights & Biases logging is enabled, creates a new run or logs information from an existing run.

        """

        if not os.path.isdir(self.save_root_dir):
            os.mkdir(self.save_root_dir)

        if self.use_wandb:
            if wandb.run is None:
                self.create_wandb_run()
            else:
                print("EXISTING RUN", wandb.run)

            for file in self.wandb_save_files:
                wandb.save(file)

    def create_wandb_run(self):
        """Initializes a Weights & Biases run.
        Prints the current configuration and then initializes a new Weights & Biases run using the project, configuration, and run name specified in the arguments.

        Returns:
            wandb.Run: The initialized Weights & Biases run object.

        """
        print("WANDB CONFIG:", self.wandb_config)
        return wandb.init(
            project=self.wandb_project,
            config=self.wandb_config,
            name=self.wandb_run_name
        )

    def should_open_file(self, filename):
        """Determines whether a file should be opened for processing.

        Checks if a database file corresponding to the given filename already exists. If it does, the file is skipped.

        Args:
            filename (str): The name of the file to check.

        Returns:
            bool: True if the file should be opened, False otherwise.

        """

        db_name = self.db_name_for_file(filename)
        should_open = not os.path.exists(db_name)
        if not should_open:
            print(f"Skipping {filename} as already exists")
        return should_open

    def should_process_document(self, document):
        """Determines whether a document should be processed.

        If a validation function (`self.is_valid_document`) is provided, it's used to assess the document's validity. Otherwise, all documents are considered valid.

        Args:
            document: The document object to validate.

        Returns:
            bool: True if the document should be processed, False otherwise.

        """
        if self.is_valid_document is None:
            return True

        is_valid = self.is_valid_document(document)

        return is_valid

    def configure_document(self, document):
        """Configures a document object for extraction.

        Sets up the document with the models and additional arguments specified in the extractor's configuration.

        Args:
            document: The document object to configure.

        """

        document.models = self.models

        for key, value in self.document_args.items():
            setattr(document, key, value)

    def postprocess_records(self, records, filename):
        """Postprocesses extracted records and writes them to a database.

        Filters the extracted records (if a filter function is provided) and then writes them to a CDE database.

        Args:
            records (list): The extracted records.
            filename (str): The name of the original file from which the records were extracted.

        """
        if self.filter_results is not None and len(records):
            records = self.filter_results(records)
        db_name = self.db_name_for_file(filename)
        db = CDEDatabase(db_name, coder=JSONCoder())
        db.write(records)

    def db_name_for_file(self, filename):
        """Generates a database name for a given file.

        The database name is based on the filename, without the extension, and is placed within the specified save root directory.

        Args:
            filename (str): The name of the file.

        Returns:
            str: The generated database name.

        """
        only_filename = os.path.split(filename)[-1]
        no_ext_filename = os.path.splitext(only_filename)[0]
        return os.path.join(self.save_root_dir, no_ext_filename)

    def extract_paper(self, document_path):
        """Extracts information from a single document.

        This method performs the following steps:

        1. Checks if the document needs to be processed (based on the existence of a corresponding database file).
        2. Loads the document, optionally hydrating it from the cache.
        3. Configures the document for extraction.
        4. If the document is valid, extracts records using the specified models (with a timeout).
        5. Postprocesses the extracted records and saves them to a database.
        6. If caching is enabled and not used initially, caches the document for future use.
        7. Logs the time taken for the extraction process.

        Args:
            document_path (str): The path to the document file.
        
        """
        doc_start_time = datetime.datetime.now()

        if self.should_open_file(document_path):
            did_use_cache = False
            doc = Document.from_file(document_path)
            self.configure_document(doc)
            if self.cache_dir is not None:
                try:
                    self.cacher.hydrate_document(doc, document_path)
                    did_use_cache = True
                except AttributeError:
                    pass

            document_records = ModelList()
            if self.should_process_document(doc):
                signal.alarm(300)
                try:
                    document_records = doc.records
                except TimeoutError:
                    pass
            else:
                print(f"CANCELLED DOCUMENT {document_path}")

            self.postprocess_records(document_records, document_path)

            if not did_use_cache and self.cache_dir is not None:
                self.cacher.cache_document(doc, document_path, overwrite_cache=True)

        doc_end_time = datetime.datetime.now()

        print(f"{document_path} took:", doc_end_time - doc_start_time)


        def extract(self, document_dir, num_papers=None):

            """Extracts information from documents in a directory.

            This method orchestrates the extraction process, either in single-threaded mode or using MPI for parallel processing. It performs the following:

            1. Calls `will_start_extraction()` to handle pre-extraction setup.
            2. Determines whether to use single-threaded or MPI-based extraction.
            3. If single-threaded, calls `_extract_single_threaded()`.
            4. If MPI is enabled, calls `_extract_mpi()`.

            Args:
                document_dir (str): The directory containing the document files.
                num_papers (int, optional): The maximum number of papers to process (default: None, processes all papers).

            """
        if not self.use_mpi or self.is_main_thread:
            self.will_start_extraction()

        if not self.use_mpi or self.size == 1:
            self._extract_single_threaded(document_dir, num_papers)
        else:
            self._extract_mpi(document_dir, num_papers)





    def _extract_single_threaded(self, document_dir, num_papers=None):

        all_start_time = datetime.datetime.now()

        filenames = [filename for filename in os.listdir(document_dir) if filename[0] != '.' and 'records.txt' not in filename]

        for index, filename in enumerate(filenames):
            if num_papers is not None and index > num_papers:
                break

            print(f"\n\n\nPaper {index + 1}/{len(filenames)}: {filename}")
            if self.use_wandb:
                wandb.log({"num_papers_processed": index})
            full_path = os.path.join(document_dir, filename)

            self.extract_paper(full_path)

        print(f"Extraction as a whole took: {datetime.datetime.now() - all_start_time}")

    def _extract_mpi(self, document_dir, num_papers=None):
        from mpi4py import MPI

        if self.is_main_thread:
            all_start_time = datetime.datetime.now()
            index = 0
            n_finished = 0
            filenames = [filename for filename in os.listdir(document_dir) if filename[0] != '.' and 'records.txt' not in filename]
            num_papers = len(filenames) if num_papers is None else num_papers

            while True:
                status = MPI.Status()
                if index == 0:
                    for i in range(1, self.size):
                        filename = filenames[index]
                        full_path = os.path.join(document_dir, filename)
                        self._send_to_worker(i, full_path)
                        index += 1
                else:
                    _ = self.comm.recv(
                        source=MPI.ANY_SOURCE,
                        tag=MPI.ANY_TAG,
                        status=status
                    )
                    finished_worker_index = status.Get_source()
                    n_finished += 1
                    if self.use_wandb:
                        wandb.log({"num_papers_processed": n_finished})

                    if n_finished == index and index >= num_papers:
                        break
                    elif index < num_papers:
                        print(index, num_papers)
                        filename = filenames[index]
                        full_path = os.path.join(document_dir, filename)
                        self._send_to_worker(finished_worker_index, full_path)
                        index += 1
            for i in range(1, self.size):
                self._exit_worker(i)
            print(f"Extraction as a whole took: {datetime.datetime.now() - all_start_time}")

        else:
            self._start_worker()

    def _send_to_worker(self, worker_index, document_path):
        data = {
            "exit": False,
            "document_path": document_path
        }
        self.comm.send(data, dest=worker_index, tag=AWAITING_DATA_TAG)

    def _exit_worker(self, worker_index):
        data = {"exit": True}
        self.comm.send(data, dest=worker_index, tag=AWAITING_DATA_TAG)

    def _start_worker(self):
        while True:
            data = self.comm.recv(source=0, tag=AWAITING_DATA_TAG)
            if data["exit"]:
                break
            else:
                document_path = data["document_path"]
                try:
                    result = self.extract_paper(document_path)
                    self.comm.send(result, dest=0, tag=RETURNING_DATA_TAG)
                except Exception as e:
                    print(f"EXITED FOR {document_path} DUE TO: {e}")
                    self.comm.send([], dest=0, tag=RETURNING_DATA_TAG)
                    # break

