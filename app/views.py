from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
from .serializers import *
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.conf import settings 
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from datetime import datetime
from collections import Counter
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render


import jwt
import string 
import random
from django.contrib.auth.tokens import default_token_generator
from django.template import Template, Context
from django.shortcuts import get_object_or_404
from .utils import *




class ClientSignupView(APIView):
    """
    API view to sign up a new client user.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        combined_values = request.data

        try:
            with transaction.atomic():
                user_serializer = CustomUserSerializer(data={
                    'email': combined_values.get('email'),
                    'username': combined_values.get('username'),
                    'role': CustomUser.CLIENT,
                    'credit' : 50,
                    'password': combined_values.get('password')
                })
                if user_serializer.is_valid(raise_exception=True):
                    user = user_serializer.save()
                    user.set_password(combined_values.get('password'))
                    user.save()
                    
                    
                    client_data = {
                        'username': user.username,
                        'user': user.id,
                        'name_of_organization': combined_values.get('name_of_organization'),
                        'designation': combined_values.get('designation'),
                        'contact_number': combined_values.get('contact_number'),
                        'website_url': combined_values.get('website_url'),
                        'gst_number': combined_values.get('gst'),
                        'company_pan': combined_values.get('company_pan'),
                        'company_address': combined_values.get('company_address')
                    }
                    client_serializer = ClientDetailsSerializer(data=client_data)
                    
                    if client_serializer.is_valid(raise_exception=True):
                        client_serializer.save()
                        subject = 'Welcome to Our Service!'
                        message = 'Thank you for signing up with us.'

                        try:
                            send_mail(
                                subject=subject,
                                message=message,
                                from_email='noreply@hiresync.com',  # Add a valid sender email address
                                recipient_list=[combined_values.get('email')],
                                fail_silently=False,
                            )
                        except Exception as e:
                            # Print error to the console for debugging
                            print(f"Error sending email: {e}")

                            # Return an error message to the frontend
                            return Response(
                                {"error": "There was an issue sending the welcome email. Please try again later."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )

                    return Response({"message": "Client created successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AgencySignupView(APIView):
    """
    API view to sign up a new client user.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        combined_values = request.data
        org_code = combined_values.get('org_code')
        if Organization.objects.filter(org_code=org_code).exists():
            return Response({"error": "Organization with the give code already exists"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                user_serializer = CustomUserSerializer(data={
                    'email': combined_values.get('email'),
                    'username': combined_values.get('username'),
                    'role': CustomUser.MANAGER,
                    'credit' : 0,
                    'password': combined_values.get('password')
                })

                if user_serializer.is_valid(raise_exception=True):
                    user = user_serializer.save()
                    user.set_password(combined_values.get('password'))
                    user.save()
                    
                    
                    org_data = {
                        'name': combined_values.get('name'),
                        'org_code': combined_values.get('org_code'),
                        'contact_number': combined_values.get('contact_number'),
                        'website_url': combined_values.get('website_url'),
                        'gst_number': combined_values.get('gst'),
                        'company_pan': combined_values.get('company_pan'),
                        'company_address': combined_values.get('company_address'),
                        'manager': user.id,
                    }
                    org_serializer = OrganizationSerializer(data=org_data)
                    
                    if org_serializer.is_valid(raise_exception=True):
                        org_serializer.save()
                    subject = "Agency Created Successfully on HireSync"
                    message = f"""
Dear {user.username},

Your agency "{org_data['name']}" has been successfully created on HireSync.

Organization Code: {org_data['org_code']}
Username: {user.username}
Email: {user.email}

Please log in to the platform to explore the features and manage your agency:
Login Link: https://hiresync.com/lpgin

If you have any questions or need assistance, feel free to contact support.

Regards,
HireSync Team
"""
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email='',
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    return Response({"message": "Agency created successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if email is not None:
            email = email.strip()
        password = request.data.get("password")
        if password is not None:
            password = password.strip()
        user = authenticate(request, email=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            # print(refresh)
            access_token = str(refresh.access_token)
            message = f"Successfully signed in. If not done by you please change your password."
            return Response({'access_token': access_token,'role':user.role}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class VerifyTokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token not provided"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded_token = jwt.decode(token, settings.SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM])
            return Response({"valid": True, "decoded_token": decoded_token}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

class TokenRefreshView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        refresh = RefreshToken.for_user(request.user)
        access_token = str(refresh.access_token)
        return Response({'access_token': access_token}, status=status.HTTP_200_OK)

class GetUserDetails(APIView):
    def get(self,request):
        try:
            user = request.user
            data = {
                'username' : user.username,
                'email' : user.email,
                'role' : user.role,
            }
            return Response({'data':data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

class ForgotPasswordAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=404)
        else:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_password_link = f"http://localhost:3000/reset/{uid}/{token}"

            email_template = """
Hi {{ user.username }},
Please click the link below to reset your password:
{{ reset_password_link }}
"""
            template = Template(email_template)
            context = Context({
                'user': user,
                'reset_password_link': reset_password_link,
            })
            print(reset_password_link)
            message = template.render(context)

            send_mail('Reset your password', message,'', [email])
            return Response({'success': 'Password reset email has been sent.'})

class ResetPasswordAPIView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid token.'}, status=400)
        else:
            if default_token_generator.check_token(user, token):
                return Response({'uidb64': uidb64, 'token': token})
            else:
                return Response({'error': 'Invalid token.'}, status=400)

    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid token.'}, status=400)
        else:
            print(default_token_generator.check_token(user, token))
            if default_token_generator.check_token(user, token):
                new_password = request.data.get('password')
                user.set_password(new_password)
                user.save()
                message = f"Password successfully changed. If not done by you please change your password."
                send_mail(
                    'Password Changed',
                    message,
                    '',
                    [user.email],
                    fail_silently=False,
                )
                return Response({'success': 'Password has been reset successfully.'})
            else:
                return Response({'error': 'Invalid token.'}, status=400)

class changePassword(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')
        confirm_password = request.data.get('confirmPassword')

        if user.check_password(current_password):
            if new_password == confirm_password:
                user.set_password(new_password)
                user.save()
                message = f"Password successfully changed. If not done by you please change your password."
                send_mail(
                    'Password Changed',
                    message,
                    '',
                    [user.email],
                    fail_silently=False,
                )
                return Response({'success': True})
            else:
                return Response({'success': False, 'message': 'New passwords do not match.'})
        else:
            return Response({'success': False, 'message': 'Invalid current password.'})

class getClientJobposts(APIView):
    def get(self,request):
        try:
            if request.GET.get('id'):
                id = request.GET.get('id')
                jobpost = JobPostings.objects.get(id=id)
                serializer = JobPostingsSerializer(jobpost)
            else:
                jobpost = JobPostings.objects.filter(username = request.user)
                serializer = JobPostingsSerializer(jobpost,many=True)
            return Response(serializer.data)
        except Exception as e:
            print(str(e))
            return Response(status=status.HTTP_400_BAD_REQUEST, errorData = (str(e)))
        
class JobPostingView(APIView):
    permission_classes = [IsAuthenticated]  

    def post(self, request):
        data = request.data
        username = request.user
        organization = Organization.objects.filter(org_code=data.get('organization_code')).first()
        if not username or username.role != 'client':
            return Response({"detail": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST)

        if not organization:
            return Response({"detail": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                interview_rounds = data.get('interview_rounds', [])
                acceptedterms = data.get('accepted_terms', [])
                job_close_duration_raw = data.get('job_close_duration')
                try:
                    job_close_duration = datetime.strptime(job_close_duration_raw, "%Y-%m-%dT%H:%M:%S.%fZ").date()
                except (ValueError, TypeError):
                    return Response({"detail": "Invalid date format for job_close_duration. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

                job_posting = JobPostings.objects.create(
                    username=username,
                    organization=organization,
                    job_title=data.get('job_title', ''),
                    job_department=data.get('job_department'),
                    job_description=data.get('job_description'),
                    primary_skills=data.get('primary_skills'),
                    secondary_skills=data.get('secondary_skills'),
                    years_of_experience=data.get('years_of_experience','Not Specified'),
                    ctc=data.get('ctc',"Not Specified"),
                    rounds_of_interview = len(interview_rounds),
                    job_locations=data.get('job_locations'),
                    job_type=data.get('job_type'),
                    job_level=data.get('job_level'),
                    qualifications=data.get('qualifications'),
                    timings=data.get('timings'),
                    other_benefits=data.get('other_benefits'),
                    working_days_per_week=data.get('working_days_per_week'),
                    decision_maker=data.get('decision_maker'),
                    decision_maker_email=data.get('decision_maker_email'),
                    bond=data.get('bond'),
                    rotational_shift = data.get('rotational_shift') == "yes",
                    age = data.get('age_limit'),
                    gender = data.get('gender'), 
                    industry = data.get('industry'),
                    differently_abled = data.get('differently_abled'),
                    visa_status = data.get('visa_status'),
                    time_period = data.get('time_period'),
                    notice_period = data.get('notice_period'),
                    notice_time = data.get('notice_time'),
                    qualification_department = data.get('qualification_department'),
                    languages = data.get('languages'),
                    num_of_positions = data.get('num_of_positions'),
                    job_close_duration  = job_close_duration,
                    status='opened',
                    is_approved=False,
                    is_assigned=None,
                    created_at=None
                )

                if interview_rounds:
                    for round_data in interview_rounds:
                        interviewer = CustomUser.objects.get(username = round_data.get('name'))
                        InterviewerDetails.objects.create(
                            job_id=job_posting,
                            round_num=round_data.get('round_num'),
                            name=interviewer,
                            type_of_interview=round_data.get('type_of_interview', ''),
                            mode_of_interview=round_data.get('mode_of_interview'),
                        )
                        print("mode of interview is ",round_data.get('mode_of_interview'), " and total interviewer data is ",round_data)
                client = ClientDetails.objects.get(user=username)
                client_message = f"""
    Dear {username.first_name},
    Your job posting for "{job_posting.job_title}" has been successfully created with the following details:

    **Organization:** {organization.name}
    **Job Title:** {job_posting.job_title}
    **Department:** {job_posting.job_department}
    **Job Location:** {job_posting.job_locations}
    **CTC:** {job_posting.ctc}
    **Years of Experience Required:** {job_posting.years_of_experience}
    **Primary Skills:** {(job_posting.primary_skills or [])}
    **Secondary Skills:** {(job_posting.secondary_skills or [])}

  

    Thank you for using our platform.

    Best regards,
    The Recruitment Team
"""

                manager_message = f"""
Dear {organization.manager.first_name},

A new job posting has been created for your organization "{organization.name}" by {username.first_name} {username.last_name}.

**Job Title:** {job_posting.job_title}
**Department:** {job_posting.job_department}
**Location:** {job_posting.job_locations}
**CTC:** {job_posting.ctc}
**Years of Experience:** {job_posting.years_of_experience}



Please review and approve the posting at your earliest convenience.

Best regards,
The Recruitment Team
"""

                send_mail(
                    subject="Job Posting Created Successfully",
                    message=client_message,
                    from_email='',
                    recipient_list=[username.email]
                )

                send_mail(
                    subject="New Job Posting Created",
                    message=manager_message,
                    from_email='',
                    recipient_list=[organization.manager.email]
                )

                clientTerms = ClientTermsAcceptance.objects.filter(client=client,organization=organization,valid_until__gte=timezone.now())
                if clientTerms.count() < 0:
                    ClientTermsAcceptance.objects.create(client=client,organization=organization,service_fee = acceptedterms.service_fee,replacement_clause = acceptedterms.replacement_clause,invoice_after = acceptedterms.invoice_after,payment_within = acceptedterms.payment_within,interest_percentage = acceptedterms.interest_percentage)
            return Response(
                {"detail": "Job and interview rounds created successfully", "job_id": job_posting.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def put(self, request, job_id):
        job_posting = get_object_or_404(JobPostings, id=job_id)

        data = request.data

        if job_posting.username != request.user:
            return Response({"detail": "You do not have permission to edit this job posting."}, status=status.HTTP_403_FORBIDDEN)

        job_posting.job_title = data.get('job_title', job_posting.job_title)
        job_posting.job_department = data.get('job_department', job_posting.job_department)
        job_posting.job_description = data.get('job_description', job_posting.job_description)
        job_posting.primary_skills = data.get('primary_skills', job_posting.primary_skills)
        job_posting.secondary_skills = data.get('secondary_skills', job_posting.secondary_skills)
        job_posting.years_of_experience = data.get('years_of_experience', job_posting.years_of_experience)
        job_posting.ctc = data.get('ctc', job_posting.ctc)
        job_posting.rounds_of_interview = data.get('rounds_of_interview', job_posting.rounds_of_interview)
        job_posting.job_locations = data.get('job_locations', job_posting.job_locations)
        job_posting.job_type = data.get('job_type', job_posting.job_type)
        job_posting.job_level = data.get('job_level', job_posting.job_level)
        job_posting.qualifications = data.get('qualifications', job_posting.qualifications)
        job_posting.timings = data.get('timings', job_posting.timings)
        job_posting.other_benefits = data.get('other_benefits', job_posting.other_benefits)
        job_posting.working_days_per_week = data.get('working_days_per_week', job_posting.working_days_per_week)
        job_posting.decision_maker = data.get('decision_maker', job_posting.decision_maker)
        job_posting.decision_maker_email = data.get('decision_maker_email', job_posting.decision_maker_email)
        job_posting.bond = data.get('bond', job_posting.bond)
        job_posting.rotational_shift = data.get('rotational_shift', job_posting.rotational_shift)
        job_posting.age = data.get('age_limit', job_posting.age)
        job_posting.gender = data.get('gender', job_posting.gender)
        job_posting.industry = data.get('industry', job_posting.industry)
        job_posting.differently_abled = data.get('differently_abled', job_posting.differently_abled)
        job_posting.visa_status = data.get('visa_status', job_posting.visa_status)
        job_posting.time_period = data.get('time_period', job_posting.time_period)
        job_posting.notice_period = data.get('notice_period', job_posting.notice_period)
        job_posting.languages = data.get('languages', job_posting.languages)
        job_posting.notice_time = data.get('notice_time', job_posting.notice_time)
        job_posting.num_of_positions = data.get('num_of_positions', job_posting.num_of_positions)
        job_posting.job_close_duration = data.get('job_close_duration', job_posting.job_close_duration)

        job_posting.save()

        return Response({"detail": "Job posting updated successfully", "id": job_posting.id}, status=status.HTTP_200_OK)
    
class AcceptJobPostView(APIView):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.role != 'manager':  
                return Response({"error": "You are not allowed to run this view"}, status=status.HTTP_403_FORBIDDEN)
            
            job_id = int(request.GET.get('id'))
            print(job_id, "is the id")
            if not job_id:
                return Response({"error": "Job post id is required"}, status=status.HTTP_400_BAD_REQUEST) 
            
            accept = request.query_params.get('accept')


            try:
                job_post = JobPostings.objects.get(id = job_id)
                if accept:
                    job_post.approval_status  = "accepted"
                else:
                    job_post.approval_status  = "rejected"

                job_post.save()
                return Response({"message":"Job post updated successfully"}, status=status.HTTP_200_OK)
            except JobPostings.DoesNotExist:
                return Response({"error":"Job post does not exists"}, status = status.HTTP_400_BAD_REQUEST)


        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    
class JobEditRequestsView(APIView):
    def get(self, request):
        try:
            user = request.user
            if(user.role != 'client'):
                return Response({"error":"You are not allowed to view this"}, status=status.HTTP_400_BAD_REQUEST)
            if(request.GET.get('id')):
                id = request.GET.get('id')
                try:  
                    job = JobPostings.objects.get(id = id)
                    edited_job = JobPostingsEditedVersion.objects.get(id = id)
                    if(edited_job.status != 'pending'):
                        return Response({"error":"You have already reacted to this job post edit"}, status = status.HTTP_400_BAD_REQUEST)
                    serialized_edited_job = JobPostEditedSerializer(edited_job)
                    serialized_job = JobPostingsSerializer(job)
                    return Response({"data":serialized_edited_job.data,"job":serialized_job.data}, status = status.HTTP_200_OK)
                except JobPostings.DoesNotExist:
                    return Response({"error":"job posting not found"},status = status.HTTP_400_BAD_REQUEST)
                except JobPostingsEditedVersion.DoesNotExist:
                    return Response({"error":"Job posting edited not found"},status = status.HTTP_400_BAD_REQUEST)
            else:
                edited_jobs = JobPostingsEditedVersion.objects.filter(username = user)
                if not edited_jobs:
                    return Response({"details":"There are no Edit Job Requests"}, status = status.HTTP_200_OK)
                serialized_edited_jobs = JobPostEditedSerializerMinFields(edited_jobs,many=True)
                return Response(serialized_edited_jobs.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"details":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class AcceptJobEditRequestView(APIView):
    def get(self, request):
        try:
            id = request.GET.get('id')
            user = request.user
            if user.role != 'client':
                return Response({"error":"You are not allowed to do this request"}, status=status.HTTP_400_BAD_REQUEST)
            edited_job = JobPostingsEditedVersion.objects.get(id=id)
            if not edited_job:
                return Response({"error":"Unable to process your request"}, status = status.HTTP_400_BAD_REQUEST)
            
            edited_job = JobPostingsEditedVersion.objects.get(id=id)
            job_post = JobPostings.objects.get(id=id)
            organization = job_post.organization
            manager_mail = organization.manager.email

            edited_data_serializer = JobPostUpdateSerializer(edited_job)
            edited_data = edited_data_serializer.data
            if 'notice_time' not in edited_data:
                edited_data['notice_time'] = ''
            if 'time_period' not in edited_data:
                edited_data['time_period'] = ''
                
            job_post_serializer = JobPostUpdateSerializer(instance=job_post, data=edited_data, partial=True)
            if job_post_serializer.is_valid():
                job_post_serializer.save()
            else:
                print(job_post_serializer.errors)
                return Response(job_post_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            edited_interviewers = InterviewerDetailsEditedVersion.objects.filter(job_id= id)
            edited_inter_serializer = InterviewDetailsEditedSerializer(edited_interviewers,many = True)
            edited_inter_data = edited_inter_serializer.data

            for interviewer in edited_inter_data:
                interviewer_instance = InterviewerDetails.objects.get(job_id = job_post, round_num = interviewer['round_num'] )

                interviewer_instance.type_of_interview = interviewer.get('type_of_interview')
                interviewer_instance.mode_of_interview = interviewer.get('mode_of_interview')
                interviewer_instance.save()

            job_edit_status = JobPostingsEditedVersion.objects.get(id = id)
            job_edit_status.status = 'accepted'
            job_edit_status.save()
            
             
            
             
            client_email_message = f"""
            # Dear Manager,

            We are pleased to inform you that your requested changes to the job posting have been accepted and processed successfully.

            Thank you for your continued support. The job posting has been updated accordingly.

            Best regards,  
            The Recruitment Team
            """

            # Send the email to the manager
            send_mail(
                subject="Accepted Edit Request",
                message=client_email_message,
                from_email='your-client@example.com',  # Replace with your actual sender email
                recipient_list=[manager_mail]
            )

            return Response({"message": "Job edit request accepted successfully"}, status = status.HTTP_200_OK)

        except JobPostingsEditedVersion.DoesNotExist:
            return Response({"error": "Edited job post not found"}, status=status.HTTP_404_NOT_FOUND)
        except JobPostings.DoesNotExist:
            return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class RejectJobEditRequestView(APIView):
    def get(self, request):
        try:
            if(not request.user):
                return Response({"error":"You are not an user"},status=status.HTTP_400_BAD_REQUEST)
            if not request.user.role =='client':
                return Response({"error":"You are not allowed to do this job"},status=status.HTTP_400_BAD_REQUEST)
            id = request.GET.get('id')
            job = JobPostings.objects.get(id=id)
            organization = organization.organization
            manager_mail = organization.manager.email
            edited_job =JobPostingsEditedVersion.objects.get(id = job)
            edited_job.status = 'rejected'
            edited_job.save()
            client_email_message = f"""
            # Dear Manager,

            We are sorry to inform you that your requested changes to the job posting have been Rejected 

            Thank you for your continued support. The job posting has been Rejected.

            Best regards,  
            The Recruitment Team
            """

            # Send the email to the manager
            send_mail(
                subject="Accepted Edit Request",
                message=client_email_message,
                from_email='your-client@example.com',  # Replace with your actual sender email
                recipient_list=[manager_mail]
            )
            return Response({"message":"Rejected successfully"}, status=status.HTTP_200_OK)
        except JobPostings.DoesNotExist:
            return Response({"error":"Edited Job not found"},status=status.HTTP_400_BAD_REQUEST)
        except JobPostingsEditedVersion.DoesNotExist:
            return Response({"error":"Edited Job not found"},status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class OrganizationTermsView(APIView):
    permission_classes = [IsAuthenticated]   

    def get(self, request):
        user = request.user
        organization = Organization.objects.filter(manager=user).first()

        if not organization:
            return render(request, "error.html", {"message": "Organization not found"})
        
        values = request.GET.get('values')
        if values:
            try:
                organization_terms = OrganizationTerms.objects.get(organization = organization)
                serializer = OrganizationTermsSerializer(organization_terms)
            except OrganizationTerms.DoesNotExist:
                return Response({"error":"Organization Terms does not exist"}, status = status.HTTP_400_BAD_REQUEST)
            return Response({"data":serializer.data}, status=status.HTTP_200_OK)

        organization_terms, _ = OrganizationTerms.objects.get_or_create(organization=organization)
        serializer = OrganizationTermsSerializer(organization_terms)
        data = serializer.data

        context = {
            "service_fee": data.get("service_fee"),
            "invoice_after": data.get("invoice_after"),
            "payment_within": data.get("payment_within"),
            "replacement_clause": data.get("replacement_clause"),
            "interest_percentage": data.get("interest_percentage"),
            "data":data
        }

        return render(request, "organizationTerms.html", context)



    def put(self, request):
        try:
            user = request.user
            organization = Organization.objects.filter(manager = user).first()
            organization_terms = get_object_or_404(OrganizationTerms, organization = organization)
            data = request.data
            if data.get('description'):
                organization_terms.description = data.get('description' , organization_terms.description)
                organization_terms.save()
                return Response({"message":"Organization description updated successfully"}, status = status.HTTP_200_OK)
            else:
                organization_terms.service_fee = data.get('service_fee', organization_terms.service_fee)
                organization_terms.replacement_clause = data.get('replacement_clause', organization_terms.replacement_clause)
                organization_terms.invoice_after = data.get('invoice_after', organization_terms.invoice_after)
                organization_terms.payment_within = data.get('payment_within', organization_terms.payment_within)
                organization_terms.interest_percentage = data.get('interest_percentage', organization_terms.interest_percentage)
                organization_terms.save()

                return Response({"detail": "Organization terms updated successfully", "id": organization_terms.id}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)


class GetOrganizationTermsView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request):
        user = request.user
        org_code = request.GET.get('org_code')
        try:
            organization = Organization.objects.get(org_code = org_code)
        except:
            return Response({"detail": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        
        client = ClientDetails.objects.get(user=user)
        clientTerms = ClientTermsAcceptance.objects.filter(client=client,organization=organization,valid_until__gte=timezone.now())

        if clientTerms.count() > 0:
            organization_terms=clientTerms.first()
        else:
            organization_terms = OrganizationTerms.objects.get(organization = organization)

        serializer = OrganizationTermsSerializer(organization_terms)
        data = serializer.data
        context = {
            "service_fee": data.get("service_fee"),
            "invoice_after": data.get("invoice_after"),
            "payment_within": data.get("payment_within"),
            "replacement_clause": data.get("replacement_clause"),
            "interest_percentage": data.get("interest_percentage"),
            "data":data
        }

        context['data_json'] = json.dumps(context['data'])

        html = render_to_string("organizationTerms.html", context)
        return HttpResponse(html)

class NegotiateTermsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == "manager":
            organization = Organization.objects.get(manager=user)
            negotiationrequests = NegotiationRequests.objects.filter(organization=organization)
        elif user.role == "client":
            client = ClientDetails.objects.get(user=user)
            negotiationrequests = NegotiationRequests.objects.filter(client=client)
        else:
            return Response({"detail": "You are not authorized to access this page"}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = NegotiationSerializer(negotiationrequests, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.role != "client":
            return Response({"detail": "Only clients can create negotiation requests"}, status=status.HTTP_403_FORBIDDEN)

        client = ClientDetails.objects.get(user=user)
        code = request.data.get('code')
        organization = Organization.objects.filter(org_code=code).first()

        if not organization:
            return Response({"detail": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = request.data

            negotiation_request = NegotiationRequests.objects.create(
                client=client,
                organization=organization,
                service_fee=data.get('service_fee'),
                replacement_clause=data.get('replacement_clause'),
                invoice_after=data.get('invoice_after'),
                payment_within=data.get('payment_within'),
                interest_percentage=data.get('interest_percentage')
            )

            
            client_email_message = f"""
Dear {client.user.first_name},

Your negotiation request has been successfully submitted to {organization.name}. The details of your request are as follows:

**Service Fee:** {data.get('service_fee')}
**Replacement Clause:** {data.get('replacement_clause')}
**Invoice After:** {data.get('invoice_after')} days
**Payment Within:** {data.get('payment_within')} days
**Interest Percentage:** {data.get('interest_percentage')}%

We will notify you as soon as the organization manager reviews your request.

Best regards,  
The Negotiation Team
"""

            
            manager_email_message = f"""
Dear {organization.manager.first_name},

A new negotiation request has been submitted by {client.user.first_name} {client.user.last_name} from {organization.name}. Here are the details:

**Service Fee:** {data.get('service_fee')}
**Replacement Clause:** {data.get('replacement_clause')}
**Invoice After:** {data.get('invoice_after')} days
**Payment Within:** {data.get('payment_within')} days
**Interest Percentage:** {data.get('interest_percentage')}%

Please review this request at your earliest convenience.

Best regards,  
The Negotiation Team
"""

            
            send_mail(
                subject="Negotiation Request Submitted",
                message=client_email_message,
                from_email='',
                recipient_list=[client.user.email]
            )

            send_mail(
                subject="New Negotiation Request Received",
                message=manager_email_message,
                from_email='',
                recipient_list=[organization.manager.email]
            )

            return Response({"detail": "Negotiation request created successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        data = request.data
        user = request.user

        if user.role != "manager":
            return Response({"detail": "Only managers can update negotiation requests"}, status=status.HTTP_403_FORBIDDEN)

        try:
            negotiation_request = NegotiationRequests.objects.get(id=data.get('id'))

            
            if data.get('status') == "accepted":
                negotiation_request.is_accepted = True
                negotiation_request.save()

                
                ClientTermsAcceptance.objects.create(
                    client=negotiation_request.client,
                    organization=negotiation_request.organization,
                    service_fee=negotiation_request.service_fee,
                    replacement_clause=negotiation_request.replacement_clause,
                    invoice_after=negotiation_request.invoice_after,
                    payment_within=negotiation_request.payment_within,
                    interest_percentage=negotiation_request.interest_percentage
                )

                
                client_email_message = f"""
Dear {negotiation_request.client.user.first_name},

Your negotiation request with {negotiation_request.organization.name} has been accepted. Here are the agreed terms:

**Service Fee:** {negotiation_request.service_fee}
**Replacement Clause:** {negotiation_request.replacement_clause}
**Invoice After:** {negotiation_request.invoice_after} days
**Payment Within:** {negotiation_request.payment_within} days
**Interest Percentage:** {negotiation_request.interest_percentage}%

Thank you for negotiating with us. We look forward to a successful collaboration.

Best regards,  
{negotiation_request.organization.name} Team
                """
                send_mail(
                    subject="Negotiation Request Accepted",
                    message=client_email_message,
                    from_email="",
                    recipient_list=[negotiation_request.client.user.email]
                )

            elif data.get('status') == "rejected":
                negotiation_request.is_accepted = False
                negotiation_request.save()

                
                client_email_message = f"""
Dear {negotiation_request.client.user.first_name},

We regret to inform you that your negotiation request with {negotiation_request.organization.name} has been rejected.

Please feel free to reach out to discuss any other possible terms.

Best regards,  
{negotiation_request.organization.name} Team
                """
                send_mail(
                    subject="Negotiation Request Rejected",
                    message=client_email_message,
                    from_email="",
                    recipient_list=[negotiation_request.client.user.email]
                )

            else:
                return Response({"detail": "Invalid status provided. Please use 'accepted' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Negotiation request updated successfully"}, status=status.HTTP_200_OK)

        except NegotiationRequests.DoesNotExist:
            return Response({"detail": "Negotiation request not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class OrgJobPostings(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            job_postings = JobPostings.objects.filter(organization=org)
            serializer = JobPostingsSerializer(job_postings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
class OrgParticularJobPost(APIView):
    def get(self, request):
        try:
            user= request.user
            if(user.role == 'manager'):
                id = request.GET.get('id')
                if(id==None):
                    return Response({"error":"ID is not mentioned"}, status= status.HTTP_400_BAD_REQUEST)
                try:
                    jobEditedPost = JobPostingsEditedVersion.objects.get(id=id).status
                    if jobEditedPost=='pending': 
                        print("your job edit request is in pending")    
                        return Response({"error":"Your have already sent an edit request to this job post"}, status = status.HTTP_400_BAD_REQUEST)
                except JobPostingsEditedVersion.DoesNotExist:
                    pass
                
                jobPost = JobPostings.objects.get(id = id)
                jobPost_serializer = JobPostingsSerializer(jobPost)
                return Response(jobPost_serializer.data, status=status.HTTP_200_OK) 
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status= status.HTTP_400_BAD_REQUEST)
        
class OrgJobEdits(APIView):
    def get(self, request):
        try:
            user = request.user
            print('user is ', user)
            if( request.GET.get('id')):
                id = request.GET.get('id')
                edited_job = JobPostingsEditedVersion.objects.get(id = id)
                if(edited_job.edited_by != user):
                    return Response({'error':'You are not allowed to edit other people job posts'}, status=status.HTTP_400_BAD_REQUEST)
                serialized_edited_job = JobPostEditedSerializer(edited_job)
                return Response(serialized_edited_job.data,status=status.HTTP_202_ACCEPTED)
            else:
                edited_jobs = JobPostingsEditedVersion.objects.filter(edited_by = user)
                if(edited_jobs == None):
                    return Response({"message":"There are no edited job posts"}, status=status.HTTP_200_OK)
                edited_jobs_serialized_data = JobPostEditedSerializerMinFields(edited_jobs,many = True)
                return Response(edited_jobs_serialized_data.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        data = request.data
        username = request.user
        id = request.GET.get('id')
        # print(" is the job id")
        # if(id != data.get('job_post_id')):
        #     return Response({"details":"job post details are not matching"}, status = status.HTTP_400_BAD_REQUEST)
        organization = Organization.objects.filter(org_code=data.get('organization_code')).first()
        job = JobPostings.objects.get(id = id)
        if not username or username.role != 'manager':
            return Response({"detail": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST)

        if not organization:
            return Response({"detail": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not job:
            return Response({"detail":"Invalid Job ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            job_edited_post = JobPostingsEditedVersion.objects.get(id=id)
            if(job_edited_post) and job_edited_post.status != 'pending':
                job_edited_post.delete()
                InterviewerDetailsEditedVersion.objects.filter(job_id=id).delete()
        except JobPostingsEditedVersion.DoesNotExist:
            pass

        try:
            with transaction.atomic():
                interview_rounds = data.get('interview_details', [])
                client = JobPostings.objects.get(id=id).username
                client_email=client.email
                
                print("client",client)
                job_posting = JobPostingsEditedVersion.objects.create(
                    id = job,
                    username = client,
                    edited_by=username,
                    organization=organization,
                    job_title=data.get('job_title', ''),
                    job_department=data.get('job_department'),
                    job_description=data.get('job_description'),
                    primary_skills=data.get('primary_skills'),
                    secondary_skills=data.get('secondary_skills'),
                    years_of_experience=data.get('years_of_experience','Not Specified'),
                    ctc=data.get('ctc',"Not Specified"),
                    rounds_of_interview = len(interview_rounds),
                    job_locations=data.get('job_locations'),
                    job_type=data.get('job_type'),
                    job_level=data.get('job_level'),
                    qualifications=data.get('qualifications'),
                    timings=data.get('timings'),
                    other_benefits=data.get('other_benefits'),
                    working_days_per_week=data.get('working_days_per_week'),
                    decision_maker=data.get('decision_maker'),
                    decision_maker_email=data.get('decision_maker_email'),
                    bond=data.get('bond'),
                    rotational_shift = data.get('rotational_shift') == "yes",
                    age = data.get('age'),
                    gender = data.get('gender'), 
                    industry = data.get('industry'),
                    differently_abled = data.get('differently_abled'),
                    visa_status = data.get('visa_status'),
                    time_period = data.get('time_period'),
                    notice_period = data.get('notice_period'),
                    notice_time = data.get('notice_time',''),
                    qualification_department = data.get('qualification_department'),
                    languages = data.get('languages'),
                    num_of_positions = data.get('num_of_positions'),
                    job_close_duration  = data.get('job_close_duration'),
                    status = 'pending'
                )

                if interview_rounds:
                    for round_data in interview_rounds:
                        print(round_data)
                        name = CustomUser.objects.get(username = round_data.get('name').get('username'))
                        InterviewerDetailsEditedVersion.objects.create(
                            job_id=job_posting,
                            round_num=round_data.get('round_num'),
                            name=name,
                            type_of_interview=round_data.get('type_of_interview', ''),
                            mode_of_interview=round_data.get('mode_of_interview'),
                        )
                        
                client_message = f"""
                We would like to inform you that there has been a request to edit the job posting for "{job_posting.job_title}" with the following details:

                Please review the requested changes and update the job posting accordingly.

                Thank you for using our platform.

                Best regards,  
                The Recruitment Team
                """

                send_mail(
                    subject="Upadte In Job Posting",
                    message=client_message,
                    from_email='',
                    recipient_list=[client_email]
                )
            return Response(
                {"detail": "Job post and interview rounds edit request sent successfully"},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class JobDetailsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            job_id = request.GET.get('job_id')
            job_posting = JobPostings.objects.get(id=job_id)
            serializer = JobPostingsSerializer(job_posting)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)

class JobEditStatusAPIView(APIView):
    def get(self, request):
        try:
            job_id = request.GET.get('id')
            job_edit_post = JobPostingsEditedVersion.objects.get(id=job_id)
            return Response({"status":job_edit_post.status}, status=status.HTTP_200_OK)
        except JobPostingsEditedVersion.DoesNotExist:
            return Response({'notFound':"Job edit post not found"},status= status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)
class RecruitersView(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            serializer = OrganizationSerializer(org)
            return Response(serializer.data["recruiters"], status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def post(self, request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            alloted_to_id = request.data.get('alloted_to')
            alloted_to = CustomUser.objects.get(id = alloted_to_id)
            
            username = request.data.get('username')
            email = request.data.get('email')

            password = generate_random_password()

            user_serializer = CustomUserSerializer(data={
                'email': email,
                'username': username,
                'role': CustomUser.RECRUITER,
                'credit': 0,
                'password': password,
            })

            if user_serializer.is_valid(raise_exception=True):
                new_user = user_serializer.save()
                new_user.set_password(password)
                new_user.save()
                
                RecruiterProfile.objects.create(
                    name = new_user,
                    alloted_to = alloted_to,
                    organization = org,
                )

                org.recruiters.add(new_user)

                subject = "Account Created on HireSync"
                message = f"""
Dear {username},

Welcome to HireSync! Your recruiter account has been successfully created.

Here are your account details:
Username: {username}
Email: {email}
Password: {password}

Please log in to your account and change your password for security purposes.

Login Link: https://hiresync.com/login

If you have any questions, feel free to contact our support team.

Regards,
HireSync Team
                """

                send_mail(
                    subject=subject,
                    message=message,
                    from_email='',
                    recipient_list=[email],
                    fail_silently=False,
                )

                return Response(
                    {"message": "Recruiter account created successfully, and email sent."},
                    status=status.HTTP_201_CREATED
                )

        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found for the current user."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UpdateRecruiterView(APIView):
    def post(self,request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            if org:
                job_id = request.data.get('job_id')
                job = JobPostings.objects.get(id=job_id,organization = org)
                recruiter_id = request.data.get('recruiter_id')
                recruiter = CustomUser.objects.get(id=recruiter_id)
                job.is_assigned = recruiter
                job.save()
                return Response({"detail":"Recruiter Assigned Successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RecJobPostings(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job_postings = JobPostings.objects.filter(organization=org, is_assigned = user)
            serializer = JobPostingsSerializer(job_postings,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RecJobDetails(APIView):
    def get(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = JobPostings.objects.get(id=job_id, organization=org)
            serializer = JobPostingsSerializer(job)

            resume_count = JobApplication.objects.filter(job_id = job_id, sender = user).count()

            try:
                summary = summarize_jd(job)
            except:
                summary = ''
            return Response({'jd':serializer.data,'summary':summary, 'count':resume_count}, status=status.HTTP_200_OK)
        except:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)


class GenerateQuestions(APIView):
    def get(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = JobPostings.objects.get(id=job_id, organization=org)
            questions = generate_questions_with_gemini(job)
            return Response(questions, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

class AnalyseResume(APIView):
    def post(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = JobPostings.objects.get(id=job_id, organization=org)
            resume = request.FILES.get('resume')
            resume = extract_text_from_file(resume)
            analysis = analyse_resume(job, resume)
            return Response(analysis, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

class ScreenResume(APIView):
    def post(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = JobPostings.objects.get(id=job_id, organization=org)
            resume = request.FILES.get('resume')
            resume = extract_text_from_file(resume)
            analysis = screen_profile_ai(job,resume)
            return Response(analysis, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        

class CandidateResumeView(APIView):
    parser_classes = (MultiPartParser, FormParser)


    def post(self, request):
        try:
            job_id = request.GET.get('id')
            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            if not user or user.role != 'recruiter':
                return Response({"error": "You are not allowed to handle this request"}, status=status.HTTP_403_FORBIDDEN)

            job = JobPostings.objects.get(id=job_id)
            receiver = job.username

            if 'resume' not in request.FILES:
                return Response({"error": "Resume file is required."}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data
            date_string = data.get('date_of_birth', '')

            try:
                date_of_birth = datetime.strptime(date_string, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Please use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
            primary_skills = json.loads(data.get('primary_skills', '[]'))
            secondary_skills = json.loads(data.get('secondary_skills', '[]'))

            if not primary_skills:
                return Response({"error": "Primary skills are required"}, status=status.HTTP_400_BAD_REQUEST)

            if JobApplication.objects.filter(
                job_id=job, resume__candidate_email=data.get('candidate_email')
            ).exists():
                return Response({"error": "Candidate application is submitted previously"}, status=status.HTTP_400_BAD_REQUEST)

            #check job application of this user, with this id
            try:
                resumes =  CandidateResume.objects.filter(candidate_name = data.get('candidate_name'))
                application = JobApplication.objects.get(job_id = job_id, resume__in = resumes)

                if application:
                    return Response({"error":"Job application already posted for this email id"}, status=status.HTTP_400_BAD_REQUEST)
            except JobApplication.DoesNotExist:

            # Create a CandidateResume instance
                candidate_resume = CandidateResume.objects.create(
                    resume=request.FILES['resume'],
                    candidate_name=data.get('candidate_name'),
                    candidate_email = data.get('candidate_email'),
                    contact_number=data.get('contact_number'),
                    alternate_contact_number=data.get('alternate_contact_number', ''),
                    other_details=data.get('other_details', ''),
                    current_organisation=data.get('current_organization', ''),
                    current_job_location=data.get('current_job_location', ''),
                    current_job_type=data.get('current_job_type', ''),
                    date_of_birth=date_of_birth,
                    experience=data.get('experience', ''),
                    current_ctc=data.get('current_ctc', ''),
                    expected_ctc=data.get('expected_ctc', ''),
                    notice_period=data.get('notice_period', ''),
                    job_status=data.get('job_status', ''),
                )

                # Add Primary Skills
                for skill, experience in primary_skills:
                    PrimarySkillSet.objects.create(
                        candidate=candidate_resume,
                        skill=skill,
                        years_of_experience=experience,
                    )

                # Add Secondary Skills
                for skill, experience in secondary_skills:
                    SecondarySkillSet.objects.create(
                        candidate=candidate_resume,
                        skill=skill,
                        years_of_experience=experience,
                    )

                # Create Job Application
                JobApplication.objects.create(
                    resume=candidate_resume,
                    job_id=job,
                    status='pending',
                    sender=user,
                    receiver=receiver,
                )

                return Response({"message": "Resume added successfully"}, status=status.HTTP_201_CREATED)

        except JobPostings.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class GetResumeByApplicationId(APIView):

    def get(self, request, application_id, *args, **kwargs):
        try:
            job_application = JobApplication.objects.get(id=application_id)

            candidate_resume = job_application.resume

            resume_data = CandidateResumeWithoutContactSerializer(candidate_resume).data

            return Response(resume_data, status=status.HTTP_200_OK)

        except JobApplication.DoesNotExist:
            return Response({"detail": "Job application not found."}, status=status.HTTP_404_NOT_FOUND)

class GetResumeView(APIView):
    def get(self,request):
        try:
            user = request.user
            if (user.role != "client"):
                return Response({"error":"User client is only allowed to do this job"},status=status.HTTP_400_BAD_REQUEST)
            
            if request.GET.get("jobid"):
                id = request.GET.get("jobid")
                applications_all = JobApplication.objects.filter(job_id = id)
                applications_serializer = JobApplicationSerializer(applications_all, many=True)
        
                candidates = []
                for application in applications_all:
                    # if application.status == 'pending':
                        candidates.append(application.resume)

                candidates_serializer = CandidateResumeWithoutContactSerializer(candidates,many=True)
                

                job = JobPostings.objects.get(id = id)
                job_data = {
                    "job_id": id,
                    "job_title" : job.job_title,
                    "job_description": job.job_description,
                    "ctc": job.ctc, 
                }
                return Response({"data":candidates_serializer.data, "job_data": job_data},   status=status.HTTP_200_OK)
            
            else:
                job_postings = JobPostings.objects.filter(username = user )
                job_applications_json = []
                for job_post in job_postings:
                    job_id = job_post.id
                    num_of_postings = job_post.num_of_positions
                    last_date = job_post.job_close_duration
                    total_applications = JobApplication.objects.filter(job_id=job_id).count()
                    processing_count = JobApplication.objects.filter(job_id =job_id,status = 'processing').count()
                    selected_count = JobApplication.objects.filter(job_id=job_id, status="selected").count()
                    pending_count = JobApplication.objects.filter(job_id=job_id, status="pending").count()
                    rejected_count = JobApplication.objects.filter(job_id=job_id, status="rejected").count()

                    # Append data to the response list
                    job_applications_json.append({
                        "job_id": job_id,
                        "num_of_postings": num_of_postings,
                        "last_date": last_date,
                        "applications_sent": total_applications,
                        "processing": processing_count,
                        "selected": selected_count,
                        "pending": pending_count,
                        "rejected": rejected_count,
                    })
                return Response(job_applications_json, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
class RejectApplicationView(APIView):
    def post(self, request):
        try:
            user = request.user
            if not user:
                return Response({"error":"User Does not exists"}, status = status.HTTP_400_BAD_REQUEST)
            
            if user.role != 'client':
                return Response({"error":"User Role not matches"}, status = status.HTTP_400_BAD_REQUEST)
            
            id = request.GET.get('id')          # <--- candidate application id
            if not id:
                return Response({"error":"Application Id is mandatory to reject the application"}, status = status.HTTP_400_BAD_REQUEST)
            
            candidate_resume = CandidateResume.objects.get(id = id)
            job_application = JobApplication.objects.get(resume = candidate_resume)
            job_application.status = "rejected"
            job_application.feedback = request.data.get("feedback")
            job_application.next_interview = None
            job_application.save()

            return Response({"message":"Rejected Successfully"}, status = status.HTTP_200_OK)
        
        except CandidateResume.DoesNotExist:
            return Response({"error":"Candidate Resume not exists with that id"}, status = status.HTTP_400_BAD_REQUEST)
        
        except JobApplication.DoesNotExist:
            return Response({"error": "Job Application does not exists"}, status = status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class NextInterviewerDetails(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            job_id = request.GET.get('id')
            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                job = JobPostings.objects.get(id=job_id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

            if job.username != request.user:
                return Response({"error": "You are not authorized to view this job posting"}, status=status.HTTP_403_FORBIDDEN)

            resume_id = request.GET.get('resume_id')
            if not resume_id:
                return Response({"error": "Resume ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                job_application = JobApplication.objects.get(resume_id=resume_id, job_id=job)
            except JobApplication.DoesNotExist:
                return Response({"error": "Job application not found"}, status=status.HTTP_404_NOT_FOUND)

            next_round = job_application.round_num + 1 if job_application.round_num else 1

            try:
                next_interview_details = InterviewerDetails.objects.get(job_id=job_id, round_num=next_round)
                serializer = InterviewerDetailsSerializer(next_interview_details)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except InterviewerDetails.DoesNotExist:
                return Response({"message": "There are no further rounds"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": "An error occurred while processing your request"},status=status.HTTP_400_BAD_REQUEST)
    
class AcceptApplicationView(APIView):
    def create_user_and_profile(self, candidate_name, candidate_email):

        password = generate_random_password()

        # Serialize and create the user
        user_serializer = CustomUserSerializer(data={
            'email': candidate_email,
            'username': candidate_name,
            'role': CustomUser.CANDIDATE,
            'credit': 0,
            'password': password,
        })

        if user_serializer.is_valid(raise_exception=True):
            new_user = user_serializer.save()
            new_user.set_password(password)
            new_user.save()

            candidate_profile= CandidateProfile.objects.create(
                name = new_user,
                email =candidate_email,
            )
            subject = "Account Created on HireSync"
            message = f"""
Dear {candidate_name},

Welcome to HireSync! Your Candidate account has been successfully created.

Here are your account details:
Username: {candidate_name}
Email: {candidate_email}
Password: {password}

Please log in to your account and change your password for security purposes.

Login Link: https://hiresync.com/login

If you have any questions, feel free to contact our support team.

Regards,
HireSync Team
                """
            send_mail(
                        subject=subject,
                        message=message,
                        from_email='noreply@hiresync.com',
                        recipient_list=[candidate_email],
                        fail_silently=False,
                )
            return candidate_profile
        else:
            raise serializers.ValidationError(user_serializer.errors)
        

    def post(self, request):
        try:
            resume_id = request.GET.get('id')
            round_num = request.data.get('round_num')
            scheduled_date_and_time = request.data.get('date_and_time')
            application = JobApplication.objects.get(resume = resume_id)
            interviewer_details = InterviewerDetails.objects.filter(job_id = application.job_id).get(round_num = round_num)
            
            candidate_details = CandidateResume.objects.get(id=resume_id)

            scheduled_interview = InterviewSchedule.objects.create(
                interviewer = interviewer_details,
                schedule_date = scheduled_date_and_time,
                candidate = candidate_details,
                round_num = round_num,
                status = 'scheduled',
                job_id = application.job_id
            )
            
            application.round_num = round_num
            application.next_interview = scheduled_interview
            application.status = 'processing'
            application.save()

            candidate_name = candidate_details.candidate_name
            candidate_email = candidate_details.candidate_email
            try:
                user = CustomUser.objects.get(email = candidate_email)
                candidate_profile = CandidateProfile.objects.get(name = user)
            except CustomUser.DoesNotExist:
                candidate_profile = self.create_user_and_profile(candidate_name,candidate_email)
            except Exception as e:
                print(str(e), " at creating candidate profile")
                return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message":"Next Interview for this application Scheduled successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class ScheduledInterviewsForJobId(APIView):
    def get(self, request, job_id):
        try:
            interviews = InterviewSchedule.objects.select_related("interviewer", "candidate", "job_id").filter(job_id=job_id)
            serializer = InterviewScheduleSerializer(interviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NextRoundInterviewDetails(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            job_id = request.GET.get('id')
            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                job = JobPostings.objects.get(id=job_id)

            except JobPostings.DoesNotExist:
                return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
           
            resume_id = request.GET.get('resume_id')

            if not resume_id:
                return Response({"error": "Resume ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                job_application = JobApplication.objects.get(resume_id=resume_id, job_id=job)
            except JobApplication.DoesNotExist:
                return Response({"error": "Job application not found"}, status=status.HTTP_404_NOT_FOUND)

            next_round = job_application.round_num + 1 if job_application.round_num else 1

            try:
                next_interview_details = InterviewerDetails.objects.get(job_id=job_id, round_num=next_round)
                serializer = InterviewerDetailsSerializer(next_interview_details)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            except InterviewerDetails.DoesNotExist:
                return Response({"message": "There are no further rounds"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": "An error occurred while processing your request"},status=status.HTTP_400_BAD_REQUEST)
    

class AllInterviewsView(APIView):
    def get(self, request):
        try:
            if request.user.is_authenticated:
                if request.user.role != 'client':
                    return Response({"error":"Sorry, You are not allowed"},status=status.HTTP_400_BAD_REQUEST)                

                # requiredfields-->   job_title, interviewer_name, candidate_name, scheduled_interview, application_status, job_postings_deadline, job_post_status, round_num
                response_json = []
                all_interviews = InterviewSchedule.objects.filter(job_id__in = JobPostings.objects.filter(username = request.user).values_list('id', flat=True))
                for interview in all_interviews:
                    job_post = JobPostings.objects.get(id = interview.job_id)
                    job_title = job_post.job_title
                    interviewer_name = interview.interviewer.name.username
                    candidate_name = interview.candidate.candidate_name
                    scheduled_interview = interview.schedule_date
                    interview_status = interview.status
                    if JobApplication.objects.get(next_interview = interview):
                        candidate_status = JobApplication.objects.get(next_interview = interview).status
                    else:
                        candidate_staus = "cleared"
                    job_post_status = job_post.status
                    job_submission_date = job_post.job_close_duration

                    json_fromat = {
                        "job"
                    }

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

class ScheduledInterviewsView(APIView):
    def get(self, request):
        try:
            if request.GET.get('id'):
                try:
                    interview_id = request.GET.get('id')
                    scheduled_interview = InterviewSchedule.objects.get(id = interview_id)
                    candidate = scheduled_interview.candidate
                    try:
                        interview_details_json = {
                            "job_id" : scheduled_interview.job_id.id,
                            "job_title": scheduled_interview.job_id.job_title,
                            "interviewer_name" : scheduled_interview.interviewer.name.username,
                            "candidate_name" : scheduled_interview.candidate.candidate_name,
                            "candidate_resume_id": JobApplication.objects.get(next_interview = scheduled_interview).resume.id,
                            "round_num" : scheduled_interview.round_num,
                            "scheduled_date": scheduled_interview.schedule_date
                        }
                        return Response(interview_details_json, status = status.HTTP_200_OK)
                    except Exception as e:
                        return Response({"error":str(e)}, status= status.HTTP_400_BAD_REQUEST)

                except InterviewSchedule.DoesNotExist:
                    return Response({"error":"There is no interview scheduled with that id"}, status = status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(str(e))
                    return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
            else:
                if not request.user.is_authenticated:
                    return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
                if not request.user.role == 'interviewer':
                    return Response({"error":"You are not allowed to run this view"},status=status.HTTP_400_BAD_REQUEST)
                try:
                    interviews = InterviewSchedule.objects.filter(interviewer__name = request.user )

                except CustomUser.DoesNotExist:
                    return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

                scheduled_json = []
                for interview in interviews:
                    application_id = JobApplication.objects.get(resume = interview.candidate)
                    id = interview.id
                    schedule_date = interview.schedule_date
                    round_of_interview = interview.round_num
                    interviewer_name = interview.interviewer.name.username
                    job_id = interview.job_id.id
                    job_title = interview.job_id.job_title
                    try:
                        application = JobApplication.objects.get(next_interview = interview)
                        candidate_name = application.resume.candidate_name
                        statuss = application.status
                    except JobApplication.DoesNotExist:
                        candidate_name = interview.candidate.candidate_name
                        statuss = "completed"

                    scheduled_json.append({
                        "interview_id": id,
                        "job_id":job_id,
                        "job_title":job_title,
                        "candidate_name":candidate_name,
                        "interviewer_name":interviewer_name,
                        "round_of_interview":round_of_interview,
                        "schedule_date":schedule_date,
                        "status":statuss,
                        "application_id":application_id.id,
                        
                    })

                return Response(scheduled_json, status =status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)
        
class JobPostSkillsView(APIView):
    def get(self, request):
        try:
            if not request.GET.get('id'):
                return Response({"error":"Job ID is required to fetch the details"}, status=status.HTTP_400_BAD_REQUEST)
            
            job_id = request.GET.get('id')
            job = JobPostings.objects.get(id = job_id)
            skills_json = {
                "primary_skills" : job.primary_skills,
                "secondary_skills" : job.secondary_skills
            }
            return Response(skills_json, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response({"error":"Job Not found"}, status= status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
class PromoteCandidateView(APIView):
    def post(self, request):
        # print(request.data.get("meet_link"))
        try:
            resume_id = request.GET.get('id')
            round_num = request.data.get('round_num')
            meet_link = request.data.get('meet_link')
            scheduled_date_and_time = request.data.get('date_and_time')
            application = JobApplication.objects.get(resume = resume_id)
            interviewer_details = InterviewerDetails.objects.filter(job_id = application.job_id).get(round_num = round_num)

            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)
            candidate_resume = CandidateResume.objects.get(id = resume_id)

            print(scheduled_date_and_time, " is the scheduled date and time")
            candidate_resume = CandidateResume.objects.get(id = resume_id)
            scheduled_interview = InterviewSchedule.objects.create(
                interviewer = interviewer_details,
                candidate = candidate_resume,
                schedule_date = scheduled_date_and_time,
                round_num = round_num,
                status = 'scheduled',
                job_id = application.job_id
            )

            remarks = CandidateEvaluation.objects.create(
                primary_skills_rating = primary_skills,
                secondary_skills_ratings = secondary_skills,
                round_num = round_num-1,
                remarks = remarks,
                status = "SELECTED",
                job_application = application,
                score = score,
                job_id = application.job_id,
                interview_schedule = application.next_interview,
            )
           
          
            application.next_interview.status = 'completed'
            application.next_interview.save()
            application.round_num = round_num
            application.next_interview = scheduled_interview
            application.status = 'processing'
            application.save()
            generated_meet_link=f'here is the meet link for the round 2 :{meet_link}'
            subject=f'congrates you have selected for the round 2 online meet '
            send_mail(
                        subject=subject,
                        message=generated_meet_link,
                        from_email='',
                        recipient_list=[candidate_resume.candidate_email],
                        fail_silently=False,
                    )
            
            subject2=f'you need to screen round 2 candidate with :{meet_link}'
            send_mail(
                        subject=subject2,
                        message=generated_meet_link,
                        from_email='',
                        recipient_list=[interviewer_details.name.email],
                        fail_silently=False,
                    )
            
            return Response({"message":"Next Interview for this application Scheduled successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class ShortlistCandidate(APIView):

    def closeJob(self, id):
        try:
            job = JobPostings.objects.get(id = id)
            job.status = 'closed'
            job.save()
            remaining_applications = JobApplication.objects.exclude(status = 'selected').exclude(status = 'rejected')
            for application in remaining_applications:
                application.status = 'rejected'
                application.save()

                # TODO send_mail()

            return Response({"message":"All positions are filled for this job posting successfully, Job posting is closed"}, status = status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            resume_id = request.GET.get('id')
            round_num = request.data.get('round_num')
            application = JobApplication.objects.get(resume = resume_id)
            print(request.data)
            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)

            remarks = CandidateEvaluation.objects.create(
                primary_skills_rating = primary_skills,
                secondary_skills_ratings = secondary_skills,
                round_num = round_num,
                remarks = remarks,
                status = "SELECTED",
                job_application = application,
                score = score,
                job_id = application.job_id,
                interview_schedule = application.next_interview,
            )
            application.next_interview.status = 'completed'
            application.next_interview.save()
            application.status = 'selected'
            application.save()

            applications_selected  = JobApplication.objects.filter(job_id = application.job_id).filter(status  = 'selected').count()
            job_postings_req = JobPostings.objects.get(id = application.job_id.id).num_of_positions

            if applications_selected >= job_postings_req:
                return self.closeJob(application.job_id.id)

            return Response({"message":"Next Interview for this application Scheduled successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class RejectCandidate(APIView):
    def post(self, request):
        try:
            resume_id = request.GET.get('id')
            round_num = request.data.get('round_num')
            application = JobApplication.objects.get(resume = resume_id)
            print(request.data)
            primary_skills = request.data.get('primary_skills', '')
            secondary_skills = request.data.get('secondary_skills', '')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)

            remarks = CandidateEvaluation.objects.create(
                primary_skills_rating = primary_skills,
                secondary_skills_ratings = secondary_skills,
                round_num = round_num,
                remarks = remarks,
                status = "REJECTED",
                job_application = application,
                score = score,
                job_id = application.job_id,
                interview_schedule = application.next_interview,
            )
            application.next_interview.status = 'completed'
            application.next_interview.save()
            application.status = 'rejected'
            application.save()

            return Response({"message":"Rejected successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)


class InterviewersView(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            client = ClientDetails.objects.get(user = user)
            serializer = ClientDetailsInterviewersSerializer(client)
            return Response(serializer.data["interviewers"], status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def post(self, request):
        try:
            user = request.user
            client = ClientDetails.objects.get(user = user)
            # org = Organization.objects.get(manager=user)

            username = request.data.get('username')
            email = request.data.get('email')

            password = generate_random_password()

            user_serializer = CustomUserSerializer(data={
                'email': email,
                'username': username,
                'role': CustomUser.INTERVIEWER,
                'credit': 0,
                'password': password,
            })

            if user_serializer.is_valid(raise_exception=True):
                new_user = user_serializer.save()
                new_user.set_password(password)
                new_user.save()
                
                client.interviewers.add(new_user)

                subject = "Account Created on HireSync"
                message = f"""
Dear {username},

Welcome to HireSync! Your interviewer account has been successfully created.

Here are your account details:
Username: {username}
Email: {email}
Password: {password}

Please log in to your account and change your password for security purposes.

Login Link: https://hiresync.com/login

If you have any questions, feel free to contact our support team.

Regards,
HireSync Team
                """

                send_mail(
                    subject=subject,
                    message=message,
                    from_email='',
                    recipient_list=[email],
                    fail_silently=False,
                )

                return Response(
                    {"message": "Interviewer account created successfully, and email sent."},
                    status=status.HTTP_201_CREATED
                )

        except ClientDetails.DoesNotExist:
            return Response(
                {"detail": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CandidateProfileView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_profile_serializer = CandidateProfileSerializer(candidate_profile)
                return Response(candidate_profile_serializer.data, status = status.HTTP_200_OK)
            
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def put(self,request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                data = request.data

                skills = data.get('skills')
                
                date_str= data.get('date_of_birth', None)

                formatted_date = date_str
                
                print(formatted_date)

                profile = request.FILES.get('profile', None)
                input_data_json = {
                    "profile": profile,
                    "about" : data.get('about',""),
                    "first_name" : data.get('first_name',""),
                    "middle_name" : data.get('middle_name',''),
                    "last_name" : data.get('last_name',' '),
                    "communication_address" : data.get('communication_address',''),
                    "permanent_address": data.get('permanent_address',''),
                    "phone_num" : data.get('phone_num',''),
                    "date_of_birth": formatted_date,
                    "designation": data.get('designation',''),
                    "linked_in" : data.get('linked_in', None),
                    "instagram": data.get('instagram', None),
                    "facebook":data.get('facebook', None),
                    "blood_group": data.get('blood_group'),
                    "experience_years": data.get('experience_years',""),
                    "skills": skills,
                }
                
                candidate_profile_serializer = CandidateProfileSerializer(instance = candidate_profile, data = input_data_json, partial = True)

                if(candidate_profile_serializer.is_valid()):
                    candidate_profile_serializer.save()
                    return Response({"message":"Candidate Profile updated successfully"}, status = status.HTTP_200_OK)

                else:
                    print(candidate_profile_serializer.errors)
                    return Response({"error":candidate_profile_serializer.errors}, status = status.HTTP_400_BAD_REQUEST)

            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class CandidateExperiencesView(APIView):
       
    parser_classes = (MultiPartParser, FormParser)
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateExperiences.objects.filter(candidate = candidate_profile)

                candidate_certificate_serializer = CandidateExperienceSerializer(candidate_certificates,many=True)
                return Response(candidate_certificate_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
            except CandidateCertificates.DoesNotExist:
                return Response({"message":"Candidate Doesnot Added any certificates"}, status= status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)

                experience = request.data
                if experience: 
                    CandidateExperiences.objects.create(
                        candidate = candidate_profile,
                        company_name= experience.get('company_name'),
                        from_date = experience.get('from_date'),
                        to_date = experience.get('to_date'),
                        status = experience.get('status'),
                        reason_for_resignation = experience.get('reason_for_resignation'),
                        relieving_letter = experience.get('relieving_letter',''),
                        pay_slip1 = experience.get('pay_slip1',''),
                        pay_slip2 = experience.get('pay_slip2',''),
                        pay_slip3 = experience.get('pay_slip3',''),
                    )

                    return Response({"error":"Candidate Experiences added successfully"}, status = status.HTTP_200_OK)
                
                else:
                    return Response({"error":"You haven't added any experiences"}, status = status.HTTP_400_BAD_REQUEST)
                
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            experience = get_object_or_404(CandidateExperiences, id=id)

            if experience.candidate.name.id == request.user.id:
                experience.delete()
                return Response({"message": "Candidate Experience deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
class CandidateCertificatesView(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateCertificates.objects.filter(candidate = candidate_profile)

                candidate_certificate_serializer = CandidateCertificateSerializer(candidate_certificates,many=True)
                return Response(candidate_certificate_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
            except CandidateCertificates.DoesNotExist:
                return Response({"message":"Candidate Doesnot Added any certificates"}, status= status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
    
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            
            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name=user)
            except CandidateProfile.DoesNotExist:
                return Response({"error": "Candidate profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            data = request.data
            if not data.get('certificate_name') or not data.get('certificate_image'):
                return Response({"error": "Both 'certificate_name' and 'certificate_image' are required"}, status=status.HTTP_400_BAD_REQUEST)

            certificate_name = data.get('certificate_name')
            certificate_image = data.get('certificate_image')

            if not hasattr(certificate_image, 'name') or not certificate_image.content_type.startswith('image/'):
                return Response({"error": "Invalid certificate image"}, status=status.HTTP_400_BAD_REQUEST)

            CandidateCertificates.objects.create(
                candidate=candidate_profile,
                certificate_name=certificate_name,
                certificate_image=certificate_image
            )

            return Response({"message": "Candidate certificate added successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            # Log the error for debugging
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            certificate = get_object_or_404(CandidateCertificates, id=id)

            if certificate.candidate.name.id == request.user.id:
                certificate.delete()
                return Response({"message": "Candidate Certificate deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CandidateEducationView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateEducation.objects.filter(candidate = candidate_profile)

                candidate_education_serializer = CandidateEducationSerializer(candidate_certificates,many=True)
                return Response(candidate_education_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
        except CandidateCertificates.DoesNotExist:
            return Response({"message":"Candidate Doesnot Added any education details"}, status= status.HTTP_200_OK)
        
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)



            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                # print(request.body)
                education = request.data
                print(education)
                if education:
                    
                        CandidateEducation.objects.create(
                            candidate = candidate_profile,
                            institution_name = education.get('institution_name'),
                            education_proof = education.get('education_proof'),
                            field_of_study = education.get('field_of_study'),
                            start_date = education.get('start_date'),
                            end_date = education.get('end_date'),
                            degree = education.get('degree')
                        )

                        return Response({"error": "Your education details added successfully"}, status = status.HTTP_200_OK)
                
                else:
                    return Response({"error":"You haven't send any education details"}, status = status.HTTP_400_BAD_REQUEST)
                
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            education = get_object_or_404(CandidateEducation, id=id)

            if education.candidate.name.id == request.user.id:
                education.delete()
                return Response({"message": "Candidate Education deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class CandidateUpcomingInterviews(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to run this"}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            
            candidate_profile = CandidateProfile.objects.get(name=user)

            applications = JobApplication.objects.filter(resume__candidate_name=candidate_profile)

            applications_json = []

            for application in applications:
                if application.next_interview is not None:
                    next_interview = application.next_interview
                    try:
                        application_json = {
                            "round_num": application.round_num,
                            "job_id": {
                                "id": application.job_id.id,
                                "job_title": application.job_id.job_title,
                                "company_name": application.job_id.username.username
                            },
                            "interviewer_name": next_interview.interviewer.name.username,
                            "scheduled_date_and_time": InterviewScheduleSerializer(next_interview).data,
                        }
                        applications_json.append(application_json)  
                    except Exception as e:
                        print(str(e))
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(applications_json, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrevInterviewRemarksView(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not request.user.role == 'interviewer':
                return Response({"error":"You are not allowed to run this view"}, status = status.HTTP_400_BAD_REQUEST)

            resume_id = request.GET.get('id')
            resume = CandidateResume.objects.get(id = resume_id)
            application_id = JobApplication.objects.get(resume = resume).id
            if not application_id:
                return Response({"error":"Application ID is requrired"}, status=status.HTTP_400_BAD_REQUEST)
            
            application_evaluations = CandidateEvaluation.objects.filter(job_application = application_id)
            evaluation_serializer = CandidateEvaluationSerializer(application_evaluations, many=True)
            
            return Response({"data":evaluation_serializer.data},status= status.HTTP_200_OK)
        

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CandidateApplicationsView(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not request.user.role == 'candidate':
                return Response({"error":"You are not allowed to run this view"}, status = status.HTTP_400_BAD_REQUEST)

            user = CustomUser.objects.get(username = request.user)
            candidate_resume = CandidateResume.objects.get(candidate_name = user.username, candidate_email = user.email)
            applications= JobApplication.objects.filter(resume = candidate_resume)
            applications_serialized = JobApplicationSerializer(applications, many=True)
            return Response({"data":applications_serialized.data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class RecruitersList(APIView):

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.role != 'manager':  
                return Response({"error": "You are not allowed to run this view"}, status=status.HTTP_403_FORBIDDEN)

            org = Organization.objects.filter(manager=request.user).first()  
            if not org:
                print("org not found")
                return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

            all_recruiters = RecruiterProfile.objects.filter(organization=org)

            id_list = [
                {"id": recruiter.name.id, "name": recruiter.name.username, "role": "recruiter"}
                for recruiter in all_recruiters
            ]

            id_list.append({"id": request.user.id, "name": request.user.username, "role": "manager"})  

            return Response({"data": id_list}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # Changed status to 500


def returnTemplate(request):
    context = {"name":"Kalki"}
    return render(request, 'organizationTerms.html', context)