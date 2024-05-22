# -*- coding: utf-8 -*-
"""
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re
import shutil
from tempfile import mkstemp
from abc import ABC, abstractmethod
import os
import six


class BaseCoder(ABC):
    """
    Abstract base class for file coders. Implement concrete classes from this to allow CDEDatabases
    to be saved in arbitrary file formats.
    """

    @abstractmethod
    def record(self, record_type, id_, db_name):
        """
        The record method returns a single object of the desired type with the
        given id in the dictionary form as documented in
        :method:`~chemdataextractor.database.database.CDEDatabase.dictionary_form`

        :param Type(:class:`~chemdataextractor.model.base.BaseModel`) record_type:
            The type of record that is desired.
        :param object id_: The unique identifier of the object that is desired.
            This parameter can be of different types depending on the coder.
        :param str db_name: The name of the database.
        :returns: An object of the type desired with the given ID if it exists in the database
            in the form documented in :method:`~chemdataextractor.database.database.CDEDatabase.dictionary_form`
        :rtype: dict or None
        """
        pass

    @abstractmethod
    def records(self, record_type, db_name):
        """
        Get all records of the given type from the database.

        :param Type(:class:`~chemdataextractor.model.base.BaseModel`) record_type:
            The type of record that is desired.
        :param str db_name: The name of the database.
        :returns: An iterator over dictionary representations
            of all objects of the type desired in the database. The representation is documented in
            :method:`~chemdataextractor.database.database.CDEDatabase.dictionary_form`.
        :rtype: iterator(dict)
        """
        pass

    @abstractmethod
    def contains_id(self, id_, record_type, db_name):
        """
        Whether the database contains an object of the given type with the given identifier.

        :param object id_: The unique identifier of the object that is desired.
            This parameter can be of diferent types depending on the coder.
        :param Type(:class:`~chemdataextractor.model.base.BaseModel`) record_type:
            The type of record that is desired.
        :param str db_name: The name of the database.
        :returns: Whether the database contains an object of the given type with the given identifier.
        :rtype: bool
        """
        pass

    @abstractmethod
    def next_id(self, record_type, db_name):
        """
        The next unique identifier for a record of the given type for
        the given database.

        :param Type(:class:`~chemdataextractor.model.base.BaseModel`) record_type:
            The type of record for which a unique identifier is desired.
        :param str db_name: The name of the database.
        :returns: A unique identifier for the object.
        :rtype: object
        """
        pass

    @abstractmethod
    def add(self, records, db_name):
        """
        Add the given records to the given database.

        :param list(dict) records: A dictionary of the records to add, where the keys are the
            types of each record, and the values are a list of records of that type to add,
            with each record being expressed in the form of a dictionary as documented in
            :method:`~chemdataextractor.database.database.CDEDatabase.dictionary_form`.
        :param str db_name: The name of the database.
        """
        pass

    @abstractmethod
    def update(self, records, db_name):
        """
        Update the given records in the database.

        :param list(dict) records: A dictionary of the records to update, where the keys are the
            types of each record, and the values are a list of records of that type to update,
            with each record being expressed in the form of a dictionary as documented in
            :method:`~chemdataextractor.database.database.CDEDatabase.dictionary_form`.
        :param str db_name: The name of the database.
        """
        pass

    @abstractmethod
    def delete(self, record_type, ids, db_name):
        """
        Delete all records of the given type with the given identifiers in the database.

        :param Type(:class:`~chemdataextractor.model.base.BaseModel`) object_type:
            The type of record for which records will be deleted.
        :param list(object) ids: A list of the identifiers for the objects that are to be deleted.
        :param str db_name: The name of the database.
        """
        pass


class PlainTextCoder(BaseCoder):

    file_extension = ''

    def __init__(self):
        self._max_ids = {}
        self._file_names = {}

    def _get_file_name(self, record_type, folder, extension=None, initialise=True):
        if extension is None:
            extension = self.file_extension
        if folder not in self._file_names.keys():
            self._file_names[folder] = {}
        if extension not in self._file_names[folder].keys():
            self._file_names[folder][extension] = {}
        if record_type not in self._file_names[folder].keys():
            file_name = record_type.__name__ + extension
            total_path = os.path.join(folder, file_name)
            if not os.path.isfile(total_path):
                if initialise:
                    self._initialise(total_path, record_type)
            self._file_names[folder][extension][record_type] = total_path
        return self._file_names[folder][extension][record_type]

    def _initialise(self, file_path, record_type):
        pass

    def add(self, records, db_name):
        folder = db_name
        for record_type, records_list in six.iteritems(records):
            id_location = self._get_file_name(record_type, folder,
                                              extension='_ids', initialise=False)
            with open(id_location, 'a+') as f:
                for record in records_list:
                    f.write(str(record['_id']) + '\n')

    def next_id(self, record_type, db_name):
        folder = db_name
        if record_type not in self._max_ids.keys():
            id_location = self._get_file_name(record_type, folder,
                                              extension='_ids', initialise=False)
            max_id = 0
            if os.path.exists(id_location):
                with open(id_location, 'r+') as f:
                    for line in f:
                        integer = int(line)
                        if integer > max_id:
                            max_id = integer
            self._max_ids[record_type] = max_id
        self._max_ids[record_type] += 1
        return self._max_ids[record_type]

    def contains_id(self, id_, record_type, db_name):
        folder = db_name
        id_location = self._get_file_name(record_type, folder,
                                          extension='_ids', initialise=False)
        if os.path.exists(id_location):
            with open(id_location, 'r+') as f:
                for line in f:
                    if id_ == int(line):
                        return True
        return False

    def delete(self, record_type, ids, db_name):
        folder = db_name
        ids = [str(id_) for id_ in ids]
        if ids:
            file_handle, abs_path = mkstemp()
            filename = self._get_file_name(record_type, folder,
                                           extension='_ids', initialise=False)
            with open(filename) as old_file:
                with open(file_handle, 'w') as new_file:
                    for line in old_file:
                        processed_line = line[:-1]
                        if processed_line not in ids:
                            new_file.write(line)
            os.remove(filename)
            shutil.move(abs_path, filename)
