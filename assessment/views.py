from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import AssessmentAttempt, LearningContent

from .ai_generator import generate_questions
from .ai_generator import generate_learning_plan
from .ai_generator import generate_adaptive_notes
from .ai_generator import generate_adaptive_content
from .ai_generator import search_adaptive_videos

# ============================================================
# ASSESSMENT HOME
# ============================================================

@login_required
def assessment_home(request):

    if request.method == "POST":

        subject = request.POST.get("subject")
        topic = request.POST.get("topic")
        difficulty = request.POST.get("difficulty")

        number_of_questions = int(
            request.POST.get(
                "number_of_questions",
                5
            )
        )

        try:

            questions = generate_questions(
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                number_of_questions=number_of_questions
            )

            question_data = []

            for question in questions:

                question_data.append({

                    "question": question.question,

                    "option_a": question.option_a,

                    "option_b": question.option_b,

                    "option_c": question.option_c,

                    "option_d": question.option_d,

                    "correct_answer":
                        question.correct_answer,

                    "explanation":
                        question.explanation,

                })

            # Store questions in session

            request.session[
                "generated_questions"
            ] = question_data

            request.session[
                "assessment_subject"
            ] = subject

            request.session[
                "assessment_topic"
            ] = topic

            request.session[
                "assessment_difficulty"
            ] = difficulty

            return redirect("quiz")

        except Exception as e:

            return render(
                request,
                "assessment/assessment.html",
                {
                    "error": str(e)
                }
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

    # No questions available

    if not questions:

        return redirect(
            "assessment_home"
        )

    # --------------------------------------------------------
    # SUBMIT QUIZ
    # --------------------------------------------------------

    if request.method == "POST":

        correct = 0

        for index, question in enumerate(
            questions
        ):

            answer = request.POST.get(
                f"question_{index}"
            )

            if answer == question[
                "correct_answer"
            ]:

                correct += 1

        total = len(questions)

        if total > 0:

            score = (
                correct / total
            ) * 100

        else:

            score = 0

        # ----------------------------------------------------
        # GET ASSESSMENT INFORMATION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SAVE RESULT
        # ----------------------------------------------------

        AssessmentAttempt.objects.create(

            user=request.user,

            subject=subject,

            topic=topic,

            difficulty=difficulty,

            total_questions=total,

            correct_answers=correct,

            score=score

        )

        # ----------------------------------------------------
        # SAVE RESULT IN SESSION
        # ----------------------------------------------------

        request.session[
            "last_score"
        ] = score

        request.session[
            "last_correct"
        ] = correct

        request.session[
            "last_total"
        ] = total

        # Remove old generated questions

        request.session.pop(
            "generated_questions",
            None
        )

        return redirect(
            "assessment_result"
        )

    # --------------------------------------------------------
    # SHOW QUIZ
    # --------------------------------------------------------

    return render(
        request,
        "assessment/quiz.html",
        {
            "questions": questions
        }
    )


# ============================================================
# ASSESSMENT RESULT
# ============================================================

@login_required
def assessment_result(request):

    score = request.session.get(
        "last_score",
        0
    )

    correct = request.session.get(
        "last_correct",
        0
    )

    total = request.session.get(
        "last_total",
        0
    )

    return render(
        request,
        "assessment/result.html",
        {
            "score": score,
            "correct": correct,
            "total": total,
        }
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

    if total_assessments > 0:

        average_score = (
            sum(
                attempt.score
                for attempt in attempts
            )
            / total_assessments
        )

        best_score = max(
            attempt.score
            for attempt in attempts
        )

    else:

        average_score = 0
        best_score = 0

    # --------------------------------------------------------
    # TOPIC PERFORMANCE
    # --------------------------------------------------------

    topic_data = {}

    for attempt in attempts:

        topic = attempt.topic

        if topic not in topic_data:

            topic_data[topic] = []

        topic_data[topic].append(
            attempt.score
        )

    topic_performance = []

    for topic, scores in topic_data.items():

        average = (
            sum(scores)
            / len(scores)
        )

        topic_performance.append({

            "topic": topic,

            "average": round(
                average,
                1
            ),

            "attempts": len(scores)

        })

    topic_performance.sort(
        key=lambda x: x["average"],
        reverse=True
    )

    recent_attempts = list(
        attempts[:10]
    )

    recent_attempts.reverse()

    context = {

        "attempts": attempts,

        "total_assessments":
            total_assessments,

        "average_score":
            average_score,

        "best_score":
            best_score,

        "topic_performance":
            topic_performance,

        "recent_attempts":
            recent_attempts,

    }

    return render(
        request,
        "assessment/history.html",
        context
    )


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
                "has_data": False
            }
        )

    # --------------------------------------------------------
    # OVERALL PERFORMANCE
    # --------------------------------------------------------

    total_attempts = attempts.count()

    average_score = (
        sum(
            attempt.score
            for attempt in attempts
        )
        / total_attempts
    )

    # --------------------------------------------------------
    # TOPIC PERFORMANCE
    # --------------------------------------------------------

    topic_data = {}

    for attempt in attempts:

        topic = attempt.topic

        if topic not in topic_data:

            topic_data[topic] = {
                "scores": [],
                "attempts": 0
            }

        topic_data[topic][
            "scores"
        ].append(
            attempt.score
        )

        topic_data[topic][
            "attempts"
        ] += 1

    topic_analysis = []

    for topic, data in topic_data.items():

        average = (
            sum(data["scores"])
            / len(data["scores"])
        )

        topic_analysis.append({

            "topic": topic,

            "average": round(
                average,
                1
            ),

            "attempts":
                data["attempts"]

        })

    topic_analysis.sort(
        key=lambda x: x["average"],
        reverse=True
    )

    # --------------------------------------------------------
    # STRONG / WEAK TOPICS
    # --------------------------------------------------------

    strong_topics = [

        topic
        for topic in topic_analysis
        if topic["average"] >= 80

    ]

    weak_topics = [

        topic
        for topic in topic_analysis
        if topic["average"] < 60

    ]

    # --------------------------------------------------------
    # DIFFICULTY ANALYSIS
    # --------------------------------------------------------

    difficulty_data = {}

    for attempt in attempts:

        difficulty = attempt.difficulty

        if difficulty not in difficulty_data:

            difficulty_data[difficulty] = []

        difficulty_data[
            difficulty
        ].append(
            attempt.score
        )

    difficulty_analysis = []

    for difficulty, scores in difficulty_data.items():

        average = (
            sum(scores)
            / len(scores)
        )

        difficulty_analysis.append({

            "difficulty": difficulty,

            "average": round(
                average,
                1
            ),

            "attempts": len(scores)

        })

    # --------------------------------------------------------
    # LEARNING TREND
    # --------------------------------------------------------

    if total_attempts >= 2:

        first_score = attempts.first().score

        last_score = attempts.last().score

        improvement = (
            last_score - first_score
        )

        if improvement > 5:

            trend = "improving"

        elif improvement < -5:

            trend = "declining"

        else:

            trend = "stable"

    else:

        improvement = 0

        trend = "insufficient"

    # --------------------------------------------------------
    # RECOMMENDED TOPICS
    # --------------------------------------------------------

    recommended_topics = sorted(
        topic_analysis,
        key=lambda x: x["average"]
    )[:3]

    # --------------------------------------------------------
    # DATA FOR GEMINI
    # --------------------------------------------------------

    student_data = {

        "overall_score":
            round(
                average_score,
                1
            ),

        "total_attempts":
            total_attempts,

        "topics":
            topic_analysis,

        "strong_topics":
            strong_topics,

        "weak_topics":
            weak_topics,

        "difficulty_analysis":
            difficulty_analysis,

        "learning_trend":
            trend,

        "score_improvement":
            round(
                improvement,
                1
            )

    }

    # --------------------------------------------------------
    # AI PLAN
    # --------------------------------------------------------

    try:

        plan = generate_learning_plan(
            student_data
        )

    except Exception as e:

        if (
            "429" in str(e)
            or
            "RESOURCE_EXHAUSTED"
            in str(e)
        ):

            plan = """
## 🤖 AI Plan Temporarily Unavailable

Your learning analysis has been calculated successfully.

The Gemini API has temporarily reached its quota.

You can still use:

📊 Performance Analysis  
🎯 Topic Recommendations  
📝 Assessments  
🧠 Adaptive Learning  

Please try the AI plan again later.
"""

        else:

            plan = """
## 🤖 AI Plan Temporarily Unavailable

Your performance data is safe.

Please try again later.
"""

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "has_data": True,

        "average_score":
            round(
                average_score,
                1
            ),

        "total_attempts":
            total_attempts,

        "trend":
            trend,

        "strong_topics":
            strong_topics[:3],

        "weak_topics":
            weak_topics[:3],

        "recommended_topics":
            recommended_topics,

        "difficulty_analysis":
            difficulty_analysis,

        "plan":
            plan

    }

    return render(
        request,
        "assessment/learning_analysis.html",
        context
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
                "has_data": False
            }
        )

    # --------------------------------------------------------
    # OVERALL
    # --------------------------------------------------------

    total_attempts = attempts.count()

    average_score = (
        sum(
            attempt.score
            for attempt in attempts
        )
        / total_attempts
    )

    # --------------------------------------------------------
    # TOPIC PERFORMANCE
    # --------------------------------------------------------

    topic_data = {}

    for attempt in attempts:

        topic = attempt.topic

        if topic not in topic_data:

            topic_data[topic] = []

        topic_data[topic].append(
            attempt.score
        )

    topic_analysis = []

    for topic, scores in topic_data.items():

        average = (
            sum(scores)
            / len(scores)
        )

        topic_analysis.append({

            "topic": topic,

            "average": round(
                average,
                1
            ),

            "attempts": len(scores)

        })

    # --------------------------------------------------------
    # STRONG TOPICS
    # --------------------------------------------------------

    strong_topics = [

        item
        for item in topic_analysis
        if item["average"] >= 80

    ]

    # --------------------------------------------------------
    # WEAK TOPICS
    # --------------------------------------------------------

    weak_topics = [

        item
        for item in topic_analysis
        if item["average"] < 60

    ]

    # --------------------------------------------------------
    # DIFFICULTY PERFORMANCE
    # --------------------------------------------------------

    difficulty_data = {}

    for attempt in attempts:

        difficulty = attempt.difficulty

        if difficulty not in difficulty_data:

            difficulty_data[difficulty] = []

        difficulty_data[
            difficulty
        ].append(
            attempt.score
        )

    difficulty_analysis = []

    for difficulty, scores in difficulty_data.items():

        average = (
            sum(scores)
            / len(scores)
        )

        difficulty_analysis.append({

            "difficulty": difficulty,

            "average": round(
                average,
                1
            ),

            "attempts": len(scores)

        })

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    if total_attempts >= 2:

        first_score = attempts.first().score

        last_score = attempts.last().score

        improvement = (
            last_score - first_score
        )

        if improvement > 5:

            trend = "Improving"

        elif improvement < -5:

            trend = "Declining"

        else:

            trend = "Stable"

    else:

        improvement = 0

        trend = "Insufficient data"

    # --------------------------------------------------------
    # DATA FOR GEMINI
    # --------------------------------------------------------

    student_data = f"""

Student Learning Performance

Overall Average:
{average_score:.1f}%

Total Assessments:
{total_attempts}

Strong Topics:
{strong_topics}

Weak Topics:
{weak_topics}

Topic Performance:
{topic_analysis}

Difficulty Performance:
{difficulty_analysis}

Learning Trend:
{trend}

Score Improvement:
{improvement}%

"""

    # --------------------------------------------------------
    # GENERATE PLAN
    # --------------------------------------------------------

    try:

        plan = generate_learning_plan(
            student_data
        )

    except Exception as e:

        if (
            "429" in str(e)
            or
            "RESOURCE_EXHAUSTED"
            in str(e)
        ):

            plan = """
## 🤖 AI Plan Temporarily Unavailable

Your performance data is available,
but the Gemini API quota has temporarily
been reached.

Please try again later.
"""

        else:

            plan = """
## 🤖 AI Plan Temporarily Unavailable

Something went wrong while generating
your personalized plan.

Please try again later.
"""

    context = {

        "has_data": True,

        "plan": plan,

        "average_score":
            round(
                average_score,
                1
            ),

        "total_attempts":
            total_attempts,

        "trend":
            trend,

    }

    return render(
        request,
        "assessment/personalized_plan.html",
        context
    )


