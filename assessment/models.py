from django.db import models
from django.contrib.auth.models import User


class AssessmentAttempt(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    subject = models.CharField(
        max_length=100
    )

    topic = models.CharField(
        max_length=200
    )

    difficulty = models.CharField(
        max_length=30
    )

    total_questions = models.PositiveIntegerField()

    correct_answers = models.PositiveIntegerField(
        default=0
    )

    score = models.FloatField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.user.username} - "
            f"{self.topic} - "
            f"{self.score}%"
        )

class LearningContent(models.Model):

    topic = models.CharField(max_length=200)

    content_type = models.CharField(max_length=50)

    difficulty = models.CharField(max_length=30)

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.content_type} - {self.difficulty}"