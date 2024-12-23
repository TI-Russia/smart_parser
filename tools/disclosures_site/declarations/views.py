from . import models
from declarations.documents import ElasticSectionDocument, ElasticPersonDocument, ElasticOfficeDocument, ElasticFileDocument
from common.russian_fio import TRussianFio, TRussianFioRecognizer
from disclosures_site.declarations.statistics import TDisclosuresStatisticsHistory
from office_db.rubrics import fill_combo_box_with_rubrics
from common.content_types import file_extension_to_content_type
from declarations.apps import DeclarationsConfig
from declarations.car_brands import CAR_BRANDS
from declarations.gender_recognize import TGender
from dlrobot_human.input_document import TIntersectionStatus
from pylem import MorphanHolder, MorphLanguage
from office_db.region_year_snapshot import TRegionYearStats
from office_db.russia import RUSSIA
from common.primitives import russian_numeral_group
from office_db.rubrics import get_russian_rubric_str
from office_db.year_income import TYearIncome


from django.views import generic
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django import forms
from datetime import datetime
from django_elasticsearch_dsl import TextField
from django.http import HttpResponse
import os
import urllib
from django.shortcuts import render
from django.http import Http404
from django.shortcuts import redirect
import logging
import json
from django.template import loader
import csv


logger = logging.getLogger(__name__)
FIO_MISSPELL_CORRECTOR = MorphanHolder(MorphLanguage.FioDisclosures, TRussianFio.fio_misspell_path)


class SectionView(generic.DetailView):
    model = models.Section
    template_name = 'section/detail.html'


class PersonView(generic.DetailView):
    model = models.Person
    template_name = 'person/detail.html'

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            person_id = self.kwargs.get(self.pk_url_kwarg)
            rec = models.PersonRedirect.objects.filter(id=person_id).first()
            if rec is None:
                raise
            else:
                return redirect('/person/{}'.format(rec.new_person_id))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class FileView(generic.DetailView):
    model = models.Source_Document
    template_name = 'file/detail.html'


class OfficeView(generic.DetailView):
    model = models.Office
    template_name = 'office/detail.html'

    def get_source_doc_html(self):
        num = self.office_stats.source_document_count
        return "{} {}".format(num, russian_numeral_group(num, "документ", "документа", "документов"))

    def section_count_html(self):
        num = self.office_stats.section_count
        s = "{} {}".format(num, russian_numeral_group(num, "декларация", "декларации", "деклараций"))
        return s

    def section_count_by_years_html(self):
        data = self.office_stats.year_snapshots
        html = "<table class=\"section_by_count\"> <tr> "
        years = sorted(data.keys())
        for year in years:
            html += "<th>{}</th>".format(year)
        html += "</tr><tr>"
        for year in years:
            dc = data[year].declarants_count
            html += "<td><a href=\"/section?office_id={}&income_year={}\">{}</a></td>".format(self.office.office_id, year, dc)
        html += "</tr></table>"
        return html

    def median_income_by_years_html(self):
        data = self.office_stats.year_snapshots
        years = sorted(data.keys())
        td = ""
        th = ""
        incomes = list()
        for year in years:
            dc = data[year].median_year_income
            if dc is not None:
                incomes.append(TYearIncome(year, int(dc)))
                th += "<th>{}</th>".format(year)
                td += "<td><a href=\"/section?office_id={}&income_year={}\">{}</a></td>".format(self.office.office_id, year, int(dc))
        html ="<table class=\"section_by_count\"> <tr> " + th + "</tr><tr>" + td + "</tr></table>"

        #return RUSSIA.get_average_nominal_incomes(incomes)

        return html

    def comparison_to_population(self):
        incomes = list()
        for year, value in self.office_stats.year_snapshots.items():
            incomes.append(TYearIncome(year, value.median_year_income))
        incomes.sort()
        return RUSSIA.get_average_nominal_incomes(incomes)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        office_id = self.object.id
        self.office = RUSSIA.get_office(office_id)
        self.office_stats = RUSSIA.calc_data_current.office_stats.get_group_data(office_id)
        region_name = ""
        if self.office.region_id is not None:
            region_name = RUSSIA.regions.get_region_by_id(self.office.region_id).name
        child_examples = list((id, RUSSIA.get_office(id).name) for id in self.office_stats.child_office_examples)
        extra = {
            'source_document_count':  self.office_stats.source_document_count,
            'region_name': region_name,
            'source_document_count_html': self.get_source_doc_html(),
            'child_offices_count': self.office_stats.child_offices_count,
            'section_count_html': self.section_count_html(),
            'section_count_by_years_html': self.section_count_by_years_html(),
            'median_income_by_years_html': self.median_income_by_years_html(),
            'child_office_examples': child_examples,
            'office_in_memory': self.office,
            'parent_office_name': "" if self.office.parent_id is None else RUSSIA.get_office(self.office.parent_id).name,
            "rubric_str": "unknown" if self.office.rubric_id is None else get_russian_rubric_str(self.office.rubric_id),
            "income_comparison": self.comparison_to_population()
        }
        context.update(extra)
        return context

