from modeltranslation.translator import translator, TranslationOptions
from .models import Country, Relative, Office, OwnType, RealEstateType, Vehicle, Section


class CountryTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Country, CountryTranslationOptions)


class RelativeTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Relative, RelativeTranslationOptions)


class OfficeTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Office, OfficeTranslationOptions)


class OwnTypeTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(OwnType, OwnTypeTranslationOptions)


class RealEstateTypeTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(RealEstateType, RealEstateTypeTranslationOptions)


class VehicleTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Vehicle, VehicleTranslationOptions)


class SectionTranslationOptions(TranslationOptions):
    fields = ('person_name', 'position', "department")
translator.register(Section, SectionTranslationOptions)

