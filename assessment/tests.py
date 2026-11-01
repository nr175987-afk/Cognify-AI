from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from .models import AssessmentAttempt
from .views import (
    get_adaptive_difficulty,
    get_difficulty_status,
    get_learning_progression,
)


class AssessmentAuthenticationTests(TestCase):

    def test_assessment_home_requires_login(self):
        response = self.client.get(
            reverse("assessment_home")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("assessment_home")
        )

    def test_quiz_requires_login(self):
        response = self.client.get(
            reverse("quiz")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("quiz")
        )

    def test_assessment_result_requires_login(self):
        response = self.client.get(
            reverse("assessment_result")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("assessment_result")
        )

    def test_assessment_history_requires_login(self):
        response = self.client.get(
            reverse("assessment_history")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("assessment_history")
        )

    def test_learning_analysis_requires_login(self):
        response = self.client.get(
            reverse("learning_analysis")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("learning_analysis")
        )

    def test_personalized_plan_requires_login(self):
        response = self.client.get(
            reverse("personalized_plan")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("personalized_plan")
        )

    def test_adaptive_learning_requires_login(self):
        response = self.client.get(
            reverse("adaptive_learning")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("adaptive_learning")
        )

    def test_adaptive_content_requires_login(self):
        response = self.client.get(
            reverse("adaptive_content")
        )

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("adaptive_content")
        )


class AdaptiveDifficultyTests(TestCase):

    def test_beginner_level(self):
        self.assertEqual(
            get_adaptive_difficulty(30),
            "Beginner"
        )

    def test_easy_level(self):
        self.assertEqual(
            get_adaptive_difficulty(50),
            "Easy"
        )

    def test_medium_level(self):
        self.assertEqual(
            get_adaptive_difficulty(70),
            "Medium"
        )

    def test_advanced_level(self):
        self.assertEqual(
            get_adaptive_difficulty(90),
            "Advanced"
        )

    def test_expert_level(self):
        self.assertEqual(
            get_adaptive_difficulty(100),
            "Expert"
        )


class LearningProgressionTests(TestCase):

    def test_advanced_progression(self):
        progression = get_learning_progression("Advanced")

        self.assertEqual(
            progression["next_level"],
            "Expert"
        )

    def test_easy_progression(self):
        progression = get_learning_progression("Easy")

        self.assertEqual(
            progression["next_level"],
            "Medium"
        )

    def test_expert_progression(self):
        progression = get_learning_progression("Expert")

        self.assertEqual(
            progression["next_level"],
            "Expert"
        )


class DifficultyStatusTests(TestCase):

    def test_unassessed_status(self):
        self.assertEqual(
            get_difficulty_status(0, 0),
            "Not assessed"
        )

    def test_single_perfect_assessment(self):
        self.assertEqual(
            get_difficulty_status(100, 1),
            "Excellent performance (100% on 1 assessment)"
        )

    def test_multiple_perfect_assessments(self):
        self.assertEqual(
            get_difficulty_status(100, 2),
            "Excellent performance (100% across 2 assessments)"
        )

    def test_proficient_status(self):
        self.assertEqual(
            get_difficulty_status(85, 2),
            "Proficient"
        )

    def test_developing_status(self):
        self.assertEqual(
            get_difficulty_status(65, 2),
            "Developing"
        )

    def test_needs_improvement_status(self):
        self.assertEqual(
            get_difficulty_status(45, 2),
            "Needs improvement"
        )


class AssessmentHistoryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="assessmentstudent",
            password="StrongTestPass123!"
        )

        self.client.login(
            username="assessmentstudent",
            password="StrongTestPass123!"
        )

    def test_empty_assessment_history_loads(self):
        response = self.client.get(
            reverse("assessment_history")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.context["total_assessments"],
            0
        )

    def test_assessment_history_displays_attempts(self):

        AssessmentAttempt.objects.create(
            user=self.user,
            subject="Python",
            topic="Exception Handling",
            difficulty="Easy",
            total_questions=5,
            correct_answers=4,
            score=80
        )

        response = self.client.get(
            reverse("assessment_history")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.context["total_assessments"],
            1
        )

        self.assertEqual(
            response.context["average_score"],
            80
        )


class AdaptiveLearningTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="adaptivestudent",
            password="StrongTestPass123!"
        )

        self.client.login(
            username="adaptivestudent",
            password="StrongTestPass123!"
        )

    def test_adaptive_learning_without_attempts(self):

        response = self.client.get(
            reverse("adaptive_learning")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.context["topics"],
            []
        )

    def test_adaptive_learning_with_attempts(self):

        AssessmentAttempt.objects.create(
            user=self.user,
            subject="Python",
            topic="Functions",
            difficulty="Easy",
            total_questions=5,
            correct_answers=5,
            score=100
        )

        response = self.client.get(
            reverse("adaptive_learning")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            len(response.context["topics"]),
            1
        )

        self.assertEqual(
            response.context["topics"][0]["level"],
            "Expert"
        )