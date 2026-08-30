from urllib import request

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone

import json
import re
import os
import tempfile
import subprocess

from urllib.request import Request, urlopen

import fitz


from .models import (
    StudentProfile,
    Subject,
    Topic,
    LearningContent,
    Quiz,
    Question
)


# =================================================
# WHISPER CONFIGURATION
# =================================================

os.environ["HF_HOME"] = r"D:\Whisper\Models"



# =================================================
# OLLAMA / GEMMA
# =================================================

def ask_ollama(prompt, json_mode=False, timeout=300):

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

        with urlopen(request, timeout=timeout) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        return result.get("response", "")

    except Exception as e:

        return f"Ollama error: {e}"


# =================================================
# REGISTER
# =================================================

def register(request):

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        education_level = request.POST.get("education_level")
        learning_goal = request.POST.get("learning_goal")

        preferred_learning_style = request.POST.get(
            "preferred_learning_style"
        )

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect("register")

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists."
            )

            return redirect("register")

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
            "Registration successful. You can now login."
        )

        return redirect("login")

    return render(
        request,
        "learning/register.html"
    )


# =================================================
# LOGIN
# =================================================

def user_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password."
        )

        return redirect("login")

    return render(
        request,
        "learning/login.html"
    )


# =================================================
# LOGOUT
# =================================================

def user_logout(request):

    logout(request)

    return redirect("login")


# =================================================
# DASHBOARD
# =================================================

@login_required
def dashboard(request):

    student = request.user.studentprofile

    return render(
        request,
        "learning/dashboard.html",
        {
            "student": student
        }
    )


# =================================================
# SUBJECTS
# =================================================

@login_required
def subjects(request):

    subjects = Subject.objects.all()

    return render(
        request,
        "learning/subjects.html",
        {
            "subjects": subjects
        }
    )


# =================================================
# TOPICS
# =================================================

@login_required
def topics(request, subject_id):

    subject = Subject.objects.get(
        id=subject_id
    )

    topics = Topic.objects.filter(
        subject=subject
    )

    return render(
        request,
        "learning/topics.html",
        {
            "subject": subject,
            "topics": topics
        }
    )


# =================================================
# LEARNING CONTENT
# =================================================

@login_required
def learning_content(request, topic_id):

    topic = Topic.objects.get(
        id=topic_id
    )

    contents = LearningContent.objects.filter(
        topic=topic
    )

    return render(
        request,
        "learning/learning_content.html",
        {
            "topic": topic,
            "contents": contents
        }
    )


# =================================================
# AI TEST
# =================================================

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

    ai_response = ask_ollama(
        prompt,
        json_mode=True,
        timeout=600
    )

    return render(
        request,
        "learning/ai_test.html",
        {
            "ai_response": ai_response
        }
    )


# =================================================
# EXTRACT TIMESTAMPED TRANSCRIPT SEGMENTS
# =================================================

def extract_transcript_segments(transcript):

    segments = []

    if not transcript:
        return segments

    pattern = (
        r"^\[(\d+(?:\.\d+)?)\s*-\s*"
        r"(\d+(?:\.\d+)?)\]\s*(.*)$"
    )

    for line in transcript.splitlines():

        match = re.match(
            pattern,
            line.strip()
        )

        if match:

            segments.append(
                {
                    "start": float(match.group(1)),
                    "end": float(match.group(2)),
                    "text": match.group(3).strip()
                }
            )

    return segments


# =================================================
# FIND VIDEO TIMESTAMP FOR QUIZ QUESTION
# =================================================

