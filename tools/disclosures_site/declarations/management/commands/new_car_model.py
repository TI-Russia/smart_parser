from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
from django.db import connection
from itertools import groupby
from operator import itemgetter


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.logger = None

    def find_vehicle_buy_year(self):
        query = """
            select person_id, section_id, income_year, v.name 
            from declarations_section s
            left join (
                 select section_id, group_concat(name) as name 
                 from declarations_vehicle 
                 group by section_id
                 ) v on s.id = v.section_id
            where person_id is not null
            order by person_id, income_year
        """
        no_vehicle = "no_vehicle"
        positive_count = 0
        negative_count = 0
        with connection.cursor() as cursor:
            cursor.execute(query)
            for person_id, items in groupby(cursor, itemgetter(0)):
                vehicle_by_year = dict()
                for _, section_id, income_year, vehicle_name in items:
                    if vehicle_name is None:
                        vehicle_name = no_vehicle
                    if income_year in vehicle_by_year:
                        continue
                    vehicle_by_year[income_year] = vehicle_name
                    if vehicle_name != no_vehicle and vehicle_by_year.get(income_year - 1) == no_vehicle:
                        self.logger.debug("person_id = {}, income_year = {} vehicle_name = {}".format(
                            person_id, income_year, vehicle_name
                        ))
                        positive_count += 1
                    elif vehicle_name == no_vehicle and vehicle_by_year.get(income_year - 1) == no_vehicle:
                        negative_count += 1
        self.logger.info("positive count = {}, negative count = {}".format(positive_count, negative_count))

    def handle(self, *args, **options):
        self.options = options
        self.logger = setup_logging(logger_name="new_car_model")
        self.find_vehicle_buy_year()
