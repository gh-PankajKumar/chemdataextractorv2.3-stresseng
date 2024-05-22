# -*- coding: utf-8 -*-
"""
Functionality for saving CDE models.

.. codeauthor:: Taketomo Isazawa <ti250@cam.ac.uk>
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re
import os
import six

from .results import Results
from .mongocoder import MongoCoder

class CDEDatabase(object):
    """
    CDEDatabase allows for easy saving of CDE records and the management of such a database.
    It uses MongoDB as a backend by default but can also save to JSON files.

    Writing to a database::

        db = CDEDatabase()
        mp = MeltingPoint(raw_value='200', raw_units='K',
                          compound=Compound(names=['H2O']))
        db.add([mp])

    Updating a value::

        mp_new = MeltingPoint(raw_value='210', raw_units='K',
                              compound=Compound(names=['H2O', 'water']))
        mp_new._id = mp._id
        db.update([mp_new])

    Deleting values:

        db.delete([ids_to_delete])

    Reading from a database::

        melting_points = db.records(MeltingPoint)
        filter = lambda x: x.value > 100
        for melting_point in melting_points.filter(filter):
            print(melting_point.serialize())

    Getting a single object from a database:

        melting_point = db.record(MeltingPoint, id_)
    """

    def __init__(self, db_name=None, coder=None):
        """
        :param str db_name: The name of the database.
        :param BaseCoder coder: An implementation of the BaseCoder class
            which handles any interactions with the database backend.
            CDE provides coders for MongoDB and JSON by default.
        """
        if db_name is None:
            db_name = 'CDEDatabase'
        self.db_name = db_name
        if not os.path.exists(db_name):
            os.makedirs(db_name)
        self.coder = coder
        if coder is None:
            self.coder = MongoCoder()

    def record(self, record_type, id_):
        """
        A single record of the desired type with the given ID.
        If such an record does not exist, returns None.

        :param Type(BaseModel) record_type: The class for which a single record is desired.
        :param object id_: The unique identifier for the object that is desired.
            This parameter can be of a different type depending on the coder.
        :returns: A single object of the desired type with the given ID.
        :rtype: BaseModel
        """
        return self.create_record(record_type,
                                  self.coder.record(record_type, id_, self.db_name))

    def records(self, record_type):
        """
        All records of the given type in this database

        :param Type(BaseModel) record_type: The class for which the records are desired
        :returns: All objects of the given type in this database
        :rtype: :class:`~chemdataextractor.database.results.Results`
        """
        coder_generator = self.coder.records(record_type, self.db_name)
        def internal_generator():
            for dictionary in coder_generator:
                yield self.create_record(record_type, dictionary)
        return Results(internal_generator(), self)

    def write(self, records):
        """
        Write the given records into the database. Automatically checks whether each
        record is already contained within the database and chooses to either
        add or update the individual record. Automatically assigns IDs to each
        record.

        :param list(BaseModel) records: The records that one wants to write into the database.
        """
        dictionary_forms = self.dictionary_forms(records)
        taken_ids = {}
        for record_type, records_list in six.iteritems(dictionary_forms):
            if record_type not in taken_ids.keys():
                taken_ids[record_type] = []
            update_records = []
            add_records = []
            for record in records_list:
                if self.coder.contains_id(record['_id'], record_type, self.db_name):
                    if record['_id'] not in taken_ids[record_type]:
                        update_records.append(record)
                        taken_ids[record_type].append(record['_id'])
                else:
                    if record['_id'] not in taken_ids[record_type]:
                        add_records.append(record)
                        taken_ids[record_type].append(record['_id'])
            self.coder.add({record_type: add_records}, db_name=self.db_name)
            self.coder.update({record_type: update_records}, db_name=self.db_name)

    def add(self, records):
        """
        Add the given records to the database. Automatically assigns IDs to each record.

        :param list(BaseModel) records: The records that one wants to write into the database.
        """
        dictionary_forms = self.dictionary_forms(records)
        self.coder.add(dictionary_forms, self.db_name)

    def update(self, records):
        """
        Update the given records in the database. Automatically checks whether each
        record is already contained within the database so that model type parameters
        can be updated easily. And chooses to either add or update the individual record.
        Automatically assigns IDs to each record.

        :param list(BaseModel) records: The records that one wants to update in the database.
        """
        self.write(records)

    def delete(self, record_type, ids):
        """
        Delete all records of the given type with the given identifiers from the database.

        :param Type(BaseModel) record_type: The class for which one wishes to delete records.
        :param list(object) ids: A list of identifiers corresponding to the records the user wishes to delete.
        """
        self.coder.delete(record_type, ids, self.db_name)

    def dictionary_forms(self, records):
        """
        Dictionary forms for the records provided. Unique identifiers are automatically provided.
        The dictionary form is similar to the serialized form
        (implemented in :class:`~chemdataextractor.model.base.BaseModel`) in that it is a dictionary
        representation of the object, but has the following differences:

            - The dictionary form replaces each submodel with the unique identifier for the submodel.
            - The dictionary form does not document the types of the submodels.
            - The dictionary form includes the unique identifier for the model, while the serialized form
              does not.

        An example of the difference can be seen in the serialized and dictionary forms of the same record.

        Serialized::

            'MeltingPoint': {'compound': {'Compound': {'names': ['H2O']}},
                             'raw_units': 'K',
                             'raw_value': '200',
                             'units': 'Kelvin^(1.0)',
                             'value': [200.0]}}

        Dictionary form::

            {'_id': 1,
             'compound': 1,
             'raw_units': 'K',
             'raw_value': '200',
             'units': 'Kelvin^(1.0)',
             'value': [200.0]}

        to represent the melting point, and::

            {'_id': 1, 'labels': [], 'names': ['H2O'], 'roles': []}

        to represent the compound.

        :param list(BaseModel) records: A list of models for which the dictionary forms are desired.
        :returns: A dictionary of the form {type of record: list of records of given type in dictionary form}
        :rtype: {Type(BaseModel): list(dict)}
        """
        dictionary_forms = {}
        for record in records:
            dictionary_form = self.dictionary_form(record)
            for element in dictionary_form:
                if element[0] in dictionary_forms.keys():
                    dictionary_forms[element[0]].append(element[1])
                else:
                    dictionary_forms[element[0]] = [element[1]]
        return dictionary_forms

    def dictionary_form(self, record):
        """
        The dictionary form for the records provided. Unique identifiers are automatically provided.
        The dictionary form is similar to the serialized form
        (implemented in :class:`~chemdataextractor.model.base.BaseModel`) in that it is a dictionary
        representation of the object, but has the following differences:

            - The dictionary form replaces each submodel with the unique identifier for the submodel.
            - The dictionary form does not document the types of the submodels.
            - The dictionary form includes the unique identifier for the model, while the serialized form
              does not.

        An example of the difference can be seen in the serialized and dictionary forms of the same record.

        Serialized::

            'MeltingPoint': {'compound': {'Compound': {'names': ['H2O']}},
                             'raw_units': 'K',
                             'raw_value': '200',
                             'units': 'Kelvin^(1.0)',
                             'value': [200.0]}}

        Dictionary form::

            {'_id': 1,
             'compound': 1,
             'raw_units': 'K',
             'raw_value': '200',
             'units': 'Kelvin^(1.0)',
             'value': [200.0]}

        to represent the melting point, and::

            {'_id': 1, 'labels': [], 'names': ['H2O'], 'roles': []}

        to represent the compound.

        :param record: A record for which the dictionary forms is desired.
        :returns: A list of tuples of the form (type of record, record in dictionary form)
        :rtype: list((Type(BaseModel), dict))
        """
        dictionary_forms = []
        dictionary_form = {}
        self.assign_ids(record)
        dictionary_form['_id'] = record._id
        for field_name, field in six.iteritems(record.fields):
            nested_field = self._get_nested(field)
            if self._is_list_type(field) and record[field_name] is not None:
                if hasattr(nested_field, 'model_class'):
                    list_field = []
                    for subrecord in record[field_name]:
                        sub_dictionary_form = self.dictionary_form(subrecord)
                        dictionary_forms.extend(sub_dictionary_form)
                        list_field.append(subrecord._id)
                    if list_field:
                        dictionary_form[field_name] = list_field
                    else:
                        dictionary_form[field_name] = None
                else:
                    dictionary_form[field_name] = field.serialize(record[field_name])
            elif hasattr(nested_field, 'model_class') and record[field_name] is not None:
                subrecord = record[field_name]
                sub_dictionary_form = self.dictionary_form(subrecord)
                dictionary_forms.extend(sub_dictionary_form)
                dictionary_form[field_name] = subrecord._id
            elif record[field_name] is not None:
                dictionary_form[field_name] = field.serialize(record[field_name])
        dictionary_forms.append((type(record), dictionary_form))
        return dictionary_forms

    def assign_ids(self, record):
        """
        Assign unique identifiers to the record and its subrecords.

        :param BaseModel record: The record to which unique identifiers will be added.
        """
        if hasattr(record, '_id') and record._id is not None:
            pass
        else:
            record._id = self.coder.next_id(type(record), self.db_name)
        for field_name, field in six.iteritems(record.fields):
            nested_field = self._get_nested(field)
            if hasattr(nested_field, 'model_class') and record[field_name] is not None:
                if self._is_list_type(field):
                    for el in record[field_name]:
                        self.assign_ids(el)
                else:
                    self.assign_ids(record[field_name])

    def _get_nested(self, field):
        while hasattr(field, 'field'):
            field = field.field
        return field

    def _is_list_type(self, field):
        while hasattr(field, 'field'):
            if not hasattr(field, 'inferrer'):
                return True
            field = field.field
        return False

    def create_record(self, record_type, dictionary_form):
        """
        Create a record of the desired type from its dictionary form.
        The dictionary form is similar to the serialized form
        (implemented in :class:`~chemdataextractor.model.base.BaseModel`) in that it is a dictionary
        representation of the object, but has the following differences:

            - The dictionary form replaces each submodel with the unique identifier for the submodel.
            - The dictionary form does not document the types of the submodels.
            - The dictionary form includes the unique identifier for the model, while the serialized form
              does not.

        An example of the difference can be seen in the serialized and dictionary forms of the same record.

        Serialized::

            'MeltingPoint': {'compound': {'Compound': {'names': ['H2O']}},
                             'raw_units': 'K',
                             'raw_value': '200',
                             'units': 'Kelvin^(1.0)',
                             'value': [200.0]}}

        Dictionary form::

            {'_id': 1,
             'compound': 1,
             'raw_units': 'K',
             'raw_value': '200',
             'units': 'Kelvin^(1.0)',
             'value': [200.0]}

        to represent the melting point, and::

            {'_id': 1, 'labels': [], 'names': ['H2O'], 'roles': []}

        to represent the compound.

        :param Type(BaseModel) record_type: The type of the record that one wants to create
        :param dict dictionary_form: The record in dictionary form.
        """
        model = record_type()
        if dictionary_form is None:
            return None
        for key, value in six.iteritems(dictionary_form):
            if key == '_id':
                model._id = value
            elif hasattr(self._get_nested(model.fields[key]), 'model_class'):
                submodel_class = self._get_nested(model.fields[key]).model_class
                if self._is_list_type(model.fields[key]):
                    submodels = []
                    if value:
                        for sub_id in value:
                            sub_dictionary_form = self.coder.record(submodel_class,
                                                                    sub_id,
                                                                    self.db_name)
                            submodel = self.create_record(submodel_class, sub_dictionary_form)
                            if submodel:
                                submodels.append(submodel)
                    if submodels:
                        model[key] = submodels
                else:
                    sub_dictionary_form = self.coder.record(submodel_class,
                                                            value,
                                                            self.db_name)
                    submodel = self.create_record(submodel_class, sub_dictionary_form)
                    model[key] = submodel
            else:
                model[key] = value
        return model

