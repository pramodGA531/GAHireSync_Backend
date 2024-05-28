from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginView, SignupView, User_view

router = DefaultRouter()
router.register(r'CustomUser',UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view()),
    path('signup/', SignupView.as_view(), name='signup'),
    path('user_view/', User_view.as_view() ),
]