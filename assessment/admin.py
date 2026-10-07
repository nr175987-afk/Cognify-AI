from django.contrib import admin

from .models import AssessmentAttempt


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "subject",
        "topic",
        "difficulty",
        "correct_answers",
        "total_questions",
        "score",
        "created_at",
    )

    list_filter = (
        "subject",
        "difficulty",
        "created_at",
    )

    search_fields = (
        "user__username",
        "topic",
    )