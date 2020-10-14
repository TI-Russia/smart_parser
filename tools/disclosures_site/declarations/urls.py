from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home_page'),
    path('about.html', views.AboutPageView.as_view(), name='about_page'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    path('person/', views.PersonSearchView.as_view(), name='person_search'),
    path('person/<int:pk>/', views.PersonView.as_view(), name='person_detail'),

    path('section/', views.SectionSearchView.as_view(), name='section_search'),
    path('section/<int:pk>/', views.SectionView.as_view(), name='section_detail'),

    path('office/', views.OfficeSearchView.as_view(), name='office_search'),
    path('office/<int:pk>/', views.OfficeView.as_view(), name='office_detail'),

    path('file/<int:pk>/', views.FileView.as_view(), name='file_detail'),
    path('file/', views.FileSearchView.as_view(), name='file_search'),

]
