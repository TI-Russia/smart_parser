import declarations.models as models
from declarations.ratings import TPersonRatings

from django.core.management import BaseCommand
import heapq
from collections import defaultdict
from django.db import connection

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

    def build_income_sql(self, ):
        return region_stats

    def fill_income_ratings(self):
        query = """
            select p.id, s.income_year, d.office_id,  i.size, i.relative 
            from declarations_section s 
            join declarations_source_document d on d.id=s.source_document_id 
            join declarations_income i on i.section_id=s.id
            join declarations_person p on p.id=s.person_id  
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, income_year, office_id, income_size, relative_code  in cursor:
                if relative_code == models.Relative.main_declarant_code:
                    self.update_rating(
                        (TPersonRatings.MaxDeclarantOfficeIncomeRating, income_year, office_id),
                        (income_size, person_id))

                if relative_code == models.Relative.spouse_code:
                    self.update_rating(
                        (TPersonRatings.MaxSpouseOfficeIncomeRating, income_year, office_id),
                        (income_size, person_id))

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
        self.fill_income_ratings()
        self.save_ratings_to_db()

BuildRatingCommand=Command