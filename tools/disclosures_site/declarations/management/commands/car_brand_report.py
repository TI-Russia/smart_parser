import declarations.models as models

from django.core.management import BaseCommand
from declarations.car_brands import CAR_BRANDS


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None
        self.year = None

    def add_arguments(self, parser):
        parser.add_argument(
                '--year',
            dest='year',
            type=int,
            default=2019
        )

    def handle(self, *args, **options):
        self.options = options
        self.year = options['year']
        cnt = 0
        for section in models.Section.objects.filter(income_year=self.year):
            for v in section.vehicle_set.all():
                if v.name is not None and len(v.name) > 1:
                    for b in CAR_BRANDS.find_brands(v.name):
                        name = CAR_BRANDS.get_brand_name(b)
                        vehicle_name = v.name.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                        print("\t".join((vehicle_name, name)))
            #if cnt > 10000:
            #    break
            cnt += 1

