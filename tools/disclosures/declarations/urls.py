from django.urls import path
from . import views

urlpatterns = [
    path('section/<int:pk>/', views.SectionView.as_view(), name='section_detail'),
    path('person/<int:pk>/', views.PersonView.as_view(), name='person_detail'),
    path('file/<int:pk>/', views.FileView.as_view(), name='file_detail'),
    path('', views.HomePageView.as_view(), name='home_page'),
    path('about.html', views.AboutPageView.as_view(), name='about_page'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
]
