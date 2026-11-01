from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import StudentProfile


class AccountPageTests(TestCase):

    def test_home_redirects_to_login(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(
            response,
            reverse("login")
        )

    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("dashboard")
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))

        self.assertRedirects(
            response,
            reverse("login") + "?next=" + reverse("profile")
        )


class AccountRegistrationTests(TestCase):

    def test_user_can_register(self):

        response = self.client.post(
            reverse("register"),
            {
                "username": "teststudent",
                "email": "student@example.com",
                "password": "StrongTestPass123!",
                "password2": "StrongTestPass123!",
            }
        )

        self.assertRedirects(
            response,
            reverse("login")
        )

        self.assertTrue(
            User.objects.filter(
                username="teststudent"
            ).exists()
        )

        user = User.objects.get(
            username="teststudent"
        )

        self.assertTrue(
            StudentProfile.objects.filter(
                user=user
            ).exists()
        )

    def test_registration_rejects_password_mismatch(self):

        response = self.client.post(
            reverse("register"),
            {
                "username": "teststudent",
                "email": "student@example.com",
                "password": "StrongTestPass123!",
                "password2": "DifferentPass123!",
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                username="teststudent"
            ).exists()
        )


class AccountLoginTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="teststudent",
            password="StrongTestPass123!"
        )

    def test_user_can_login(self):

        response = self.client.post(
            reverse("login"),
            {
                "username": "teststudent",
                "password": "StrongTestPass123!",
            }
        )

        self.assertRedirects(
            response,
            reverse("dashboard")
        )

    def test_login_rejects_invalid_password(self):

        response = self.client.post(
            reverse("login"),
            {
                "username": "teststudent",
                "password": "WrongPassword123!",
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            response.wsgi_request.user.is_authenticated
        )