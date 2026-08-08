from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from auth_.models import CustomUser
from lms.models import Course, Module, Chapter


class LMSTests(APITestCase):

    def setUp(self):
        # Create user
        self.user = CustomUser.objects.create_user(
            username="jude",
            email="jude@example.com",
            password="password123",
            is_student=True,
            is_teacher=False,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

        # Create sample data
        self.course = Course.objects.create(
            title="Python",
            description="Python Course"
        )

        self.module = Module.objects.create(
            course=self.course,
            name="Introduction",
            sort_index=1
        )

        self.chapter = Chapter.objects.create(
            module=self.module,
            title="Variables",
            sort_index=1,
            is_signable=True,
            content_filepath="test.csv"
        )

    # ---------------- COURSE ---------------- #

    def test_list_courses(self):
        url = reverse("course-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_course(self):
        url = reverse("course-list")

        data = {
            "title": "Django",
            "description": "REST API"
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)

    # ---------------- MODULE ---------------- #

    def test_list_modules(self):
        url = reverse("module-list") + f"?course_id={self.course.id}"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_modules_without_course_id(self):
        url = reverse("module-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_module(self):
        url = reverse("module-detail", args=[self.module.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---------------- CHAPTER ---------------- #

    def test_list_chapters(self):
        url = reverse("chapter-list") + f"?module_id={self.module.id}"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_chapters_without_module(self):
        url = reverse("chapter-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_chapter(self):
        url = reverse("chapter-detail", args=[self.chapter.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)