from common.logging_wrapper import setup_logging
from common.russian_fio import TRussianFio
import declarations.models as models

from django.core.management import BaseCommand
import re
import os
import sys


def is_in_rml_alphabet(s):
    word_regexp = "^[ _.АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ-]+$"
    return re.match(word_regexp, s) is not None


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="create_misspell_db.log")
        self.rml_path = None
        self.converter1 = None
        self.converter2 = None
        self.output_folder = None

    def init_options(self, options):
        self.rml_path = options['rml_path']
        if not os.path.exists(self.rml_path):
            raise Exception("folder {} does not exist".format(self.rml_path))
        self.converter1 = os.path.join(self.rml_path, 'Source/morph_dict/scripts/mrd_manager.py')
        if not os.path.exists(self.converter1):
            raise Exception("{} does not exist".format(self.converter1))
        self.converter2 = os.path.join(self.rml_path, 'Bin/MorphGen')
        if not os.path.exists(self.converter2):
            raise Exception("{} does not exist".format(self.converter2))
        self.output_folder = options['output_folder']

    def build_person_names(self):
        self.logger.info("process {} person names".format(models.Section.objects.count()))
        for p in models.Section.objects.only('person_name'):
            yield p.person_name

    def write_list(self, outp):
        used = set()
        for person_name in self.build_person_names():
            fio = TRussianFio(person_name.strip(), from_search_request=False, make_lower=False)
            if fio.is_resolved:
                norm = TRussianFio.convert_to_rml_encoding(fio.get_normalized_person_name())
                if not is_in_rml_alphabet(norm):
                    self.logger.debug("bad alphabet {}".format(person_name.strip()))
                else:
                    if norm not in used:
                        outp.write("{}\n".format(norm))
                        used.add(norm)
                    norm = TRussianFio.convert_to_rml_encoding(fio.get_abridged_normalized_person_name())
                    if norm not in used:
                        outp.write("{}\n".format(norm))
                        used.add(norm)
        self.logger.info("create {} person names in {}".format(len(used), outp.name))
        assert len(used) > 0

    def run_system(self, cmd):
        self.logger.info(cmd)
        exitcode = os.system(cmd)
        assert exitcode == 0

    def build_binaries_with_RML(self, temp_list_path):
        cmd = '{} {} --action create_for_misspell --word-list {} --output-mrd-path {}'.format(
            sys.executable, self.converter1, temp_list_path, os.path.join(self.output_folder, "morphs.mrd")
        )
        self.run_system(cmd)

        cmd = '{} --input {} --output-folder {}'.format(
            self.converter2, os.path.join(self.output_folder, "project.mwz"), self.output_folder)
        self.run_system(cmd)

    def add_arguments(self, parser):
        parser.add_argument(
                '--rml-path',
            dest='rml_path',
            default="/home/sokirko/RML"
        )
        parser.add_argument(
                '--output-folder',
            dest='output_folder',
            default=TRussianFio.fio_misspell_path
        )

    def handle(self, *args, **options):
        self.init_options(options)
        if not os.path.exists(self.output_folder):
            os.mkdir(self.output_folder)
        temp_list = os.path.join(self.output_folder, "fio_list.txt")
        with open(temp_list, "w") as outp:
            self.write_list(outp)
        self.build_binaries_with_RML(temp_list)
        os.unlink(temp_list)
