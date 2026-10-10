from django import forms


class PreferenceForm(forms.Form):
    language = forms.ChoiceField(
        label='Question language', choices=[('en', 'English'), ('hi', 'Hinglish')]
    )
