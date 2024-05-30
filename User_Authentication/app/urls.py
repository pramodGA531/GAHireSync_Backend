from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginView, SignupView, User_view, JobPostingView, GetAllJobPosts, TandC, TandC_for_client

router = DefaultRouter()
router.register(r'CustomUser',UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view()),
    path('signup/', SignupView.as_view(), name='signup'),
    path('user_view/', User_view.as_view() ),
    path('job_posting/', JobPostingView.as_view()),
    path('get_all_job_posts/', GetAllJobPosts.as_view()),
    path('t_and_c/',TandC.as_view()),
    path('t_and_c_for_client/', TandC_for_client.as_view())
]
