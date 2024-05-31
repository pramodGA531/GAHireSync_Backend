# from django.shortcuts import render
from rest_framework import viewsets
from .serializers import (
    UserSerializer,
    LoginSerializer,
    JobPostingSerializer,
    GetAllJobPostsSerializer,
    TandC_Serializer,
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, JobPostings, ManagerDetails
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
import random


# Create your views here.

def send_email(sender, subject, message,receipents_list):
    send_mail(
        subject,
        message,
        sender,
        [receipents_list],
        fail_silently=False
    )

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            user = authenticate(username=username, password=password)
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                role = user.role
                return Response(
                    {"token": str(token), "role": role}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid username or password"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        if data['role'] == "manager":
            user = CustomUser.objects.filter(role = "manager")
            if user:
                return Response({"error":"only one manager is allowed"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {"token": str(token), "role": user.role}, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class User_view(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, *args, **kwargs):
        user = request.user
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
        return Response(user_data, status=status.HTTP_200_OK)

    def patch(self, request):
        pass


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        # Optionally filter or customize the queryset
        return CustomUser.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        # Custom logic before updating instance
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Custom logic before partially updating instance
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Custom logic before deleting instance
        return super().destroy(request, *args, **kwargs)


class JobPostingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        job_postings = JobPostings.objects.filter(username=request.user)
        serializer = JobPostingSerializer(job_postings, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = JobPostingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(username=request.user)  # Assign the user to the `username` field
            subject =  f'Job added by {request.user}'
            message = f'These are the Job posts details \n {serializer.data}'
            client= CustomUser.objects.get(username = request.user)
            client_email = client.email
            sender_email = CustomUser.objects.get(role = "manager").email
            send_email(sender = client_email, subject=subject, message=message, receipents_list=sender_email)
            print(client_email)
            
            return Response({"data":serializer.data,"username":str(request.user)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAllJobPosts(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        # print(request.role)
        user = CustomUser.objects.get(username=request.user)
        if user.role == "manager":
            job_postings = JobPostings.objects.all()
            serializer = GetAllJobPostsSerializer(job_postings, many=True)
            print(serializer.data)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Only manager can see the details"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class TandC_for_client(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        user = CustomUser.objects.get(username=request.user)
        if user.role == "client":
            Manager = ManagerDetails.objects.all()
            serializer = TandC_Serializer(Manager, many=True)
            print(serializer)
            print(serializer.data)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Only client can see the Terms and conditions"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class TandC(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        try:
            user = ManagerDetails.objects.get(username=request.user)
            serializer = TandC_Serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ManagerDetails.DoesNotExist:
            return Response(
                {"error": "ManagerDetails not found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request, *args, **kwargs):
        try:
            user = ManagerDetails.objects.get(username=request.user)
        except ManagerDetails.DoesNotExist:
            # If ManagerDetails does not exist, create a new one
            user = ManagerDetails.objects.create(username=request.user)

        serializer = TandC_Serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class Authenticating_mail(APIView):
    def post(self, request):
        token = random.randint(1000,9999)
        try:
            send_email(sender='mrsaibalaji112@gmail.com',subject="email authentication",message= f'This is your OTP {token}',receipents_list=request.data['email'])
            print("mail sent successfully")
        except Exception as e:
            print(e,"this is the error")
        # print(request.data['email'])
        return Response({"token":token})
