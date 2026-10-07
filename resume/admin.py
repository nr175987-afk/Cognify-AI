from django.contrib import admin

from .models import (
    ResumeProfile,
    ResumeEducation,
    ResumeProject,
    ResumeExperience,
    ResumeCertification,
    ResumeAchievement,
    ResumeVersion,
)


@admin.register(ResumeProfile)
class ResumeProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone",
        "location",
        "updated_at",
    )


@admin.register(ResumeEducation)
class ResumeEducationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "degree",
        "institution",
        "start_year",
        "end_year",
    )


@admin.register(ResumeProject)
class ResumeProjectAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "is_featured",
        "created_at",
    )


@admin.register(ResumeExperience)
class ResumeExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "job_title",
        "company",
        "currently_working",
    )


@admin.register(ResumeCertification)
class ResumeCertificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "issuing_organization",
        "issue_date",
    )


@admin.register(ResumeAchievement)
class ResumeAchievementAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "source",
        "verified",
        "created_at",
    )

    list_filter = (
        "source",
        "verified",
    )


@admin.register(ResumeVersion)
class ResumeVersionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "version_number",
        "created_at",
    )