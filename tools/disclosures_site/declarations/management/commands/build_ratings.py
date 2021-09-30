import declarations.models as models
from declarations.ratings import TPersonRatings
from declarations.car_brands import CAR_BRANDS

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

    def add_arguments(self, parser):
        parser.add_argument(
                '--min-members-count',
            dest='min_members_count',
            default=10,
            type=int,
            help='min rating members count'
        )

    def build_car_brand_ratings(self):
        query = """
            select p.id, s.income_year, s.office_id,  v.name 
            from declarations_section s 
            join declarations_vehicle v on v.section_id=s.id
            join declarations_person p on p.id=s.person_id  
        """
        person2car = dict()
        brand_and_office_freq = defaultdict(int)
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id,  income_year, office_id, vehicle_name in cursor:
                for brand_id in CAR_BRANDS.find_brands(vehicle_name):
                    brand_info = CAR_BRANDS.get_brand_info(brand_id)
                    if brand_info.get('luxury', False):
                        person2car[person_id, brand_id] = (income_year, office_id)
                        brand_and_office_freq[(office_id, brand_id)] = brand_and_office_freq[(office_id, brand_id)] + 1

        for (person_id, brand_id), (income_year, office_id) in person2car.items():
            models.Person_Rating_Items(
                person_id=person_id,
                rating_id=TPersonRatings.LuxuryCarRating,
                person_place=1,
                rating_year=income_year,
                rating_value=brand_id,
                competitors_number=brand_and_office_freq[office_id, brand_id],
                office_id=office_id
            ).save()

    def update_rating(self, rating_key, person_result, max_rating_size):
        rating = self.rating_items[rating_key]
        if person_result[0] != 0 and person_result[0] is not None:
            if len(rating) < max_rating_size:
                heapq.heappush(rating, person_result)
            else:
                heapq.heappushpop(rating, person_result)
            self.ratings_person_count[rating_key] += 1

    def prepare_income_ratings(self):
        query = """
            select p.id, s.income_year, s.office_id,  i.size, i.relative 
            from declarations_section s 
            join declarations_income i on i.section_id=s.id
            join declarations_person p on p.id=s.person_id  
        """
        max_rating_size = 3
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, income_year, office_id, income_size, relative_code  in cursor:
                if relative_code == models.Relative.main_declarant_code:
                    self.update_rating(
                        (TPersonRatings.MaxDeclarantOfficeIncomeRating, income_year, office_id),
                        (income_size, person_id),
                        max_rating_size)

                if relative_code == models.Relative.spouse_code:
                    self.update_rating(
                        (TPersonRatings.MaxSpouseOfficeIncomeRating, income_year, office_id),
                        (income_size, person_id),
                        max_rating_size)

    def save_income_ratings_to_db(self):
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
        self.build_car_brand_ratings()

        self.prepare_income_ratings()
        self.save_income_ratings_to_db()

BuildRatingCommand=Command