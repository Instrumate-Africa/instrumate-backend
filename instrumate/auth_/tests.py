from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from auth_.models import CustomUser


class AuthTests(APITestCase):

    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.refresh_url = reverse("refresh")
        self.logout_url = reverse("logout")

        self.user = CustomUser.objects.create_user(
            username="jude",
            email="jude@example.com",
            password="password123",
            is_student=True,
            is_teacher=False,
        )

    # ==========================
    # Registration Tests
    # ==========================

    def test_register_student_success(self):
        data = {
            "username": "john",
            "email": "john@example.com",
            "password": "password123",
            "is_student": True,
            "is_teacher": False,
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["message"],
            "successful registration"
        )
        self.assertTrue(
            CustomUser.objects.filter(username="john").exists()
        )

    def test_register_teacher_success(self):
        data = {
            "username": "mary",
            "email": "mary@example.com",
            "password": "password123",
            "is_student": False,
            "is_teacher": True,
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["message"],
            "successful registration"
        )
        self.assertTrue(
            CustomUser.objects.filter(username="mary").exists()
        )

    def test_register_student_and_teacher_fails(self):
        data = {
            "username": "peter",
            "email": "peter@example.com",
            "password": "password123",
            "is_student": True,
            "is_teacher": True,
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
        "One cannot be a teacher and student at the same time",
        str(response.data),
    )

    def test_register_missing_username(self):
        data = {
            "email": "john@example.com",
            "password": "password123",
            "is_student": True,
            "is_teacher": False,
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================
    # Login Tests
    # ==========================

    def test_login_success(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "jude",
                "password": "password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "login successful"
        )
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.cookies)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "jude",
                "password": "wrongpassword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "invalid login"
        )

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "unknown",
                "password": "password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "invalid login"
        )

    # ==========================
    # Refresh Token Tests
    # ==========================

    def test_refresh_token_success(self):
        login = self.client.post(
            self.login_url,
            {
                "username": "jude",
                "password": "password123",
            },
            format="json",
        )

        self.client.cookies["refresh_token"] = (
            login.cookies["refresh_token"].value
        )

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "successful refresh"
        )
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.cookies)

    def test_refresh_without_token(self):
         # Ensure there are no cookies
        self.client.cookies.clear()

        response = self.client.post(self.refresh_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    # ==========================
    # Logout Tests
    # ==========================

    def test_logout(self):
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "user logged out"
        )

        self.assertEqual(
            response.cookies["refresh_token"].value,
            ""
        )

        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            0
        )


