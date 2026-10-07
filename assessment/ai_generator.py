import os
import json
import re

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from googleapiclient.discovery import build


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not configured in .env"
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=API_KEY
)

MODEL_NAME = "gemini-2.5-flash"


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

def generate_questions(
    subject,
    topic,
    difficulty,
    number_of_questions
):

    prompt = f"""
You are CognifyAI, an expert educational assessment generator.

Generate exactly {number_of_questions} multiple-choice questions.

Subject:
{subject}

Topic:
{topic}

Difficulty:
{difficulty}

IMPORTANT REQUIREMENTS:

1. Questions must be directly related to the given topic.
2. Questions must match the requested difficulty.
3. Each question must have exactly four options.
4. Only one option must be correct.
5. The correct answer must be represented by A, B, C, or D.
6. Do not create duplicate questions.
7. Avoid ambiguous questions.
8. Questions should test understanding, not only memorization.
9. Provide a short educational explanation for every answer.
10. Do not include information outside the requested topic.
11. Use clear language suitable for a college student.
12. Make the questions meaningful and educational.

Return only structured data.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": QuestionSet,
        },
    )

    result = QuestionSet.model_validate_json(
        response.text
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
            default=str
        )

    prompt = f"""
You are CognifyAI, an adaptive AI learning assistant.

Your job is to analyze a student's learning performance and
decide what the student should learn next.

STUDENT PERFORMANCE DATA:

{student_information}

============================================================
ADAPTIVE LEARNING RULES
============================================================

1. If the student's score is below 60%:
   - Current level = Beginner
   - Recommend easy/basic learning content.
   - Focus strongly on fundamentals.

2. If the student's score is between 60% and 79%:
   - Current level = Intermediate
   - Recommend medium-level content.
   - Strengthen concepts.
   - Introduce application-based problems.

3. If the student's score is between 80% and 99%:
   - Current level = Advanced
   - Recommend advanced concepts.
   - Include difficult questions.
   - Include real-world applications.

4. If the student's score is exactly 100%:
   - NEVER say learning is complete.
   - Current level = Mastery.
   - Recommend expert-level concepts.
   - Recommend advanced real-world problems.
   - Recommend interview-level challenges.

5. If a student successfully completes Easy content:
   Recommend Medium content.

6. If a student successfully completes Medium content:
   Recommend Advanced content.

7. If a student successfully completes Advanced content:
   Recommend Expert/Mastery content.

8. Never repeatedly recommend concepts that the student has
   already mastered.

9. Recommendations must be specific to the student's topics.

10. Provide multiple learning choices:
   - Notes
   - Videos
   - Practice questions
   - Real-world problems

11. Video recommendations must match the student's level.

12. Practice questions must match the student's level.

13. Real-world problems should resemble situations that
    developers or professionals actually encounter.

14. If the student performs very well, increase the difficulty
    instead of stopping their learning.

15. The goal is continuous improvement and mastery.

============================================================
OUTPUT REQUIREMENTS
============================================================

Return structured data only.
Do not return Markdown.
Do not return explanations outside the requested structure.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AdaptiveLearningPlan,
        },
    )

    result = AdaptiveLearningPlan.model_validate_json(
        response.text
    )

    return result


# ============================================================
# GENERATE ADAPTIVE NOTES
# ============================================================

def generate_adaptive_notes(
    topic,
    level,
    score
):

    prompt = f"""
You are CognifyAI, an adaptive learning assistant.

Create personalized learning notes for a college student.

Topic:
{topic}

Student accuracy:
{score}%

Recommended learning level:
{level}

============================================================
LEVEL RULES
============================================================

BEGINNER:
- Assume the student has very little knowledge.
- Start from fundamentals.
- Explain terminology simply.
- Use very simple examples.
- Avoid unnecessary advanced concepts.

EASY:
- Explain fundamentals clearly.
- Include simple examples.
- Add small practice examples.
- Focus on building confidence.

MEDIUM:
- Assume the student understands the basics.
- Explain intermediate concepts.
- Include practical examples.
- Include common mistakes.

HARD:
- Focus on advanced concepts.
- Include challenging examples.
- Explain edge cases.
- Include interview-style concepts.

ADVANCED:
- Do NOT repeat basic explanations unnecessarily.
- Teach advanced concepts.
- Include complex examples.
- Include optimization and edge cases.
- Include real-world applications.
- Include interview-level insights.

============================================================
IMPORTANT
============================================================

The student should feel that the content was specifically
created for their current ability.

Do not give exactly the same explanation to every level.

Structure the response as:

# {topic}

## What You Should Learn

## Core Concepts

## Example

## Common Mistakes

## Practice Yourself

## Real-World Application

## What To Learn Next

Keep the explanation practical, clear and engaging.

Return only Markdown content.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# ============================================================
# GENERATE ADAPTIVE CONTENT
# ============================================================

def generate_adaptive_content(
    topic,
    content_type,
    difficulty
):

    # ========================================================
    # PRACTICE QUESTIONS
    # ========================================================

    if content_type == "questions":

        prompt = f"""
