from django.test import TestCase
from declarations.common import resolve_fullname


class ResolveFullNameTestCase(TestCase):

    def test_search_section_by_person_name(self):
        def _P(fio):
            return resolve_fullname(fio, as_list=True)
        self.assertEqual(_P("Мамедов Чингиз Георгиевич"), ("Мамедов", "Чингиз", "Георгиевич"))
        self.assertEqual(_P("Мамедов Ч.Г."), ("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов ЧГ"), ("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("МамедовЧГ."), ("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Ч.Г. Мамедов"), ("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов Ч.Г.-О."), ("Мамедов", "Ч", "Г-О"))
        self.assertEqual(_P("Халиуллина Гульнур Ахметнагимовна Ахметнагимовна"),
                         ("Халиуллина", "Гульнур", "Ахметнагимовна"))
        self.assertEqual(_P("Мамедов .Ч. Г."), ("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов Ч..Г."), ("Мамедов", "Ч", "Г"))

        self.assertEqual(_P("квартира"), None)
        self.assertEqual(_P("Иванов"), None)
        self.assertEqual(_P("Иванов .."), None)
        self.assertEqual(_P("Мамедов ААА"), None)
        self.assertEqual(_P("Мамедов Ч."), None)
        self.assertEqual(_P("Жена Суконцева А.В."), None)
        self.assertEqual(_P("Журавлев А.В. Супруга"), None)

