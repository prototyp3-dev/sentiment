import unittest

from sklearn.base import BaseEstimator

from dapp import sentiment


class LoadModelTestCase(unittest.TestCase):

    def test_load_model(self):
        model = sentiment.get_model()
        self.assertIsNotNone(model)
        self.assertIsInstance(model, BaseEstimator)


class InferenceTestCase(unittest.TestCase):

    def test_data_types(self):

        sent = sentiment.classify_sentiment('This was a great flight')

        self.assertIsInstance(sent, str)
        self.assertEqual(sent, 'positive')
