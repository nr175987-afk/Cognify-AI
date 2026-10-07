from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    InterviewSession,
    InterviewQuestion,
)

from .ai_interview import (
    generate_interview_questions,
    evaluate_interview_answer,
)


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

        return redirect(
            "interview_home"
        )

    role = request.POST.get(
        "role",
        ""
    ).strip()

    difficulty = request.POST.get(
        "difficulty",
        ""
    ).strip()

    total_questions = request.POST.get(
        "total_questions",
        "5"
    ).strip()


    # Validate role

    if not role:

        return redirect(
            "interview_home"
        )


    # Validate difficulty

    if difficulty not in [
        "Easy",
        "Medium",
        "Hard"
    ]:

        return redirect(
            "interview_home"
        )


    # Convert question count

    try:

        total_questions = int(
            total_questions
        )

    except ValueError:

        total_questions = 5


    # Allow only 5 or 10 questions

    if total_questions not in [
        5,
        10
    ]:

        total_questions = 5


    # ========================================================
    # CREATE INTERVIEW SESSION
    # ========================================================

    session = InterviewSession.objects.create(

        user=request.user,

        role=role,

        difficulty=difficulty,

        total_questions=total_questions,

        completed_questions=0,

        overall_score=0,

        status="In Progress",
    )


    # ========================================================
    # GENERATE AI QUESTIONS
    # ========================================================

    ai_questions = generate_interview_questions(

        role=role,

        difficulty=difficulty,

        total_questions=total_questions,
    )


    # ========================================================
    # STORE QUESTIONS
    # ========================================================

    for index, question in enumerate(

        ai_questions.questions,

        start=1

    ):

        InterviewQuestion.objects.create(

            session=session,

            question_number=index,

            question=question,
        )


    # ========================================================
    # OPEN FIRST QUESTION
    # ========================================================

    return redirect(

        "interview_session",

        session_id=session.id

    )


# ============================================================
# INTERVIEW SESSION
# ============================================================

@login_required
def interview_session(

    request,

    session_id

):

    session = get_object_or_404(

        InterviewSession,

        id=session_id,

        user=request.user,

    )


    # Find the first unanswered question

    current_question = (

        session.questions

        .filter(

            user_answer=""

        )

        .order_by(

            "question_number"

        )

        .first()

    )


    # ========================================================
    # ALL QUESTIONS ANSWERED
    # ========================================================

    if not current_question:

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
def submit_answer(

    request,

    session_id

):

    session = get_object_or_404(

        InterviewSession,

        id=session_id,

        user=request.user,

    )


    # Only accept POST

    if request.method != "POST":

        return redirect(

            "interview_session",

            session_id=session.id

        )


    # ========================================================
    # GET CURRENT QUESTION
    # ========================================================

    question_id = request.POST.get(
        "question_id"
    )


    current_question = get_object_or_404(

        InterviewQuestion,

        id=question_id,

        session=session,

    )


    # ========================================================
    # GET USER ANSWER
    # ========================================================

    user_answer = request.POST.get(

        "user_answer",

        ""

    ).strip()


    # Don't allow empty answers

    if not user_answer:

        return redirect(

            "interview_session",

            session_id=session.id

        )


    # ========================================================
    # AI EVALUATION
    # ========================================================

    evaluation = evaluate_interview_answer(

        role=session.role,

        difficulty=session.difficulty,

        question=current_question.question,

        user_answer=user_answer,

    )


    # ========================================================
    # SAVE ANSWER
    # ========================================================

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


    # ========================================================
    # UPDATE COMPLETED QUESTIONS
    # ========================================================

    completed_count = (

        session.questions

        .exclude(

            user_answer=""

        )

        .count()

    )


    session.completed_questions = completed_count


    # ========================================================
    # CHECK IF INTERVIEW IS COMPLETE
    # ========================================================

    if completed_count >= session.total_questions:

        scores = [

            question.score

            for question in session.questions.all()

        ]


        if scores:

            average_score = (

                sum(scores) / len(scores)

            )

        else:

            average_score = 0


        session.overall_score = (

            average_score * 10

        )

        session.status = "Completed"

        from django.utils import timezone

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


    # ========================================================
    # SAVE PROGRESS
    # ========================================================

    session.save(

        update_fields=[

            "completed_questions",

        ]

    )


    # ========================================================
    # GO TO NEXT QUESTION
    # ========================================================

    return redirect(

        "interview_session",

        session_id=session.id

    )


# ============================================================
# INTERVIEW RESULT
# ============================================================

@login_required
def interview_result(

    request,

    session_id

):

    session = get_object_or_404(

        InterviewSession,

        id=session_id,

        user=request.user,

    )


    questions = (

        session.questions

        .order_by(

            "question_number"

        )

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

        .filter(

            user=request.user

        )

        .order_by(

            "-created_at"

        )

    )


    return render(

        request,

        "interview/interview_history.html",

        {

            "sessions": sessions,

        }

    )