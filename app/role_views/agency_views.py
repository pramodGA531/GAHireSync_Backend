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
from ..utils import *
from django.db.models import Prefetch
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.timezone import now,is_aware, make_naive
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum  
from decimal import Decimal, InvalidOperation



class AgencyJobApplications(APIView):
    permission_classes = [IsManager]
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            job_postings = JobPostings.objects.filter(organization=org)
            job_locations = JobLocationsModel.objects.filter(job_id__organization = org)
            job_locations_ids = job_locations.values('id')
            applications = JobApplication.objects.filter(job_location__in=job_locations_ids).select_related('resume', 'job_location')
            print("entered ", applications)

            job_titles = [
                {"job_id": job.id, "job_title": job.job_title}
                for job in job_postings.distinct()
            ]

            applications_list = []
            for app in applications:
                job = app.job_location.job_id
                applications_list.append({
                "candidate_name": app.resume.candidate_name,
                    "application_id": app.id,
                    "job_id":app.id,
                    "job_title": job.job_title,
                    "job_department": job.job_department,
                    "job_description": job.job_description,
                    "job_title": job.job_title,
                    "job_department": job.job_department,
                    "job_description": job.job_description,
                    "application_status": app.status,   
                    "feedback": app.feedback,
                })
            
            return Response(
                {"applications_list": applications_list, "job_titles": job_titles},
                status=status.HTTP_200_OK
            )

        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
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
            all_applications = JobApplication.objects.filter(job_location__job_id__organization__name = agency_name)
            all_jobs = JobPostings.objects.filter(organization__name = agency_name) 
            pending_assigned = 0
            for job in all_jobs:
                locations = JobLocationsModel.objects.filter(job_id = job).count()                
                assigned_locations = AssignedJobs.objects.filter(job_id=job).values_list('job_location', flat=True).distinct()
                assigned_jobs = len(set(assigned_locations))

                if(locations > assigned_jobs):
                    pending_assigned += 1
                

            approval_pending = all_jobs.filter(approval_status='pending').count()
            interviews_scheduled = all_applications.exclude(next_interview=None).count()
            recruiter_allocation_pending = pending_assigned
            jobpost_edit_requests = JobPostingsEditedVersion.objects.filter(job_id__organization__manager=user).count()  
            opened_jobs = all_jobs.filter(status='opened').count()
            closed_jobs = all_jobs.filter(status='closed').count()
            applications = all_applications.exclude(next_interview=None).order_by('-next_interview__scheduled_date')[:20]
            upcoming_interviews = []

            for application in applications:
                upcoming_interviews.append({
                    "interviewer_name" : application.next_interview.interviewer.name.username,
                    "round_num" : application.round_num,
                    "candidate_name": application.resume.candidate_name,
                    "scheduled_time": application.next_interview.scheduled_date,
                    "from_time": application.next_interview.from_time,
                    "to_time": application.next_interview.to_time,
                    "job_title": application.job_location.job_id.job_title,
                })


            latest_jobs_ids = all_jobs.order_by('-created_at')[:10].values('id')
            latest_jobs = JobLocationsModel.objects.filter(job_id__in = latest_jobs_ids)[:5]
            
            jobs_details = []
            for location in latest_jobs:
                
                joined = SelectedCandidates.objects.filter(application__job_location = location, joining_status = 'joined').count()
                selected = all_applications.filter(job_location = location, status = 'selected').count()
                rejected = all_applications.filter(job_location = location, status = "rejected").count()
                applications = all_applications.filter(job_location = location).count()
                number_of_rounds =  InterviewerDetails.objects.filter(job_id = location.job_id).count()
                rejected_at_last_round = all_applications.filter(job_location = location, round_num = number_of_rounds, status = 'rejected').count()
                interviewed = selected + rejected_at_last_round

                job_details = {
                    "role":location.job_id.job_title,
                    "positions_left": location.positions - joined,
                    "applications": applications,
                    "interviewed":interviewed,
                    "rejected": rejected,
                    "feedback_pending": 0,
                    "location": location.location,
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

            job_edit_version = JobPostingsEditedVersion.objects.filter(job_id=job_id).order_by("-created_at").first()

            if not job_edit_version:
                return Response({'notFound': "Job edit post not found"}, status=status.HTTP_404_NOT_FOUND)

            
            job_edit_fields = JobPostEditFields.objects.filter(edit_id=job_edit_version)

            print(job_edit_fields)
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

            if job_edit_version.user == request.user or job_edit_version.status == 'accepted':
                return Response({"status": job_edit_version.status}, status=status.HTTP_200_OK)

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
    permission_classes = [IsManager]
    def post(self, request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            if org:
                job_id = request.data.get('job_id')
                recruiter_map = request.data.get('recruiter_ids', {})  

                try:
                    job = JobPostings.objects.get(id=job_id, organization=org)
                except JobPostings.DoesNotExist:
                    return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

                for location_id_str, recruiter_ids in recruiter_map.items():
                    try:
                        location_id = int(location_id_str)
                        job_location = JobLocationsModel.objects.get(id=location_id, job_id=job)

                        assigned_job = AssignedJobs.objects.create(job_location=job_location, job_id = job)
                        recruiters = CustomUser.objects.filter(id__in=recruiter_ids, role='recruiter')
                        assigned_job.assigned_to.set(recruiters)

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
                    
                    
                    except JobLocationsModel.DoesNotExist:
                        return Response({"error":"JOb location doesnot exist"}, status=status.HTTP_200_OK)
                   

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

        try:
            all_jobs = JobPostings.objects.filter(organization__manager=user).select_related('username')

            total_postings = 0
            num_of_open_jobs = 0
            pending_approval = 0
            expired_jobs = 0
            closed_positions = 0


            jobs_list = []
            for job in all_jobs:
                job_postings = JobApplication.objects.filter(job_location__job_id = job.id)
                applied = job_postings.count()
                under_review = job_postings.filter( status='processing').count()
                hired = job_postings.filter( status='selected').count()
                rejected = job_postings.filter( status='rejected').count()
                
                num_of_rounds = job.rounds_of_interview
                rounds_details = []

                num_of_positions = 0
                locations = JobLocationsModel.objects.filter(job_id =  job)
                for location in locations:
                    num_of_positions += location.positions

                rounds_details.extend([
                                     {"Vacancies": num_of_positions},
                                     {"Applied": applied},
                                     {"Under Review": under_review},
                                    ])

                for round_num in range(1, num_of_rounds + 1):
                    count = job_postings.filter(
                        round_num=round_num,
                        status='processing'
                    ).count()
                    
                    rounds_details.append({f"Interview Round {round_num}": count})
                
                rounds_details.extend([
                                     {"Hired":hired},
                                     {"Rejected" : rejected}
                                    ])
                
                locations_assigned_to = AssignedJobs.objects.filter(job_id = job)
                assigned_to = {}
                for location in locations:
                    recruiters = list(locations_assigned_to.filter(job_location = location).values_list('assigned_to__username', flat= True))
                    assigned_to[location.location] = recruiters
                
              
                # print(assigned_to)

                job_details = {
                    "job_title": job.job_title,
                    "assigned_to": assigned_to,
                    "client_name": job.username.username if job.username else "Unknown",
                    "deadline": job.job_close_duration,
                    "status": job.status,
                    "approval_status": job.approval_status,
                    "id": job.id,
                    "rounds_details": rounds_details,
                    "is_posted_on_linkedin" : job.is_linkedin_posted,
                }

                jobs_list.append(job_details)
                total_postings += num_of_positions

                if job.approval_status == 'pending':
                    pending_approval+=1

                if job.status == 'opened':
                    num_of_open_jobs += 1
                
                if job.job_close_duration < timezone.now().date():
                    expired_jobs+=1

                applications_closed = job_postings.filter( status = 'selected').count()
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
            print(str(e))
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
            job_locations = JobLocationsModel.objects.filter(job_id__in = job_postings)
            current_time = now().date()

            for job in job_locations:
                
                job_close_duration = job.job_id.job_close_duration

                if current_time > job_close_duration - timedelta(days=5):
                    priority = "high"
                elif current_time > job_close_duration - timedelta(days=10):
                    priority = "medium"
                else:
                    priority = "low"

                jobs_closed = JobApplication.objects.filter(job_location=job.id, status='selected').count()
                status_percentage = (jobs_closed / job.positions * 100) if job.positions > 0 else 0
                assigned_to = AssignedJobs.objects.filter(job_location = job).values_list('assigned_to__username', flat=True)

                job_json = {
                    "job_title": job.job_id.job_title,
                    "num_of_positions": job.positions,
                    "priority": priority,
                    "due_date": job_close_duration,
                    "status": round(status_percentage, 2),  
                    "recruiters": assigned_to,
                    "location": job.location,
                }
                job_data.append(job_json)

            try:
                organization = Organization.objects.get(manager=user)
            except Organization.DoesNotExist:
                return Response({"error": "No organization found for this manager"}, status=status.HTTP_404_NOT_FOUND)

            all_recruiters = organization.recruiters.all()
            recruiters_list = [{"name": recruiter.username} for recruiter in all_recruiters]

            recent_activities = []
            applications = JobApplication.objects.filter(attached_to__in=all_recruiters).order_by('-updated_at')[:6]
            for application in applications:
                job = application.job_location.job_id
                task = ""
                if application.status == 'pending':
                    task = f"{application.resume.candidate_name}'s Resume is sent to {job.job_title}"
                elif application.status == 'processing' and application.next_interview:
                    task = f"New meeting scheduled for {application.resume.candidate_name}"
                

                time_diff = now() - application.updated_at

                if time_diff.seconds < 60:
                    thumbnail = f"Updated {time_diff.seconds} seconds ago"
                elif time_diff.seconds < 3600:
                    thumbnail = f"Updated {time_diff.seconds // 60} minutes ago"
                elif time_diff.seconds < 86400:
                    thumbnail = f"Updated {time_diff.seconds // 3600} hours ago"
                else:
                    thumbnail = f"Updated {time_diff.days} days ago"                                        


                recent_activities.append({
                    "name": application.attached_to.username,
                    "job_title": job.job_title,
                    "task": task,
                    "thumbnail": thumbnail
                })

            five_days_ago = datetime.now() - timedelta(days=5)
            new_jobs = job_postings.filter(created_at__gte=five_days_ago).count()
            on_going = job_postings.filter(status ='opened').count()

            completed_posts = 0
            completed_deadline = 0
            completed_jobs = job_postings.filter(status='closed')

            for job in completed_jobs:
                job_locations = JobLocationsModel.objects.filter(job_id  = job)
                total_positions = job_locations.aggregate(total=Sum('positions'))['total'] or 0
                positions_closed = JobApplication.objects.filter(job_location__in=job_locations, status='selected').count()
                if positions_closed >= total_positions:
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
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
class ViewSelectedCandidates(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            selected_candidates_list = []
            applications = JobApplication.objects.filter(job_location__job_id__organization__manager = user, status = 'selected')
            selected_candidates = SelectedCandidates.objects.filter(application__in = applications)
            for candidate in selected_candidates:
                job = candidate.application.job_location.job_id
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
                    "location": candidate.application.job_location.location,
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

            organization_data = {
                "name": organization.name,
                "org_code": organization.org_code,
                "username": organization.manager.username,
                "email": organization.manager.email,
                "company_address": organization.company_address,
                "gst_number": organization.gst_number,
                "company_pan": organization.company_pan,
                "contact_number": organization.contact_number,
                "id": organization.id,
                "website_url": organization.website_url,
            }

            return Response(organization_data,status=status.HTTP_200_OK)
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
            client_id = request.GET.get('id')

            if client_id:
                try:
                    client = ClientDetails.objects.filter(user=client_id).first()
                    if not client:
                        return Response({'error': 'Client not found'}, status=404)
                    
                    jobs = JobPostings.objects.filter(username=client.user, organization__manager=user)
                    associated_at = jobs.order_by('created_at').first()

                    total_positions = JobLocationsModel.objects.filter(
                        job_id__in=jobs
                    ).aggregate(total=Sum('positions'))['total'] or 0


                    client_data = {
                        'client_username': client.username,
                        'organization_name': client.name_of_organization,
                        'contact_number': client.contact_number,
                        'website_url': client.website_url,
                        'gst_number': client.gst_number,
                        'company_address': client.company_address,
                        'associated_at': associated_at.created_at
                    }

                    jobs_data = []
                    for job in jobs:
                        locations = JobLocationsModel.objects.filter(job_id = job)
                        for location in locations:
                            applications = JobApplication.objects.filter(job_location = location)
                            selected_application = SelectedCandidates.objects.filter(application__in = applications)

                            jobs_data.append(
                                {
                                    "openings": location.positions,
                                    "pending": applications.filter(status = 'pending').count(),
                                    "processing": applications.filter(status = 'processing').count(),
                                    "rejected": applications.filter(status = 'rejected').count(),
                                    "joined": selected_application.filter(joining_status = 'joined').count(),
                                    "selected": selected_application.filter(joining_status = 'pending').count(),
                                    "job_title": job.job_title,
                                    "status": job.status,
                                }
                            )

                    return Response({"client_data":client_data, "jobs_data": jobs_data}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({'error': str(e)}, status=500)
            else:
                jobs = JobPostings.objects.filter(organization__manager=user).order_by('created_at')
                data = []
                requests = ClientOrganizations.objects.filter(organization__manager = request.user, approval_status = 'pending')
                requests_list= []
                for connection_request in requests:
                    requests_list.append(
                        {
                            "company_name": connection_request.client.name_of_organization,
                            "client_name": connection_request.client.user.username,
                            "client_email": connection_request.client.user.email,
                            "id": connection_request.id
                        }
                    )

                added_clients = set()  
                for job_item in jobs:
                    client = ClientDetails.objects.filter(user=job_item.username).first()
                    if client and client.username not in added_clients:
                        data.append({
                            "client_id": client.id,
                            'client_username': client.username,
                            'organization_name': client.name_of_organization,
                            'contact_number': client.contact_number,
                            'website_url': client.website_url,
                            'gst_number': client.gst_number,
                            'company_address': client.company_address,
                            "associated_at": job_item.created_at,
                        })
                        added_clients.add(client.username)  

                return Response({"data":data, "connection_requests":requests_list}, status=200)


        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class RejectApprovalClient(APIView):
    permission_classes = [IsManager]
    def post(self, request):
        try:
            connection_id = request.GET.get('connection_id')
            connection = ClientOrganizations.objects.get(id = connection_id)
            connection.approval_status = 'rejected'
            connection.save()
            return Response({"message":"Rejected successfully"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcceptApprovalClient(APIView):
    permission_classes = [IsManager]
    def post(self, request):
        try:
            connection_id = request.GET.get('connection_id')
            if not connection_id:
                return Response({'error': 'Missing connection_id'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                connection = ClientOrganizations.objects.get(id=connection_id)
            except ClientOrganizations.DoesNotExist:
                return Response({'error': 'Invalid connection_id'}, status=status.HTTP_404_NOT_FOUND)
            connection = ClientOrganizations.objects.get(id = connection_id)

            terms_list = request.data.get('terms')
            if not isinstance(terms_list, list):
                return Response({'error': 'Expected a list of terms'}, status=status.HTTP_400_BAD_REQUEST)
            
            
            with transaction.atomic():
                connection.approval_status = "accepted"
                connection.save()
                for terms in terms_list:
                    print(terms.get('service_fee_type'), terms)
                    try:
                        raw_fee = terms.get('service_fee')
                        service_fee = Decimal(str(raw_fee)) if raw_fee is not None else Decimal("0.00")
                        print(service_fee)
                    except InvalidOperation:
                        return Response({'error': f"Invalid service_fee value: {raw_fee}"}, status=status.HTTP_400_BAD_REQUEST)
                    ClientOrganizationTerms.objects.create(
                        client_organization = connection,
                        service_fee_type = terms.get('service_fee_type'),
                        ctc_range = terms.get('ctc_range'),
                        service_fee = service_fee,
                        replacement_clause = terms.get('replacement_clause'),
                        invoice_after = terms.get('invoice_after'),
                        payment_within = terms.get('payment_within'),
                        interest_percentage = terms.get('interest_percentage')
                    )
            return Response({"message":"Accepted successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
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
        

class PostOnLinkedIn(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            if not job_id:
                return Response({"error":"Job Id required"}, status=status.HTTP_400_BAD_REQUEST)
            job = JobPostings.objects.get(id = job_id)
            if job.approval_status == False:
                return Response({"error":"Job must be approved before posting it on linkedin"}, status=status.HTTP_400_BAD_REQUEST)
            if job.is_linkedin_posted:
                return Response({"error":"Already posted on linkedin"}, status=status.HTTP_400_BAD_REQUEST)
            if job.status == 'closed':
                return Response({"error":"Jobpost is closed, unable to post"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                linkedin_connection = LinkedinIntegrations.objects.get(agency__manager= request.user)
            except Exception as e:
                return Response({"error":"You are not connected to linkedin, go to profile and add your account"}, status=status.HTTP_400_BAD_REQUEST)
            
            if linkedin_connection.token_expires_at <= timezone.now():
                return Response({
                    "error": "Your LinkedIn session has expired. Please reconnect your account from your profile.",
                    "reason": "TOKEN_EXPIRED"
                }, status=status.HTTP_401_UNAUTHORIZED)

            
            token = linkedin_connection.access_token
            urn = linkedin_connection.organization_urn

            job_title = job.job_title
            job_description = job.job_description
            job_primary_skills = SkillMetricsModel.objects.filter(job_id = job, is_primary = True).values('id','skill_name')
            job_secondary_skills = SkillMetricsModel.objects.filter(job_id = job, is_primary = False).values('id','skill_name')
            years_of_experience = job.years_of_experience

            post_content = f"""📢 Job Opportunity: {job_title} 📢

We are looking for a talented individual with {years_of_experience} years of experience to join our team as a {job_title}.

About the Role:
{job_description}

Primary Skills Required:
{', '.join([skill['skill_name'] for skill in job_primary_skills])}

Secondary Skills (Good to Have):
{', '.join([skill['skill_name'] for skill in job_secondary_skills])}

If you are interested in this exciting opportunity, please apply or reach out for more details!

#jobopening #hiring #{job_title.replace(' ', '')} #career
"""

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            data = {
                "author": urn,  # Example: "urn:li:organization:123456"
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_content
                        },
                        "shareMediaCategory": "NONE",  # Use "IMAGE" or "ARTICLE" if needed
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            response_org = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=data)

            if response_org.status_code == 201:
                job.is_linkedin_posted_organization = True

                hiresync_linkedin_cred = HiresyncLinkedinCred.objects.filter()[0]

                personal_token = hiresync_linkedin_cred.access_token
                personal_urn = hiresync_linkedin_cred.organization_urn

                personal_headers = {
                    "Authorization": f"Bearer {personal_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                }

                personal_data = {
                    "author": personal_urn,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {
                                "text": post_content
                            },
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }

                response_personal = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=personal_headers, json=personal_data)

                if response_personal.status_code == 201:
                    job.is_linkedin_posted_personal = True 
                    job.save()
                    return Response({"message": "Successfully posted on LinkedIn Organization and your Personal profile."}, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "message": "Successfully posted on LinkedIn Organization, but failed to post on your Personal profile.",
                        "personal_error_details": response_personal.json()
                    }, status=status.HTTP_200_OK)
                

            else:
                return Response({
                    "error": "Failed to post on LinkedIn",
                    "details": response.json()
                }, status=response.status_code)

        except Exception as e:
            print( str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class IsManagerLinkedVerifiedView(APIView):
    permission_classes  = [IsManager]
    def get(self, request):
        try:
            manager = request.user
            try:
                manager_linkedin = LinkedinIntegrations.objects.get(agency__manager=manager)
            except LinkedinIntegrations.DoesNotExist:
                return Response({"status": False}, status=status.HTTP_200_OK)


            if manager_linkedin.token_expires_at and manager_linkedin.token_expires_at < timezone.now():
                
                state = str(manager_linkedin.agency.id)
                auth_url = (
                    f"https://www.linkedin.com/oauth/v2/authorization?"
                    f"response_type=code&client_id={settings.LINKEDIN_CLIENT_ID}"
                    f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
                    f"&scope=w_member_social%20rw_organization_admin%20w_organization_social"
                    f"&state={state}"
                )
                return Response({
                    "status": False,
                    "expired": True,
                    "auth_url": auth_url,
                    "message": "LinkedIn access token expired. Please re-authenticate."
                }, status=status.HTTP_200_OK)

            # ✅ Token still valid
            return Response({"status": manager_linkedin.is_linkedin_connected}, status=status.HTTP_200_OK)

        except Exception as e:
            print("Error in IsManagerLinkedVerifiedView:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    
    def post(self, request):
        try:
            user = request.user
            agency = Organization.objects.get(manager = user)

            with transaction.atomic():
                try:
                    agency_linkedin = LinkedinIntegrations.objects.get(agency = agency)

                except LinkedinIntegrations.DoesNotExist:
                    agency_linkedin = LinkedinIntegrations.objects.create(
                        agency = agency,
                    )

                state = str(agency.id)
                request.session['linkedin_auth_state'] = state

                LINKEDIN_REDIRECT_URI = f"{os.environ.get('frontendurl')}/linkedin/callback"
                
                auth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"response_type=code&client_id={settings.LINKEDIN_CLIENT_ID}"
            f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
            f"&scope=w_member_social%20rw_organization_admin%20w_organization_social"
            f"&state={agency.id}"
        )
                return Response({"url":auth_url}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print("Error in RemoveRecruiter:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class LinkedINCallBackView(APIView):
    def get(self, request):
        try:
            code = request.GET.get('code')
            agency_id = request.GET.get('state')
            error = request.GET.get('error')

            if error:
                return Response({"message": "Authorization denied by user.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            if not code or not agency_id:
                return Response({"message": "Missing code or state in the request.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            # Exchange code for access token
            token_response = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                },
            )

            if token_response.status_code != 200:
                return Response({
                    "message": "Failed to retrieve access token from LinkedIn.",
                    "details": token_response.json(),
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")

            if not access_token:
                return Response({"message": "Access token not found in response.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch organizations (pages) the user has admin access to
            orgs_response = requests.get(
                "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if orgs_response.status_code != 200:
                return Response({
                    "message": "Failed to fetch LinkedIn organizations.",
                    "details": orgs_response.json(),
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            org_data = orgs_response.json()
            elements = org_data.get("elements", [])

            if not elements:
                return Response({
                    "message": "No LinkedIn Page found for this account.",
                    "reason": "NO_PAGE",
                    "status": False
                }, status=status.HTTP_200_OK)

            organization_urn = elements[0].get("organizationalTarget")
            if not organization_urn:
                return Response({
                    "message": "Organization URN not found.",
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            # Save token and organization info
            try:
                agency_linkedin = LinkedinIntegrations.objects.get(agency=agency_id)
            except LinkedinIntegrations.DoesNotExist:
                return Response({
                    "message": "LinkedinIntegration record not found for this agency.",
                    "status": False
                }, status=status.HTTP_404_NOT_FOUND)

            agency_linkedin.access_token = access_token
            agency_linkedin.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
            agency_linkedin.organization_urn = organization_urn
            agency_linkedin.is_linkedin_connected = True
            agency_linkedin.save()

            return Response({
                "message": "Agency connected to LinkedIn successfully.",
                "status": True
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("Callback Error:", str(e))
            return Response({"message": "Unexpected error occurred.", "error": str(e), "status": False}, status=status.HTTP_400_BAD_REQUEST)

class RecSummaryMetrics(APIView):
    permission_classes = [IsManager]
    def get(self, request, *args, **kwargs):
        rctr_id = request.GET.get("rctr_id")

        try:
            rctr_obj = CustomUser.objects.get(id=rctr_id)  
        except ObjectDoesNotExist:
            return Response({"error": "Recruiter not found"}, status=404)

        jobs_assigned = AssignedJobs.objects.filter(assigned_to = rctr_obj)
        total_jobs_assigned = jobs_assigned.count()


        interviews = InterviewSchedule.objects.filter(rctr=rctr_obj)
        interviews_count = interviews.count()

        applications = JobApplication.objects.filter(attached_to = rctr_obj)
        applications_count = applications.count()

        selected_candidates = SelectedCandidates.objects.filter(application__attached_to = rctr_id)


        pending_candidates_count = selected_candidates.filter(joining_status = "pending").count()

        joined_candidates_count = selected_candidates.filter(joining_status = 'joined').count()

        candidates_on_processing = applications.filter( status = 'processing')[:10]
        candidates_data = []
        for candidate in candidates_on_processing:
    
            candidates_data.append({
                "candidate_name": candidate.resume.candidate_name,
                "role": candidate.job_location.job_id.job_title,
                "status": candidate.status,
                "profile": None
            }) 
        
        cards_data = {
            "application_count": applications_count,
            "interviews_count": interviews_count,
            "job_postings_count": total_jobs_assigned,
            "pending_candidates_count": pending_candidates_count,
            "joined_candidates_count": joined_candidates_count,
        }
        
        interview_data = []
        for interview in interviews:
            interview_data.append({
                "scheduled_date":interview.scheduled_date,
                "profile": interview.interviewer.name.profile.url if interview.interviewer.name.profile else None,
                "job_title": interview.job_location.job_id.job_title,
                "scheduled_time": f"{interview.from_time} - {interview.to_time}",
                "candidate_name": interview.candidate.candidate_name,
                "from_time": interview.from_time,
                "to_time": interview.to_time,
                "round_num": interview.round_num,
                "id": interview.id,
                "interviewer_name": interview.interviewer.name.username
            })

        
        job_data = []
        for assigned_job in jobs_assigned:
            applications = JobApplication.objects.filter(job_location = assigned_job.job_location)
            job = assigned_job.job_id
            job_location = assigned_job.job_location
            joined = 0
            for application in applications:
                try:
                    selected_candidate = SelectedCandidates.objects.get(application = application, joining_status = 'joined')
                    joined +=1
                except SelectedCandidates.DoesNotExist:
                    continue
            job_data.append(
                {
                    "job_id": job.id,
                    "job_title": job.job_title,
                    "location": job_location.location,
                    "positions": job_location.positions,
                    "dead_line": job.job_close_duration,
                    "application_count": len(applications),
                    "joined": joined,
                }
            )

        return Response({
            "cards_data": cards_data,
            "on_processing": candidates_data,
            "interviews": interview_data,
            "jobs_data": job_data,
        }, status=status.HTTP_200_OK)
    


class ManagerResumeBankView(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            applications = JobApplication.objects.filter(
                job_location__job_id__organization__manager=request.user
            ).select_related('resume', 'job_location__job_id')

            candidate_data = {}

            for app in applications:
                email = app.resume.candidate_email

                if email not in candidate_data:
                    candidate_data[email] = {
                        'resume': app.resume.resume.url if app.resume.resume else None,
                        'candidate_name': app.resume.candidate_name,
                        'candidate_email': email,
                        'job_count': 0,
                        'jobs': []
                    }

                candidate_data[email]['job_count'] += 1
                candidate_data[email]['jobs'].append({
                    'job_title': app.job_location.job_id.job_title,
                    'status': app.status
                })

            candidate_data = list(candidate_data.values())
            paginator = TenResultsPagination()
            page = paginator.paginate_queryset(candidate_data,request )

            recruiters = list(Organization.objects.get(manager = request.user).recruiters.values_list('email','username'))

            applications_list = []
            for application in applications:
                application_status = application.status
                if application_status == 'selected':
                    try:
                        application_status = SelectedCandidates.objects.get(application = application).joining_status
                    except SelectedCandidates.DoesNotExist:
                        pass
                applications_list.append({
                    "status": application_status,
                    "attached_to":application.attached_to.email
                })

            
            selectedPlan = OrganizationPlan.objects.get(organization__manager = request.user ).plan
            storage_feature = PlanFeature.objects.get(feature__code = 'storage', plan = selectedPlan)
            storage_limit = storage_feature.limit

            return paginator.get_paginated_response({
                "resumes": page,
                "storage": get_resume_storage_usage(request.user) ,
                "applications": applications_list,
                "recruiters": recruiters,
                "storage_limit": storage_limit
            })

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConnectionRequests(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            connection_id = request.GET.get('connection_id')
            if connection_id:
                pass
            
            requests = ClientOrganizations.objects.filter(organization__manager = request.user, approval_status = 'pending')
            requests_list= []
            for connection_request in requests:
                requests_list.append(
                    {
                        "company_name": connection_request.client.name_of_organization,
                        "client_name": connection_request.client.user.username,
                        "client_email": connection_request.client.user.email,
                        "id": connection_request.id
                    }
                )
            return Response({"data":requests_list}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)