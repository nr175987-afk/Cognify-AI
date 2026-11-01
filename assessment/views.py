from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import logging
import markdown

from .models import AssessmentAttempt, LearningContent

from .ai_generator import (
    generate_questions,
    generate_learning_plan,
    search_adaptive_videos,
)

from .ai_service import generate_learning_content


logger = logging.getLogger(__name__)


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
# HELPER: EVIDENCE-BASED DIFFICULTY STATUS
# ============================================================

def get_difficulty_status(score, attempts):
    """Describe performance without claiming mastery from too little data."""

    if attempts == 0:
        return "Not assessed"

    if score >= 100:
        if attempts == 1:
            return "Excellent performance (100% on 1 assessment)"

        return (
            f"Excellent performance "
            f"(100% across {attempts} assessments)"
        )

    if score >= 80:
        return "Proficient"

    if score >= 60:
        return "Developing"

    return "Needs improvement"


# ============================================================
# HELPER: LEARNING PROGRESSION
# ============================================================

def get_learning_progression(current_level):
    """Return a clear next step while keeping revision optional."""

    progression = {

        "Beginner": {
            "next_level": "Easy",
            "focus": (
                "Build strong fundamentals through guided practice."
            ),
            "revision": (
                "Continue practising basic concepts and examples."
            ),
        },

        "Easy": {
            "next_level": "Medium",
            "focus": (
                "Apply the fundamentals to intermediate problems."
            ),
            "revision": (
                "Use short revision exercises when needed."
            ),
        },

        "Medium": {
            "next_level": "Advanced",
            "focus": (
                "Solve challenging problems and practical applications."
            ),
            "revision": (
                "Review intermediate concepts when needed."
            ),
        },

        "Advanced": {
            "next_level": "Expert",
            "focus": (
                "Work on expert-level projects, advanced optimization, "
                "complex problem-solving and interview challenges."
            ),
            "revision": (
                "Advanced revision is optional. Revisit diagnostics, "
                "regularization and feature engineering whenever needed."
            ),
        },

        "Expert": {
            "next_level": "Expert",
            "focus": (
                "Continue with research-oriented problems, independent "
                "projects and advanced real-world applications."
            ),
            "revision": (
                "Revise specific concepts whenever required."
            ),
        },
    }

    return progression.get(
        current_level,
        progression["Beginner"],
    )


# ============================================================
# ASSESSMENT HOME
# ============================================================

@login_required
def assessment_home(request):

    if request.method == "POST":

        subject = request.POST.get("subject", "").strip()
        topic = request.POST.get("topic", "").strip()

        difficulty = request.POST.get(
            "difficulty",
            "Medium"
        ).strip()

        selected_count = request.POST.get(
            "number_of_questions",
            "5"
        )

        context = {
            "selected_subject": subject,
            "selected_topic": topic,
            "selected_difficulty": difficulty,
            "selected_number_of_questions": selected_count,
        }

        try:

            number_of_questions = int(selected_count)

            if not subject or not topic:
                raise ValueError(
                    "Please select a subject and enter a topic."
                )

            if difficulty not in ["Easy", "Medium", "Hard"]:
                raise ValueError(
                    "Please select a valid difficulty."
                )

            if not 1 <= number_of_questions <= 20:
                raise ValueError(
                    "Choose between 1 and 20 questions."
                )

        except (TypeError, ValueError) as error:

            context["error"] = str(error)

            return render(
                request,
                "assessment/assessment.html",
                context,
            )

        try:

            questions = generate_questions(
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                number_of_questions=number_of_questions,
            )

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
                        question,
                        key,
                        default
                    )

                question_data.append({

                    "question": get_value(
                        "question",
                        ""
                    ),

                    "option_a": get_value(
                        "option_a",
                        ""
                    ),

                    "option_b": get_value(
                        "option_b",
                        ""
                    ),

                    "option_c": get_value(
                        "option_c",
                        ""
                    ),

                    "option_d": get_value(
                        "option_d",
                        ""
                    ),

                    "correct_answer": get_value(
                        "correct_answer",
                        ""
                    ),

                    "explanation": get_value(
                        "explanation",
                        ""
                    ),

                })

            if not question_data:
                raise ValueError(
                    "No usable questions were generated."
                )

            request.session["generated_questions"] = question_data

            request.session["assessment_subject"] = subject

            request.session["assessment_topic"] = topic

            request.session["assessment_difficulty"] = difficulty

            return redirect("quiz")

        except Exception:

            logger.exception(
                "Assessment generation failed"
            )

            context["error"] = (
                "Question generation failed. Your selections have "
                "been preserved. Check the terminal for details."
            )

            return render(
                request,
                "assessment/assessment.html",
                context,
            )

    return render(
        request,
        "assessment/assessment.html"
    )


