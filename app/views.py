# from django.shortcuts import render
from rest_framework import viewsets
from .serializers import *
from User_Authentication import settings
import uuid
import json
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, JobPostings, TermsAndConditions, Resume
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
# from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count,F
import random
from django.db.models import Q
import os
from dotenv import load_dotenv
load_dotenv()


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
                
                role = user.role
                is_verified = user.is_verified
                print(is_verified)
                refresh = RefreshToken.for_user(user)
                token = str(refresh.access_token)

                return Response(
                    {"token": str(token), "role": role,"is_verified" : is_verified}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid username or password"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        apiurl = os.getenv('DJANGO_FORNTEND_URL')
        print(apiurl)
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
                        message=f"This is the link to verify your account, please click on this link {apiurl}/verify/?token={email_token}",
                        sender = settings.EMAIL_HOST_USER,
                        receipents_list=data['email']
                        )
            user.save()
            refresh = (RefreshToken.for_user(user))
            token = str(refresh.access_token)

            return Response(
                {"token": token,"is_verified":user.is_verified,"role": user.role}, status=status.HTTP_201_CREATED
            )
        return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ClientSignup(APIView):
    def post(self, request):
        print(request.data)
        data = {
            'username': request.data['username'],
            'email': request.data['email'],
            'password': request.data['password'],
            'role': 'client',  
        }
        email_token = str(uuid.uuid4())
        serializer = UserSerializer(data = data)
        if serializer.is_valid():
            user = serializer.save()
            user.email_token = email_token
            refresh = (RefreshToken.for_user(user))
            token = str(refresh.access_token)
            print(user.email_token,"is the email token", "entred here")
            
            client_data = {
                'username': request.data['username'],
                'email': user.pk,
                'name_of_organization' : request.data['name_of_organization'],
                'designation': request.data['designation'],
                'contact_number': request.data['contact_number'],
                'website_url': request.data['website_url'],
                'gst':request.data['gst'],
                'company_pan': request.data['company_pan'],
                'company_address':request.data['company_address'],
             }
            
            client_serializer = ClientSignupSerializer(data = client_data)
            if client_serializer.is_valid():
                instance = client_serializer.save()
                print(client_serializer.data, "is the client serializer data")
                send_email(subject="Email Verification for RMS ",
                        message=f"This is the link to verify your account, please click on this link http://localhost:3000/verify/?token={email_token}",
                        sender = settings.EMAIL_HOST_USER,
                        receipents_list=data['email']
                        )
                user.save()
                return Response(
                    {"token": token,"is_verified":user.is_verified,"role": user.role}, status=status.HTTP_201_CREATED
                )
            print(client_serializer.errors)
        print(serializer.errors)
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
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        user = request.user
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
        return Response(user_data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        obj = CustomUser.objects.get(username = user)
        for qun,ans in request.data:
            obj.qun = ans
        obj.save()
        print(request.data)
        return Response({"success":"This is the success message"})


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
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        job_postings = JobPostings.objects.filter(username=request.user)
        serializer = JobPostingSerializer(job_postings, many=True)

        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = JobPostingSerializer(data=request.data['job_data'])
        interviewer_data = request.data['interviewers_data']
        if serializer.is_valid() :

            job_instance = serializer.save(username=request.user) 
            for interviewer in interviewer_data:
                interviewer['job_id'] = job_instance.id

            interview_serializer = InterviewerDetailsSerializer(data=interviewer_data,many=True)
            if(interview_serializer.is_valid()):
                interview_serializer.save()
                manager = CustomUser.objects.get(role="manager")
                manager_email= manager.email
                subject =  f'Job added by {request.user}'
                message = f'your Client {request.user} added new Job posts.. go and check it \n this is link go and join \n '
                sender = settings.EMAIL_HOST_USER
                receipents_list = manager_email
                send_email(sender=sender, subject=subject, message=message, receipents_list=receipents_list)
                return Response({"data":serializer.data,"username":str(request.user)}, status=status.HTTP_201_CREATED)
            print(interview_serializer.errors, "is the errors of interviewers")
        print(serializer.errors)
        return Response({"error" : serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class EditJobPostView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, pk):
        data = request.data
        print(data)
        title = request.data['job_title']
        job_post = JobPostings.objects.get(pk =pk)
        user = job_post.username
        job_post.is_approved = False
        job_post.save()
        try:
            job = JobPostingEdited.objects.get(id = pk)
            serializer = EditJobSerializer(job, data=data)
            job.status = 'pending'
            job.save()
        except JobPostingEdited.DoesNotExist:
            # If not found, we'll create a new one
            serializer = EditJobSerializer(data=data)

        if serializer.is_valid():
            serializer.save(username = user)
            # job.status = 'pending'
            # job.save()
            return Response({"success": "Successfully modified"}, status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request,pk):        
        try:
            job_post = JobPostings.objects.get(pk=pk)
            print(job_post.username)
            job_post.is_approved = False
            receiver_email = CustomUser.objects.get(username = job_post.username).email
            print(receiver_email)
        except JobPostings.DoesNotExist:
            return Response({"error": "Job post does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = JobPostingSerializer(instance=job_post, data=request.data)
        if serializer.is_valid():
            serializer.save( username = job_post.username)
            subject = f'Job edited by {request.user}'
            message = f'Your Manager {request.user} has updated your job post. Go and check it!\nThis is the link to see: '
            sender = settings.EMAIL_HOST_USER
            receipients_list = receiver_email
            send_email(sender=sender, subject=subject, message=message , receipents_list=receipients_list)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetAllJobPosts(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

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
    authentication_classes = [JWTAuthentication]

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
    authentication_classes = [JWTAuthentication]

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
    authentication_classes = [JWTAuthentication]
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'manager':
            try:
                job_details = JobPostings.objects.get(id=id)
                interview_details = InterviewerDetails.objects.filter(job_id = id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            interview_serializer = InterviewerDetailsSerializer(interview_details,many=True)
            serializer = GetAllJobPostsSerializer(job_details)
            return Response({"data":serializer.data, "interviewers_data":interview_serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only manager can see this page"})
        

    def put(self, request, id):
        try:
            job_posting = JobPostings.objects.get(id=id)
            data = request.data
            print(data)
            
            # Assuming interviewers_data is an array of objects
            interviewers_data = data.get('interviewers_data', [])
            
            # Iterate through each interviewer data and update/create InterviewerDetails
            for interviewer_data in interviewers_data:
                print("Processing interviewer data")
                round_num = interviewer_data.get('round_num')
                interviewer_name = interviewer_data.get('name')
                interviewer_email = interviewer_data.get('email')
                type_of_interview = interviewer_data.get('type_of_interview')
                
                # Check if InterviewerDetailsEdited instance exists for this round
                interviewer_obj, created = InterviewerDetailsEdited.objects.get_or_create(
                    job_id=job_posting,
                    round_num=round_num,
                    defaults={
                        'name': interviewer_name,
                        'email': interviewer_email,
                        'type_of_interview': type_of_interview
                    }
                )
                
                # If not created (i.e., already exists), update the existing instance
                if not created:
                    print("Updating existing interviewer detail")
                    interviewer_obj.name = interviewer_name
                    interviewer_obj.email = interviewer_email
                    interviewer_obj.type_of_interview = type_of_interview
                    interviewer_obj.status = 'pending'
                    interviewer_obj.edited_by = 'manager'
                    interviewer_obj.save()
            
            # Update JobPostingSerializer with partial=True to allow partial updates
            serializer = JobPostingSerializer(job_posting, data=data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({'success': "Successfully modified"}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except JobPostings.DoesNotExist:
            return Response({"error": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        except InterviewerDetails.DoesNotExist:
            return Response({"error": "Interviewer details not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class GetStaff(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        role = "recruiter"
        staff= CustomUser.objects.filter(role=role)
        print(staff)
        serializer = GetStaffSerializer(staff, many=True)
        return Response(serializer.data)

class SelectStaff(APIView):
    permission_classes  = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        print(request.user)
        try:
            userid = CustomUser.objects.get(username=request.user).id
            jobs = JobPostings.objects.filter(is_assigned = userid).filter(status = 'opened')
            serializer = JobPostingSerializer(jobs,many = True)
            return Response({"data":serializer.data})
        except Exception as e:
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    
    
class ParticularJobForStaff(APIView):
    permission_classes=[IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'recruiter':
            try:
                job_details = JobPostings.objects.get(id=id)
                interview_details = InterviewerDetails.objects.filter(job_id = id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            interview_serializer = InterviewerDetailsSerializer(interview_details,many=True)
            serializer = GetAllJobPostsSerializer(job_details)
            return Response({"data":serializer.data, "interviewers_data":interview_serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only recruiter can see this page"})
        
    def put(self, request, id):
        try:
            job_posting = JobPostings.objects.get(id=id)
            data = request.data
            print(data)
            
            # Assuming interviewers_data is an array of objects
            interviewers_data = data.get('interviewers_data', [])
            
            # Iterate through each interviewer data and update/create InterviewerDetails
            for interviewer_data in interviewers_data:
                print("Processing interviewer data")
                round_num = interviewer_data.get('round_num')
                interviewer_name = interviewer_data.get('name')
                interviewer_email = interviewer_data.get('email')
                type_of_interview = interviewer_data.get('type_of_interview')
                
                # Check if InterviewerDetailsEdited instance exists for this round
                interviewer_obj, created = InterviewerDetailsEdited.objects.get_or_create(
                    job_id=job_posting,
                    round_num=round_num,
                    defaults={
                        'name': interviewer_name,
                        'email': interviewer_email,
                        'type_of_interview': type_of_interview
                    }
                )
                
                # If not created (i.e., already exists), update the existing instance
                if not created:
                    print("Updating existing interviewer detail")
                    interviewer_obj.name = interviewer_name
                    interviewer_obj.email = interviewer_email
                    interviewer_obj.type_of_interview = type_of_interview
                    interviewer_obj.status = 'pending'
                    interviewer_obj.edited_by = 'recruiter'
                    interviewer_obj.save()
            
            # Update JobPostingSerializer with partial=True to allow partial updates
            serializer = JobPostingSerializer(job_posting, data=data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({'success': "Successfully modified"}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except JobPostings.DoesNotExist:
            return Response({"error": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        except InterviewerDetails.DoesNotExist:
            return Response({"error": "Interviewer details not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # try:
        #     job_posting = JobPostings.objects.get(id=id)
        #     data = request.data
        #     print(data)
            
        #     # Assuming interviewers_data is an array of objects
        #     interviewers_data = data.get('interviewers_data', [])
            
        #     # Iterate through each interviewer data and update/create InterviewerDetails
        #     for interviewer_data in interviewers_data:
        #         round_num = interviewer_data.get('round_num')
        #         interviewer_name = interviewer_data.get('name')
        #         interviewer_email = interviewer_data.get('email')
        #         type_of_interview = interviewer_data.get('type_of_interview')
                
        #         # Check if InterviewerDetails instance exists for this round
        #         interviewer_obj, created = InterviewerDetails.objects.get_or_create(
        #             job_id=job_posting,
        #             round_num=round_num,
        #             defaults={
        #                 'name': interviewer_name,
        #                 'email': interviewer_email,
        #                 'type_of_interview': type_of_interview
        #             }
        #         )
                
        #         # If not created (i.e., already exists), update the existing instance
        #         if not created:
        #             interviewer_obj.name = interviewer_name
        #             interviewer_obj.email = interviewer_email
        #             interviewer_obj.type_of_interview = type_of_interview
        #             interviewer_obj.save()
            
        #     # Update JobPostingSerializer with partial=True to allow partial updates
        #     serializer = JobPostingSerializer(job_posting, data=data, partial=True)
            
        #     if serializer.is_valid():
        #         serializer.save()
        #         return Response({'success': "Successfully modified"}, status=status.HTTP_200_OK)
        #     else:
        #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # except JobPostings.DoesNotExist:
        #     return Response({"error": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        # except Exception as e:
        #     print(str(e))
        #     return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        

class ParticularJobForClient(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'client':
            try:
                job_details = JobPostings.objects.get(id=id)
                interview_details = InterviewerDetails.objects.filter(job_id = id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            interview_serializer = InterviewerDetailsSerializer(interview_details,many=True)
            serializer = GetAllJobPostsSerializer(job_details)
            return Response({"data":serializer.data, "interviewers_data":interview_serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only client can see this page"})
    
class ParticularJobEditClient(APIView):
    def get(self,request,id):
        user = CustomUser.objects.get(username = request.user)
        if user.role == 'client':
            try:
                job_details = JobPostingEdited.objects.get(id=id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = GetAllJobPostEditSerializer(job_details)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"warning":"only client can see this page"})

        
class UploadResume(APIView):

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request,id,  *args, **kwargs):
        sender = User.objects.get(username=request.user).id
        job_id = id
        
        print(id)
        if not job_id or job_id == 'undefined':
            return Response({'error': 'Job ID is missing or invalid'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver_name = JobPostings.objects.get(id=job_id).username
            receiver = User.objects.get(username=receiver_name).id
        except JobPostings.DoesNotExist:
            return Response({'error': 'Job posting not found'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'Receiver not found'}, status=status.HTTP_404_NOT_FOUND)

        resume = request.FILES.get('resume')
        if not resume:
            return Response({'error': 'Resume file is missing'}, status=status.HTTP_400_BAD_REQUEST)
        print(request.data.get('skillset'))
        print(request.data)
        try:
            skillset = json.loads(request.data.get('skillset'))
        except json.JSONDecodeError:
            # print("entered 3")
            return Response({'error': 'Invalid skillset data'}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'job_id': job_id,
            'resume': resume,
            'candidate_name': request.data.get('candidate_name'),
            'candidate_email': request.data.get('candidate_email'),
            'candidate_phone': request.data.get('candidate_phone'),
            'other_details': request.data.get('other_details'),
            'sender': sender,
            'receiver': receiver,
            'message': request.data.get('message'),
            'current_organisation': request.data.get('current_organisation'),
            'current_job_type': request.data.get('current_job_type'),
            'alternate_candidate_phone': request.data.get('alternate_candidate_phone'),
            'date_of_birth': request.data.get('date_of_birth'),
            'total_years_of_experience': request.data.get('total_years_of_experience'),
            'years_of_experience_in_cloud': request.data.get('years_of_experience_in_cloud'),
            'skillset': skillset,
            'current_ctc': request.data.get('current_ctc'),
            'expected_ctc': request.data.get('expected_ctc'),
            'notice_period': request.data.get('notice_period'),
            'joining_days_required': request.data.get('joining_days_required'),
            'highest_qualification': request.data.get('highest_qualification'),
            'contact_number': request.data.get('contact_number'),
            'alternate_contact_number': request.data.get('alternate_contact_number'),
            'is_viewed':False,
            'status':'pending',
        }

        file_serializer = ResumeUploadSerializer(data=data)
        if file_serializer.is_valid():
            file_serializer.save()
            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("entered 4",file_serializer.errors) 
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class ResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
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


class NotApprovalJobs(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        user_role = CustomUser.objects.get(username= request.user).role
        if user_role == 'client':
            user = CustomUser.objects.get(username = request.user).id
            data = JobPostingEdited.objects.filter(username=user)
            serializer = EditJobSerializer(data,many=True)
            interviewers_data = []
            jobs = JobPostings.objects.filter(username = request.user)
            for job in jobs:
                interviewers = InterviewerDetailsEdited.objects.filter(job_id = job.id).filter(status = 'pending')
                print(job.id, "is the id")
                print("entereed",interviewers)
                interviewers_serializer = InterviewerDetailsEditedSerializer(interviewers,many = True)
                interviewers_data.append(interviewers_serializer)
            print(interviewers_data)
            print(request.user)
            print(interviewers_serializer.data)
            return Response({"data":serializer.data, "interviewers_data":interviewers_serializer.data})
            
            
        elif user_role == 'manager':
            data = JobPostingEdited.objects.all()
            serializer = EditJobSerializer(data,many=True)
            interviewers_data = InterviewerDetailsEdited.objects.all()
            i_serializer = InterviewerDetailsEditedSerializer(interviewers_data,many=True)
            return Response({"data":serializer.data, "interviewers_data":i_serializer.dataa})


class ApproveJob(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self,request,key):
        job = JobPostings.objects.get(id =key )
        serializer = JobPostingSerializer(job,data = request.data['data'])
        if serializer.is_valid():
            serializer.save()
            job.is_approved = True
            jobedit = JobPostingEdited.objects.get(id=key)
            jobedit.status = 'approved'
            manager = CustomUser.objects.get(role="manager")
            manager_email= manager.email
            print(manager_email)
            try:
                send_email(sender=settings.EMAIL_HOST_USER,
                        subject=f"Your Reqeust has been approved by {request.user}",
                        message="Your request has been approved, go and assign the clients", 
                        receipents_list=manager_email)
                job.save()
                return Response({"success":"Approved successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response({"error":"check your internet connection/email"})
        else:
            print(serializer.errors)
            return Response({"error":"there is an error"}, status=status.HTTP_400_BAD_REQUEST)
    
class RejectJob(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self,request,key):
        print(request.user)
        job = JobPostings.objects.get(id =key )
        job.is_approved = False
        jobedit = JobPostingEdited.objects.get(id=key)
        jobedit.status = 'rejected'
        message = request.data['message']
        jobedit.message = message
        jobedit.save()
        print(jobedit)
        manager = CustomUser.objects.get(role="manager")
        manager_email= manager.email
        print(manager_email)
        try:
            send_email(sender=settings.EMAIL_HOST_USER,
                    subject=f"Your Reqeust has been Rejected by {request.user}",
                    message="Your edit request has been rejected", 
                    receipents_list=manager_email)
            job.save()
            return Response({"success":"Rejected successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"error":"check your internet connection/email"})

class ReceivedData(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        job_counts = CandidateResume.objects.values('job_id').annotate(job_count=Count('job_id'))
        print(job_counts)
        response_data = [{'job_id': job['job_id'], 'job_count': job['job_count']} for job in job_counts]
        return Response(response_data)
        
class JobResume(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request , id):
        # objects = CandidateResume.objects.filter(receiver = request.user).filter(job_id = id).filter(is_accepted = False).filter(is_rejected = False).filter(on_hold = False)
        objects = CandidateResume.objects.filter(receiver = request.user).filter(job_id = id)
        job_details = JobPostings.objects.get(id=id)
        job_serializer = JobPostingSerializer(job_details)
        serializer = ResumeUploadSerializer(objects, many = True)
        return Response({"data":serializer.data,"job_data":job_serializer.data},status=status.HTTP_200_OK)

class CandidateDataResponse(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request,id):
        try:
            obj = CandidateResume.objects.get(id = id)
            response = request.data.get('response')
            job_id = CandidateResume.objects.get(id = id).job_id
            objects = CandidateResume.objects.filter(receiver = request.user).filter(job_id = job_id)
            file_serializer = ResumeUploadSerializer(objects , many = True)
            print(request.data)
            message = ''
            if(response == 'Shortlisted'):
                email = obj.candidate_email
                full_name = obj.candidate_name
                last_name = full_name.split()[-1]
                print("entered", last_name)
                base_username = last_name.replace(' ', '')
                
                # Generate a unique username
                while True:
                    random_number = random.randint(1000, 9999)
                    username = f"{base_username}{random_number}"
                    if not User.objects.filter(username=username).exists():
                        break
                
                password = "123"
                role = 'candidate'
                data = {
                    "email": email,
                    "username": username,
                    "password": password,
                    "role": role,
                }
                serializer = UserSerializer(data=data)
                if serializer.is_valid():
                    serializer.save()
                    print("entered")
                    user = CustomUser.objects.get(username= username)
                    user.is_verified = True
                    user.save()
                    obj.is_accepted = True
                    obj.is_rejected = False
                    feedback = request.data.get('feedback')

                    obj.message = feedback
                    obj.on_hold = False
                    obj.status = 'shortlisted'
                    print(obj.status,"is the status")
                    obj.save()
                    subject = "Your account is created in RMS"
                    description =  f"These are your login credentials, \n username : {username} \n password :{password} \n click here to login http://localhost:3000/"
                    sender = settings.EMAIL_HOST
                    receipent_list = "sivakalkipusarla6@gmail.com"
                    send_email(subject=subject, message= description, sender=sender, receipents_list=receipent_list)
                    
                else:
                    obj.is_accepted = True
                    obj.is_rejected = False
                    obj.on_hold = False
                    feedback = request.data.get('feedback')
                    obj.message = feedback
                    obj.status = 'shortlisted'
                    obj.save()
                    return Response({"success": "Account already created", "details": serializer.errors,"data":file_serializer.data}, status=status.HTTP_200_OK)
            if(response == 'Reject'):
                obj.is_accepted = False
                obj.is_rejected = True
                obj.on_hold = False
                feedback = request.data.get('feedback')
                obj.message = feedback
                obj.status = 'rejected'
            if(response == 'Hold'):
                obj.is_accepted = False
                obj.is_rejected = False
                obj.on_hold = True
                obj.status = 'hole'
            obj.save()
            print(obj.is_accepted, "object saved")
            
            return Response({"success":"Your response saved successfully","message":message,"data":file_serializer.data})  
        except Exception as e:
            print(e) 
            return Response({"error":str(e)})    
        
class ViewedCandidateResume(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def put(self, request, id):
        try:
            obj = CandidateResume.objects.get(id = id)
            obj.is_viewed = True
            obj.save()
            return Response({"success":"edited successfully"}, status= status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":"there is an error"})

class FeedbackResume(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def put(self, request, id):
        try:
            obj = CandidateResume.objects.get(id = id)
            obj.message = request.data.get('feedback')
            print(request.data)
            obj.save()
            print("entereed")
            return Response({"success":"edited successfully"}, status= status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":"there is an error"})

class ViewApplication(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        user = CustomUser.objects.get(username = request.user)
        if(user.role == 'recruiter'):
            objects = CandidateResume.objects.filter(sender = request.user)
            serializer = ResumeUploadSerializer(objects, many=True)
            print(serializer.data)
            return Response({"data":serializer.data}, status=status.HTTP_200_OK)
        if(user.role == 'manager'):
            objects = CandidateResume.objects.all()
            serializer = ResumeUploadSerializer(objects,many = True)
            return Response({"data":serializer.data},status= status.HTTP_200_OK)
        if(user.role=='client'):
            objects = CandidateResume.objects.filter(receiver= request.user)
            serializer = ResumeUploadSerializer(objects,many = True)
            return Response({"data":serializer.data},status= status.HTTP_200_OK)

class ParticularApplication(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, id):
        obj = CandidateResume.objects.get(id = id)
        serializer = ResumeUploadSerializer(obj)
        return Response({"data":serializer.data},status=status.HTTP_200_OK) 

class SearchJobTitles(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        print(request.GET.get('search',''))
        search_term = request.GET.get('search',"")
        if search_term:
            job_titles = JobPostings.objects.filter(job_title__icontains = search_term).values_list('job_title',flat=True).distinct()
            jobs = []
            for job_title in job_titles:
                total_jobs= JobPostings.objects.filter(job_title = job_title)
                for job in total_jobs:
                    if job:
                        jobs.append(job)
            serializer = JobPostingSerializer(jobs, many = True)
            # serializer = JobTitleSerializer(job_titles , many = True)
            print(serializer.data)
            return Response({"data":serializer.data, "titles":job_titles}, status=status.HTTP_200_OK)
        return Response([])

class CandidateApplications(APIView):   
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        user_email = CustomUser.objects.get(username = request.user).email
        objects = CandidateResume.objects.filter(candidate_email = user_email).select_related('job_id')
        serializer = CandidateApplicationsSerializer(objects, many = True)
        print(serializer.data)
        return Response({"success":"true","data":serializer.data})

class InterviewsScheduleList(APIView):
    def post(self,request):
        try:
            dataaa = request.data
            recruiter_id = CustomUser.objects.get(username=request.user).id
            
            # Assuming dataaa contains selectedJobId directly, otherwise fetch it from JobPostings
            job_id = dataaa.get('selectedJobId', None)
            if job_id is None:
                raise ValueError("No job_id found in request data")
            
            # Assuming dataaa contains selectedCandidate directly, otherwise fetch it from Candidate model
            resume_id = dataaa.get('selectedCandidate', None)
            if resume_id is None:
                raise ValueError("No resume_id found in request data")
            
            data = {
                "event_description": dataaa.get('eventDetails', ''),
                "round_num": dataaa.get('selectedRound', ''),
                "job_id": job_id,
                "resume_id": resume_id,
                "interview_time": dataaa.get('datetime', ''),
                "recruiter_id": recruiter_id
            }
            
            serializer = InterviewManageSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": "Event successfully added"}, status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response({"error": "There is an error in the input"}, status=status.HTTP_400_BAD_REQUEST)
        
        except CustomUser.DoesNotExist:
            return Response({"error": "Recruiter does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        except JobPostings.DoesNotExist:
            return Response({"error": "JobPostings does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self,request):
        user_id = CustomUser.objects.get(username = request.user).id
        objects = InterviewsSchedule.objects.filter(recruiter_id=user_id)
        try:
            serializer = InterviewManageSerializer(objects, many = True)
            return Response({"success":serializer.data},status = status.HTTP_200_OK)
        except Exception as e:
            print(serializer.errors)
            return Response({"error":serializer.errors},status = status.HTTP_400_BAD_REQUEST)
        
class JobDetailsForInterviews(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        user_id = CustomUser.objects.get(username = request.user).id
        jobs = JobPostings.objects.filter(is_assigned = user_id)
        # jobs = InterviewerDetails.objects.filter
        candidates = CandidateResume.objects.filter( 
                                Q(status='shortlisted') |
                                Q(status='round1') |
                                Q(status='round2') |
                                Q(status='round3'))
        
        data = []
        for job in jobs:
            json_data={
                "rounds_of_interview": job.rounds_of_interview,
                # "interviewers" : job.interviewers,
                "job_title":job.job_title,
                "id":job.id
            }
            data.append(json_data)
        try:
            serializer = JobDetailsForInterviewSerializer(data,many = True)
            candidateSerializer = CandidateApplicationsSerializer(candidates, many =True)
            return Response({'data':serializer.data,"candidates_data":candidateSerializer.data},status=status.HTTP_200_OK)
            
            # return Response({"error":serializer.errors},status= status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)

class RecruiterDataForClient(APIView):
    def get(self, request ,id):
        recruiter = JobPostings.objects.get(id= id).is_assigned
        recruiter_name = CustomUser.objects.get(username = recruiter).username
        print(recruiter_name)
        resume_sent = CandidateResume.objects.filter(job_id = id).count()
        resume_selected = CandidateResume.objects.filter(job_id=id).filter(status = 'shortlisted').count()
        resume_rejected = CandidateResume.objects.filter(job_id = id).filter(status='rejected').count()
        resume_pending = CandidateResume.objects.filter(job_id = id).filter(status='pending').count()
        data = {
            "recruiter_name":recruiter_name,
            "resume_sent":resume_sent,
            "resume_selected":resume_selected,
            "resume_rejected":resume_rejected,
            "resume_pending" : resume_pending,
        }
        return Response({'data':data},status=status.HTTP_200_OK)

class PromoteCandidates(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self,request):
        candidates = CandidateResume.objects.filter(receiver = request.user)
        serializer = CandidateApplicationsSerializer(candidates , many = True)
        print(serializer.data)
        return Response({"data":serializer.data},status=status.HTTP_200_OK)
    def post(self, request):
        print(request.data)
        data = request.data

        try:
            candidate = CandidateResume.objects.get(id=data['id'])
        except CandidateResume.DoesNotExist:
            return Response({"error": "Candidate not found"}, status=status.HTTP_404_NOT_FOUND)
        
        print(f"Candidate status: {candidate.status}")
        
        rounds = InterviewerDetails.objects.filter(job_id=data['job_id']).count()
        print(f"Total rounds: {rounds}")

        current_status = candidate.status

        try:
            if current_status == 'shortlisted':
                candidate.status = 'round1'
            elif current_status.startswith('round'):
                current_round = int(current_status.replace('round', ''))
                next_round = current_round + 1
                if next_round > rounds:
                    candidate.status = 'accepted'
                else:
                    candidate.status = f'round{next_round}'
            else:
                return Response({"error": "Invalid candidate status"}, status=status.HTTP_400_BAD_REQUEST)
            
            candidate.save()
            print(f"Updated candidate status: {candidate.status}")

            round_num = int(candidate.status.replace('round', '')) if 'round' in candidate.status else None
            print(f"Round number: {round_num}")
            
            if round_num:
                round_data = {
                    "round_num": round_num,
                    "job_id": data['job_id'],
                    "candidate": data['id'],  # Assuming data['id'] is candidate ID, update if it's candidate's name
                    "feedback": data.get('feedback', ''),  # Ensure feedback is provided or set default
                }

                print(f"Round data to be saved: {round_data}")

                candidate_serializer = RoundsDataSerializer(data=round_data)
                if candidate_serializer.is_valid():
                    saved_instance = candidate_serializer.save()
                    print(f"Saved instance: {saved_instance}")
                    if not saved_instance:
                        raise ValueError("Saved instance is None")
                else:
                    print(candidate_serializer.errors)
                    return Response({"error": candidate_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error during status update: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"success": "Successfully promoted"}, status=status.HTTP_200_OK)

class CloseJobs(APIView):
    def get(self, request):
        user_id = CustomUser.objects.get(username = request.user).id
        jobs = JobPostings.objects.filter(is_assigned = user_id)
        data = []
        for job in jobs:
            sent = CandidateResume.objects.filter(sender= user_id).filter(job_id = job.id).count()
            accepted = CandidateResume.objects.filter(sender= user_id).filter(job_id = job.id).filter(status = 'accepted').count()
            rejected = CandidateResume.objects.filter(sender= user_id).filter(job_id = job.id).filter(status = 'rejected').count()
            small_data = {
                "sent" : sent,
                "rejected" : rejected,
                "accepted":accepted,
                "job_id":job.id,
                "status":job.status,
                "job_title":job.job_title
            }
            data.append(small_data)

        return Response({"success":"is the success","data":data})
    
class CloseParticularJob(APIView):
    def post(self, request, id):
        job = JobPostings.objects.get(id = id)
        job.status = 'closed'
        job.save()
        user_id = CustomUser.objects.get(username = request.user).id
        candidates = CandidateResume.objects.filter(sender= user_id).filter(job_id = id).filter(status = 'accepted')
        for candidate in candidates:
            name_parts = candidate.candidate_name.split()        
            if len(name_parts) == 1:
                first_name = name_parts[0]
                middle_name = ''
                last_name = ''
            elif len(name_parts) == 2:
                first_name = name_parts[0]
                middle_name = ''
                last_name = name_parts[1]
            else:
                first_name = name_parts[0]
                middle_name = ' '.join(name_parts[1:-1])
                last_name = name_parts[-1]
            
            small_data = {
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "resume": candidate.resume
            }
            print(small_data,"is the data")
            resumeBank_serializer = ResumeBankSerializer(data = small_data)
            if(resumeBank_serializer.is_valid()):
                resume_bank_instance = resumeBank_serializer.save()
                resume_bank_instance.freeze_resume()
                print("success")
            else:
                print(resumeBank_serializer.errors)
                return Response({"error":resumeBank_serializer.errors})
        return Response({"success":"successfully closed job posting"})
    
class GetResumeBank(APIView):
    def get(self, request):
        resumes = ResumeBank.objects.all()
        resume_serializer = ResumeBankSerializer(resumes,many = True)
        return Response({"data":resume_serializer.data},status=status.HTTP_200_OK)

class ParticularInterviewersEdited(APIView):
    def get(self, request, id):
        interviewers = InterviewerDetailsEdited.objects.filter(job_id = id)
        serializer = InterviewerDetailsEditedSerializer(interviewers,many = True)
        return Response({"data":serializer.data},status=status.HTTP_200_OK)
    
class AcceptInterviewersEdited(APIView):
     def get(self, request, id):
        try:
            # Fetch all edited interviewers for the specified job_id
            edited_interviewers = InterviewerDetailsEdited.objects.filter(job_id=id)
            
            # Fetch all original interviewers for the same job_id
            interviewers = InterviewerDetails.objects.filter(job_id=id)
            
            # Iterate over edited_interviewers and update or create corresponding interviewers
            for edited_interviewer in edited_interviewers:
                edited_interviewer.status = 'accepted'
                edited_interviewer.save()
                round_num = edited_interviewer.round_num
                name = edited_interviewer.name
                email = edited_interviewer.email
                type_of_interview = edited_interviewer.type_of_interview
                
                # Check if there is an existing interviewer in the original data
                interviewer = interviewers.filter(round_num=round_num).first()
                
                if interviewer:
                    # Update existing interviewer
                    interviewer.name = name
                    interviewer.email = email
                    interviewer.type_of_interview = type_of_interview
                    interviewer.save()
                else:
                    # Create new interviewer if not found
                    InterviewerDetails.objects.create(
                        job_id=id,
                        round_num=round_num,
                        name=name,
                        email=email,
                        type_of_interview=type_of_interview
                    )
            
            # Optionally, serialize and return updated interviewers data
            interviewers_updated = InterviewerDetails.objects.filter(job_id=id)
            serializer = InterviewerDetailsSerializer(interviewers_updated, many=True)
            return Response(serializer.data)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class RejectInterviewersEdited(APIView):
    def get(self,request,id):
        interviewers_edited = InterviewerDetailsEdited.objects.filter(job_id = id)
        for interviewer in interviewers_edited:
            interviewer.status = 'Rejected'
            interviewer.save()
        
        return Response({"success":"success"},status = status.HTTP_200_OK)
        
class TermsAndConditionsEditedView(APIView):
    def post(self, request):
        print(request.data)
        user = CustomUser.objects.get(username=request.user)
        email = user.email
        data = {
            'username': user.pk,
            'terms_and_conditions': request.data['negotiationText']
        }

        # Check if the user already has a TermsAndConditionsEdited instance
        try:
            user_tandc_instance = TermsAndConditionsEdited.objects.get(username=user)
            # Update the existing instance
            serializer = TermsAndConditionsEditedSerializer(user_tandc_instance, data=data, partial=True)
        except TermsAndConditionsEdited.DoesNotExist:
            # Create a new instance
            serializer = TermsAndConditionsEditedSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            subject = 'Request From client'
            sender = settings.EMAIL_HOST_USER
            recipients_list = [email]
            message = f'Your client {request.user} has some negotiations with you. You can check those negotiations.'

            send_mail(subject, message, sender, recipients_list)
            
            return Response({"success": "Successfully sent a request"}, status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)