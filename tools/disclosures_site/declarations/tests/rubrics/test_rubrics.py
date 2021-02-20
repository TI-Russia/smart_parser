from declarations.rubrics import check_rubric, TOfficeRubrics


from django.test import TestCase


class RubricTestCase(TestCase):

    def test_rubrics(self):
        self.assertTrue(check_rubric("Бабушкинский районный суд", 1316, TOfficeRubrics.Court))
        self.assertTrue(check_rubric("Воронеж - городской округ", 627, TOfficeRubrics.Municipality))
        self.assertTrue(check_rubric("УФСИН Брянская область", 482, TOfficeRubrics.Gulag))
        self.assertTrue(check_rubric("Совет Федерации", -1, TOfficeRubrics.Legislature))
        self.assertTrue(check_rubric("Министерство здравоохранения Кузбасса", 173, TOfficeRubrics.Medicine))
        self.assertTrue(check_rubric("Избирательная комиссия Ростовской области", 3, TOfficeRubrics.Election))
        self.assertTrue(check_rubric("Прокуратура Удмуртской республики", 8, TOfficeRubrics.Prosecutor))
        self.assertTrue(check_rubric("Агентство по гражданской обороне, чрезвычайным ситуациям и пожарной безопасности Красноярского края",
                                     177, TOfficeRubrics.ExecutivePower))
        self.assertTrue(check_rubric("Федеральная служба безопасности", 464, TOfficeRubrics.Siloviki))
        self.assertTrue(check_rubric("Федеральная служба охраны", 494, TOfficeRubrics.Siloviki))
        self.assertTrue(check_rubric("Министерство внутренних дел", 589, TOfficeRubrics.Siloviki))
        self.assertTrue(check_rubric("Восточно-Сибирское линейное управление внутренних дел МВД России на транспорте", 4327,
                                     TOfficeRubrics.Siloviki))
        self.assertTrue(check_rubric("ФГКОУ ВО Академия управления министерства внутренних дел Российской Федерации", 870,
                                     TOfficeRubrics.Education))
        self.assertTrue(check_rubric("Федеральная служба войск национальной гвардии Российской Федерации", 464,
                                     TOfficeRubrics.Siloviki))
        self.assertTrue(check_rubric("Федеральная служба государственной статистики", 464,
                                     TOfficeRubrics.ExecutivePower))
        self.assertTrue(check_rubric("Министерство обороны", 589,
                                     TOfficeRubrics.Military))
        self.assertTrue(check_rubric("Ивановский сельсовет", -1,TOfficeRubrics.Municipality))

