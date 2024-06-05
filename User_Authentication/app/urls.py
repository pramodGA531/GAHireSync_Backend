from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

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
    path("upload_resume/", ResumeUploadView.as_view(), name='upload_resume'),
]
