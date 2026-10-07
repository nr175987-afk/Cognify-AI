import re
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from .ai_resume import AIResumeOutput


from .models import (
    ResumeProfile,
    ResumeSkill,
    ResumeEducation,
    ResumeProject,
    ResumeExperience,
    ResumeCertification,
    ResumeAchievement,
    ResumeVersion,
)

from .achievement_service import get_verified_learning_achievements
from .ai_resume import generate_resume
from .pdf_generator import generate_resume_pdf
from django.http import HttpResponse


def get_section_indices(post, prefix):
    """
    Finds all indexes used by dynamic form fields.

    Example:
    education_0_institution
    education_2_institution

    Returns:
    [0, 2]
    """

    pattern = re.compile(
        rf"^{re.escape(prefix)}_(\d+)_"
    )

    indexes = set()

    for key in post.keys():

        match = pattern.match(key)

        if match:
            indexes.add(
                int(match.group(1))
            )

    return sorted(indexes)


@login_required
def resume_home(request):

    profile, created = ResumeProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "resume_name": request.user.get_full_name()
            or request.user.username
        }
    )

    education = ResumeEducation.objects.filter(
        user=request.user
    )

    projects = ResumeProject.objects.filter(
        user=request.user
    )

    experience = ResumeExperience.objects.filter(
        user=request.user
    )

    certifications = ResumeCertification.objects.filter(
        user=request.user
    )

    skills = ResumeSkill.objects.filter(
        user=request.user
    )

    achievements = get_verified_learning_achievements(
        request.user
    )

    return render(
        request,
        "resume/resume_form.html",
        {
            "profile": profile,
            "education": education,
            "projects": projects,
            "experience": experience,
            "certifications": certifications,
            "skills": skills,
            "achievements": achievements,
        }
    )


