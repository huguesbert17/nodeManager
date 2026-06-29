from django.urls import path

from . import views

app_name = "nodeManager"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path("admin/", views.admin_index, name="admin_index"),
    path("settings/", views.settings, name="settings"),
    path("app/<int:app_id>/", views.detail, name="detail"),
    path("app/<int:app_id>/start/", views.start, name="start"),
    path("app/<int:app_id>/stop/", views.stop, name="stop"),
    path("app/<int:app_id>/restart/", views.restart, name="restart"),
    path("app/<int:app_id>/redeploy/", views.redeploy, name="redeploy"),
    path("app/<int:app_id>/logs/", views.logs, name="logs"),
    path("app/<int:app_id>/delete/", views.delete, name="delete"),
]
