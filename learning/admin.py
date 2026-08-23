from django.contrib import admin
from .models import (
    StudentProfile,
    Subject,
    Topic,
    LearningContent,
    Quiz,
    Question,
    QuizAttempt,
    StudentProgress,
    Recommendation,
)

admin.site.register(StudentProfile)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(LearningContent)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(QuizAttempt)
admin.site.register(StudentProgress)
admin.site.register(Recommendation)