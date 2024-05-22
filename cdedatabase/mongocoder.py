# -*- coding: utf-8 -*-
"""
MongoDB encoder and decoder for CDEDatabase.

.. codeauthor:: Taketomo Isazawa <ti250@cam.ac.uk>
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import six
from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo.errors import BulkWriteError

from .coder import BaseCoder


class MongoCoder(BaseCoder):
    """
    A :class:`~chemdataextractor.database.coder.BaseCoder` implementation for saving to a MongoDB database.
    The database is stored in the default MongoDB database location and the database name is the
    one provided by the :class:`~chemdataextractor.database.database.CDEDatabase`.

    All unique identifiers used in this coder are of type ObjectId.
    """

    def __init__(self, client=None):
        """
        :param MongoClient client: The MongoClient to use.
        """
        self._max_ids = {}
        if client is None:
            self.client = MongoClient()
        else:
            self.client = client

    def _get_collection_name(self, object_type):
        return object_type.__name__

    def record(self, record_type, id_, db_name):
        db = self.client[db_name]
        collection = db[self._get_collection_name(record_type)]
        return collection.find_one({"_id": ObjectId(str(id_))})

    def records(self, record_type, db_name):
        db = self.client[db_name]
        collection = db[self._get_collection_name(record_type)]
        return collection.find()

    def contains_id(self, id_, record_type, db_name):
        db = self.client[db_name]
        collection = db[self._get_collection_name(record_type)]
        contains = collection.find({"_id": ObjectId(str(id_))}, {"_id": 1})\
                             .limit(1).count(with_limit_and_skip=True)
        if contains:
            return True
        return False

    def next_id(self, record_type, db_name):
        return ObjectId()

    def add(self, records, db_name):
        db = self.client[db_name]
        for record_type, records_list in six.iteritems(records):
            if records_list:
                collection = db[self._get_collection_name(record_type)]
                collection.insert_many(records_list)

    def update(self, records, db_name):
        db = self.client[db_name]
        for record_type, records_list in six.iteritems(records):
            if records_list:
                collection = db[self._get_collection_name(record_type)]
                transformed_list = []
                for record in records_list:
                    transformed_list.append([{"_id": record["_id"]},
                                             record])
                for element in transformed_list:
                    collection.update(*element)

    def delete(self, record_type, ids, db_name):
        db = self.client[db_name]
        collection = db[self._get_collection_name(record_type)]
        collection.remove({'_id': {'$in': ids}})