@login_required
@transaction.atomic
def save_resume(request):

    if request.method != "POST":
        return redirect("resume_home")

    profile, created = ResumeProfile.objects.get_or_create(
        user=request.user
    )

    # ==================================================
    # PERSONAL INFORMATION
    # ==================================================

    profile.resume_name = request.POST.get(
        "resume_name",
        ""
    ).strip()

    profile.phone = request.POST.get(
        "phone",
        ""
    ).strip()

    profile.location = request.POST.get(
        "location",
        ""
    ).strip()

    profile.professional_summary = request.POST.get(
        "professional_summary",
        ""
    ).strip()

    profile.linkedin_url = request.POST.get(
        "linkedin_url",
        ""
    ).strip()

    profile.github_url = request.POST.get(
        "github_url",
        ""
    ).strip()

    profile.leetcode_url = request.POST.get(
        "leetcode_url",
        ""
    ).strip()

    profile.portfolio_url = request.POST.get(
        "portfolio_url",
        ""
    ).strip()

    profile.save()


    # ==================================================
    # DELETE OLD EDUCATION
    # ==================================================

    education_delete_ids = request.POST.getlist(
        "delete_education"
    )

    if education_delete_ids:

        ResumeEducation.objects.filter(
            user=request.user,
            id__in=education_delete_ids
        ).delete()


    # ==================================================
    # DELETE OLD PROJECTS
    # ==================================================

    project_delete_ids = request.POST.getlist(
        "delete_project"
    )

    if project_delete_ids:

        ResumeProject.objects.filter(
            user=request.user,
            id__in=project_delete_ids
        ).delete()


    # ==================================================
    # DELETE OLD EXPERIENCE
    # ==================================================

    experience_delete_ids = request.POST.getlist(
        "delete_experience"
    )

    if experience_delete_ids:

        ResumeExperience.objects.filter(
            user=request.user,
            id__in=experience_delete_ids
        ).delete()


    # ==================================================
    # DELETE OLD CERTIFICATIONS
    # ==================================================

    certification_delete_ids = request.POST.getlist(
        "delete_certification"
    )

    if certification_delete_ids:

        ResumeCertification.objects.filter(
            user=request.user,
            id__in=certification_delete_ids
        ).delete()


    # ==================================================
    # SAVE EDUCATION
    # ==================================================

    education_indexes = get_section_indices(
        request.POST,
        "education"
    )

    for index in education_indexes:

        education_id = request.POST.get(
            f"education_{index}_id"
        )

        institution = request.POST.get(
            f"education_{index}_institution",
            ""
        ).strip()

        degree = request.POST.get(
            f"education_{index}_degree",
            ""
        ).strip()

        field_of_study = request.POST.get(
            f"education_{index}_field_of_study",
            ""
        ).strip()

        start_year = request.POST.get(
            f"education_{index}_start_year"
        )

        end_year = request.POST.get(
            f"education_{index}_end_year"
        )

        percentage_or_cgpa = request.POST.get(
            f"education_{index}_percentage_or_cgpa",
            ""
        ).strip()

        description = request.POST.get(
            f"education_{index}_description",
            ""
        ).strip()

        if not institution and not degree:
            continue

        if education_id:

            education = ResumeEducation.objects.filter(
                id=education_id,
                user=request.user
            ).first()

            if education:

                education.institution = institution
                education.degree = degree
                education.field_of_study = field_of_study

                education.start_year = (
                    int(start_year)
                    if start_year
                    else None
                )

                education.end_year = (
                    int(end_year)
                    if end_year
                    else None
                )

                education.percentage_or_cgpa = (
                    percentage_or_cgpa
                )

                education.description = description

                education.save()

        else:

            ResumeEducation.objects.create(
                user=request.user,
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                start_year=(
                    int(start_year)
                    if start_year
                    else None
                ),
                end_year=(
                    int(end_year)
                    if end_year
                    else None
                ),
                percentage_or_cgpa=(
                    percentage_or_cgpa
                ),
                description=description,
            )


    # ==================================================
    # SAVE PROJECTS
    # ==================================================

    project_indexes = get_section_indices(
        request.POST,
        "project"
    )

    for index in project_indexes:

        project_id = request.POST.get(
            f"project_{index}_id"
        )

        title = request.POST.get(
            f"project_{index}_title",
            ""
        ).strip()

        description = request.POST.get(
            f"project_{index}_description",
            ""
        ).strip()

        technologies = request.POST.get(
            f"project_{index}_technologies",
            ""
        ).strip()

        github_url = request.POST.get(
            f"project_{index}_github_url",
            ""
        ).strip()

        live_url = request.POST.get(
            f"project_{index}_live_url",
            ""
        ).strip()

        start_date = request.POST.get(
            f"project_{index}_start_date"
        )

        end_date = request.POST.get(
            f"project_{index}_end_date"
        )

        if not title:
            continue

        if project_id:

            project = ResumeProject.objects.filter(
                id=project_id,
                user=request.user
            ).first()

            if project:

                project.title = title
                project.description = description
                project.technologies = technologies
                project.github_url = github_url
                project.live_url = (
                    live_url
                )

                project.start_date = (
                    start_date
                    if start_date
                    else None
                )

                project.end_date = (
                    end_date
                    if end_date
                    else None
                )

                project.save()

        else:

            ResumeProject.objects.create(
                user=request.user,
                title=title,
                description=description,
                technologies=technologies,
                github_url=github_url,
                live_url=live_url,
                start_date=(
                    start_date
                    if start_date
                    else None
                ),
                end_date=(
                    end_date
                    if end_date
                    else None
                ),
            )


    # ==================================================
    # SAVE EXPERIENCE
    # ==================================================

    experience_indexes = get_section_indices(
        request.POST,
        "experience"
    )

    for index in experience_indexes:

        experience_id = request.POST.get(
            f"experience_{index}_id"
        )

        job_title = request.POST.get(
            f"experience_{index}_job_title",
            ""
        ).strip()

        company = request.POST.get(
            f"experience_{index}_company",
            ""
        ).strip()

        location = request.POST.get(
            f"experience_{index}_location",
            ""
        ).strip()

        description = request.POST.get(
            f"experience_{index}_description",
            ""
        ).strip()

        start_date = request.POST.get(
            f"experience_{index}_start_date"
        )

        end_date = request.POST.get(
            f"experience_{index}_end_date"
        )

        currently_working = (
            f"experience_{index}_currently_working"
            in request.POST
        )

        if not job_title and not company:
            continue

        if experience_id:

            experience = ResumeExperience.objects.filter(
                id=experience_id,
                user=request.user
            ).first()

            if experience:

                experience.job_title = job_title
                experience.company = company
                experience.location = location
                experience.description = description

                experience.start_date = (
                    start_date
                    if start_date
                    else None
                )

                experience.end_date = (
                    end_date
                    if end_date
                    else None
                )

                experience.currently_working = (
                    currently_working
                )

                experience.save()

        else:

            ResumeExperience.objects.create(
                user=request.user,
                job_title=job_title,
                company=company,
                location=location,
                description=description,
                start_date=(
                    start_date
                    if start_date
                    else None
                ),
                end_date=(
                    end_date
                    if end_date
                    else None
                ),
                currently_working=(
                    currently_working
                ),
            )


    # ==================================================
    # SAVE CERTIFICATIONS
    # ==================================================

    certification_indexes = get_section_indices(
        request.POST,
        "certification"
    )

    for index in certification_indexes:

        certification_id = request.POST.get(
            f"certification_{index}_id"
        )

        name = request.POST.get(
            f"certification_{index}_name",
            ""
        ).strip()

        issuing_organization = request.POST.get(
            f"certification_{index}_issuing_organization",
            ""
        ).strip()

        issue_date = request.POST.get(
            f"certification_{index}_issue_date"
        )

        credential_id = request.POST.get(
            f"certification_{index}_credential_id",
            ""
        ).strip()

        credential_url = request.POST.get(
            f"certification_{index}_credential_url",
            ""
        ).strip()

        if not name:
            continue

        if certification_id:

            certification = ResumeCertification.objects.filter(
                id=certification_id,
                user=request.user
            ).first()

            if certification:

                certification.name = name

                certification.issuing_organization = (
                    issuing_organization
                )

                certification.issue_date = (
                    issue_date
                    if issue_date
                    else None
                )

                certification.credential_id = (
                    credential_id
                )

                certification.credential_url = (
                    credential_url
                )

                certification.save()

        else:

            ResumeCertification.objects.create(
                user=request.user,
                name=name,
                issuing_organization=(
                    issuing_organization
                ),
                issue_date=(
                    issue_date
                    if issue_date
                    else None
                ),
                credential_id=credential_id,
                credential_url=credential_url,
            )


    # ==================================================
    # SAVE TECHNICAL SKILLS
    # ==================================================

    ResumeSkill.objects.filter(
        user=request.user
    ).delete()

    skill_categories = request.POST.getlist(
        "skill_category[]"
    )

    skills = request.POST.getlist(
        "skill[]"
    )

    for category, skill in zip(
        skill_categories,
        skills
    ):

        category = category.strip()
        skill = skill.strip()

        if not category or not skill:
            continue

        ResumeSkill.objects.create(
            user=request.user,
            category=category,
            skill=skill
        )


    messages.success(
        request,
        "Resume saved successfully."
    )

    return redirect("resume_home")


