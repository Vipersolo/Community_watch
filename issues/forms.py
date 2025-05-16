from django import forms
from .models import Issue, IssueCategory, Comment

class IssueForm(forms.ModelForm):
    # Explicitly define category to use a ModelChoiceField for better control if needed,
    # or rely on ModelForm's default. Using ModelChoiceField for clarity here.
    category = forms.ModelChoiceField(
        queryset=IssueCategory.objects.all(),
        empty_label="Select a category",
        widget=forms.Select(attrs={'class': 'form-select'}) # Add bootstrap class
    )
    # Add hidden fields for latitude and longitude; they will be populated by JavaScript.
    latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'image', 'video_url', 'latitude', 'longitude']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Large pothole on Main Street'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Provide details about the issue, location landmarks, etc.'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/video_link (Optional)'}),
        }
        help_texts = {
            'image': 'Upload a clear picture of the issue if possible.',
            'video_url': 'If you have a video of the issue (e.g., on YouTube, Vimeo), paste the link here.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can further customize fields here if needed
        # For example, make certain fields not required if they are optional in the model but ModelForm makes them required by default
        self.fields['image'].required = False
        self.fields['video_url'].required = False

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        # Basic validation for geolocation
        if latitude is None or longitude is None:
            # If you want to make geolocation strictly required, raise a validation error.
            # For now, we'll assume it might be optional or handled if JS fails.
            # If making it required:
            # raise forms.ValidationError("Geolocation is required. Please enable location services or select on map.")
            pass # Or log a warning, or decide if issue can be submitted without precise coords

        return cleaned_data
    



class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment_text'] # Only the user needs to fill this
        widgets = {
            'comment_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your comment here...'
            }),
        }
        labels = {
            'comment_text': '', # Hides the default label if placeholder is enough
        }