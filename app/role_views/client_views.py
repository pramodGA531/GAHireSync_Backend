from ..models import *
from ..permissions import *
from ..serializers import *
from ..authentication_views import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.conf import settings 
from django.core.mail import send_mail
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from datetime import date
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from ..utils import *



def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password



# Job Postings

# Get Terms and Conditions by company code
class GetOrganizationTermsView(APIView):
    permission_classes = [IsClient]  

    def get(self, request):
        user = request.user
        org_code = request.GET.get('org_code')
        try:
            organization = Organization.objects.get(org_code = org_code)

        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        
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

# Create Job Post
class JobPostingView(APIView):
    permission_classes = [IsClient]  

    def addTermsAndConditions(self, job_post):
        try:
            organization = Organization.objects.get(org_code=job_post.organization.org_code)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            client = ClientDetails.objects.get(user=job_post.username)
        except ClientDetails.DoesNotExist:
            return Response({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
        
        clientTerms = ClientTermsAcceptance.objects.filter(
            client=client, organization=organization, valid_until__gte=timezone.now()
        )
        
        if clientTerms.exists():
            organization_terms = clientTerms.first()
        else:
            try:
                organization_terms = OrganizationTerms.objects.get(organization=organization)
            except OrganizationTerms.DoesNotExist:
                return Response({"error": "Organization terms not found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        try:
            job_post_terms = JobPostTerms.objects.create(
                job_id=job_post,
                description=organization_terms.description,
                service_fee=organization_terms.service_fee,
                replacement_clause=organization_terms.replacement_clause,
                invoice_after=organization_terms.invoice_after,
                payment_within=organization_terms.payment_within,
                interest_percentage=organization_terms.interest_percentage,
                valid_until=timezone.now() + timedelta(days=organization_terms.replacement_clause)  # Set expiry
            )
        except Exception as e:  # Catch any exception and return an error response
            return Response({"error": f"Failed to create job post terms: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": "Job post terms added successfully", "terms_id": job_post_terms.id}, status=status.HTTP_201_CREATED)
        

    def post(self, request):
        data = request.data
        username = request.user
        organization = Organization.objects.filter(org_code=data.get('organization_code')).first()
        if not username or username.role != 'client':
            return Response({"error": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST)

        if not organization:
            return Response({"error": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                interview_rounds = data.get('interview_rounds', [])
                acceptedterms = data.get('accepted_terms', [])
                job_close_duration_raw = data.get('job_close_duration')
                try:
                    job_close_duration = datetime.strptime(job_close_duration_raw, "%Y-%m-%dT%H:%M:%S.%fZ").date()
                except (ValueError, TypeError):
                    return Response({"error": "Invalid date format for job_close_duration. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

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
                    probation_type =data.get('probation_type',""),
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
                    passport_availability = data.get('passport_availability',''),
                    time_period = data.get('time_period'),
                    notice_period = data.get('notice_period'),
                    notice_time = data.get('notice_time'),
                    qualification_department = data.get('qualification_department'),
                    languages = data.get('languages'),
                    num_of_positions = data.get('num_of_positions'),
                    job_close_duration  = job_close_duration,
                    status='opened',
                    is_approved=False,
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

                self.addTermsAndConditions(job_posting)
                # clientTerms = ClientTermsAcceptance.objects.filter(client=client,organization=organization,valid_until__gte=timezone.now())
                # if clientTerms.count() < 0:
                #     ClientTermsAcceptance.objects.create(client=client,organization=organization,service_fee = acceptedterms.service_fee,replacement_clause = acceptedterms.replacement_clause,invoice_after = acceptedterms.invoice_after,payment_within = acceptedterms.payment_within,interest_percentage = acceptedterms.interest_percentage)
            return Response(
                {"message": "Job and interview rounds created successfully", "job_id": job_posting.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def put(self, request, job_id):
        job_posting = get_object_or_404(JobPostings, id=job_id)

        data = request.data

        if job_posting.username != request.user:
            return Response({"error": "You do not have permission to edit this job posting."}, status=status.HTTP_403_FORBIDDEN)

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

        job_posting.probation_type = data.get('probation_type', job_posting.probation_type)
        job_posting.passport_availability = data.get('passport_availability', job_posting.passport_availability)

        job_posting.time_period = data.get('time_period', job_posting.time_period)
        job_posting.notice_period = data.get('notice_period', job_posting.notice_period)
        job_posting.languages = data.get('languages', job_posting.languages)
        job_posting.notice_time = data.get('notice_time', job_posting.notice_time)
        job_posting.num_of_positions = data.get('num_of_positions', job_posting.num_of_positions)
        job_posting.job_close_duration = data.get('job_close_duration', job_posting.job_close_duration)

        job_posting.save()

        return Response({"message": "Job posting updated successfully", "id": job_posting.id}, status=status.HTTP_200_OK)
    
# View All Job posts by client
class getClientJobposts(APIView):
    def get(self,request):
        try:
            print("entered")
            if request.GET.get('id'):
                id = request.GET.get('id')
                jobpost = JobPostings.objects.get(id=id)
                serializer = ClientJobPostingsSerializer(jobpost)
                return Response(serializer.data , status=status.HTTP_200_OK)
            else:
                jobposts = JobPostings.objects.filter(username = request.user)
                jobs = []
                for job in jobposts:
                    job_details = {
                        "id": job.id,
                        "job_title": job.job_title,
                        "ctc":job.ctc,
                        "status": job.status,
                        "job_close_duration": job.job_close_duration,
                        "approval_status": job.approval_status,
                    }
                    jobs.append(job_details)
            return Response(jobs, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response(status=status.HTTP_400_BAD_REQUEST, errorData = (str(e)))
        

# Edit Requests for the Job

# Edit Requests For Created Job posts
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
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Accept Edit request of the agecy
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
        
# Reject Edit Request of the agency
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



# Interviewers

# Adding and Vieweing Clients Interviewers
class InterviewersView(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            client = ClientDetails.objects.get(user = user)
            serializer = ClientDetailsInterviewersSerializer(client)
            return Response(serializer.data["interviewers"], status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
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
                {"error": "Client not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )



# Handling Candidates Applicaitons

# Get all the applicaitons
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
                    "num_of_rounds": job.rounds_of_interview
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
     
# reject applicaiton
class RejectApplicationView(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            user = request.user
            
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

# accept applicaiton
class AcceptApplicationView(APIView):

    permission_classes = [IsClient]

    def create_user_and_profile(self, candidate_name, candidate_email):

        existing_user = CustomUser.objects.filter(email=candidate_email).first()

        if existing_user:
            candidate_profile = CandidateProfile.objects.get(name=existing_user)

            subject = "You Have Been Shortlisted for Another Job on HireSync"
            message = f"""
Dear {candidate_name},

Congratulations! You have been shortlisted for another job opportunity on HireSync.

Please log in to your account to view more details.

Login Link: https://hiresync.com/login

If you have any questions, feel free to contact our support team.

Best Regards,  
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


        password = generate_random_password()

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
            
            try:
                resume = CandidateResume.objects.get(id = resume_id)
                job_application = JobApplication.objects.get(resume = resume)
            except JobApplication.DoesNotExist:
                return Response({"error":"There is no job with that id"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                job_application.status = 'processing'
                job_application.round_num = 1
                candidate = self.create_user_and_profile(candidate_email=resume.candidate_email, candidate_name= resume.candidate_name)
                job_application.save()

            return Response({"message":"Candidate successfully selected to next round"}, status = status.HTTP_200_OK)
            
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
  

class SelectApplicationView(APIView):
    permission_classes = [IsClient]

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
            
            try:
                resume = CandidateResume.objects.get(id = resume_id)
                job_application = JobApplication.objects.get(resume = resume)
            except JobApplication.DoesNotExist:
                return Response({"error":"There is no job with that id"}, status=status.HTTP_400_BAD_REQUEST)
            
            num_of_postings_completed = JobApplication.objects.filter(job_id = job_application.job_id, status = 'selected', ).count()
            req_postings = JobPostings.objects.get(id= job_application.job_id.id).num_of_positions

            if(num_of_postings_completed >= req_postings):
                return Response({"error":"All job openings are filled"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                job_application.status = 'hold'
                job_application.round_num = 0
                candidate = self.create_user_and_profile(candidate_email=resume.candidate_email, candidate_name= resume.candidate_name)
                job_application.save()

            return Response({"message":"Candidate successfully selected to next round"}, status = status.HTTP_200_OK)
            
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


# Get all the scheduled interviews for the job
class ScheduledInterviewsForJobId(APIView):
    def get(self, request, job_id):
        try:
            interviews = InterviewSchedule.objects.select_related("interviewer", "candidate", "job_id").filter(job_id=job_id)
            serializer = InterviewScheduleSerializer(interviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



# Get all interview details
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
                    scheduled_interview = interview.scheduled_date
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
        

class CandidatesOnHold(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            user = request.user
            job_posts = JobPostings.objects.filter(username = user)
            candidates_on_hold = JobApplication.objects.filter(job_id__in = job_posts, status = 'hold')
            
            candidate_list = []
            for candidate in candidates_on_hold:
                candidate_json = {
                    "candidate_name":candidate.resume.candidate_name,
                    "job_title": candidate.job_id.job_title,
                    "organization_name": candidate.job_id.organization.name,
                    "application_id": candidate.id,
                }
                candidate_list.append(candidate_json)

            return Response(candidate_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        

class HandleSelect(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            id = request.GET.get('id')
            data = request.data
            application = JobApplication.objects.get(id = id)

            job_post = JobPostings.objects.get(id = application.job_id.id)
            selected_applications = SelectedCandidates.objects.filter(application__job_id = job_post.id , joining_status = 'joined').count()
            # selected_applications = JobApplication.objects.filter(job_id = job_post.id, status = 'joined').count()

            if selected_applications >= job_post.num_of_positions:
                return Response({"message":"All Job Postings are filled, If you want to recruit extra members recruit renew your job post"}, status = status.HTTP_200_OK)

            candidate = CandidateProfile.objects.get(email = application.resume.candidate_email)

            SelectedCandidates.objects.create(
                application = application,
                candidate = candidate,
                ctc = data.get('ctc'),
                joining_date = data.get('joining_date'),
                joining_status = "pending",
                other_benefits = data.get('other_benefits', ''),
            )
            
            application.status = 'selected'
            application.save()

            # send email and sms notifications here

            return Response({"message":"Candidate is Selected"},status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
class ClosedJobsClient(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            closed_jobs = JobPostings.objects.filter(username = request.user, )
            closed_jobs_list = []
            for job in closed_jobs:
                closed_job_json = {
                    "job_title": job.job_title,
                    "job_department": job.job_department,
                    "organization": job.organization.name,
                    "job_id": job.id,
                }
                closed_jobs_list.append(closed_job_json)
            return Response(closed_jobs_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            user = request.user
            job_post = JobPostings.objects.get(id = request.GET.get('job_id'))
            if user != job_post.username:
                return Response({"error":"usernames are not matching"}, status= status.HTTP_400_BAD_REQUEST)
            
            job_post.status = 'closed'
            job_post.save()
            
            JobApplication.objects.filter(job_id=job_post.id, status__in=['processing', 'pending']).update(status='rejected')
                
            return Response({"message":"Job post closed successfully"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

class ReopenJob(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            user = request.user
            job_id = request.GET.get('id')

            if not job_id:
                return Response({"error":"JobId is not sent"}, status=status.HTTP_400_BAD_REQUEST)

            job_post = JobPostings.objects.get(id=job_id)

            if user != job_post.username:
                return Response({"error": "Usernames are not matching"}, status=status.HTTP_400_BAD_REQUEST)

            interviewers = InterviewerDetails.objects.filter(job_id=job_post)
            interviewers_list = [
                {   
                    "round_num":interviewer.round_num,
                    "interviewer_name": interviewer.name.username,
                    "mode_of_interview": interviewer.mode_of_interview,
                    "type_of_interview": interviewer.type_of_interview,
                }
                for interviewer in interviewers
            ]

            client_details = ClientDetails.objects.get(user=user)
            company_interviewers = [
                {"interviewer_name": interviewer.username, "id": interviewer.id}
                for interviewer in client_details.interviewers.all()
            ]

            response_json = {
                "job_title": job_post.job_title,
                "job_description": job_post.job_description,
                "job_department": job_post.job_department,
                # "primary_skills": job_post.primary_skills,
                # "secondary_skills": job_post.secondary_skills,
                "ctc": job_post.ctc,
                "rounds_of_interview": job_post.rounds_of_interview,
                "job_id": job_post.id,
                "interviewer_details": interviewers_list,
                "company_interviewers": company_interviewers,  # Include all eligible interviewers
            }

            return Response(response_json, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response({"error": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)

        except ClientDetails.DoesNotExist:
            return Response({"error": "Client details not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            user = request.user
            job_id = request.GET.get('job_id')

            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                job_post = JobPostings.objects.get(id=job_id)
            except JobPostings.DoesNotExist:
                return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)

            if user != job_post.username:
                return Response({"error": "Usernames do not match"}, status=status.HTTP_403_FORBIDDEN)

            new_positions = request.data.get('num_of_positions', job_post.num_of_positions)
            new_ctc_range = request.data.get('ctc', job_post.ctc)
            new_job_close_duration = request.data.get('job_close_duration', job_post.job_close_duration)
            
            with transaction.atomic():
                try:
                    new_job_post = JobPostings.objects.create(
                        ctc=new_ctc_range,  
                        num_of_positions=new_positions,  
                        job_close_duration=new_job_close_duration,  
                        status='opened',  

                        username=job_post.username,
                        organization=job_post.organization,
                        job_title=job_post.job_title,
                        job_department=job_post.job_department,
                        job_description=job_post.job_description,
                        primary_skills=job_post.primary_skills,
                        secondary_skills=job_post.secondary_skills,
                        years_of_experience=job_post.years_of_experience,
                        rounds_of_interview=job_post.rounds_of_interview,
                        job_locations=job_post.job_locations,
                        job_type=job_post.job_type,
                        probation_type=job_post.probation_type,
                        job_level=job_post.job_level,
                        qualifications=job_post.qualifications,
                        timings=job_post.timings,
                        other_benefits=job_post.other_benefits,
                        working_days_per_week=job_post.working_days_per_week,
                        decision_maker=job_post.decision_maker,
                        decision_maker_email=job_post.decision_maker_email,
                        bond=job_post.bond,
                        rotational_shift=job_post.rotational_shift,
                        is_approved=False,
                        age=job_post.age,
                        gender=job_post.gender,
                        visa_status=job_post.visa_status,
                        passport_availability=job_post.passport_availability,
                        time_period=job_post.time_period,
                        qualification_department=job_post.qualification_department,
                        notice_period=job_post.notice_period,
                        notice_time=job_post.notice_time,
                        industry=job_post.industry,
                        differently_abled=job_post.differently_abled,
                        languages=job_post.languages,
                        approval_status='pending'
                    )
                except IntegrityError:
                    return Response({"error": "Database integrity error while creating job post"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except ValidationError as e:
                    return Response({"error": f"Invalid job post data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

                interviewer_details = request.data.get('interviewer_details', [])

                if not isinstance(interviewer_details, list):
                    return Response({"error": "Invalid format for interviewer details"}, status=status.HTTP_400_BAD_REQUEST)

                for interviewe in interviewer_details:
                    try:
                        interviewer = CustomUser.objects.get(id=interviewe.get("interviewer_id"))
                    except CustomUser.DoesNotExist:
                        return Response({"error": f"Interviewer with ID {interviewe.get('interviewer_id')} not found"}, status=status.HTTP_404_NOT_FOUND)

                    try:
                        InterviewerDetails.objects.create(
                            job_id=new_job_post,
                            name=interviewer,
                            round_num=interviewe.get("round_num"),
                            type_of_interview=interviewe.get("type_of_interview"),
                            mode_of_interview=interviewe.get("mode_of_interview"),
                        )
                    except ValidationError as e:
                        return Response({"error": f"Invalid interviewer data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Job Post Renewed successfully", "new_job_id": new_job_post.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(str(e))
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TodayJoingings(APIView):
    def get(self, request):
        try:
            client_user = request.user  

            today=date.today() 

            today_joinings = SelectedCandidates.objects.filter(
                joining_date__gte=today, 
                joining_date__lt=today + timedelta(days=1),
                application__job_id__username=client_user 
            ).select_related('application__job_id') 


            # Prepare response data
            response_data = []
            for selected in today_joinings:
                application = selected.application
                job_posting = application.job_id  

                response_data.append({
                    "selected_candidate": {
                        "id": selected.id,
                        "application_id": application.id,
                        "ctc": selected.ctc,
                        "joining_date": selected.joining_date,
                        "joining_status": selected.joining_status
                    },
                    "application": {
                        "id": application.id,
                        # "resume_id": application.resume.id,
                        "job_id": application.job_id.id,
                        "status": application.status,
                        "sender_id": application.sender.username,
                        "receiver_id": application.receiver.username,
                        "feedback": application.feedback
                    },
                    "job_posting": {
                        "id": job_posting.id,
                        "job_title": job_posting.job_title,
                        "job_description": job_posting.job_description,
                        "organization_id": job_posting.organization.id,
                        "job_locations": job_posting.job_locations,
                        "job_type": job_posting.job_type
                    }
                })

            return Response({"data": response_data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class UpdateJoiningStatus(APIView):
    permission_classes  = [IsClient]
    def post(self, request):
        try:
            data = request.data
            new_status = data.get('status')
            application_id = request.GET.get('application_id')
            
            if new_status not in dict(SelectedCandidates.JOINING_STATUS_CHOICES):
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
            selected_application = SelectedCandidates.objects.get(application__id = application_id)

            selected_application.status = new_status
            selected_application.save()
            
            return Response({'message': 'Application status updated successfully', 'status': selected_application.status}, status=status.HTTP_200_OK)
        except JobApplication.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON format'}, status=status.HTTP_400_BAD_REQUEST)        

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

class AllSelectedCandidates(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            applications = JobApplication.objects.filter(job_id__username=request.user).prefetch_related("selected_candidates")

            candidates_list = []
            for application in applications:

                candidates = application.selected_candidates.all()

                job_candidates = [
                    {
                        "candidate_name": candidate.candidate.name.username,
                        "joining_status": candidate.joining_status,
                        "candidate_id": candidate.id,
                    }
                    for candidate in candidates
                ]

                job_details_json = {
                    "job_title": application.job_id.job_title,
                    "created_at": application.job_id.created_at,
                    "candidates": job_candidates,
                }
                candidates_list.append(job_details_json)

            return Response(candidates_list, status=status.HTTP_200_OK)

        except JobApplication.DoesNotExist:
            return Response({"error": "No job applications found"}, status=status.HTTP_404_NOT_FOUND)

        except SelectedCandidates.DoesNotExist:
            return Response({"error": "No selected candidates found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
# class AllJoinedCandidates(APIView):
#     permission_classes = [IsClient]
#     def get(self, request):
#         try:
#             applications = JobApplication.objects.filter(
#                 job_id__username=request.user
#             ).select_related("selected_candidates")  # Use select_related for OneToOneField

#             candidates_list = []

#             for application in applications:
#                 candidate = application.selected_candidates  # Directly get the related object

#                 if candidate and candidate.joining_status == 'joined':
#                     job_details_json = {
#                         "job_title": application.job_id.job_title,
#                         "created_at": application.job_id.created_at,
#                         "candidates": [
#                             {
#                                 "candidate_name": candidate.candidate.name.username,
#                                 "joining_status": candidate.joining_status,
#                                 "candidate_id": candidate.id,
#                             }
#                         ],
#                     }
#                     candidates_list.append(job_details_json)

#             return Response(candidates_list, status=status.HTTP_200_OK)

#         except JobApplication.DoesNotExist:
#             return Response({"error": "No job applications found"}, status=status.HTTP_404_NOT_FOUND)

#         except Exception as e:
#             return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class AllJoinedCandidates(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            applications = JobApplication.objects.filter(
                job_id__username=request.user
            ).select_related("selected_candidates")  # Use select_related for OneToOneField

            candidates_list = []

            for application in applications:
                candidate = getattr(application, "selected_candidates", None)  # Safely get the attribute
                
                if candidate :
                    job_details_json = {
                        "job_title": application.job_id.job_title,
                        "created_at": application.job_id.created_at,
                        "candidates": [
                            {
                                "candidate_name": candidate.candidate.name.username,
                                "joining_status": candidate.joining_status,
                                "candidate_id": candidate.id,
                                "is_replacement_eligible": candidate.is_replacement_eligible,
                            }
                        ],
                    }
                    candidates_list.append(job_details_json)

            if not candidates_list:
                return Response({"message": "No joined candidates found"}, status=status.HTTP_404_NOT_FOUND)

            return Response(candidates_list, status=status.HTTP_200_OK)

        except JobApplication.DoesNotExist:
            return Response({"error": "No job applications found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class CandidateLeftView(APIView):
    def post(self, request):
        try:
            print('entered here')
            reason = request.data.get('reason')
            candidate_id = request.GET.get('candidate_id')
            candidate = SelectedCandidates.objects.get(id = candidate_id)
            candidate.joining_status = 'left'
            candidate.resigned_date = date.today()
            if reason == "performance_issues":
                candidate.is_replacement_eligible = False
            else:
                candidate.is_replacement_eligible = True
            candidate.left_reason = request.data.get('reason')
            candidate.save()
            application = candidate.application
            application.status = 'left'
            application.save()
            print(candidate.joining_status)
            return Response({"message":"Candidate status updated successfully"},status = status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ApplyReplacementView(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            candidate_id = request.GET.get('candidate_id')
            candidate = SelectedCandidates.objects.get(id = candidate_id)
            job_post = candidate.application.job_id
            try:
                job_post_terms = JobPostTerms.objects.get(job_id= job_post)
            except JobPostTerms.DoesNotExist:
                return Response({"error":"Terms for this job post doesnot exist"}, status= status.HTTP_200_OK)
            
            replacement_clause = job_post_terms.replacement_clause
            joining_date = candidate.joining_date
            today = datetime.today().date()

            if isinstance(joining_date, str):
                joining_date = datetime.strptime(joining_date, "%Y-%m-%d").date()

            if joining_date-today < replacement_clause:
                return Response({"error":"Date is expired to replace"},status=status.HTTP_400_BAD_REQUEST)

            job_post.status= 'opened'
            job_post.save()
            return Response({"message":"Replacement request sent to organization successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)