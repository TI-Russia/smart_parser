from modeltranslation.translator import translator, TranslationOptions
from .models import Office, Vehicle, Section


class OfficeTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Office, OfficeTranslationOptions)


class VehicleTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Vehicle, VehicleTranslationOptions)


class SectionTranslationOptions(TranslationOptions):
    fields = ('person_name', 'position', "department")
translator.register(Section, SectionTranslationOptions)

