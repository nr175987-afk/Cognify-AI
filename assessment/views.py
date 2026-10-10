from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import AssessmentAttempt, LearningContent

import markdown
import traceback

from .ai_generator import (
    generate_questions,
    generate_learning_plan,
    search_adaptive_videos,
)

from .ai_service import generate_learning_content


# ============================================================
# HELPER: ADAPTIVE DIFFICULTY
# ============================================================

def get_adaptive_difficulty(score):
    if score < 40:
        return "Beginner"
    elif score < 60:
        return "Easy"
    elif score < 80:
        return "Medium"
    elif score < 100:
        return "Advanced"
    return "Expert"


# ============================================================
# ASSESSMENT HOME
# ============================================================

@login_required
def assessment_home(request):

    if request.method == "POST":

        subject = request.POST.get("subject", "").strip()
        topic = request.POST.get("topic", "").strip()
        difficulty = request.POST.get("difficulty", "Medium").strip()
        selected_count = request.POST.get("number_of_questions", "5")

        context = {
            "selected_subject": subject,
            "selected_topic": topic,
            "selected_difficulty": difficulty,
            "selected_number_of_questions": selected_count,
        }

        try:
            number_of_questions = int(selected_count)

            if not subject or not topic:
                raise ValueError("Please select a subject and enter a topic.")

            if difficulty not in ["Easy", "Medium", "Hard"]:
                raise ValueError("Please select a valid difficulty.")

            if not 1 <= number_of_questions <= 20:
                raise ValueError("Choose between 1 and 20 questions.")

        except (TypeError, ValueError) as error:
            context["error"] = str(error)

            return render(
                request,
                "assessment/assessment.html",
                context,
            )

        try:
            print("\n========== ASSESSMENT GENERATION ==========")
            print("Subject:", subject)
            print("Topic:", topic)
            print("Difficulty:", difficulty)
            print("Number of questions:", number_of_questions)
            print("Calling generate_questions()...")

            questions = generate_questions(
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                number_of_questions=number_of_questions,
            )

            # Support generators that return a QuestionSet object.
            if hasattr(questions, "questions"):
                questions = questions.questions

            if not questions:
                raise ValueError(
                    "The question generator returned no questions."
                )

            question_data = []

            for question in questions:

                if isinstance(question, dict):
                    get_value = question.get
                else:
                    get_value = lambda key, default="": getattr(
                        question, key, default
                    )

                question_data.append({
                    "question": get_value("question", ""),
                    "option_a": get_value("option_a", ""),
                    "option_b": get_value("option_b", ""),
                    "option_c": get_value("option_c", ""),
                    "option_d": get_value("option_d", ""),
                    "correct_answer": get_value("correct_answer", ""),
                    "explanation": get_value("explanation", ""),
                })

            if not question_data:
                raise ValueError("No usable questions were generated.")

            # Store questions in the session for the quiz page.
            request.session["generated_questions"] = question_data
            request.session["assessment_subject"] = subject
            request.session["assessment_topic"] = topic
            request.session["assessment_difficulty"] = difficulty

            print("Successfully generated", len(question_data), "questions.")
            print("Redirecting to quiz page.")
            print("===========================================\n")

            return redirect("quiz")

        except Exception as error:
            print("\n========== ASSESSMENT GENERATION FAILED ==========")
            print("Error:", repr(error))
            traceback.print_exc()
            print("==================================================\n")

            context["error"] = (
                "Question generation failed. Your selections have been "
                "preserved. Check the VS Code terminal for the exact error."
            )

            return render(
                request,
                "assessment/assessment.html",
                context,
            )

    return render(request, "assessment/assessment.html")

# ============================================================
# QUIZ
# ============================================================