You are CognifyAI, an adaptive learning assistant.

Create a practice test for a college student.

Topic:
{topic}

Student Level:
{difficulty}

IMPORTANT:

Generate EXACTLY 12 multiple-choice questions.

Requirements:

1. Create exactly 12 questions.
2. Each question must have exactly 4 options.
3. Options must be A, B, C and D.
4. Only one option must be correct.
5. Questions must test understanding.
6. Avoid duplicate questions.
7. Cover different concepts from the topic.
8. Include application-based questions where appropriate.
9. Do not reveal the answer immediately after a question.
10. Do not place the answer beside the question.
11. Put ALL answers and explanations ONLY at the very end.
12. Keep the questions directly related to {topic}.
13. Do not include questions from unrelated topics.

FORMAT:

# Practice Test

## Question 1

Question text

A. option
B. option
C. option
D. option

Continue until Question 12.

Then create:

# Answer Key & Explanations

1. **Answer: X**

Explanation...

Continue until Question 12.

IMPORTANT:
The Answer Key must appear ONLY after all 12 questions.

Return only Markdown.
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    # ========================================================
    # REAL WORLD PROBLEMS
    # ========================================================

    if content_type == "realworld":

        prompt = f"""
You are CognifyAI, an adaptive learning assistant.

Create practical programming/data-science real-world
challenges for a college student.

Topic:
{topic}

Student Level:
{difficulty}

Generate EXACTLY 3 different real-world problems.

Each problem must be practical and related directly to
{topic}.

Do NOT provide the complete solution.

For each problem use this structure:

# Real-World Challenges

## Challenge 1 — [Title]

### Problem

Clearly explain what needs to be solved.

### Real-World Scenario

Describe a realistic situation where this problem is useful.

### Requirements

Give a numbered list of what the student must implement.

### Input

Explain what input/data the student should use.

### Expected Output

Explain what the student should produce.

### Skills Tested

List the concepts being tested.

### Difficulty

Explain why this matches the student's level.

### 🧑‍💻 Workspace

Tell the student what they should implement in the workspace.

---

Repeat the same structure for Challenge 2 and Challenge 3.

IMPORTANT:

1. Generate exactly 3 challenges.
2. Each challenge must be different.
3. Do not give complete solutions.
4. Do not give code solutions.
5. Make them realistic.
6. Make them suitable for the student's level.
7. Problems should encourage implementation.
8. Keep them directly related to {topic}.

Return only Markdown.
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    # ========================================================
    # NOTES
    # ========================================================

    if content_type == "notes":

        prompt = f"""
You are CognifyAI, an adaptive learning assistant.

Create book-style study notes for a college student.

Topic:
{topic}

Student Level:
{difficulty}

The content should feel like a small textbook chapter.

Structure:

# {topic}

## 1. Learning Objective

Explain what the student will learn.

## 2. Introduction

Give a clear introduction.

## 3. Core Concepts

Explain the important concepts step by step.

## 4. Important Terminology

Explain important terms.

## 5. Mathematical / Technical Explanation

Explain formulas, algorithms or technical details
where relevant.

## 6. Worked Example

Give a complete example and explain it step by step.

## 7. Common Mistakes

List common mistakes.

## 8. Real-World Applications

Explain practical applications.

## 9. Quick Revision

Give important points for revision.

## 10. Practice Yourself

Give a few questions without answers.

## 11. What To Learn Next

Recommend the next concepts according to the student's level.

Make it easy to read like study material.

Do not unnecessarily repeat basic concepts for advanced students.

