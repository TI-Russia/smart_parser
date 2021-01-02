from . import models
from .documents import ElasticSectionDocument, ElasticPersonDocument, ElasticOfficeDocument, ElasticFileDocument
from declarations.russian_fio import TRussianFio
from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory
from .rubrics import fill_combo_box_with_rubrics
from common.content_types import file_extension_to_content_type
from declarations.apps import DeclarationsConfig

from django.views import generic
from django.views.generic.edit import FormView
from django import forms
from datetime import datetime
from django_elasticsearch_dsl import TextField
from django.http import HttpResponse
import os
import urllib


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


def sitemapView(request):
    sitemap_path = os.path.join(os.path.dirname(__file__), "../disclosures/static/sitemap", "sitemap.txt")
    with open(sitemap_path) as inp:
        return HttpResponse(inp.read())


def sitemapXmlView(request):
    sitemap_path = os.path.join(os.path.dirname(__file__), "../disclosures/static/sitemap.xml")
    with open(sitemap_path) as inp:
        return HttpResponse(inp.read())


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


CACHED_REGIONS = None


def fill_combo_box_with_regions():
    global CACHED_REGIONS
    if CACHED_REGIONS is  None:
        CACHED_REGIONS = list()
        CACHED_REGIONS.append(('', ''))
        for r in models.Region.objects.all():
            name = r.name
            if len(name) > 33:
                name = name[:33]
            CACHED_REGIONS.append((r.id, name))
    return CACHED_REGIONS


def fill_combo_box_with_first_crawl_epochs():
    values = list()
    values.append(('', ''))
    for epoch in StatisticsView.history.history:
        epoch_date = datetime.fromtimestamp(epoch.crawl_epoch)
        dlrobot_birthday = datetime.fromisocalendar(2020, 2, 1)
        if epoch_date < dlrobot_birthday:
            epoch_date = dlrobot_birthday
        values.append((str(epoch.crawl_epoch), epoch_date.strftime("%Y-%m-%d")))
    return values


class CommonSearchForm(forms.Form):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'size': 25}),
        strip=True,
        required=False,
        empty_value="",
        label="Название"
    )
    person_name = forms.CharField(
        widget=forms.TextInput(attrs={'size': 30}),
        strip=True,
        required=False,
        empty_value="",
        label="ФИО"
    )
    web_domains = forms.CharField(
        widget=forms.TextInput(attrs={'size': 20}),
        strip=True,
        required=False,
        empty_value="",
        label="Web domain"
    )
    rubric_id = forms.ChoiceField(
        required=False,
        label="Рубрика",
        choices=fill_combo_box_with_rubrics)
    income_year = forms.ChoiceField(
        required=False,
        label="Год",
        choices=fill_combo_box_with_section_years)
    region_id = forms.ChoiceField(
        required=False,
        label="Регион",
        choices=fill_combo_box_with_regions)
    office_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 25}),
        required=False,
        empty_value="",
        label="Ведомство")
    position_and_department = forms.CharField(
        widget=forms.TextInput(attrs={'size': 26}),
        required=False,
        empty_value="",
        label="Должность или отдел")
    first_crawl_epoch = forms.ChoiceField(
        required=False,
        label="Дата обнаружения",
        choices=fill_combo_box_with_first_crawl_epochs)


def compare_Russian_fio(search_query, person_name):
    if search_query.find(' ') == -1 and search_query.find('.') == -1:
        return True
    fio1 = TRussianFio(search_query, from_search_request=True)
    fio2 = TRussianFio(person_name)
    return fio1.is_resolved and fio2.is_resolved and fio1.is_compatible_to(fio2)


