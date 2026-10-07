import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ============================================================
# AI OUTPUT STRUCTURE
# ============================================================

class AIProject(BaseModel):
    title: str
    description: str
    technologies: list[str] = Field(default_factory=list)


class AIExperience(BaseModel):
    job_title: str
    company: str
    location: str
    description: str


class AICertification(BaseModel):
    name: str
    issuing_organization: str
    credential_id: str


class AISkillCategory(BaseModel):
    category: str
    skills: list[str] = Field(default_factory=list)


class AIResumeOutput(BaseModel):
    professional_summary: str

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
    # PROFILE
    # --------------------------------------------------------

    profile_data = {
        "resume_name": profile.resume_name,
        "professional_summary": profile.professional_summary,
    }


    # --------------------------------------------------------
    # TECHNICAL SKILLS
    # --------------------------------------------------------

    skill_data = []

    for skill in skills:
        skill_data.append({
            "category": skill.category,
            "skill": skill.skill,
        })


    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    education_data = []

    for item in education:
        education_data.append({
            "institution": item.institution,
            "degree": item.degree,
            "field_of_study": item.field_of_study,
            "start_year": item.start_year,
            "end_year": item.end_year,
            "percentage_or_cgpa": item.percentage_or_cgpa,
            "description": item.description,
        })


    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    project_data = []

    for item in projects:
        project_data.append({
            "title": item.title,
            "description": item.description,
            "technologies": item.technologies,
        })


    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    experience_data = []

    for item in experience:
        experience_data.append({
            "job_title": item.job_title,
            "company": item.company,
            "location": item.location,
            "description": item.description,
        })


    # --------------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------------

    certification_data = []

    for item in certifications:
        certification_data.append({
            "name": item.name,
            "issuing_organization": item.issuing_organization,
            "credential_id": item.credential_id,
        })


    # --------------------------------------------------------
    # VERIFIED ACHIEVEMENTS
    # --------------------------------------------------------

    achievement_data = []

    for item in achievements:

        # Only verified achievements are sent to AI
        if item.verified:
            achievement_data.append({
                "title": item.title,
                "description": item.description,
                "verified": True,
            })


    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are a professional technical resume writer.

Create concise, professional and ATS-friendly resume
content for a technical student.

The resume must be suitable for recruiters and placement
applications.

IMPORTANT RULES:

1. Use ONLY the information provided below.

2. NEVER invent skills.

3. NEVER invent projects.

4. NEVER invent work experience.

5. NEVER invent certifications.

6. NEVER invent achievements.

7. NEVER add technologies that were not provided.

8. NEVER create fake numbers, percentages, companies,
   organizations or achievements.

9. Do not exaggerate experience.

10. Projects are NOT work experience.

11. Keep the professional summary concise and realistic.

12. Do not include contact information in the AI output.

13. Do not create sections called:
    - AI Generated Resume
    - Additional Information
    - New Achievement
    - CognifyAI Generated Content

14. Only include achievements marked as verified.

15. Organize technical skills into meaningful categories.

16. Preserve the user's actual project titles.

17. Improve wording of project descriptions without
    changing their meaning.

18. Do not change facts provided by the user.

19. If a section has no information, return an empty list.

20. Do not add unnecessary filler.

21. Use standard professional English.

22. Do not convert projects into job experience.

23. Do not create a skill merely because a technology
    appears related to another skill.

24. Only use the exact technical skills supplied by the user.

25. Resume name must not be changed.

26. Achievements must contain ONLY verified achievements.

27. Do not create achievement titles such as:
    - New CognifyAI Achievement
    - 100% Mastery
    - Achievement
    - Verified Achievement

28. Preserve the actual achievement topic/title supplied
    by the user.

29. Technical skills should be grouped into categories
    such as:
    - Programming
    - Web / Backend
    - Databases
    - ML / Data Science
    - Computer Vision
    - GenAI / LLM
    - Tools / Platforms
    - Other

    Only create a category if the supplied skills support it.

30. Do not add empty categories.

31. Do not include education in the generated technical
    skills, projects, experience or achievements.

32. Do not invent work experience when the user has none.

33. Do not invent certifications when the user has none.


============================================================
RESUME PROFILE
============================================================

{profile_data}


============================================================
TECHNICAL SKILLS
============================================================

{skill_data}


============================================================
EDUCATION
============================================================

{education_data}


============================================================
PROJECTS
============================================================

{project_data}


============================================================
EXPERIENCE
============================================================

{experience_data}


============================================================
CERTIFICATIONS
============================================================

{certification_data}


============================================================
VERIFIED ACHIEVEMENTS
============================================================

{achievement_data}


============================================================
GENERATE
============================================================

Generate:

1. Professional Summary

2. Technical Skills grouped by category

3. Projects

4. Experience

5. Certifications

6. Verified Achievements


Return ONLY the requested structured JSON.

Do not return Markdown.

Do not return explanations outside the JSON.
"""


    # ========================================================
    # GEMINI REQUEST
    # ========================================================

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AIResumeOutput,
        },
    )


    # ========================================================
    # VALIDATE AI RESPONSE
    # ========================================================

    return AIResumeOutput.model_validate_json(
        response.text
    )