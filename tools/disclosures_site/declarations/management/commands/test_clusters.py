from django.core.management import BaseCommand
import declarations.models as models
import declarations.models as models
from declarations.russian_fio import resolve_fullname, are_compatible_Russian_fios
import scipy

import sys
from collections import defaultdict


# def build_fio_with_initials(fio):
#     return "{} {} {}".format(
#         fio['family_name'].lower(),
#         fio['name'].lower()[0:1],
#         fio['patronymic'].lower()[0:1],
#     )
#
#
# class TFioCluster:
#     def __init__(self):
#         self.fios = set()
#         self.minimal_fio = None
#         self.sections = set()
#
#     def are_compatible(self, fio):
#         for f in self.fios():
#             if not are_compatible_Russian_fios(f, fio):
#                 return False
#         return True
#
#
#     def add_fio(self, section):
#         fio = resolve_fullname(s.person_name)
#         for f in self.fios:
#         self.fios.add(fio)
#         if self.minimal_fio is None:
#             self.minimal_fio = build_fio_with_initials(fio)
#         self.sections.add(section)
#
#
# class Command(BaseCommand):
#     def __init__(self, *args, **kwargs):
#         super(Command, self).__init__(*args, **kwargs)
#
#     def handle(self, *args, **options):
#         fios = list()
#         for section in models.Section.objects.filter(person_name__istartswith='Иванов'):
#             c = TFioCluster()
#
#             fios.append ((id, fio))
#         fios.sort((key=lambda x: len(x[1])), reverse=True)
#         fio_with_initials = defauldict(list)
#         clusters = defaultdict(list)
#         for section_id, fio in fios:
#             if len(clusters) == 0:
#                 c = TFioCluster()
#                 c.add_fio(fio, section_id)
#                 clusters[c.minimal_fio].append(c)
#             else:
#                 for
#             for clusters.
#
#             if fio is None:
#                 continue
#             fio_with_initials[build_fio_with_initials(fio)].append(fio)
#         for initials, fios in fio_with_initials.items():
#             #https://stackoverflow.com/questions/13079563/how-does-condensed-distance-matrix-work-pdist
#             condensed_distance_matrix = list()
#             for i in range(len(fios)):
#                 for k in range(i+1, len(fios)):
#                     res = are_compatible_Russian_fios(fios[i], fios[k])
#                     condensed_distance_matrix.append(res)
#             scipy.cluster.hierarchy.linkage(condensed_distance_matrix)