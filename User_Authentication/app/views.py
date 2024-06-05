# from django.shortcuts import render
from rest_framework import viewsets
from .serializers import *
from User_Authentication import settings
import uuid
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, JobPostings, TermsAndConditions, Resume
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from rest_framework.authentication import TokenAuthentication
from django.core.mail import send_mail
from rest_framework.parsers import MultiPartParser, FormParser

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
                is_verified = user.is_verified
                print(is_verified)
                return Response(
                    {"token": str(token), "role": role, "is_verified" : is_verified}, status=status.HTTP_200_OK
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
                print("only one user is allowed as manager")
                return Response({"error":"only one manager is allowed"}, status=status.HTTP_400_BAD_REQUEST)
        email_token = str(uuid.uuid4())
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            print(data['role'])
            user = serializer.save()
            user.email_token = email_token
            print(user.email_token,"is the email token")
            send_email(subject="Email Verification for RMS ",
                        message=f"This is the link to verify your account, please click on this link http://localhost:3000/verify/?token={email_token}",
                        sender = settings.EMAIL_HOST_USER,
                        receipents_list=data['email']
                        )
            user.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {"token": str(token),"is_verified":user.is_verified, "role": user.role}, status=status.HTTP_201_CREATED
            )
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class Verify_email(APIView):
    def get(self, request, token):
        # print("token is ", request.data,"and the token is ", token)
        try:
            print("entered here")
            user = CustomUser.objects.get(email_token=token)
            if not user.is_verified:
                user.is_verified = True
                user.save()
                return Response({"message": "Email verification successful.","role":user.role}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Email already verified."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class Resend_verify_email(APIView):
    def post(self, request):
        print(request.data["username"])
        try:
            email_token = str(uuid.uuid4())
            sender_email = settings.EMAIL_HOST_USER
            message = f"Now you can verify this email by clicking this link  http://localhost:3000/verify/?token={email_token}"
            subject = "Verication for RMS portal"
            user = CustomUser.objects.get(username=request.data['username'])
            receipents_list = user.email
            user.email_token = email_token
            print(email_token)
            print(user.email_token)
            user.save()
            send_email(sender=sender_email, message=message, subject=subject, receipents_list=receipents_list)
            return Response({"success":"email sent successfully"},status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({'error':str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
        

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
            serializer.save(username=request.user) 
             # Assign the user to the `username` field
            manager = CustomUser.objects.get(role="manager")
            manager_email= manager.email
            subject =  f'Job added by {request.user}'
            message = f'your Client {request.user} added new Job posts.. go and check it \n this is link go and join \n '
            sender = settings.EMAIL_HOST_USER
            receipents_list = manager_email
            send_email(sender=sender, subject=subject, message=message, receipents_list=receipents_list)
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
            Manager = TermsAndConditions.objects.all()
            serializer = TandC_Serializer(Manager, many=True)
            
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
            user = TermsAndConditions.objects.get(username=request.user)
            serializer = TandC_Serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TermsAndConditions.DoesNotExist:
            return Response(
                {"error": "TermsAndConditions not found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request, *args, **kwargs):
        try:
            user = TermsAndConditions.objects.get(username=request.user)
        except TermsAndConditions.DoesNotExist:
            # If TermsAndConditions does not exist, create a new one
            user = TermsAndConditions.objects.create(username=request.user)

        serializer = TandC_Serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ParticularJob(APIView):

    permission_classes=[IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'manager':
            try:
                job_details = JobPostings.objects.get(id=id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetAllJobPostsSerializer(job_details)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only manager can see this page"})
    
class GetStaff(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self, request):
        role = "recruiter"
        staff= CustomUser.objects.filter(role=role)
        print(staff)
        serializer = GetStaffSerializer(staff, many=True)
        return Response(serializer.data)

class SelectStaff(APIView):
    permission_classes  = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def post(self, request):
        # print(request.data['id'])
        print(request.data.get("client"))
        client = request.data.get("client")
        try:
            id = request.data.get("id")
            print(id)
            obj = JobPostings.objects.get(id=id)
            print(obj)
            print("entered here")
            serializer = JobPostingSerializer(obj)
            user = CustomUser.objects.get(username = client)
            obj.is_assigned = user
            obj.save()
            # obj.save()

            return Response({"success":serializer.data})
        except Exception as e:
            print(e)
            return Response({"error":"there is an error"})

class GetName(APIView):
    def post(self, request):
        user = CustomUser.objects.get(id=request.data.get("id")).username
        return Response({"name":user})
    
class GetJobsForStaff(APIView):
    permission_classes= [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self,request):
        print(request.user)
        try:
            userid = CustomUser.objects.get(username=request.user).id
            jobs = JobPostings.objects.filter(is_assigned = userid)
            serializer = JobPostingSerializer(jobs,many = True)
            return Response({"data":serializer.data})
        except Exception as e:
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    
    
class ParticularJobForStaff(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'recruiter':
            try:
                job_details = JobPostings.objects.get(id=id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetAllJobPostsSerializer(job_details)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only recruiter can see this page"})
        
class UploadResume(APIView):

    # def post(self, request):
    #     sender = CustomUser.objects.get(id = request.data['sender_id']).username
    #     receiver = CustomUser.objects.get(id= request.data['receiver_id']).username
    #     serializer = ResumeUploadSerializer(data=request.data)
    #     if serializer.is_valid():
    #         return Response({"success":"Resume Upload Successfully"})
    #     return Response({"error":"There is an error in uploading resume"})
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def post(self, request, *args, **kwargs):

        sender = CustomUser.objects.get(username = request.user).id
        print(sender,"is the sender")
        job_id = request.data.get('job_id')
        receiver_name = JobPostings.objects.get(id=job_id).username
        receiver = CustomUser.objects.get(username = receiver_name).id
        print(receiver)
        resumes = [request.FILES[key] for key in request.FILES if 'resumes[' in key]
        feedbacks = [request.data[key] for key in request.data if 'feedbacks[' in key]
        if not job_id or not resumes or not feedbacks:
            print("entered here")
            return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
        
        response_data = []

        for resume, feedback in zip(resumes, feedbacks):
            data = {
               'job_id': job_id,
                'resume': resume,
                'message': feedback,
                'sender': sender,
                'receiver': receiver,
            }
            
            file_serializer = ResumeUploadSerializer(data=data)
            if file_serializer.is_valid():
                file_serializer.save()
                response_data.append(file_serializer.data)
            else:
                print(file_serializer.errors)
                return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_data, status=status.HTTP_201_CREATED)


class ResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        print(request)
        if user.role != 'candidate':
            return Response({"error": "Only candidates can upload resumes"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ResumeSerializer(data=request.data, partial=True)
        if serializer.is_valid():

            serializer.save()
            
            return Response({"message": "Resume uploaded successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

