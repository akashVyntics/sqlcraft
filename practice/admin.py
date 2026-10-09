from django.contrib import admin
from .models import Attempt, Draft

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem_id', 'accepted', 'created_at']
    readonly_fields = ['user', 'problem_id', 'sql', 'accepted', 'created_at']
    def has_add_permission(self, request):
        return False

@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem_id', 'updated_at']
