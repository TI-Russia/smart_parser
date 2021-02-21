from django.test import TestCase
from declarations.russian_fio import TRussianFio


class ResolveFullNameTestCase(TestCase):

    def test_search_section_by_person_name(self):
        def _P(fio):
            return TRussianFio(fio)

        def _F(family_name, first_name, patronymic):
            return TRussianFio("").build_from_parts(family_name, first_name, patronymic)

        self.assertEqual(_P("Мамедов Чингиз Георгиевич"), _F("Мамедов", "Чингиз", "Георгиевич"))
        self.assertEqual(_P("Мамедов Чингиз Георгиевич,"), _F("Мамедов", "Чингиз", "Георгиевич"))
        self.assertEqual(_P("Мамедов Чингиз Георгиевич*"), _F("Мамедов", "Чингиз", "Георгиевич"))
        self.assertEqual(_P("Мамедов Ч.Г."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов ЧГ"), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("МамедовЧГ."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Ч.Г. Мамедов"), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов Ч.Г.-О."), _F("Мамедов", "Ч", "Г-О"))
        self.assertEqual(_P("Халиуллина Гульнур Ахметнагимовна Ахметнагимовна"),
                         _F("Халиуллина", "Гульнур", "Ахметнагимовна"))
        self.assertEqual(_P("Мамедов .Ч. Г."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов Ч..Г."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(TRussianFio("Иванов", from_search_request=True), _F("Иванов", "", ""))

        self.assertEqual(_P("квартира").is_resolved, False)
        self.assertEqual(_P("Иванов").is_resolved, False)
        self.assertEqual(_P("Иванов ..").is_resolved, False)
        self.assertEqual(_P("Мамедов ААА").is_resolved, False)
        self.assertEqual(_P("Мамедов Ч.").is_resolved, False)
        self.assertEqual(_P("Жена Суконцева А.В.").is_resolved, False)
        self.assertEqual(_P("Журавлев А.В. Супруга").is_resolved, False)

        self.assertTrue(_P("Иванов Иван Иванович").is_compatible_to(_P("Иванов И. И.")))
        self.assertTrue(_P("Иванов Иван Иванович").is_compatible_to(_P(" Иванов Иван Иванович ")))
        self.assertTrue(_P("Иванов Иван Иванович").is_compatible_to(_F("Иванов", "И", "")))
        self.assertTrue(_P("Иванов Иван Иванович").is_compatible_to(_F("Иванов", "", "")))

    def test_resolve_person_name_search_request(self):
        def _P(fio):
            return TRussianFio(fio, from_search_request=True)
        def _F(family_name, first_name, patronymic):
            return TRussianFio("").build_from_parts(family_name, first_name, patronymic)

        self.assertEqual(_P("Иванов Иван Иванович"), _F("Иванов", "Иван", "Иванович"))
        self.assertEqual(_P(" Иванов Иван  Иванович "), _F("Иванов", "Иван", "Иванович"))

