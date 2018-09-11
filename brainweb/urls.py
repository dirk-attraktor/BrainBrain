from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('p2p/getIndividuals/<str:problem_name>', views.p2p_getIndividuals, name='p2p_getIndividuals'),
    path('problem/', views.problem_index, name='problem_index'),
    path('problem/<int:pk>', views.problem_show, name='problem_show'),
    path('species/<int:pk>', views.species_show, name='species_show'),
    path('individual/<int:pk>', views.individual_show, name='individual_show'),
    path('problem/<int:pk>/cleanup', views.problem_cleanup, name='problem_cleanup'),
    path('population/<int:pk>', views.population_show, name='population_show'),
    path('population/<int:pk>/delete', views.population_delete, name='population_delete'),
    path('referencefunction/<int:pk>', views.referencefunction_show, name='referencefunction_show'),
    path('referencefunction/<int:pk>/reset', views.referencefunction_reset, name='referencefunction_reset'),
    path('admin/', admin.site.urls),
]
