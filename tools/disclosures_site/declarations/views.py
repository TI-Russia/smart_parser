from . import models
from django.views import generic
from django.views.generic.edit import FormView
from .documents import ElasticSectionDocument, ElasticPersonDocument, ElasticOfficeDocument, ElasticFileDocument
from django import forms
import json
import logging
import urllib
from declarations.common import resolve_fullname, resolve_person_name_from_search_request
from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory
from .rubrics import fill_combo_box_with_rubrics
from datetime import datetime


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
    history = TDisclosuresStatisticsHistory()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for key, value in StatisticsView.history.get_last().metrics.items():
            context[key] = value
            context[key+"_name"] = TDisclosuresStatisticsHistory.get_metric_name(key)
        return context


def fill_combo_box_with_section_years():
    res = [("", "")]
    for year in range(2008, datetime.now().year):
        res.append((str(year), str(year)))
    return res


class CommonSearchForm(forms.Form):
    search_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 80}),
        strip=True,
        required=False,
        empty_value="",
        label="ФИО")
    office_rubric = forms.ChoiceField(
        required=False,
        label="Рубрика",
        choices=fill_combo_box_with_rubrics)
    section_year = forms.ChoiceField(
        required=False,
        label="Год",
        choices=fill_combo_box_with_section_years)
    office_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 28}),
        required=False,
        empty_value="",
        label="Ведомство")
    position_and_department = forms.CharField(
        widget=forms.TextInput(attrs={'size': 28}),
        required=False,
        empty_value="",
        label="Должность или отдел")


def check_Russian_name(name1, name2):
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
    return check_Russian_name(fio1.get('name'), fio2.get('name')) \
           and check_Russian_name(fio1.get('patronymic'), fio2.get('patronymic'))


class CommonSearchView(FormView, generic.ListView):

    paginate_by = 20
    #paginate_by = 2  #temporal

    form_class = CommonSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "hits_count"):
            context['hits_count'] = self.hits_count
            context['query_fields'] = self.get_query_in_cgi()
            old_sort_by, old_order = self.get_sort_order()
            old_cgi_fields = self.get_initial()
            for field in self.elastic_search_document._fields.keys():
                new_cgi_fields = dict(old_cgi_fields.items())
                new_cgi_fields["sort_by"] = field
                if field == old_sort_by and old_order == "asc":
                    new_cgi_fields["order"] = "desc"
                else:
                    new_cgi_fields.pop("order", None)
                context['sort_by_' + field]  = self.get_query_in_cgi(cgi_fields=new_cgi_fields)
            cgi_fields_wo_order = dict(old_cgi_fields.items())
            cgi_fields_wo_order.pop("order", None)
            cgi_fields_wo_order.pop("sort_by", None)
            context['without_order'] = self.get_query_in_cgi(cgi_fields=cgi_fields_wo_order)

        return context

    def get_initial(self):
        return {
            'search_request': self.request.GET.get('search_request'),
            'office_request': self.request.GET.get('office_request'),
            'office_rubric': self.request.GET.get('office_rubric'),
            'section_year': self.request.GET.get('section_year'),
            'position_and_department': self.request.GET.get('position_and_department'),
            'sort_by': self.request.GET.get('sort_by'),
            'order': self.request.GET.get('order'),
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
        person_name_query = self.get_initial().get('search_request')
        if person_name_query is None or len(person_name_query) == 0:
            person_name_filtering = False
        max_count = min(search_results.count(), max_count)
        object_list = list()
        for search_doc in search_results[:max_count]:
            try:
                if not person_name_filtering or compare_Russian_fio(person_name_query, search_doc.person_name):
                    object_list.append(search_doc)
            except Exception as exp:
                logging.getLogger('django').error("cannot get record, id={}".format(search_doc.id))
                raise
        self.hits_count = search_results.count()
        return object_list

    def get_sort_order(self):
        sort_by = self.get_initial().get('sort_by')
        order = self.get_initial().get('order')
        if order is None:
            order = 'asc'
        return sort_by, order

    def process_query(self, max_count=100, match_operator="OR"):
        search_results = self.query_elastic_search(match_operator)
        if search_results is None:
            return []
        return self.process_search_results(search_results, max_count)

    def get_query_in_cgi(self, cgi_fields=None):
        if cgi_fields is None:
            cgi_fields = self.get_initial()
        query_fields = []
        for (k, v) in cgi_fields.items():
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
        try:
            if query is not None and query.startswith('{') and query.endswith('}'):
                query_dict = json.loads(query)
                return self.elastic_search_document.search().query('match', **query_dict)
            else:
                should_items = []
                if query is not None and query != "":
                    should_items.append({"match": {"person_name": query}})

                office_query = self.get_initial().get('office_request')
                if office_query is not None and len(office_query) > 0:
                    offices_search = ElasticOfficeDocument.search().query('match', name=office_query)
                    total = offices_search.count()
                    if total == 0:
                        return None
                    offices = list(o.id for o in offices_search[0:total])
                    should_items.append({"terms": {"office_id": offices}})

                office_rubric = self.get_initial().get('office_rubric')
                if office_rubric is not None and office_rubric != '-1':
                    should_items.append({"terms": {"rubric_id": [int(office_rubric)]}})

                income_year = self.get_initial().get('section_year')
                if income_year is not None and income_year != '':
                    should_items.append({"terms": {"income_year": [int(income_year)]}})

                pos_and_dep = self.get_initial().get('position_and_department')
                if pos_and_dep is not None and pos_and_dep != '':
                    should_items.append({"terms": {"position_and_department": [pos_and_dep]}})

                if len(should_items) == 0:
                    return None

                query_dict = {"query": {"bool": {
                               "should": should_items,
                               "minimum_should_match": len(should_items)
                           }}}
                sort_by, order = self.get_sort_order()
                if sort_by is not None:
                    query_dict['sort'] = [{sort_by: {"order": order}}]

                search = self.elastic_search_document.search()
                search_results = search.update_from_dict(query_dict)
                return search_results
        except Exception as e:
            return None

    def get_queryset(self):
        search_results = self.query_elastic_search()
        if search_results is None:
            return []
        object_list = self.process_search_results(search_results, max_count=1000, person_name_filtering=True)
        if self.get_sort_order()[0] is None:
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
