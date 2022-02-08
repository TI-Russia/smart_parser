import os.path

from django.urls import path, re_path
from . import views
from django.views.generic import TemplateView
from functools import partial
from office_db.russia import RUSSIA

urlpatterns = [
    path('', TemplateView.as_view(template_name="morda/index.html"), name='home_page'),
    path('about.html', TemplateView.as_view(template_name="morda/about.html"), name='about_page'),
    path('permalinks.html', TemplateView.as_view(template_name="morda/permalinks.html"), name='permalinks'),
    path('second_office.html', TemplateView.as_view(template_name='morda/second_office.html'), name='second_office'),
    path('smart_parser_spec.html', TemplateView.as_view(template_name='morda/smart_parser_spec.html'), name='spv'),
    path('news.html', TemplateView.as_view(template_name='morda/news_mobile.html'), name='news_page'),
    path('compare_income_descr.html', TemplateView.as_view(template_name='morda/compare_income_descr.html'), name='compare_income_descr'),

    path('sitemap.txt', views.sitemapView, name='sitemap'),
    path('sitemap.xml', views.sitemapXmlView, name='sitemapxml'),
    re_path('sitemap(?P<sitemapid>[0-9a-z-]+)?.xml', views.sitemapAuxXmlView, name='sitemapauxxml'),
    re_path('static/(?P<sitemapid>[0-9a-z-]+)?/sitemap.xml', views.sitemapAuxXmlView, name='sitemapauxxml'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    path('person/', views.PersonSearchView.as_view(), name='person_search'),
    path('person/<int:pk>/', views.PersonView.as_view(), name='person_detail'),

    path('section/', views.SectionSearchView.as_view(), name='section_search'),
    path('section/<int:pk>/', views.SectionView.as_view(), name='section_detail'),

    path('office/', views.OfficeSearchView.as_view(), name='office_search'),
    path('office/<int:pk>/', views.OfficeView.as_view(), name='office_detail'),

    path('region/', views.region_list_view, name='region_list'),
    path('region/<int:region_id>/', views.region_detail_view, name='region_detail'),

    path('file/<int:pk>/', views.FileView.as_view(), name='file_detail'),
    path('file/', views.FileSearchView.as_view(), name='file_search'),
    path('sourcedoc/<str:sha256_and_file_extension>', views.source_doc_getter, name='source_doc_getter'),

    path('reports/genders/index.html', views.anyUrlView),
    path('reports/names/index.html', views.anyUrlView),
    path('reports/car-brands/index.html', views.anyUrlView),
    path('reports/car-brands/car-brands-by-years.html', views.anyUrlView),
    path('reports/web_site_snapshots/index.html', views.anyUrlView),
    path('reports/regions/index.html', views.anyUrlView),
    path('reports/new-car/index.html', views.anyUrlView),
    path('reports/offices/index.html', views.anyUrlView),
    path('reports/regions2020/index.html', partial(views.region_report_view, 2020)),
    path('reports/regions2020/data.csv', partial(views.region_report_csv, 2020)),

    path('reports/offices2020/index.html', views.office_report_2020_view),
    path('reports/offices2020/office_stat_data.csv', partial(views.write_csv, RUSSIA.calc_data_2020.office_stats.get_csv_path())),
]