def find_video_timestamp(
    transcript,
    question_text,
    options=None
):

    """
    Find the most relevant timestamped transcript
    segment for a quiz question.

    Returns:

        (start_time, end_time)

    or:

        (None, None)
    """

    if not transcript or not question_text:

        return None, None

    # -------------------------------------------------
    # Extract transcript segments
    # -------------------------------------------------

    segments = extract_transcript_segments(
        transcript
    )

    if not segments:

        return None, None

    # -------------------------------------------------
    # Build search text
    # -------------------------------------------------

    search_text = question_text

    if options:

        search_text += " " + " ".join(options)

    search_text = search_text.lower()

    # -------------------------------------------------
    # Extract useful words
    # -------------------------------------------------

    words = re.findall(
        r"\b[a-zA-Z]{3,}\b",
        search_text
    )

    stop_words = {
        "what",
        "which",
        "where",
        "when",
        "why",
        "how",
        "does",
        "this",
        "that",
        "these",
        "those",
        "from",
        "with",
        "about",
        "into",
        "than",
        "the",
        "and",
        "are",
        "was",
        "were",
        "for",
        "you",
        "your",
        "can",
        "could",
        "would",
        "should",
        "has",
        "have",
        "had",
        "following",
        "correct",
        "option",
        "according",
        "mentioned",
        "primary",
        "reason",
        "study",
        "notes"
    }

    keywords = {
        word
        for word in words
        if word not in stop_words
    }

    if not keywords:

        return None, None

    # -------------------------------------------------
    # Find best matching transcript segment
    # -------------------------------------------------

    best_segment = None
    best_score = 0

    for segment in segments:

        transcript_text = segment["text"].lower()

        transcript_words = set(
            re.findall(
                r"\b[a-zA-Z]{3,}\b",
                transcript_text
            )
        )

        score = len(
            keywords.intersection(
                transcript_words
            )
        )

        if score > best_score:

            best_score = score
            best_segment = segment

    # -------------------------------------------------
    # No reliable match
    # -------------------------------------------------

    if best_segment is None or best_score == 0:

        return None, None

    return (
        best_segment["start"],
        best_segment["end"]
    )


# =================================================
# AI STUDY NOTES
# =================================================

