# -*- coding: utf-8 -*-
import logging
import array

import numpy
from scipy.sparse import csr_matrix
from schema import Schema, SchemaError, Use


logger = logging.getLogger(__name__)


# TODO: Integrate sparse matrix output code


class SequenceValidator(object):
    def __init__(self, size=None):
        if size is None or isinstance(size, int):
            self.size = size
        else:
            seq = SequenceValidator().validate(size)
            self.size = len(seq)

    def validate(self, x):
        if not (isinstance(x, list) or isinstance(x, tuple) or
                isinstance(x, numpy.ndarray)):
            raise SchemaError("Sequence is not list, tuple or numpy array", [])
        if isinstance(x, numpy.ndarray):
            if x.dtype.kind != "f":
                raise SchemaError("Array dtype must be float, "
                                  "but was {}".format(x.dtype), [])
            x = x.ravel()
        if len(x) == 0:
            raise ValueError("Expecting a non-empty sequence but "
                             "got {}".format(x))
        if self.size is not None and len(x) != self.size:
            raise SchemaError("Expecting sequence length {} but got "
                              "{}".format(self.size, len(x)), [])
        if not isinstance(x, numpy.ndarray):
            for value in x:
                if not isinstance(value, (int, float)):
                    raise SchemaError("Values in sequence are expected to be "
                                      "numeric", [])
            x = numpy.array(x, dtype=float)
        return x

    def __str__(self):
        size = self.size
        if size is None:
            size = ""
        return "SequenceValidator({})".format(size)

    def __repr__(self):
        return str(self)


class TupleValidator(object):
    def __init__(self, types_tuple):
        self.tt = map(Schema, types_tuple)
        self.N = len(self.tt)

    def validate(self, x):
        if not isinstance(x, tuple):
            raise SchemaError("Expecting tuple, got {}".format(type(x)), [])
        if len(x) != self.N:
            raise SchemaError("Expecting a tuple of size {}, but got".format(
                              self.N, len(x)), [])
        return tuple(schema.validate(y) for y, schema in zip(x, self.tt))