@login_required
def quiz(request):

    questions = request.session.get("generated_questions", [])

    if not questions:
        return redirect("assessment_home")

    if request.method == "POST":

        correct = 0

        for index, question in enumerate(questions):
            answer = request.POST.get(f"question_{index}")

            if answer == question["correct_answer"]:
                correct += 1

        total = len(questions)
        score = (correct / total) * 100 if total else 0

        subject = request.session.get(
            "assessment_subject", "Unknown"
        )
        topic = request.session.get(
            "assessment_topic", "Unknown"
        )
        difficulty = request.session.get(
            "assessment_difficulty", "Medium"
        )

        AssessmentAttempt.objects.create(
            user=request.user,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            total_questions=total,
            correct_answers=correct,
            score=score,
        )

        request.session["last_score"] = score
        request.session["last_correct"] = correct
        request.session["last_total"] = total

        request.session.pop("generated_questions", None)

        return redirect("assessment_result")

    return render(
        request,
        "assessment/quiz.html",
        {"questions": questions},
    )


# ============================================================
# ASSESSMENT RESULT
# ============================================================

@login_required
def assessment_result(request):

    return render(
        request,
        "assessment/result.html",
        {
            "score": request.session.get("last_score", 0),
            "correct": request.session.get("last_correct", 0),
            "total": request.session.get("last_total", 0),
        },
    )


# ============================================================
# ASSESSMENT HISTORY
# ============================================================

@login_required
def assessment_history(request):

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("-created_at")

    total_assessments = attempts.count()

    if total_assessments:
        average_score = sum(
            attempt.score for attempt in attempts
        ) / total_assessments

        best_score = max(
            attempt.score for attempt in attempts
        )
    else:
        average_score = 0
        best_score = 0

    topic_data = {}

    for attempt in attempts:
        topic_data.setdefault(attempt.topic, []).append(
            attempt.score
        )

    topic_performance = []

    for topic, scores in topic_data.items():
        topic_performance.append({
            "topic": topic,
            "average": round(sum(scores) / len(scores), 1),
            "attempts": len(scores),
        })

    topic_performance.sort(
        key=lambda item: item["average"],
        reverse=True,
    )

    recent_attempts = list(attempts[:10])
    recent_attempts.reverse()

    context = {
        "attempts": attempts,
        "total_assessments": total_assessments,
        "average_score": round(average_score, 1),
        "best_score": best_score,
        "topic_performance": topic_performance,
        "recent_attempts": recent_attempts,
    }

    return render(request, "assessment/history.html", context)


# ============================================================
# HELPER: STUDENT PERFORMANCE
# ============================================================

def get_student_performance(attempts):

    total_attempts = attempts.count()

    average_score = (
        sum(attempt.score for attempt in attempts) / total_attempts
        if total_attempts else 0
    )

    topic_data = {}
    difficulty_data = {}

    for attempt in attempts:

        topic_data.setdefault(
            attempt.topic, []
        ).append(attempt.score)

        difficulty_data.setdefault(
            attempt.difficulty, []
        ).append(attempt.score)

    topic_analysis = []

    for topic, scores in topic_data.items():
        topic_analysis.append({
            "topic": topic,
            "average": round(sum(scores) / len(scores), 1),
            "attempts": len(scores),
        })

    topic_analysis.sort(
        key=lambda item: item["average"],
        reverse=True,
    )

    difficulty_analysis = []

    for difficulty, scores in difficulty_data.items():
        difficulty_analysis.append({
            "difficulty": difficulty,
            "average": round(sum(scores) / len(scores), 1),
            "attempts": len(scores),
        })

    strong_topics = [
        item for item in topic_analysis
        if item["average"] >= 80
    ]

    weak_topics = [
        item for item in topic_analysis
        if item["average"] < 60
    ]

    if total_attempts >= 2:
        first_score = attempts.first().score
        last_score = attempts.last().score
        improvement = last_score - first_score

        if improvement > 5:
            trend = "Improving"
        elif improvement < -5:
            trend = "Declining"
        else:
            trend = "Stable"
    else:
        improvement = 0
        trend = "Insufficient data"

    return {
        "total_attempts": total_attempts,
        "average_score": round(average_score, 1),
        "topic_analysis": topic_analysis,
        "difficulty_analysis": difficulty_analysis,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "recommended_topics": sorted(
            topic_analysis,
            key=lambda item: item["average"],
        )[:3],
        "trend": trend,
        "improvement": round(improvement, 1),
    }


