from django.urls import path

from . import views

app_name = "cals"
urlpatterns = [
    # ex: /posts/
    path("", views.index, name="index"),
]
