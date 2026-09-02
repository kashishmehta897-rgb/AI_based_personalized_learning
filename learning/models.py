from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    education_level = models.CharField(max_length=100, blank=True)
    learning_goal = models.CharField(max_length=255, blank=True)
    preferred_learning_style = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Subject(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class LearningContent(models.Model):
    CONTENT_TYPES = [
        ('video', 'Video'),
        ('article', 'Article'),
        ('pdf', 'PDF'),
        ('exercise', 'Exercise'),
    ]

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='contents'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES
    )
    content_file = models.FileField(
    upload_to='content/',
    max_length=255,
    blank=True,
    null=True


)
    difficulty = models.CharField(max_length=50, default='Beginner')
    created_at = models.DateTimeField(auto_now_add=True)

    transcript = models.TextField(blank=True, null=True)
    ai_notes = models.TextField(blank=True, null=True)
    notes_generated_at = models.DateTimeField(blank=True, null=True)

    
    def __str__(self):
        return self.title


class Quiz(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1)

    # Video timestamp mapping
    video_start_time = models.FloatField(
        blank=True,
        null=True
    )
    video_end_time = models.FloatField(
        blank=True,
        null=True
    )
    # PDF page mapping
    pdf_page = models.PositiveIntegerField(
    blank=True,
    null=True
    )

    def __str__(self):
        return self.question_text[:50]

    
class QuizAttempt(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    score = models.FloatField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.quiz} - {self.score}"


class StudentProgress(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='student_progress'
    )
    completion_percentage = models.FloatField(default=0)
    average_score = models.FloatField(default=0)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.topic}"


class Recommendation(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    reason = models.TextField()
    priority = models.CharField(max_length=20, default='Medium')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.topic}"