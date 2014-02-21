# -*- coding: utf-8 -*-
import unittest
import random

import numpy

from featureforge.flattener import FeatureMappingFlattener


#TODO: Test that matrix output has expected values
#TODO: Test that fit_transform works with one pass of the input


class TestFeatureMappingFlattener(unittest.TestCase):
    def _get_random_tuples(self):
        for _ in xrange(100):
            t = (random.randint(0, 100),
                 random.randint(-3, 3),
                 random.random() * 10 + 5,
                 random.choice([u"pepsi", u"coca", "nafta"]),
                 [random.randint(0, 3) or random.random() for _ in xrange(5)]
                )
            yield t

    def test_fit_empty(self):
        V = FeatureMappingFlattener()
        self.assertRaises(ValueError, V.fit, [])

    def test_fit_ok(self):
        random.seed("sofi needs a ladder")
        X = list(self._get_random_tuples())
        V = FeatureMappingFlattener()
        V.fit(X)
        V = FeatureMappingFlattener()
        V.fit([next(self._get_random_tuples())])  # Test that works for one dict

    def test_fit_bad_values(self):
        random.seed("the alphabet city elite")
        V = FeatureMappingFlattener()
        self.assertRaises(ValueError, V.fit, [tuple()])
        self.assertRaises(ValueError, V.fit, [({},)])
        self.assertRaises(ValueError, V.fit, [([],)])
        self.assertRaises(ValueError, V.fit, [(random,)])
        self.assertRaises(ValueError, V.fit, [([1, u"a"],)])
        self.assertRaises(ValueError, V.fit, [("a",), (1,)])

    def test_transform_empty(self):
        X = list(self._get_random_tuples())
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)
            V.fit(X)
            Z = V.transform([])
            self.assertEqual(Z.shape[0], 0)

    def test_transform_ok(self):
        random.seed("i am the program")
        X = list(self._get_random_tuples())
        random.seed("dream on")
        Y = self._get_random_tuples()
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)
        V.fit(X)
        Z = V.transform(Y)
        n = 100
        m = 3 + 3 + 5  # 3 float, 1 enum, 1 list
        self.assertEqual(Z.shape, (n, m))
        d = next(self._get_random_tuples())
        Z = V.transform([d])  # Test that works for one dict too
        self.assertEqual(Z.shape, (1, m))

    def test_transform_bad_values(self):
        random.seed("king of the streets")
        X = list(self._get_random_tuples())
        d = X.pop()
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)
        V.fit(X)
        dd = tuple(list(d)[:-1])  # Missing value
        self.assertRaises(ValueError, V.transform, [dd])
        dd = d + (10, )  # Extra value
        self.assertRaises(ValueError, V.transform, [dd])
        dd = tuple([u"a string"] + list(d)[1:])  # Changed type
        self.assertRaises(ValueError, V.transform, [dd])

    def test_fit_transform_empty(self):
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)
            self.assertRaises(ValueError, V.fit_transform, [])

    def test_fit_transform_ok(self):
        random.seed("a kiss to build a dream on")
        X = list(self._get_random_tuples())
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)
            Z = V.fit_transform(X)
            n = 100
            m = 3 + 3 + 5  # 3 float, 1 enum, 1 list
            self.assertEqual(Z.shape, (n, m))
            d = next(self._get_random_tuples())
            Z = V.transform([d])  # Test that works for one dict too
            self.assertEqual(Z.shape, (1, m))

    def test_fit_transform_bad_values(self):
        random.seed("king of the streets")
        X = list(self._get_random_tuples())
        d = X.pop()
        for sparse in [True, False]:
            V = FeatureMappingFlattener(sparse=sparse)

            # Typical fit failures
            self.assertRaises(ValueError, V.fit_transform, [tuple()])
            self.assertRaises(ValueError, V.fit_transform, [({},)])
            self.assertRaises(ValueError, V.fit_transform, [([],)])
            self.assertRaises(ValueError, V.fit_transform, [(random,)])
            self.assertRaises(ValueError, V.fit_transform, [([1, u"a"],)])
            self.assertRaises(ValueError, V.fit_transform, [("a",), (1,)])

            # Typical transform failures
            bad = X + [tuple(list(d)[:-1])]  # Missing value
            self.assertRaises(ValueError, V.fit_transform, bad)
            bad = X + [d + (10, )]  # Extra value
            self.assertRaises(ValueError, V.fit_transform, bad)
            bad = X + [tuple([u"a string"] + list(d)[1:])]  # Changed type
            self.assertRaises(ValueError, V.fit_transform, bad)

    def test_fit_transform_equivalent(self):
        random.seed("j0hny guitar")
        X = list(self._get_random_tuples())

        for sparse in [True, False]:
            # fit + transform
            A = FeatureMappingFlattener(sparse=sparse)
            A.fit(X)
            YA = A.transform(X)
            
            # fit_transform
            B = FeatureMappingFlattener(sparse=sparse)
            YB = B.fit_transform(X)

            if sparse:
                self.assertTrue(numpy.array_equal(YA.todense(), YB.todense()))
            else:
                self.assertTrue(numpy.array_equal(YA, YB))
            self.assertEqual(A.indexes, B.indexes)
            self.assertEqual(A.reverse, B.reverse)

    def test_sparse_is_equivalent(self):
        random.seed("jingle dingle")
        X = list(self._get_random_tuples())

        # fit + transform
        A = FeatureMappingFlattener(sparse=True)
        YA = A.fit_transform(X).todense()
        
        # fit_transform
        B = FeatureMappingFlattener(sparse=False)
        YB = B.fit_transform(X)

        self.assertTrue(numpy.array_equal(YA, YB))
