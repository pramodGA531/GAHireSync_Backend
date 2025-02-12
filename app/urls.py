from django.urls import path
from .role_views import *
from .authentication_views import *
from .views import *

urlpatterns = [
    path('signup/client/',ClientSignupView.as_view(),name="client_signup"),
    path('signup/agency/',AgencySignupView.as_view(),name="agency_signup"),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-token/',VerifyTokenView.as_view(), name='verify-token'),
    path('get-user-details/', GetUserDetails.as_view(), name='user_details'),
    path('forgotpassword/', ForgotPasswordAPIView.as_view(),name='forgotpassword'),
    path('resetpassword/<uidb64>/<token>/',ResetPasswordAPIView.as_view(), name='resetpassword'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name="verify-email"),
    path('send-verification-email/', VerifyEmailView.as_view(), name="send-verification-email"),

    path('changepassword/', changePassword.as_view(), name='changepassword'),


    path('job-postings/', JobPostingView.as_view(), name='create-job-posting'),
    path('org-job-postings/', OrgJobPostings.as_view(), name='org-job-posting'),
    path('org-particular-job/',OrgParticularJobPost.as_view(), name='org-particular-job'),
    path('org/get-recruiters/', RecruitersList.as_view(), name='get-recruiters-to-allot'),
    path('org-edit-jobpost/', OrgJobEdits.as_view(), name='org-job-edits'),
    path('org/accept-job/', AcceptJobPostView.as_view(), name='accept-job-post'),
    path('job-postings/<int:job_id>/', JobPostingView.as_view(), name='edit-job-posting'),
    path('job-details/recruiter/<int:job_id>/', RecJobDetails.as_view(), name='rec-job-details'),
    path('accept-job-post/',AcceptJobEditRequestView.as_view(),name = 'accept-job-post'),
    path('reject-job-post/',RejectJobEditRequestView.as_view(),name='reject-job-post'),

    path('generatequestionary/<int:job_id>', GenerateQuestions.as_view(), name='generate-questionary'),
    path('analyse-resume/<int:job_id>', AnalyseResume.as_view(), name='analyse-resume'),
    path('screen-resume/<int:job_id>', ScreenResume.as_view(), name='screen-resume'),
    path('recruiter/create-candidate/',CandidateResumeView.as_view(),name='candidate-share-resume'),

    path('job-details/', JobDetailsAPIView.as_view(), name='view-job-posting'),
    path('organization-terms/', OrganizationTermsView.as_view(), name='organization-terms'),
    path('get-organization-terms/', GetOrganizationTermsView.as_view(), name='get-organization-terms'),

    path('client/job-postings/', getClientJobposts.as_view(), name='client-job-posting'),
    path('client/not-approval-jobs/', JobEditRequestsView.as_view(),name='get-edited-job-posts'),
    path('client/job-edit-details/',JobEditStatusAPIView.as_view(),name='to-check-job-edit-status'),
    path('client/get-resumes/',GetResumeView.as_view(),name = 'get-resumes'),
    path('client/reject-application/',RejectApplicationView.as_view(), name ='reject-application'),
    path('client/accept-application/',AcceptApplicationView.as_view(), name ='accept-application'),
    path('client/select-application/',SelectApplicationView.as_view(), name ='select-application'),
    path('client/get-next-interviewer-details/',NextInterviewerDetails.as_view(),name='get-interviewer-details'),
    path('client/add-interviewers/', InterviewersView.as_view(), name='add-interviewers'),
    path('client/get-interviewers/', InterviewersView.as_view(), name='get-interviewers'),
    path('client/scheduled-interviews/<int:job_id>/', ScheduledInterviewsForJobId.as_view(), name='scheduled_interviews'),
    path('get-resume/<int:application_id>/', GetResumeByApplicationId.as_view(), name='get-resume-by-application-id'),
    # path('client/get-next-interviewer-details/',NextInterviewerDetails.as_view(),name='get-interviewer-details'),

    path('interviewer/get-next-interviewer-details/',NextRoundInterviewDetails.as_view(),name='get-interviewer-details'),
    path('interviewer/prev-interview-remarks/', PrevInterviewRemarksView.as_view(), name="previous-interview-remarks" ),
    path('interviewer/scheduled-interviews/',ScheduledInterviewsView.as_view(), name='schedule-interviews'),
    path('interviewer/promote-candidate/', PromoteCandidateView.as_view(), name="promote-candidate"),
    path('interviewer/select-candidate/', SelectCandidate.as_view(), name= 'shortlist-candidate'),
    path('interviewer/reject-candidate/', RejectCandidate.as_view(), name= 'reject-candidate'),

    path('fetch-skills/', JobPostSkillsView.as_view(),name='get-jobpost-skills'),

    path('negotiate-terms/', NegotiateTermsView.as_view(), name='negotiate-terms'),
    path('agency/recruiters/', RecruitersView.as_view(), name='agency-recruiters'),
    path('assign-recruiter/', AssignRecruiterView.as_view(), name='update-recruiters'),

    path('candidate/upcoming-interviews/', CandidateUpcomingInterviews.as_view(), name='candidate-upcoming-interviews'),
    path('candidate/profile/', CandidateProfileView.as_view(), name='candidate-profile-details'),
    path('candidate/certificates/', CandidateCertificatesView.as_view(), name='candidate-certificates'),
    path('candidate/experience/', CandidateExperiencesView.as_view(), name='candidate-experience'), 
    path('candidate/applications/', CandidateApplicationsView.as_view(), name="candidate-application-view"),
    path('candidate/education/', CandidateEducationView.as_view(), name='candidate-experience'), 

    path('rec-job-postings/', RecJobPostings.as_view(), name='rec-job-posting'),
    path('recruiter/get-profile/', RecruiterProfileView.as_view(), name="recruiter-profile"),
    path('recruiter/schedule_interview/pending_application/', ScheduleInterview.as_view(), name='schedule-interviews'),
    
    path('manager/get_invoices/', InvoicesAPIView.as_view(), name='get-invoices'),
    path('manager/close-job/', CloseJobView.as_view(), name='close-job-by-manager'),
    path('manager/dashboard/', AgencyDashboardAPI.as_view() , name='agency-dashboard' ),
    path('manager/job-posts/',AgencyJobPosts.as_view(),name='agency-job-posts' ),

    path('view_candidate_profile/', ViewCandidateProfileAPI.as_view(), name = 'view candidate profile'),
    path('candidate_status_for_job/',CandidateStatusForJobView.as_view(), name='candidate-status-for-particular-job'),
    path('notification_to_update_profile/', NotificationToUpdateProfileView.as_view(), name='notification-to-update-profile'),
]