class CommonSearchView(FormView, generic.ListView):

    paginate_by = 20

    form_class = CommonSearchForm

    def get_paginate_by(self, queryset):
        user_page_size = self.request.GET.get('page_size')
        if user_page_size is not None and user_page_size.isdigit():
            return int(user_page_size)
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "hits_count"):
            context['hits_count'] = self.hits_count
            if hasattr(self, "fuzzy_search"):
                context['fuzzy_search'] = self.fuzzy_search
            context['query_fields'] = self.get_query_in_cgi()
            old_sort_by, old_order = self.get_sort_order()
            old_cgi_fields = self.get_initial()
            for field in self.elastic_search_document._fields.keys():
                new_cgi_fields = dict(old_cgi_fields.items())
                new_cgi_fields["sort_by"] = field
                if field == old_sort_by:
                    new_cgi_fields["order"] = "desc" if old_order == "asc" else "asc"
                context['sort_by_' + field] = self.get_query_in_cgi(cgi_fields=new_cgi_fields)

        return context

    def get_initial(self):
        return {
            'person_name': self.request.GET.get('person_name'),
            'office_request': self.request.GET.get('office_request'),
            'rubric_id': self.request.GET.get('rubric_id'),
            'income_year': self.request.GET.get('income_year'),
            'position_and_department': self.request.GET.get('position_and_department'),
            'region_id': self.request.GET.get('region_id'),
            'sort_by': self.request.GET.get('sort_by'),
            'order': self.request.GET.get('order'),
            'name': self.request.GET.get('name'),
            'web_domains': self.request.GET.get('web_domains'),
            'source_document_id': self.request.GET.get('source_document_id'),
            'office_id': self.request.GET.get('office_id'),
            'page_size': self.request.GET.get('page_size'),
            'person_id': self.request.GET.get('person_id'),
            'first_crawl_epoch': self.request.GET.get('first_crawl_epoch'),
            'parent_id': self.request.GET.get('parent_id'),
        }

    def build_person_name_elastic_search_query(self, should_items):
        person_name = self.get_initial().get("person_name")
        if person_name is not None and person_name != '':
            should_items.append({"match": {"person_name": person_name}})
            fio = TRussianFio(person_name, from_search_request=True)
            should_items.append({"match": {"person_name": fio.family_name}})

    def build_office_full_text_elastic_search_query(self, should_items):
        office_query = self.get_initial().get('office_request')
        if office_query is not None and len(office_query) > 0:
            oqd = {"query": {"match": {"name": {"query": office_query, "operator": "and"}}}}
            search_results = ElasticOfficeDocument.search().update_from_dict(oqd)
            total = search_results.count()
            if total == 0:
                return None
            offices = list(o.id for o in search_results[0:total])
            should_items.append({"terms": {"office_id": offices}})

    def query_elastic_search(self):
        def add_should_item(field_name, elastic_search_operaror, field_type, should_items):
            field_value = self.get_initial().get(field_name)
            if field_value is not None and field_value != '':
                should_items.append({elastic_search_operaror: {field_name: field_type(field_value)}})
        try:
            should_items = []
            self.build_person_name_elastic_search_query(should_items)
            add_should_item("name", "match", str, should_items)
            add_should_item("rubric_id", "term", int, should_items)
            add_should_item("region_id", "term", int, should_items)
            add_should_item("income_year", "term", int, should_items)
            add_should_item("position_and_department", "match", str, should_items)
            add_should_item("web_domains", "match", str, should_items)
            add_should_item("source_document_id", "term", int, should_items)
            add_should_item("office_id", "term", int, should_items)
            add_should_item("person_id", "term", int, should_items)
            add_should_item("first_crawl_epoch", "term", int, should_items)
            add_should_item("min_income_year", "term", int, should_items)
            add_should_item("max_income_year", "term", int, should_items)
            add_should_item("section_count", "term", int, should_items)
            add_should_item("parent_id", "term", int, should_items)
            self.build_office_full_text_elastic_search_query(should_items)

            if len(should_items) == 0:
                return None

            query_dict = {"query": {"bool": {
                           "should": should_items,
                           "minimum_should_match": len(should_items)
                       }}}
            sort_by, order = self.get_sort_order()

            if sort_by is not None:
                field_type = type(self.elastic_search_document._fields.get(sort_by))
                if field_type != TextField: # elasticsearch cannot sort by a TextField
                    query_dict['sort'] = [{sort_by: {"order": order}}]

            search = self.elastic_search_document.search()
            search_results = search.update_from_dict(query_dict)
            return search_results
        except Exception as e:
            return None

    def get_person_name_field(self):
        person_name_query = self.get_initial().get('person_name')
        if person_name_query is None or len(person_name_query) == 0:
            return None
        if 'person_name' not in self.elastic_search_document._fields:
            return None
        return person_name_query

    def filter_search_results(self, search_results):
        person_name_query = self.get_person_name_field()
        max_count = min(search_results.count(), self.max_document_count)
        normal_documents = list()
        doubtful_documents = list()
        for search_doc in search_results[:max_count]:
            if person_name_query is None:
                normal_documents.append(search_doc)
            else:
                if compare_Russian_fio(person_name_query, search_doc.person_name):
                    normal_documents.append(search_doc)
                else:
                    doubtful_documents.append(search_doc)
        if len(normal_documents) == 0:
            normal_documents.extend(doubtful_documents)
            self.fuzzy_search = True
        else:
            self.fuzzy_search = False
        self.hits_count = search_results.count()

        return normal_documents

    def get_sort_order(self):
        sort_by = self.get_initial().get('sort_by')
        if sort_by is None:
            if self.default_sort_field is not None:
                sort_by = self.default_sort_field[0]
        order = self.get_initial().get('order')
        if order is None:
            if self.default_sort_field is not None:
                order = self.default_sort_field[1]
            else:
                order = "asc"
        return sort_by, order

    def get_query_in_cgi(self, cgi_fields=None):
        if cgi_fields is None:
            cgi_fields = self.get_initial()
        query_fields = []
        for (k, v) in cgi_fields.items():
            if v is not None and len(v) > 0:
                query_fields.append((k, v))
        query_fields = urllib.parse.urlencode(query_fields)
        return query_fields

    def get_queryset_common(self):
        search_results = self.query_elastic_search()
        if search_results is None:
            return []
        object_list = self.filter_search_results(search_results)
        sort_by, order = self.get_sort_order()
        if sort_by == "person_name":
            object_list.sort(key=lambda x: x.person_name, reverse=(order=="desc"))
        elif sort_by == "name":
            object_list.sort(key=lambda x: x.name, reverse=(order == "desc"))
        elif sort_by == "web_domains":
            object_list.sort(key=lambda x: x.web_domains, reverse=(order == "desc"))
        elif sort_by == "intersection_status":
            object_list.sort(key=lambda x: x.intersection_status, reverse=(order == "desc"))
        return object_list


