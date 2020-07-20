import declarations.models as models
from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        for p in models.Person.objects.all():
            updated = False
            if p.declarator_person_id is None:
                for s in p.section_set.all():
                    if len(p.person_name) < len(s.person_name):
                        p.person_name = s.person_name
                        print ("set {} to person.id={}".format(p.person_name, p.id))
                        updated = True
                if updated:
                    p.save()
