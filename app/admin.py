from django.contrib import admin
from .models import (
    CustomUser,
    Organization,
    OrganizationTerms,
    UserProfile,
    ClientDetails,
    JobPostings,
    InterviewerDetails,
    CandidateResume,
    JobApplication,
    InterviewSchedule,
    CandidateEvaluation,
    ClientTermsAcceptance,
    JobPostingsEditedVersion,
    InterviewerDetailsEditedVersion,
    PrimarySkillSet,
    SecondarySkillSet,
)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('role', 'is_active', 'is_staff')
    ordering = ('username',)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager')
    search_fields = ('name',)
    list_filter = ('manager',)
    ordering = ('name',)

@admin.register(OrganizationTerms)
class OrganizationTermsAdmin(admin.ModelAdmin):
    list_display = ('organization', 'service_fee', 'replacement_clause', 'invoice_after', 'payment_within')
    search_fields = ('organization__name',)
    ordering = ('organization',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'gender',)
    search_fields = ('user__username', 'first_name', 'last_name',)
    list_filter = ('gender',)
    ordering = ('user',)

@admin.register(ClientDetails)
class ClientDetailsAdmin(admin.ModelAdmin):
    list_display = ('name_of_organization', 'username', 'user', 'contact_number', 'website_url', 'gst_number')
    search_fields = ('name_of_organization', 'username', 'user')
    ordering = ('name_of_organization',)

@admin.register(JobPostings)
class JobPostingsAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'username', 'status', 'created_at')
    search_fields = ('job_title', 'username__username')
    list_filter = ('status', 'job_department')
    ordering = ('-created_at',)

@admin.register(InterviewerDetails)
class InterviewerDetailsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'job_id', 'type_of_interview')
    search_fields = ('name', 'email', 'job_id__job_title')
    list_filter = ('type_of_interview',)
    ordering = ('name',)

@admin.register(CandidateResume)
class CandidateResumeAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'candidate_email', 'current_organisation',)
    search_fields = ('candidate_name', 'candidate_email', 'job_id__job_title')
    # list_filter = ('job_id',)
    ordering = ('candidate_name',)

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('resume', 'job_id', 'status', 'application_date')
    search_fields = ('resume__candidate_name', 'job_id__job_title')
    list_filter = ('status',)
    ordering = ('-application_date',)

@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = ( 'interviewer', 'schedule_date', 'status')
    search_fields = ( 'interviewer__name', 'job_id__job_title')
    list_filter = ('status',)
    ordering = ('schedule_date',)

@admin.register(CandidateEvaluation)
class CandidateEvaluationAdmin(admin.ModelAdmin):
    list_display = ('interview_schedule', 'score', 'remarks')
    search_fields = ('interview_schedule__candidate_resume__candidate_name',)
    list_filter = ('score',)
    ordering = ('-interview_schedule__schedule_date',)

@admin.register(ClientTermsAcceptance)
class ClientTermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('client', 'accepted_date', 'valid_until')
    search_fields = ('client__name_of_organization',)
    ordering = ('-accepted_date',)

@admin.register(JobPostingsEditedVersion)
class JobPostingEditedVersionAdmin(admin.ModelAdmin):
    list_display= ('id','edited_by','job_title')


@admin.register(InterviewerDetailsEditedVersion)
class InterviewerDetailsEditedVersionAdmin(admin.ModelAdmin):
    list_display = ('job_id','round_num','name')

admin.site.register(PrimarySkillSet)
admin.site.register(SecondarySkillSet)