import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


# ============================================================
# AI OUTPUT STRUCTURE
# ============================================================

class AIProject(BaseModel):
    title: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class AIExperience(BaseModel):
    job_title: str
    company: str
    location: str = ""
    description: str = ""


class AICertification(BaseModel):
    name: str
    issuing_organization: str = ""
    credential_id: str = ""


class AISkillCategory(BaseModel):
    category: str
    skills: list[str] = Field(default_factory=list)


class AIResumeOutput(BaseModel):
    professional_summary: str = ""

    technical_skills: list[AISkillCategory] = Field(
        default_factory=list
    )

    projects: list[AIProject] = Field(
        default_factory=list
    )

    experience: list[AIExperience] = Field(
        default_factory=list
    )

    certifications: list[AICertification] = Field(
        default_factory=list
    )

    achievements: list[str] = Field(
        default_factory=list
    )


# ============================================================
# HELPER: GROUP ORIGINAL SKILLS
# ============================================================

def build_skill_categories(skills):
    grouped = {}

    for item in skills:
        category = (item.category or "Other").strip()
        skill = (item.skill or "").strip()

        if not skill:
            continue

        if category not in grouped:
            grouped[category] = []

        if skill.lower() not in [
            existing.lower() for existing in grouped[category]
        ]:
            grouped[category].append(skill)

    return [
        AISkillCategory(
            category=category,
            skills=skill_list,
        )
        for category, skill_list in grouped.items()
        if skill_list
    ]


# ============================================================
# GENERATE AI RESUME
# ============================================================

def generate_resume(
    profile,
    education,
    projects,
    experience,
    certifications,
    achievements,
    skills,
):
    # --------------------------------------------------------
    # ORIGINAL DATA: THIS IS THE SOURCE OF TRUTH
    # --------------------------------------------------------

    original_summary = (
        getattr(profile, "professional_summary", "") or ""
    ).strip()

    original_skill_categories = build_skill_categories(skills)

    original_projects = [
        AIProject(
            title=item.title or "",
            description=item.description or "",
            technologies=[
                technology.strip()
                for technology in (item.technologies or "").split(",")
                if technology.strip()
            ],
        )
        for item in projects
        if (item.title or "").strip()
    ]

    original_experience = [
        AIExperience(
            job_title=item.job_title or "",
            company=item.company or "",
            location=item.location or "",
            description=item.description or "",
        )
        for item in experience
        if (item.job_title or item.company)
    ]

    original_certifications = [
        AICertification(
            name=item.name or "",
            issuing_organization=item.issuing_organization or "",
            credential_id=item.credential_id or "",
        )
        for item in certifications
        if (item.name or "").strip()
    ]

    original_achievements = [
        f"{item.title}: {item.description}".strip(": ")
        if item.description
        else item.title
        for item in achievements
        if getattr(item, "verified", False)
        and getattr(item, "title", "")
    ]

    # --------------------------------------------------------
    # BUILD INPUT DATA FOR GEMINI
    # --------------------------------------------------------

    input_data = {
        "resume_name": getattr(profile, "resume_name", ""),
        "professional_summary": original_summary,

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
            }
            for item in projects
        ],

        "experience": [
            {
                "job_title": item.job_title,
                "company": item.company,
                "location": item.location,
                "description": item.description,
            }
            for item in experience
        ],

        "certifications": [
            {
                "name": item.name,
                "issuing_organization": item.issuing_organization,
                "credential_id": item.credential_id,
            }
            for item in certifications
        ],

        "verified_achievements": [
            {
                "title": item.title,
                "description": item.description,
            }
            for item in achievements
            if getattr(item, "verified", False)
        ],
    }

    # --------------------------------------------------------
    # DEFAULT OUTPUT: PRESERVE ALL ORIGINAL SECTIONS
    # --------------------------------------------------------

    result = AIResumeOutput(
        professional_summary=original_summary,
        technical_skills=original_skill_categories,
        projects=original_projects,
        experience=original_experience,
        certifications=original_certifications,
        achievements=original_achievements,
    )

    # Preserve the user's exact factual details. AI rewriting is intentionally
    # disabled here so names, project descriptions and experience are not changed.
    return result
