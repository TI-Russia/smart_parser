from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Office, Section, Source_Document

admin.site.register(Office)
admin.site.register(Section)
admin.site.register(Source_Document)