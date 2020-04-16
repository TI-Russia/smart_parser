from django import forms

SEARCH_TYPE_CHOICES = [
    ('sections_search', 'декларации'),
    ('people_search', 'люди'),
]


class SearchForm(forms.Form):
    q = forms.CharField(label='')
    search_object_type = forms.CharField(
                label='',
                widget=forms.RadioSelect(choices=SEARCH_TYPE_CHOICES),
                initial=SEARCH_TYPE_CHOICES[0][0])

    success_url = 'search/search_form.html'

    def send_search_query(self):
        # send email using the self.cleaned_data dictionary
        pass
