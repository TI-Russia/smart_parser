from common.primitives import TUrlUtf8Encode
from unittest import TestCase


class TestIDNA(TestCase):

    def test_idna_basic(self):
        def check(s):
            idna = TUrlUtf8Encode.to_idna(s)
            s1 = TUrlUtf8Encode.from_idna(idna)
            self.assertEqual(s, s1)
        check("дом.рф")
        check("дом.рф:443")
        check("дом.рф.txt") # we use it for file names (without path)

    def test_idna_url(self):
        def check(s):
            idna = TUrlUtf8Encode.convert_url_to_idna(s)
            s1 = TUrlUtf8Encode.convert_url_from_idna(idna)
            self.assertEqual(s, s1)
        check("дом.рф/html.html")
        check("http://дом.рф/html.html")
        check("http://дом.рф")

    def test_idna_exception(self):
        bad_idna_string = ".bad_domain"  # error in encoding
        s = TUrlUtf8Encode.to_idna(bad_idna_string)
        self.assertEqual(s, bad_idna_string)

    def test_idna2(self):
        s = "https://xn----7sbabb9bafefpyi3bm2b9a2gra.xn--p1ai/a.href"
        u = TUrlUtf8Encode.convert_url_from_idna(s)
        self.assertEqual("https://батайск-официальный.рф/a.href", u)

