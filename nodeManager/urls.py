from django.urls import path

from . import views

app_name = "nodeManager"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path("admin/", views.admin_index, name="admin_index"),
    path("settings/", views.settings, name="settings"),
    path("app/<int:app_id>/", views.legacy_detail_redirect, name="legacy_detail"),
    path("app/<uuid:public_id>/", views.detail, name="detail"),
    path("app/<uuid:public_id>/start/", views.start, name="start"),
    path("app/<uuid:public_id>/stop/", views.stop, name="stop"),
    path("app/<uuid:public_id>/restart/", views.restart, name="restart"),
    path("app/<uuid:public_id>/redeploy/", views.redeploy, name="redeploy"),
    path("app/<uuid:public_id>/logs/", views.logs, name="logs"),
    path("app/<uuid:public_id>/delete/", views.delete, name="delete"),
]
