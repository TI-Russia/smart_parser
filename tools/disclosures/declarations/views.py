from .models import Section, Income, RealEstate
from django.views import generic


class SectionView(generic.DetailView):
    model = Section
    template_name = 'sections/detail.html'

    #def get_context_data(self, **kwargs):
    #    context = super().get_context_data(**kwargs)
    #    context['incomes'] = Income.objects.filter(section=context['section'])
    #    context['real_estates'] = RealEstate.objects.filter(section=context['section'])
    #    context['vehicles'] = RealEstate.objects.filter(section=context['section'])
    #    return context

