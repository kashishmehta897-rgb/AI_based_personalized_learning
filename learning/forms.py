from django import forms
from .models import LearningContent


class LearningContentUploadForm(forms.ModelForm):

    class Meta:
        model = LearningContent
        fields = [
            "topic",
            "title",
            "description",
            "content_type",
            "content_file",
        ]

        widgets = {
            "topic": forms.Select(attrs={
                "class": "form-input"
            }),

            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Enter content title"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-input",
                "placeholder": "Enter a short description",
                "rows": 4
            }),

            "content_type": forms.Select(
                choices=[
                    ("video", "Video"),
                    ("pdf", "PDF"),
                ],
                attrs={
                    "class": "form-input"
                }
            ),

            "content_file": forms.ClearableFileInput(attrs={
                "class": "form-input",
                "accept": ".mp4,.avi,.mov,.mkv,.webm,.pdf"
            }),
        }