@login_required
def generate_ai_resume(request):
    profile, created = ResumeProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "resume_name": "",
            "phone": "",
            "linkedin_url": "",
            "github_url": "",
            "leetcode_url": "",
            "portfolio_url": "",
        },
    )

    education = list(
        ResumeEducation.objects.filter(
            user=request.user
        )
    )

    projects = list(
        ResumeProject.objects.filter(
            user=request.user
        )
    )

    experience = list(
        ResumeExperience.objects.filter(
            user=request.user
        )
    )

    certifications = list(
        ResumeCertification.objects.filter(
            user=request.user
        )
    )

    skills = list(
        ResumeSkill.objects.filter(
            user=request.user
        )
    )

    achievements = list(
        get_verified_learning_achievements(
            request.user
        )
    )

    # --------------------------------------------------
    # GENERATE AI RESUME
    # --------------------------------------------------

    ai_resume = generate_resume(
        profile=profile,
        education=education,
        projects=projects,
        experience=experience,
        certifications=certifications,
        achievements=achievements,
        skills=skills,
    )

    # --------------------------------------------------
    # CREATE COMPLETE HISTORICAL SNAPSHOT
    # --------------------------------------------------

    resume_data = ai_resume.model_dump()

    resume_data["_snapshot"] = {
        "profile": {
            "resume_name": profile.resume_name,
            "email": request.user.email,
            "phone": profile.phone,
            "location": profile.location,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "leetcode_url": profile.leetcode_url,
            "portfolio_url": profile.portfolio_url,
        },

        "education": [
            {
                "institution": item.institution,
                "degree": item.degree,
                "field_of_study": item.field_of_study,
                "start_year": item.start_year,
                "end_year": item.end_year,
                "percentage_or_cgpa": item.percentage_or_cgpa,
                "description": item.description,
            }
            for item in education
        ],

        "skills": [
            {
                "category": item.category,
                "skill": item.skill,
            }
            for item in skills
        ],

        "projects": [
            {
                "title": item.title,
                "description": item.description,
                "technologies": item.technologies,
                "github_url": item.github_url,
                "live_url": item.live_url,
                "start_date": (
                    item.start_date.isoformat()
                    if item.start_date
                    else None
                ),
                "end_date": (
                    item.end_date.isoformat()
                    if item.end_date
                    else None
                ),
            }
            for item in projects
        ],

        "experience": [
            {
                "job_title": item.job_title,
                "company": item.company,
                "location": item.location,
                "description": item.description,
                "start_date": (
                    item.start_date.isoformat()
                    if item.start_date
                    else None
                ),
                "end_date": (
                    item.end_date.isoformat()
                    if item.end_date
                    else None
                ),
                "currently_working": item.currently_working,
            }
            for item in experience
        ],

        "certifications": [
            {
                "name": item.name,
                "issuing_organization": item.issuing_organization,
                "issue_date": (
                    item.issue_date.isoformat()
                    if item.issue_date
                    else None
                ),
                "credential_id": item.credential_id,
                "credential_url": item.credential_url,
            }
            for item in certifications
        ],

        "achievements": [
            {
                "title": item.title,
                "description": item.description,
                "source": item.source,
                "verified": item.verified,
                "source_reference": item.source_reference,
            }
            for item in achievements
        ],
    }

    # --------------------------------------------------
    # VERSION NUMBER
    # --------------------------------------------------

    latest_version = (
        ResumeVersion.objects
        .filter(user=request.user)
        .order_by("-version_number")
        .first()
    )

    if latest_version:
        next_version = (
            latest_version.version_number + 1
        )
    else:
        next_version = 1

    # --------------------------------------------------
    # SAVE VERSION
    # --------------------------------------------------

    version = ResumeVersion.objects.create(
        user=request.user,
        version_number=next_version,
        resume_data=resume_data,
        change_summary=(
            "AI-generated resume version "
            f"{next_version}"
        ),
    )

    # --------------------------------------------------
    # SHOW PREVIEW
    # --------------------------------------------------

    return render(
        request,
        "resume/resume_preview.html",
        {
            "ai_resume": ai_resume,
            "version": version,
            "profile": profile,
        },
    )


