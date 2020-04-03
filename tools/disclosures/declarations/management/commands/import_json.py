from django.core.management import BaseCommand
from multiprocessing import Pool
from functools import partial
import .declarations.models  as models
from .dlrobot_and_declarator import TDlrobotAndDeclarator, normalize_whitespace


def init_person_info(section, section_json):
    person_info = section_json.get('person')
    if person_info is None:
        return False
    fio = person_info.get('name', person_info.get('name_raw'))
    if fio is None:
        return False
    section.person_name =  normalize_whitespace(fio.replace('"', ' '))
    section.person_name_ru = section.person_name
    section.position =  person_info.get("role")
    section.position_ru = section.position
    section.department =  person_info.get("department")
    section.department_ru = section.department
    return True


ChildRelative = models.Relative.objects.filter(name="ребенок")
SpouseRelative = models.Relative.objects.filter(name="cупруг(а)")
def get_relative(r):
    name = r.get('relative')
    if name is None or name == "":
        return None
    if name.lower() == "cупруг(а)":
        return SpouseRelative
    if name.lower() == "ребенок":
        return ChildRelative
    assert False
    return None


def create_section_incomes(section, section_json):
    for i in section_json.get('incomes', []):
        relative = get_relative( i.get('relative') )
        size = i.get('size', "null")
        if isinstance(size, float):
            size = int(size)
        if size.isdigit():
            size = int(size)
        i = models.Income(section=section, size=size, relative=relative)
        i.save()

def get_country(s):
    country_str = s.get("country", s.get("country_raw"))
    if country_str is None:
        return None
    try:
        return models.Country.objects.get(name_ru=country_str)
    except:
        print ("unknown country: {}".format(country_str))
        return None

def get_or_create_realty_type(s):
    realty_type_str = s.get("type", s.get("text"))
    if realty_type_str is None:
        return None
    try:
        return models.RealEstateType.objects.get_or_create(name_ru=realty_type_str, name=realty_type_str)
    except Exception as exp:
        print (exp)
        return None

def get_or_create_own_type(s):
    name = s.get("own_type", s.get("own_type_by_column"))
    if name is None:
        return None
    try:
        return models.OwnType.objects.get_or_create(name_ru=name, name=name)
    except Exception as exp:
        print(exp)
        return None


def create_section_real_estates(section, section_json):
    for i in section_json.get('real_estates', []):
        i = models.RealEstate(
                section=section,
                type=get_or_create_realty_type(i),
                country=get_country(i),
                relative=get_relative(i),
                owntype=get_or_create_own_type(i),
                square=i.get("square"),
                share=i.get("share_amount")
                )
        i.save()


def create_section_vehicle(section, section_json):
    for i in section_json.get('vehicles', []):
        i = models.Vehicle(
            section=section,
            name=i.get("text"),
            relative=get_relative(i)
        }
        i.save()


class TDisclosuresDBWrapper:
    @staticmethod
    def register_source_file(self, file_path, office_id, source_file_sha256, web_domain):
        office = models.Office(id=office_id)
        docfile = models.DocumentFile(office=office, sha256=source_file_sha256, file_path=file_path, web_domain=web_domain)
        docfile.save()
        return docfile

    @staticmethod
    def import_one_section(self,  income_year, document_file, section_json):
        section = models.Section(document_file=document_file,
                          income_year=income_year,
                          )
        if not init_person_info(section, section_json):
            return
        create_section_incomes(section, section_json)
        create_section_real_estates(section, section_json)
        create_section_vehicles(section, section_json)


def process_one_file_in_thread(declarator_db, office_id):
    from django.db import connection
    connection.connect()
    declarator_db.import_office((office_id)


class Command(BaseCommand):
    help = 'Import JSONFile or run re-validation for all JSONFiles'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.importer = None
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='only validate',
        )
        parser.add_argument(
            '--process',
            action='store_true',
            dest='process_count',
            default=1,
            help='number of processes for import all'
        )
        parser.add_argument(
            '--dlrobot-human',
            dest='dlrobot_human',
            required=True
        )
        parser.add_argument(
            '--smart-parser-human-json-folder',
            dest='smart_parser_human_json',
            required=True
        )


    def handle(self, *args, **options):
        declarator_db = TDlrobotAndDeclarator(options)
        from django import db
        db.connections.close_all()
        pool = Pool(processes=int(options.get('process_count')))
        self.stdout.write("start importing")
        pool.map(partial(process_one_file_in_thread, declarator_db), (i for i in declarator_db.offices_to_domains.keys()))

