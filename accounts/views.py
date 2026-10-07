from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Max
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import StudentProfile
from assessment.models import AssessmentAttempt


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return redirect("login")


def register(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        form_data = {
            "username": username,
            "email": email,
        }

        if not username:
            messages.error(request, "Please enter a username.")
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        if not email:
            messages.error(request, "Please enter your email address.")
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        if password != password2:
            messages.error(request, "Passwords do not match.")
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        if len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )
            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        try:
            validate_password(password)

        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)

            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        try:

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "department": "",
                        "semester": 1
                    }
                )

        except Exception:
            messages.error(
                request,
                "Unable to create your account. Please try again."
            )

            return render(
                request,
                "accounts/register.html",
                {"form_data": form_data}
            )

        messages.success(
            request,
            "Account created successfully. Please login."
        )

        return redirect("login")

    return render(request, "accounts/register.html")


def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    username_value = ""

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        username_value = username

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "accounts/login.html",
        {
            "username_value": username_value
        }
    )


def logout_view(request):

    logout(request)

    return redirect("login")


def _profile_completion(profile):

    fields = [
        profile.department,
        profile.semester,
        profile.skills,
        profile.interests,
        profile.career_goal,
        profile.study_hours,
        profile.preferred_learning_method,
    ]

    completed = 0

    for value in fields:

        if value is not None and str(value).strip():
            completed += 1

    return round((completed / len(fields)) * 100)


def _assessment_streak(attempts):

    dates = set(
        attempts.values_list(
            "created_at__date",
            flat=True
        )
    )

    if not dates:
        return 0

    current_date = timezone.localdate()

    if current_date not in dates:
        current_date = current_date - timedelta(days=1)

    streak = 0

    while current_date in dates:

        streak += 1

        current_date = current_date - timedelta(days=1)

    return streak


@login_required(login_url="login")
def dashboard(request):

    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "department": "",
            "semester": 1
        }
    )

    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    )

    statistics = attempts.aggregate(
        average=Avg("score"),
        best=Max("score")
    )

    average_score = round(
        float(statistics["average"] or 0),
        1
    )

    best_score = round(
        float(statistics["best"] or 0),
        1
    )

    total_assessments = attempts.count()

    total_topics = attempts.values(
        "topic"
    ).distinct().count()

    assessment_streak = _assessment_streak(attempts)

    recent_attempts = attempts.order_by(
        "-created_at"
    )[:5]

    latest_attempt = attempts.order_by(
        "-created_at"
    ).first()

    if average_score >= 80:
        learning_message = "Excellent progress. You are ready for more challenging concepts."

    elif average_score >= 60:
        learning_message = "Good progress. Keep strengthening your concepts and practice."

    elif total_assessments > 0:
        learning_message = "Focus on fundamentals and use adaptive learning to improve."

    else:
        learning_message = "Take your first assessment and let CognifyAI understand your learning level."

    context = {
        "profile": profile,
        "profile_completion": _profile_completion(profile),

        "average_score": average_score,
        "best_score": best_score,
        "total_assessments": total_assessments,
        "total_topics": total_topics,
        "assessment_streak": assessment_streak,

        "recent_attempts": recent_attempts,
        "latest_attempt": latest_attempt,

        "learning_message": learning_message,
    }

    return render(
        request,
        "accounts/dashboard.html",
        context
    )


@login_required(login_url="login")
def profile(request):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "department": "",
            "semester": 1
        }
    )

    if request.method == "POST":

        department = request.POST.get(
            "department",
            ""
        ).strip()

        semester_raw = request.POST.get(
            "semester",
            "1"
        ).strip()

        skills = request.POST.get(
            "skills",
            ""
        ).strip()

        interests = request.POST.get(
            "interests",
            ""
        ).strip()

        career_goal = request.POST.get(
            "career_goal",
            ""
        ).strip()

        study_hours = request.POST.get(
            "study_hours",
            ""
        ).strip()

        preferred_learning_method = request.POST.get(
            "preferred_learning_method",
            ""
        ).strip()

        try:
            semester = int(semester_raw)

            if semester < 1 or semester > 8:
                raise ValueError

        except ValueError:

            messages.error(
                request,
                "Semester must be between 1 and 8."
            )

            return redirect("profile")

        student_profile.department = department
        student_profile.semester = semester
        student_profile.skills = skills
        student_profile.interests = interests
        student_profile.career_goal = career_goal
        student_profile.preferred_learning_method = (
            preferred_learning_method
        )

        if study_hours:

            try:
                student_profile.study_hours = float(study_hours)

            except ValueError:

                messages.error(
                    request,
                    "Study hours must be a valid number."
                )

                return redirect("profile")

        student_profile.save()

        messages.success(
            request,
            "Your profile has been updated successfully."
        )

        return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": student_profile,
            "profile_completion": _profile_completion(
                student_profile
            )
        }
    )