@login_required
def generate_ai_notes(request, content_id):

    content = LearningContent.objects.get(
        id=content_id
    )

    # -------------------------------------------------
    # STEP 1: If AI notes already exist, load them
    # -------------------------------------------------

    if content.ai_notes:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": content.ai_notes,
                "from_database": True
            }
        )

    # -------------------------------------------------
    # STEP 2: Get source text
    #
    # VIDEO → Faster-Whisper → transcript
    # PDF   → PyMuPDF → extracted text
    # ARTICLE → text file
    # -------------------------------------------------

    source_text = ""

    # =================================================
    # VIDEO
    # =================================================

    if content.content_type == "video":

        if not content.transcript:

            try:

                video_path = content.content_file.path

                transcript = transcribe_video(
                    video_path
                )

                if not transcript.strip():

                    return render(
                        request,
                        "learning/ai_notes.html",
                        {
                            "content": content,
                            "ai_notes": (
                                "Transcription completed, "
                                "but no speech was detected "
                                "in the video."
                            ),
                            "from_database": False
                        }
                    )

                # Save transcript

                content.transcript = transcript

                content.save(
                    update_fields=[
                        "transcript"
                    ]
                )

            except Exception as e:

                return render(
                    request,
                    "learning/ai_notes.html",
                    {
                        "content": content,
                        "ai_notes": (
                            "Video transcription failed.\n\n"
                            f"Error: {e}"
                        ),
                        "from_database": False
                    }
                )

        # Use saved transcript

        source_text = content.transcript

    # =================================================
    # PDF
    # =================================================

    elif content.content_type == "pdf":

        try:

            pdf_path = content.content_file.path

            pdf_document = fitz.open(
                pdf_path
            )

            extracted_text = ""

            for page in pdf_document:

                extracted_text += page.get_text()

            pdf_document.close()

            source_text = extracted_text.strip()

            if not source_text:

                return render(
                    request,
                    "learning/ai_notes.html",
                    {
                        "content": content,
                        "ai_notes": (
                            "No readable text was found "
                            "in this PDF. This may be a "
                            "scanned/image-based PDF."
                        ),
                        "from_database": False
                    }
                )

        except Exception as e:

            return render(
                request,
                "learning/ai_notes.html",
                {
                    "content": content,
                    "ai_notes": (
                        "PDF text extraction failed.\n\n"
                        f"Error: {e}"
                    ),
                    "from_database": False
                }
            )

    # =================================================
    # ARTICLE
    # =================================================

    elif content.content_type == "article":

        try:

            article_path = content.content_file.path

            with open(
                article_path,
                "r",
                encoding="utf-8"
            ) as file:

                source_text = file.read().strip()

            if not source_text:

                return render(
                    request,
                    "learning/ai_notes.html",
                    {
                        "content": content,
                        "ai_notes": (
                            "The article text file "
                            "is empty."
                        ),
                        "from_database": False
                    }
                )

        except UnicodeDecodeError:

            return render(
                request,
                "learning/ai_notes.html",
                {
                    "content": content,
                    "ai_notes": (
                        "The article file could not "
                        "be read as UTF-8 text."
                    ),
                    "from_database": False
                }
            )

        except Exception as e:

            return render(
                request,
                "learning/ai_notes.html",
                {
                    "content": content,
                    "ai_notes": (
                        "Article text extraction failed."
                        "\n\n"
                        f"Error: {e}"
                    ),
                    "from_database": False
                }
            )

    # =================================================
    # OTHER CONTENT TYPES
    # =================================================

    else:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "AI study notes are currently "
                    "supported for video, PDF, and "
                    "Article content."
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 3: Make sure source text exists
    # -------------------------------------------------

    if not source_text.strip():

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "No readable content was found."
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 4: Send source content to Gemma 3 4B
    # -------------------------------------------------

    prompt = f"""
You are an AI study-note generator.

Your task is to create study notes based ONLY on the source
content provided below.

STRICT RULES:

1. Use ONLY information contained in the source content.
2. Do NOT use your own prior knowledge.
3. Do NOT add information that is not present in the source.
4. Do NOT invent examples.
5. Do NOT invent facts.
6. Do NOT add concepts that are not discussed in the source.
7. Do NOT add facts from outside the source.
8. If something is unclear or missing from the source, do not
   guess or complete it using your own knowledge.
9. Translate the information into clear English if the source
   is in another language.
10. Keep the meaning of the original source.
11. The notes must represent only the information actually
    present in the source.

Create the notes using this structure:

1. Introduction
2. Important Concepts
3. Key Points
4. Examples Mentioned in the Source
5. Summary

IMPORTANT:

The "Examples Mentioned in the Source" section must contain ONLY
examples that actually appear in the source.

SOURCE CONTENT:

--------------------
{source_text}
--------------------

Generate the final study notes now.
"""

    # -------------------------------------------------
    # STEP 5: Generate notes
    # -------------------------------------------------

    print(
        "========== AI NOTES DEBUG =========="
    )

    print(
        "SOURCE TEXT LENGTH:",
        len(source_text)
    )

    print(
        "PROMPT LENGTH:",
        len(prompt)
    )

    print(
        "===================================="
    )

    ai_notes = ask_ollama(
        prompt
    )

    # -------------------------------------------------
    # STEP 6: Check Ollama error
    # -------------------------------------------------

    if ai_notes.startswith(
        "Ollama error:"
    ):

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": ai_notes,
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 7: Save AI notes
    # -------------------------------------------------

    content.ai_notes = ai_notes

    content.notes_generated_at = timezone.now()

    content.save(
        update_fields=[
            "ai_notes",
            "notes_generated_at"
        ]
    )

    # -------------------------------------------------
    # STEP 8: Display notes
    # -------------------------------------------------

    return render(
        request,
        "learning/ai_notes.html",
        {
            "content": content,
            "ai_notes": ai_notes,
            "from_database": False
        }
    )


# =================================================
# VIDEO TRANSCRIPTION
# =================================================

def transcribe_video(video_path):

    import subprocess
    import tempfile

    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        raise Exception(
            "Faster-Whisper could not be loaded.\n\n"
            f"Error: {e}"
        )

    whisper_model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    ...
