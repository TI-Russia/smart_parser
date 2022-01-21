from office_db.rubrics import TOfficeProps, TOfficeRubrics


from django.test import TestCase, tag


class RubricTestCase(TestCase):

    def check(self, name, top_parent,  rubric, immediate_parent=None):
        pattern = TOfficeProps(name, top_parent=top_parent, immediate_parent=immediate_parent)
        self.assertTrue(pattern.check_rubric(rubric))

    @tag('central', 'front')
    def test_rubrics(self):
        self.check("Бабушкинский районный суд", 1316, TOfficeRubrics.Court)
        self.check("Воронеж - городской округ", 627, TOfficeRubrics.Municipality)
        self.check("УФСИН Брянская область", 482, TOfficeRubrics.Gulag)
        self.check("Совет Федерации", -1, TOfficeRubrics.Legislature)
        self.check("Министерство здравоохранения Кузбасса", 173, TOfficeRubrics.Medicine)
        self.check("Избирательная комиссия Ростовской области", 3, TOfficeRubrics.Election)
        self.check("Прокуратура Удмуртской республики", 8, TOfficeRubrics.Prosecutor)
        self.check("Агентство по гражданской обороне, чрезвычайным ситуациям и пожарной безопасности Красноярского края",
                                     177, TOfficeRubrics.ExecutivePower)
        self.check("Федеральная служба безопасности", 464, TOfficeRubrics.Siloviki)
        self.check("Федеральная служба охраны", 494, TOfficeRubrics.Siloviki)
        self.check("Министерство внутренних дел", 589, TOfficeRubrics.Siloviki)
        self.check("Восточно-Сибирское линейное управление внутренних дел МВД России на транспорте", 4327,
                                     TOfficeRubrics.Siloviki)
        self.check("ФГКОУ ВО Академия управления министерства внутренних дел Российской Федерации", 870,
                                     TOfficeRubrics.Education)
        self.check("Федеральная служба войск национальной гвардии Российской Федерации", 464, TOfficeRubrics.Siloviki)
        self.check("Федеральная служба государственной статистики", 464,TOfficeRubrics.ExecutivePower)
        self.check("Министерство обороны", 589, TOfficeRubrics.Military)
        self.check("Ивановский сельсовет", -1, TOfficeRubrics.Municipality)
        self.check("Федеральная служба по налогам и сборам", -1, TOfficeRubrics.Tax, immediate_parent=470)

