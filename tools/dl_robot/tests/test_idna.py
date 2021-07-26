from common.primitives import TUrlUtf8Encode
from unittest import TestCase


class TestIDNA(TestCase):

    def test_idna1(self):
        bad_idna_string = ".bad_domain"  # error in encoding
        s = TUrlUtf8Encode.to_idna(bad_idna_string)
        self.assertEqual(s, bad_idna_string)

    def test_idna2(self):
        s = "https://xn----7sbabb9bafefpyi3bm2b9a2gra.xn--p1ai/a.href"
        u = TUrlUtf8Encode.from_idna(s)
        self.assertEqual("https://батайск-официальный.рф/a.href", u)
