from django.urls import path

from . import views

urlpatterns = [
    path("config/", views.config, name="config"),
    path("transformations/", views.transformation_list, name="transformation-list"),
    path("transformations/upload/", views.transformation_create, name="transformation-create"),
    path("transformations/<str:pk>/", views.transformation_detail, name="transformation-detail"),
]
