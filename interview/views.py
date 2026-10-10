
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import InterviewSession, InterviewQuestion

from .ai_interview import (
    generate_interview_questions,
    evaluate_interview_answer,
    generate_concept_lesson,
)


logger = logging.getLogger(__name__)


# ============================================================
# INTERVIEW HOME
# ============================================================

@login_required
def interview_home(request):
    return render(
        request,
        "interview/interview_home.html"
    )


# ============================================================
# START INTERVIEW
# ============================================================

@login_required
def start_interview(request):

    if request.method != "POST":
        return redirect("interview_home")

    role = request.POST.get("role", "").strip()
    difficulty = request.POST.get("difficulty", "").strip()
    total_questions = request.POST.get("total_questions", "5").strip()

    # Validate role
    if not role:
        return redirect("interview_home")

    # Validate difficulty
    if difficulty not in ["Easy", "Medium", "Hard"]:
        return redirect("interview_home")

    # Validate question count
    try:
        total_questions = int(total_questions)
    except (ValueError, TypeError):
        total_questions = 5

    if total_questions not in [5, 10]:
        total_questions = 5

    # Create interview session
    session = InterviewSession.objects.create(
        user=request.user,
        role=role,
        difficulty=difficulty,
        total_questions=total_questions,
        completed_questions=0,
        overall_score=0,
        status="In Progress",
    )

    # Generate questions using AI
    try:
        ai_questions = generate_interview_questions(
            role=role,
            difficulty=difficulty,
            total_questions=total_questions,
        )

        generated_questions = ai_questions.questions

        if not generated_questions:
            session.delete()
            logger.error("AI returned no interview questions.")
            return redirect("interview_home")

        # Save the actual number of generated questions.
        # This prevents the session from becoming impossible
        # to complete if the AI returns fewer questions.
        session.total_questions = len(generated_questions)
        session.save(update_fields=["total_questions"])

        for index, question_text in enumerate(
            generated_questions,
            start=1
        ):
            InterviewQuestion.objects.create(
                session=session,
                question_number=index,
                question=question_text,
            )

    except Exception:
        logger.exception("Failed to generate interview questions.")

        session.delete()
        return redirect("interview_home")

    # Open the first question
    return redirect(
        "interview_session",
        session_id=session.id
    )


# ============================================================
# INTERVIEW SESSION
# ============================================================

@login_required
def interview_session(request, session_id):

    session = get_object_or_404(
        InterviewSession,
        id=session_id,
        user=request.user,
    )

    # Find the first unanswered question
    current_question = (
        session.questions
        .filter(user_answer="")
        .order_by("question_number")
        .first()
    )

    # All questions have been answered
    if not current_question:

        # If questions exist and all have answers, make sure
        # the result page is displayed.
        return redirect(
            "interview_result",
            session_id=session.id
        )

    return render(
        request,
        "interview/interview_session.html",
        {
            "session": session,
            "current_question": current_question,
        }
    )


# ============================================================
# SUBMIT ANSWER
# ============================================================

@login_required
def submit_answer(request, session_id):

    session = get_object_or_404(
        InterviewSession,
        id=session_id,
        user=request.user,
    )

    # Only accept POST requests
    if request.method != "POST":
        return redirect(
            "interview_session",
            session_id=session.id
        )

    # Get the question submitted by the user
    question_id = request.POST.get("question_id")

    current_question = get_object_or_404(
        InterviewQuestion,
        id=question_id,
        session=session,
    )

    # Get and validate the answer
    user_answer = request.POST.get(
        "user_answer",
        ""
    ).strip()

    if not user_answer:
        return redirect(
            "interview_session",
            session_id=session.id
        )

    # Prevent an already answered question from being
    # evaluated again through a repeated form submission.
    if current_question.user_answer:
        return redirect(
            "interview_session",
            session_id=session.id
        )

    # --------------------------------------------------------
    # STEP 1: EVALUATE THE ANSWER
    # --------------------------------------------------------

    try:
        evaluation = evaluate_interview_answer(
            role=session.role,
            difficulty=session.difficulty,
            question=current_question.question,
            user_answer=user_answer,
        )

    except Exception:
        logger.exception(
            "Failed to evaluate interview question %s.",
            current_question.id
        )

        # Do not save a fake score if AI evaluation fails.
        return redirect(
            "interview_session",
            session_id=session.id
        )

    # --------------------------------------------------------
    # STEP 2: SAVE THE ANSWER, SCORE, AND FEEDBACK
    # --------------------------------------------------------

    current_question.user_answer = user_answer
    current_question.score = evaluation.score
    current_question.feedback = evaluation.feedback

    current_question.save(
        update_fields=[
            "user_answer",
            "score",
            "feedback",
        ]
    )

    # --------------------------------------------------------
    # STEP 3: GENERATE A BEGINNER-FRIENDLY LESSON
    # --------------------------------------------------------

    try:
        lesson = generate_concept_lesson(
            role=session.role,
            difficulty=session.difficulty,
            question=current_question.question,
            user_answer=user_answer,
            feedback=evaluation.feedback,
        )

        # Save all five learning sections
        current_question.concept_explanation = (
            lesson.concept_explanation
        )

        current_question.how_it_works = (
            lesson.how_it_works
        )

        current_question.example = lesson.example

        current_question.interview_ready_answer = (
            lesson.interview_ready_answer
        )

        current_question.practice_question = (
            lesson.practice_question
        )

        current_question.save(
            update_fields=[
                "concept_explanation",
                "how_it_works",
                "example",
                "interview_ready_answer",
                "practice_question",
            ]
        )

    except Exception:
        # Keep the submitted answer, score, and feedback even
        # if lesson generation fails.
        logger.exception(
            "Failed to generate lesson for question %s.",
            current_question.id
        )

    # --------------------------------------------------------
    # STEP 4: UPDATE COMPLETED QUESTION COUNT
    # --------------------------------------------------------

    completed_count = (
        session.questions
        .exclude(user_answer="")
        .count()
    )

    session.completed_questions = completed_count

    # --------------------------------------------------------
    # STEP 5: COMPLETE THE INTERVIEW IF ALL ARE ANSWERED
    # --------------------------------------------------------

    actual_total = session.questions.count()

    if completed_count >= actual_total and actual_total > 0:

        scores = [
            question.score
            for question in session.questions.all()
        ]

        average_score = (
            sum(scores) / len(scores)
            if scores
            else 0
        )

        session.overall_score = average_score * 10
        session.completed_questions = completed_count
        session.status = "Completed"
        session.completed_at = timezone.now()

        session.save(
            update_fields=[
                "completed_questions",
                "overall_score",
                "status",
                "completed_at",
            ]
        )

        return redirect(
            "interview_result",
            session_id=session.id
        )

    # --------------------------------------------------------
    # STEP 6: SAVE PROGRESS AND OPEN THE NEXT QUESTION
    # --------------------------------------------------------

    session.save(
        update_fields=[
            "completed_questions",
        ]
    )

    return redirect(
        "interview_session",
        session_id=session.id
    )


# ============================================================
# INTERVIEW RESULT
# ============================================================

@login_required
def interview_result(request, session_id):

    session = get_object_or_404(
        InterviewSession,
        id=session_id,
        user=request.user,
    )

    questions = (
        session.questions
        .order_by("question_number")
    )

    return render(
        request,
        "interview/interview_result.html",
        {
            "session": session,
            "questions": questions,
        }
    )


# ============================================================
# INTERVIEW HISTORY
# ============================================================

@login_required
def interview_history(request):

    sessions = (
        InterviewSession.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "interview/interview_history.html",
        {
            "sessions": sessions,
        }
    )