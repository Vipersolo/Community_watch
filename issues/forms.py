from django import forms
from .models import Issue, IssueCategory, Comment

class IssueForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=IssueCategory.objects.all(),
        empty_label="Select a category",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    latitude = forms.DecimalField(
        # This autocomplete='off' tells the browser not to autofill.
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False 
    )
    longitude = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': True, 'autocomplete': 'off'}),
        required=False
    )

    class Meta:
        model = Issue
        fields = ['title', 'description', 'category', 'video_url', 'latitude', 'longitude']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Large pothole on Main Street'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Provide details about the issue, location landmarks, etc.'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/video_link (Optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].required = False

    def clean(self):
        # This server-side check is our final safety net.
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if latitude is None or longitude is None:
            raise forms.ValidationError(
                "Location is required. Please select a point on the map.",
                code='location_missing'
            )
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




class ManagerIssueUpdateForm(forms.ModelForm):
    # Define which statuses a manager can set. This can be a subset of all Issue.STATUS_CHOICES
    MANAGER_STATUS_CHOICES = [
        ('', '--------- Select New Status ---------'), # Optional empty label
        ('Manager Acknowledged', 'Acknowledge Receipt'),
        ('Manager Investigating', 'Start Investigation'),
        ('Work In Progress', 'Mark as Work In Progress'),
        ('Awaiting Resources', 'Mark as Awaiting Resources'),
        ('Requires Assistance', 'Flag for Moderator Assistance'), # Informal escalation
        ('Resolved', 'Mark as Resolved'),
        # Add other statuses a manager can directly set
    ]
    status = forms.ChoiceField(choices=MANAGER_STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select mb-2'}))

    class Meta:
        model = Issue
        fields = ['status', 'resolution_notes', 'resolution_image']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control mb-2', 'rows': 4, 'placeholder': 'Enter details about actions taken or resolution...'}),
            'resolution_image': forms.ClearableFileInput(attrs={'class': 'form-control mb-2'}),
        }
        labels = {
            'status': 'Update Issue Status:',
            'resolution_notes': 'Resolution Notes / Progress Update:',
            'resolution_image': 'Upload Resolution Image (Optional):',
        }



#report

class ReportGenerationForm(forms.Form):
    # We get the choices from the Issue model and add an 'All' option
    STATUS_CHOICES = [('', 'All Statuses')] + Issue.STATUS_CHOICES

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date cannot be before the start date.")

        return cleaned_data