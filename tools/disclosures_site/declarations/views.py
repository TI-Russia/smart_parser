from . import models
from django.views import generic
from django.views.generic.edit import FormView
from .documents import ElasticSectionDocument, ElasticPersonDocument, ElasticOfficeDocument, ElasticFileDocument
from declarations.input_json import TIntersectionStatus
from django import forms
import json
import logging
import urllib
from declarations.common import resolve_fullname, resolve_person_name_from_search_request

class SectionView(generic.DetailView):
    model = models.Section
    template_name = 'section/detail.html'


class PersonView(generic.DetailView):
    model = models.Person
    template_name = 'person/detail.html'


class FileView(generic.DetailView):
    model = models.Source_Document
    template_name = 'file/detail.html'


class HomePageView(generic.TemplateView):
    template_name = 'morda/index.html'


class OfficeView(generic.DetailView):
    model = models.Office
    template_name = 'office/detail.html'


class AboutPageView(generic.TemplateView):
    template_name = 'morda/about.html'


class StatisticsView(generic.TemplateView):
    template_name = "statistics/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source_document_count'] = models.Source_Document.objects.all().count()
        context['source_document_only_dlrobot_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.only_dlrobot).count()
        context['source_document_only_human_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.only_human).count()
        context['source_document_both_found_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.both_found).count()

        context['sections_count'] = models.Section.objects.all().count()
        context['sections_count_only_dlrobot'] = models.Section.objects.filter(
            source_document__intersection_status=TIntersectionStatus.only_dlrobot).count()
        context['sections_count_both_found'] = models.Section.objects.filter(
            source_document__intersection_status=TIntersectionStatus.both_found).count()
        context['sections_dedupe_score_greater_0'] = models.Section.objects.filter(
            dedupe_score__gt=0).count()
        context['person_count'] = models.Person.objects.all().count()
        return context


class CommonSearchForm(forms.Form):
    search_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 80}),
        strip=True,
        label="ФИО")
    office_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 80}),
        required=False,
        empty_value="",
        label="Ведомство")


def check_Russiam_name(name1, name2):
    if name1 is None or name2 is None:
        return True
    if len(name1) == 0 or len(name2) == 0:
        return True
    name1 = name1.strip(".").lower()
    name2 = name2.strip(".").lower()
    return name1.startswith(name2) or name2.startswith(name1)


def compare_Russian_fio(search_query, person_name):
    if search_query.find(' ') == -1 and search_query.find('.') == -1:
        return True
    fio1 = resolve_person_name_from_search_request(search_query)
    fio2 = resolve_fullname(person_name)
    if fio1 is None or fio2 is None:
        return True
    if fio1['family_name'].lower() != fio2['family_name'].lower():
        return False
    return     check_Russiam_name(fio1.get('name'), fio2.get('name')) \
           and check_Russiam_name(fio1.get('patronymic'), fio2.get('patronymic'))


class CommonSearchView(FormView, generic.ListView):

    paginate_by = 20
    #paginate_by = 2  #temporal

    form_class = CommonSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "hits_count"):
            context['hits_count'] = self.hits_count
            context['query_fields'] = self.get_query_in_cgi()
        return context

    def get_initial(self):
        return {
            'search_request': self.request.GET.get('search_request'),
            'office_request': self.request.GET.get('office_request')
        }

    def query_elastic_search(self, match_operator="OR"):
        query = self.get_initial().get('search_request')
        if query is None:
            return None
        if len(query) == 0:
            return None
        try:
            if query.startswith('{') and query.endswith('}'):
                query_dict = json.loads(query)
            else:
                query_dict = {
                    #self.elastic_search_document.default_field_name: query,
                    self.elastic_search_document.default_field_name : {
                        'query': query,
                        'operator': match_operator
                    }
                }


                search_results = self.elastic_search_document.search().query('match', **query_dict)
            return search_results
        except Exception:
            return None

    def process_search_results(self, search_results, max_count, person_name_filtering=False):
        object_list = list()
        person_name_query = self.get_initial().get('search_request')
        for x in search_results[:max_count]:
            try:
                if not person_name_filtering or compare_Russian_fio(person_name_query, x.person_name):
                    rec = self.model.objects.get(pk=x.id)
                    object_list.append(rec)
            except Exception as exp:
                logging.getLogger('django').error("cannot get record, id={}".format(x.id))
                raise
        self.hits_count = len(object_list)
        return object_list

    def process_query(self, max_count=100, match_operator="OR"):
        search_results = self.query_elastic_search(match_operator)
        if search_results is None:
            return []
        return self.process_search_results(search_results, max_count)

    def get_query_in_cgi(self):
        query_fields = []
        for (k, v) in self.get_initial().items():
            if v is not None and len(v) > 0:
                query_fields.append((k, v))
        query_fields = urllib.parse.urlencode(query_fields)
        return query_fields


class OfficeSearchView(CommonSearchView):
    model = models.Office
    template_name = 'office/index.html'
    elastic_search_document = ElasticOfficeDocument

    def get_queryset(self):
        if self.get_initial().get('search_request') is None:
            object_list = list(models.Office.objects.all())
            return object_list
        else:
            object_list = self.process_query(500, match_operator="and")
            object_list.sort(key=lambda x: x.source_document_count, reverse=True)
            return object_list


class PersonSearchView(CommonSearchView):
    model = models.Person
    template_name = 'person/index.html'
    elastic_search_document = ElasticPersonDocument

    def get_queryset(self):
        search_results = self.query_elastic_search()
        if search_results is None:
            return []
        object_list = self.process_search_results(search_results, 1000, person_name_filtering=True)

        object_list.sort(key=lambda x: x.section_count, reverse=True)
        return object_list


class SectionSearchView(CommonSearchView):
    model = models.Section
    template_name = 'section/index.html'
    elastic_search_document = ElasticSectionDocument

    def query_elastic_search(self):
        query = self.get_initial().get('search_request')
        if query is None or len(query) == 0:
            return None
        try:
            if query.startswith('{') and query.endswith('}'):
                query_dict = json.loads(query)
                return self.elastic_search_document.search().query('match', **query_dict)
            else:
                query_string = "(person_name: {})".format(query)
                office_query = self.get_initial().get('office_request')
                if office_query is not None and len(office_query) > 0:
                    offices_search = ElasticOfficeDocument.search().query('match', name=office_query)
                    total = offices_search.count()
                    if total == 0:
                        return None
                    offices = list(str(o.id) for o in offices_search[0:total])
                    office_query = " AND (office_id: ({}))".format(" OR ".join(offices))
                    query_string += office_query

                search_results = self.elastic_search_document.search().query('query_string',
                       query=query_string
                     )
                return search_results
        except Exception as e:
            return None

    def get_queryset(self):
        search_results = self.query_elastic_search()
        if search_results is None:
            return []
        object_list = self.process_search_results(search_results, max_count=1000, person_name_filtering=True)
        object_list.sort(key=lambda x: x.person_name)
        return object_list


class FileSearchView(CommonSearchView):
    model = models.Source_Document
    template_name = 'file/index.html'
    elastic_search_document = ElasticFileDocument

    def get_queryset(self):
        # using 300 here to allow search bots to crawl all file links going from one office
        object_list = self.process_query(max_count=300)

        object_list.sort(key=lambda x: x.file_path, reverse=True)
        return object_list
