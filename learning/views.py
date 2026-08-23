from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
from urllib.request import Request, urlopen
from faster_whisper import WhisperModel
from .models import (
    StudentProfile,
    Subject,
    Topic,
    LearningContent,
    Quiz,
    Question
)

import os

os.environ["HF_HOME"] = r"D:\Whisper\Models"

whisper_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


from .models import (
    StudentProfile,
    Subject,
    Topic,
    LearningContent
)
def ask_ollama(prompt, json_mode=False):
    url = "http://127.0.0.1:11434/api/generate"

    data = {
        "model": "gemma3:4b",
        "prompt": prompt,
        "stream": False
    }

    if json_mode:
        data["format"] = "json"

    request = Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=300) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        return result.get("response", "")

    except Exception as e:
        return f"Ollama error: {e}"

    
def register(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        education_level = request.POST.get('education_level')
        learning_goal = request.POST.get('learning_goal')
        preferred_learning_style = request.POST.get(
            'preferred_learning_style'
        )

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        StudentProfile.objects.create(
            user=user,
            education_level=education_level,
            learning_goal=learning_goal,
            preferred_learning_style=preferred_learning_style
        )

        messages.success(
            request,
            'Registration successful. You can now login.'
        )

        return redirect('login')

    return render(request, 'learning/register.html')
def user_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, 'Invalid username or password.')
        return redirect('login')

    return render(request, 'learning/login.html')
def user_logout(request):
    logout(request)
    return redirect('login')
@login_required
def dashboard(request):
    student = request.user.studentprofile

    return render(
        request,
        'learning/dashboard.html',
        {'student': student}
    )
@login_required
def subjects(request):
    subjects = Subject.objects.all()

    return render(
        request,
        'learning/subjects.html',
        {'subjects': subjects}
    )
@login_required
def topics(request, subject_id):
    subject = Subject.objects.get(id=subject_id)
    topics = Topic.objects.filter(subject=subject)

    return render(
        request,
        'learning/topics.html',
        {
            'subject': subject,
            'topics': topics
        }
    )
@login_required
def learning_content(request, topic_id):

    topic = Topic.objects.get(id=topic_id)

    contents = LearningContent.objects.filter(
        topic=topic
    )

    return render(
        request,
        'learning/learning_content.html',
        {
            'topic': topic,
            'contents': contents
        }
    )
@login_required
def ai_test(request):

    prompt = """
You are an AI tutor for an AI-Powered Personalized Learning System.

Explain the topic "Python Variables" to a beginner student.

Give:
1. A simple definition
2. Important points
3. One simple example
4. A short summary

Use simple language.
"""

    ai_response = ask_ollama(prompt)

    return render(
        request,
        'learning/ai_test.html',
        {
            'ai_response': ai_response
        }
    )
@login_required
@login_required
def generate_ai_notes(request, content_id):

    content = LearningContent.objects.get(id=content_id)

    # -------------------------------------------------
    # STEP 1: If AI notes already exist, load them
    # -------------------------------------------------

    if content.ai_notes:
        return render(
            request,
            'learning/ai_notes.html',
            {
                'content': content,
                'ai_notes': content.ai_notes,
                'from_database': True
            }
        )

    # -------------------------------------------------
    # STEP 2: If transcript does not exist,
    # automatically transcribe the video
    # -------------------------------------------------

    if not content.transcript:

        if content.content_type != "video":
            return render(
                request,
                'learning/ai_notes.html',
                {
                    'content': content,
                    'ai_notes': (
                        'This content is not a video and '
                        'does not have a transcript.'
                    ),
                    'from_database': False
                }
            )

        try:
            # Get uploaded video path
            video_path = content.content_file.path

            # Run Faster-Whisper automatically
            transcript = transcribe_video(video_path)

            # Make sure transcription produced text
            if not transcript.strip():
                return render(
                    request,
                    'learning/ai_notes.html',
                    {
                        'content': content,
                        'ai_notes': (
                            'Transcription completed, but no speech '
                            'was detected in the video.'
                        ),
                        'from_database': False
                    }
                )

            # Save transcript to PostgreSQL
            content.transcript = transcript

            content.save(
                update_fields=['transcript']
            )

        except Exception as e:

            return render(
                request,
                'learning/ai_notes.html',
                {
                    'content': content,
                    'ai_notes': (
                        'Video transcription failed.\n\n'
                        f'Error: {e}'
                    ),
                    'from_database': False
                }
            )

    # -------------------------------------------------
    # STEP 3: Transcript now exists
    # Send transcript to Gemma 3 4B
    # -------------------------------------------------

    prompt = f"""
You are an AI study-note generator.

Your task is to create study notes based ONLY on the transcript
provided below.

STRICT RULES:

1. Use ONLY information contained in the transcript.
2. Do NOT use your own prior knowledge.
3. Do NOT add information that is not present in the transcript.
4. Do NOT invent examples.
5. Do NOT invent Python code.
6. Do NOT add concepts that the speaker did not discuss.
7. Do NOT add facts from outside the transcript.
8. If something is unclear or missing from the transcript, do not
   guess or complete it using your own knowledge.
9. Translate the information into clear English if the transcript
   is in another language.
10. Keep the meaning of the original transcript.
11. The notes must represent what was actually said in the video.

Create the notes using this structure:

1. Introduction
2. Important Concepts
3. Key Points
4. Examples Mentioned in the Video
5. Summary

IMPORTANT:

The "Examples Mentioned in the Video" section must contain ONLY
examples that actually appear in the transcript.

TRANSCRIPT:

--------------------
{content.transcript}
--------------------

Generate the final study notes now.
"""

    # -------------------------------------------------
    # STEP 4: Generate notes using Gemma 3 4B
    # -------------------------------------------------

    ai_notes = ask_ollama(prompt)

    # -------------------------------------------------
    # STEP 5: Check for Ollama error
    # -------------------------------------------------

    if ai_notes.startswith("Ollama error:"):
        return render(
            request,
            'learning/ai_notes.html',
            {
                'content': content,
                'ai_notes': ai_notes,
                'from_database': False
            }
        )

    # -------------------------------------------------
    # STEP 6: Save AI notes to PostgreSQL
    # -------------------------------------------------

    content.ai_notes = ai_notes
    content.notes_generated_at = timezone.now()

    content.save(
        update_fields=[
            'ai_notes',
            'notes_generated_at'
        ]
    )

    # -------------------------------------------------
    # STEP 7: Display newly generated notes
    # -------------------------------------------------

    return render(
        request,
        'learning/ai_notes.html',
        {
            'content': content,
            'ai_notes': ai_notes,
            'from_database': False
        }
    )
