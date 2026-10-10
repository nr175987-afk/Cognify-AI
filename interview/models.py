
from django.db import models
from django.contrib.auth.models import User


class InterviewSession(models.Model):

    DIFFICULTY_CHOICES = [
        ("Easy", "Easy"),
        ("Medium", "Medium"),
        ("Hard", "Hard"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="interview_sessions"
    )

    role = models.CharField(max_length=150)

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES
    )

    total_questions = models.PositiveIntegerField(default=5)

    completed_questions = models.PositiveIntegerField(default=0)

    overall_score = models.FloatField(default=0)

    status = models.CharField(
        max_length=30,
        default="Not Started"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.role} - "
            f"{self.difficulty}"
        )


class InterviewQuestion(models.Model):

    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_number = models.PositiveIntegerField()

    question = models.TextField()

    expected_answer = models.TextField(blank=True)

    user_answer = models.TextField(blank=True)

    score = models.FloatField(default=0)

    feedback = models.TextField(blank=True)

    # AI-generated learning content
    concept_explanation = models.TextField(blank=True)

    how_it_works = models.TextField(blank=True)

    example = models.TextField(blank=True)

    interview_ready_answer = models.TextField(blank=True)

    practice_question = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.session.role} - "
            f"Question {self.question_number}"
        )