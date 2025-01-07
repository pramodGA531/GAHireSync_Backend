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
        if request.GET.get('id'):
            jobpost = JobPostings.objects.get(id=id)
            serializer = JobPostingsSerializer(jobpost)
        else:
            jobpost = JobPostings.objects.filter(username = request.user)
            serializer = JobPostingsSerializer(jobpost,many=True)
        return Response(serializer.data)


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
                job_posting = JobPostings.objects.create(
                    username=username,
                    organization=organization,
                    job_title=data.get('job_title', ''),
                    job_department=data.get('job_department'),
                    job_description=data.get('job_description'),
                    primary_skills=data.get('primary_skills'),
                    secondary_skills=data.get('secondary_skills'),
                    years_of_experience=data.get('years_of_experience'),
                    ctc=data.get('ctc'),
                    rounds_of_interview = len(interview_rounds),
                    job_location=data.get('job_location'),
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
                    status='opened',
                    is_approved=False,
                    is_assigned=None,
                    created_at=None  
                )

                if interview_rounds:
                    for round_data in interview_rounds:
                        InterviewerDetails.objects.create(
                            job_id=job_posting,
                            round_num=round_data.get('round_num'),
                            name=round_data.get('name', ''),
                            email=round_data.get('email', ''),
                            type_of_interview=round_data.get('type_of_interview', 'face_to_face')
                        )

                client = ClientDetails.objects.get(user=username)
                client_message = f"""
    Dear {username.first_name},

    Your job posting for "{job_posting.job_title}" has been successfully created with the following details:

    **Organization:** {organization.name}
    **Job Title:** {job_posting.job_title}
    **Department:** {job_posting.job_department}
    **Job Location:** {job_posting.job_location}
    **CTC:** {job_posting.ctc}
    **Years of Experience Required:** {job_posting.years_of_experience}
    **Primary Skills:** {', '.join(job_posting.primary_skills or [])}
    **Secondary Skills:** {', '.join(job_posting.secondary_skills or [])}

  

    Thank you for using our platform.

    Best regards,
    The Recruitment Team
"""

                manager_message = f"""
Dear {organization.manager.first_name},

A new job posting has been created for your organization "{organization.name}" by {username.first_name} {username.last_name}.

**Job Title:** {job_posting.job_title}
**Department:** {job_posting.job_department}
**Location:** {job_posting.job_location}
**CTC:** {job_posting.ctc}
**Years of Experience:** {job_posting.years_of_experience}

**Accepted Terms:**
- Service Fee: {acceptedterms.get('service_fee')}
- Replacement Clause: {acceptedterms.get('replacement_clause')}
- Invoice After: {acceptedterms.get('invoice_after')} days
- Payment Within: {acceptedterms.get('payment_within')} days
- Interest Percentage: {acceptedterms.get('interest_percentage')}%

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
                {"detail": "Job posting and interview rounds created successfully", "job_id": job_posting.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
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
        job_posting.job_location = data.get('job_location', job_posting.job_location)
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

        job_posting.save()

        return Response({"detail": "Job posting updated successfully", "id": job_posting.id}, status=status.HTTP_200_OK)

class OrganizationTermsView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request):
        user = request.user
        organization = Organization.objects.filter(manager = user).first()
        organization_terms,_ = OrganizationTerms.objects.get_or_create(organization = organization)
        serializer = OrganizationTermsSerializer(organization_terms)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        organization = Organization.objects.filter(manager = user).first()
        organization_terms = get_object_or_404(OrganizationTerms, organization = organization)
        data = request.data
        organization_terms.service_fee = data.get('service_fee', organization_terms.service_fee)
        organization_terms.replacement_clause = data.get('replacement_clause', organization_terms.replacement_clause)
        organization_terms.invoice_after = data.get('invoice_after', organization_terms.invoice_after)
        organization_terms.payment_within = data.get('payment_within', organization_terms.payment_within)
        organization_terms.interest_percentage = data.get('interest_percentage', organization_terms.interest_percentage)
        organization_terms.save()

        return Response({"detail": "Organization terms updated successfully", "id": organization_terms.id}, status=status.HTTP_200_OK)

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
        return Response(serializer.data)

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

A new negotiation request has been submitted by {client.user.first_name} {client.user.last_name} from {client.organization.name}. Here are the details:

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

class JobDetailsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            job_id = request.GET.get('job_id')
            job_posting = JobPostings.objects.get(id=job_id)
            serializer = JobPostingsSerializer(job_posting)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)

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
            summary = summarize_jd(job)
            return Response({'jd':serializer.data,'summary':summary}, status=status.HTTP_200_OK)
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