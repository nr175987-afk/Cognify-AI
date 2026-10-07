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
# AI QUESTION GENERATION
# ============================================================

class InterviewQuestionOutput(BaseModel):

    questions: list[str] = Field(
        default_factory=list
    )


def generate_interview_questions(
    role,
    difficulty,
    total_questions,
):

    prompt = f"""
You are a professional technical interviewer.

Generate interview questions for the following job role.

Job Role:
{role}

Difficulty:
{difficulty}

Number of Questions:
{total_questions}

IMPORTANT RULES:

1. Generate exactly {total_questions} questions.
2. Questions must be relevant to the job role.
3. Follow the requested difficulty level.
4. Questions must test technical knowledge and reasoning.
5. Do not assume the candidate has work experience.
6. Do not invent a candidate background.
7. Do not include answers.
8. Do not include explanations.
9. Do not number the questions inside the question text.
10. Avoid duplicate questions.
11. Use clear professional English.
12. Keep each question concise.
13. Return only structured JSON.
"""

    response = client.models.generate_content(

        model=MODEL_NAME,

        contents=prompt,

        config={
            "response_mime_type": "application/json",
            "response_schema": InterviewQuestionOutput,
        },
    )

    return InterviewQuestionOutput.model_validate_json(
        response.text
    )


# ============================================================
# AI ANSWER EVALUATION
# ============================================================

class InterviewEvaluationOutput(BaseModel):

    score: float

    feedback: str


def evaluate_interview_answer(
    role,
    difficulty,
    question,
    user_answer,
):

    prompt = f"""
You are a professional technical interviewer.

Evaluate the candidate's answer to the interview question.

Job Role:
{role}

Difficulty:
{difficulty}

Interview Question:
{question}

Candidate Answer:
{user_answer}

Evaluate the answer based on:

1. Technical correctness
2. Understanding of the concept
3. Relevance to the question
4. Completeness
5. Clarity of explanation

Scoring:

0 = Completely incorrect or irrelevant
1-2 = Very poor understanding
3-4 = Limited understanding
5-6 = Basic understanding
7-8 = Good understanding
9 = Very good answer
10 = Excellent and complete answer

IMPORTANT RULES:

1. Give a score between 0 and 10.
2. Do not give marks simply because the answer is long.
3. Do not assume information that the candidate did not provide.
4. Do not penalize the candidate for not having work experience.
5. Focus on the actual answer.
6. Give concise and useful feedback.
7. Mention what was done well.
8. Mention what could be improved.
9. Do not provide a completely rewritten answer.
10. Return only structured JSON.
"""

    response = client.models.generate_content(

        model=MODEL_NAME,

        contents=prompt,

        config={
            "response_mime_type": "application/json",
            "response_schema": InterviewEvaluationOutput,
        },
    )

    return InterviewEvaluationOutput.model_validate_json(
        response.text
    )