@login_required
def download_resume_pdf(request):

    latest_version = (
        ResumeVersion.objects
        .filter(user=request.user)
        .order_by("-version_number")
        .first()
    )

    if not latest_version:

        messages.error(
            request,
            "Please generate a resume first."
        )

        return redirect("resume_home")


    profile = ResumeProfile.objects.get(
        user=request.user
    )

    education = ResumeEducation.objects.filter(
        user=request.user
    )

    achievements = get_verified_learning_achievements(
        request.user
    )


    # ==================================================
    # RECREATE AI RESUME OBJECT
    # ==================================================

    data = latest_version.resume_data

    technical_skills = []

    for category in data.get(
        "technical_skills",
        []
    ):

        technical_skills.append(
            SimpleNamespace(
                category=category.get(
                    "category",
                    ""
                ),
                skills=category.get(
                    "skills",
                    []
                )
            )
        )


    ai_resume = SimpleNamespace(

        professional_summary=data.get(
            "professional_summary",
            ""
        ),

        technical_skills=technical_skills,

        projects=[
            SimpleNamespace(**project)
            for project in data.get(
                "projects",
                []
            )
        ],

        experience=[
            SimpleNamespace(**experience)
            for experience in data.get(
                "experience",
                []
            )
        ],

        certifications=[
            SimpleNamespace(**certification)
            for certification in data.get(
                "certifications",
                []
            )
        ],

    )


    # ==================================================
    # GENERATE PDF
    # ==================================================

    pdf_buffer = generate_resume_pdf(
        user=request.user,
        profile=profile,
        education=education,
        ai_resume=ai_resume,
        achievements=achievements,
    )


    filename = (
        f"{request.user.username}_resume_"
        f"v{latest_version.version_number}.pdf"
    )


    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf"
    )


# ==========================================================
# SAVED RESUME VERSIONS
# ==========================================================

@login_required
def resume_versions(request):

    versions = (
        ResumeVersion.objects
        .filter(user=request.user)
        .order_by("-version_number")
    )

    return render(
        request,
        "resume/resume_versions.html",
        {
            "versions": versions,
        }
    )


