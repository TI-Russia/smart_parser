from django.urls import path
from . import views

urlpatterns = [
    path('section/<int:pk>/', views.SectionView.as_view(), name='detail'),
    path('person/<int:pk>/', views.PersonView.as_view(), name='detail'),
    path('', views.HomePageView.as_view(), name='detail'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('statistics/', views.StatisticsView.as_view()),
#    path('elastic-section-search/', views.SectionElasticSearchView.as_view()),
]
