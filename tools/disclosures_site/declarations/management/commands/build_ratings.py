import declarations.models as models
from declarations.ratings import TPersonRatings

from django.core.management import BaseCommand
import heapq
from collections import defaultdict


class Command(BaseCommand):
    help = 'all ratings'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

        self.rating_items = defaultdict(list)
        self.ratings_person_count = defaultdict(int)
        self.max_rating_size = 3

    def add_arguments(self, parser):
        parser.add_argument(
                '--min-members-count',
            dest='min_members_count',
            default=10,
            type=int,
            help='min rating members count'
        )

    def update_rating(self, rating_key, person_result):
        rating = self.rating_items[rating_key]
        if person_result[0] != 0 and person_result[0] is not None:
            if len(rating) < self.max_rating_size:
                heapq.heappush(rating, person_result)
            else:
                heapq.heappushpop(rating, person_result)
            self.ratings_person_count[rating_key] += 1

    def fill_ratings(self):
        for person in models.Person.objects.all():
            for s in person.section_set.all():
                self.update_rating(
                    (TPersonRatings.MaxDeclarantOfficeIncomeRating, s.income_year, s.source_document.office_id),
                    (s.get_declarant_income_size(), person.id))

                self.update_rating(
                    (TPersonRatings.MaxSpouseOfficeIncomeRating, s.income_year, s.source_document.office_id),
                    (s.get_spouse_income_size(), person.id))

    def save_ratings_to_db(self):
        for rating_key, rating in self.rating_items.items():
            competitors_number = self.ratings_person_count[rating_key]
            if competitors_number >= self.options['min_members_count']:
                rating.sort(reverse=True)
                (rating_id, year, office_id) = rating_key
                place = 1
                for value, person_id in rating:
                    models.Person_Rating_Items(
                        person_id=person_id,
                        rating_id=rating_id,
                        person_place=place,
                        rating_year=year,
                        rating_value=value,
                        competitors_number=competitors_number,
                        office_id=office_id
                    ).save()
                    place += 1

    def handle(self, *args, **options):
        self.options = options
        models.Person_Rating_Items.objects.all().delete()
        models.Person_Rating.objects.all().delete()
        models.Person_Rating.create_ratings()
        self.fill_ratings()
        self.save_ratings_to_db()

BuildRatingCommand=Command