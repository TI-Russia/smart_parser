from django.test import TestCase
from common.russian_fio import TRussianFio, TRussianFioRecognizer


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
        self.assertEqual(_P("Мамедов Ч.Г.-О."), _F("Мамедов", "Ч", "Г.-О"))
        self.assertEqual(_P("Халиуллина Гульнур Ахметнагимовна Ахметнагимовна"),
                         _F("Халиуллина", "Гульнур", "Ахметнагимовна"))
        self.assertEqual(_P("Мамедов .Ч. Г."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Мамедов Ч..Г."), _F("Мамедов", "Ч", "Г"))
        self.assertEqual(_P("Пашин А.Е"), _F("Пашин", "А", "Е"))
        self.assertEqual(_P("Гулиев Гурбангули Арастун Оглы"), _F("Гулиев", "Гурбангули", "Арастун Оглы"))
        self.assertEqual(_P("Заман Шамима Хасмат-Уз"), _F("Заман", "Шамима", "Хасмат-Уз"))
        self.assertEqual(_P("А.В.Бойко"), _F("Бойко", "А", "В"))
        self.assertEqual(_P('Дорошенкова М В.'), _F("Дорошенкова", "М", "В"))
        self.assertEqual(_P('Ахмедова З. М.-Т.'), _F("Ахмедова", "З", "М.-Т"))
        self.assertEqual(_P('Пыжик Игорь Григорьев Ич.'), _F("Пыжик", "Игорь", "Григорьевич"))
        self.assertEqual(_P('Изъюрова Вик- Тория Александровна'), _F("Изъюрова", "Виктория", "Александровна"))
        self.assertEqual(_P('Романова Людмила Афанасьевна.'), _F("Романова", "Людмила", "Афанасьевна"))
        self.assertEqual(_P('Строганова Наталья Александров На'), _F("Строганова", "Наталья", "Александровна"))

        # to do after add morphology
        self.assertEqual(_P('Великоречан Ина Е.Е'), _F("Великоречанина", "Е", "Е"))
        self.assertEqual(_P('Махиборо Да Н.М.'), _F("Махиборода", "Н", "М"))
        self.assertEqual(_P('Халыев А.С .'), _F("Халыев", "А", "С"))
        self.assertEqual(_P('Погуляйченко Оле Г Васильевич'), _F("Погуляйченко", "Олег", "Васильевич"))

        self.assertEqual(TRussianFio("Иванов", from_search_request=True), _F("Иванов", "", ""))

        self.assertEqual(_P("квартира").is_resolved, False)
        self.assertEqual(_P("Иванов").is_resolved, False)
        self.assertEqual(_P("Иванов ..").is_resolved, False)
        self.assertEqual(_P("Мамедов ААА").is_resolved, False)
        self.assertEqual(_P("Мамедов Ч.").is_resolved, False)
        self.assertEqual(_P("Жена Суконцева А.В.").is_resolved, False)
        self.assertEqual(_P("Журавлев А.В. Супруга").is_resolved, False)
        self.assertEqual(_P('Долевая 2/3 Доля').is_resolved, False)
        self.assertEqual(_P('Цинцадзе Гис Ионович (Супруг)').is_resolved, False)
        self.assertEqual(_P('Сотрудник Кондратьев Вадим Сергеевич').is_resolved, False)

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

    def test_contains(self):
        r = TRussianFioRecognizer()
        self.assertTrue(r.string_contains_Russian_name('Новикова Татьяна Николаевна Жилой Дом (Долевая Собственность ½)'))
        self.assertTrue(r.string_contains_Russian_name('Советник Абрамова Елена Евгеньевна'))
