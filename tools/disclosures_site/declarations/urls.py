from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home_page'),
    path('about.html', views.AboutPageView.as_view(), name='about_page'),
    path('sitemap.txt', views.sitemapView, name='sitemap'),
    path('sitemap.xml', views.sitemapXmlView, name='sitemapxml'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    path('person/', views.PersonSearchView.as_view(), name='person_search'),

    path('section/', views.SectionSearchView.as_view(), name='section_search'),
    path('section/<int:pk>/', views.SectionView.as_view(), name='section_detail'),

    path('office/', views.OfficeSearchView.as_view(), name='office_search'),
    path('office/<int:pk>/', views.OfficeView.as_view(), name='office_detail'),

    path('file/<int:pk>/', views.FileView.as_view(), name='file_detail'),
    path('file/', views.FileSearchView.as_view(), name='file_search'),
    path('sourcedoc/<str:sha256_and_file_extension>', views.source_doc_getter, name='source_doc_getter'),

]
