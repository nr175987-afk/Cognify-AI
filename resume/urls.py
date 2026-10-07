from django.urls import path
from . import views

urlpatterns = [
    path("", views.resume_home, name="resume_home"),

    path(
        "save/",
        views.save_resume,
        name="save_resume"
    ),

    path(
        "generate/",
        views.generate_ai_resume,
        name="generate_ai_resume"
    ),

    path(
        "download/",
        views.download_resume_pdf,
        name="download_resume_pdf"
    ),

    path(
        "versions/",
        views.resume_versions,
        name="resume_versions"
    ),

    path(
        "versions/<int:version_id>/",
        views.view_resume_version,
        name="view_resume_version"
    ),

    path(
        "versions/<int:version_id>/download/",
        views.download_resume_version_pdf,
        name="download_resume_version_pdf"
    ),
]