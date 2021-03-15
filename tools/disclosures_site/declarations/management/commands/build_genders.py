from common.logging_wrapper import setup_logging
from declarations.gender_recognize import TGenderRecognizer
from django.core.management import BaseCommand


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(log_file_name="build_genders.log")

    def handle(self, *args, **options):
        recognizer =  TGenderRecognizer()
        self.logger.info("build_masc_and_fem_names")
        recognizer.build_masc_and_fem_names()

        self.logger.info("build_masc_and_fem_surnames")
        recognizer.build_masc_and_fem_surnames()
        recognizer.build_genders_for_sections(self.logger)


