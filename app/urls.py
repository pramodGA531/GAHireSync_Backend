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
    path('add-profile/', AddProfileView.as_view(), name='add-profile'),
    path('forgotpassword/', ForgotPasswordAPIView.as_view(),name='forgotpassword'),
    path('resetpassword/<uidb64>/<token>/',ResetPasswordAPIView.as_view(), name='resetpassword'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name="verify-email"),
    path('send-verification-email/', VerifyEmailView.as_view(), name="send-verification-email"),
    path('landing-page/fetchjobs/', FetchAllJobs.as_view(), name="send-verification-email"),

    path('changepassword/', changePassword.as_view(), name='changepassword'),
    path('candidate/sendapplication/', SendApplicationDetailsView.as_view(), name='changepassword'),



    path('job-postings/', JobPostingView.as_view(), name='create-job-posting'),
    path('org-job-postings/', OrgJobPostings.as_view(), name='org-job-posting'),
    path('org-particular-job/',OrgParticularJobPost.as_view(), name='org-particular-job'),
    path('org/get-recruiters/', RecruitersList.as_view(), name='get-recruiters-to-allot'),
    path('org-edit-jobpost/', OrgJobEdits.as_view(), name='org-job-edits'),
    path('job-postings/<int:job_id>/', JobPostingView.as_view(), name='edit-job-posting'),
    path('job-details/recruiter/<int:job_id>/', RecJobDetails.as_view(), name='rec-job-details'),
    path('accept-job-post/',AcceptJobEditRequestView.as_view(),name = 'accept-job-post'),
    path('reject-job-post/',RejectJobEditRequestView.as_view(),name='reject-job-post'),

    path('generatequestionary/<int:job_id>', GenerateQuestions.as_view(), name='generate-questionary'),
    path('analyse-resume/<int:job_id>', AnalyseResume.as_view(), name='analyse-resume'),
    path('screen-resume/<int:job_id>', ScreenResume.as_view(), name='screen-resume'),
    path('recruiter/create-candidate/',CandidateResumeView.as_view(),name='candidate-share-resume'),

    path('job-details/', JobDetailsAPIView.as_view(), name='view-job-posting'),
    path('job-details/outsider/', JobDetailsAPIView.as_view(), name='view-job-posting-outsider'),
    path('organization-terms/', OrganizationTermsView.as_view(), name='organization-terms'),
    path('get-organization-terms/', GetOrganizationTermsView.as_view(), name='get-organization-terms'),

    path("client/information/", ClientInfo.as_view(), name="client-info"),
    path('client/dashboard/',ClientDashboard.as_view(), name='client-dashboard-details'),
    path('client/job-postings/', getClientJobposts.as_view(), name='client-job-posting'),
    path('client/edit-job-count/', EditJobsCountView.as_view(), name='count-of-number-of-edit-requests'),
    path('client/not-approval-jobs/', JobEditRequestsView.as_view(),name='get-edited-job-posts'),
    path('client/get-resumes/',GetResumeView.as_view(),name = 'get-resumes'),
    path('client/reject-application/',RejectApplicationView.as_view(), name ='reject-application'),
    path('client/accept-application/',AcceptApplicationView.as_view(), name ='accept-application'),
    path('client/select-application/',SelectApplicationView.as_view(), name ='holds-application'),
    path('client/select-candidate/',HandleSelect.as_view(), name ='selects-application'),
    path('client/applications/complete-resume/',ViewCompleteResume.as_view(), name ='view-complete-application'),
    path('client/get-next-interviewer-details/',NextInterviewerDetails.as_view(),name='get-interviewer-details'),
    path('client/add-interviewers/', InterviewersView.as_view(), name='add-interviewers'),
    path('client/job-post/interviews/', ClientInterviewsView.as_view(), name='client-interviewes'),
    path('client/get-interviewers/', InterviewersView.as_view(), name='get-interviewers'),
    path('client/remove-interviewer/', InterviewersView.as_view(), name='remove-interviewer'),
    path('client/closed-jobslist/',ClosedJobsClient.as_view(), name='list-of-closed-jobs' ),
    path('client/reopen-job/', ReopenJob.as_view(), name='reopen-new-job'),
    path('client/scheduled-interviews/<int:job_id>/', ScheduledInterviewsForJobId.as_view(), name='scheduled_interviews'),
    path('get-resume/<int:application_id>/', GetResumeByApplicationId.as_view(), name='get-resume-by-application-id'),
    path('client/on-hold/', CandidatesOnHold.as_view(), name= 'candidates-on-hold' ),
    path('client/cand-request/', CandidatesRequestedDate.as_view(), name= 'candidates-request' ),
    
    
    path('client/today-joinings/', TodayJoingings.as_view(), name='today-joinings-of-candidates'),
    path('client/joined-candidates/', AllJoinedCandidates.as_view(), name='all-joined-candidates'),
    path('client/candidate-left/', CandidateLeftView.as_view(), name='updating-joining-status-of-candidate-as-left'),
    path('client/candidate-joined/', CandidateJoined.as_view(), name='updating-joining-status-of-candidate-as-joined'),
    path('client/candidate/', ViewCandidateDetails.as_view(), name='view-candidate'),
    path('client/replacements/', ReplacementsView.as_view(), name='apply-replacement-and-get-all-replacements'),
    path('client/replace-candidate/', ReplaceCandidate.as_view(), name='candidate-replacing'),
    path('client/compare-list-view/', CompareListView.as_view(), name='candidate-replacing'),
    path('client/selected-candidates/', SelectedCandidatesView.as_view(), name='candidates-selected'),
    path('client/shortlisted-candidates/', ShortlistedCandidatesView.as_view(), name='candidates-selected'),
    path('client/delete-job-post/', DeleteJobPost.as_view(), name='delete-job-post'),
    path('client/orgs-data/', OrgsData.as_view(), name='orgs-data'),
    path('client/all-alerts/', ClientAllAlerts.as_view(), name='client-all-alerts'),
    path('client/interviewer-details/', InterviewerRoundsView.as_view(), name='client-all-alerts'),


    # path('client/get-next-interviewer-details/',NextInterviewerDetails.as_view(),name='get-interviewer-details'),

    path('interviewer/interviewer-dashboard/',InterviewerDashboardView.as_view(),name='dashboard-of-interviewer'),
    path('interviewer/get-next-interviewer-details/',NextRoundInterviewDetails.as_view(),name='get-interviewer-details'),
    path('interviewer/prev-interview-remarks/', PrevInterviewRemarksView.as_view(), name="previous-interview-remarks" ),
    path('interviewer/scheduled-interviews/',ScheduledInterviewsView.as_view(), name='schedule-interviews'),
    path('interviewer/completed-interviews/',CompletedInterviewsView.as_view(), name='completed-interviews'),
    path('interviewer/missed-interviews/',MissedInterviewsView.as_view(), name='missed-interviews'),
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
    path('candidate/selected-jobs/', SelectedJobsCandidate.as_view(), name = 'list-of-selected-jobs'),
    path('candidate/handle-accepted/', CandidateAcceptJob.as_view(), name='handle-select'),
    path('candidate/handle-rejected/', CandidateRejectJob.as_view(), name='handle-reject'),
    path('candidate/handle-edit/', CandidateEditRequestUpdate.as_view(), name='handle-edit'),
    path('candidate/all-alerts/', CandidateAllAlerts.as_view(), name='candidate-all-alerts'),

    path('rec-job-postings/', RecJobPostings.as_view(), name='rec-job-posting'),
    path('rec-job-summary/', RecSummery.as_view(), name='rec-job-posting'),
    path('rctr/interviews/', GetInterviews.as_view(), name='rctr-interviews'),
    path('rctr/summary/',RecSummaryMetrics.as_view(),name='rctr-summar-metrics'),
    
    

    path('recruiter/get-profile/', RecruiterProfileView.as_view(), name="recruiter-profile"),
    path('recruiter/all-alerts/', RecruiterAllAlerts.as_view(), name='recruiter-all-alerts'),
    path('recruiter/assigned-jobs/', RecAssignedJobsView.as_view(), name='recruiter-assigned-jobs'),
    path('recruiter/schedule_interview/pending_application/', ScheduleInterview.as_view(), name='schedule-interviews'),
    path('recruiter/candidate-selected-jobs/', ReConfirmResumes.as_view(), name = 'list-of-cadidate-selected-jobs'),
    path('recruiter/reconfirmation-accept/', AcceptReconfirmResumes.as_view(), name='handle-select'),
    path('recruiter/reconfirmation-reject/', RejectReconfirmResumes.as_view(), name='handle-reject'),
    path('recruiter/organization-applications/', OrganizationApplications.as_view(), name='organization-all-applications'),
    path('recruiter/resumesent/',ResumesSent.as_view(),name="resumes-sent"),
    path('recruiter/all-scheduled-interviews/',AllScheduledInterviews.as_view(), name='all-scheduled-interviews' ),
    path('recruiter/get-interview-marks/', GetIntervieweRemarks.as_view(), name='get-interview-remarks'),
    path('recruiter/incoming-applications/', IncomingApplicationsView.as_view(), name='get-interview-remarks'),
    path('recruiter/accept-incoming-applications/', AcceptIncomingApplication.as_view(), name='get-interview-remarks'),
    path('recruiter/reject-incoming-applications/', RejectIncomingApplication.as_view(), name='get-interview-remarks'),

    path('get_invoices/',Invoices.as_view()),
    path('update_invoices/',Invoices.as_view()),
    path('basic-application-details/<int:application_id>/',BasicApplicationDetails.as_view(), name='get-basic-applicaiton-details'),
    
    path('manager/clients-data/', ClientsData.as_view(), name='get-invoices'),
    path('manager/get_invoices/', InvoicesAPIView.as_view(), name='get-invoices'),
    
    path('manager/all-alerts/', ManagerAllAlerts.as_view(), name='manager-all-alerts'),
    path('manager/job-action/', AcceptJobPostView.as_view(), name='accept-job-post'),
    path('manager/information/',OrganizationView.as_view(),name='org-info'),
    path('manager/close-job/', CloseJobView.as_view(), name='close-job-by-manager'),
    path('manager/dashboard/', AgencyDashboardAPI.as_view() , name='agency-dashboard' ),
    path('manager/create_accountant/', AccountantsView.as_view() , name='create-acountant' ),
    path('manager/accountants/', AccountantsView.as_view() , name='create-acountant' ),
    path('manager/action-on-edit-job/', JobEditActionView.as_view(), name='handle-job-edit-request'),
    path('manger/applications/',AgencyJobApplications.as_view()),
    path('manager/job-edit-details/',JobEditStatusAPIView.as_view(),name='to-check-job-edit-status'),
    path('manager/job-posts/',AgencyJobPosts.as_view(),name='agency-job-posts' ),
    path('manager/all-recruiters/',AllRecruitersView.as_view(),name='agency-all-recruiters' ),
    path('manager/selected-candidates/',ViewSelectedCandidates.as_view(),name='get-all-selected-candidates' ),
    path('manager/recruiters-task-tracking/',RecruiterTaskTrackingView.as_view(), name='manager-tracking-recruiters'),
    path('manager/recruiter/jobs/',RecruiterJobsView.as_view(), name='manager-tracking-recruiters'),
    path('manager/remove-recruiter/',RemoveRecruiter.as_view(), name='manager-tracking-recruiters'),
    path('manager/is_linkedin_verified/',IsManagerLinkedVerifiedView.as_view(), name='manager-tracking-recruiters'),
    path('manager/job/post_on_linkedin/',PostOnLinkedIn.as_view(), name='manager-tracking-recruiters'),
    

    
    path('api/linkedin/callback/', LinkedINCallBackView.as_view(), name='linkedin callback view'),
 
    path('change-password/', ChangePassword.as_view(), name='change-password'),
    
    path('view-applications/', AllApplicationsForJob.as_view(), name='view-all-applications-for-job-id'),

    path('view_candidate_profile/', ViewCandidateProfileAPI.as_view(), name = 'view candidate profile'),
    path('candidate_status_for_job/',CandidateStatusForJobView.as_view(), name='candidate-status-for-particular-job'),
    path('notification_to_update_profile/', NotificationToUpdateProfileView.as_view(), name='notification-to-update-profile'),
    path('cand/reconfirmation/', CandidateReConfirmation.as_view()),

    path('view-tickets/', RaiseTicketView.as_view(),name='raise-ticket' ),
    path('ticket/send-reply/', HandleReplies.as_view(),name='handle-replies' ),
    path('ticket/update-status/', UpdateStatus.as_view(),name='handle-replies' ),

    path('superadmin/handle-tickets/', HandleTicketView.as_view(),name='handle-tickets-by-admin' ),
    

    path('user/blogs/', BlogPostView.as_view(), name='view-and-create-blogs'),
    path('superadmin/approve-blogs/', ApproveBlogPost.as_view(), name='admin-handling-blogs'),
    path('myblogs/', MyBlogs.as_view(), name='his-blogs'),
    
    path('jobpost/terms/',GetJobPostTerms.as_view(),name='job-terms'),
    
    path('notifications/',GetNotifications.as_view(),name='all-notifications'),
    path('check-notifications/', check_notifications, name='check-notifications'),
    path('update-notification-seen/',NotificationStatusChange.as_view(), name='notification-viewed' ),

    path('complete-application/',CompleteApplicationDetailsView.as_view(),name="resumes-sent"),
    path('hiresync/generate-linkedincode/',GenerateLinkedInTokens.as_view(), name='generate linkedin token for hiresync' ),
    path('hiresync/generate-linkedincode/callback/',LinkedInRedirectView.as_view(), name='callback for linkedin token for hiresync' ),
]