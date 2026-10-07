from django.db import models
from django.contrib.auth.models import User


class ResumeProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="resume_profile"
    )

    # Editable resume name
    resume_name = models.CharField(
        max_length=150,
        default=""
    )

    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=150, blank=True)

    professional_summary = models.TextField(blank=True)

    linkedin_url = models.URLField()
    github_url = models.URLField()
    leetcode_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.resume_name} - {self.user.username}"


class ResumeEducation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_education"
    )

    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)

    start_year = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    end_year = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    percentage_or_cgpa = models.CharField(
        max_length=50,
        blank=True
    )

    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-end_year", "-start_year"]

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class ResumeSkill(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_skills"
    )

    category = models.CharField(max_length=100)
    skill = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "skill"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "skill"],
                name="unique_resume_user_skill"
            )
        ]

    def __str__(self):
        return f"{self.category} - {self.skill}"


class ResumeProject(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_projects"
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    technologies = models.CharField(
        max_length=500,
        blank=True
    )

    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return self.title


class ResumeExperience(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_experience"
    )

    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)

    location = models.CharField(
        max_length=150,
        blank=True
    )

    description = models.TextField()

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    currently_working = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-currently_working", "-start_date"]

    def __str__(self):
        return f"{self.job_title} - {self.company}"


class ResumeCertification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_certifications"
    )

    name = models.CharField(max_length=200)

    issuing_organization = models.CharField(
        max_length=200
    )

    issue_date = models.DateField(
        null=True,
        blank=True
    )

    credential_id = models.CharField(
        max_length=200,
        blank=True
    )

    credential_url = models.URLField(
        blank=True
    )

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return self.name


class ResumeAchievement(models.Model):

    ACHIEVEMENT_SOURCES = [
        ("USER", "User Added"),
        ("LEARNING_SYSTEM", "Learning System"),
        ("ASSESSMENT", "Assessment"),
        ("PROJECT", "Project"),
        ("CERTIFICATION", "Certification"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_achievements"
    )

    title = models.CharField(
        max_length=250
    )

    description = models.TextField()

    source = models.CharField(
        max_length=30,
        choices=ACHIEVEMENT_SOURCES,
        default="USER"
    )

    verified = models.BooleanField(
        default=False
    )

    source_reference = models.CharField(
        max_length=250,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-verified", "-created_at"]

    def __str__(self):
        return self.title


class ResumeVersion(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_versions"
    )

    version_number = models.PositiveIntegerField()

    resume_data = models.JSONField()

    change_summary = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.user.username} - Resume v{self.version_number}"