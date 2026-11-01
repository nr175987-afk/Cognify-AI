import os
import json
import re

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from googleapiclient.discovery import build

from .ai_service import generate_ai_response


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Allow Django to start even if the Gemini key is missing.
client = genai.Client(api_key=API_KEY) if API_KEY else None

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ============================================================
# SHARED AI GENERATION HELPER
# ============================================================

def _generate_text(
    prompt,
    response_schema=None,
    use_cache=True,
    task="assessment_generation",
):
    """
    Generate text through the shared AI service.

    Supports caching, Gemini, Ollama fallback,
    and structured Pydantic responses.
    """

    result = generate_ai_response(
        task=task,
        prompt=prompt,
        schema=response_schema,
        use_cache=use_cache,
    )

    if response_schema is not None:
        return result.model_dump_json()

    return result


# ============================================================
# QUESTION MODELS
# ============================================================

class Question(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    explanation: str


class QuestionSet(BaseModel):
    questions: list[Question]


# ============================================================
# GENERATE ASSESSMENT QUESTIONS
# ============================================================

def generate_questions(subject, topic, difficulty, number_of_questions):

    if not 1 <= number_of_questions <= 20:
        raise ValueError("Choose between 1 and 20 questions.")

    prompt = f"""
You are CognifyAI, an expert educational assessment generator.

Generate exactly {number_of_questions} multiple-choice questions.

SUBJECT: {subject}
TOPIC: {topic}
DIFFICULTY: {difficulty}

REQUIREMENTS:

1. Every question must directly test the requested topic.
2. Match the requested difficulty.
3. Each question must have exactly four options.
4. There must be exactly one correct option.
5. correct_answer must be one uppercase letter: A, B, C, or D.
6. Do not repeat questions or use ambiguous wording.
7. Test understanding and application, not only memorization.
8. Give a short, accurate educational explanation for every answer.
9. Keep all questions appropriate for a college student.
10. Ensure numerical answers and calculations are accurate.
11. Return only data matching the requested JSON schema.
"""

    result = QuestionSet.model_validate_json(
        _generate_text(
            prompt,
            response_schema=QuestionSet,
        )
    )

    if len(result.questions) != number_of_questions:
        raise RuntimeError(
            f"AI returned {len(result.questions)} questions; "
            f"{number_of_questions} were requested."
        )

    for question in result.questions:

        question.correct_answer = (
            question.correct_answer.strip().upper()
        )

        if question.correct_answer not in {"A", "B", "C", "D"}:
            raise RuntimeError(
                "AI returned an invalid correct_answer. "
                "Expected A, B, C, or D."
            )

    return result.questions


# ============================================================
# LEARNING PLAN MODELS
# ============================================================

class LearningLevel(BaseModel):
    status: str
    recommended_content: list[str]


class RealWorldProblem(BaseModel):
    title: str
    description: str
    difficulty: str


class AdaptiveLearningPlan(BaseModel):
    topic: str
    current_score: float
    current_level: str
    next_level: str
    learning_summary: str
    priority_concepts: list[str]
    recommended_mode: str
    easy: LearningLevel
    medium: LearningLevel
    advanced: LearningLevel
    real_world_problem: RealWorldProblem
    next_action: str


# ============================================================
# GENERATE PERSONALIZED LEARNING PLAN
# ============================================================

def generate_learning_plan(student_data):

    if isinstance(student_data, str):
        student_information = student_data

    else:
        student_information = json.dumps(
            student_data,
            indent=2,
            default=str,
        )

    prompt = f"""
You are CognifyAI, an intelligent adaptive learning assistant
that creates personalized learning paths for college students.

Your responsibility is to analyze actual student performance
and recommend the most appropriate next learning activities.

============================================================
STUDENT PERFORMANCE DATA
============================================================

{student_information}


============================================================
1. PERFORMANCE ANALYSIS RULES
============================================================

Analyze the student's:

- Overall average score.
- Individual topic scores.
- Strong topics.
- Weak topics.
- Number of assessment attempts.
- Difficulty-wise performance.
- Learning trend.
- Score improvement.

Base every recommendation on the supplied information.

Never invent assessment scores, weak topics, mastered concepts,
or learning achievements.

Do not confuse difficulty-wise performance with topic-wise
performance.


============================================================
2. ADAPTIVE DIFFICULTY LEVELS
============================================================

Determine the current level using these exact score ranges:

- Below 40%: Beginner
- 40% to below 60%: Easy
- 60% to below 80%: Medium
- 80% to below 100%: Advanced
- Exactly 100%: Expert / Mastery

The current level must reflect the student's demonstrated
performance.

Do not recommend Beginner-level learning to a student who
has already demonstrated strong performance.


============================================================
3. TOPIC-BASED RECOMMENDATIONS
============================================================

Analyze each topic separately.

For topics below 60%:
- Prioritize the concepts the student struggles with.
- Recommend clear explanations and guided practice.
- Strengthen prerequisite knowledge.
- Gradually increase difficulty.

For topics scoring 60% to below 80%:
- Strengthen conceptual understanding.
- Recommend application-based questions.
- Include intermediate exercises.
- Prepare the student for advanced concepts.

For topics scoring 80% to below 100%:
- Treat the topic as a strong area.
- Avoid unnecessary beginner-level repetition.
- Recommend advanced applications.
- Include challenging exercises and analytical problems.
- Introduce deeper concepts and practical implementations.

For topics scoring exactly 100%:
- Treat the topic as demonstrated mastery.
- Recommend expert-level applications.
- Include complex projects and interview-level challenges.
- Introduce related advanced concepts.
- Never tell the student to stop learning.

If weak topics are provided, prioritize them.

If there are no weak topics, do not manufacture weaknesses.
Instead, recommend advanced applications and related concepts
that can extend the student's knowledge.


============================================================
4. DIFFICULTY-WISE PERFORMANCE
============================================================

Use difficulty_analysis when deciding what to recommend.

If the student performs well in Easy assessments:
- Do not repeatedly recommend only basic content.
- Introduce Medium-level learning activities.

If the student performs well in Medium assessments:
- Progress towards Advanced content.

If the student performs well in Hard assessments:
- Recommend more challenging applications.
- Include complex analytical problems and projects.

If the student struggles with a particular difficulty:
- Recommend targeted practice at that level.
- Explain what needs improvement.

Do not assume that a student has mastered a difficulty level
unless the supplied assessment data supports that conclusion.


============================================================
5. LEARNING PROGRESSION
============================================================

Follow this progression:

Beginner → Easy → Medium → Advanced → Expert

However, do not automatically restart the student at Beginner.

Use actual assessment performance to determine the appropriate
starting point.

A strong student should continue progressing rather than
repeating content they have already demonstrated.


============================================================
6. RECOMMENDATION CONTENT
============================================================

Provide useful recommendations for:

- Study notes and explanations.
- Practice questions.
- Advanced exercises.
- Video learning.
- Real-world problem solving.
- Projects and practical implementation.
- Interview-level questions where appropriate.

Every recommendation must:

1. Relate directly to the student's actual topic.
2. Match the student's demonstrated ability.
3. Explain what the student should learn or practise.
4. Provide a meaningful next step.
5. Avoid unnecessary repetition.


============================================================
7. PERSONALIZATION EXAMPLE
============================================================

If the student has:

- Overall score: 93.3%
- Linear Regression score: 93.3%
- Three assessment attempts.
- No weak topics.
- Easy average: 90%.
- Hard average: 100%.

Then:

- Current level should be Advanced.
- The student should not be sent back to Beginner.
- Recommend advanced Linear Regression applications.
- Include model diagnostics, regularization, feature selection,
  optimization, and practical projects where appropriate.
- Recommend challenging problems and interview-level exercises.
- Do not invent weak concepts or claim the student failed topics.

This is an example of how to interpret performance, not a
replacement for the actual supplied student data.


============================================================
8. REQUIRED OUTPUT
============================================================

Return data matching the AdaptiveLearningPlan schema.

Field requirements:

topic:
The main topic or learning focus selected from the supplied data.

current_score:
The actual overall score used for the learning plan.

current_level:
The student's current adaptive difficulty level.

next_level:
The next appropriate learning level.

learning_summary:
A personalized explanation of the student's performance.

priority_concepts:
A list of specific concepts that should receive attention next.
Prioritize weak concepts when they exist. Otherwise, recommend
meaningful advanced concepts.

recommended_mode:
The most suitable learning approach for the student.

easy:
Provide suitable content for the Easy level.
If the student has already demonstrated strong performance,
mark this level as lower priority rather than recommending
unnecessary revision.

medium:
Provide suitable content for the Medium level.
Indicate whether the student should revise or progress through
this level.

advanced:
Provide suitable content for the Advanced level.
Prioritize this level for students with strong performance.

real_world_problem:
Create one realistic problem related to the student's topic.
Its difficulty must match the student's demonstrated ability.

next_action:
Give one clear and actionable next step.

IMPORTANT:

- Do not fabricate performance information.
- Do not contradict the supplied scores.
- Do not recommend easier content unnecessarily.
- Do not claim mastery of topics without evidence.
- Never say that learning is complete.
- Return structured data only.
- Do not include Markdown outside the required structure.
"""

    return AdaptiveLearningPlan.model_validate_json(
        _generate_text(
            prompt,
            response_schema=AdaptiveLearningPlan,
            use_cache=False,
            task="personalized_learning_plan",
        )
    )


# ============================================================
# GENERATE ADAPTIVE NOTES
# ============================================================

def generate_adaptive_notes(topic, level, score):
    """
    Generate detailed study notes personalized to the learner's level.
    """

    prompt = f"""
You are CognifyAI, an expert university lecturer and technical author.

Create comprehensive, accurate, textbook-quality study notes.

TOPIC: {topic}
STUDENT ACCURACY: {score}%
RECOMMENDED LEVEL: {level}

IMPORTANT:
The title, explanations, examples, and difficulty must match
the requested level. Never call Expert notes beginner-friendly.

DIFFICULTY GUIDELINES

Beginner:
- Assume no prior knowledge.
- Explain terminology from scratch.
- Use simple analogies and fully worked examples.

Easy:
- Strengthen the fundamentals.
- Explain formulas and demonstrate their use.
- Include straightforward practice examples.

Medium:
- Explain intermediate theory and applications.
- Include multi-step examples, assumptions, and common mistakes.

Hard:
- Cover advanced theory, derivations, edge cases, and diagnostics.
- Include challenging numerical or analytical examples where relevant.

Advanced or Expert:
- Focus on rigorous theory, deeper mathematical reasoning,
  derivations, parameter interpretation, assumptions, and limitations.
- Explain when methods work, why they work, and when they fail.
- Discuss diagnostics, optimization, edge cases, trade-offs,
  computational considerations, and real-world implications.
- Include advanced worked examples and interview-level insights.
- Avoid unnecessary repetition of elementary definitions.

DEPTH REQUIREMENTS

Aim for 1,800–2,500 words for a substantial topic.
For a narrower topic, use the length needed to explain it properly.

Do not pad the response with repetitive filler.

Use these sections where relevant:

# {topic}

## Learning Objectives
List measurable things the learner should understand or be able to do.

## Prerequisites
Explain the knowledge required to understand this topic.

## Introduction and Motivation
Explain the purpose of the topic, the problem it solves,
and why it matters.

## Core Concepts
Explain each major concept in detail, including terminology
and the relationship between the concepts.

## Mathematical Formulation
Present relevant equations, define every symbol, and explain
what each term means.

## Step-by-Step Working
Explain how the method or concept works in a logical sequence.
Include derivations where appropriate.

## Detailed Worked Examples
Provide at least two meaningful examples when the topic supports them.
Show the data, formula, substitutions, intermediate calculations,
final result, and interpretation.

## Advanced Concepts
Cover additional theory, edge cases, diagnostics, optimization,
or alternative approaches appropriate to the requested level.

## Assumptions and Limitations
Explain the relevant assumptions and what can happen when
they are violated.

## Advantages and Disadvantages
Explain meaningful strengths and weaknesses.

## Common Mistakes
Identify likely misunderstandings and explain how to avoid them.

## Real-World Applications
Give concrete applications and explain how the topic is used.

## Quick Revision
Summarize the key concepts and formulas.

## Practice Questions
Provide five questions appropriate to the requested difficulty.

## Answers and Explanations
Give correct answers and clear explanations for those questions.

## What to Learn Next
Recommend relevant follow-on concepts in a logical learning sequence.

Adapt the structure to the subject. Do not include irrelevant
sections simply to satisfy a template.

MATHEMATICAL FORMATTING

Use valid LaTeX delimiters.

Inline:
The estimated response is $\\hat{{y}} = \\beta_0 + \\beta_1 x$.

Display:
$$
\\hat{{y}} = \\beta_0 + \\beta_1 x
$$

- Put display delimiters on separate lines.
- Use correct subscripts, superscripts, Greek letters, fractions,
  summations, matrices, and mathematical operators where relevant.
- Explain every important symbol immediately after introducing
  the equation.
- Never use square brackets as equation delimiters.
- Never leave a formula blank or omit its mathematical symbols.
- Do not place mathematical equations inside code fences.
- Use literal Markdown table pipes, without preceding backslashes.
- Use normal Markdown headings, numbered lists, and bullet lists.

NUMERICAL ACCURACY

- Independently verify each calculation before writing the result.
- Show intermediate steps for important calculations.
- Check signs, substitutions, units, rounding, and final answers.
- Do not invent regression coefficients, R-squared values, RMSE,
  p-values, or experimental findings.
- Clearly identify hypothetical data as illustrative.
- Do not claim that a result was calculated from data unless
  the calculation actually supports it.
- If a problem has insufficient data, explain what is missing.
- If a model's parameters cannot be uniquely determined,
  explain the identifiability problem.
- Do not claim that assumptions are satisfied without evidence.

QUALITY CHECK

Before returning the notes, verify:
1. The title matches the requested difficulty.
2. The notes provide sufficient depth for a college student.
3. Important concepts are explained, not merely listed.
4. Equations and symbol definitions are complete.
5. Numerical examples are internally consistent.
6. Markdown tables and mathematical delimiters are valid.
7. Practice questions have answers that match the questions.
8. The conclusion and revision section reflect the material taught.

Return only the finished Markdown notes.
"""

    generated_text = _generate_text(prompt)

    if not generated_text or not generated_text.strip():
        raise ValueError("The AI provider returned empty study notes.")

    return generated_text.strip()


# ============================================================
# GENERATE ADAPTIVE CONTENT
# ============================================================

def generate_adaptive_content(topic, content_type, difficulty):
    """
    Generate adaptive learning content.

    Returns raw Markdown. HTML conversion is handled by views.py.
    """

    topic = str(topic).strip()
    content_type = str(content_type).strip().lower()
    difficulty = str(difficulty).strip().title()

    if not topic:
        raise ValueError("A topic is required.")

    allowed_types = {"notes", "questions", "realworld"}

    if content_type not in allowed_types:
        raise ValueError(
            f"Unsupported content type: {content_type}"
        )

    allowed_difficulties = {
        "Beginner",
        "Easy",
        "Medium",
        "Hard",
        "Advanced",
        "Expert",
    }

    if difficulty not in allowed_difficulties:
        difficulty = "Medium"

    difficulty_instructions = {

        "Beginner": """
Assume no prior knowledge. Define every important term.
Explain concepts step by step using simple examples and
fully worked calculations. Avoid unexplained jargon.
""",

        "Easy": """
Focus on fundamentals, straightforward applications,
clear formula explanations, and simple worked examples.
""",

        "Medium": """
Provide intermediate theory, multi-step examples,
formula applications, common mistakes, and interpretation.
""",

        "Hard": """
Include advanced theory, derivations, challenging examples,
assumptions, limitations, diagnostics, and edge cases.
""",

        "Advanced": """
Emphasize deeper theory, mathematical reasoning, derivations,
evaluation methods, limitations, optimization, and applications.
""",

        "Expert": """
Produce genuinely expert-level material for a college student
who already understands the fundamentals.

Focus on rigorous reasoning, mathematical derivations,
assumptions and their implications, parameter interpretation,
diagnostics, edge cases, limitations, trade-offs, optimization,
computational considerations, and advanced applications.

Explain why methods work, when they work, and when they fail.
Include technically meaningful worked examples and practical
implications. Avoid generic introductory material and repetition.

Never title the content beginner-friendly.
""",
    }

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    if content_type == "notes":

        content_instructions = f"""
Create comprehensive, textbook-quality study notes on {topic}.

TARGET LENGTH:
Aim for approximately 1,800–2,500 words when the topic supports
that depth. Do not add repetitive filler merely to reach the target.

REQUIRED CONTENT:

1. A descriptive title matching the requested difficulty.
2. Learning objectives.
3. Prerequisites and terminology.
4. Introduction and motivation.
5. Detailed explanations of the core concepts.
6. Mathematical formulation and symbol definitions, if relevant.
7. Step-by-step working and derivations, if relevant.
8. At least two substantial worked examples when appropriate.
9. Intermediate calculations and interpretation of results.
10. Assumptions and conditions of validity.
11. Evaluation metrics and diagnostics, where applicable.
12. Advantages, limitations, and common mistakes.
13. Practical applications and a realistic illustrative case study.
14. Advanced concepts appropriate to the requested level.
15. A quick-revision section containing important concepts and formulas.
16. Five revision questions with answers and explanations.
17. A logical list of concepts to learn next.

Use headings and subheadings to organize the notes.
Explain each major concept in paragraphs; do not merely list keywords.
Include tables when they make comparisons easier to understand.
Include code only when useful, and explain its important steps.

MATHEMATICAL NOTATION:

- Inline mathematics: $y = mx + c$
- Display mathematics on separate lines:

  $$
  y = \\beta_0 + \\beta_1 x + \\epsilon
  $$

Use valid LaTeX for the actual subject.
Never wrap equations in square brackets.
Never leave symbols or variable definitions blank.
Define variables, subscripts, and parameters explicitly.
Use literal Markdown table pipes, not escaped pipes.

NUMERICAL VALIDATION:

Verify every worked calculation and final result.
Do not invent coefficients, evaluation scores, or measurements.
Distinguish hypothetical examples from actual observations.
When data is insufficient or parameters are not identifiable,
explain the limitation instead of fabricating a result.

DIFFICULTY:
{difficulty_instructions[difficulty]}

Return only the completed Markdown notes.
"""

    # --------------------------------------------------------
    # PRACTICE QUESTIONS
    # --------------------------------------------------------

    elif content_type == "questions":

        content_instructions = f"""
Create exactly 12 well-designed practice questions about {topic}.

Match all questions to the requested difficulty:

{difficulty_instructions[difficulty]}

Use a suitable mixture of conceptual, analytical, application-based,
and numerical questions where relevant.

STRUCTURE:

# Practice Questions: {topic}

## Questions

Number the questions from 1 to 12.

Include all necessary data, assumptions, units, and precision
requirements for every numerical problem.

Do not put answers immediately after the individual questions.

## Answer Key and Explanations

Provide all 12 answers after the questions.
Explain the reasoning and show verified calculations when relevant.
Ensure that each question and answer agree and are unambiguous.

Use valid LaTeX and ordinary Markdown.
Return only the completed Markdown.
"""

    # --------------------------------------------------------
    # REAL-WORLD PROBLEMS
    # --------------------------------------------------------

    else:

        content_instructions = f"""
Create exactly three substantial real-world challenges about {topic}.

Match the complexity to the requested difficulty:

{difficulty_instructions[difficulty]}

For each challenge, include:

1. A descriptive title.
2. A realistic scenario and the problem to solve.
3. All required illustrative data, constraints, and assumptions.
4. The concepts and skills required.
5. Clearly numbered tasks.
6. Expected deliverables and evaluation criteria.
7. Hints that guide the learner without giving away the full solution.
8. Relevant mathematical formulations, where applicable.
9. Potential edge cases or limitations to consider.

Label hypothetical data as illustrative.
Do not invent research results or claim illustrative outcomes are real.

Use valid LaTeX and ordinary Markdown.
Return only the completed Markdown.
"""

    # --------------------------------------------------------
    # FINAL PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are CognifyAI, an experienced university lecturer,
technical author, and subject-matter expert.

TOPIC:
{topic}

REQUESTED DIFFICULTY:
{difficulty}

CONTENT TYPE:
{content_type}

DIFFICULTY REQUIREMENTS:
{difficulty_instructions[difficulty]}

CONTENT REQUIREMENTS:
{content_instructions}

FINAL VALIDATION:

- Match the requested topic and difficulty.
- Explain concepts in sufficient depth.
- Check every formula and numerical calculation.
- Ensure every variable definition is complete.
- Use valid Markdown and LaTeX delimiters.
- Never use square brackets as equation delimiters.
- Never escape Markdown table pipes.
- Do not fabricate results or claim unperformed calculations.
- Return only the requested content.
"""

    generated_text = generate_ai_response(
        task=f"adaptive_{content_type}",
        prompt=prompt,
        use_cache=True,
    )

    if not generated_text or not generated_text.strip():
        raise ValueError(
            "The AI provider returned empty learning content."
        )

    return generated_text.strip()


# ============================================================
# SEARCH RELEVANT ADAPTIVE VIDEOS
# ============================================================

def search_adaptive_videos(
    topic,
    difficulty,
    max_results=5,
    subject=None,
):

    if not YOUTUBE_API_KEY:
        raise ValueError(
            "YOUTUBE_API_KEY is not configured in .env"
        )

    topic = (topic or "").strip()
    subject = (subject or "").strip()

    if not topic:
        return []

    # --------------------------------------------------------
    # DIFFICULTY SEARCH TERMS
    # --------------------------------------------------------

    level_words = {
        "Beginner": "basics tutorial for beginners",
        "Easy": "simple explanation tutorial",
        "Medium": "intermediate tutorial examples",
        "Hard": "challenging advanced tutorial",
        "Advanced": "advanced tutorial deep dive",
        "Expert": "expert deep dive advanced concepts",
    }

    level_text = level_words.get(
        difficulty,
        "tutorial explanation",
    )

    # --------------------------------------------------------
    # SEARCH QUERY
    # --------------------------------------------------------

    if subject:
        query = f'"{subject}" "{topic}" {level_text}'
    else:
        query = f'"{topic}" {level_text}'

    print("YouTube Search Query:", query)

    # --------------------------------------------------------
    # YOUTUBE API
    # --------------------------------------------------------

    youtube = build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY,
    )

    response = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=min(max(int(max_results) * 5, 10), 50),
        order="relevance",
        relevanceLanguage="en",
        safeSearch="strict",
    ).execute()

    # --------------------------------------------------------
    # TOPIC WORDS
    # --------------------------------------------------------

    topic_words = set(
        re.findall(r"[a-zA-Z0-9]+", topic.lower())
    )

    stop_words = {
        "the", "a", "an", "and", "or", "of", "to", "for",
        "in", "on", "with", "using", "tutorial", "basics",
        "basic", "introduction",
    }

    topic_words = {
        word for word in topic_words
        if word not in stop_words
    }

    subject_words = set(
        re.findall(r"[a-zA-Z0-9]+", subject.lower())
    )

    subject_words = {
        word for word in subject_words
        if word not in stop_words and len(word) > 1
    }

    videos = []
    seen_ids = set()

    # --------------------------------------------------------
    # PROCESS RESULTS
    # --------------------------------------------------------

    for item in response.get("items", []):

        video_id = (item.get("id") or {}).get("videoId")

        if not video_id or video_id in seen_ids:
            continue

        snippet = item.get("snippet", {})

        title = snippet.get("title", "")
        description = snippet.get("description", "")

        title_lower = title.lower()
        description_lower = description.lower()

        # Topic relevance check
        if topic_words:

            matching_words = 0

            for word in topic_words:

                if re.search(
                    r"\b" + re.escape(word) + r"\b",
                    title_lower,
                ):
                    matching_words += 1

            required_words = max(
                1,
                int(len(topic_words) * 0.6),
            )

            if matching_words < required_words:
                continue

        # Subject relevance check
        if subject_words:

            subject_match = False

            for word in subject_words:

                if (
                    re.search(
                        r"\b" + re.escape(word) + r"\b",
                        title_lower,
                    )
                    or re.search(
                        r"\b" + re.escape(word) + r"\b",
                        description_lower,
                    )
                ):
                    subject_match = True
                    break

            if not subject_match:
                continue

        # Thumbnail selection
        thumbnails = snippet.get("thumbnails", {})

        thumbnail = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )

        videos.append({
            "title": title,
            "description": description,
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": thumbnail.get("url", ""),
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

        seen_ids.add(video_id)

        if len(videos) >= max_results:
            break

    return videos