def transcribe_video(video_path):

    segments, info = whisper_model.transcribe(
        video_path,
        beam_size=1,
        vad_filter=True
    )

    transcript_parts = []

    for segment in segments:
        transcript_parts.append(segment.text.strip())

    transcript = " ".join(transcript_parts)

    return transcript

@login_required
def whisper_test(request, content_id):

    content = LearningContent.objects.get(id=content_id)

    if content.content_type != "video":
        return render(
            request,
            'learning/ai_notes.html',
            {
                'content': content,
                'ai_notes': 'This content is not a video.',
                'from_database': False
            }
        )

    video_path = content.content_file.path

    # -----------------------------------------
    # STEP 1: Transcribe video
    # -----------------------------------------

    transcript = transcribe_video(video_path)

    # -----------------------------------------
    # STEP 2: Save transcript to PostgreSQL
    # -----------------------------------------

    content.transcript = transcript
    content.save(update_fields=['transcript'])

    # -----------------------------------------
    # STEP 3: Display transcript
    # -----------------------------------------

    return render(
        request,
        'learning/ai_notes.html',
        {
            'content': content,
            'ai_notes': transcript,
            'from_database': False
        }
    )

@login_required
@login_required
def generate_ai_quiz(request, content_id):

    content = LearningContent.objects.get(id=content_id)

    # -------------------------------------------------
    # STEP 1: Check whether AI study notes exist
    # -------------------------------------------------

    if not content.ai_notes:
        return render(
            request,
            'learning/ai_notes.html',
            {
                'content': content,
                'ai_notes': 'Please generate AI study notes first.',
                'from_database': False
            }
        )

    # -------------------------------------------------
    # STEP 2: Ask Gemma to generate quiz questions
    # -------------------------------------------------

    prompt = f"""
You are an AI quiz generator for an AI-Powered Personalized Learning System.

Create a multiple-choice quiz based ONLY on the study notes provided below.

Study notes:
{content.ai_notes}

Generate exactly 5 multiple-choice questions.

Each question must have:
- question
- option_a
- option_b
- option_c
- option_d
- correct_answer

The correct_answer must contain ONLY:
A
B
C
or D

Return ONLY valid JSON.

Use exactly this format:

{{
    "questions": [
        {{
            "question": "Question text",
            "option_a": "Option A",
            "option_b": "Option B",
            "option_c": "Option C",
            "option_d": "Option D",
            "correct_answer": "B"
        }}
    ]
}}

Do not add explanations.
Do not add Markdown.
"""

    ai_response = ask_ollama(prompt)

    # -------------------------------------------------
    # STEP 3: Clean Gemma response and convert to JSON
    # -------------------------------------------------

    try:

        cleaned_response = ai_response.strip()

        if cleaned_response.startswith("```"):

            lines = cleaned_response.splitlines()

            if lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned_response = "\n".join(lines).strip()

        start = cleaned_response.find("{")
        end = cleaned_response.rfind("}")

        if start == -1 or end == -1:
            raise json.JSONDecodeError(
                "No JSON object found",
                cleaned_response,
                0
            )

        cleaned_response = cleaned_response[start:end + 1]

        quiz_data = json.loads(cleaned_response)

    except json.JSONDecodeError:

        return render(
            request,
            'learning/ai_notes.html',
            {
                'content': content,
                'ai_notes': (
                    'Quiz generation failed because '
                    'Gemma returned invalid JSON.\n\n'
                    + ai_response
                ),
                'from_database': False
            }
        )

    # -------------------------------------------------
    # STEP 4: Create Quiz in PostgreSQL
    # -------------------------------------------------

    quiz = Quiz.objects.create(
        topic=content.topic,
        title=f"AI Quiz - {content.title}",
        description="AI-generated quiz based on the study material."
    )

    # -------------------------------------------------
    # STEP 5: Save Questions in PostgreSQL
    # -------------------------------------------------

    for item in quiz_data.get('questions', []):

        Question.objects.create(
            quiz=quiz,
            question_text=item['question'],
            option_a=item['option_a'],
            option_b=item['option_b'],
            option_c=item['option_c'],
            option_d=item['option_d'],
            correct_answer=item['correct_answer']
        )

    # -------------------------------------------------
    # STEP 6: Display generated quiz
    # -------------------------------------------------

    return render(
        request,
        'learning/quiz.html',
        {
            'content': content,
            'quiz': quiz
        }
    )