@login_required
def whisper_test(request, content_id):

    content = LearningContent.objects.get(
        id=content_id
    )

    if content.content_type != "video":

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "This content is not a video."
                ),
                "from_database": False
            }
        )

    video_path = content.content_file.path

    # -------------------------------------------------
    # STEP 1: Transcribe
    # -------------------------------------------------

    transcript = transcribe_video(
        video_path
    )

    # -------------------------------------------------
    # STEP 2: Save transcript
    # -------------------------------------------------

    content.transcript = transcript

    content.save(
        update_fields=[
            "transcript"
        ]
    )

    # -------------------------------------------------
    # STEP 3: Display transcript
    # -------------------------------------------------

    return render(
        request,
        "learning/ai_notes.html",
        {
            "content": content,
            "ai_notes": transcript,
            "from_database": False
        }
    )


# =================================================
# AI QUIZ
# =================================================

@login_required
def generate_ai_quiz(request, content_id):

    content = LearningContent.objects.get(
        id=content_id
    )

    # -------------------------------------------------
    # STEP 1: Check AI notes
    # -------------------------------------------------

    if not content.ai_notes:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "Please generate AI study "
                    "notes first."
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 2: Check timestamped transcript
    # -------------------------------------------------

    transcript_segments = extract_transcript_segments(
        content.transcript
    )

    if not transcript_segments:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "Quiz generation failed because "
                    "no timestamped transcript is "
                    "available."
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 3: Ask Gemma to generate quiz
    #
    # IMPORTANT:
    # Only AI study notes are sent to Gemma.
    #
    # The timestamped transcript stays inside Django.
    # -------------------------------------------------

    prompt = f"""
You are an AI quiz generator for an
AI-Powered Personalized Learning System.

Create exactly 5 multiple-choice questions based ONLY
on the study notes below.

IMPORTANT RULES:

1. Use ONLY information contained in the study notes.
2. Do NOT use outside knowledge.
3. Do NOT invent facts or examples.
4. Questions must directly test concepts actually
   present in the study notes.
5. Each question must have exactly four options.
6. Only one option must be correct.
7. correct_answer must be exactly A, B, C, or D.
8. Return ONLY valid JSON.
9. Do NOT use Markdown.
10. Do NOT add explanations outside the JSON.
11. Do NOT generate timestamps.

Use exactly this JSON format:

{{
    "questions": [
        {{
            "question": "Question text",
            "option_a": "Option A",
            "option_b": "Option B",
            "option_c": "Option C",
            "option_d": "Option D",
            "correct_answer": "A"
        }}
    ]
}}

Study notes:

--------------------
{content.ai_notes}
--------------------

Generate exactly 5 questions.

Return ONLY the JSON object.
"""

    print(
        "========== AI QUIZ DEBUG =========="
    )

    print(
        "AI NOTES LENGTH:",
        len(content.ai_notes)
    )

    print(
        "PROMPT LENGTH:",
        len(prompt)
    )

    print(
        "==================================="
    )

       # -------------------------------------------------
    # STEP 4: Gemma 3 4B
    # -------------------------------------------------

    ai_response = ask_ollama(
        prompt,
        json_mode=True,
        timeout=600
    )

    # -------------------------------------------------
    # STEP 5: Ollama error
    # -------------------------------------------------

    if ai_response.startswith(
        "Ollama error:"
    ):

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": ai_response,
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 6: Clean and parse JSON
    # -------------------------------------------------

    try:

        cleaned_response = ai_response.strip()

        if cleaned_response.startswith("```"):

            lines = cleaned_response.splitlines()

            if lines[0].startswith("```"):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            cleaned_response = "\n".join(
                lines
            ).strip()

        start = cleaned_response.find("{")
        end = cleaned_response.rfind("}")

        if start == -1 or end == -1:

            raise json.JSONDecodeError(
                "No JSON object found",
                cleaned_response,
                0
            )

        cleaned_response = (
            cleaned_response[
                start:end + 1
            ]
        )

        quiz_data = json.loads(
            cleaned_response
        )

        print(
            "========== GEMMA QUIZ RESPONSE =========="
        )

        print(
            json.dumps(
                quiz_data,
                indent=2
            )
        )

        print(
            "========================================="
        )

    except json.JSONDecodeError:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "Quiz generation failed because "
                    "Gemma returned invalid JSON.\n\n"
                    + ai_response
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 7: Validate questions
    # -------------------------------------------------

    questions_data = quiz_data.get(
        "questions",
        []
    )

    if len(questions_data) != 5:

        return render(
            request,
            "learning/ai_notes.html",
            {
                "content": content,
                "ai_notes": (
                    "Quiz generation failed because "
                    "Gemma did not generate exactly "
                    "5 questions.\n\n"
                    f"Gemma generated: "
                    f"{len(questions_data)} questions."
                ),
                "from_database": False
            }
        )

    # -------------------------------------------------
    # STEP 7A: Check required fields
    # -------------------------------------------------

    required_fields = [
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_answer"
    ]

    # -------------------------------------------------
    # STEP 8: Create ONE Quiz
    #
    # IMPORTANT:
    # Quiz must be created BEFORE the question loop.
    # Otherwise every question gets its own quiz.
    # -------------------------------------------------

    quiz = Quiz.objects.create(
        topic=content.topic,
        title=f"AI Quiz - {content.title}",
        description=(
            "AI-generated quiz based on "
            "the study material."
        )
    )

    # -------------------------------------------------
    # STEP 9: Validate + Save ALL 5 Questions
    # -------------------------------------------------

    for index, item in enumerate(questions_data):

        print(
            f"CHECKING QUESTION {index + 1}:",
            item
        )

        # ---------------------------------------------
        # Validate required fields
        # ---------------------------------------------

        missing_fields = [
            field
            for field in required_fields
            if field not in item
            or not str(item[field]).strip()
        ]

        # ---------------------------------------------
        # Repair missing correct_answer
        # ---------------------------------------------

        if missing_fields:

            if missing_fields == ["correct_answer"]:

                repair_prompt = f"""
You are correcting an incomplete multiple-choice
quiz question.

Use ONLY the information already present in this
question and its four options.

Determine which option is correct.

Return ONLY valid JSON.

Use exactly this format:

{{
    "correct_answer": "A"
}}

The answer MUST be exactly one of:

A
B
C
D

Question:
{item["question"]}

Option A:
{item["option_a"]}

Option B:
{item["option_b"]}

Option C:
{item["option_c"]}

Option D:
{item["option_d"]}

Return ONLY the JSON object.
"""

                print(
                    "Missing correct_answer."
                )

                print(
                    "Asking Gemma to repair it..."
                )

                repair_response = ask_ollama(
                    repair_prompt,
                    json_mode=True,
                    timeout=120
                )

                print(
                    "========== GEMMA REPAIR RESPONSE =========="
                )

                print(
                    repair_response
                )

                print(
                    "============================================"
                )

                try:

                    repair_cleaned = (
                        repair_response.strip()
                    )

                    repair_start = (
                        repair_cleaned.find("{")
                    )

                    repair_end = (
                        repair_cleaned.rfind("}")
                    )

                    if (
                        repair_start == -1
                        or repair_end == -1
                    ):

                        raise json.JSONDecodeError(
                            "No JSON object found",
                            repair_cleaned,
                            0
                        )

                    repair_cleaned = (
                        repair_cleaned[
                            repair_start:
                            repair_end + 1
                        ]
                    )

                    repair_data = json.loads(
                        repair_cleaned
                    )

                    correct_answer = str(
                        repair_data.get(
                            "correct_answer",
                            ""
                        )
                    ).strip().upper()

                    if correct_answer not in [
                        "A",
                        "B",
                        "C",
                        "D"
                    ]:

                        raise ValueError(
                            "Invalid correct_answer"
                        )

                    item["correct_answer"] = (
                        correct_answer
                    )

                    print(
                        "REPAIRED CORRECT ANSWER:",
                        correct_answer
                    )

                except (
                    json.JSONDecodeError,
                    ValueError,
                    TypeError
                ):

                    # Delete the empty quiz because
                    # question generation failed.
                    quiz.delete()

                    return render(
                        request,
                        "learning/ai_notes.html",
                        {
                            "content": content,
                            "ai_notes": (
                                "Quiz generation failed "
                                "because Gemma did not "
                                "provide a valid "
                                "correct_answer."
                                "\n\n"
                                f"Question: "
                                f"{json.dumps(item, indent=2)}"
                                "\n\n"
                                f"Gemma repair response:"
                                f"\n{repair_response}"
                            ),
                            "from_database": False
                        }
                    )

            else:

                # Delete the quiz if another required
                # field is missing.
                quiz.delete()

                return render(
                    request,
                    "learning/ai_notes.html",
                    {
                        "content": content,
                        "ai_notes": (
                            "Quiz generation failed "
                            "because Gemma did not "
                            "return all required "
                            "fields.\n\n"
                            f"Question {index + 1}\n\n"
                            f"Missing fields: "
                            f"{missing_fields}\n\n"
                            f"Gemma returned:\n"
                            f"{json.dumps(item, indent=2)}"
                        ),
                        "from_database": False
                    }
                )

        # ---------------------------------------------
        # Normalize correct_answer
        # ---------------------------------------------

        item["correct_answer"] = str(
            item["correct_answer"]
        ).strip().upper()

        if item["correct_answer"] not in [
            "A",
            "B",
            "C",
            "D"
        ]:

            quiz.delete()

            return render(
                request,
                "learning/ai_notes.html",
                {
                    "content": content,
                    "ai_notes": (
                        "Quiz generation failed "
                        "because Gemma returned an "
                        "invalid correct_answer.\n\n"
                        "Expected A, B, C, or D.\n\n"
                        f"Gemma returned: "
                        f"{item['correct_answer']}"
                    ),
                    "from_database": False
                }
            )

        # ---------------------------------------------
        # Find hidden video timestamp
        # ---------------------------------------------

        start_time, end_time = find_video_timestamp(
            content.transcript,
            item["question"],
            [
                item["option_a"],
                item["option_b"],
                item["option_c"],
                item["option_d"]
            ]
        )

        print(
            "VIDEO TIMESTAMP:",
            start_time,
            "->",
            end_time
        )

        # ---------------------------------------------
        # Save question into THE SAME QUIZ
        # ---------------------------------------------

        Question.objects.create(
            quiz=quiz,
            question_text=item["question"],
            option_a=item["option_a"],
            option_b=item["option_b"],
            option_c=item["option_c"],
            option_d=item["option_d"],
            correct_answer=item["correct_answer"],
            video_start_time=start_time,
            video_end_time=end_time
        )

    # -------------------------------------------------
    # STEP 10: Display ONE Quiz containing 5 Questions
    # -------------------------------------------------

    return render(
        request,
        "learning/quiz.html",
        {
            "content": content,
            "quiz": quiz
        }
    )




