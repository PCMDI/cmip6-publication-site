from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^index', views.index, name='index'),
    url(r'^review', views.review, name='review'),
    url(r'^search$', views.search, name='search'),
    url(r'^new$', views.new, name='new'),
    url(r'^finddoi$', views.finddoi),
    url(r'^review/', views.review, name='review'),
    url(r'^edit/(\d+)', views.edit, name='edit'),
    url(r'^delete/(\d+)', views.delete, name='delete'),
    #url(r'ensembles'), views.ensembles, name='ensembles'),
]