# ============================================================
# ADAPTIVE LEARNING
# ============================================================

@login_required
def adaptive_learning(request):

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("-created_at")

    # --------------------------------------------------------
    # NO DATA
    # --------------------------------------------------------

    if not attempts.exists():

        return render(
            request,
            "assessment/adaptive_learning.html",
            {
                "topics": []
            }
        )

    # --------------------------------------------------------
    # GROUP BY TOPIC
    # --------------------------------------------------------

    topic_data = {}

    for attempt in attempts:

        topic = attempt.topic

        if topic not in topic_data:

            topic_data[topic] = {

                "subject":
                    attempt.subject,

                "scores": [],

                "latest_score":
                    attempt.score

            }

        topic_data[
            topic
        ][
            "scores"
        ].append(
            attempt.score
        )

    # --------------------------------------------------------
    # CREATE ADAPTIVE TOPICS
    # --------------------------------------------------------

    topics = []

    for topic, data in topic_data.items():

        scores = data["scores"]

        average_score = (
            sum(scores)
            / len(scores)
        )

        average_score = round(
            average_score,
            1
        )

        # ================================================
        # ADAPTIVE LEVEL
        # ================================================

        if average_score < 40:

            level = "Beginner"

            recommendation = (
                "Start with fundamentals, "
                "simple explanations and examples."
            )

            next_goal = 60

        elif average_score < 60:

            level = "Easy"

            recommendation = (
                "Strengthen your basics using "
                "easy notes and guided practice."
            )

            next_goal = 70

        elif average_score < 80:

            level = "Medium"

            recommendation = (
                "Your foundation is developing. "
                "Practice medium-level concepts."
            )

            next_goal = 80

        elif average_score < 100:

            level = "Advanced"

            recommendation = (
                "Excellent progress. Challenge yourself "
                "with advanced concepts and problems."
            )

            next_goal = 100

        else:

            level = "Expert"

            recommendation = (
                "🎉 Mastered! Continue with expert "
                "problems, projects and real-world challenges."
            )

            next_goal = 100

        topics.append({

            "topic":
                topic,

            "subject":
                data["subject"],

            "score":
                average_score,

            "level":
                level,

            "recommendation":
                recommendation,

            "next_goal":
                next_goal,

            "attempts":
                len(scores)

        })

    # --------------------------------------------------------
    # LOWEST PERFORMANCE FIRST
    # --------------------------------------------------------

    topics.sort(
        key=lambda x: x["score"]
    )

    return render(
        request,
        "assessment/adaptive_learning.html",
        {
            "topics": topics
        }
    )


