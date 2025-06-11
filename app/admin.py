from django.contrib import admin
from .models import *

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
    list_display = ('name_of_organization', 'username', 'user', 'contact_number', 'website_url',)
    search_fields = ('name_of_organization', 'username', 'user')
    ordering = ('name_of_organization',)

@admin.register(JobPostings)
class JobPostingsAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'username', 'approval_status', 'created_at')
    search_fields = ('job_title', 'username__username')
    list_filter = ('status', 'job_department')
    ordering = ('-created_at',)

@admin.register(InterviewerDetails)
class InterviewerDetailsAdmin(admin.ModelAdmin):
    list_display = ('name',  'job_id', 'type_of_interview')
    search_fields = ('name__username',  'job_id__job_title')
    list_filter = ('type_of_interview',)
    ordering = ('name__username',)

@admin.register(CandidateResume)
class CandidateResumeAdmin(admin.ModelAdmin):
    list_display = ( 'get_username','candidate_email', 'current_organisation',)
    search_fields = ( 'candidate_email', 'job_id__job_title')
    # list_filter = ('job_id',)
    # ordering = ('candidate_name__name__username',)

    def get_username(self,obj):
        return obj.candidate_name
    get_username.short_description = "Username"

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('resume', 'job_id', 'status', 'application_date')
    search_fields = ('resume__candidate_name', 'job_id__job_title')
    list_filter = ('status',)
    ordering = ('-application_date',)

@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = ( 'interviewer', 'scheduled_date', 'status')
    search_fields = ( 'interviewer__name', 'job_id__job_title')
    list_filter = ('status',)
    ordering = ('scheduled_date',)

@admin.register(CandidateEvaluation)
class CandidateEvaluationAdmin(admin.ModelAdmin):
    list_display = ('interview_schedule', 'score', 'remarks')
    search_fields = ('interview_schedule__candidate_resume__candidate_name',)
    list_filter = ('score',)
    ordering = ('-interview_schedule__scheduled_date',)

@admin.register(ClientTermsAcceptance)
class ClientTermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('client', 'accepted_date', 'valid_until')
    search_fields = ('client__name_of_organization',)
    ordering = ('-accepted_date',)

@admin.register(JobPostingsEditedVersion)
class JobPostingEditedVersionAdmin(admin.ModelAdmin):
    list_display= ('id','version_number','user','status')


@admin.register(InterviewerDetailsEditedVersion)
class InterviewerDetailsEditedVersionAdmin(admin.ModelAdmin):
    list_display = ('job_id','round_num','name')

admin.site.register(CandidateProfile)
admin.site.register(CandidateCertificates)
admin.site.register(CandidateEducation)
admin.site.register(CandidateExperiences)
admin.site.register(RecruiterProfile)

@admin.register(SelectedCandidates)
class SelectedCandidatesAdmin(admin.ModelAdmin):
    list_display = ('application','joining_date','ctc','joining_status','candidate')
    search_fields = ('candidate__name',)
    ordering = ('-joining_date',)

@admin.register(JobPostTerms)
class JobPostTermsAdmin(admin.ModelAdmin):
    list_display = ('job_id',)
    search_fields = ('job_id__job_title',)
    ordering = ('-created_at',)
    
@admin.register(InvoiceGenerated)
class InvoiceGeneratedAdmin(admin.ModelAdmin):
    list_display = ('application_id','organization_id','organization_email','client_id','client_email','terms_id','status','created_at','payment_method','payment_transaction_id','payment_verification')
    


@admin.register(SkillMetricsModel)
class SkillMetricsModelAdmin(admin.ModelAdmin):
    list_display = ('job_id','skill_name','is_primary','metric_type')
    search_fields = ('job_id__job_title','is_primary')
    ordering = ('-job_id__created_at',)

@admin.register(SkillMetricsModelEdited)
class SkillMetricsModelEditedAdmin(admin.ModelAdmin):
    list_display = ('job_id','skill_name','is_primary','metric_type')
    ordering = ('-job_id__created_at',)

@admin.register(CandidateSkillSet)
class CandidateSkillSetAdmin(admin.ModelAdmin):
    list_display = ('candidate',)


@admin.register(Tickets)
class TicketsAdmin(admin.ModelAdmin):
    list_display = ('raised_by', 'assigned_to', 'category')

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('user','is_approved','created_at',)
    ordering = ('-created_at',)

@admin.register(JobPostEditFields)
class JobPostEditFieldsAdmin(admin.ModelAdmin):
    list_display = ('edit_id','field_name','field_value','status')

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ('sender','receiver','seen')

@admin.register(NegotiationRequests)
class NegotiationRequestsAdmin(admin.ModelAdmin):
    list_display = ('client','organization','status')

admin.site.register(LinkedinIntegrations)
admin.site.register(HiresyncLinkedinCred)