# ============================================================
# QUIZ
# ============================================================

@login_required
def quiz(request):

    questions = request.session.get(
        "generated_questions",
        []
    )

    if not questions:
        return redirect("assessment_home")

    if request.method == "POST":

        correct = 0

        for index, question in enumerate(questions):

            answer = request.POST.get(
                f"question_{index}"
            )

            if answer == question["correct_answer"]:
                correct += 1

        total = len(questions)

        score = (
            (correct / total) * 100
            if total else 0
        )

        subject = request.session.get(
            "assessment_subject",
            "Unknown"
        )

        topic = request.session.get(
            "assessment_topic",
            "Unknown"
        )

        difficulty = request.session.get(
            "assessment_difficulty",
            "Medium"
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

        request.session.pop(
            "generated_questions",
            None
        )

        return redirect("assessment_result")

    return render(
        request,
        "assessment/quiz.html",
        {
            "questions": questions,
        },
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
            "score": request.session.get(
                "last_score",
                0
            ),

            "correct": request.session.get(
                "last_correct",
                0
            ),

            "total": request.session.get(
                "last_total",
                0
            ),
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

        topic_data.setdefault(
            attempt.topic,
            []
        ).append(attempt.score)

    topic_performance = []

    for topic, scores in topic_data.items():

        topic_performance.append({

            "topic": topic,

            "average": round(
                sum(scores) / len(scores),
                1
            ),

            "attempts": len(scores),

        })

    topic_performance.sort(
        key=lambda item: item["average"],
        reverse=True,
    )

    recent_attempts = list(
        attempts[:10]
    )

    recent_attempts.reverse()

    return render(
        request,
        "assessment/history.html",
        {

            "attempts": attempts,

            "total_assessments": total_assessments,

            "average_score": round(
                average_score,
                1
            ),

            "best_score": best_score,

            "topic_performance": topic_performance,

            "recent_attempts": recent_attempts,

        },
    )


# ============================================================
# HELPER: STUDENT PERFORMANCE
# ============================================================

def get_student_performance(attempts):

    total_attempts = attempts.count()

    average_score = (

        sum(
            attempt.score for attempt in attempts
        ) / total_attempts

        if total_attempts else 0

    )

    topic_data = {}

    difficulty_data = {}

    for attempt in attempts:

        topic_data.setdefault(
            attempt.topic,
            []
        ).append(attempt.score)

        difficulty_data.setdefault(
            attempt.difficulty,
            []
        ).append(attempt.score)

    topic_analysis = []

    for topic, scores in topic_data.items():

        topic_analysis.append({

            "topic": topic,

            "average": round(
                sum(scores) / len(scores),
                1
            ),

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

            "average": round(
                sum(scores) / len(scores),
                1
            ),

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

        "average_score": round(
            average_score,
            1
        ),

        "topic_analysis": topic_analysis,

        "difficulty_analysis": difficulty_analysis,

        "strong_topics": strong_topics,

        "weak_topics": weak_topics,

        "recommended_topics": sorted(
            topic_analysis,
            key=lambda item: item["average"],
        )[:3],

        "trend": trend,

        "improvement": round(
            improvement,
            1
        ),

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
            {
                "has_data": False,
            },
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

    except Exception:

        logger.exception(
            "Learning analysis AI error"
        )

        plan = """
## Personalized Learning Plan Temporarily Unavailable

Your assessment results and performance analysis are still available.
Practise your weak topics and revisit difficult concepts while the
AI service is unavailable.
"""

    return render(
        request,
        "assessment/learning_analysis.html",
        {

            "has_data": True,

            "average_score": data["average_score"],

            "total_attempts": data["total_attempts"],

            "trend": data["trend"],

            "strong_topics": data["strong_topics"][:3],

            "weak_topics": data["weak_topics"][:3],

            "recommended_topics": data["recommended_topics"],

            "difficulty_analysis": data["difficulty_analysis"],

            "plan": plan,

        },
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
            {
                "has_data": False,
            },
        )

    data = get_student_performance(attempts)

    # --------------------------------------------------------
    # DETERMINE CURRENT AND NEXT LEARNING LEVEL
    # --------------------------------------------------------

    current_level = get_adaptive_difficulty(
        data["average_score"]
    )

    progression = get_learning_progression(
        current_level
    )

    # --------------------------------------------------------
    # GROUP ASSESSMENTS BY DIFFICULTY
    # --------------------------------------------------------
    # Assessment form stores Easy / Medium / Hard.
    # Hard is displayed as Advanced in the learning plan.

    difficulty_scores = {

        "Easy": [],

        "Medium": [],

        "Advanced": [],

    }

    for attempt in attempts:

        level = attempt.difficulty.strip().title()

        if level == "Hard":
            level = "Advanced"

        if level in difficulty_scores:

            difficulty_scores[level].append(
                attempt.score
            )

    # --------------------------------------------------------
    # DETERMINE DIFFICULTY STATUS
    # --------------------------------------------------------

    difficulty_status = {}

    for level, scores in difficulty_scores.items():

        average = (
            sum(scores) / len(scores)
            if scores else 0
        )

        difficulty_status[level.lower()] = (
            get_difficulty_status(
                average,
                len(scores),
            )
        )

    # --------------------------------------------------------
    # PREPARE STUDENT DATA FOR AI
    # --------------------------------------------------------

    student_data = {

        "overall_score": data["average_score"],

        "total_attempts": data["total_attempts"],

        "topics": data["topic_analysis"],

        "strong_topics": data["strong_topics"],

        "weak_topics": data["weak_topics"],

        "difficulty_analysis": data["difficulty_analysis"],

        "learning_trend": data["trend"],

        "score_improvement": data["improvement"],

        "current_level": current_level,

        "next_level": progression["next_level"],

    }

    plan_data = None

    try:

        plan = generate_learning_plan(student_data)

        # Support both Pydantic response objects and dictionaries.

        if hasattr(plan, "model_dump"):

            plan_data = plan.model_dump()

        elif isinstance(plan, dict):

            plan_data = plan

        else:

            raise TypeError(
                "The learning-plan generator returned an unsupported format."
            )

        # ----------------------------------------------------
        # USE ACTUAL ASSESSMENT DATA FOR STATUS LABELS
        # ----------------------------------------------------

        for level in (
            "easy",
            "medium",
            "advanced"
        ):

            if isinstance(
                plan_data.get(level),
                dict
            ):

                plan_data[level]["status"] = (
                    difficulty_status[level]
                )

        # ----------------------------------------------------
        # KEEP LEARNING LEVELS CONSISTENT
        # ----------------------------------------------------

        plan_data["current_level"] = current_level

        plan_data["next_level"] = progression["next_level"]

        # ----------------------------------------------------
        # EVIDENCE-BASED LEARNING SUMMARY
        # ----------------------------------------------------
        # The summary is generated from actual assessment records.
        # It does not allow the AI to overstate mastery.

        summary_parts = [

            (
                f"You achieved an overall average of "
                f"{data['average_score']}% across "
                f"{data['total_attempts']} assessment(s)."
            )

        ]

        easy_scores = difficulty_scores["Easy"]

        medium_scores = difficulty_scores["Medium"]

        advanced_scores = difficulty_scores["Advanced"]

        # EASY PERFORMANCE

        if easy_scores:

            easy_average = round(
                sum(easy_scores) / len(easy_scores),
                1
            )

            summary_parts.append(

                f"Your Easy-level average is {easy_average}% "
                f"across {len(easy_scores)} assessment(s)."

            )

        else:

            summary_parts.append(
                "No Easy-level assessment has been recorded yet."
            )

        # MEDIUM PERFORMANCE

        if medium_scores:

            medium_average = round(
                sum(medium_scores) / len(medium_scores),
                1
            )

            summary_parts.append(

                f"Your Medium-level average is {medium_average}% "
                f"across {len(medium_scores)} assessment(s)."

            )

        else:

            summary_parts.append(
                "No Medium-level assessment has been recorded yet."
            )

        # ADVANCED PERFORMANCE

        if advanced_scores:

            advanced_average = round(
                sum(advanced_scores) / len(advanced_scores),
                1
            )

            if len(advanced_scores) == 1:

                summary_parts.append(

                    f"You scored {advanced_average}% in one "
                    "Advanced-level assessment. This is an excellent "
                    "individual result; additional assessments would "
                    "provide stronger evidence of consistent performance."

                )

            else:

                summary_parts.append(

                    f"Your Advanced-level average is {advanced_average}% "
                    f"across {len(advanced_scores)} assessments."

                )

        else:

            summary_parts.append(
                "No Advanced-level assessment has been recorded yet."
            )

        plan_data["learning_summary"] = " ".join(
            summary_parts
        )

        # ----------------------------------------------------
        # ALIGN NEXT ACTION WITH THE NEXT LEARNING LEVEL
        # ----------------------------------------------------

        if current_level == "Advanced":

            plan_data["next_action"] = (

                "Your next goal is to progress towards Expert-level work. "

                "Make an expert-level project your primary activity, "

                "focusing on advanced optimization, complex problem-solving "

                "and practical implementation. You can optionally revisit "

                "Advanced concepts such as model diagnostics, regularization "

                "and feature engineering whenever you need additional support."

            )

        else:

            plan_data["next_action"] = (

                f"Your next goal is to progress towards "

                f"{progression['next_level']} level. "

                f"{progression['focus']} "

                f"{progression['revision']}"

            )

    except Exception:

        logger.exception(
            "Personalized plan generation failed"
        )

        plan_data = None

    # --------------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------------

    context = {

        "has_data": True,

        "plan": plan_data,

        "average_score": data["average_score"],

        "total_attempts": data["total_attempts"],

        "trend": data["trend"],

        "progression": progression,

    }

    return render(
        request,
        "assessment/personalized_plan.html",
        context,
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
            {
                "topics": [],
            },
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

    recommendations = {

        "Beginner": (
            "Start with fundamentals, simple explanations and examples."
        ),

        "Easy": (
            "Strengthen your basics using easy notes and guided practice."
        ),

        "Medium": (
            "Practise medium-level concepts and apply what you learned."
        ),

        "Advanced": (
            "Challenge yourself with advanced concepts and problems."
        ),

        "Expert": (
            "Continue with expert problems, projects and real-world challenges."
        ),

    }

    next_goal = {

        "Beginner": 60,

        "Easy": 70,

        "Medium": 80,

        "Advanced": 100,

        "Expert": 100,

    }

    for topic, data in topic_data.items():

        average_score = round(

            sum(data["scores"]) / len(data["scores"]),

            1

        )

        level = get_adaptive_difficulty(
            average_score
        )

        topics.append({

            "topic": topic,

            "subject": data["subject"],

            "score": average_score,

            "level": level,

            "recommendation": recommendations[level],

            "next_goal": next_goal[level],

            "attempts": len(data["scores"]),

        })

    topics.sort(
        key=lambda item: item["score"]
    )

    return render(
        request,
        "assessment/adaptive_learning.html",
        {
            "topics": topics,
        },
    )


# ============================================================
# ADAPTIVE CONTENT
# ============================================================

@login_required
def adaptive_content(request):

    topic = request.GET.get(
        "topic",
        ""
    ).strip()

    content_type = request.GET.get(
        "type",
        "notes"
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
            "Please select a topic."
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

    score = round(
        score,
        1
    )

    difficulty = get_adaptive_difficulty(
        score
    )

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
                if latest_attempt else ""
            )

            videos = search_adaptive_videos(

                topic=topic,

                difficulty=difficulty,

                max_results=8,

                subject=subject,

            )

        except Exception:

            logger.exception(
                "YouTube search error"
            )

            messages.warning(

                request,

                "Videos are temporarily unavailable. Please try again later.",

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

                # Diagnostic: inspect AI output before caching.

                print(
                    "\n========== RAW LEARNING CONTENT =========="
                )

                print(
                    repr(content[:2000])
                )

                print(
                    "===========================================\n"
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

            except Exception:

                logger.exception(
                    "Adaptive content generation error"
                )

                content = (

                    "## Learning Content Temporarily Unavailable\n\n"

                    "The AI providers could not generate content "

                    "right now. Please try again later. "

                    "Your assessment data has not been affected."

                )

                messages.warning(

                    request,

                    "AI content generation failed. Please try again later.",

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

        except Exception:

            logger.exception(
                "Markdown conversion error"
            )

            # Fallback without optional math extension.

            content_html = markdown.markdown(

                content,

                extensions=[

                    "extra",

                    "tables",

                    "fenced_code",

                ],

            )

        # Diagnostic: compare original text and rendered HTML.

        print(
            "\n========== SPACING DIAGNOSTIC =========="
        )

        print("RAW TEXT:")

        print(
            repr(content[:1500])
        )

        print("\nCONVERTED HTML:")

        print(
            repr(content_html[:1500])
        )

        print(
            "========================================\n"
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