# ============================================================
# LEARNING ANALYSIS
# ============================================================

@login_required
def learning_analysis(request):

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("created_at")

    if not attempts.exists():
        return render(
            request,
            "assessment/learning_analysis.html",
            {"has_data": False},
        )

    data = get_student_performance(attempts)

    student_data = {
        "overall_score": data["average_score"],
        "total_attempts": data["total_attempts"],
        "topics": data["topic_analysis"],
        "strong_topics": data["strong_topics"],
        "weak_topics": data["weak_topics"],
        "difficulty_analysis": data["difficulty_analysis"],
        "learning_trend": data["trend"],
        "score_improvement": data["improvement"],
    }

    try:
        plan = generate_learning_plan(student_data)

    except Exception as error:
        print("Learning analysis AI error:", error)

        plan = """
## Personalized Learning Plan Temporarily Unavailable

Your assessment results and performance analysis are still available.
Practise your weak topics and revisit difficult concepts while the
AI service is unavailable.
"""

    context = {
        "has_data": True,
        "average_score": data["average_score"],
        "total_attempts": data["total_attempts"],
        "trend": data["trend"],
        "strong_topics": data["strong_topics"][:3],
        "weak_topics": data["weak_topics"][:3],
        "recommended_topics": data["recommended_topics"],
        "difficulty_analysis": data["difficulty_analysis"],
        "plan": plan,
    }

    return render(
        request,
        "assessment/learning_analysis.html",
        context,
    )


# ============================================================
# PERSONALIZED PLAN
# ============================================================

@login_required
def personalized_plan(request):

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("created_at")

    if not attempts.exists():
        return render(
            request,
            "assessment/personalized_plan.html",
            {"has_data": False},
        )

    data = get_student_performance(attempts)

    student_data = f"""
Student Learning Performance

Overall Average: {data['average_score']}%
Total Assessments: {data['total_attempts']}
Strong Topics: {data['strong_topics']}
Weak Topics: {data['weak_topics']}
Topic Performance: {data['topic_analysis']}
Difficulty Performance: {data['difficulty_analysis']}
Learning Trend: {data['trend']}
Score Improvement: {data['improvement']}%
"""

    try:
        plan = generate_learning_plan(student_data)

    except Exception as error:
        print("Personalized plan AI error:", error)

        plan = """
## Personalized Plan Temporarily Unavailable

Your performance information is safe. Please try again later.
"""

    return render(
        request,
        "assessment/personalized_plan.html",
        {
            "has_data": True,
            "plan": plan,
            "average_score": data["average_score"],
            "total_attempts": data["total_attempts"],
            "trend": data["trend"],
        },
    )


# ============================================================
# ADAPTIVE LEARNING DASHBOARD
# ============================================================

@login_required
def adaptive_learning(request):

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("-created_at")

    if not attempts.exists():
        return render(
            request,
            "assessment/adaptive_learning.html",
            {"topics": []},
        )

    topic_data = {}

    for attempt in attempts:

        if attempt.topic not in topic_data:
            topic_data[attempt.topic] = {
                "subject": attempt.subject,
                "scores": [],
            }

        topic_data[attempt.topic]["scores"].append(
            attempt.score
        )

    topics = []

    for topic, data in topic_data.items():

        average_score = round(
            sum(data["scores"]) / len(data["scores"]),
            1,
        )

        level = get_adaptive_difficulty(average_score)

        recommendations = {
            "Beginner": (
                "Start with fundamentals, simple explanations "
                "and examples."
            ),
            "Easy": (
                "Strengthen your basics using easy notes "
                "and guided practice."
            ),
            "Medium": (
                "Practise medium-level concepts and apply "
                "what you have learned."
            ),
            "Advanced": (
                "Challenge yourself with advanced concepts "
                "and problems."
            ),
            "Expert": (
                "Continue with expert problems, projects "
                "and real-world challenges."
            ),
        }

        next_goal = {
            "Beginner": 60,
            "Easy": 70,
            "Medium": 80,
            "Advanced": 100,
            "Expert": 100,
        }

        topics.append({
            "topic": topic,
            "subject": data["subject"],
            "score": average_score,
            "level": level,
            "recommendation": recommendations[level],
            "next_goal": next_goal[level],
            "attempts": len(data["scores"]),
        })

    topics.sort(key=lambda item: item["score"])

    return render(
        request,
        "assessment/adaptive_learning.html",
        {"topics": topics},
    )


