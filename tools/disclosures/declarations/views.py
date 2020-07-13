from . import models
from django.views import generic
from django.views.generic.edit import FormView
from .documents import ElasticSectionDocument, ElasticPersonDocument, ElasticOfficeDocument
from declarations.input_json import TIntersectionStatus
from django import forms


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
    q = forms.CharField(label='')
    def send_search_query(self):
        pass


class CommonSearchView(FormView, generic.ListView):
    paginate_by = 20
    form_class = CommonSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "hits_count"):
            context['hits_count'] = self.hits_count
            context['query'] = self.query

        return context

    def get_initial(self):
        result = {}
        if 'q' in self.request.GET:
            result['q'] = self.request.GET["q"]
        return result


class OfficeSearchView(CommonSearchView):
    model = models.Office
    template_name = 'office/index.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return []
        search = ElasticOfficeDocument.search().query('match', name=query)
        self.hits_count = search.count()
        self.query = query
        object_list = list()
        for x in search[:100]:
            object_list.append(models.Office.objects.get(pk=x.id))
            if len(object_list) > 100:
                break
        object_list.sort(key=lambda x: x.source_document_count, reverse=True)
        return object_list


class ChildOfficeSearchView(CommonSearchView):
    model = models.Office
    template_name = 'office/index.html'

    def get_queryset(self):
        parent_id = self.request.GET.get('parent_id')
        if parent_id is None:
            return []
        parent_id = int(parent_id)
        office = models.Office.objects.get(id=parent_id)
        self.hits_count = office.child_offices_count
        self.query = "parent_id={}".format(parent_id)
        object_list = list()
        for id, _ in office.get_child_offices(1000):
            object_list.append(models.Office.objects.get(pk=id))
        object_list.sort(key=lambda x: x.source_document_count, reverse=True)
        return object_list


class PersonSearchView(CommonSearchView):
    model = models.Person
    template_name = 'person/index.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return []
        search = ElasticPersonDocument.search().query('match', person_name=query)
        self.hits_count = search.count()
        self.query = query
        object_list = list()
        for x in search[:100]:
            object_list.append(models.Person.objects.get(pk=x.id))
            if len(object_list) > 100:
                break
        object_list.sort(key=lambda x: x.section_count, reverse=True)
        return object_list


class SectionSearchView(CommonSearchView):
    model = models.Section
    template_name = 'section/index.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return []
        search = ElasticSectionDocument.search().query('match', person_name=query)
        self.hits_count = search.count()
        self.query = query
        object_list = list()
        for x in search[:100]:
            object_list.append(models.Section.objects.get(pk=x.id))
            if len(object_list) > 100:
                break
        object_list.sort(key=lambda x: x.income_year, reverse=True)
        return object_list