class OfficeSearchView(CommonSearchView):
    model = models.Office
    template_name = 'office/index.html'
    elastic_search_document = ElasticOfficeDocument
    default_sort_field = None
    max_document_count = 500

    def get_queryset(self):
        if self.get_initial().get('name') is None and self.get_initial().get('parent_id') is None:
            try:
                search = self.elastic_search_document.search()
                query_dict = {
                        "query": { "range": {"source_document_count":{"gte": 1}} },
                        "sort": [{"source_document_count": {"order": "desc"}}]
                }
                search_results = search.update_from_dict(query_dict)
                return self.filter_search_results(search_results)
            except Exception as exp:
                raise exp
        else:
            object_list = self.get_queryset_common()
            return object_list


class PersonSearchView(CommonSearchView):
    model = models.Person
    template_name = 'person/index.html'
    elastic_search_document = ElasticPersonDocument
    default_sort_field = ("section_count", "desc")
    max_document_count = 1000

    def get_queryset(self):
        return self.get_queryset_common()


class SectionSearchView(CommonSearchView):
    model = models.Section
    template_name = 'section/index.html'
    elastic_search_document = ElasticSectionDocument
    default_sort_field = ("person_name", "asc")
    max_document_count = 1000

    def get_queryset(self):
        return self.get_queryset_common()


class FileSearchView(CommonSearchView):
    model = models.Source_Document
    template_name = 'file/index.html'
    elastic_search_document = ElasticFileDocument
    default_sort_field = ("web_domains", "asc")
    max_document_count = 300

    def get_queryset(self):
        return self.get_queryset_common()


def source_doc_getter(request, sha256_and_file_extension):
    sha256, _ = os.path.splitext(sha256_and_file_extension)
    data, file_extension = DeclarationsConfig.SOURCE_DOC_CLIENT.retrieve_file_data_by_sha256(sha256)
    content_type = file_extension_to_content_type(file_extension)
    return HttpResponse(data, content_type=content_type)
