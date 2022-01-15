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

    def build_binaries_with_RML(self, temp_list_path, output_path):
        RML = "/home/sokirko/RML"
        assert os.path.exists(RML)
        converter1 = os.path.join(RML, 'Source/morph_dict/scripts/mrd_manager.py')
        cmd = '{} {} --action create_for_misspell --word-list {} --output-mrd-path {}'.format(
            sys.executable, converter1, temp_list_path, os.path.join(output_path, "morphs.mrd")
        )
        self.run_system(cmd)

        converter2 = os.path.join(RML, 'Bin/MorphGen')
        cmd = '{} --input {} --output-folder {}'.format(
            converter2, os.path.join(output_path, "project.mwz"), output_path)
        self.run_system(cmd)

    def handle(self, *args, **options):
        output_folder = TRussianFio.fio_misspell_path
        temp_list = os.path.join(output_folder, "fio_list.txt")
        with open(temp_list, "w") as outp:
            self.write_list(outp)
        self.build_binaries_with_RML(temp_list, output_folder)
        os.unlink(temp_list)
