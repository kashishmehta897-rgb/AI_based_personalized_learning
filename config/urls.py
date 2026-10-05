"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from learning import views
from learning.views import (
    register,
    user_login,
    user_logout,
    dashboard,
    subjects,
    topics
)


urlpatterns = [
    path('admin/', admin.site.urls),

    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('subjects/', views.subjects, name='subjects'),
    path( 'subjects/<int:subject_id>/topics/',topics,name='topics'),
    path(
    'topics/<int:topic_id>/content/',
    views.learning_content,
    name='learning_content'
),
path(
    'content/<int:content_id>/ai-notes/',
    views.generate_ai_notes,
    name='generate_ai_notes'
),
path(
    'ai-test/',
    views.ai_test,
    name='ai_test'
),

path(
    'whisper-test/<int:content_id>/',
    views.whisper_test,
    name='whisper_test'
),
path(
    'content/<int:content_id>/generate-quiz/',
    views.generate_ai_quiz,
    name='generate_ai_quiz'
),
path(
    "quiz/<int:quiz_id>/submit/",
    views.submit_quiz,
    name="submit_quiz"
),
path(
    "quiz/<int:quiz_id>/retake/",
    views.retake_quiz,
    name="retake_quiz"
),
path(
    'learning-content/',
    views.learning_content_list,
    name='learning_content_list'
),
path(
    'learning-content/upload/',
    views.upload_learning_content,
    name='upload_learning_content'
),
path(
    'quizzes/',
    views.quiz_list,
    name='quiz_list'
),
path(
    "progress/",
    views.student_progress,
    name="student_progress"
),
path(
    "progress/clear/",
    views.clear_quiz_history,
    name="clear_progress_history"
),
path(
    'topics/<int:topic_id>/quizzes/',
    views.topic_quizzes,
    name='topic_quizzes'
),
path(
    "learning-content/<int:content_id>/delete/",
    views.delete_learning_content,
    name="delete_learning_content"
),

path(
    "topics/<int:topic_id>/delete/",
    views.delete_topic,
    name="delete_topic"
),
path(
    'content/<int:content_id>/regenerate-notes/',
    views.regenerate_ai_notes,
    name='regenerate_ai_notes'
),
path(
    'recommendations/',
    views.ai_recommendations,
    name='ai_recommendations'
),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)