# =================================================
# SUBMIT QUIZ
# =================================================

@login_required
@login_required
def submit_quiz(request, quiz_id):

    quiz = Quiz.objects.get(
        id=quiz_id
    )

    if request.method != "POST":
        return redirect(
            "dashboard"
        )

    # -------------------------------------------------
    # Find the LearningContent that generated this quiz
    # -------------------------------------------------

    content = LearningContent.objects.filter(
        topic=quiz.topic,
        title=quiz.title.replace(
            "AI Quiz - ",
            "",
            1
        )
    ).first()

    questions = quiz.questions.all()

    score = 0
    total_questions = questions.count()

    results = []

    # -------------------------------------------------
    # Check each answer
    # -------------------------------------------------

    for question in questions:

        selected_answer = request.POST.get(
            f"question_{question.id}"
        )

        is_correct = (
            selected_answer
            == question.correct_answer
        )

        if is_correct:
            score += 1

        results.append(
            {
                "question": question,
                "selected_answer": selected_answer,
                "is_correct": is_correct
            }
        )

    # -------------------------------------------------
    # Calculate percentage
    # -------------------------------------------------

    if total_questions > 0:
        percentage = round(
            (score / total_questions) * 100
        )
    else:
        percentage = 0

    # -------------------------------------------------
    # Display quiz result
    # -------------------------------------------------

    return render(
        request,
        "learning/quiz_result.html",
        {
            "quiz": quiz,
            "content": content,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results
        }
    )