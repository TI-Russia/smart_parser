import declarations.models as models
from declarations.management.commands.build_ratings import BuildRatingCommand

from django.test import TestCase


class RatingTestCase(TestCase):

    def test_rating(self):
        models.Person.objects.all().delete()
        models.Section.objects.all().delete()
        models.Source_Document.objects.all().delete()

        src_doc = models.Source_Document(id=1)
        src_doc.office_id = 1
        src_doc.save()

        person_id = 99
        person = models.Person(id=person_id)
        person.save()

        models.Section(id=1,
                       source_document=src_doc,
                       person_name="i1",
                       income_year=2019,
                       person=person).save()
        models.Section(id=2,
                       source_document=src_doc,
                       person_name="i2",
                       income_year=2019,
                       person=person).save()
        models.Section(id=3,
                       source_document=src_doc,
                       person_name="i3",
                       income_year=2019,
                       person=person).save()
        models.Income(section_id=1, size=1, relative=models.Relative.main_declarant_code).save()
        models.Income(section_id=2, size=2, relative=models.Relative.main_declarant_code).save()
        models.Income(section_id=3, size=3, relative=models.Relative.main_declarant_code).save()

        builder = BuildRatingCommand(None, None)
        builder.handle(None, min_members_count=3)

        self.assertEqual(models.Person_Rating_Items.objects.count(), 3)
        rating = list(models.Person_Rating_Items.objects.all())

        self.assertEqual(rating[0].rating_value, 3)
        self.assertEqual(rating[0].person_place, 1)

        self.assertEqual(rating[1].rating_value, 2)
        self.assertEqual(rating[1].person_place, 2)

        self.assertEqual(rating[2].rating_value,  1)
        self.assertEqual(rating[2].person_place, 3)
