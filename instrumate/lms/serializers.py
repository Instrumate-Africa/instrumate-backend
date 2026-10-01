from rest_framework import serializers
from . import models

class CourseSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Course
        fields = '__all__'
        read_only_fields = ['created_at']


class ModuleSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Module
        fields = '__all__'
        read_only_fields = ['created_at']

class ChapterSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Chapter
        fields = '__all__'
        read_only_fields = ['created_at']

class CourseProgressionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.CourseProgression
        fields = '__all__'
        read_only_fields = ['user', 'last_entry']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['course'] = CourseSerializer(instance.course).data
        rep['current_module'] = ModuleSerializer(instance.current_module).data
        rep['current_chapter'] = ChapterSerializer(instance.current_chapter).data
        return rep

class CompletedSignableSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.CompletedSignable
        fields = '__all__'
        read_only_fields = ['completed_at']

class CompletedCourseSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.CompletedCourse
        fields = '__all__'
        read_only_fields = ['user', 'completed_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['course'] = CourseSerializer(instance.course).data
        return rep