def anyUrlView(request):
    path = request.path
    if path.startswith('/'):
        path = path[1:]
    return render(request, path)


def sitemapView(request):
    sitemap_path = os.path.join(os.path.dirname(__file__), "../disclosures/static/sitemap", "sitemap.txt")
    with open(sitemap_path) as inp:
        return HttpResponse(inp.read(), content_type="text/xml; charset=utf-8")


def sitemapXmlView(request):
    sitemap_path = os.path.join(os.path.dirname(__file__), "../disclosures/static/sitemap.xml")
    with open(sitemap_path) as inp:
        return HttpResponse(inp.read(), content_type="text/xml; charset=utf-8")


def sitemapAuxXmlView(request, sitemapid):
    sitemap_path = os.path.join(os.path.dirname(__file__), "../disclosures/static/", request.path.strip('/'))
    with open(sitemap_path) as inp:
        return HttpResponse(inp.read(), content_type="text/xml; charset=utf-8")


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


def fill_document_intersection_status():
    return [("", "")] + [(s,s) for s in TIntersectionStatus.all_intersection_statuses()]


CACHED_CAR_BRANDS = None


def fill_combo_box_with_car_brands():
    global CACHED_CAR_BRANDS
    if CACHED_CAR_BRANDS is None:
        CACHED_CAR_BRANDS = list()
        CACHED_CAR_BRANDS.append(('', ''))
        for id, brand_info in CAR_BRANDS.brand_dict.items():
            CACHED_CAR_BRANDS.append((id, brand_info['name']))
    return CACHED_CAR_BRANDS


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
        widget=forms.TextInput(attrs={'size': 20}),
        strip=True,
        required=False,
        empty_value="",
        label="Название"
    )
    person_name = forms.CharField(
        widget=forms.TextInput(attrs={'size': 25}),
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
    min_income_year = forms.ChoiceField(
        required=False,
        label="Мин. год",
        choices=fill_combo_box_with_section_years)
    max_income_year = forms.ChoiceField(
        required=False,
        label="Макс. год",
        choices=fill_combo_box_with_section_years)
    intersection_status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=fill_document_intersection_status)
    region_id = forms.ChoiceField(
        required=False,
        label="Регион",
        choices=RUSSIA.sorted_region_list_for_web_interface)
    car_brands = forms.ChoiceField(
        required=False,
        label="Машина",
        choices=fill_combo_box_with_car_brands)
    office_request = forms.CharField(
        widget=forms.TextInput(attrs={'size': 25}),
        required=False,
        empty_value="",
        label="Ведомство")
    position_and_department = forms.CharField(
        widget=forms.TextInput(attrs={'size': 21}),
        required=False,
        empty_value="",
        label="Должность или отдел")
    first_crawl_epoch = forms.ChoiceField(
        required=False,
        label="Дата обнаружения",
        choices=fill_combo_box_with_first_crawl_epochs)
    sha256 = forms.CharField(
        widget=forms.TextInput(attrs={'size': 26}),
        required=False,
        empty_value="",
        label="Sha256")
    match_phrase = forms.BooleanField(label="Фраза", required=False)
    gender = forms.ChoiceField(
        required=False,
        label="Пол",
        choices=TGender.fill_combo_box_with_genders)


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
            if self.hits_count > 0:
                if hasattr(self, "fuzzy_search"):
                    context['fuzzy_search'] = self.fuzzy_search
                if hasattr(self, "skip_rubric_filtering"):
                    context['skip_rubric_filtering'] = self.skip_rubric_filtering

            old_cgi_fields = self.field_params
            if hasattr(self, "person_name_corrections"):
                context['corrections'] = list()
                for person_name in self.person_name_corrections:
                    new_cgi_fields = dict(old_cgi_fields.items())
                    new_cgi_fields["person_name"] = person_name
                    context['corrections'].append((self.get_query_in_cgi(new_cgi_fields), person_name))

            context['query_fields'] = self.get_query_in_cgi(self.field_params)
            old_sort_by, old_order = self.get_sort_order()
            old_cgi_fields = self.field_params
            for field in self.elastic_search_document._fields.keys():
                new_cgi_fields = dict(old_cgi_fields.items())
                new_cgi_fields["sort_by"] = field
                if field == old_sort_by:
                    new_cgi_fields["order"] = "desc" if old_order == "asc" else "asc"
                context['sort_by_' + field] = self.get_query_in_cgi(new_cgi_fields)

        return context

    # get_initial is a predefined Django method, do not rename it, since django uses it for rendering
    def get_initial(self):
        dct =  {
            'person_name': TRussianFioRecognizer.prepare_for_search_index(self.request.GET.get('person_name')),
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
            'sha256': self.request.GET.get('sha256'),
            'car_brands': self.request.GET.get('car_brands'),
            'match_phrase': self.request.GET.get('match_phrase'),
            'gender': self.request.GET.get('gender'),
            'min_income_year': self.request.GET.get('min_income_year'),
            'max_income_year': self.request.GET.get('max_income_year'),
            'intersection_status': self.request.GET.get('intersection_status'),
        }

        if self.request.GET.get('match_phrase'):
            dct['match_operator'] = 'match_phrase'
        else:
            dct['match_operator'] = 'match'

        return dct

    def build_field_params(self):
        self.field_params = self.get_initial()
        self.request_reference = self.request.GET.get('request_ref')

    def log(self, msg):
        if self.request_reference is not None and self.request_reference == "search_frm":
            logger.debug(msg)

    def build_person_name_elastic_search_query(self, should_items):
        person_name = self.field_params.get("person_name")
        if person_name is not None and person_name != '':
            should_items.append({"match": {"person_name": person_name}})
            fio = TRussianFio(person_name, from_search_request=True)
            should_items.append({"match": {"person_name": fio.family_name}})

    def build_office_full_text_elastic_search_query(self, should_items):
        office_query = self.field_params.get('office_request')
        if office_query is not None and len(office_query) > 0:
            if office_query.isdigit():
                should_items.append({"terms": {"office_id": [int(office_query)]}})
            else:
                oqd = {"query": {self.field_params.get('match_operator'): {"name": {"query": office_query, "operator": "and"}}}}
                search_results = ElasticOfficeDocument.search().update_from_dict(oqd)
                total = search_results.count()
                if total == 0:
                    return None
                offices = list(o.id for o in search_results[0:total])
                should_items.append({"terms": {"office_id": offices}})

    def query_elastic_search(self, use_rubric_filtering):
        def add_should_item(field_name, elastic_search_operaror, field_type, should_items):
            field_value = self.field_params.get(field_name)
            if field_value is not None and field_value != '':
                should_items.append({elastic_search_operaror: {field_name: field_type(field_value)}})
        try:
            should_items = []
            self.build_person_name_elastic_search_query(should_items)
            add_should_item("name", "match", str, should_items)
            if use_rubric_filtering:
                add_should_item("rubric_id", "term", int, should_items)
            add_should_item("region_id", "term", int, should_items)
            add_should_item("car_brands", "term", str, should_items)
            add_should_item("income_year", "term", int, should_items)
            add_should_item("position_and_department", self.field_params.get("match_operator"), str, should_items)
            add_should_item("web_domains", "term", str, should_items)
            add_should_item("source_document_id", "term", int, should_items)
            add_should_item("office_id", "term", int, should_items)
            add_should_item("person_id", "term", int, should_items)
            add_should_item("first_crawl_epoch", "term", int, should_items)
            add_should_item("sha256", "term", str, should_items)
            add_should_item("min_income_year", "term", int, should_items)
            add_should_item("max_income_year", "term", int, should_items)
            add_should_item("section_count", "term", int, should_items)
            add_should_item("parent_id", "term", int, should_items)
            add_should_item("gender", "term", int, should_items)
            add_should_item("intersection_status", "term", str, should_items)
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
            self.log("search_query {} {}".format(
                self.elastic_search_document.__name__,
                json.dumps(query_dict, ensure_ascii=False)))
            search = self.elastic_search_document.search()
            search_results = search.update_from_dict(query_dict)
            self.log("search_results_count = {}".format(search_results.count()))
            return search_results
        except Exception as e:
            self.log("exception = {}".format(str(e)))
            return None

    def get_person_name_field(self):
        person_name_query = self.field_params.get('person_name')
        if person_name_query is None or len(person_name_query) == 0:
            return None
        if 'person_name' not in self.elastic_search_document._fields:
            return None
        return person_name_query

    def filter_search_results(self, search_results):
        person_name_query = self.get_person_name_field()
        max_doc_count_to_process = min(search_results.count(), self.max_document_count)
        normal_documents = list()
        doubtful_documents = list()
        for search_doc in search_results[:max_doc_count_to_process]:
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

        if search_results.count() < self.max_document_count:
            self.hits_count = len(normal_documents)
        else:
            # we apply compare_Russian_fio(filter after elasticsearch) only to the first 1000 document and we do not know how
            # many "normal" documents in the main collection, so we return the upper bound (unfiltered document count)
            self.hits_count = search_results.count()

        return normal_documents

    def get_sort_order(self):
        sort_by = self.field_params.get('sort_by')
        if sort_by is None:
            if self.default_sort_field is not None:
                sort_by = self.default_sort_field[0]
        order = self.field_params.get('order')
        if order is None:
            if self.default_sort_field is not None:
                order = self.default_sort_field[1]
            else:
                order = "asc"
        return sort_by, order

    def get_query_in_cgi(self, cgi_fields):
        query_fields = []
        for (k, v) in cgi_fields.items():
            if v is not None and len(v) > 0:
                query_fields.append((k, v))
        query_fields = urllib.parse.urlencode(query_fields)
        return query_fields

    def get_queryset_common(self):
        search_results = self.query_elastic_search(True)
        if search_results is None:
            return []
        object_list = self.filter_search_results(search_results)
        if len(object_list) == 0 and self.field_params.get("rubric_id") is not None and len(self.field_params.get("rubric_id")) > 0:
            self.log("search without rubric, because we get no results with rubric")
            search_results = self.query_elastic_search(False)
            if search_results is None:
                return []
            object_list = self.filter_search_results(search_results)
            self.skip_rubric_filtering = True

        sort_by, order = self.get_sort_order()
        if sort_by == "person_name":
            object_list.sort(key=lambda x: x.person_name, reverse=(order == "desc"))
        elif sort_by == "name":
            object_list.sort(key=lambda x: x.name, reverse=(order == "desc"))
        elif sort_by == "web_domains":
            object_list.sort(key=lambda x: x.web_domains, reverse=(order == "desc"))
        elif sort_by == "intersection_status":
            object_list.sort(key=lambda x: x.intersection_status, reverse=(order == "desc"))
        self.log('serp_size_after_filtering = {}'.format(len(object_list)))
        self.init_person_name_corrections(object_list)
        return object_list

    def init_person_name_corrections(self, object_list):
        if len(object_list) == 0:
            name = self.field_params.get('person_name')
            if name is not None and len(name) > 5:
                fio = TRussianFio(name, from_search_request=False)
                if fio.is_resolved:
                    name = TRussianFio.convert_to_rml_encoding(fio.get_normalized_person_name())
                    corrections = FIO_MISSPELL_CORRECTOR.correct_misspell(name)
                    if len(corrections) > 0:
                        if name != corrections[0]:
                            self.person_name_corrections = list(TRussianFio.convert_from_rml_encoding(c) for c in corrections[:10])
                            self.log('person names corrections count = {}'.format(len(self.person_name_corrections)))


