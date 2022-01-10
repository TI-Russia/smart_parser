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
        self.assertEqual(_P("Гасанова Рена Амрали Кызы"), _F("Гасанова", "Рена", "Амрали Кызы"))

        self.assertEqual(_P("Заман Шамима Хасмат-Уз"), _F("Заман", "Шамима", "Хасмат-Уз"))
        self.assertEqual(_P("А.В.Бойко"), _F("Бойко", "А", "В"))
        self.assertEqual(_P('Дорошенкова М В.'), _F("Дорошенкова", "М", "В"))
        self.assertEqual(_P('Ахмедова З. М.-Т.'), _F("Ахмедова", "З", "М.-Т"))
        self.assertEqual(_P('Пыжик Игорь Григорьев Ич.'), _F("Пыжик", "Игорь", "Григорьевич"))
        self.assertEqual(_P('Изъюрова Вик- Тория Александровна'), _F("Изъюрова", "Виктория", "Александровна"))
        self.assertEqual(_P('Романова Людмила Афанасьевна.'), _F("Романова", "Людмила", "Афанасьевна"))
        self.assertEqual(_P('Строганова Наталья Александров На'), _F("Строганова", "Наталья", "Александровна"))
        self.assertEqual(_P('А.А. Кайгородова'), _F("Кайгородова", "А", "А"))
        self.assertEqual(_P('Туба Давор Симович'), _F("Туба", "Давор", "Симович"))
        self.assertEqual(_P('Шпак Игрь Алесандрович'), _F("Шпак", "Игрь", "Алесандрович"))
        self.assertEqual(_P('Слатвинский Д,А.'), _F("Слатвинский", "Д", "А"))
        self.assertEqual(_P('ШАККУМ Мартин Люцианович'), _F("Шаккум", "Мартин", "Люцианович"))

        # I do know how to solve it
        #self.assertEqual(_P('ЛеКиашвили Д.З.'), _F("Лекиашвили", "Д", "З"))

        self.assertEqual(_P('Зейналов Б.Н.о.'), _F("Зейналов", "Б", "Н.о"))
        self.assertEqual(_P('Никулаева Мария ивановна'), _F("Никулаева", "Мария", "Ивановна"))
        self.assertEqual(_P('Гунбатов Д.Ш.О'), _F("Гунбатов", "Д", "Ш.о"))
        self.assertEqual(_P('Мамедов.Х.Н.'), _F("Мамедов", "Х", "Н"))
        self.assertEqual(_P('Морозова С,А'), _F("Морозова", "С", "А"))
        self.assertEqual(_P('Грудинин И. В..'), _F("Грудинин", "И", "В"))
        self.assertEqual(_P('Рыбаков Анатолий Витальевич, Глава Муниципального Образования'),
                            _F("Рыбаков", "Анатолий", "Витальевич"))

        #correct ocr errors ѐ ->   ё
        self.assertEqual(_P('Кулѐва Ольга Владимировна'), _F("Кулёва", "Ольга", "Владимировна"))

        # use Russian morphology dictionary
        self.assertEqual(_P('Великоречан Ина Е.Е'), _F("Великоречанина", "Е", "Е"))
        self.assertEqual(_P('Махиборо Да Н.М.'), _F("Махиборода", "Н", "М"))
        self.assertEqual(_P('Халыев А.С .'), _F("Халыев", "А", "С"))
        self.assertEqual(_P('Погуляйченко Оле Г Васильевич'), _F("Погуляйченко", "Олег", "Васильевич"))
        self.assertEqual(_P('Воецкая Ирина'), _F("Воецкая", "Ирина", ""))
        self.assertEqual(_P('Друзина Инна'), _F("Друзина", "Инна", ""))
        self.assertEqual(_P('Гладилина Светлана В.'), _F("Гладилина", "Светлана", "В"))
        self.assertEqual(_P('Разогрееванина Николаевна'), _F("Разогреева", "Нина", "Николаевна"))

        self.assertEqual(TRussianFio("Иванов", from_search_request=True), _F("Иванов", "", ""))

        self.assertEqual(_P("квартира").is_resolved, False)
        self.assertEqual(_P("Ф.И.О.").is_resolved, False)
        self.assertEqual(_P("Иванов").is_resolved, False)
        self.assertEqual(_P("Иванов ..").is_resolved, False)
        self.assertEqual(_P("Мамедов ААА").is_resolved, False)
        self.assertEqual(_P("Мамедов Ч.").is_resolved, False)
        self.assertEqual(_P("Жена Суконцева А.В.").is_resolved, False)
        self.assertEqual(_P("Журавлев А.В. Супруга").is_resolved, False)
        self.assertEqual(_P('Долевая 2/3 Доля').is_resolved, False)
        self.assertEqual(_P('Цинцадзе Гис Ионович (Супруг)').is_resolved, False)
        self.assertEqual(_P('Сотрудник Кондратьев Вадим Сергеевич').is_resolved, False)
        self.assertEqual(_P('Сделка Совершалась').is_resolved, False)
        self.assertEqual(_P('Сделка Не Совершалась').is_resolved, False)
        self.assertEqual(_P('Руденко Р.Р. Учитель С Доплатой За Руководство Оу').is_resolved, False)
        self.assertEqual(_P('Дети Тиханова Надежда Евгеньевна').is_resolved, False)
        self.assertEqual(_P('Земельный Участок Дачный').is_resolved, False)
        self.assertEqual(_P('Дачный Земельный Участок').is_resolved, False)
        self.assertEqual(_P('Садовый Земельный Участок').is_resolved, False)
        self.assertEqual(_P('Летний Домик Индивидуальная').is_resolved, False)
        self.assertEqual(_P('Земли Населенных Пунктов').is_resolved, False)
        self.assertEqual(_P('Машина Рено Логан').is_resolved, False)
        self.assertEqual(_P('Жилой дом пай').is_resolved, False)
        self.assertEqual(_P('Овощная Ячейка Дом').is_resolved, False)
        self.assertEqual(_P('Изолированная Часть Жилого').is_resolved, False)
        self.assertEqual(_P('Военная Пенсия').is_resolved, False)
        self.assertEqual(_P('Дмитрий Анатольевич').is_resolved, False)
        self.assertEqual(_P('Горячева Михайловна').is_resolved, False)

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

    def test_normalize_person_name(self):
        def _P(fio):
            return TRussianFio(fio).get_normalized_person_name()

        self.assertEqual(_P("Иванов Иван Иванович"), "Иванов Иван Иванович")
        self.assertEqual(_P("Иванов И. И."),"Иванов И. И.")
        self.assertEqual(_P("Иванов И.И."), "Иванов И. И.")
        self.assertEqual(_P("И.И. Иванов"), "Иванов И. И.")
        self.assertEqual(_P("Иванов И И"), "Иванов И И")
        self.assertEqual(_P("Иванов Иван Иванович    оглы"), "Иванов Иван Иванович Оглы")

    def test_contains(self):
        r = TRussianFioRecognizer()
        self.assertTrue(r.string_contains_Russian_name('Новикова Татьяна Николаевна Жилой Дом (Долевая Собственность ½)'))
        self.assertTrue(r.string_contains_Russian_name('Советник Абрамова Елена Евгеньевна'))
