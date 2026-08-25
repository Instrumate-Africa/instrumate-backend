import os
from tempfile import TemporaryDirectory

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_.models import CustomUser
from lms.models import (
    Chapter,
    CompletedCourse,
    CompletedSignable,
    Course,
    CourseProgression,
    Module,
)


class LMSViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="jude",
            email="jude@example.com",
            password="password123",
            is_student=True,
            is_teacher=False,
        )
        self.other_user = CustomUser.objects.create_user(
            username="amina",
            email="amina@example.com",
            password="password123",
            is_student=True,
            is_teacher=False,
        )
        self.client.force_authenticate(user=self.user)

        self.course = Course.objects.create(
            title="INTRO TO KSL",
            description="An introduction to Kenyan Sign Language",
        )
        self.other_course = Course.objects.create(
            title="Advanced KSL",
            description="More Kenyan Sign Language lessons",
        )

        self.module_1 = Module.objects.create(
            course=self.course,
            name="Basics",
            sort_index=1,
        )
        self.module_2 = Module.objects.create(
            course=self.course,
            name="Family",
            sort_index=2,
        )
        self.module_3 = Module.objects.create(
            course=self.course,
            name="Food",
            sort_index=3,
        )
        self.other_course_module = Module.objects.create(
            course=self.other_course,
            name="Other Course Module",
            sort_index=1,
        )

        self.chapter_1 = Chapter.objects.create(
            module=self.module_1,
            title="Intro",
            sort_index=1,
            is_signable=False,
            content_filepath="intro.md",
        )
        self.chapter_2 = Chapter.objects.create(
            module=self.module_1,
            title="Family Signs",
            sort_index=2,
            is_signable=True,
            content_filepath="family.csv",
        )
        self.chapter_3 = Chapter.objects.create(
            module=self.module_1,
            title="Food Signs",
            sort_index=3,
            is_signable=True,
            content_filepath="food.csv",
        )
        self.module_2_chapter = Chapter.objects.create(
            module=self.module_2,
            title="Module 2 Chapter",
            sort_index=1,
            is_signable=True,
            content_filepath="module-2.csv",
        )

    def create_progression(self, module=None, chapter=None, user=None):
        return CourseProgression.objects.create(
            user=user or self.user,
            course=self.course,
            current_module=module or self.module_2,
            current_chapter=chapter or self.chapter_2,
        )

    def assert_status_by_id(self, response, expected_statuses):
        actual_statuses = {item["id"]: item["status"] for item in response.data}
        self.assertEqual(actual_statuses, expected_statuses)

    def test_protected_viewsets_require_authentication(self):
        self.client.force_authenticate(user=None)

        protected_urls = [
            reverse("course-list"),
            reverse("module-list"),
            reverse("chapter-list"),
            reverse("completedsignable-list"),
            reverse("courseprogression-list"),
            reverse("completedcourse-list"),
        ]

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_courses_returns_existing_courses(self):
        response = self.client.get(reverse("course-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {course["title"] for course in response.data},
            {"INTRO TO KSL", "Advanced KSL"},
        )

    def test_create_course_persists_course(self):
        response = self.client.post(
            reverse("course-list"),
            {
                "title": "KSL 2",
                "description": "KSL level 2",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Course.objects.filter(title="KSL 2").exists())

    def test_list_modules_requires_course_id(self):
        response = self.client.get(reverse("module-list"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "expected 'course_id' parameter"})

    def test_list_modules_filters_by_course_and_marks_incomplete_without_progression(self):
        response = self.client.get(
            reverse("module-list"),
            {"course_id": self.course.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertNotIn(self.other_course_module.id, [item["id"] for item in response.data])
        self.assert_status_by_id(
            response,
            {
                self.module_1.id: "incomplete",
                self.module_2.id: "incomplete",
                self.module_3.id: "incomplete",
            },
        )

    def test_list_modules_marks_statuses_from_current_progression(self):
        self.create_progression(module=self.module_2, chapter=self.chapter_2)

        response = self.client.get(
            reverse("module-list"),
            {"course_id": self.course.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_status_by_id(
            response,
            {
                self.module_1.id: "complete",
                self.module_2.id: "pending",
                self.module_3.id: "incomplete",
            },
        )

    def test_retrieve_first_module_is_allowed_without_progression(self):
        response = self.client.get(reverse("module-detail", args=[self.module_1.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.module_1.id)

    def test_retrieve_future_module_is_blocked_without_progression(self):
        response = self.client.get(reverse("module-detail", args=[self.module_2.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"error": "Not allowed to access this module when the previous ones are not done"},
        )

    def test_retrieve_future_module_is_blocked_with_progression(self):
        self.create_progression(module=self.module_2, chapter=self.chapter_2)

        response = self.client.get(reverse("module-detail", args=[self.module_3.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"error": "Not allowed to access this module when the previous ones are not done"},
        )

    ## CHAPTER TESTING ##
    def test_list_chapters_requires_module_id(self):
        response = self.client.get(reverse("chapter-list"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "expected 'module_id' parameter"})

    def test_list_chapters_marks_incomplete_without_progression(self):
        response = self.client.get(
            reverse("chapter-list"),
            {"module_id": self.module_1.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_status_by_id(
            response,
            {
                self.chapter_1.id: "incomplete",
                self.chapter_2.id: "incomplete",
                self.chapter_3.id: "incomplete",
            },
        )

    def test_list_chapters_marks_statuses_from_current_progression(self):
        self.create_progression(module=self.module_1, chapter=self.chapter_2)

        response = self.client.get(
            reverse("chapter-list"),
            {"module_id": self.module_1.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_status_by_id(
            response,
            {
                self.chapter_1.id: "complete",
                self.chapter_2.id: "pending",
                self.chapter_3.id: "incomplete",
            },
        )

    def test_list_chapters_marks_incomplete_when_progression_is_for_another_module(self):
        self.create_progression(module=self.module_2, chapter=self.module_2_chapter)

        response = self.client.get(
            reverse("chapter-list"),
            {"module_id": self.module_1.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_status_by_id(
            response,
            {
                self.chapter_1.id: "incomplete",
                self.chapter_2.id: "incomplete",
                self.chapter_3.id: "incomplete",
            },
        )

    def test_retrieve_first_chapter_is_allowed_without_progression(self):
        response = self.client.get(reverse("chapter-detail", args=[self.chapter_1.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.chapter_1.id)

    def test_retrieve_future_chapter_is_blocked_without_progression(self):
        response = self.client.get(reverse("chapter-detail", args=[self.chapter_2.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"error": "Not allowed to access this chapter when the previous ones are not done"},
        )

    def test_retrieve_future_chapter_is_blocked_with_progression(self):
        self.create_progression(module=self.module_1, chapter=self.chapter_2)

        response = self.client.get(reverse("chapter-detail", args=[self.chapter_3.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"error": "Not allowed to access this chapter when the previous ones are not done"},
        )

    def test_course_progression_create_then_update_for_authenticated_user(self):
        create_response = self.client.post(
            reverse("courseprogression-list"),
            {
                "user": self.other_user.id,
                "course": self.course.id,
                "current_module": self.module_1.id,
                "current_chapter": self.chapter_1.id,
            },
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        progression = CourseProgression.objects.get()
        self.assertEqual(progression.user, self.user)

        update_response = self.client.post(
            reverse("courseprogression-list"),
            {
                "current_module": self.module_2.id,
                "current_chapter": self.module_2_chapter.id,
            },
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseProgression.objects.count(), 1)
        progression.refresh_from_db()
        self.assertEqual(progression.user, self.user)
        self.assertEqual(progression.current_module, self.module_2)
        self.assertEqual(progression.current_chapter, self.module_2_chapter)

    def test_completed_signable_create_uses_authenticated_user(self):
        response = self.client.post(
            reverse("completedsignable-list"),
            {
                "user": self.other_user.id,
                "chapter": self.chapter_2.id,
                "word": "mother",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        completed_signable = CompletedSignable.objects.get()
        self.assertEqual(completed_signable.user, self.user)
        self.assertEqual(completed_signable.word, "mother")

    def test_completed_signable_list_requires_chapter_id(self):
        response = self.client.get(reverse("completedsignable-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"error": "Requires field 'chapter_id'!"})

    def test_completed_signable_list_rejects_non_signable_chapter(self):
        response = self.client.get(
            reverse("completedsignable-list"),
            {"chapter_id": self.chapter_1.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"error": "Chapter is not of signable type! Malformed request!"},
        )

    def test_completed_signable_list_reads_csv_and_marks_user_completed_words(self):
        with TemporaryDirectory() as temp_base_dir:
            content_dir = os.path.join(temp_base_dir, "content")
            os.makedirs(content_dir)
            with open(os.path.join(content_dir, "family.csv"), "w", newline="") as csv_file:
                csv_file.write("mother,mama\nfather,baba\n")

            CompletedSignable.objects.create(
                user=self.user,
                chapter=self.chapter_2,
                word="mother",
            )
            CompletedSignable.objects.create(
                user=self.other_user,
                chapter=self.chapter_2,
                word="father",
            )

            expected_content_path = os.path.join(temp_base_dir, "content", "family.csv")
            with override_settings(BASE_DIR=temp_base_dir):
                response = self.client.get(
                    reverse("completedsignable-list"),
                    {"chapter_id": self.chapter_2.id},
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["chapter_id"], str(self.chapter_2.id))
        self.assertEqual(
            response.json()["chapter_content_filepath"],
            expected_content_path,
        )
        self.assertEqual(
            response.json()["words"],
            [
                {"english": "mother", "swahili": "mama", "status": "complete"},
                {"english": "father", "swahili": "baba", "status": "incomplete"},
            ],
        )

    def test_completed_course_create_uses_authenticated_user(self):
        response = self.client.post(
            reverse("completedcourse-list"),
            {
                "user": self.other_user.id,
                "course": self.course.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        completed_course = CompletedCourse.objects.get()
        self.assertEqual(completed_course.user, self.user)


    def test_completed_course_list_only_returns_authenticated_users_courses(self):
        CompletedCourse.objects.create(user=self.user, course=self.course)
        CompletedCourse.objects.create(user=self.other_user, course=self.other_course)

        response = self.client.get(reverse("completedcourse-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.user.id)
        self.assertEqual(response.data[0]["course"]["id"], self.course.id)
