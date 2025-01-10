from django.urls import path
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
    path('changepassword/', changePassword.as_view(), name='changepassword'),

    path('client/job-postings/', getClientJobposts.as_view(), name='client-job-posting'),
    path('client/not-approval-jobs', JobEditRequestsView.as_view(),name='get-edited-job-posts'),

    path('job-postings/', JobPostingView.as_view(), name='create-job-posting'),
    path('org-job-postings/', OrgJobPostings.as_view(), name='org-job-posting'),
    path('org-particular-job/',OrgParticularJobPost.as_view(), name='org-particular-job'),
    path('org-edit-jobpost/', OrgJobEdits.as_view(), name='org-job-edits'),
    path('rec-job-postings/', RecJobPostings.as_view(), name='rec-job-posting'),
    path('job-postings/<int:job_id>/', JobPostingView.as_view(), name='edit-job-posting'),
    path('job-details/recruiter/<int:job_id>', RecJobDetails.as_view(), name='rec-job-details'),

    path('generatequestionary/<int:job_id>', GenerateQuestions.as_view(), name='generate-questionary'),
    path('analyse-resume/<int:job_id>', AnalyseResume.as_view(), name='analyse-resume'),
    path('screen-resume/<int:job_id>', ScreenResume.as_view(), name='screen-resume'),

    path('job-details/', JobDetailsAPIView.as_view(), name='view-job-posting'),
    path('organization-terms/', OrganizationTermsView.as_view(), name='organization-terms'),
    path('get-organization-terms/', GetOrganizationTermsView.as_view(), name='get-organization-terms'),

    path('negotiate-terms/', NegotiateTermsView.as_view(), name='negotiate-terms'),
    path('agency/recruiters/', RecruitersView.as_view(), name='aagency-recruiters'),
    path('assign-recruiter/', UpdateRecruiterView.as_view(), name='update-recruiters'),
]