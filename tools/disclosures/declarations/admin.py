from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Office,  Section, DocumentFile

admin.site.register(Office)
admin.site.register(Section)
admin.site.register(DocumentFile)