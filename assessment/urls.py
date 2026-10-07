from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.assessment_home,
        name="assessment_home"
    ),

    path(
        "quiz/",
        views.quiz,
        name="quiz"
    ),

    path(
        "result/",
        views.assessment_result,
        name="assessment_result"
    ),

    path(
    "history/",
    views.assessment_history,
    name="assessment_history"
    ),

    path(
    "learning-analysis/",
    views.learning_analysis,
    name="learning_analysis"
    ),

    path(
    "personalized-plan/",
    views.personalized_plan,
    name="personalized_plan"
    ),

    path(
    "adaptive-learning/",
    views.adaptive_learning,
    name="adaptive_learning"
    ),

    path(
    "adaptive-content/",
    views.adaptive_content,
    name="adaptive_content"
    ),

]