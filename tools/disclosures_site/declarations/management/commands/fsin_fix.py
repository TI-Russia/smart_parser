import declarations.models as models
from common.logging_wrapper import setup_logging
from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def filter_set(self, logger, section_id, record_set, model_type):
        prev_good_id = None
        ids_to_delete = set()
        left_count = 0
        record_ids = list(i.id for i in record_set)
        for id in record_ids:
            if prev_good_id is None or id < prev_good_id + 200:
                prev_good_id = id
                left_count += 1
            else:
                # резкий прыжок
                ids_to_delete.add(id)
        if len(ids_to_delete) > 0:
            logger.debug("section_id = {} ids = {} left_count = {} ids_to_delete = {}".format(
                section_id, record_ids, left_count, ids_to_delete))
            #assert (left_count * 1 == len(ids_to_delete)) or (left_count * 2 == len(ids_to_delete)) or (left_count * 3 == len(ids_to_delete)) or (left_count * 5 == len(ids_to_delete))
            for id in ids_to_delete:
                logger.debug("delete {} id={}".format(model_type, id))
                model_type.objects.filter(id=id).delete()

    def handle(self, *args, **options):
        logger = setup_logging("fix_fsin")

        for s in models.Section.objects.filter(rubric_id=10):
            self.filter_set(logger, s.id, s.income_set.all().order_by('id'), models.Income)
            self.filter_set(logger, s.id, s.vehicle_set.all().order_by('id'), models.Vehicle)
            self.filter_set(logger, s.id, s.realestate_set.all().order_by('id'), models.RealEstate)