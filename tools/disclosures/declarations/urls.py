from django.urls import path

from . import views

urlpatterns = [
    path('sections/<int:pk>/', views.SectionView.as_view(), name='detail'),
]