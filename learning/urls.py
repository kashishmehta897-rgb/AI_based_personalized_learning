from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('subjects/', views.subjects, name='subjects'),
    path(
        'subjects/<int:subject_id>/',
        views.topics,
        name='topics'
    ),
    path(
    'content/<int:content_id>/transcribe/',
    views.whisper_test,
    name='whisper_test'
),
 # AI Quiz
    path(
        'content/<int:content_id>/quiz/',
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
]