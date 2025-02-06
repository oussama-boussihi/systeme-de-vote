from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('votant/', views.votant, name='votant'),
    path('co/', views.co, name='co'),
    path('de/', views.de, name='de'),
]
