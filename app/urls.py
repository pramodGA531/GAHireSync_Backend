from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r"CustomUser", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginView.as_view()),
    path("signup/", SignupView.as_view(), name="signup"),
    path("user_view/", User_view.as_view()),
    path("job_posting/", JobPostingView.as_view()),
    path("get_all_job_posts/", GetAllJobPosts.as_view()),
    path("t_and_c/", TandC.as_view()),
    path("t_and_c_for_client/", TandC_for_client.as_view()),
    path("verify_email/<str:token>/",Verify_email.as_view(), name='verify_email'),
    path("particular_job/<str:id>/",ParticularJob.as_view()),
    path("get_all_staff/",GetStaff.as_view()),
    path("select_staf/",SelectStaff.as_view()),
    path("get_name/",GetName.as_view()),
    path('candidates_data/<str:id>/',UploadResume.as_view()),
    path("upload_resume/", ResumeUploadView.as_view(), name='upload_resume'),
    path("jobposts_for_staff/",GetJobsForStaff.as_view()),
    path("particular_job_staff/<str:id>/",ParticularJobForStaff.as_view()),
    path("particular_job_client/<str:id>/",ParticularJobForClient.as_view()),
    path("particular_job_edit_client/<str:id>/",ParticularJobEditClient.as_view()),
    path("verify_resend_email/",Resend_verify_email.as_view()),
    path("recruiter/upload_resume/<str:id>",UploadResume.as_view()),
    path("edit_particular_job/<str:pk>/",EditJobPostView.as_view()),
    path('not_approval_jobs/',NotApprovalJobs.as_view()),
    path('client/approve_job/<str:key>/',ApproveJob.as_view()),
    path('client/reject_job/<str:key>/',RejectJob.as_view()),
    path('client/received_data/',ReceivedData.as_view()),
    path('client/job_resume/<str:id>/',JobResume.as_view()),
    path('client/candidate/save_response/<str:id>/',CandidateDataResponse.as_view()),
    path('update_details/',User_view.as_view()),
    path('client/CandidateResume/is_viewed/<str:id>/', ViewedCandidateResume.as_view()),
    path('client/CandidateResume/set_feedback/<str:id>/', FeedbackResume.as_view()),
    path('recruiter/applications/',ViewApplication.as_view()),
    path('particular_application/<str:id>/',ParticularApplication.as_view()),
    path('job_titles/',SearchJobTitles.as_view()),
    path('candidate/applications/',CandidateApplications.as_view()),
    path('manage_interviews/',InterviewsScheduleList.as_view()),
    path('job_details_interview/',JobDetailsForInterviews.as_view()),
    path('client/recruiter_data/<str:id>/',RecruiterDataForClient.as_view()),
    path('client/promote_candidates/',PromoteCandidates.as_view()),
    path('recruiter/close_job_page/',CloseJobs.as_view()),
    path('recruiter/close_particular_job/<str:id>/',CloseParticularJob.as_view()),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

