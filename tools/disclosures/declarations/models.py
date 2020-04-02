from django.db import models


class Office(models.Model):
    name = models.TextField(verbose_name='office name')


class Country(models.Model):
    name = models.CharField(max_length=200, verbose_name='название')
    alpha2 = models.CharField(max_length=2, verbose_name='alpha-2 ISO_3166-1', null=True, blank=True, default=None)
    alpha3 = models.CharField(max_length=3, verbose_name='alpha-3 ISO_3166-1', null=True, blank=True, default=None)
    code = models.CharField(max_length=13, verbose_name='code ISO 3166-2', null=True, blank=True, default=None)


class Relative(models.Model):
    name = models.TextField()


class OwnType(models.Model):
    name = models.TextField()


class RealEstateType(models.Model):
    name = models.TextField()


class DocumentFile(models.Model):
    office = models.ForeignKey('declarations.Office', verbose_name="office name", on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=200)
    web_domain = models.CharField(max_length=64)
    file_path = models.CharField(max_length=64)


class Person(models.Model):
    pass


class RealEstate(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    type = models.ForeignKey('declarations.RealEstateType', null=True, on_delete=models.CASCADE)
    country = models.ForeignKey('declarations.Country', null=True, on_delete=models.CASCADE)
    relative = models.ForeignKey('declarations.Relative', null=True, on_delete=models.CASCADE)
    owntype = models.ForeignKey('declarations.OwnType', null=True, on_delete=models.CASCADE)
    square = models.IntegerField(null=True)
    share = models.TextField()


class Vehicle(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    name = models.ForeignKey('declarations.RealEstateType', null=True, on_delete=models.CASCADE)
    relative = models.ForeignKey('declarations.Relative', null=True, on_delete=models.CASCADE)


class Income(models.Model):
    section = models.ForeignKey('declarations.Section', on_delete=models.CASCADE)
    size = models.IntegerField(null=True)
    relative = models.ForeignKey('declarations.Relative', null=True, on_delete=models.CASCADE)


class Section(models.Model):
    document_file = models.ForeignKey('declarations.DocumentFile', null=True, verbose_name="document file", on_delete=models.CASCADE)
    person = models.ForeignKey('declarations.Person', null=True, verbose_name="person id", on_delete=models.CASCADE)
    person_name = models.TextField(verbose_name='person name')
    income_year = models.IntegerField(null=True)
    department = models.TextField(null=True)
    position = models.TextField(null=True)