class OfficeSearchView(CommonSearchView):
    model = models.Office
    template_name = 'office/index.html'
    elastic_search_document = ElasticOfficeDocument
    default_sort_field = None
    max_document_count = 500

    def get_queryset(self):
        self.build_field_params()
        if self.field_params.get('name') is None and self.field_params.get('parent_id') is None and  self.field_params.get("rubric_id") is None and \
            self.field_params.get('region_id') is None:
            try:
                search = self.elastic_search_document.search()
                query_dict = {
                        "query": {"range": {"source_document_count": {"gte": 1}}},
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
        self.build_field_params()
        return self.get_queryset_common()


class SectionSearchView(CommonSearchView):
    model = models.Section
    template_name = 'section/index.html'
    elastic_search_document = ElasticSectionDocument
    default_sort_field = ("person_name", "asc")
    max_document_count = 1000

    def get_queryset(self):
        self.build_field_params()
        object_list = self.get_queryset_common()
        return object_list


class FileSearchView(CommonSearchView):
    model = models.Source_Document
    template_name = 'file/index.html'
    elastic_search_document = ElasticFileDocument
    default_sort_field = ("min_income_year", "desc")
    max_document_count = 300

    def get_queryset(self):
        self.build_field_params()
        return self.get_queryset_common()


def source_doc_getter(request, sha256_and_file_extension):
    if DeclarationsConfig.SOURCE_DOC_CLIENT is None:
        raise Http404('source_doc_backend is not initialized')
    sha256, _ = os.path.splitext(sha256_and_file_extension)
    data, file_extension = DeclarationsConfig.SOURCE_DOC_CLIENT.retrieve_file_data_by_sha256(sha256)
    content_type = file_extension_to_content_type(file_extension)
    return HttpResponse(data, content_type=content_type)


def region_report_view(year, request):
    template_name = 'reports/regions{}/index.html'.format(year)
    template = loader.get_template(template_name)
    data = RUSSIA.year_stat.get(year)
    context = {
        'table_headers': list(zip(TRegionYearStats.get_table_headers(), TRegionYearStats.get_table_column_description())),
        'table_rows': list(i.get_table_cells() for i in data.data_by_region.values()),
        'year': year,
        'corr_matrix': data.corr_matrix,
    }
    return HttpResponse(template.render(context, request))


def region_report_csv(year, request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="region_report_view_{}.csv"'.format(year)
    data = RUSSIA.year_stat.get(year)
    writer = csv.writer(response, delimiter="\t")
    writer.writerow([TRegionYearStats.get_table_headers()])
    for i in data.data_by_region.values():
        writer.writerow(i.get_table_cells())
    return response


def region_list_view(request):
    template_name = 'region/index.html'
    template = loader.get_template(template_name)
    context = {
        'region_list': list(RUSSIA.regions.iterate_inner_regions_without_joined())
    }
    return HttpResponse(template.render(context, request))


def region_detail_view(request, region_id):
    template_name = 'region/detail.html'
    template = loader.get_template(template_name)
    context = {
        'region': RUSSIA.regions.get_region_by_id(region_id)
    }
    return HttpResponse(template.render(context, request))


def office_report_2020_view(request):
    template_name = 'reports/offices2020/index.html'
    template = loader.get_template(template_name)
    data = RUSSIA.calc_data_2020.rubric_stats
    context = {
        'table_headers': list(zip(data.get_table_headers(), data.get_table_column_description())),
        'table_rows': list(data.get_all_office_report_rows(RUSSIA)),
    }
    return HttpResponse(template.render(context, request))


def write_csv(csv_file_path, request):
    response = HttpResponse(content_type='text/csv')
    file_name = os.path.basename(csv_file_path)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(file_name)
    with open(csv_file_path) as inp:
        response.write(inp.read())
    return response


    template_name = 'reports/offices2020/index.html'
    template = loader.get_template(template_name)
    data = RUSSIA.calc_data_2020.rubric_stats
    context = {
        'table_headers': list(zip(data.get_table_headers(), data.get_table_column_description())),
        'table_rows': list(data.get_all_office_report_rows(RUSSIA)),
    }
    return HttpResponse(template.render(context, request))
