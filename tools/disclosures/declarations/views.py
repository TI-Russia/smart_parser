from . import models
from .forms import SearchForm
from django.views import generic
from django.views.generic.edit import FormView
from .documents import ElasticSectionDocument, ElasticPersonDocument
from declarations.input_json import TIntersectionStatus


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SearchForm
        return context


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


class SearchResultsView(FormView, generic.ListView):
    model = models.Section
    paginate_by = 40
    form_class = SearchForm

    def get_template_names(self):
        search_object_type = self.request.GET.get('search_object_type')
        if search_object_type == "people_search":
            return 'person/search_results.html'
        return 'section/search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        search_object_type = self.request.GET.get('search_object_type')

        if search_object_type == "people_search":
            persons = list(ElasticPersonDocument.search().query('match', person_name=query))
            object_list = list()
            for x in persons:
                object_list.append(models.Person.objects.get(pk=x.id))
                if len(object_list) > 100:
                    break
        else:
            sections = list(ElasticSectionDocument.search().query('match', person_name=query))
            object_list = list()
            for x in sections:
                object_list.append(models.Section.objects.get(pk=x.id))
                if len(object_list) > 100:
                    break
        return object_list

    def get_initial(self):
        return {'q': self.request.GET["q"],
                'search_object_type': self.request.GET["search_object_type"]
                }

