import os
import unittest

from readability import Document


SAMPLES = os.path.join(os.path.dirname(__file__), 'samples')


def load_sample(filename):
    """Helper to get the content out of the sample files"""
    f = open(os.path.join(SAMPLES, filename))
    out = f.read()
    f.close()
    return out


class TestArticleOnly(unittest.TestCase):
    """The option to not get back a full html doc should work

    Given a full html document, the call can request just divs of processed
    content. In this way the developer can then wrap the article however they
    want in their own view or application.

    """

    def test_si_sample(self):
        """Using the si sample, load article with only opening body element"""
        sample = load_sample('si-game.sample.html')
        doc = Document(sample)
        doc.parse(["summary"])
        res = doc.summary()
        self.assertEqual('<html><body><h1>Tigers-Roya', res[0:27])

    def test_si_sample_html_partial(self):
        """Using the si sample, make sure we can get the article alone."""
        sample = load_sample('si-game.sample.html')
        doc = Document(sample)
        doc.parse(["summary"], html_partial=True)
        res = doc.summary()
        self.assertEqual('<div><h1>Tigers-R', res[0:17])
