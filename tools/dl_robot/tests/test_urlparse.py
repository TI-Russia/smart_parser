from common.primitives import TUrlUtf8Encode, urlsplit_pro, strip_scheme_and_query
from unittest import TestCase


class TestUrlParse(TestCase):

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

        self.assertEqual(TUrlUtf8Encode.convert_url_from_idna('xn--80agabx3af.xn--p1ai'), 'дагони.рф')

    def test_idna_exception(self):
        bad_idna_string = ".bad_domain"  # error in encoding
        s = TUrlUtf8Encode.to_idna(bad_idna_string)
        self.assertEqual(s, bad_idna_string)

    def test_idna_url(self):
        s = "https://xn----7sbabb9bafefpyi3bm2b9a2gra.xn--p1ai/a.href"
        u = TUrlUtf8Encode.convert_url_from_idna(s)
        self.assertEqual("https://батайск-официальный.рф/a.href", u)

    def test_url_split(self):
        self.assertEqual(urlsplit_pro('http://petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('https://petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('ftp://petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('mailto://petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('http://petushki.info:99').netloc, 'petushki.info:99')

        self.assertEqual(urlsplit_pro('https:////petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('petushki.info').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('//petushki.info').netloc, 'petushki.info')

        self.assertEqual(urlsplit_pro('https:////petushki.info/test').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('petushki.info/test').netloc, 'petushki.info')
        self.assertEqual(urlsplit_pro('//petushki.info/test').netloc, 'petushki.info')

        self.assertEqual(urlsplit_pro('дагогни.рф').netloc, 'дагогни.рф')
        self.assertEqual(urlsplit_pro('дагогни.рф/test').netloc, 'дагогни.рф')
        self.assertEqual(urlsplit_pro('http://дагогни.рф/test').netloc, 'дагогни.рф')

        self.assertEqual(urlsplit_pro('https://xn--80agabx3af.xn--p1ai').netloc, 'xn--80agabx3af.xn--p1ai')
        self.assertEqual(urlsplit_pro('xn--80agabx3af.xn--p1ai').netloc, 'xn--80agabx3af.xn--p1ai')
        self.assertEqual(urlsplit_pro('xn--80agabx3af.xn--p1ai/test').netloc, 'xn--80agabx3af.xn--p1ai')

    def test_url_strip(self):
        self.assertEqual(strip_scheme_and_query('https://aot.ru/test'), 'aot.ru/test')
        self.assertEqual(strip_scheme_and_query('https://www.aot.ru/test'), 'aot.ru/test')
        self.assertEqual(strip_scheme_and_query('www.aot.ru/test'), 'aot.ru/test')
        self.assertEqual(strip_scheme_and_query('www.aot.ru/test'), 'aot.ru/test')
        self.assertEqual(strip_scheme_and_query('https://xn--80agabx3af.xn--p1ai/'), 'дагогни.рф')