class FeatureMappingFlattener(object):
    """
    This class maps feature dicts into numpy arrays.
    Strictly speaking, maps iterables of feature dicts into bidimensional
    numpy arrays such that if the array shape is (N, M) then there were N
    elements in the iterable and M features.

    A feature dict is a python dictionary of the shape:
        {
            "key1": 3,  # Any int
            "key2": u"value",  # Any basestring
            "key3": [1, 5, 9]  # A list of integers
        }
    Keys are meant to be feature names, valid types are str and unicode
    Values are:
        - int/float
        - str/unicode: Are meant to be enumerated types and are one-hot
          encoded.
        - list/tuple/array of integers/floats: A convenience method to pack
          several numbers togheter but otherwise equivalent to giving each
          number in the list a unique key in the dict.

    The flattener needs to be _fitted_ to the available feature dictionaries
    before being able to transform feature dicts to numpy arrays. This is
    because during fitting:
        - The dimension of the output array is calculated.
        - A mapping between dict keys and output array indexes is fixed.
        - A schema of the data for validation is inferred.
        - one-hot encoding values are learned.
        - Validation is applied to the data being fitted.

    Validation checks:
        - Types comply with the above description.
        - key/value pairs don't have different types between different dicts.
        - No key/value pairs are missing (from what is learnt during fitting).
        - No extra key/value pair is present.

    After fitting the instance is ready to transform new feature dicts into
    numpy arrays as long as they comply with the schema inferred during
    fitting.
    """

    def fit(self, X, y=None):
        """X must be a list, sequence or iterable of points,
        but not a single data point.
        """
        return self._wrapcall(self._fit, X)

    def transform(self, X, y=None):
        """X must be a list, sequence or iterable points,
        but not a single data point.
        """
        return self._wrapcall(self._transform, X)

    def fit_transform(self, X, y=None):
        """X must be a list, sequence or iterable points,
        but not a single data point.
        """
        return self._wrapcall(self._fit_transform, X)

    def _wrapcall(self, method, X):
        try:
            return method(X)
        except SchemaError as e:
            raise ValueError(*e.args)

    def _add_column(self, i, value):
        key = (i, value)
        if key not in self.indexes:
            self.indexes[key] = len(self.indexes)
            self.reverse.append(key)

    def _fit_first(self, first):
        # Check for a tuples of numbers, strings or "sequences".
        schema = Schema((int, float, basestring, SequenceValidator()))
        schema.validate(first)
        if not first:
            raise ValueError("Cannot fit with no empty features")

        # Build validation schema using the first data point
        self.indexes = {}  # Tuple index to matrix column mapping
        self.reverse = []  # Matrix column to tuple index mapping
        self.schema = [None] * len(first)
        self.str_tuple_indexes = []
        for i, data in enumerate(first):
            if isinstance(data, (int, float)):
                type_ = Use(float)  # ints and floats are all mapped to float
                self._add_column(i, None)
            elif isinstance(data, basestring):
                type_ = basestring  # One-hot encoded indexes are added last
                self.str_tuple_indexes.append(i)
            else:
                type_ = SequenceValidator(data)
                for j in xrange(type_.size):
                    self._add_column(i, j)
            self.schema[i] = type_
        assert None not in self.schema
        self.schema = tuple(self.schema)
        self.validator = TupleValidator(self.schema)

    def _fit_step(self, datapoint):
        for i in self.str_tuple_indexes:
            self._add_column(i, datapoint[i])

    def _iter_valid(self, X, first=None):
        if first is not None:
            yield self.validator.validate(first)
        for datapoint in X:
            yield self.validator.validate(datapoint)

    def _fit(self, X):
        X = iter(X)
        try:
            first = next(X)
        except (TypeError, StopIteration):
            raise ValueError("Cannot fit with an empty dataset")
        logger.info("Starting flattener.fit")

        # Build basic schema
        self._fit_first(first)

        if self.str_tuple_indexes:  # Is there anything to one-hot encode ?
            # See all datapoints looking for one-hot encodeable feature values
            for datapoint in self._iter_valid(X, first=first):
                self._fit_step(datapoint)

        logger.info("Finished flattener.fit")
        logger.info("Input tuple size %s, output vector size %s" %
                     (len(first), len(self.indexes)))
        return self

    def _transform_step(self, datapoint):
        vector = numpy.zeros(len(self.indexes), dtype=float)
        for i, data in enumerate(datapoint):
            if isinstance(data, float):
                j = self.indexes[(i, None)]
                vector[j] = data
            elif isinstance(data, basestring):
                if (i, data) in self.indexes:
                    j = self.indexes[(i, data)]
                    vector[j] = 1.0
            else:
                j = self.indexes[(i, 0)]
                assert self.indexes[(i, len(data) - 1)] == \
                       j + len(data) - 1
                vector[j:j + len(data)] = data
        return vector

    def _transform(self, X):
        logger.info("Starting flattener.transform")
        matrix = []

        for datapoint in self._iter_valid(X):
            vector = self._transform_step(datapoint)
            matrix.append(vector.reshape((1, -1)))

        if not matrix:
            result = numpy.zeros((0, len(self.indexes)))
        else:
            result = numpy.concatenate(matrix)

        logger.info("Finished flattener.transform")
        logger.info("Matrix has size %sx%s" % result.shape)
        return result

    def _fit_transform(self, X):
        X = iter(X)
        try:
            first = next(X)
        except (TypeError, StopIteration):
            raise ValueError("Cannot fit with an empty dataset")
        logger.info("Starting flattener.fit_transform")

        self._fit_first(first)

        matrix = []
        for datapoint in self._iter_valid(X, first=first):
            self._fit_step(datapoint)
            vector = self._transform_step(datapoint)
            matrix.append(vector.reshape((1, -1)))

        N = len(self.indexes)
        for i, vector in enumerate(matrix):
            if len(vector) == N:
                break
            # This works because one-hot encoded features go at the end
            vector = numpy.array(vector)
            vector.resize((1, N))
            matrix[i] = vector

        if not matrix:
            result = numpy.zeros((0, N))
        else:
            result = numpy.concatenate(matrix)

        logger.info("Finished flattener.fit_transform")
        logger.info("Matrix has size %sx%s" % result.shape)
        return result

    def _sparse_transform_step(self, datapoint):
        for i, data in enumerate(datapoint):
            if isinstance(data, float):
                j = self.indexes[(i, None)]
                yield j, data
            elif isinstance(data, basestring):
                if (i, data) in self.indexes:
                    j = self.indexes[(i, data)]
                    yield j, 1.0
            else:
                j = self.indexes[(i, 0)]
                assert self.indexes[(i, len(data) - 1)] == \
                       j + len(data) - 1
                for k, data_k in enumerate(data):
                    yield j + k, data_k

    def _sparse_transform(self, X):
        logger.info("Starting flattener.transform")

        data = array.array("f")
        indices = array.array("i")
        indptr = array.array("i", [0])

        for datapoint in self._iter_valid(X):
            for i, value in self._sparse_transform_step(datapoint):
                data.append(value)
                indices.append(i)
            indptr.append(len(data))

        if not data:
            result = numpy.zeros((0, len(self.indexes)))
        else:
            result = csr_matrix((data, indices, indptr))

        logger.info("Finished flattener.transform")
        logger.info("Matrix has size %sx%s" % result.shape)
        return result

    def _sparse_fit_transform(self, X):
        X = iter(X)
        try:
            first = next(X)
        except (TypeError, StopIteration):
            raise ValueError("Cannot fit with an empty dataset")
        logger.info("Starting flattener.fit_transform")

        self._fit_first(first)

        data = array.array("d")
        indices = array.array("i")
        indptr = array.array("i", [0])

        for datapoint in self._iter_valid(X, first=first):
            self._fit_step(datapoint)
            for i, value in self._sparse_transform_step(datapoint):
                data.append(value)
                indices.append(i)
            indptr.append(len(data))

        if not data:
            result = numpy.zeros((0, len(self.indexes)))
        else:
            result = csr_matrix((data, indices, indptr), dtype=float)

        logger.info("Finished flattener.fit_transform")
        logger.info("Matrix has size %sx%s" % result.shape)
        return result
