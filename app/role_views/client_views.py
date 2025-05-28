from ..models import *
from ..permissions import *
from ..serializers import *
from ..authentication_views import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.core.mail import send_mail
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from datetime import date
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from ..utils import *
from django.db.models import Count, Sum
from collections import defaultdict
from django.utils.timesince import timesince




def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

# Dashboard
class ClientDashboard(APIView):
    permission_classes = [IsClient]
    def get(self, request):

        try:
            now  = timezone.now()
            seven_days_ago = now - timedelta(days = 7)

            all_jobs = JobPostings.objects.filter(username = request.user)
            job_posts = all_jobs.order_by("-created_at")[:4]

            all_applications = JobApplication.objects.filter(job_id__in=all_jobs)
            application_counts = all_applications.values('job_id').annotate(total=Count('id'))
            application_counts_dict = {item['job_id']: item['total'] for item in application_counts}

            recent_applications = all_applications.filter(created_at__gte=seven_days_ago).values('job_id').annotate(total=Count('id'))
            recent_applications_dict = {item['job_id']: item['total'] for item in recent_applications}

            jobs_list = []
            for post in job_posts:

                edit_status = ""

                edit_request = JobPostingsEditedVersion.objects.filter(job_id=post.id).first()
                if edit_request:
                    edit_status = edit_request.status

                jobs_list.append({
                    "job_title": post.job_title,
                    "posted": timesince(post.created_at) + " ago",
                    "id": post.id,
                    "location": post.job_locations.split(",")[0].strip() if post.job_locations else "",
                    "applications": application_counts_dict.get(post.id, 0),
                    "applications_last_week": recent_applications_dict.get(post.id, 0),
                    "years_of_experience": post.years_of_experience,
                    "approval_status" : post.approval_status,
                    "edit_request_status": edit_status,
                })

            
            total_vacancies = all_jobs.aggregate(total=Sum('num_of_positions'))['total'] or 0
            resumes_received = all_applications.count()
            on_process = all_applications.filter(status='processing').count()
            no_of_roles = all_jobs.count()
            closed = SelectedCandidates.objects.filter(
                application__in=all_applications, joining_status="joined"
            ).count()

            data_json = {
                "resumes_received": resumes_received,
                "on_process": on_process,
                "no_of_roles": no_of_roles,
                "closed": closed,
                "vacancies": total_vacancies,
            }

            # interviewer name, interviewer email, num_of_jobs_alloted, num_of_round_alloted, rounds_completed, rounds_pending
            interviewers = ClientDetails.objects.get(user=request.user).interviewers.all() 

            interviewer_ids = [interviewer.id for interviewer in interviewers]
            interviewer_usernames = {interviewer.id: interviewer.username for interviewer in interviewers}
            interviewer_emails = {interviewer.id: interviewer.email for interviewer in interviewers}

            jobs = InterviewerDetails.objects.filter(
                name=request.user,
                job_id__in=all_jobs
            ).values('id', 'job_id')

            jobs_alloted_dict = defaultdict(set)
            for job in jobs:
                jobs_alloted_dict[job['interviewer_id']].add(job['job_id'])

            rounds_alloted_dict = defaultdict(int)
            for job in jobs:
                rounds_alloted_dict[job['interviewer_id']] += 1

            # Fetch all interview schedules for these interviewers in bulk
            rounds_status = InterviewSchedule.objects.filter(interviewer__in=interviewer_ids).values('interviewer_id', 'status')

            # Count of pending and completed rounds
            rounds_status_count = defaultdict(lambda: {'pending': 0, 'completed': 0})
            for round_status in rounds_status:
                if round_status['status'] == 'pending':
                    rounds_status_count[round_status['interviewer_id']]['pending'] += 1
                elif round_status['status'] == 'completed':
                    rounds_status_count[round_status['interviewer_id']]['completed'] += 1

            # Now, build the final data
            interviewers_data = []
            for interviewer in interviewers:
                interviewer_id = interviewer.id
                interviewer_json = {
                    "interviewer_name": interviewer_usernames[interviewer_id],
                    "interviewer_email": interviewer_emails[interviewer_id],
                    "rounds_alloted": rounds_alloted_dict[interviewer_id],
                    "jobs_alloted": len(jobs_alloted_dict[interviewer_id]),
                    "pending": rounds_status_count[interviewer_id]['pending'],
                    "completed": rounds_status_count[interviewer_id]['completed'],
                }
                interviewers_data.append(interviewer_json)

            today_interviews_list = []
            today_interviews = InterviewSchedule.objects.filter(job_id__in = all_jobs,scheduled_date = now.date() ).select_related('interviewer__name', 'candidate', 'job_id')
            today_interviews_list = []
            for interview in today_interviews:
                today_interviews_list.append({
                    "interviewer_name": interview.interviewer.name.username,
                    "candidate_name": interview.candidate.candidate_name,
                    "from_time": interview.from_time,
                    "round": interview.round_num,
                    "job_title": interview.job_id.job_title
                })

            return Response({"data":data_json, "interviewers_data":interviewers_data, "today_interviews": today_interviews_list, "job_posts": jobs_list},status = status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": f"Failed to create job post terms: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        

# Job Postings

# Get Terms and Conditions by company code
class GetOrganizationTermsView(APIView):
    permission_classes = [IsClient]  

    def get(self, request):
        try:
            user = request.user
            org_code = request.GET.get("org_code")
            organization = get_object_or_404(Organization, org_code=org_code)
            
            client = get_object_or_404(ClientDetails, user=user)
            
            clientTerms = ClientTermsAcceptance.objects.filter(
                client=client, organization=organization, valid_until__gte=timezone.now()
            )

            negotiation_request = NegotiationRequests.objects.filter(
                client__user=user, organization=organization, status = 'pending'
            )

            if clientTerms.count() > 0:
             organization_terms=clientTerms.first()
            else:
                organization_terms = OrganizationTerms.objects.get(organization = organization)

            terms_serializer = OrganizationTermsSerializer(organization_terms)
            terms_data = terms_serializer.data



            negotiated_data = (
                NegotiationSerializer(negotiation_request.first()).data if negotiation_request.exists() else None
            )

            context = {
                "service_fee": terms_data.get("service_fee"),
                "invoice_after": terms_data.get("invoice_after"),
                "payment_within": terms_data.get("payment_within"),
                "replacement_clause": terms_data.get("replacement_clause"),
                "interest_percentage": terms_data.get("interest_percentage"),
                "data": terms_data,
            }

            context["data_json"] = json.dumps(context["data"])

            html_context = {"service_fee": terms_data.get("service_fee"), 
                "invoice_after": terms_data.get("invoice_after"), 
                "payment_within": terms_data.get("payment_within"), 
                "replacement_clause": terms_data.get("replacement_clause"), 
                "data_json": json.dumps(terms_data)}
            
            
            html = render(request, "organizationTerms.html", html_context).content.decode("utf-8")

            return JsonResponse(
                {"negotiated_data": negotiated_data, "terms_data": context, "html": html},
                safe=False,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print(str(e))  
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        



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
                # valid_until=timezone.now() + timedelta(days=organization_terms.replacement_clause) 
            )
            print(job_post_terms)
        except Exception as e:
            print(str(e))
            return Response({"error": f"Failed to create job post terms: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": "Job post terms added successfully", "terms_id": job_post_terms.id}, status=status.HTTP_201_CREATED)
        
    def generate_unique_jobcode(self, user):
        try:
            job_count = JobPostings.objects.filter(username=user).count()

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            jobcode = f"JOB-{user.username.upper()}-{timestamp}-{job_count + 1:03d}"
            return jobcode

        except Exception as e:
            print(str(e))
            return None

    def post(self, request):
        data = request.data
        username = request.user

        organization = Organization.objects.filter(org_code=data.get('organization_code')).first()
        if not username or username.role != 'client':
            return Response({"error": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST)

        if not organization:
            return Response({"error": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)
        
        generated_job_code = self.generate_unique_jobcode(request.user)

        if not generated_job_code:
                return Response({"error": "Failed to generate job code"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
                    jobcode = generated_job_code,
                    job_title=data.get('job_title', ''),
                    job_department=data.get('job_department'),
                    job_description=data.get('job_description'),
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
                    created_at=None
                )

                primary_skills = data.get('primarySkills')
                secondary_skills = data.get('secondarySkills')

                for skill in primary_skills:
                    skill_metric = SkillMetricsModel.objects.create(
                        job_id = job_posting,
                        is_primary = True,
                        skill_name = skill.get('skill_name'),
                        metric_type = skill.get('skill_metric'),
                        metric_value = skill.get('metric_value'),
                    )
                    
                    if skill.get('skill_metric') == 'custom':
                        skill_metric.metric_type = skill.get('custom_metric')
                        
                    skill_metric.save()

                for skill in secondary_skills:
                    skill_metric = SkillMetricsModel.objects.create(
                        job_id = job_posting,
                        is_primary = False,
                        skill_name = skill.get('skill_name'),
                        metric_type = skill.get('skill_metric'),
                        metric_value = skill.get('metric_value'),
                    )

                    if skill.get('skill_metric') == 'custom':
                        skill_metric.metric_type = skill.get('custom_metric')
                        
                    skill_metric.save()

                if interview_rounds:
                    for round_data in interview_rounds:
                        interviewer = CustomUser.objects.get(email = round_data.get('email'))
                        InterviewerDetails.objects.create(
                            job_id=job_posting,
                            round_num=round_data.get('round_num'),
                            name=interviewer,
                            type_of_interview=round_data.get('type_of_interview', ''),
                            mode_of_interview=round_data.get('mode_of_interview'),
                        )
                new_job_link = f"{frontend_url}/agency/postings/{job_posting.id}"
                manager_message = f"""

Dear {organization.manager.username},

A new job post has been created by {username} for the position {job_posting.job_title}. Please review the details and take the necessary action.
🔗 {new_job_link}

Best,
HireSync Team

"""

                send_custom_mail(
                    subject="New Job Post Created – Action Required",
                    body=manager_message,
                    to_email=[organization.manager.email]
                )

                self.addTermsAndConditions(job_posting)
                
                Notifications.objects.create(
                    sender=request.user,
                    receiver=organization.manager,
                    category = Notifications.CategoryChoices.CREATE_JOB,
                    subject=f"New Job Request by {request.user.username}",
                    message = (
    f"🔔 New Job Request\n\n"
    f"Client: {request.user.username}\n"
    f"Position: {job_posting.job_title}\n\n"
    f"{request.user.username} has sent a new job request to your organization for the position of "
    f"{job_posting.job_title}.\n\n"
    f"id::{job_posting.id}"  # This will be parsed in frontend
    f"link::'agency/postings/'"
)
                )
            
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
    pagination_class = TenResultsPagination
    def get(self,request):
        try:
            if request.GET.get('only_titles'):
                jobs = JobPostings.objects.filter(username = request.user)
                jobs_list = []
                for job in jobs:
                    job_json = {
                        "job_id": job.id,
                        "job_title": job.job_title,
                        "created_at": job.created_at,
                        "job_code": job.jobcode
                    }
                    jobs_list.append(job_json)
                return Response(jobs_list, status=status.HTTP_200_OK)
            if request.GET.get('id'):
                id = request.GET.get('id')
                jobpost = JobPostings.objects.get(id=id)
                serializer = JobPostingsSerializer(jobpost)
                return Response(serializer.data , status=status.HTTP_200_OK)
            else:
                jobposts = JobPostings.objects.filter(username = request.user)
                jobs = []
                for job in jobposts:
                    applications = JobApplication.objects.filter(job_id = job)
                    applications_count = applications.count()
                    closed = SelectedCandidates.objects.filter(application__in = applications, joining_status = 'joined').count()
                    job_details = {
                        "id": job.id,
                        "job_code": job.jobcode,
                        "job_title": job.job_title,
                        "total_candidates": applications_count,
                        "company": job.organization.name,
                        "status": job.status,
                        "reason": job.reason,
                        "positions_closed": f"{closed}/{job.num_of_positions}",
                        "ctc":job.ctc,
                        "job_close_duration": job.job_close_duration,
                        "approval_status": job.approval_status
                    }
                    jobs.append(job_details)

                paginator = self.pagination_class()
                paginated_jobs = paginator.paginate_queryset(jobs, request)

                return paginator.get_paginated_response(paginated_jobs)
        
        except Exception as e:
            print(str(e))
            return Response(status=status.HTTP_400_BAD_REQUEST, errorData = (str(e)))
        

# Edit Requests for the Job

# Edit Requests For Created Job posts

class EditJobsCountView(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            notifications = Notifications.objects.filter(receiver = request.user, seen = False, category = Notifications.CategoryChoices.EDIT_JOB).count()
            return Response({"count":notifications}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response(status=status.HTTP_400_BAD_REQUEST, errorData = (str(e)))
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
                    edited_job = JobPostingsEditedVersion.objects.filter(job_id = job).exclude(user  = user).order_by('-created_at').first()
                    if(edited_job.status != 'pending'):
                        return Response({"error":"You have already reacted to this job post edit"}, status = status.HTTP_400_BAD_REQUEST)
                    
                    edited_data = JobPostEditFields.objects.filter(edit_id = edited_job)
                    edited_data_json = []

                    for field in edited_data:
                        edited_data_json.append({
                            "field_name": field.field_name,
                            "field_value": field.field_value,
                            "status": field.status,
                        })

                    serialized_job = JobPostingsSerializer(job)
                    return Response({"edited_job":edited_data_json,"job":serialized_job.data}, status = status.HTTP_200_OK)
                except JobPostings.DoesNotExist:
                    return Response({"error":"Job posting not found"},status = status.HTTP_400_BAD_REQUEST)
                except JobPostingsEditedVersion.DoesNotExist:
                    return Response({"error":"Job posting edited not found"},status = status.HTTP_400_BAD_REQUEST)
                
                
            else:
                edited_jobs = JobPostingsEditedVersion.objects.filter(job_id__username = user).exclude(user  = user)
                if not edited_jobs:
                    return Response({"details":"There are no Edit Job Requests"}, status = status.HTTP_200_OK)
                jobs_list = []
                for job in edited_jobs:
                    jobs_list.append({
                        "job_title":job.job_id.job_title,
                        "organization_code": job.job_id.organization.org_code,
                        "edited_by": job.user.username,
                        "status": job.status,
                        "organization_name": job.job_id.organization.name,
                        "job_code": job.job_id.jobcode,
                        "id": job.job_id.id,
                    })
                return Response(jobs_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcceptJobEditRequestView(APIView):
    permission_classes = [IsClient]

    def post(self, request):
        try:
            job_id = request.GET.get('job_id')
            user = request.user

            job_post = JobPostings.objects.get(id=job_id)
            edited_fields_version = JobPostingsEditedVersion.objects.filter(job_id=job_post).first()
            if not edited_fields_version:
                return Response({"error": "Edited job post not found"}, status=status.HTTP_404_NOT_FOUND)

            changes = request.data.get('changes', [])
            new_changes = request.data.get('new_changes', [])

            accepted_field_names = [field.get('field_name') for field in changes]

            edited_field_values = JobPostEditFields.objects.filter(edit_id=edited_fields_version)

            with transaction.atomic():
                for field_edit in edited_field_values:
                    if field_edit.field_name in accepted_field_names:

                        new_value = next((item['field_value'] for item in changes if item['field_name'] == field_edit.field_name), None)
                        setattr(job_post, field_edit.field_name, new_value)
                        field_edit.status = 'accepted'
                        field_edit.field_value = new_value
                    else:
                        field_edit.status = 'rejected'
                    field_edit.save()

                job_post.save()

                edited_fields_version.status = 'accepted'
                edited_fields_version.save()

                if len(new_changes) > 0:
                    new_version = JobPostingsEditedVersion.objects.create(
                        job_id=job_post,
                        user=user,
                    )
                    for change in new_changes:
                        field_name = change.get('field_name')
                        field_value = change.get('field_value')
                        if field_name and field_value is not None:
                            JobPostEditFields.objects.create(
                                edit_id=new_version,
                                field_name=field_name,
                                field_value=field_value,
                            )

            manager_email_message = f"""
Dear Manager,

We are pleased to inform you that your requested changes to the job posting have been accepted and processed successfully.

Thank you for your continued support. The job posting has been updated accordingly.

Best regards,  
The Recruitment Team
"""

            manager_mail = job_post.organization.manager.email
            send_custom_mail(
                subject="Accepted Edit Request",
                body=manager_email_message,
                to_email=[manager_mail]
            )
            
            Notifications.objects.create(
                sender=request.user,
                receiver=job_post.organization.manager, 
                category = Notifications.CategoryChoices.ACCEPT_JOB_EDIT,
                subject=f"Client has taken action on your job request for the position: {job_post.job_title}",
                message=(
                    f" Job Post Update\n\n"
                    f"The client has reviewed and taken action on your job request for the position: *{job_post.job_title}*.\n\n"
                    f"please check"
                    f"id::{job_post.id}"  
                    f"link::agency/postings/"
                )
            )
            return Response({"message": "Job edit request accepted successfully"}, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response({"error": "Job post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RejectJobEditRequestView(APIView):
    permission_classes= [IsClient]
    def get(self, request):
        try:

            job_id = request.GET.get('job_id')
            job = JobPostings.objects.get(id=job_id)
            manager_mail = job.organization.manager.email

            edited_job =JobPostingsEditedVersion.objects.filter(id = job).order_by('-created_at').first()
            edited_job_fields = JobPostEditFields.objects.filter(edit_id = edited_job)

            for field in edited_job_fields:
                field.status = 'rejected'
                field.save()

            edited_job.status = 'rejected'
            edited_job.save()
            client_email_message = f"""
            # Dear Manager,

We are sorry to inform you that your requested changes to the job posting have been Rejected 

Thank you for your continued support. The job posting has been Rejected.

Best regards,  
The Recruitment Team
"""

            send_custom_mail(
                subject="Accepted Edit Request",
                body=client_email_message,
                to_email=[manager_mail]
            )
            Notifications.objects.create(
                sender=request.user,
                receiver=job.organization.manager, 
                category = Notifications.CategoryChoices.ACCEPT_JOB_EDIT,
                subject=f"Client has taken action on your job request for the position: {job.job_title}",
                message=(
                    f" Job Post Update\n\n"
                    f"The client has reviewed and taken action on your job request for the position: *{job.job_title}*.\n\n"
                    f"please check"
                    f"id::{job.id}"  
                    f"link::agency/postings/"
                )
            )
            return Response({"message":"Rejected successfully"}, status=status.HTTP_200_OK)
        except JobPostings.DoesNotExist:
            return Response({"error":"Edited Job not found"},status=status.HTTP_400_BAD_REQUEST)
        except JobPostingsEditedVersion.DoesNotExist:
            return Response({"error":"Edited Job not found"},status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)



# Interviewers

# Adding and Vieweing Clients Interviewers
class InterviewersView(APIView):
    permission_classes= [IsClient]
    def get(self, request,*args, **kwargs):
        try:
            if request.GET.get('interviewer_id'):
                interviewer_id = request.GET.get('interviewer_id')
                interviews = InterviewerDetails.objects.filter(name__id=interviewer_id)
                interviews_list = []
                user = CustomUser.objects.get(id = interviewer_id)
                count = 0
                for interview in interviews:
                    try:
                        scheduled_interviews = InterviewSchedule.objects.filter(interviewer=interview)

                        for scheduled in scheduled_interviews:
                            if scheduled.status == 'completed':
                                count += 1

                            interviews_list.append({
                                "interviewer_id": interviewer_id,
                                "candidate_name": scheduled.candidate.candidate_name,
                                "scheduled_date": scheduled.scheduled_date,
                                "interview_status": scheduled.status,
                                "round_num": interview.round_num,
                                "type_of_interview": interview.type_of_interview,
                                "mode_of_interview": interview.mode_of_interview,
                                "job_title": interview.job_id.job_title,
                                "agency_name": interview.job_id.organization.name
                            })

                        return Response({
                            "interviewer_name": user.username,
                            "interviewer_email": user.email,
                            "alloted":interviews.count(),
                            "scheduled": scheduled_interviews.count(),
                            "completed": count,
                            "interviews": interviews_list
                        }, status=200)

                    except CustomUser.DoesNotExist:
                        return Response({"error": "Interviewer not found"}, status=404)

                    except Exception as e:
                        return Response({"error": str(e)}, status=500)

            user = request.user
            client = ClientDetails.objects.get(user = user)
            interviewers = client.interviewers.all()
            interviewers_list = []
            for interviewer in interviewers:
                
                rounds_alloted = InterviewerDetails.objects.filter(name = interviewer)
                rounds_alloted_count = rounds_alloted.count()
                scheduled_interviews = InterviewSchedule.objects.filter(interviewer__in = rounds_alloted )
                scheduled_count = scheduled_interviews.count()
                rounds_completed = scheduled_interviews.filter(status = 'completed').count()
                interviewer_json = {
                    "interviewer_name": interviewer.username,
                    "interviewer_email": interviewer.email,
                    "joining_date": interviewer.date_joined,
                    "rounds_alloted": rounds_alloted_count,
                    "scheduled_interviews": scheduled_count,
                    "rounds_completed": rounds_completed,
                    "id":interviewer.id,
                }

                interviewers_list.append(interviewer_json)
            return Response(interviewers_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
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

                send_email_verification_link(new_user, True, "interviewer", password = password)

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

    def delete(self, request):
        try:
            data = request.data
            print(data, "is the allotted data")

            interviewer_id = request.GET.get('interviewer_id')
            if not interviewer_id:
                return Response({"error": "interviewer_id is required in query params."}, status=status.HTTP_400_BAD_REQUEST)

            interviewer = CustomUser.objects.get(id=interviewer_id)

            if data:
                for job in data:
                    round_num = job.get("round_num")
                    job_id = job.get("job_id")
                    selected_interviewer_id = job.get("selectedInterviewer")

                    if not (round_num and job_id and selected_interviewer_id):
                        continue  

                    interviewer_details = InterviewerDetails.objects.get(round_num=round_num, job_id=job_id)

                    scheduled_interviews = InterviewSchedule.objects.filter(
                        interviewer=interviewer_details,
                        status__in=['scheduled', 'pending']
                    )

                    for interview in scheduled_interviews:
                        applications = JobApplication.objects.filter(next_interview=interview)
                        for application in applications:
                            application.next_interview = None
                            application.save()
                        interview.delete()

                    new_interviewer = CustomUser.objects.get(id=selected_interviewer_id)
                    interviewer_details.name = new_interviewer
                    interviewer_details.save()

            client_details = ClientDetails.objects.get(user=request.user.id)
            client_details.interviewers.remove(interviewer)

            interviewer.delete()

            return Response(
                {"message": "Interviewer removed successfully, and all the interviews allotted to the old interviewer are sent to reschedule"},
                status=status.HTTP_200_OK
            )

        except CustomUser.DoesNotExist:
            return Response({"error": "Interviewer not found."}, status=status.HTTP_404_NOT_FOUND)
        except InterviewerDetails.DoesNotExist:
            return Response({"error": "Interviewer details not found for some jobs."}, status=status.HTTP_404_NOT_FOUND)
        except ClientDetails.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



# Get all the applicaitons
class GetResumeView(APIView):
    pagination_class = TenResultsPagination
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
                job_postings = JobPostings.objects.filter(username=user).exclude(status='closed')
                job_applications_list = []

                for job_post in job_postings:
                    job_id = job_post.id
                    num_of_postings = job_post.num_of_positions
                    last_date = job_post.job_close_duration
                    total_applications = JobApplication.objects.filter(job_id=job_id).count()

                    job_applications_list.append({
                        "job_id": job_id,  # ensure job_id is included for frontend
                        "job_title": job_post.job_title,
                        "num_of_postings": num_of_postings,
                        "last_date": last_date,
                        "applications_sent": total_applications,
                        "organization":job_post.organization.name,
                    })

                paginator = self.pagination_class()
                paginated_data = paginator.paginate_queryset(job_applications_list, request)

                return paginator.get_paginated_response(paginated_data)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
     
# reject applicaiton
class RejectApplicationView(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            if not request.data.get('feedback'):
                return Response({"error":"Feedback is not sent, please give the feedback"}, status= status.HTTP_400_BAD_REQUEST)
            
            
            id = request.GET.get('id')          # <--- candidate application id
            if not id:
                return Response({"error":"Application Id is mandatory to reject the application"}, status = status.HTTP_400_BAD_REQUEST)
            
            candidate_resume = CandidateResume.objects.get(id = id)
            job_application = JobApplication.objects.get(resume = candidate_resume)
            job_application.status = "rejected"
            job_application.feedback = request.data.get('feedback')
            job_application.next_interview = None
            job_application.save()
            clientCompanyDetails=ClientDetails.objects.get(user=request.user)
            Notifications.objects.create(
    sender=request.user,
    receiver=job_application.attached_to, 
    category = Notifications.CategoryChoices.REJECT_CANDIDATE, 
    subject=f"Profile for {job_application.job_id.job_title} Rejected by Client",
    message=(
        f"Update:\n\n"
        f"The candidate profile of {candidate_resume.candidate_name} you submitted for the position of **{job_application.job_id.job_title}** "
        f"has been **rejected** by the client.\n\n"
        f"Client: {clientCompanyDetails.name_of_organization}\n\n"
        f"You may suggest other candidates for this role.\n\n"
        f"feedback by client: {job_application.feedback}"
        f"id::\n"
        f"link::recruiter/postings/" 
    )
)

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

            return candidate_profile, existing_user, None


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
    
            return candidate_profile,new_user, password
        else:
            raise serializers.ValidationError(user_serializer.errors)
        

    def post(self, request):
        try:
            resume_id = request.GET.get('id')
            if not request.data.get('feedback'):
                return Response({"error":"Feedback is not sent, please give the feedback"}, status= status.HTTP_400_BAD_REQUEST)
            
            try:
                resume = CandidateResume.objects.get(id = resume_id)
                job_application = JobApplication.objects.get(resume = resume)
            except JobApplication.DoesNotExist:
                return Response({"error":"There is no application with that id"}, status=status.HTTP_400_BAD_REQUEST)
            
            client = ClientDetails.objects.get(user = request.user)
            company_name = client.name_of_organization

            with transaction.atomic():
                job_application.status = 'processing'
                job_application.round_num = 1
                job_application.feedback = request.data.get('feedback')
                candidate ,customCand, password   = self.create_user_and_profile(candidate_email=resume.candidate_email, candidate_name= resume.candidate_name)
                clientCompanyDetails=ClientDetails.objects.get(user=request.user)
                

                link = f"{frontend_url}/candidate/applications"
                message = f"""

Dear {candidate.name.username},
Great news! You have been shortlisted for the {job_application.job_id.job_title} role at {company_name}.
Next steps: [Interview scheduling details]

Login Credentials:

email: {candidate.name.email}
password : {password}

🔗 {link}
Good luck!

Best,
HireSync Team

"""             
                send_custom_mail("Congratulations! You’ve Been Shortlisted", body = message, to_email = [candidate.name.email])
                job_application.save()
                
                Notifications.objects.create(
    sender=request.user,
    receiver=customCand,
    category = Notifications.CategoryChoices.SHORTLIST_APPLICATION,
    subject=f"Shortlisted for {job_application.job_id.job_title}",
    message=(
        f"✅ Congratulations!\n\n"
        f"You have been **shortlisted** for the position of **{job_application.job_id.job_title}**.\n\n"
        f"Company: {clientCompanyDetails.name_of_organization}\n\n"
        f"Please check your dashboard for more details and next steps.\n\n"
        f"link::candidate/applications/" 
    )
)
                
                Notifications.objects.create(
    sender=request.user,
    receiver=job_application.attached_to,  
    category = Notifications.CategoryChoices.SCHEDULE_INTERVIEW,
    subject=f"Profile for {job_application.job_id.job_title} Accepted by Client",
    message=(
        f"✅ Great News!\n\n"
        f"The candidate profile you submitted for the position of **{job_application.job_id.job_title}** "
        f"has been **accepted** by the client.\n\n"
        f"Client: {clientCompanyDetails.name_of_organization}\n\n"
        f"Schedule interview as per candidate and interviewer availability.\n\n"
        f"id::\n"
        f"link::recruiter/schedule_applications/"  
    )
)

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
            return candidate_profile,new_user
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
            
            applications = JobApplication.objects.filter(job_id = job_application.job_id)
            num_of_postings_completed = SelectedCandidates.objects.filter(application__in = applications,joining_status = 'joined' ).count()
            req_postings = JobPostings.objects.get(id= job_application.job_id.id).num_of_positions

            if(num_of_postings_completed >= req_postings):
                return Response({"error":"All job openings are filled"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                job_application.status = 'hold'
                job_application.round_num = 0
                candidate ,customCand= self.create_user_and_profile(candidate_email=resume.candidate_email, candidate_name= resume.candidate_name)
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
        
class ClientInterviewsView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            rounds_list = []
            interviews_list = []

            if job_id:
                job_ids = [job_id]
            else:
                client = request.user
                job_ids = JobPostings.objects.filter(username=client).values_list('id', flat=True)

            for jid in job_ids:
                interviewer_details = InterviewerDetails.objects.filter(job_id=jid)
                job = JobPostings.objects.get(id=jid)
                serialized_job = JobPostingsSerializer(job).data
                for round in interviewer_details:
                    rounds_list.append({
                        "job_id": serialized_job,
                        "interviewer_name": round.name.username,
                        "interviewer_email": round.name.email,
                        "round_num": round.round_num,
                        "mode_of_interview": round.mode_of_interview,
                        "type_of_interview": round.type_of_interview,
                    })

                scheduled_interviews = InterviewSchedule.objects.filter(job_id=jid)
                for interview in scheduled_interviews:
                    interviews_list.append({
                        "job_id": serialized_job,
                        "interviewer_name": interview.interviewer.name.username,
                        "round_num": interview.round_num,
                        "status": interview.status,
                        "meet_link": interview.meet_link,
                        "candidate_name": interview.candidate.candidate_name,
                        "scheduled_date": interview.scheduled_date,
                        "scheduled_time": f"{interview.from_time} - {interview.to_time}",
                        "mode_of_interview": interview.interviewer.mode_of_interview,
                        "type_of_interview": interview.interviewer.type_of_interview,
                    })

            return Response({
                "scheduled_interviews": interviews_list,
                "interviewers": rounds_list
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CandidatesOnHold(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            if job_id and job_id.isdigit():
                applications_on_hold = JobApplication.objects.filter(job_id = job_id, status = 'hold').select_related('resume')

                application_list = [
                {
                    "candidate_name": application.resume.candidate_name,
                    "candidate_email": application.resume.candidate_email,
                    "application_id": application.id,
                    "expected_ctc": application.resume.expected_ctc,
                    "experience": application.resume.experience,
                }

                for application in applications_on_hold
            ]
                return Response(application_list, status= status.HTTP_200_OK)
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
                    "job_department": candidate.job_id.job_department,
                    "job_status": candidate.job_id.status,
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

            selectedCand = SelectedCandidates.objects.create(
                application = application,
                candidate = candidate,
                ctc = data.get('ctc'),
                joining_date = data.get('joining_date'),
                joining_status = "pending",
                other_benefits = data.get('other_benefits', ''),
            )
            
            application.status = 'selected'
            application.save()
            
            customCand=CustomUser.objects.get(email=candidate.email)
            
            
            Notifications.objects.create(
    sender=request.user,
    receiver=customCand,
    category = Notifications.CategoryChoices.SELECT_CANDIDATE,
    subject=f"You Have Selected for position {application.job_id.job_title}",
    message = (
    f"Dear {customCand.username},\n\n"
    f"Congratulations!\n\n"
    f"We are excited to inform you that you have been selected for the position of {application.job_id.job_title}"
    f"Your joining date is scheduled for{selectedCand.joining_date}, and your agreed CTC is {selectedCand.ctc}.\n\n"
    f"We look forward to having you on board!\n\n"
    f"please accept the offer In the dashboard"
    f"link::candidate/selected_jobs/"
)
)
            Notifications.objects.create(
    sender=request.user,
    receiver=application.attached_to, 
    category = Notifications.CategoryChoices.SELECT_CANDIDATE,
    subject=f"Candidate {customCand.username} Selected for the Position {application.job_id.job_title}",
    message=(
        f"congrates Dear Recruiter"
        f"Candidate Selection Update\n\n"
        f"The candidate {customCand.username} has been selected for the position of {application.job_id.job_title}.\n\n"
        f"Joining Date: {selectedCand.joining_date}\n"
        f"Agreed CTC: {selectedCand.ctc}\n\n"
        f"Please proceed with the onboarding formalities and coordinate further as needed.\n\n"
    )
)
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
    
    def generate_unique_jobcode(self, user):
        try:
            job_count = JobPostings.objects.filter(username=user).count()

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            jobcode = f"JOB-{user.username.upper()}-{timestamp}-{job_count + 1:03d}"
            return jobcode

        except Exception as e:
            print(str(e))
            return None
    

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

            generated_job_code = self.generate_unique_jobcode(request.user)

            if not generated_job_code:

                return Response({"error": "Failed to generate job code"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                        
            with transaction.atomic():
                try:
                    new_job_post = JobPostings.objects.create(
                        ctc=new_ctc_range,  
                        num_of_positions=new_positions,  
                        job_close_duration=new_job_close_duration,  
                        status='opened',  
                        jobcode = generated_job_code,
                        username=job_post.username,
                        organization=job_post.organization,
                        job_title=job_post.job_title,
                        job_department=job_post.job_department,
                        job_description=job_post.job_description,
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

                actual_primary_skills = SkillMetricsModel.objects.filter(job_id = job_id, is_primary = True)
                actual_secondary_skills = SkillMetricsModel.objects.filter(job_id = job_id, is_primary = False)

                for skill in actual_primary_skills:
                    SkillMetricsModel.objects.create(
                        job_id = new_job_post,
                        skill_name= skill.skill_name,
                        metric_type = skill.metric_type,
                        metric_value= skill.metric_value,
                        is_primary = True
                    )

                for skill in actual_secondary_skills:
                    SkillMetricsModel.objects.create(
                        job_id = new_job_post.id,
                        skill_name= skill.skill_name,
                        metric_type = skill.metric_type,
                        metric_value= skill.metric_value,
                        is_primary = False
                    )


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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                        "sender_id": application.attached_to.username,
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
            # if new_status=="joined":
                # here call the invoice function here so, do it 
                # here fetch the selected_application table data and selected
                # pass
                
                
                
                
                
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
        

class SelectedCandidatesView(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            if job_id and job_id.isdigit():
                job_id = int(job_id)
                applications = JobApplication.objects.filter(job_id = request.GET.get('job_id'),status = 'selected').select_related('selected_candidates')
            else:
                applications = JobApplication.objects.filter(job_id__username = request.user,status = 'selected').select_related('selected_candidates')
            candidates_list = []
            for application in applications:
                candidate = getattr(application, "selected_candidates", None)
                if candidate is not None:
                    candidates_list.append({
                        "candidate_name": candidate.candidate.name.username,
                        "application_id": candidate.application.id,
                        "selected_candidate_id": candidate.id,
                        "job_title": candidate.application.job_id.job_title,
                        "joining_status": candidate.joining_status,
                        "joining_date": candidate.joining_date,
                        "job_status": application.job_id.status,
                    })

            return Response(candidates_list, status = status.HTTP_200_OK)
        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
class ShortlistedCandidatesView(APIView):
    permission_classes = [IsClient]
    def get(self,request):
        try:
            job_id = request.GET.get('job_id')
            if job_id and job_id.isdigit():
                job_id = int(job_id)
                applications = JobApplication.objects.filter(job_id = request.GET.get('job_id'),status = 'processing' )
            else:   
                applications = JobApplication.objects.filter(job_id__username = request.user, status = 'processing')
            applications_list = []
            for application in applications:
                applications_list.append(
                    {
                        "application_id": application.id,
                        "job_title":application.job_id.job_title,
                        "candidate_name": application.resume.candidate_name,
                        "current_status": application.round_num,
                        "agency": application.job_id.organization.name,
                        "next_interview": application.next_interview.scheduled_date if application.next_interview else "No Interviews",
                        "job_status": application.job_id.status,
                    }
                )
            return Response(applications_list, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
class AllJoinedCandidates(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            if job_id and job_id.isdigit():
                job_id = int(job_id)
                applications = JobApplication.objects.filter(
                    job_id = request.GET.get('job_id')
                ).select_related("selected_candidates") 
            else:
                applications = JobApplication.objects.filter(
                    job_id__username=request.user
                ).select_related("selected_candidates") 

            candidates_list = []

            for application in applications:
                candidate = getattr(application, "selected_candidates", None)  # Safely get the attribute
                
                if candidate and candidate.joining_status == "joined":
                    job_details_json = {
                        "job_title": application.job_id.job_title,
                        "created_at": application.job_id.created_at,
                        "candidate_name": application.resume.candidate_name,
                        "organization_name":application.job_id.organization.name,
                        "joining_status": candidate.joining_status,
                        "candidate_id": candidate.id,
                        "joined_date": candidate.joining_date,
                        
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
    permission_classes = [ IsClient]
    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            if job_id and job_id.isdigit():
                job_id = int(job_id)
                applications= JobApplication.objects.filter(job_id = request.GET.get('job_id')).select_related("selected_candidates")
            else:
                applications= JobApplication.objects.filter(job_id__username = request.user).select_related("selected_candidates")
            selected_candidates_list = []
            for application in applications:
                selected_candidate  = getattr(application ,"selected_candidates",None)
                if selected_candidate and selected_candidate.joining_status == "left":
                    selected_candidates_list.append(
                        {
                            "candidate_name": application.resume.candidate_name,
                            "job_title": application.job_id.job_title,
                            "joining_date": selected_candidate.joining_date,
                            "left_reason": selected_candidate.left_reason,
                            "is_replacement_eligible": selected_candidate.is_replacement_eligible,
                            "left_date": selected_candidate.resigned_date,
                            "replacement_status": selected_candidate.replacement_status,
                            "id":selected_candidate.id,
                            "job_status": application.job_id.status,
                        }
                    )
            return Response(selected_candidates_list, status = status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            reason = request.data.get('reason')
            candidate_id = request.GET.get('candidate_id')
            candidate = SelectedCandidates.objects.get(id = candidate_id)
            candidate.joining_status = 'left'      
            candidate.resigned_date = date.today()
            candidate.left_reason = reason
            candidate.save()

            if reason == "performance_issues":  
                candidate.is_replacement_eligible = False
            else:
                terms = JobPostTerms.objects.get(job_id=candidate.application.job_id)
                replacement_clause = terms.replacement_clause  # Number of days within which replacement is allowed

                resigned_date = candidate.resigned_date
                candidate_joining_date = candidate.joining_date

                if candidate_joining_date and resigned_date:
                    days_worked = (resigned_date - candidate_joining_date).days  

                    candidate.is_replacement_eligible = days_worked <= replacement_clause

            candidate.save()
            
            
            Notifications.objects.create(
    sender=request.user,
    receiver=candidate.application.attached_to,
    category = Notifications.CategoryChoices.CANDIDATE_LEFT,
    subject=f"Candidate {candidate.candidate.name.username} is left",
    message=(
        f"Application Update\n\n"
        f"Position: {candidate.application.job_id.job_title}\n\n"
        f"The candidate {candidate.candidate.name.username} has left the organization.\n\n"
        f"Reason for leaving: {candidate.left_reason}\n\n"
    )
)           
            Notifications.objects.create(
    sender=request.user,
    receiver=candidate.application.job_id.organization.manager,
    category = Notifications.CategoryChoices.CANDIDATE_LEFT,
    subject=f"Candidate {candidate.candidate.name.username} is left",
    message=(
        f"Application Update\n\n"
        f"Position: {candidate.application.job_id.job_title}\n\n"
        f"The candidate {candidate.candidate.name.username} has left the organization.\n\n"
        f"Reason for leaving: {candidate.left_reason}\n\n"
    )
)        
            
            

            return Response({"message":"Candidate status updated successfully"},status = status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class CandidateJoined(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:

            with transaction.atomic():

                candidate_id = request.GET.get('candidate_id')
                candidate = SelectedCandidates.objects.get(id = candidate_id)
                candidate.joining_status = "joined"
                candidate.save()

                job_openings = candidate.application.job_id.num_of_positions

                print("entered 2")
                job_applications = JobApplication.objects.filter(job_id = candidate.application.job_id)

                print("entered 3")
                jobs_filled = SelectedCandidates.objects.filter(application__in = job_applications, joining_status = 'joined').count()

                if job_openings>jobs_filled:
                    return Response({"message":"Status updated successfully"}, status=status.HTTP_200_OK)
            
                print("etnered 4")
                # send_mass_email here that all the postings are filled here and best of luck for next time

                job_post = candidate.application.job_id
                job_post.status = 'closed'
                job_post.save()

                for application in job_applications:
                    if application.next_interview:
                        application.next_interview.status = "cancelled"
                        application.next_interview.save()

            
                Notifications.objects.create(
    sender=request.user,
    receiver=candidate.application.attached_to,
    category = Notifications.CategoryChoices.CANDIDATE_JOINED,
    subject=f"Candidate {request.user.username} Has Successfully Joined",
    message=(
        f"Joining Confirmation\n\n"
        f"We are pleased to inform you that the candidate {candidate.candidate.name.username} "
        f"has successfully joined for the position of {candidate.application.job_id.job_title}.\n\n"
    )
)
            return Response({"message":"All Job openings are filled, job post is closed successfully"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ReplacementsView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            user = request.user
            replacements = ReplacementCandidates.objects.filter(
                replacement_with__job_id__username=user, status='pending'
            ).select_related(
                'replacement_with__job_id__organization', 
                'replacement_with__resume',
                'replacement_with__selected_candidates'
            )

            replacements_list = [
                {
                    "job_title": replacement.replacement_with.job_id.job_title,
                    "organization_name": replacement.replacement_with.job_id.organization.name,
                    "candidate_name": replacement.replacement_with.resume.candidate_name,
                    "agreed_ctc": getattr(replacement.replacement_with.selected_candidates, 'ctc', None),  # Direct access
                    "job_id": replacement.replacement_with.job_id.id,
                    "joining_date": getattr(replacement.replacement_with.selected_candidates, 'joining_date', None),  # Direct access
                    "replacement_id": replacement.id,
                }
                for replacement in replacements
            ]

            return Response(replacements_list,status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            selected_candidate_id = request.GET.get("candidate_id")
            selected_candidate = SelectedCandidates.objects.select_related("application__job_id").get(id=selected_candidate_id)

            with transaction.atomic():
                selected_candidate.replacement_status = 'pending'
                selected_candidate.save()

                ReplacementCandidates.objects.create(
                    replacement_with=selected_candidate.application
                )

                job_post = selected_candidate.application.job_id
                job_post.status = "opened"
                job_post.save()  

            return Response({"message": "Replacement applied successfully"}, status=status.HTTP_200_OK)

        except SelectedCandidates.DoesNotExist:
            return Response({"error": "Selected candidate not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(str(e))  
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            

class ReplaceCandidate(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            replacement_id = request.GET.get('replacement_id')
            replacement_instance = ReplacementCandidates.objects.get(id = replacement_id)
            data = request.data
            new_application = JobApplication.objects.get(id=data.get('new_application_id'))
            replacement_instance.replaced_by = new_application
            replacement_instance.status = 'completed'
            replacement_instance.save()
            
            # handling old candidate status
            old_candidate = SelectedCandidates.objects.get(application = replacement_instance.replacement_with)
            old_candidate.replacement_status = "completed"
            old_candidate.save()

            # creating instance for new candidate with agreed CTC and joining date
            new_candidate_profile = CandidateProfile.objects.get(email = new_application.resume.candidate_email)
            SelectedCandidates.objects.create(
                application = new_application,
                ctc = data.get('accepted_ctc'),
                joining_date = data.get('joining_date'),
                other_benefits = data.get('other_benefits'),
                joining_status = 'pending',
                candidate = new_candidate_profile
            )

            new_application.status = 'selected'
            new_application.save()

            return Response({"message":"Candidate Replaced Successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))  
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class CompareListView(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            job_id = request.data.get('jobid')
            application_ids = request.data.get('application_ids')

            if not job_id or not application_ids:
                return Response({"error": "Both jobid and application_ids are required."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Fetch the job details
            job = JobPostings.objects.filter(id=job_id).first()
            if not job:
                return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

            interviews = InterviewerDetails.objects.filter(job_id = job)
            job_data = {
                "job_id": job.id,
                "job_title": job.job_title,
                "job_description": job.job_description,
                "ctc": job.ctc,
                "interviews": interviews.count()
            }

            # Query applications based on IDs and job_id
            applications = JobApplication.objects.filter(id__in=application_ids, job_id=job_id)
            application_list = []

            for application in applications:
                resume = application.resume

                primary_skills_qs = CandidateSkillSet.objects.filter(candidate=resume, is_primary=True)
                secondary_skills_qs = CandidateSkillSet.objects.filter(candidate=resume, is_primary=False)

                primary_skills = [
                    {
                        "skill_name": skill.skill_name,
                        "skill_metric": skill.skill_metric,
                        "metric_value": skill.metric_value
                    }
                    for skill in primary_skills_qs
                ]
                secondary_skills = [
                    {
                        "skill_name": skill.skill_name,
                        "skill_metric": skill.skill_metric,
                        "metric_value": skill.metric_value
                    }
                    for skill in secondary_skills_qs
                ]

                application_list.append({
                    "id":application.id,
                    "resume_id": resume.id,
                    "candidate_name": resume.candidate_name,
                    "sender": application.attached_to.username,
                    "other_details": resume.other_details,
                    "notice_period": resume.notice_period,
                    "expected_ctc": resume.expected_ctc,
                    "current_ctc": resume.current_ctc,
                    "job_status": resume.job_status,
                    "current_job_location": resume.current_job_location,
                    "current_job_type": resume.current_job_type,
                    "current_organization": resume.current_organisation,
                    "date_of_birth": resume.date_of_birth,
                    "experience": resume.experience,
                    "resume": resume.resume.url if resume.resume else None,
                    "status": application.status,
                    "primary_skills": primary_skills,  
                    "secondary_skills": secondary_skills,  
                })

            return Response({"data": application_list, "job_data": job_data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


class ViewCompleteResume(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            id = request.GET.get('id')
            if not id:
                return Response({"error":"Id is required"}, status=status.HTTP_200_OK)
            try:
                application = JobApplication.objects.get(id = id)
                interviews = InterviewerDetails.objects.filter(job_id = application.job_id).count()

            except JobApplication.DoesNotExist:
                return Response({"error":"Job application with that id does not exist"}, status=status.HTTP_400_BAD_REQUEST)
            
            resume = application.resume

            primary_skills_qs = CandidateSkillSet.objects.filter(candidate=resume, is_primary=True)
            secondary_skills_qs = CandidateSkillSet.objects.filter(candidate=resume, is_primary=False)

            primary_skills = [
                    {
                        "skill_name": skill.skill_name,
                        "skill_metric": skill.skill_metric,
                        "metric_value": skill.metric_value
                    }
                    for skill in primary_skills_qs
                ]
            secondary_skills = [
                    {
                        "skill_name": skill.skill_name,
                        "skill_metric": skill.skill_metric,
                        "metric_value": skill.metric_value
                    }
                    for skill in secondary_skills_qs
                ]
            
            if(interviews == 0):
                next_interview = False
            else:
                next_interview = True

            application_json = ({
                    "id":application.id,
                    "resume_id": resume.id,
                    "candidate_name": resume.candidate_name,
                    "sender": application.attached_to.username,
                    "other_details": resume.other_details,
                    "notice_period": resume.notice_period,
                    "expected_ctc": resume.expected_ctc,
                    "current_ctc": resume.current_ctc,
                    "job_status": resume.job_status,
                    "current_job_location": resume.current_job_location,
                    "current_job_type": resume.current_job_type,
                    "current_organization": resume.current_organisation,
                    "date_of_birth": resume.date_of_birth,
                    "experience": resume.experience,
                    "resume": resume.resume.url if resume.resume else None,
                    "status": application.status,
                    "primary_skills": primary_skills,  
                    "secondary_skills": secondary_skills,  
                    "next_interview": next_interview,
                })
            
            
            return Response(application_json, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
class ViewCandidateDetails(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            application_id = request.GET.get('application_id')
            application = JobApplication.objects.get(id = application_id)
            try:
                candidate_profile = CandidateProfile.objects.get(email = application.resume.candidate_email)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate with this id doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
            
            candidate_experiences_qs = CandidateExperiences.objects.filter(candidate = candidate_profile.id)
            candidate_education_qs = CandidateEducation.objects.filter(candidate = candidate_profile.id, )

            candidate_evaluation = CandidateEvaluation.objects.filter(candidate = candidate_profile)[:5]
            review_list = []
            for review in candidate_evaluation:
                review_list.append(
                    {
                        "interviewer": review.interview_schedule.interviewer.name.username,
                        "review": review.remarks,
                    }
                )
            candidate_experiences = [
                {
                    "company_name": experience.company_name,
                    "from_time": experience.from_date,
                    "to_time": experience.is_working or experience.to_date,
                    "role": experience.role,
                    "job_type": experience.job_type,
                }
                for experience in candidate_experiences_qs
            ]
            
            candidate_education = [
                {
                    "institution_name": education.institution_name,
                    "field_of_study": education.field_of_study,
                    "start_date": education.start_date,
                    "end_date": education.end_date,
                    "degree": education.degree
                }
                for education in candidate_education_qs
            ]

            candidate_details_json = {
                "name": candidate_profile.name.username,
                "email": candidate_profile.email,
                "address": candidate_profile.permanent_address,
                "phone": candidate_profile.phone_num,
                "experiences": candidate_experiences,  
                "education": candidate_education,  
                "resume": candidate_profile.resume.url if candidate_profile.resume else None,
                "profile": candidate_profile.profile.url if candidate_profile.profile else None,
                "reviews": review_list,
            }

            return Response(candidate_details_json, status = status.HTTP_200_OK)     
               
        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


class DeleteJobPost(APIView):
    permission_classes = [IsClient]
    def delete(self, request):
        try:
            id = request.GET.get('id')
            job_post = JobPostings.objects.get(id = id)  

            if job_post.username != request.user:
                return Response({"error":"You are not authorized to delete this job"}, status = status.HTTP_200_OK)
            
            if job_post.approval_status == 'accepted':
                return Response({"error":"Job is approved by manager, unable to delete this job"}, status = status.HTTP_400_BAD_REQUEST)
            
            job_post.delete()
            return Response({"message":"Job post deleted succesfully"})
        
        except Exception as e:
            print(str(e))  
            return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


class OrgsData(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            user = request.user
            organization_id = request.GET.get('id')

            if organization_id:
                try:
                    
                    organization = Organization.objects.get(id = organization_id)
                    
                    all_postings = JobPostings.objects.filter(organization = organization, username = request.user)
                    total_postings = all_postings.count()
                    completed = JobPostings.objects.filter(organization = organization, status = 'closed', username = request.user).count()

                    jobs_data = []
                    for job in all_postings:
                        job_applications = JobApplication.objects.filter(job_id = job.id)
                        selected = job_applications.filter(status = 'selected').count()
                        processing = job_applications.filter(status = 'processing').count()
                        rejected = job_applications.filter(status = 'rejected').count()
                        hold = job_applications.filter(status = 'hold').count()
                        pending = job_applications.filter(status = 'pending').count()

                        jobs_data.append({
                            "job_title": job.job_title,
                            "jobcode": job.jobcode,
                            "number_of_openings": job.num_of_positions,
                            "candidates_selected": selected,
                            "candidates_processing": processing,
                            "rejected": rejected,
                            "hold": hold,
                            "pending": pending,
                            "status":job.status,
                        })

                    data = {
                        'manager_username': organization.manager.username,
                        'organization_name': organization.name,
                        'contact_number': organization.contact_number,
                        'website_url': organization.website_url,
                        'gst_number': organization.gst_number,
                        'company_address': organization.company_address,
                        "pan": organization.company_pan,
                        'gst': organization.gst_number,
                        'jobs': jobs_data ,
                        "total_postings": total_postings,
                        "completed": completed,
                    }
                    return Response(data, status=200)
                except JobPostings.DoesNotExist:
                    return Response({'error': 'Job not found or not authorized.'}, status=404)
            else:
                jobs = JobPostings.objects.filter(username=user).select_related("organization__manager")
                unique_orgs = {}
                data = []

                for job_item in jobs:
                    org = job_item.organization
                    if org.id not in unique_orgs:
                        unique_orgs[org.id] = org

                for org in unique_orgs.values():
                    data.append({
                        'manager_username': org.manager.username,
                        'organization_name': org.name,
                        'contact_number': org.contact_number,
                        'website_url': org.website_url,
                        'gst_number': org.gst_number,
                        'company_address': org.company_address,
                        'id': org.id,
                    })

                return Response(data, status=200)
    
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
        
# class AllJobPosts(APIView):
#     permission_classes = [IsClient]
#     def get(self, request):
#         try:
#             jobs = JobPostings.objects.filter(username = request.user)
#             jobs_list = []
#             for job in jobs:
#                 if job.status == 'opened':
#                     jobs_list.append({
#                         "job_title": job.job_title,
#                         "job_department": job.job_department,
#                         "posted_date": job.created_at,
#                         "company": job.organization.name,
#                         "deadline": job.job_close_duration,
#                         "approval_status": job.approval_status,
#                         "job_id": job.id,
#                     })
#             return Response(jobs_list, status = status.HTTP_200_OK)
#         except Exception as e:
#             print(str(e))  
#             return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


class ClientAllAlerts(APIView):
    def get(self, request):
        try:
            all_alerts = Notifications.objects.filter(seen=False, receiver=request.user)
            reject_terms = 0
            accept_terms = 0
            accept_job = 0
            edit_job = 0
            reject_job = 0
            onhold_candidate = 0
            send_application = 0
            select_candidate = 0
            accepted_ctc = 0
            candidate_accepted = 0
            candidate_rejected = 0

            for alert in all_alerts:
                if alert.category == Notifications.CategoryChoices.REJECT_TERMS:
                    reject_terms += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPT_TERMS:
                    accept_terms += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPT_JOB:
                    accept_job += 1
                elif alert.category == Notifications.CategoryChoices.EDIT_JOB:
                    edit_job += 1
                elif alert.category == Notifications.CategoryChoices.REJECT_JOB:
                    reject_job += 1
                elif alert.category == Notifications.CategoryChoices.SEND_APPLICATION:
                    send_application += 1
                elif alert.category == Notifications.CategoryChoices.SELECT_CANDIDATE:
                    select_candidate += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPTED_CTC:
                    accepted_ctc += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_ACCEPTED:
                    candidate_accepted += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_REJECTED:
                    candidate_rejected += 1
                elif alert.category == Notifications.CategoryChoices.ONHOLD_CANDIDATE:
                    onhold_candidate +=1

            data = {
                "reject_terms": reject_terms,
                "accept_terms": accept_terms,
                "accept_job": accept_job,
                "edit_job": edit_job,
                "reject_job": reject_job,
                "send_application": send_application,
                "candidate_accepted": candidate_accepted,
                "candidate_rejected": candidate_rejected,
                "onhold_candidate": onhold_candidate,
                "total_alerts": all_alerts.count()
            }

            return Response({"data":data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InterviewerRoundsView(APIView):
    permission_classes = [IsClient]
    def get(self, request):
        try:
            interviewer_id = request.GET.get('interviewer_id')
            if not interviewer_id:
                return Response({"error":"Please send the interviewer id"}, status=status.HTTP_200_OK)
        
            interviews = InterviewerDetails.objects.filter(name__id = interviewer_id).select_related('job_id')

            remaining_interviewers = ClientDetails.objects.get(username = request.user).interviewers.all()
            interviewers_list = []
            for interviewer in remaining_interviewers:
                if interviewer.id != int(interviewer_id):
                    interviewers_list.append({
                        "interviewer_name":interviewer.username,
                        "interviewer_id": interviewer.id,
                    })

            grouped_data = defaultdict(list)
            for interview in interviews:
                interviews_pending = InterviewSchedule.objects.filter(interviewer = interview, status = 'pending').count()
                interview_list = {
                    "round_num":interview.round_num,
                    "interview_type": interview.type_of_interview,
                    "interview_mode": interview.mode_of_interview,
                    "pending_interviews": interviews_pending,
                    "job_id":interview.job_id.id,
                }
                job_id = interview.job_id
                grouped_data[job_id.job_title].append(interview_list)

            return Response({"data": dict(grouped_data), "remaining_interviewers" : interviewers_list}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class RemoveInterviewerView(APIView):
    permission_classes = [IsClient]
    def post(self, request):
        try:
            pass
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
