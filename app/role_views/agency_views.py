from ..models import *
from ..permissions import *
from ..serializers import *
from ..authentication_views import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.core.mail import send_mail
from ..utils import *
from django.db.models import Prefetch
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.timezone import now,is_aware, make_naive
from rest_framework.response import Response
from rest_framework.views import APIView


class AgencyJobApplications(APIView):
    permission_classes = [IsManager]
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            job_postings = JobPostings.objects.filter(organization=org)
            applications = JobApplication.objects.filter(job_id__in=job_postings).select_related('resume', 'job_id')

            job_titles = [
                {"job_id": job.id, "job_title": job.job_title}
                for job in job_postings.distinct()
            ]

            applications_list = [
                {
                    "candidate_name": app.resume.candidate_name,
                    "application_id": app.id,
                    "job_id":app.id,
                    "job_title": app.job_id.job_title,
                    "job_department": app.job_id.job_department,
                    "job_description": app.job_id.job_description,
                    "job_title": app.job_id.job_title,
                    "job_department": app.job_id.job_department,
                    "job_description": app.job_id.job_description,
                    "application_status": app.status,   
                    "feedback": app.feedback,
                }
                for app in applications
            ]

            return Response(
                {"applications_list": applications_list, "job_titles": job_titles},
                status=status.HTTP_200_OK
            )

        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def delete(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            application_ids = request.data.get("application_ids", [])

            
            apps_to_delete = JobApplication.objects.filter(
                id__in=application_ids,
            )

            deleted_count = apps_to_delete.count()
            apps_to_delete.delete()

            return Response({"detail": f"Deleted {deleted_count} applications."}, status=200)

        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
    


class AgencyDashboardAPI(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            user = request.user
            agency_name = Organization.objects.get(manager = user).name

            approval_pending = JobPostings.objects.filter(organization__name = agency_name, approval_status='pending').count()
            interviews_scheduled = JobApplication.objects.filter(job_id__organization__name=agency_name).exclude(next_interview=None).count()
            recruiter_allocation_pending = JobPostings.objects.filter(organization__name=agency_name, assigned_to=None).count()
            jobpost_edit_requests = JobPostingsEditedVersion.objects.filter(job_id__organization__manager=user).count()  
            opened_jobs = JobPostings.objects.filter(organization__name=agency_name, status='opened').count()
            closed_jobs = JobPostings.objects.filter(organization__name=agency_name, status='closed').count()
            upcoming_interviews = []
            applications = JobApplication.objects.filter(job_id__organization__name=agency_name).exclude(next_interview=None).order_by('-next_interview__scheduled_date')[:20]

            for application in applications:
                application_details = {
                    "interviewer_name" : application.next_interview.interviewer.name.username,
                    "round_num" : application.round_num,
                    "candidate_name": application.resume.candidate_name,
                    "scheduled_time": application.next_interview.scheduled_date,
                    "from_time": application.next_interview.from_time,
                    "to_time": application.next_interview.to_time,
                    "job_title": application.job_id.job_title,
                }

                upcoming_interviews.append(application_details)

            latest_jobs = JobPostings.objects.filter(organization__name = agency_name).order_by('-created_at')[:10]
            
            jobs_details = []
            for job in latest_jobs:

                selected = JobApplication.objects.filter(job_id = job, status = 'selected').count()
                rejected = JobApplication.objects.filter(job_id = job.id, status = "rejected").count()
                applications = JobApplication.objects.filter(job_id = job.id).count()
                number_of_rounds =  InterviewerDetails.objects.filter(job_id = job.id).count()
                rejected_at_last_round = JobApplication.objects.filter(job_id = job.id, round_num = number_of_rounds, status = 'rejected').count()
                interviewed = selected + rejected_at_last_round

                job_details = {
                    "role":job.job_title,
                    "positions_left": job.num_of_positions - selected,
                    "applications": applications,
                    "interviewed":interviewed,
                    "rejected": rejected,
                    "feedback_pending": 0,
                    "offered": selected,
                }

                jobs_details.append(job_details)

            data = {
                "approval_pending": approval_pending,
                "interviews_scheduled": interviews_scheduled,
                "recruiter_allocation_pending": recruiter_allocation_pending,
                "jobpost_edit_requests": jobpost_edit_requests,
                "opened_jobs": opened_jobs,
                "closed_jobs":closed_jobs,
            }

            return Response({"data":data, "latest_jobs":jobs_details, "upcoming_interviews":upcoming_interviews }, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
# Job Postings

# Get all job postings of the particular organization
class OrgJobPostings(APIView):
    def get(self, request,*args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            job_postings = JobPostings.objects.filter(organization=org)

            job_postings_json = []
            try:
                for job in job_postings:    
                    applied = JobApplication.objects.filter(job_id = job).count()
                    under_review = JobApplication.objects.filter(job_id = job, status='pending').count()
                    selected = JobApplication.objects.filter(job_id = job, status='selected').count()
                    rejected = JobApplication.objects.filter(job_id = job, status='rejected').count()
                    number_of_rounds = InterviewerDetails.objects.filter(job_id = job).count()
                    job_json = {
                        "job_id": job.id,
                        # "recruiter_name": job.assigned_to.username if job.assigned_to else "Not-Assigned",
                        "client_name": job.username.username,
                        "job_status": job.status,
                        "job_title": job.job_title,
                        "deadline": job.job_close_duration,
                        "vacancies": job.num_of_positions,
                        "applied": "applied",
                    }
            except Exception as e:
                return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

            serializer = JobPostingsSerializer(job_postings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
# View particular job post
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
        
# View the edit request of manager(your role)
class JobEditStatusAPIView(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            job_id = request.GET.get('id')
            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            job = JobPostings.objects.get(id=job_id)

            if job.approval_status == 'accepted':
                return Response({"status": 'accepted'}, status=status.HTTP_200_OK)

            if job.approval_status == 'reject':
                return Response({"status": 'rejected'}, status=status.HTTP_200_OK)

            # 4. Get latest job edit version
            job_edit_version = JobPostingsEditedVersion.objects.filter(job_id=job_id).order_by("-created_at").first()

            if not job_edit_version:
                return Response({'notFound': "Job edit post not found"}, status=status.HTTP_404_NOT_FOUND)

            # 5. Fetch edited fields
            job_edit_fields = JobPostEditFields.objects.filter(edit_id=job_edit_version)

            # 6. If any field is rejected, return all fields
            if any(field.status == 'rejected' for field in job_edit_fields):
                rejected_fields_json = [{
                    "field_name": field.field_name,
                    "field_value": field.field_value,
                    "status": field.status
                } for field in job_edit_fields]

                return Response({
                    "status": "field_rejected",
                    "fields_rejected": rejected_fields_json
                }, status=status.HTTP_200_OK)

            # 7. If edit is accepted or user is owner, continue with field diff view
            if job_edit_version.user == request.user or job_edit_version.status == 'accepted':
                return Response({"status": job_edit_version.status}, status=status.HTTP_200_OK)

            # 8. Build old and new fields comparison
            old_fields_json = []    
            if job_edit_version.base_version:
                old_edit_fields = JobPostEditFields.objects.filter(edit_id=job_edit_version.base_version)
                old_fields_json = [{
                    "field_name": field.field_name,
                    "field_value": field.field_value,
                    "status": field.status,
                } for field in old_edit_fields]

            new_fields_json = [{
                "field_name": field.field_name,
                "field_value": field.field_value
            } for field in job_edit_fields]

            # 9. Return diff
            return Response({
                "status": job_edit_version.status,
                "old_fields": old_fields_json,
                "new_fields": new_fields_json
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class OrgJobEdits(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            user = request.user
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
        try:
            data = request.data
            user = request.user
            job_id = request.GET.get('id')

            changes = data.get('changes', [])
            primary_skills = data.get('primarySkills', [])
            secondary_skills = data.get('secondarySkills', [])

            with transaction.atomic():
                job = JobPostings.objects.get(id=job_id)

                edit_version = JobPostingsEditedVersion.objects.create(
                    job_id=job,
                    user=user,
                )

                for field_name, field_value in changes.items():
                    original_value = getattr(job, field_name, None)

                    if field_value != original_value:
                        JobPostEditFields.objects.create(
                            edit_id=edit_version,
                            field_name=field_name,
                            field_value=field_value,
                        )

                actual_primary_skills = SkillMetricsModel.objects.filter(job_id = job, is_primary = True)
                actual_secondary_skills = SkillMetricsModel.objects.filter(job_id = job, is_primary = False)
                
                for skill in primary_skills:
                    skill_name = skill.get('skill_name')
                    metric_type = skill.get('metric_type')
                    metric_value = skill.get('metric_value')

                    try:
                        actual_skill = actual_primary_skills.get(skill_name=skill_name)

                        existing_value = getattr(actual_skill, metric_type, None)

                        if existing_value != metric_value:
                            skill_metric = SkillMetricsModelEdited.objects.create(
                                job_id=edit_version,
                                is_primary=True,
                                skill_name=skill_name,
                                metric_type=metric_type,
                            )
                            setattr(skill_metric, metric_type, metric_value)
                            skill_metric.save()

                    except actual_primary_skills.model.DoesNotExist:
                        skill_metric = SkillMetricsModelEdited.objects.create(
                            job_id=edit_version,
                            is_primary=True,
                            skill_name=skill_name,
                            metric_type=metric_type,
                        )
                        setattr(skill_metric, metric_type, metric_value)
                        skill_metric.save()
                                
                for skill in secondary_skills:
                    skill_name = skill.get('skill_name')
                    metric_type = skill.get('metric_type')
                    metric_value = skill.get('metric_value')

                    try:
                        actual_index = actual_secondary_skills.get(skill_name=skill_name)

                        if actual_index.metric_type != metric_type or actual_index.metric_value != metric_value:
                            skill_metric = SkillMetricsModelEdited.objects.create(
                                job_id=edit_version,
                                is_primary=False,
                                skill_name=skill_name,
                                metric_type=metric_type,
                                metric_value=metric_value,
                            )
                            
                    except actual_secondary_skills.DoesNotExist:
                        skill_metric = SkillMetricsModelEdited.objects.create(
                            job_id=edit_version,
                            is_primary=False,
                            skill_name=skill_name,
                            metric_type=metric_type,
                            metric_value=metric_value,
                        )
    
                        skill_metric.save()
                Notifications.objects.create(
                                    sender=request.user,
                                    category = Notifications.CategoryChoices.EDIT_JOB,
                                    receiver=job.username,
                                    subject=f"Job Edit Request",
                                    message = (
                    f"✏ Job Edit Request\n\n"
                    f"The organization has requested an edit for the following job post.\n\n"
                    f"Position: *{job.job_title}*\n"
                    f"Client: {job.username}\n\n"
                    f"Please review the requested changes and update the job post accordingly.\n\n"
                    f"link::client/approvals/"
                )
                                )
                # Email logic...

                return Response(
                    {"message": "Job post edit request sent successfully"},
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            print("error is ", str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class AcceptJobPostView(APIView):
    permission_classes = [IsManager]
    def put(self, request):
        try:
            job_id = int(request.GET.get('id'))

            if not job_id:
                return Response({"error": "Job post id is required"}, status=status.HTTP_400_BAD_REQUEST) 
            
            action = request.GET.get('action')

            try:
                job_post = JobPostings.objects.get(id = job_id)
                if(action == 'accept'):
                    job_post.approval_status  = "accepted"
                
                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category = Notifications.CategoryChoices.ACCEPT_JOB,
                        subject=f"Job Post Accepted by {request.user.username}",
                        message=(
                            f"✅ Job Request Accepted\n\n"
                            f"Your job request for the position of **{job_post.job_title}** has been accepted by "
                            f"{request.user.username}.\n\n"
                            f"The organization has started reviewing and shortlisting suitable profiles for this role. "
                            f"You will be notified once candidates are shortlisted or selected.\n\n"
                            f"Thank you for using our platform! 🙌"
                        )
                    )


                elif(action == 'reject'):
                    job_post.approval_status  = "rejected"
                    reason = request.data.get('reason')

                    job_post.reason = reason
                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category = Notifications.CategoryChoices.REJECT_JOB,
                        subject=f"Job Post Rejected by {request.user.username}",
                        message=(
                            f"Job Request Rejected\n\n"
                            f"Your job request for the position of **{job_post.job_title}** has been reviewed by "
                            f"{request.user.username} and was not accepted.\n\n"
                            f"This could be due to internal requirements or job role mismatch.\n\n"
                            f"You may consider submitting a new job request with updated details if needed.\n\n"
                            f"Thank you for understanding."
                        )
                    )

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

class JobEditActionView(APIView):
    permission_classes = [IsManager]
    def post(self, request):
        try:
            job_id = request.GET.get('id')
            job = JobPostings.objects.get(id=job_id)
            action = request.GET.get('action')
            if action == 'accept':
                job_edit_request = JobPostingsEditedVersion.objects.filter(job_id=job).order_by('-created_at').first()
                if job_edit_request.user.role == 'client':

                    job_edit_fields = JobPostEditFields.objects.filter(edit_id= job_edit_request)

                    with transaction.atomic():
                        for field in job_edit_fields:
                            setattr(job,field.field_name, field.field_value)
                            field.status = 'accepted'
                            field.save()
                        job_edit_request.status = "accepted"
                        job_edit_request.save()
                job.approval_status = 'accepted'
                job.save()
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category = Notifications.CategoryChoices.ACCEPT_JOB,
                    subject=f"Job {job.job_title} request has been approved by {request.user}",
                    message=(
                        f"Dear {job.username},\n\n"
                        f"Your request for the job '{job.job_title}' has been approved by {request.user}.\n"
                        "We will now proceed to find the perfect profiles for this job.\n\n"
                        "Best regards,\n"
                        f"{request.user}"
                    )
                )
                return Response({"message":"Job approved successfully"}, status=status.HTTP_200_OK)
            
            if action == 'reject':
                job.approval_status = 'reject'
                job.save()
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category = Notifications.CategoryChoices.REJECT_JOB,
                    subject=f"Job {job.job_title} request has been rejected by {request.user}",
                    message=(
                        f"Dear {job.username},\n\n"
                        f"Your request for the job '{job.job_title}' has been rejected by {request.user}.\n"

                        "Best regards,\n"
                        f"{request.user}"
                    )
                )
                return Response({"message":"Job post rejected successfully"}, status=status.HTTP_200_OK)            

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Get all the recruiters and Add the recruiter
class RecruitersView(APIView):

    permission_classes = [IsManager]

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

                send_email_verification_link(new_user, True, "recruiter", password = password)

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

# Assign job post to the recruiter
class AssignRecruiterView(APIView):
    def post(self, request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            if org:
                job_id = request.data.get('job_id')
                job = JobPostings.objects.get(id=job_id, organization=org)

                recruiter_ids = request.data.get('recruiter_ids', [])  
                recruiters = CustomUser.objects.filter(id__in=recruiter_ids)

                job.assigned_to.set(recruiters)  # Assign multiple recruiters
                job.save()

                for recruiter in recruiters:
                    
                    link = f"{frontend_url}/recruiter/postings/{job_id}"
                    message = f"""

A new job post {job.job_title} has been assigned to you. Please review the details and start the recruitment process.
🔗 {link}

Best,
HireSync Team
"""
                    send_custom_mail(f"New Job Assigned – {job.job_title}", message, {recruiter.email})
                    
                    notification = Notifications.objects.create(
                    sender=request.user,
                    receiver=recruiter,
                    category = Notifications.CategoryChoices.ASSIGN_JOB,
                    subject=f"New Job Assigned by Manager",
                    message=(
        f"📢 New Job Assignment\n\n"
        f"You have been assigned a new job post to source profiles for.\n\n"
        f"Position: **{job.job_title}**\n"
        f"Client: {job.username}\n\n"
        f"Please begin reviewing profiles and shortlisting suitable candidates for this role.\n\n"
        f"id::{job.id}"  
        f"link::'recruiter/postings/"
    )
                )
                    notification.category = Notifications.CategoryChoices.ASSIGN_JOB
                    notification.save()

                return Response({"detail": "Recruiters Assigned Successfully"}, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"detail": "One or more recruiters not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruitersList(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, sxxtatus=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  

# Invoices
# Get all invoice
class InvoicesAPIView(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            organization = Organization.objects.get(manager = request.user)
            jobs= JobPostings.objects.filter(organization = organization).filter(status = 'closed')
            
            if not jobs.exists():
                return Response({"noJobs": True}, status=status.HTTP_200_OK)
            
            invoices = []

            for job in jobs:
                print("job",job)
                total = 100
                context = {
                    "agency_name": job.organization.name,
                    "client_name": job.username.username,
                    "client_email": job.username.email,
                    "job_title": job.job_title,
                    "ctc": job.ctc,
                    "service_fee":23.13,
                    "payment_within": 32,
                    "invoice_id": 10212,
                    "invoice_after": 12,
                    "replacement_clause" : 23,
                    "date":45,
                    "total":total,
                    "email":job.username.email
                }

                invoice = generate_invoice(context)

                invoices.append({"invoice":invoice, "job_title":job.job_title, "job_id":job.id})

            return Response({"invoices":invoices}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)


# Close Job 
class CloseJobView(APIView):
    permission_classes = [IsManager]
    def post(self, request):
        try:
            job_id = request.GET.get('id')

            if not job_id:
                return Response({"error":"job_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                job = JobPostings.objects.get(id = job_id)
            except JobPostings.DoesNotExist:
                return Response({"error":"Job Post does not exists"},status=status.HTTP_400_BAD_REQUEST)

            job.status = 'closed'
            job_applications = JobApplication.objects.filter(job_id = job).exclude(status='selected').exclude(status='rejected')

            for job_application in job_applications:
                job_application.status = 'rejected'
                job_application.save()

            job.save()

            # generate invoice here for single job post
            return Response({"message":"Job  Post Closed Successfully"},status=status.HTTP_200_OK )

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AgencyJobPosts(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            all_jobs = JobPostings.objects.filter(organization__manager=user).select_related('username').prefetch_related('assigned_to')

            total_postings = 0
            num_of_open_jobs = 0
            pending_approval = 0
            expired_jobs = 0
            closed_positions = 0


            jobs_list = []
            for job in all_jobs:
                applied = JobApplication.objects.filter(job_id=job.id).count()
                under_review = JobApplication.objects.filter(job_id=job.id, status='processing').count()
                hired = JobApplication.objects.filter(job_id=job.id, status='selected').count()
                rejected = JobApplication.objects.filter(job_id=job.id, status='rejected').count()
                
                num_of_rounds = job.rounds_of_interview
                rounds_details = []

                rounds_details.extend([
                                     {"Vacancies": job.num_of_positions},
                                     {"Applied": applied},
                                     {"Under Review": under_review},
                                    ])

                for round_num in range(1, num_of_rounds + 1):
                    count = JobApplication.objects.filter(
                        job_id=job.id,
                        round_num=round_num,
                        status='processing'
                    ).count()
                    
                    rounds_details.append({f"Interview Round {round_num}": count})
                
                rounds_details.extend([
                                     {"Hired":hired},
                                     {"Rejected" : rejected}
                                    ])

                job_details = {
                    "job_title": job.job_title,
                    "recruiter_name": list(job.assigned_to.values_list('username', flat=True)) if job.assigned_to.exists() else ["Not Assigned"],
                    "client_name": job.username.username if job.username else "Unknown",
                    "deadline": job.job_close_duration,
                    "status": job.status,
                    "approval_status": job.approval_status,
                    "id": job.id,
                    "rounds_details": rounds_details,
                }

                jobs_list.append(job_details)
                total_postings += job.num_of_positions

                if job.approval_status == 'pending':
                    pending_approval+=1

                if job.status == 'opened':
                    num_of_open_jobs += 1
                
                if job.job_close_duration < timezone.now().date():
                    expired_jobs+=1

                applications_closed = JobApplication.objects.filter(job_id = job.id, status = 'selected').count()
                closed_positions += applications_closed
            

            org_jobs = {
                "new_positions": total_postings,
                "open_job_posts": num_of_open_jobs,
                "active_job_posts": num_of_open_jobs,
                "pending_approval": pending_approval,
                "closed_positions": closed_positions,
                "expired_posts": expired_jobs,
            }

            return Response({"data": jobs_list, "org_jobs": org_jobs}, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({"error": "No job postings found for the manager."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AllRecruitersView(APIView):
    permission_classes  = [IsManager]

    def get(self, request):
        try:
            user = request.user
            organization = Organization.objects.get(manager = user)
            recruiters = organization.recruiters.all()

            recruiters_list = []
            for recruiter in recruiters:
                recruiter_json = {
                    "name": recruiter.username,
                    "email": recruiter.email,
                    "phone" : "",
                    "profile":"",
                    "id": recruiter.id,
                }
                recruiters_list.append(recruiter_json)
            return Response({"data":recruiters_list}, status= status.HTTP_200_OK)
        
        except Organization.DoesNotExist:
            return Response({"error":"Organization with that id doesnot exists"}, status = status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        


class RecruiterTaskTrackingView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            job_data = []

            job_postings = JobPostings.objects.filter(organization__manager=user)
            current_time = now().date()

            for job in job_postings:
                
                job_close_duration = job.job_close_duration

                if current_time > job_close_duration - timedelta(days=5):
                    priority = "high"
                elif current_time > job_close_duration - timedelta(days=10):
                    priority = "medium"
                else:
                    priority = "low"

                jobs_closed = JobApplication.objects.filter(job_id=job.id, status='selected').count()
                status_percentage = (jobs_closed / job.num_of_positions * 100) if job.num_of_positions > 0 else 0

                job_json = {
                    "job_title": job.job_title,
                    "num_of_positions": job.num_of_positions,
                    "priority": priority,
                    "due_date": job.job_close_duration,
                    "status": round(status_percentage, 2),  
                    "recruiters": list(job.assigned_to.values_list('username', flat=True)),
                }
                job_data.append(job_json)

            try:
                organization = Organization.objects.get(manager=user)
            except Organization.DoesNotExist:
                return Response({"error": "No organization found for this manager"}, status=status.HTTP_404_NOT_FOUND)

            all_recruiters = organization.recruiters.all()
            recruiters_list = [{"name": recruiter.username} for recruiter in all_recruiters]

            recent_activities = []
            resumes = JobApplication.objects.filter(attached_to__in=all_recruiters).order_by('-updated_at')[:6]
            for resume in resumes:
                task = ""
                if resume.status == 'pending':
                    task = f"{resume.resume.candidate_name}'s Resume is sent to {resume.job_id.job_title}"
                elif resume.status == 'processing' and resume.next_interview:
                    task = f"New meeting scheduled for {resume.resume.candidate_name}"
                

                time_diff = now() - resume.updated_at

                if time_diff.seconds < 60:
                    thumbnail = f"Updated {time_diff.seconds} seconds ago"
                elif time_diff.seconds < 3600:
                    thumbnail = f"Updated {time_diff.seconds // 60} minutes ago"
                elif time_diff.seconds < 86400:
                    thumbnail = f"Updated {time_diff.seconds // 3600} hours ago"
                else:
                    thumbnail = f"Updated {time_diff.days} days ago"                                        


                recent_activities.append({
                    "name": resume.attached_to.username,
                    "job_title": resume.job_id.job_title,
                    "task": task,
                    "thumbnail": thumbnail
                })

            five_days_ago = datetime.now() - timedelta(days=5)
            new_jobs = JobPostings.objects.filter(organization__manager=user, created_at__gte=five_days_ago).count()
            on_going = JobPostings.objects.filter(organization__manager=user, assigned_to__isnull=False).count()

            completed_posts = 0
            completed_deadline = 0
            completed_jobs = JobPostings.objects.filter(organization__manager=user, status='closed')

            for job in completed_jobs:
                positions_closed = JobApplication.objects.filter(job_id=job.id, status='selected').count()
                if positions_closed >= job.num_of_positions:
                    completed_posts += 1
                else:
                    completed_deadline += 1

            main_components = {
                "new": new_jobs,
                "on_going": on_going,
                "completed_posts": completed_posts,
                "completed_deadline": completed_deadline
            }

            return Response({
                "job_data": job_data,
                "recruiters_list": recruiters_list,
                "recent_activities": recent_activities,
                "main_components": main_components
            }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
class ViewSelectedCandidates(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            selected_candidates_list = []
            applications = JobApplication.objects.filter(job_id__organization__manager = user, status = 'selected')
            selected_candidates = SelectedCandidates.objects.filter(application__in = applications)
            for candidate in selected_candidates:
                job = candidate.application.job_id
                candidate_json = {
                    "candidate_name" : candidate.candidate.name.username,
                    "joining_date": candidate.joining_date,
                    "joining_status": candidate.joining_status,
                    "accepted_ctc":candidate.ctc,
                    "candidate_acceptance":candidate.candidate_acceptance,
                    "candidate_joining_status":candidate.joining_status,
                    "actual_ctc":job.ctc,
                    "client_name": job.username.username,
                    "job_title": job.job_title,
                }
                selected_candidates_list.append(candidate_json)
            
            return Response(selected_candidates_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class AccountantsView(APIView):
    permission_classes = [IsManager]  

    def get(self, request):
        try:
            organization = Organization.objects.get(manager=request.user)
            accountants = Accountants.objects.filter(organization=organization)
            if not accountants.exists():
                return Response({"message": "No accountants found for this organization"}, status=status.HTTP_404_NOT_FOUND)
            serializer = AccountantsSerializer(accountants, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response({"error": "Manager does not belong to any organization"}, status=status.HTTP_404_NOT_FOUND)
        
    def post(self, request):
        email = request.data.get("email")
        username = request.data.get("username")

        if not email or not username:
            return Response({"error": "Email and Username are required"}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            print("request.user",request.user)
            organization=Organization.objects.get(manager=request.user)
        except Organization.DoesNotExist:
            return Response({"error": "Manager does not belong to an organization"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=None, 
                role='accountant' 
            )
            
            accountant = Accountants.objects.create(
                user=user,
                email=email,
                username=username,
                organization=organization  
            )

            return Response({"success": f"Accountant {username} created successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Failed to create accountant. {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationView(APIView):
    permission_classes = [IsManager]
    def get(self,request):
        try:
            user = request.user
            organization = Organization.objects.get(manager=user)
            serializer = OrganizationSerializer(organization)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
class ManagerAllAlerts(APIView):
    def get(self, request):
        try:
            all_alerts = Notifications.objects.filter(seen=False, receiver=request.user)
            negotiate_terms = 0
            create_job = 0
            accept_job_edit = 0
            reject_job_edit = 0
            partial_edit = 0
            candidate_joined = 0
            candidate_left = 0

            for alert in all_alerts:
                if alert.category == Notifications.CategoryChoices.NEGOTIATE_TERMS:
                    negotiate_terms += 1
                elif alert.category == Notifications.CategoryChoices.CREATE_JOB:
                    create_job += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPT_JOB_EDIT:
                    accept_job_edit += 1
                elif alert.category == Notifications.CategoryChoices.REJECT_JOB_EDIT:
                    reject_job_edit += 1
                elif alert.category == Notifications.CategoryChoices.PARTIAL_EDIT:
                    partial_edit += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_JOINED:
                    candidate_joined += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_LEFT:
                    candidate_left += 1

            data = {
                "negotiate_terms": negotiate_terms,
                "create_job": create_job,
                "accept_job_edit": accept_job_edit,
                "reject_job_edit": reject_job_edit,
                "partial_edit": partial_edit,
                "total_alerts": all_alerts.count()
            }

            return Response({"data":data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
        
class ClientsData(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            job_id = request.GET.get('id')

            if job_id:
                try:
                    job = JobPostings.objects.get(id=job_id, organization__manager=user)

                    jobs = JobPostings.objects.filter(username=job.username, organization__manager=user)

                    client = ClientDetails.objects.filter(user=job.username).first()

                    if not client:
                        return Response({'error': 'Client not found for this job.'}, status=404)

                    jobs_data = JobPostingsSerializer(jobs, many=True).data

                    data = {
                        'client_username': client.username,
                        'organization_name': client.name_of_organization,
                        'contact_number': client.contact_number,
                        'website_url': client.website_url,
                        'gst_number': client.gst_number,
                        'company_address': client.company_address,
                        'jobs': jobs_data,
                        
                    }

                    return Response(data, status=200)

                except JobPostings.DoesNotExist:
                    return Response({'error': 'Job not found or not authorized.'}, status=404)
            else:
                jobs = JobPostings.objects.filter(organization__manager=user)
                data = []
                added_clients = set()  
                for job_item in jobs:
                    client = ClientDetails.objects.filter(user=job_item.username).first()
                    if client and client.username not in added_clients:
                        data.append({
                            'job_code': job_item.jobcode,
                            'job_title': job_item.job_title,
                            'job_id': job_item.id,
                            'client_username': client.username,
                            'organization_name': client.name_of_organization,
                            'contact_number': client.contact_number,
                            'website_url': client.website_url,
                            'gst_number': client.gst_number,
                            'company_address': client.company_address,
                        })
                        added_clients.add(client.username)  

                return Response(data, status=200)


        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruiterJobsView(APIView):
    permission_classes = [IsManager]
    
    def get(self, request):
        try:
            recruiter_id = request.GET.get('rec_id')
            recruiter = CustomUser.objects.get(id = recruiter_id)
            recruiter_jobs = JobPostings.objects.filter(assigned_to = recruiter)
            job_details_json = []


            if not recruiter_jobs.exists():
                return Response({"data":None,"recruiters": None }, status=status.HTTP_200_OK)

            organization = Organization.objects.filter(id = recruiter_jobs[0].organization.id)

            recruiters_list = CustomUser.objects.filter(
                recruiting_organization__in=organization
            ).exclude(id=recruiter.id).distinct()

            recruiters_json = []
            for recruiter in recruiters_list:
                recruiters_json.append({
                    "recruiter_name": recruiter.username,
                    "id": recruiter.id
                })

            for job in recruiter_jobs:

                assigned_recruiters = job.assigned_to.all()
                assigned_list = []
                for member in assigned_recruiters:
                    assigned_list.append({
                        "recruiter_name":member.username,
                        "id": member.id
                    })

                job_details_json.append({
                    "job_title": job.job_title,
                    "job_id": job.id,
                    "resumes_sent": JobApplication.objects.filter(job_id = job.id, sender = recruiter).count(),
                    "assigned_list": assigned_list,
                })
            
            return Response({"data":job_details_json, "recruiters":recruiters_json}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveRecruiter(APIView):
    permission_classes = [IsManager]
    def post(self, request):
        try:
            rec_id = request.GET.get('rec_id')
            if not rec_id:
                return Response({"error": "Recruiter ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            recruiter_to_remove = get_object_or_404(CustomUser, id=rec_id)
            reassignment_data = request.data

            with transaction.atomic():
            
                for entry in reassignment_data:
                    job_id = entry.get("job_id")
                    new_rec_id = entry.get("selected_recruiter_id")

                    if not job_id or not new_rec_id:
                        continue  

                    job = get_object_or_404(JobPostings, id=job_id)
                    new_recruiter = get_object_or_404(CustomUser, id=new_rec_id)
                    job.assigned_to.remove(recruiter_to_remove)

                    if new_recruiter not in job.assigned_to.all():
                        job.assigned_to.add(new_recruiter)

                    applications = JobApplication.objects.filter(job_id = job.id, attached_to = recruiter_to_remove)
                    for application in applications:
                        application.attached_to = new_recruiter
                        application.save()

                    # write email functionality here
                    receiver = new_recruiter.email
                    subject = f"Job post reassigned to you "
                    message = '''
THis is the new job post reassigned to you
'''                 
                    send_custom_mail(subject = subject, body=message, to_email=[receiver])

                recruiter_to_remove.delete()  

            return Response({"message": "Recruiter removed and jobs reassigned successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print("Error in RemoveRecruiter:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        