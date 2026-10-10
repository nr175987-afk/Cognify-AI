
import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==================================================
# INTERVIEW QUESTION GENERATION
# ==================================================

class InterviewQuestionOutput(BaseModel):
    questions: list[str] = Field(default_factory=list)


def generate_interview_questions(
    role,
    difficulty,
    total_questions
):
    prompt = f"""
You are a professional technical interviewer.

Generate exactly {total_questions} interview questions.

Job Role: {role}
Difficulty: {difficulty}

Requirements:
1. Questions must be relevant to the selected role.
2. Match the requested difficulty.
3. Cover different concepts.
4. Test actual understanding.
5. Do not provide answers or explanations.
6. Do not number the questions.
7. Keep each question clear and interview-friendly.
8. Do not assume personal experience or background.
9. Return exactly {total_questions} questions.
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


# ==================================================
# INTERVIEW ANSWER EVALUATION
# ==================================================

class InterviewEvaluationOutput(BaseModel):
    score: float = Field(ge=0, le=10)
    feedback: str


def evaluate_interview_answer(
    role,
    difficulty,
    question,
    user_answer
):
    prompt = f"""
You are an experienced technical interviewer.

Job Role: {role}
Difficulty: {difficulty}

Interview Question:
{question}

Candidate's Answer:
{user_answer}

Evaluate the answer using:
1. Technical correctness
2. Conceptual understanding
3. Relevance
4. Completeness
5. Clarity
6. Accuracy of examples

Scoring:
0-2: Incorrect or mostly irrelevant.
3-4: Limited understanding with major gaps.
5-6: Basic understanding, but incomplete.
7-8: Good understanding with minor gaps.
9: Very strong and complete.
10: Excellent, accurate, complete interview-level answer.

Rules:
- Award partial credit for partially correct answers.
- Do not reward length alone.
- Accept technically correct wording in different forms.
- Do not invent claims about what the candidate knows.
- Do not give the ideal answer in the feedback.
- Mention the main strength and the most important improvement.
- Be constructive and concise.

Return a score from 0 to 10 and concise feedback.
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


# ==================================================
# AI-GENERATED CONCEPT LESSON
# ==================================================

class ConceptLessonOutput(BaseModel):
    concept_explanation: str
    how_it_works: str
    example: str
    interview_ready_answer: str
    practice_question: str


def generate_concept_lesson(
    role,
    difficulty,
    question,
    user_answer,
    feedback
):
    prompt = f"""
You are a patient technical tutor teaching a beginner.

Create a self-contained lesson for a candidate who has just
completed a mock interview. Teach the concept directly.
Do not tell the candidate to visit another website or watch
an external video.

Job role: {role}
Interview difficulty: {difficulty}

Interview question:
{question}

Candidate's answer:
{user_answer}

Evaluator feedback:
{feedback}

Create these five sections:

1. concept_explanation:
Explain what the concept means from scratch in simple language.
Define important technical terms. Assume the learner is a beginner.

2. how_it_works:
Explain the concept step by step. Use a small analogy when useful.
Correct misunderstandings in the candidate's answer respectfully.

3. example:
Give a simple, accurate, self-contained example relevant to the
question. For programming questions, provide runnable code and
explain its important lines. For conceptual questions, use a
clear practical example. Do not use Markdown tables.

4. interview_ready_answer:
Provide a natural, technically correct answer the learner could
give in an interview. Make it detailed enough to answer the
actual question, but not unnecessarily long.

5. practice_question:
Give one new, related question that tests understanding.
Do not include its answer.

Important rules:
- Teach the exact concept asked about in the interview question.
- Adapt the explanation to the candidate's apparent knowledge gap.
- Do not simply repeat the evaluator feedback.
- Never shame the learner.
- Ensure technical details and code are correct.
- Keep the lesson beginner-friendly and self-contained.
- Do not fabricate candidate experience or background.
- Return all five fields in the required structured format.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ConceptLessonOutput,
        },
    )

    return ConceptLessonOutput.model_validate_json(
        response.text
    )