from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    department = models.CharField(max_length=100)

    semester = models.IntegerField()

    skills = models.TextField(blank=True)

    interests = models.TextField(blank=True)

    career_goal = models.CharField(
        max_length=200,
        blank=True
    )

    study_hours = models.FloatField(default=1.0)

    preferred_learning_method = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return self.user.username