# ============================================================
# ADAPTIVE CONTENT
# ============================================================

@login_required
def adaptive_content(request):

    topic = request.GET.get("topic", "").strip()
    content_type = request.GET.get(
        "type",
        "notes"
    )

    if not topic:
        return redirect("adaptive_learning")

    # ========================================================
    # GET STUDENT ATTEMPTS FOR THIS TOPIC
    # ========================================================

    attempts = AssessmentAttempt.objects.filter(
        user=request.user,
        topic=topic
    ).order_by("-created_at")

    if attempts.exists():

        score = (
            sum(
                attempt.score
                for attempt in attempts
            )
            / attempts.count()
        )

    else:

        score = 0

    score = round(score, 1)

    # ========================================================
    # ADAPTIVE DIFFICULTY
    # ========================================================

    if score < 40:

        difficulty = "Beginner"

    elif score < 60:

        difficulty = "Easy"

    elif score < 80:

        difficulty = "Medium"

    elif score < 100:

        difficulty = "Advanced"

    else:

        difficulty = "Expert"

    # ========================================================
    # VARIABLES
    # ========================================================

    content = ""
    content_html = ""
    videos = []

    # ========================================================
    # VIDEOS
    # ========================================================

    if content_type == "videos":

        try:

            latest_attempt = attempts.first()

            subject = ""

            if latest_attempt:
                subject = latest_attempt.subject

            videos = search_adaptive_videos(
                topic=topic,
                difficulty=difficulty,
                max_results=8,
                subject=subject
            )

        except Exception as e:

            print(
                "YouTube Error:",
                e
            )

            videos = []

    # ========================================================
    # NOTES / QUESTIONS / REAL WORLD
    # ========================================================

    else:

        saved_content = LearningContent.objects.filter(
            topic=topic,
            content_type=content_type,
            difficulty=difficulty
        ).first()

        if saved_content:

            content = saved_content.content

        else:

            try:

                content = generate_adaptive_content(
                    topic=topic,
                    content_type=content_type,
                    difficulty=difficulty
                )

                LearningContent.objects.create(
                    topic=topic,
                    content_type=content_type,
                    difficulty=difficulty,
                    content=content
                )

            except Exception as e:

                print(
                    "Gemini Error:",
                    e
                )

                if content_type == "questions":

                    content = """
# Practice Questions

Content is temporarily unavailable.

Please try again later.
"""

                elif content_type == "realworld":

                    content = """
# Real-World Challenges

Problems are temporarily unavailable.

Please try again later.
"""

                else:

                    content = """
# Personalized Learning Content

Content is temporarily unavailable.

Please try again later.
"""

        # ====================================================
        # MARKDOWN → HTML
        # ====================================================

        try:

            import markdown

            content_html = markdown.markdown(
                content,
                extensions=[
                    "extra",
                    "tables",
                    "fenced_code",
                    "nl2br"
                ]
            )

        except Exception as e:

            print(
                "Markdown Error:",
                e
            )

            content_html = content

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        "topic":
            topic,

        "content_type":
            content_type,

        "difficulty":
            difficulty,

        "score":
            score,

        "content":
            content,

        "content_html":
            content_html,

        "videos":
            videos,

    }

    return render(
        request,
        "assessment/adaptive_content.html",
        context
    )