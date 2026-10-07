from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


def safe_text(value):
    """
    Safely convert a value to text for ReportLab.
    """
    if value is None:
        return ""

    return escape(str(value))


def safe_url(value):
    """
    Safely convert a URL to text.
    """
    if value is None:
        return ""

    return str(value).strip()


def generate_resume_pdf(
    user,
    profile,
    education,
    ai_resume,
    achievements,
):
    """
    Generate a clean, professional and ATS-friendly resume PDF.

    Design rules:
    - Black text only
    - Standard Helvetica font
    - No decorative colors
    - Clean section headings
    - Simple ATS-friendly structure
    """

    buffer = BytesIO()

    full_name = profile.resume_name.strip()

    if not full_name:
        full_name = user.get_full_name().strip()

    if not full_name:
        full_name = user.username

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{full_name} Resume",
        author=full_name,
    )

    # --------------------------------------------------
    # COLORS
    # --------------------------------------------------
    #
    # IMPORTANT:
    # All visible resume text is BLACK.
    #

    BLACK = colors.black
    BORDER = colors.HexColor("#B0B0B0")
    WHITE = colors.white

    # --------------------------------------------------
    # STYLES
    # --------------------------------------------------

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=BLACK,
        alignment=TA_CENTER,
        spaceAfter=3,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=BLACK,
        alignment=TA_CENTER,
        spaceAfter=1,
    )

    section_style = ParagraphStyle(
        "ResumeSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceBefore=7,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    small_style = ParagraphStyle(
        "ResumeSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=1,
    )

    project_title_style = ParagraphStyle(
        "ProjectTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=1,
    )

    education_title_style = ParagraphStyle(
        "EducationTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=11,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=1,
    )

    skill_style = ParagraphStyle(
        "SkillText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10,
        textColor=BLACK,
        alignment=TA_LEFT,
    )

    skill_category_style = ParagraphStyle(
        "SkillCategory",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        textColor=BLACK,
        alignment=TA_LEFT,
    )

    # --------------------------------------------------
    # STORY
    # --------------------------------------------------

    story = []

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    story.append(
        Paragraph(
            safe_text(full_name).upper(),
            name_style,
        )
    )

    contact_parts = []

    if profile.phone:
        contact_parts.append(
            safe_text(profile.phone)
        )

    if user.email:
        contact_parts.append(
            safe_text(user.email)
        )

    if profile.location:
        contact_parts.append(
            safe_text(profile.location)
        )

    if contact_parts:
        story.append(
            Paragraph(
                " | ".join(contact_parts),
                contact_style,
            )
        )

    # --------------------------------------------------
    # SOCIAL LINKS
    # --------------------------------------------------
    #
    # The links remain clickable, but their visible
    # text is BLACK.
    #

    links = []

    if profile.linkedin_url:
        links.append(
            f'<link href="{safe_url(profile.linkedin_url)}">'
            f'<font color="#000000">LinkedIn</font>'
            f"</link>"
        )

    if profile.github_url:
        links.append(
            f'<link href="{safe_url(profile.github_url)}">'
            f'<font color="#000000">GitHub</font>'
            f"</link>"
        )

    if profile.leetcode_url:
        links.append(
            f'<link href="{safe_url(profile.leetcode_url)}">'
            f'<font color="#000000">LeetCode</font>'
            f"</link>"
        )

    if profile.portfolio_url:
        links.append(
            f'<link href="{safe_url(profile.portfolio_url)}">'
            f'<font color="#000000">Portfolio</font>'
            f"</link>"
        )

    if links:
        story.append(
            Paragraph(
                " | ".join(links),
                contact_style,
            )
        )

    story.append(
        Spacer(1, 3)
    )

    # --------------------------------------------------
    # PROFESSIONAL SUMMARY
    # --------------------------------------------------

    if ai_resume.professional_summary:

        story.append(
            Paragraph(
                "PROFESSIONAL SUMMARY",
                section_style,
            )
        )

        story.append(
            Paragraph(
                safe_text(
                    ai_resume.professional_summary
                ),
                body_style,
            )
        )

    # --------------------------------------------------
    # EDUCATION
    # --------------------------------------------------

    if education:

        story.append(
            Paragraph(
                "EDUCATION",
                section_style,
            )
        )

        for item in education:

            institution = safe_text(
                item.institution
            )

            degree = safe_text(
                item.degree
            )

            field = safe_text(
                item.field_of_study
            )

            cgpa = safe_text(
                item.percentage_or_cgpa
            )

            year_text = ""

            if item.start_year and item.end_year:
                year_text = (
                    f"{item.start_year} - "
                    f"{item.end_year}"
                )

            elif item.start_year:
                year_text = str(
                    item.start_year
                )

            elif item.end_year:
                year_text = str(
                    item.end_year
                )

            degree_text = degree

            if field:
                degree_text += (
                    f" in {field}"
                )

            education_header = (
                f"<b>{institution}</b>"
            )

            if year_text:
                education_header += (
                    f" &nbsp;&nbsp; "
                    f"{safe_text(year_text)}"
                )

            story.append(
                Paragraph(
                    education_header,
                    education_title_style,
                )
            )

            second_line = degree_text

            if cgpa:
                second_line += (
                    f" &nbsp; | &nbsp; "
                    f"<b>{cgpa}</b>"
                )

            story.append(
                Paragraph(
                    second_line,
                    body_style,
                )
            )

            if item.description:

                story.append(
                    Paragraph(
                        safe_text(
                            item.description
                        ),
                        small_style,
                    )
                )

            story.append(
                Spacer(1, 2)
            )

    # --------------------------------------------------
    # TECHNICAL SKILLS
    # --------------------------------------------------

    technical_skills = getattr(
        ai_resume,
        "technical_skills",
        []
    )

    if technical_skills:

        story.append(
            Paragraph(
                "TECHNICAL SKILLS",
                section_style,
            )
        )

        for category in technical_skills:

            category_name = safe_text(
                getattr(
                    category,
                    "category",
                    ""
                )
            )

            skills = getattr(
                category,
                "skills",
                []
            )

            if not skills:
                continue

            skill_text = ", ".join(
                safe_text(skill)
                for skill in skills
            )

            skill_table = Table(
                [
                    [
                        Paragraph(
                            category_name,
                            skill_category_style,
                        ),
                        Paragraph(
                            skill_text,
                            skill_style,
                        ),
                    ]
                ],
                colWidths=[
                    38 * mm,
                    141 * mm,
                ],
                hAlign="LEFT",
            )

            skill_table.setStyle(
                TableStyle(
                    [
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            2,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            2,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            2,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            2,
                        ),
                        (
                            "LINEBELOW",
                            (0, 0),
                            (-1, -1),
                            0.25,
                            BORDER,
                        ),
                    ]
                )
            )

            story.append(
                skill_table
            )

    # --------------------------------------------------
    # PROJECTS
    # --------------------------------------------------

    projects = getattr(
        ai_resume,
        "projects",
        []
    )

    if projects:

        story.append(
            Paragraph(
                "PROJECTS",
                section_style,
            )
        )

        for project in projects:

            title = safe_text(
                getattr(
                    project,
                    "title",
                    ""
                )
            )

            description = safe_text(
                getattr(
                    project,
                    "description",
                    ""
                )
            )

            technologies = getattr(
                project,
                "technologies",
                []
            )

            if isinstance(
                technologies,
                str
            ):
                technologies_text = (
                    technologies
                )
            else:
                technologies_text = ", ".join(
                    safe_text(item)
                    for item in technologies
                )

            project_block = []

            if title:
                project_block.append(
                    Paragraph(
                        title,
                        project_title_style,
                    )
                )

            if technologies_text:

                project_block.append(
                    Paragraph(
                        f"<b>Technologies:</b> "
                        f"{safe_text(technologies_text)}",
                        small_style,
                    )
                )

            if description:

                project_block.append(
                    Paragraph(
                        description,
                        body_style,
                    )
                )

            story.append(
                KeepTogether(
                    project_block
                )
            )

            story.append(
                Spacer(1, 3)
            )

    # --------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------

    experience = getattr(
        ai_resume,
        "experience",
        []
    )

    if experience:

        story.append(
            Paragraph(
                "EXPERIENCE",
                section_style,
            )
        )

        for item in experience:

            job_title = safe_text(
                getattr(
                    item,
                    "job_title",
                    ""
                )
            )

            company = safe_text(
                getattr(
                    item,
                    "company",
                    ""
                )
            )

            location = safe_text(
                getattr(
                    item,
                    "location",
                    ""
                )
            )

            description = safe_text(
                getattr(
                    item,
                    "description",
                    ""
                )
            )

            heading = (
                f"<b>{job_title}</b>"
            )

            if company:
                heading += (
                    f" | {company}"
                )

            if location:
                heading += (
                    f" | {location}"
                )

            story.append(
                Paragraph(
                    heading,
                    project_title_style,
                )
            )

            if description:

                story.append(
                    Paragraph(
                        description,
                        body_style,
                    )
                )

            story.append(
                Spacer(1, 2)
            )

    # --------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------

    certifications = getattr(
        ai_resume,
        "certifications",
        []
    )

    if certifications:

        story.append(
            Paragraph(
                "CERTIFICATIONS",
                section_style,
            )
        )

        for item in certifications:

            name = safe_text(
                getattr(
                    item,
                    "name",
                    ""
                )
            )

            organization = safe_text(
                getattr(
                    item,
                    "issuing_organization",
                    ""
                )
            )

            credential_id = safe_text(
                getattr(
                    item,
                    "credential_id",
                    ""
                )
            )

            certification_text = (
                f"<b>{name}</b>"
            )

            if organization:
                certification_text += (
                    f" | {organization}"
                )

            if credential_id:
                certification_text += (
                    f" | Credential ID: "
                    f"{credential_id}"
                )

            story.append(
                Paragraph(
                    certification_text,
                    body_style,
                )
            )

    # --------------------------------------------------
    # VERIFIED ACHIEVEMENTS
    # --------------------------------------------------

    if achievements:

        story.append(
            Paragraph(
                "ACHIEVEMENTS",
                section_style,
            )
        )

        for achievement in achievements:

            title = safe_text(
                achievement.title
            )

            description = safe_text(
                achievement.description
            )

            if description:

                achievement_text = (
                    f"<b>{title}</b> — "
                    f"{description}"
                )

            else:

                achievement_text = (
                    f"<b>{title}</b>"
                )

            story.append(
                Paragraph(
                    achievement_text,
                    body_style,
                )
            )

    # --------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------

    document.build(story)

    buffer.seek(0)

    return buffer