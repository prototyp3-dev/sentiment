import unittest

from sklearn.base import BaseEstimator

from dapp import sentiment


class LoadModelTestCase(unittest.TestCase):

    def test_load_model(self):
        model = sentiment.Model()
        model.load_model()
        self.assertIsNotNone(model._model)
        self.assertIsInstance(model._model, BaseEstimator)


class InferenceTestCase(unittest.TestCase):

    def test_data_types(self):
        model = sentiment.Model()
        sent = model.predict('This was a great flight')
        self.assertIsInstance(sent, str)
        self.assertEqual(sent, 'positive')