# ============================================================
# ADAPTIVE CONTENT
# ============================================================

@login_required
def adaptive_content(request):

    topic = request.GET.get("topic", "").strip()
    content_type = request.GET.get(
        "type", "notes"
    ).strip().lower()

    allowed_types = {
        "notes",
        "questions",
        "realworld",
        "videos",
    }

    if not topic:
        messages.warning(
            request,
            "Please select a topic.",
        )
        return redirect("adaptive_learning")

    if content_type not in allowed_types:
        content_type = "notes"

    attempts = AssessmentAttempt.objects.filter(
        user=request.user,
        topic__iexact=topic,
    ).order_by("-created_at")

    if attempts.exists():
        score = sum(
            attempt.score for attempt in attempts
        ) / attempts.count()
    else:
        score = 0

    score = round(score, 1)
    difficulty = get_adaptive_difficulty(score)

    content = ""
    content_html = ""
    videos = []

    # --------------------------------------------------------
    # VIDEOS
    # --------------------------------------------------------

    if content_type == "videos":

        try:
            latest_attempt = attempts.first()

            subject = (
                latest_attempt.subject
                if latest_attempt
                else ""
            )

            videos = search_adaptive_videos(
                topic=topic,
                difficulty=difficulty,
                max_results=8,
                subject=subject,
            )

        except Exception as error:
            print(
                "YouTube search error:",
                error,
            )

            messages.warning(
                request,
                "Videos are temporarily unavailable. "
                "Please try again later.",
            )

    # --------------------------------------------------------
    # CACHED CONTENT OR NEW AI CONTENT
    # --------------------------------------------------------

    else:

        saved_content = LearningContent.objects.filter(
            topic__iexact=topic,
            content_type=content_type,
            difficulty=difficulty,
        ).first()

        if (
            saved_content
            and saved_content.content
            and saved_content.content.strip()
        ):

            content = saved_content.content

            print(
                "Using cached learning content:",
                topic,
                content_type,
                difficulty,
            )

        else:

            try:
                content = generate_learning_content(
                    topic=topic,
                    content_type=content_type,
                    difficulty=difficulty,
                )

                if not content or not content.strip():
                    raise ValueError(
                        "The AI provider returned empty content."
                    )

                LearningContent.objects.create(
                    topic=topic,
                    content_type=content_type,
                    difficulty=difficulty,
                    content=content,
                )

                print(
                    "Saved new learning content:",
                    topic,
                    content_type,
                    difficulty,
                )

            except Exception as error:
                print(
                    "Adaptive content generation error:",
                    error,
                )

                content = (
                    "## Learning Content Temporarily Unavailable\n\n"
                    "The AI providers could not generate content "
                    "right now. Please try again later. "
                    "Your assessment data has not been affected."
                )

                messages.warning(
                    request,
                    "AI content generation failed. "
                    "Please try again later.",
                )

        # ----------------------------------------------------
        # MARKDOWN TO HTML
        # ----------------------------------------------------

        try:
            content_html = markdown.markdown(
                content,
                extensions=[
                    "extra",
                    "tables",
                    "fenced_code",
                    "pymdownx.arithmatex",
                ],
                extension_configs={
                    "pymdownx.arithmatex": {
                        "generic": True,
                    },
                },
            )

        except Exception as error:
            print(
                "Markdown conversion error:",
                error,
            )

            # Fallback: render Markdown without the math extension.
            content_html = markdown.markdown(
                content,
                extensions=[
                    "extra",
                    "tables",
                    "fenced_code",
                ],
            )

    context = {
        "topic": topic,
        "content_type": content_type,
        "difficulty": difficulty,
        "score": score,
        "content": content,
        "content_html": content_html,
        "videos": videos,
    }

    return render(
        request,
        "assessment/adaptive_content.html",
        context,
    )