Return only Markdown.
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    # ========================================================
    # DEFAULT
    # ========================================================

    prompt = f"""
Create personalized learning content.

Topic: {topic}
Difficulty: {difficulty}
Content Type: {content_type}

Keep it educational, practical and directly related
to the topic.

Return only Markdown.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# ============================================================
# SEARCH RELEVANT ADAPTIVE VIDEOS
# ============================================================

def search_adaptive_videos(
    topic,
    difficulty,
    max_results=5,
    subject=None
):

    if not YOUTUBE_API_KEY:
        raise ValueError(
            "YOUTUBE_API_KEY is not configured in .env"
        )

    topic = topic.strip()
    subject = subject.strip() if subject else ""

    topic_lower = topic.lower()
    subject_lower = subject.lower()

    # --------------------------------------------------------
    # Difficulty search terms
    # --------------------------------------------------------

    level_words = {

        "Beginner":
            "basics tutorial beginners",

        "Easy":
            "simple explanation tutorial",

        "Medium":
            "intermediate tutorial examples",

        "Advanced":
            "advanced tutorial examples",

        "Expert":
            "advanced deep dive tutorial"
    }

    level_text = level_words.get(
        difficulty,
        "tutorial explanation"
    )

    # --------------------------------------------------------
    # Search query
    # --------------------------------------------------------

    if subject:
        query = (
            f'"{subject}" "{topic}" '
            f'{level_text}'
        )
    else:
        query = (
            f'"{topic}" '
            f'{level_text}'
        )

    print("YouTube Search Query:", query)

    # --------------------------------------------------------
    # YouTube API
    # --------------------------------------------------------

    youtube = build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY
    )

    response = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=25,
        order="relevance",
        relevanceLanguage="en",
        safeSearch="strict"
    ).execute()

    # --------------------------------------------------------
    # Topic words
    # --------------------------------------------------------

    topic_words = set(
        re.findall(
            r"[a-zA-Z0-9]+",
            topic_lower
        )
    )

    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "for",
        "in",
        "on",
        "with",
        "using",
        "tutorial",
        "basics",
        "basic"
    }

    topic_words = {
        word
        for word in topic_words
        if word not in stop_words
    }

    videos = []
    seen_ids = set()

    # --------------------------------------------------------
    # Process results
    # --------------------------------------------------------

    for item in response.get("items", []):

        video_id = item["id"].get("videoId")

        if not video_id:
            continue

        if video_id in seen_ids:
            continue

        snippet = item["snippet"]

        title = snippet.get(
            "title",
            ""
        )

        description = snippet.get(
            "description",
            ""
        )

        title_lower = title.lower()
        description_lower = description.lower()

        # ----------------------------------------------------
        # Topic relevance
        # ----------------------------------------------------

        if len(topic_words) == 1:

            topic_word = next(
                iter(topic_words)
            )

            if not re.search(
                r"\b" + re.escape(topic_word) + r"\b",
                title_lower
            ):
                continue

        else:

            matching_words = 0

            for word in topic_words:

                if re.search(
                    r"\b" + re.escape(word) + r"\b",
                    title_lower
                ):
                    matching_words += 1

            required_words = max(
                1,
                int(len(topic_words) * 0.6)
            )

            if matching_words < required_words:
                continue

        # ----------------------------------------------------
        # Subject relevance
        # ----------------------------------------------------

        if subject:

            subject_words = set(
                re.findall(
                    r"[a-zA-Z0-9]+",
                    subject_lower
                )
            )

            subject_words = {
                word
                for word in subject_words
                if word not in stop_words
                and len(word) > 1
            }

            subject_match = False

            for word in subject_words:

                if (
                    re.search(
                        r"\b" + re.escape(word) + r"\b",
                        title_lower
                    )
                    or
                    re.search(
                        r"\b" + re.escape(word) + r"\b",
                        description_lower
                    )
                ):
                    subject_match = True
                    break

            if not subject_match:
                continue

        # ----------------------------------------------------
        # Add video
        # ----------------------------------------------------

        seen_ids.add(video_id)

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
        )

        if thumbnail:
            thumbnail_url = thumbnail.get("url", "")
        else:
            thumbnail_url = ""

        videos.append({

            "title": title,

            "description": description,

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "thumbnail":
                thumbnail_url,

            "video_id":
                video_id,

            "url":
                f"https://www.youtube.com/watch?v={video_id}"
        })

        if len(videos) >= max_results:
            break

    return videos