@login_required
def view_resume_version(request, version_id):
    version = get_object_or_404(
        ResumeVersion,
        id=version_id,
        user=request.user,
    )

    resume_data = version.resume_data or {}

    snapshot = resume_data.get(
        "_snapshot",
        {}
    )

    profile_data = snapshot.get(
        "profile",
        {}
    )

    education = snapshot.get(
        "education",
        []
    )

    skills = snapshot.get(
        "skills",
        []
    )

    projects = snapshot.get(
        "projects",
        []
    )

    experience = snapshot.get(
        "experience",
        []
    )

    certifications = snapshot.get(
        "certifications",
        []
    )

    achievements = snapshot.get(
        "achievements",
        []
    )

    context = {
        "version": version,

        # Historical profile
        "profile_data": profile_data,

        # Historical original data
        "education": education,
        "skills": skills,
        "projects": projects,
        "experience": experience,
        "certifications": certifications,
        "achievements": achievements,

        # Historical AI-generated content
        "professional_summary": resume_data.get(
            "professional_summary",
            ""
        ),

        "technical_skills": resume_data.get(
            "technical_skills",
            []
        ),

        "ai_projects": resume_data.get(
            "projects",
            []
        ),

        "ai_experience": resume_data.get(
            "experience",
            []
        ),

        "ai_certifications": resume_data.get(
            "certifications",
            []
        ),

        "ai_achievements": resume_data.get(
            "achievements",
            []
        ),
    }

    return render(
        request,
        "resume/resume_version_detail.html",
        context,
    )

@login_required
def download_resume_version_pdf(request, version_id):

    version = get_object_or_404(
        ResumeVersion,
        id=version_id,
        user=request.user,
    )

    resume_data = version.resume_data or {}

    snapshot = resume_data.get(
        "_snapshot",
        {}
    )

    profile_data = snapshot.get(
        "profile",
        {}
    )

    education_data = snapshot.get(
        "education",
        []
    )

    achievements_data = snapshot.get(
        "achievements",
        []
    )

    # --------------------------------------------------
    # Reconstruct profile information from the snapshot
    # --------------------------------------------------

    class HistoricalProfile:
        pass

    profile = HistoricalProfile()

    profile.resume_name = profile_data.get(
        "resume_name",
        ""
    )

    profile.phone = profile_data.get(
        "phone",
        ""
    )

    profile.location = profile_data.get(
        "location",
        ""
    )

    profile.linkedin_url = profile_data.get(
        "linkedin_url",
        ""
    )

    profile.github_url = profile_data.get(
        "github_url",
        ""
    )

    profile.leetcode_url = profile_data.get(
        "leetcode_url",
        ""
    )

    profile.portfolio_url = profile_data.get(
        "portfolio_url",
        ""
    )

    # --------------------------------------------------
    # Reconstruct education
    # --------------------------------------------------

    class HistoricalEducation:
        pass

    education = []

    for item in education_data:

        education_item = HistoricalEducation()

        education_item.institution = item.get(
            "institution",
            ""
        )

        education_item.degree = item.get(
            "degree",
            ""
        )

        education_item.field_of_study = item.get(
            "field_of_study",
            ""
        )

        education_item.start_year = item.get(
            "start_year"
        )

        education_item.end_year = item.get(
            "end_year"
        )

        education_item.percentage_or_cgpa = item.get(
            "percentage_or_cgpa",
            ""
        )

        education_item.description = item.get(
            "description",
            ""
        )

        education.append(
            education_item
        )

    # --------------------------------------------------
    # Reconstruct achievements
    # --------------------------------------------------

    class HistoricalAchievement:
        pass

    achievements = []

    for item in achievements_data:

        achievement = HistoricalAchievement()

        achievement.title = item.get(
            "title",
            ""
        )

        achievement.description = item.get(
            "description",
            ""
        )

        achievements.append(
            achievement
        )

    # --------------------------------------------------
    # Reconstruct AI resume output
    # --------------------------------------------------

    ai_resume = AIResumeOutput.model_validate(
        {
            "professional_summary": resume_data.get(
                "professional_summary",
                ""
            ),

            "technical_skills": resume_data.get(
                "technical_skills",
                []
            ),

            "projects": resume_data.get(
                "projects",
                []
            ),

            "experience": resume_data.get(
                "experience",
                []
            ),

            "certifications": resume_data.get(
                "certifications",
                []
            ),

            "achievements": resume_data.get(
                "achievements",
                []
            ),
        }
    )

    # --------------------------------------------------
    # Create PDF
    # --------------------------------------------------

    pdf_buffer = generate_resume_pdf(
        user=request.user,
        profile=profile,
        education=education,
        ai_resume=ai_resume,
        achievements=achievements,
    )

    filename = (
        f"resume_version_{version.version_number}.pdf"
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="{filename}"'

    return response