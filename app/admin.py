from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, JobPostings, TermsAndConditions, Resume, CandidateResume, JobPostingEdited,InterviewerDetails,ResumeBank, InterviewerDetailsEdited, ClientDetails


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'role')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)

# Register the CustomUser model with the admin
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(JobPostings)
admin.site.register(TermsAndConditions)
admin.site.register(Resume)
admin.site.register(CandidateResume)
admin.site.register(JobPostingEdited)
admin.site.register(InterviewerDetails) 
admin.site.register(ResumeBank)
admin.site.register(InterviewerDetailsEdited)
admin.site.register(ClientDetails)
