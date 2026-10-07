from django.urls import path
from . import views


urlpatterns = [
    path(
        "",
        views.interview_home,
        name="interview_home"
    ),

    path(
        "start/",
        views.start_interview,
        name="start_interview"
    ),

    path(
        "<int:session_id>/",
        views.interview_session,
        name="interview_session"
    ),

    path(
        "<int:session_id>/submit/",
        views.submit_answer,
        name="submit_answer"
    ),

    path(
        "<int:session_id>/result/",
        views.interview_result,
        name="interview_result"
    ),

    path(
        "history/",
        views.interview_history,
        name="interview_history"
    ),
]