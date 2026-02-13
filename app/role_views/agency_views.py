from ..models import *
from datetime import date
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
from django.utils.timezone import now, is_aware, make_naive
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, Count
from decimal import Decimal, InvalidOperation
import csv
from django.http import HttpResponse
import traceback


logger = logging.getLogger(__name__)


class AgencyJobApplications(APIView):
    permission_classes = [IsManager]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            job_postings = JobPostings.objects.filter(organization=org)
            job_locations = JobLocationsModel.objects.filter(job_id__organization=org)
            job_locations_ids = job_locations.values("id")
            applications = JobApplication.objects.filter(
                job_location__in=job_locations_ids
            ).select_related("resume", "job_location")
            print("entered ", applications)

            job_titles = [
                {"job_id": job.id, "job_title": job.job_title}
                for job in job_postings.distinct()
            ]

            applications_list = []
            for app in applications:
                job = app.job_location.job_id
                applications_list.append(
                    {
                        "candidate_name": app.resume.candidate_name,
                        "application_id": app.id,
                        "job_id": app.id,
                        "job_title": job.job_title,
                        "job_department": job.job_department,
                        "job_description": job.job_description,
                        "job_title": job.job_title,
                        "job_department": job.job_department,
                        "job_description": job.job_description,
                        "application_status": app.status,
                        "feedback": app.feedback,
                    }
                )

            return Response(
                {"applications_list": applications_list, "job_titles": job_titles},
                status=status.HTTP_200_OK,
            )

        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(str(e))
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

            return Response(
                {"detail": f"Deleted {deleted_count} applications."}, status=200
            )

        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=404)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class AgencyDashboardAPI(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            agency_name = Organization.objects.get(manager=user).name
            all_applications = JobApplication.objects.filter(
                job_location__job_id__organization__name=agency_name
            )
            all_jobs = JobPostings.objects.filter(organization__name=agency_name)
            pending_assigned = 0
            for job in all_jobs:
                locations = JobLocationsModel.objects.filter(job_id=job).count()
                assigned_locations = (
                    AssignedJobs.objects.filter(job_id=job)
                    .values_list("job_location", flat=True)
                    .distinct()
                )
                assigned_jobs = len(set(assigned_locations))

                if locations > assigned_jobs:
                    pending_assigned += 1

            approval_pending = all_jobs.filter(approval_status="pending").count()
            interviews_scheduled = all_applications.exclude(next_interview=None).count()
            recruiter_allocation_pending = pending_assigned
            jobpost_edit_requests = JobPostingsEditedVersion.objects.filter(
                job_id__organization__manager=user
            ).count()
            opened_jobs = all_jobs.filter(status="opened").count()
            closed_jobs = all_jobs.filter(status="closed").count()
            applications = all_applications.exclude(next_interview=None).order_by(
                "-next_interview__scheduled_date"
            )[:20]
            upcoming_interviews = []

            for application in applications:
                upcoming_interviews.append(
                    {
                        "interviewer_name": application.next_interview.interviewer.name.username,
                        "round_num": application.round_num,
                        "candidate_name": application.resume.candidate_name,
                        "scheduled_time": application.next_interview.scheduled_date,
                        "from_time": application.next_interview.from_time,
                        "to_time": application.next_interview.to_time,
                        "job_title": application.job_location.job_id.job_title,
                    }
                )

            latest_jobs_ids = all_jobs.order_by("-created_at")[:10].values("id")
            latest_jobs = JobLocationsModel.objects.filter(job_id__in=latest_jobs_ids)[
                :5
            ]

            jobs_details = []
            for location in latest_jobs:

                joined = SelectedCandidates.objects.filter(
                    application__job_location=location, joining_status="joined"
                ).count()
                selected = all_applications.filter(
                    job_location=location, status="selected"
                ).count()
                rejected = all_applications.filter(
                    job_location=location, status="rejected"
                ).count()
                applications = all_applications.filter(job_location=location).count()
                number_of_rounds = InterviewerDetails.objects.filter(
                    job_id=location.job_id
                ).count()
                rejected_at_last_round = all_applications.filter(
                    job_location=location, round_num=number_of_rounds, status="rejected"
                ).count()
                interviewed = selected + rejected_at_last_round

                job_details = {
                    "role": location.job_id.job_title,
                    "positions_left": location.positions - joined,
                    "applications": applications,
                    "interviewed": interviewed,
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
                "closed_jobs": closed_jobs,
            }

            return Response(
                {
                    "data": data,
                    "latest_jobs": jobs_details,
                    "upcoming_interviews": upcoming_interviews,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Job Postings

# Get all job postings of the particular organization


class NotAssignedJobs(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            jobs = JobPostings.objects.filter(
                organization__manager=user, approval_status="accepted"
            )
            jobs_list = []
            for job in jobs:
                job_locations = JobLocationsModel.objects.filter(job_id=job.id)
                for location in job_locations:
                    assigned = AssignedJobs.objects.filter(job_location=location.id)
                    if assigned.count() == 0:
                        jobs_list.append(
                            {
                                "job_title": job.job_title,
                                "client_name": job.username.username,
                                "created_at": job.created_at,
                                "location": location.location,
                                "deadline": job.job_close_duration,
                                "id": job.id,
                                "location_id": location.id,
                            }
                        )

            return Response({"data": jobs_list}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClosedHoldJobs(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            jobs = JobPostings.objects.filter(
                organization__manager=user, status__in=["closed", "hold"]
            )
            jobs_list = []
            for job in jobs:
                jobs_list.append(
                    {
                        "job_title": job.job_title,
                        "client_name": job.username.username,
                        "deadline": job.job_close_duration,
                        "status": job.status,
                        "created_at": job.created_at,
                        "id": job.id,
                    }
                )

            return Response({"data": jobs_list}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            pass
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectedJobs(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            jobs = JobPostings.objects.filter(
                organization__manager=user, approval_status="rejected"
            )
            jobs_list = []
            for job in jobs:
                jobs_list.append(
                    {
                        "job_title": job.job_title,
                        "client_name": job.username.username,
                        "deadline": job.job_close_duration,
                        "status": job.status,
                        "created_at": job.created_at,
                        "id": job.id,
                        "reason": job.reason,
                    }
                )

            return Response({"data": jobs_list}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NotApprovedJobs(APIView):
    permission_classes = [IsManager]

    def get_job_post_limit(self, organization_id):
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return False

        try:
            org_plan = OrganizationPlan.objects.get(
                organization=organization, is_active=True
            )
        except OrganizationPlan.DoesNotExist:
            return False

        plan = org_plan.plan
        if not plan:
            return False

        try:
            feature = Feature.objects.get(code="active_jobpost")
        except Feature.DoesNotExist:
            return False

        try:
            plan_feature = PlanFeature.objects.get(plan=plan, feature=feature)
            job_limit = plan_feature.limit
        except PlanFeature.DoesNotExist:
            return False

        current_jobs = JobPostings.objects.filter(organization=organization).count()

        return current_jobs < job_limit if job_limit is not None else True

    def get(self, request):

        try:
            user = request.user
            jobs = JobPostings.objects.filter(
                organization__manager=user, approval_status="pending"
            )
            jobs_list = []
            for job in jobs:

                jobs_list.append(
                    {
                        "job_title": job.job_title,
                        "client_name": job.username.username,
                        "deadline": job.job_close_duration,
                        "status": job.status,
                        "created_at": job.created_at,
                        "id": job.id,
                        "can_open": self.get_job_post_limit(job.organization.id),
                        "reason": job.reason,
                    }
                )

            return Response({"data": jobs_list}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, action, job_id):
        try:
            job = JobPostings.objects.get(id=job_id)
            print(action, job_id)
            if action == "APPROVE":
                job.approval_status = "accepted"
            elif action == "REJECT":
                reject_reason = request.data.get("reason")
                job.approval_status = "rejected"
                job.reason = reject_reason
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category=Notifications.CategoryChoices.REJECT_JOB,
                    subject=f"Job Post Rejected by {request.user.username}",
                    message=(
                        f"Job Request Rejected\n\n"
                        f"Your job request for the position of **{job.job_title}** has been reviewed by "
                        f"{request.user.username} and was not accepted.\n\n"
                        f"Reason: {reject_reason}\n\n"
                        f"You may consider submitting a new job request with updated details if needed.\n\n"
                        f"Thank you for understanding."
                    ),
                )
            elif action == "PLAN_LIMIT_REJECT":
                reject_reason = request.data.get("reason")
                job.reason = reject_reason

                # Create Dashboard Notification
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category=Notifications.CategoryChoices.PLAN_LIMIT_REJECT,
                    subject=f"Update regarding your job post: {job.job_title}",
                    message=(
                        f"Dear {job.username.username},\n\n"
                        f"Thank you for posting the job for '{job.job_title}'.\n\n"
                        f"We wanted to inform you that we are unable to open this job posting at this time.\n\n"
                        f"Manager's Note: {reject_reason}\n\n"
                        f"We value our partnership and will notify you as soon as we are able to proceed with this posting.\n\n"
                        f"Best regards,\n"
                        f"{request.user.username}\n"
                        f"{request.user.organization.name if request.user.organization else ''}"
                    ),
                )

                # Send Email
                email_subject = f"Update regarding your job post: {job.job_title}"
                email_body = (
                    f"Dear {job.username.username},\n\n"
                    f"Thank you for posting the job for '{job.job_title}'.\n\n"
                    f"We wanted to inform you that we are unable to open this job posting at this time.\n\n"
                    f"Manager's Note: {reject_reason}\n\n"
                    f"We value our partnership and will notify you as soon as we are able to proceed with this posting.\n\n"
                    f"Best regards,\n"
                    f"{request.user.username}\n"
                    f"{request.user.organization.name if request.user.organization else ''}"
                )
                send_custom_mail(email_subject, email_body, [job.username.email])

            job.save()

            return Response(
                {"message": f"Job post {action}D successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrgJobPostings(APIView):
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            job_postings = JobPostings.objects.filter(organization=org)

            job_postings_json = []
            try:
                for job in job_postings:
                    applied = JobApplication.objects.filter(job_id=job).count()
                    under_review = JobApplication.objects.filter(
                        job_id=job, status="pending"
                    ).count()
                    selected = JobApplication.objects.filter(
                        job_id=job, status="selected"
                    ).count()
                    rejected = JobApplication.objects.filter(
                        job_id=job, status="rejected"
                    ).count()
                    number_of_rounds = InterviewerDetails.objects.filter(
                        job_id=job
                    ).count()
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
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            serializer = JobPostingsSerializer(job_postings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


# View particular job post
class OrgParticularJobPost(APIView):
    def get(self, request):
        try:
            user = request.user
            if user.role == "manager":
                id = request.GET.get("id")
                if id == None:
                    return Response(
                        {"error": "ID is not mentioned"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    jobEditedPost = JobPostingsEditedVersion.objects.get(id=id).status
                    if jobEditedPost == "pending":
                        print("your job edit request is in pending")
                        return Response(
                            {
                                "error": "Your have already sent an edit request to this job post"
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                except JobPostingsEditedVersion.DoesNotExist:
                    pass

                jobPost = JobPostings.objects.get(id=id)
                jobPost_serializer = JobPostingsSerializer(jobPost)
                return Response(jobPost_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# View the edit request of manager(your role)
class JobEditStatusAPIView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            job_id = request.GET.get("id")
            if not job_id:
                return Response(
                    {"error": "Job ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job = JobPostings.objects.get(id=job_id)

            job_edit_versions = JobPostingsEditedVersion.objects.filter(
                job_id=job
            ).order_by("-created_at")

            if not job_edit_versions.exists():
                return Response(
                    {"notFound": "No job edit history found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_data = []

            for version in job_edit_versions:
                job_edit_fields = JobPostEditFields.objects.filter(edit_id=version)

                fields_json = [
                    {
                        "field_name": field.field_name,
                        "field_value": field.field_value,
                        "status": field.status,
                    }
                    for field in job_edit_fields
                ]

                rejected = any(f.status == "rejected" for f in job_edit_fields)

                old_fields_json = []
                if version.base_version:
                    old_edit_fields = JobPostEditFields.objects.filter(
                        edit_id=version.base_version
                    )
                    old_fields_json = [
                        {
                            "field_name": field.field_name,
                            "field_value": field.field_value,
                            "status": field.status,
                        }
                        for field in old_edit_fields
                    ]

                response_data.append(
                    {
                        "edit_id": version.id,
                        "status": version.status,
                        "edited_by": version.user.username,
                        "created_at": version.created_at,
                        "has_rejected_fields": rejected,
                        "old_fields": old_fields_json,
                        "new_fields": fields_json,
                    }
                )

            return Response(
                {
                    "job_id": job.id,
                    "status": (
                        job_edit_versions[0].status
                        if job_edit_versions.exists()
                        else None
                    ),
                    "edit_history": response_data,
                },
                status=status.HTTP_200_OK,
            )

        except JobPostings.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrgJobEdits(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            if request.GET.get("id"):
                id = request.GET.get("id")
                edited_job = JobPostingsEditedVersion.objects.get(id=id)
                if edited_job.edited_by != user:
                    return Response(
                        {"error": "You are not allowed to edit other people job posts"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serialized_edited_job = JobPostEditedSerializer(edited_job)
                return Response(
                    serialized_edited_job.data, status=status.HTTP_202_ACCEPTED
                )
            else:
                edited_jobs = JobPostingsEditedVersion.objects.filter(
                    job_id__organization__manager=request.user, version=1
                )
                jobs = []
                for job in edited_jobs:

                    jobs.append(
                        {
                            "job_title": job.job_id.job_title,
                            "edited_on": job.created_at,
                            "status": job.status,
                            "edit_id": job.id,
                            "job_id": job.job_id.id,
                            "client_name": job.job_id.username.username,
                            "organization_name": job.job_id.username.organization,
                        }
                    )
                # if(edited_jobs == None):
                #     return Response({"message":"There are no edited job posts"}, status=status.HTTP_200_OK)
                # edited_jobs_serialized_data = JobPostEditedSerializerMinFields(edited_jobs,many = True)
                return Response(jobs, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            data = request.data
            user = request.user
            job_id = request.GET.get("id")

            changes = data.get("changes", [])
            primary_skills = data.get("primarySkills", [])
            secondary_skills = data.get("secondarySkills", [])

            with transaction.atomic():
                job = JobPostings.objects.get(id=job_id)

                edit_version = JobPostingsEditedVersion.objects.create(
                    job_id=job,
                    user=user,
                )

                for field_name, field_value in changes.items():
                    original_value = getattr(job, field_name, None)

                    print(
                        f"DEBUG: field_name='{field_name}', incoming_type={type(field_value)}, original_type={type(original_value)}"
                    )
                    print(
                        f"DEBUG: incoming_value='{field_value}', original_value='{original_value}'"
                    )

                    # Handle stringified comparison for range fields or potential type mismatches
                    str_incoming = str(field_value).replace(" ", "").strip("[]")
                    str_original = str(original_value).replace(" ", "").strip("[]")

                    if str_incoming != str_original:
                        print(
                            f"DEBUG: Field '{field_name}' changed. Creating JobPostEditFields."
                        )
                        JobPostEditFields.objects.create(
                            edit_id=edit_version,
                            field_name=field_name,
                            field_value=field_value,
                        )
                    else:
                        print(f"DEBUG: Field '{field_name}' has no change.")

                actual_primary_skills = SkillMetricsModel.objects.filter(
                    job_id=job, is_primary=True
                )
                actual_secondary_skills = SkillMetricsModel.objects.filter(
                    job_id=job, is_primary=False
                )

                for skill in primary_skills:
                    skill_name = skill.get("skill_name")
                    metric_type = skill.get("metric_type")
                    metric_value = skill.get("metric_value")

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
                    skill_name = skill.get("skill_name")
                    metric_type = skill.get("metric_type")
                    metric_value = skill.get("metric_value")

                    try:
                        actual_index = actual_secondary_skills.get(
                            skill_name=skill_name
                        )

                        if (
                            actual_index.metric_type != metric_type
                            or actual_index.metric_value != metric_value
                        ):
                            skill_metric = SkillMetricsModelEdited.objects.create(
                                job_id=edit_version,
                                is_primary=False,
                                skill_name=skill_name,
                                metric_type=metric_type,
                                metric_value=metric_value,
                            )

                    except actual_secondary_skills.model.DoesNotExist:
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
                    category=Notifications.CategoryChoices.EDIT_JOB,
                    receiver=job.username,
                    subject=f"Job Edit Request",
                    message=(
                        f"✏ Job Edit Request\n\n"
                        f"The organization has requested an edit for the following job post.\n\n"
                        f"Position: *{job.job_title}*\n"
                        f"Client: {job.username}\n\n"
                        f"Please review the requested changes and update the job post accordingly.\n\n"
                        f"link::client/edit-requests"
                    ),
                )
                job_post_log(
                    job.id,
                    f"organization has requested an edit for the job {job.job_title} to client {job.username.username}",
                )
                # Email logic...

                return Response(
                    {"message": "Job post edit request sent successfully"},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            print("error is ", str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AcceptJobPostView(APIView):
    permission_classes = [IsManager]

    def put(self, request):
        try:
            job_id = int(request.GET.get("id"))

            if not job_id:
                return Response(
                    {"error": "Job post id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            action = request.GET.get("action")

            try:
                job_post = JobPostings.objects.get(id=job_id)
                if action == "accept":
                    job_post.approval_status = "accepted"

                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category=Notifications.CategoryChoices.ACCEPT_JOB,
                        subject=f"Job Post Accepted by {request.user.username}",
                        message=(
                            f"✅ Job Request Accepted\n\n"
                            f"Your job request for the position of **{job_post.job_title}** has been accepted by "
                            f"{request.user.username}.\n\n"
                            f"The organization has started reviewing and shortlisting suitable profiles for this role. "
                            f"You will be notified once candidates are shortlisted or selected.\n\n"
                            f"Thank you for using our platform! 🙌"
                        ),
                    )

                    job_post_log(
                        job_post.id,
                        f"client {job_post.username.username} job request for  jobtitle: {job_post.job_title} has been approved by the agency manager {request.user.username} ",
                    )

                elif action == "reject":
                    job_post.approval_status = "rejected"
                    reason = request.data.get("reason")

                    job_post.reason = reason
                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category=Notifications.CategoryChoices.REJECT_JOB,
                        subject=f"Job Post Rejected by {request.user.username}",
                        message=(
                            f"Job Request Rejected\n\n"
                            f"Your job request for the position of **{job_post.job_title}** has been reviewed by "
                            f"{request.user.username} and was not accepted.\n\n"
                            f"This could be due to internal requirements or job role mismatch.\n\n"
                            f"You may consider submitting a new job request with updated details if needed.\n\n"
                            f"Thank you for understanding."
                        ),
                    )

                    job_post_log(
                        job_post.id,
                        f"client {job_post.username.username} job request for  jobtitle: {job_post.job_title} has been Rejected by the agency manager {request.user.username} reson for rejection {job_post.reason}",
                    )

                job_post.save()
                return Response(
                    {"message": "Job post updated successfully"},
                    status=status.HTTP_200_OK,
                )
            except JobPostings.DoesNotExist:
                return Response(
                    {"error": "Job post does not exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            print("error is ", str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class JobEditActionView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            job_id = request.GET.get("id")
            job = JobPostings.objects.get(id=job_id)
            action = request.GET.get("action")
            if action == "accept":
                job_edit_request = (
                    JobPostingsEditedVersion.objects.filter(job_id=job)
                    .order_by("-created_at")
                    .first()
                )
                if job_edit_request.user.role == "client":

                    job_edit_fields = JobPostEditFields.objects.filter(
                        edit_id=job_edit_request
                    )

                    with transaction.atomic():
                        for field in job_edit_fields:
                            setattr(job, field.field_name, field.field_value)
                            field.status = "accepted"
                            field.save()
                        job_edit_request.status = "accepted"
                        job_edit_request.save()
                job.approval_status = "accepted"
                job.save()
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category=Notifications.CategoryChoices.ACCEPT_JOB,
                    subject=f"Job {job.job_title} request has been approved by {request.user}",
                    message=(
                        f"Dear {job.username},\n\n"
                        f"Your request for the job '{job.job_title}' has been approved by {request.user}.\n"
                        "We will now proceed to find the perfect profiles for this job.\n\n"
                        "Best regards,\n"
                        f"{request.user}"
                    ),
                )
                job_post_log(
                    job.id,
                    f"edit request from the client has been approved by agency manager {request.user.username}",
                )

                return Response(
                    {"message": "Job approved successfully"}, status=status.HTTP_200_OK
                )

            if action == "reject":
                job.approval_status = "reject"
                job.save()
                Notifications.objects.create(
                    sender=request.user,
                    receiver=job.username,
                    category=Notifications.CategoryChoices.REJECT_JOB,
                    subject=f"Job {job.job_title} request has been rejected by {request.user}",
                    message=(
                        f"Dear {job.username},\n\n"
                        f"Your request for the job '{job.job_title}' has been rejected by {request.user}.\n"
                        "Best regards,\n"
                        f"{request.user}"
                    ),
                )

                job_post_log(
                    job.id,
                    f"edit request from the client has been Rejected by agency manager {request.user.username}",
                )

                return Response(
                    {"message": "Job post rejected successfully"},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Get all the recruiters and Add the recruiter
class RecruitersView(APIView):

    permission_classes = [IsManager]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)
            if request.GET.get("names") == "true":
                recruiters_list = [
                    {"id": recruiter.id, "name": recruiter.username}
                    for recruiter in org.recruiters.all()
                ]
                return Response(recruiters_list, status=status.HTTP_200_OK)

            serializer = OrganizationSerializer(org)
            return Response(serializer.data["recruiters"], status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            alloted_to_id = request.data.get("alloted_to")
            alloted_to = CustomUser.objects.get(id=alloted_to_id)

            username = request.data.get("username")
            email = request.data.get("email")

            password = generate_random_password()

            user_serializer = CustomUserSerializer(
                data={
                    "email": email,
                    "username": username,
                    "role": CustomUser.RECRUITER,
                    "credit": 0,
                    "password": password,
                }
            )

            if user_serializer.is_valid(raise_exception=True):
                new_user = user_serializer.save()
                new_user.set_password(password)
                new_user.save()

                RecruiterProfile.objects.create(
                    name=new_user,
                    alloted_to=alloted_to,
                    organization=org,
                )

                org.recruiters.add(new_user)

                send_email_verification_link(
                    new_user, True, "recruiter", password=password
                )

                return Response(
                    {
                        "message": "Recruiter account created successfully, and email sent."
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found for the current user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Assign job post to the recruiter
class AssignRecruiterView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            user = request.user
            org = Organization.objects.get(manager=user)

            job_id = request.data.get("job_id")
            recruiter_map = request.data.get("recruiter_ids", {})

            try:
                job = JobPostings.objects.get(id=job_id, organization=org)
            except JobPostings.DoesNotExist:
                return Response(
                    {"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND
                )

            for location_id_str, recruiter_ids in recruiter_map.items():
                try:
                    location_id = int(location_id_str)
                    job_location = JobLocationsModel.objects.get(
                        id=location_id, job_id=job
                    )

                    old_list = list(
                        AssignedJobs.objects.filter(
                            job_location=job_location
                        ).values_list("assigned_to", flat=True)
                    )
                    incoming_list = recruiter_ids

                    assigned_job, created = AssignedJobs.objects.get_or_create(
                        job_location=job_location, job_id=job
                    )

                    to_add = set(incoming_list) - set(old_list)
                    to_remove = set(old_list) - set(incoming_list)

                    if to_add:
                        recruiters_to_add = CustomUser.objects.filter(
                            id__in=to_add, role="recruiter"
                        )
                        assigned_job.assigned_to.add(*recruiters_to_add)

                        # Notify Client regarding recruiter assignment (Dashboard + Email)
                        recruiter_names = ", ".join(
                            [r.username for r in recruiters_to_add]
                        )
                        client = job.username
                        Notifications.objects.create(
                            sender=request.user,
                            receiver=client,
                            category=Notifications.CategoryChoices.RECRUITER_ASSIGNED_TO_JOB,
                            subject=f"Recruiters Assigned: {job.job_title}",
                            message=f"Recruiters ({recruiter_names}) have been assigned to your job '{job.job_title}' at {job_location.location}.",
                        )
                        send_custom_mail(
                            subject=f"Recruiters Assigned - {job.job_title}",
                            to_email=[client.email],
                            body=f"Hello {client.username},\n\nWe are pleased to inform you that the following recruiters have been assigned to source candidates for your job '{job.job_title}' at {job_location.location}:\n\n{recruiter_names}\n\nGA Hiresync Team",
                        )

                        for recruiter in recruiters_to_add:
                            link = f"{frontend_url}/recruiter/postings/{job_id}"
                            message = f"""
You have been assigned a new job posting.

📌 **Job Title:** {job.job_title}  
🏢 **Client:** {job.username}  
📍 **Location:** {job_location.location}  

Please review the job details and start sourcing profiles for this position.

🔗 [View Job Posting]({link})

Best Regards,  
HireSync Team
"""
                            send_custom_mail(
                                f"New Job Assigned – {job.job_title}",
                                message,
                                {recruiter.email},
                            )

                            Notifications.objects.create(
                                sender=request.user,
                                receiver=recruiter,
                                category=Notifications.CategoryChoices.ASSIGN_JOB,
                                subject="New Job Assigned",
                                message=(
                                    f"📢 New Job Assignment\n\n"
                                    f"You have been assigned a new job:\n\n"
                                    f"Position: {job.job_title}\n"
                                    f"Client: {job.username}\n"
                                    f"Location: {job_location.location}\n\n"
                                    f"Please review and start sourcing candidates.\n\n"
                                    f"id::{job.id} link::recruiter/postings/"
                                ),
                            )

                            job_post_log(
                                job.id,
                                f"Recruiter {recruiter} has been assigned by manager for a job posting {job.job_title} joblocation:{job_location.location}",
                            )

                    # Remove recruiters
                    if to_remove:
                        recruiters_to_remove = CustomUser.objects.filter(
                            id__in=to_remove, role="recruiter"
                        )
                        assigned_job.assigned_to.remove(*recruiters_to_remove)

                        for recruiter in recruiters_to_remove:
                            message = f"""
You have been unassigned from a job posting.

📌 **Job Title:** {job.job_title}  
🏢 **Client:** {job.username}  
📍 **Location:** {job_location.location}  

This change was made by your manager.  
No further action is required from your side for this posting.

Best Regards,  
HireSync Team
"""
                            send_custom_mail(
                                f"Job Unassignment – {job.job_title}",
                                message,
                                {recruiter.email},
                            )

                            Notifications.objects.create(
                                sender=request.user,
                                receiver=recruiter,
                                category=Notifications.CategoryChoices.ASSIGN_JOB,
                                subject="Job Unassigned",
                                message=(
                                    f"🔄 Job Unassignment\n\n"
                                    f"You have been removed from a job posting:\n\n"
                                    f"Position: {job.job_title}\n"
                                    f"Client: {job.username}\n"
                                    f"Location: {job_location.location}\n\n"
                                    f"No further action required.\n\n"
                                    f"id::{job.id} link::recruiter/postings/"
                                ),
                            )
                            job_post_log(
                                job.id,
                                f"Recruiter {recruiter} has been removed for a job posting {job.job_title} by manager joblocation:{job_location.location}",
                            )

                except JobLocationsModel.DoesNotExist:
                    return Response(
                        {"error": "Job location does not exist"},
                        status=status.HTTP_200_OK,
                    )

            return Response(
                {"detail": "Recruiter assignments updated successfully"},
                status=status.HTTP_200_OK,
            )

        except Organization.DoesNotExist:
            return Response(
                {"detail": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AssignRecruiterByLocationView(APIView):
    permission_classes = [IsManager]

    def put(self, request, location_id):
        try:
            location = JobLocationsModel.objects.get(id=location_id)
            recruiter_ids = request.data.get("recruiters", [])

            recruiters = CustomUser.objects.filter(id__in=recruiter_ids)
            if recruiters.count() != len(recruiter_ids):
                return Response(
                    {"error": "One or more recruiter IDs are invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            assigned_job, created = AssignedJobs.objects.get_or_create(
                job_location=location, job_id=location.job_id
            )
            assigned_job.assigned_to.set(recruiter_ids)

            assigned_usernames = ", ".join([r.username for r in recruiters])
            job_post_log(
                location.job_id.id,
                f"Recruiters [{assigned_usernames}] have been assigned by manager for a job posting {location.job_id.job_title} joblocation:{location}",
            )

            return Response(
                {"message": "Recruiters assigned successfully"},
                status=status.HTTP_200_OK,
            )

        except JobLocationsModel.DoesNotExist:
            return Response(
                {"error": "Job location not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruitersList(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "User is not authenticated"},
                    sxxtatus=status.HTTP_400_BAD_REQUEST,
                )

            if request.user.role != "manager":
                return Response(
                    {"error": "You are not allowed to run this view"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            org = Organization.objects.filter(manager=request.user).first()
            if not org:
                print("org not found")
                return Response(
                    {"error": "Organization not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            all_recruiters = RecruiterProfile.objects.filter(organization=org)

            id_list = [
                {
                    "id": recruiter.name.id,
                    "name": recruiter.name.username,
                    "role": "recruiter",
                }
                for recruiter in all_recruiters
            ]

            id_list.append(
                {
                    "id": request.user.id,
                    "name": request.user.username,
                    "role": "manager",
                }
            )

            return Response({"data": id_list}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Invoices
# Get all invoice
class InvoicesAPIView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            organization = Organization.objects.get(manager=request.user)
            jobs = JobPostings.objects.filter(organization=organization).filter(
                status="closed"
            )

            if not jobs.exists():
                return Response({"noJobs": True}, status=status.HTTP_200_OK)

            invoices = []

            for job in jobs:
                print("job", job)
                total = 100
                context = {
                    "agency_name": job.organization.name,
                    "client_name": job.username.username,
                    "client_email": job.username.email,
                    "job_title": job.job_title,
                    "ctc": job.ctc,
                    "service_fee": 23.13,
                    "payment_within": 32,
                    "invoice_id": 10212,
                    "invoice_after": 12,
                    "replacement_clause": 23,
                    "date": 45,
                    "total": total,
                    "email": job.username.email,
                }

                invoice = generate_invoice(context)

                invoices.append(
                    {"invoice": invoice, "job_title": job.job_title, "job_id": job.id}
                )

            return Response({"invoices": invoices}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Close Job
class CloseJobView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            job_id = request.GET.get("id")

            if not job_id:
                return Response(
                    {"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                job = JobPostings.objects.get(id=job_id)
            except JobPostings.DoesNotExist:
                return Response(
                    {"error": "Job Post does not exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job.status = "closed"
            job_applications = (
                JobApplication.objects.filter(job_id=job)
                .exclude(status="selected")
                .exclude(status="rejected")
            )

            for job_application in job_applications:
                job_application.status = "rejected"
                job_application.save()

            job.save()

            # Create notification for invoice generation
            Notifications.objects.create(
                sender=request.user,
                receiver=request.user,
                subject=f"Invoice Generated for {job.job_title}",
                message=f"Invoice has been generated for job {job.job_title}",
                category=Notifications.CategoryChoices.INVOICE_GENERATED,
            )

            # generate invoice here for single job post
            return Response(
                {"message": "Job  Post Closed Successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AgencyJobPosts(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        user = request.user

        try:
            all_jobs = JobPostings.objects.filter(
                organization__manager=user, approval_status="accepted"
            ).select_related("username")

            total_postings = 0
            num_of_open_jobs = 0
            pending_approval = 0
            expired_jobs = 0
            closed_positions = 0

            jobs_list = []
            for job in all_jobs:
                job_postings = JobApplication.objects.filter(
                    job_location__job_id=job.id
                )
                applied = job_postings.count()
                under_review = job_postings.filter(status="processing").count()
                hired = job_postings.filter(status="selected").count()
                rejected = job_postings.filter(status="rejected").count()

                num_of_rounds = job.rounds_of_interview
                rounds_details = []

                num_of_positions = 0
                locations_list = JobLocationsModel.objects.filter(job_id=job)
                for location in locations_list:
                    num_of_positions += location.positions

                # Candidate Status Counts
                applied_count = job_postings.count()  # Total Profiles Sent
                shortlisted_count = job_postings.filter(
                    status="processing", round_num=1
                ).count()
                processing_count = job_postings.filter(
                    status="processing", round_num__gt=1
                ).count()
                on_hold_count = job_postings.filter(status="hold").count()
                rejected_count = job_postings.filter(status="rejected").count()
                selected_count = job_postings.filter(status="selected").count()

                candidate_counts = {
                    "Applied": applied_count,
                    "Shortlisted": shortlisted_count,
                    "Processing": processing_count,
                    "on-Hold": on_hold_count,
                    "Rejected": rejected_count,
                    "Selected": selected_count,
                }

                num_of_rounds = job.rounds_of_interview
                rounds_details = [
                    {"Vacancies": num_of_positions},
                    {"Applied": applied_count},
                    {"Processing": processing_count},
                ]

                for round_num in range(1, num_of_rounds + 1):
                    count = job_postings.filter(
                        round_num=round_num, status="processing"
                    ).count()
                    rounds_details.append({f"Interview Round {round_num}": count})

                rounds_details.extend(
                    [{"Hired": selected_count}, {"Rejected": rejected_count}]
                )

                locations_assigned_to = AssignedJobs.objects.filter(job_id=job)
                assigned_to = {}
                is_any_assigned = locations_assigned_to.exists()

                for location in locations_list:
                    recruiters = locations_assigned_to.filter(job_location=location)
                    recruiter_list = []

                    for recruiter in recruiters:
                        for user in recruiter.assigned_to.all():
                            applications_count = JobApplication.objects.filter(
                                attached_to=user, job_location=location
                            ).count()
                            profile_url = (
                                request.build_absolute_uri(user.profile.url)
                                if user.profile
                                else None
                            )
                            recruiter_list.append(
                                [user.username, applications_count, profile_url]
                            )

                    assigned_to[location.location] = recruiter_list

                client = ClientDetails.objects.get(user=job.username)

                primary_skills = job.skills.filter(is_primary=True)
                secondary_skills = job.skills.filter(is_primary=False)

                p_skills = [
                    {
                        "skill_name": s.skill_name,
                        "metric_value": s.metric_value,
                        "metric_type": s.metric_type,
                    }
                    for s in primary_skills
                ]
                s_skills = [
                    {
                        "skill_name": s.skill_name,
                        "metric_value": s.metric_value,
                        "metric_type": s.metric_type,
                    }
                    for s in secondary_skills
                ]

                job_logs = list(
                    job.logs.all()
                    .values("message", "created_at")
                    .order_by("-created_at")
                )

                interviewers = InterviewerDetails.objects.filter(
                    job_id=job
                ).select_related("name")
                interview_panel = []
                for inter in interviewers:
                    profile_url = (
                        request.build_absolute_uri(inter.name.profile.url)
                        if inter.name.profile
                        else None
                    )
                    interview_panel.append(
                        {
                            "name": inter.name.username,
                            "type": inter.type_of_interview,
                            "mode": inter.mode_of_interview,
                            "round": inter.round_num,
                            "avatar": profile_url,
                        }
                    )

                is_under_negotiation = (
                    JobPostingsEditedVersion.objects.filter(
                        job_id=job, status="pending"
                    )
                    .exclude(user=job.organization.manager)
                    .exists()
                )

                if job.approval_status == "rejected":
                    rec_status = "rejected"
                elif job.status == "closed":
                    rec_status = "closed"
                elif is_under_negotiation:
                    rec_status = "under-negotiation"
                elif is_any_assigned:
                    rec_status = "assigned"
                else:
                    rec_status = "New"

                job_details = {
                    "job_id": job.jobcode,
                    "job_title": job.job_title,
                    "job_description": job.job_description,
                    "assigned_to": assigned_to,
                    "recruitment_status": rec_status,
                    "client_name": (
                        job.username.username if job.username else "Unknown"
                    ),
                    "organization_name": client.name_of_organization,
                    "deadline": job.job_close_duration,
                    "status": job.status,
                    "approval_status": job.approval_status,
                    "vacancies": num_of_positions,
                    "location": (
                        location.location if "location" in locals() else "Multiple"
                    ),
                    "id": job.id,
                    "rounds_details": rounds_details,
                    "candidate_counts": candidate_counts,
                    "created_at": job.created_at,
                    "is_posted_on_linkedin": job.is_linkedin_posted,
                    "job_department": job.job_department,
                    "years_of_experience": job.years_of_experience,
                    "ctc": job.ctc,
                    "job_type": job.job_type,
                    "job_level": job.job_level,
                    "qualifications": job.qualifications,
                    "timings": job.timings,
                    "other_benefits": job.other_benefits,
                    "working_days_per_week": job.working_days_per_week,
                    "decision_maker": job.decision_maker,
                    "decision_maker_email": job.decision_maker_email,
                    "bond": job.bond,
                    "rotational_shift": job.rotational_shift,
                    "age": job.age,
                    "gender": job.gender,
                    "visa_status": job.visa_status,
                    "passport_availability": job.passport_availability,
                    "notice_period": job.notice_period,
                    "notice_time": job.notice_time,
                    "industry": job.industry,
                    "languages": job.languages,
                    "job_logs": job_logs,
                    "interview_panel": interview_panel,
                    "primary_skills": p_skills,
                    "secondary_skills": s_skills,
                }
                jobs_list.append(job_details)
                total_postings += num_of_positions

                if job.approval_status == "pending":
                    pending_approval += 1

                if job.status == "opened":
                    num_of_open_jobs += 1

                if job.job_close_duration < timezone.now().date():
                    expired_jobs += 1

                applications_closed = job_postings.filter(status="selected").count()
                closed_positions += applications_closed

            org_jobs = {
                "new_positions": total_postings,
                "open_job_posts": num_of_open_jobs,
                "active_job_posts": num_of_open_jobs,
                "pending_approval": pending_approval,
                "closed_positions": closed_positions,
                "expired_posts": expired_jobs,
            }

            return Response(
                {"data": jobs_list, "org_jobs": org_jobs}, status=status.HTTP_200_OK
            )

        except ObjectDoesNotExist:
            return Response(
                {"error": "No job postings found for the manager."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            print(str(e))
            return Response(
                {"error": f"Something went wrong: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AllRecruitersView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            organization = Organization.objects.get(manager=user)
            recruiters = organization.recruiters.all()

            recruiters_list = []
            for recruiter in recruiters:
                recruiter_json = {
                    "name": recruiter.username,
                    "email": recruiter.email,
                    "phone": "",
                    "profile": "",
                    "id": recruiter.id,
                }
                recruiters_list.append(recruiter_json)
            return Response(
                {
                    "data": recruiters_list,
                    "can_add_recruiter": can_add_recruiter(organization.id),
                },
                status=status.HTTP_200_OK,
            )

        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization with that id doesnot exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruiterTaskTrackingView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            job_data = []

            job_postings = JobPostings.objects.filter(organization__manager=user)
            job_locations = JobLocationsModel.objects.filter(job_id__in=job_postings)
            current_time = now().date()

            for job in job_locations:

                job_close_duration = job.job_id.job_close_duration

                if current_time > job_close_duration - timedelta(days=5):
                    priority = "high"
                elif current_time > job_close_duration - timedelta(days=10):
                    priority = "medium"
                else:
                    priority = "low"

                jobs_closed = JobApplication.objects.filter(
                    job_location=job.id, status="selected"
                ).count()
                status_percentage = (
                    (jobs_closed / job.positions * 100) if job.positions > 0 else 0
                )
                assigned_to = AssignedJobs.objects.filter(job_location=job).values_list(
                    "assigned_to__username", flat=True
                )

                job_json = {
                    "job_title": job.job_id.job_title,
                    "num_of_positions": job.positions,
                    "priority": priority,
                    "due_date": job_close_duration,
                    "status": round(status_percentage, 2),
                    "recruiters": assigned_to,
                    "location": job.location,
                    "created_at": job.job_id.created_at,
                    "job_status": job.job_id.status,
                }
                job_data.append(job_json)

            try:
                organization = Organization.objects.get(manager=user)
            except Organization.DoesNotExist:
                return Response(
                    {"error": "No organization found for this manager"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            all_recruiters = organization.recruiters.all()
            recruiters_list = [
                {"name": recruiter.username} for recruiter in all_recruiters
            ]

            recent_activities = []
            applications = JobApplication.objects.filter(
                attached_to__in=all_recruiters
            ).order_by("-updated_at")[:6]
            for application in applications:
                job = application.job_location.job_id
                task = ""
                if application.status == "pending":
                    task = f"{application.resume.candidate_name}'s Resume is sent to {job.job_title}"
                elif application.status == "processing" and application.next_interview:
                    task = (
                        f"New meeting scheduled for {application.resume.candidate_name}"
                    )

                time_diff = now() - application.updated_at

                if time_diff.seconds < 60:
                    thumbnail = f"Updated {time_diff.seconds} seconds ago"
                elif time_diff.seconds < 3600:
                    thumbnail = f"Updated {time_diff.seconds // 60} minutes ago"
                elif time_diff.seconds < 86400:
                    thumbnail = f"Updated {time_diff.seconds // 3600} hours ago"
                else:
                    thumbnail = f"Updated {time_diff.days} days ago"

                recent_activities.append(
                    {
                        "name": application.attached_to.username,
                        "job_title": job.job_title,
                        "task": task,
                        "thumbnail": thumbnail,
                    }
                )

            five_days_ago = datetime.now() - timedelta(days=5)
            new_jobs = job_postings.filter(created_at__gte=five_days_ago).count()
            on_going = job_postings.filter(status="opened").count()

            completed_posts = 0
            completed_deadline = 0
            completed_jobs = job_postings.filter(status="closed")

            for job in completed_jobs:
                job_locations = JobLocationsModel.objects.filter(job_id=job)
                total_positions = (
                    job_locations.aggregate(total=Sum("positions"))["total"] or 0
                )
                positions_closed = JobApplication.objects.filter(
                    job_location__in=job_locations, status="selected"
                ).count()
                if positions_closed >= total_positions:
                    completed_posts += 1
                else:
                    completed_deadline += 1

            main_components = {
                "new": new_jobs,
                "on_going": on_going,
                "completed_posts": completed_posts,
                "completed_deadline": completed_deadline,
            }

            return Response(
                {
                    "job_data": job_data,
                    "recruiters_list": recruiters_list,
                    "recent_activities": recent_activities,
                    "main_components": main_components,
                },
                status=status.HTTP_200_OK,
            )

        except ObjectDoesNotExist as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response(
                {"error": f"Unexpected error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ViewSelectedCandidates(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            selected_candidates_list = []
            applications = JobApplication.objects.filter(
                job_location__job_id__organization__manager=user, status="selected"
            )
            selected_candidates = SelectedCandidates.objects.filter(
                application__in=applications
            )
            for candidate in selected_candidates:
                job = candidate.application.job_location.job_id
                candidate_json = {
                    "candidate_name": candidate.candidate.name.username,
                    "joining_date": candidate.joining_date,
                    "joining_status": candidate.joining_status,
                    "accepted_ctc": candidate.ctc,
                    "candidate_acceptance": candidate.candidate_acceptance,
                    "candidate_joining_status": candidate.joining_status,
                    "actual_ctc": job.ctc,
                    "client_name": job.username.username,
                    "job_title": job.job_title,
                    "location": candidate.application.job_location.location,
                    "id": job.id,
                }
                selected_candidates_list.append(candidate_json)

            return Response(selected_candidates_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Unexpected error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AccountantsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            organization = Organization.objects.get(manager=request.user)
            accountants = Accountants.objects.filter(organization=organization)
            if not accountants.exists():
                return Response(
                    {"message": "No accountants found for this organization"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = AccountantsSerializer(accountants, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Manager does not belong to any organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request):
        email = request.data.get("email")
        username = request.data.get("username")

        if not email or not username:
            return Response(
                {"error": "Email and Username are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {"error": "Email is already taken"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            organization = Organization.objects.get(manager=request.user)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Manager does not belong to an organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.create_user(
                username=username, email=email, password=None, role="accountant"
            )

            accountant = Accountants.objects.create(
                user=user, email=email, username=username, organization=organization
            )

            return Response(
                {"success": f"Accountant {username} created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to create accountant. {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrganizationView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
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

            return Response(organization_data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    # def put(self, request):
    #     try:
    #         user = request.user
    #         organization = Organization.objects.get(manager=user)
    #         data = request.data

    #         organization.name = data.get('name_of_organization', organization.name)
    #         organization.contact_number = data.get('contact_number', organization.contact_number)
    #         organization.website_url = data.get('website_url', organization.website_url)
    #         organization.company_address = data.get('company_address', organization.company_address)

    #         organization.save()
    #         return Response({"message": "Organization details updated successfully"}, status=status.HTTP_200_OK)

    #     except ObjectDoesNotExist:
    #          return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            edit_job = 0
            invoice_generated = 0

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
                elif alert.category == Notifications.CategoryChoices.EDIT_JOB:
                    edit_job += 1
                elif alert.category == Notifications.CategoryChoices.INVOICE_GENERATED:
                    invoice_generated += 1

            # Calculate job-related counts
            organization = Organization.objects.get(manager=request.user)
            my_jobs = JobPostings.objects.filter(
                organization=organization, status="Open"
            ).count()

            not_assigned = (
                JobPostings.objects.filter(organization=organization, status="Open")
                .annotate(recruiter_count=Count("assignedjobs"))
                .filter(recruiter_count=0)
                .count()
            )

            closed_hold = JobPostings.objects.filter(
                organization=organization, status__in=["closed", "on_hold"]
            ).count()

            analytics = 0  # Placeholder as per requirement

            data = {
                "negotiate_terms": negotiate_terms,
                "create_job": create_job,
                "accept_job_edit": accept_job_edit,
                "reject_job_edit": reject_job_edit,
                "partial_edit": partial_edit,
                "edit_job": edit_job,
                "invoice_generated": invoice_generated,
                "total_alerts": all_alerts.count(),
                "my_jobs": my_jobs,
                "not_assigned": not_assigned,
                "closed_hold": closed_hold,
                "analytics": analytics,
            }

            return Response({"data": data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClientsData(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        print("=== ClientsData API HIT ===")
        print("Manager:", request.user)
        # print("Client ID received:", id)

        try:
            user = request.user
            client_id = request.query_params.get("id")

            # ================= SINGLE CLIENT =================
            if client_id:
                print("Fetching single client data...")

                try:
                    client = ClientDetails.objects.filter(id=client_id).first()
                    print("Client object:", client)

                    if not client:
                        print("Client NOT FOUND")
                        return Response({"error": "Client not found"}, status=404)

                    jobs = JobPostings.objects.filter(
                        username=client.user, organization__manager=user
                    )
                    print("Jobs found:", jobs.count())

                    associated_at = jobs.order_by("created_at").first()
                    print("Associated at:", associated_at)

                    total_positions = (
                        JobLocationsModel.objects.filter(job_id__in=jobs).aggregate(
                            total=Sum("positions")
                        )["total"]
                        or 0
                    )
                    print("Total positions:", total_positions)

                    client_data = {
                        "client_username": client.username,
                        "organization_name": client.name_of_organization,
                        "contact_number": client.contact_number,
                        "website_url": client.website_url,
                        "gst_number": client.gst_number,
                        "company_address": client.company_address,
                        "associated_at": (
                            associated_at.created_at if associated_at else None
                        ),
                        "designation": client.designation,
                        "pan": client.company_pan,
                        "gst": client.gst_number,
                    }
                    # print("client data",client_data)

                    jobs_data = []
                    for job in jobs:
                        print("Processing job:", job.id, job.job_title)

                        locations = JobLocationsModel.objects.filter(job_id=job)
                        print("Locations count:", locations.count())

                        for location in locations:
                            print("Location ID:", location.id)

                            applications = JobApplication.objects.filter(
                                job_location=location
                            )
                            print("Applications:", applications.count())

                            selected_application = SelectedCandidates.objects.filter(
                                application__in=applications
                            )
                            print(
                                "Selected candidates:",
                                selected_application.count(),
                            )

                            jobs_data.append(
                                {
                                    "openings": location.positions,
                                    "pending": applications.filter(
                                        status="pending"
                                    ).count(),
                                    "processing": applications.filter(
                                        status="processing"
                                    ).count(),
                                    "rejected": applications.filter(
                                        status="rejected"
                                    ).count(),
                                    "joined": selected_application.filter(
                                        joining_status="joined"
                                    ).count(),
                                    "selected": selected_application.filter(
                                        joining_status="pending"
                                    ).count(),
                                    "job_title": job.job_title,
                                    "status": job.status,
                                }
                            )

                    # Calculate Stats for the client
                    total_openings = total_positions
                    total_joined = SelectedCandidates.objects.filter(
                        application__job_location__job_id__in=jobs,
                        joining_status="joined",
                    ).count()
                    total_replaced = SelectedCandidates.objects.filter(
                        application__job_location__job_id__in=jobs, is_replaced=True
                    ).count()
                    satisfaction = (
                        (total_joined / total_openings * 100)
                        if total_openings > 0
                        else 0
                    )

                    stats = {
                        "total_openings": total_openings,
                        "total_joined": total_joined,
                        "total_replaced": total_replaced,
                        "satisfaction": round(satisfaction, 2),
                    }

                    print("Single client response ready")
                    return Response(
                        {
                            "client_data": client_data,
                            "jobs_data": jobs_data,
                            "stats": stats,
                        },
                        status=status.HTTP_200_OK,
                    )

                except Exception as e:
                    print("ERROR in single client block:", str(e))
                    return Response({"error": str(e)}, status=500)

            # ================= ALL CLIENTS =================
            print("Fetching ALL clients for manager")

            jobs = JobPostings.objects.filter(organization__manager=user).order_by(
                "created_at"
            )
            print("Total jobs for manager:", jobs.count())

            org_cients = ClientOrganizations.objects.filter(
                organization__manager=request.user, approval_status="accepted"
            )
            print("Accepted clients:", org_cients.count())

            requests = ClientOrganizations.objects.filter(
                organization__manager=request.user, approval_status="pending"
            )
            print("Pending requests:", requests.count())

            requests_list = []
            for connection_request in requests:
                print("Pending request ID:", connection_request.id)

                requests_list.append(
                    {
                        "company_name": connection_request.client.name_of_organization,
                        "client_name": connection_request.client.user.username,
                        "client_email": connection_request.client.user.email,
                        "id": connection_request.id,
                    }
                )

            data = []
            for connection in org_cients:
                client = connection.client
                print("Processing client:", client.username)

                client_data = {
                    "client_id": client.id,
                    "client_username": client.username,
                    "organization_name": client.name_of_organization,
                    "contact_number": client.contact_number,
                    "website_url": client.website_url,
                    "gst_number": client.gst_number,
                    "company_address": client.company_address,
                    "associated_at": connection.created_at,
                    "negotiation_requested_on": None,
                    "negotiation_accepted_on": None,
                    "negotiations_request": None,
                }

                negotiation = NegotiationRequests.objects.filter(
                    client_organization__client=client
                ).first()

                print("Negotiation object:", negotiation)

                if negotiation:
                    client_data.update(
                        {
                            "negotiation_requested_on": negotiation.requested_date,
                            "negotiation_accepted_on": negotiation.accepted_date,
                            "negotiations_request": {
                                "ctc_range": negotiation.ctc_range,
                                "service_fee": negotiation.service_fee,
                                "replacement_clause": negotiation.replacement_clause,
                                "interest_percentage": negotiation.interest_percentage,
                                "invoice_after": negotiation.invoice_after,
                                "payment_within": negotiation.payment_within,
                                "status": negotiation.status,
                            },
                        }
                    )

                data.append(client_data)

            print("All clients response ready")
            return Response(
                {"data": data, "connection_requests": requests_list},
                status=200,
            )

        except Exception as e:
            print("UNEXPECTED ERROR:", str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ClientCommunicationsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            client_id = request.query_params.get("client_id")
            if not client_id:
                return Response({"error": "client_id is required"}, status=400)

            client = ClientDetails.objects.filter(id=client_id).first()
            if not client:
                return Response({"error": "Client not found"}, status=404)

            client_user = client.user

            # 1. Fetch Notifications
            notifications = Notifications.objects.filter(
                Q(sender=client_user) | Q(receiver=client_user)
            ).order_by("-created_at")

            # 2. Fetch JobPostLogs
            job_post_logs = JobPostLog.objects.filter(
                job_post__username=client_user
            ).order_by("-created_at")

            # 3. Fetch JobProfileLogs
            job_profile_logs = JobProfileLog.objects.filter(
                job_profile__job_location__job_id__username=client_user
            ).order_by("-created_at")

            # 4. Fetch InterviewLogs
            interview_logs = InterviewLog.objects.filter(
                interview__application__job_location__job_id__username=client_user
            ).order_by("-created_at")

            # Aggregate events
            events = []

            for n in notifications:
                events.append(
                    {
                        "type": "Notification",
                        "subject": n.subject,
                        "message": n.message,
                        "timestamp": n.created_at,
                        "category": n.category,
                        "sender": n.sender.username if n.sender else "System",
                    }
                )

            for log in job_post_logs:
                events.append(
                    {
                        "type": "Job Log",
                        "subject": f"Job: {log.job_post.job_title}",
                        "message": log.message,
                        "timestamp": log.created_at,
                        "sender": "System",
                    }
                )

            for log in job_profile_logs:
                events.append(
                    {
                        "type": "Application Log",
                        "subject": f"Candidate: {log.job_profile.resume.candidate_name}",
                        "message": log.message,
                        "timestamp": log.created_at,
                        "sender": "System",
                    }
                )

            for log in interview_logs:
                events.append(
                    {
                        "type": "Interview Log",
                        "subject": f"Round {log.interview.round_num} - {log.interview.application.resume.candidate_name}",
                        "message": log.message,
                        "timestamp": log.created_at,
                        "sender": "System",
                    }
                )

            # Sort events by timestamp descending
            events.sort(key=lambda x: x["timestamp"], reverse=True)

            return Response({"events": events}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class RejectApprovalClient(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            connection_id = request.data.get("request_id")
            reason = request.data.get("reason")
            if not connection_id:
                connection_id = request.GET.get("connection_id")

            connection = ClientOrganizations.objects.get(id=connection_id)
            connection.approval_status = "rejected"
            connection.save()

            Notifications.objects.create(
                sender=request.user,
                receiver=connection.client.user,
                category=Notifications.CategoryChoices.REJECT_JOB,
                subject=f"Collaboration Request Rejected by {request.user.username}",
                message=(
                    f"Collaboration Request Rejected\n\n"
                    f"Your request to collaborate with **{request.user.username}** has been rejected.\n\n"
                    f"Reason:\n{reason}\n\n"
                    f"Please contact the agency for more details."
                ),
            )

            return Response(
                {"message": "Rejected successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AcceptApprovalClient(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            connection_id = request.GET.get("connection_id")
            if not connection_id:
                return Response(
                    {"error": "Missing connection_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                connection = ClientOrganizations.objects.get(id=connection_id)
            except ClientOrganizations.DoesNotExist:
                return Response(
                    {"error": "Invalid connection_id"}, status=status.HTTP_404_NOT_FOUND
                )
            connection = ClientOrganizations.objects.get(id=connection_id)

            terms_list = request.data.get("terms")
            if not isinstance(terms_list, list):
                return Response(
                    {"error": "Expected a list of terms"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                connection.approval_status = "accepted"
                connection.save()
                for terms in terms_list:
                    print(terms.get("service_fee_type"), terms)
                    try:
                        raw_fee = terms.get("service_fee")
                        service_fee = (
                            Decimal(str(raw_fee))
                            if raw_fee is not None
                            else Decimal("0.00")
                        )
                        print(service_fee)
                    except InvalidOperation:
                        return Response(
                            {"error": f"Invalid service_fee value: {raw_fee}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    ClientOrganizationTerms.objects.create(
                        client_organization=connection,
                        service_fee_type=terms.get("service_fee_type"),
                        ctc_range=terms.get("ctc_range"),
                        service_fee=service_fee,
                        replacement_clause=terms.get("replacement_clause"),
                        invoice_after=terms.get("invoice_after"),
                        payment_within=terms.get("payment_within"),
                        interest_percentage=terms.get("interest_percentage"),
                    )
                    Notifications.objects.create(
                        sender=request.user,
                        receiver=connection.client.user,
                        category=Notifications.CategoryChoices.ACCEPT_CONNECTION,
                        subject=f"Connection Request Accepted by {request.user.username}",
                        message=(
                            f"Connection Request Accepted\n\n"
                            f"Manager: {request.user.username}\n\n"
                            f"Your connection request has been accepted. "
                            f"You are now successfully connected with the organization."
                        ),
                    )

            return Response(
                {"message": "Accepted successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruiterJobsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            recruiter_id = request.GET.get("rec_id")
            recruiter = CustomUser.objects.get(id=recruiter_id)
            recruiter_jobs = AssignedJobs.objects.filter(assigned_to=recruiter)
            job_details_json = []

            if not recruiter_jobs.exists():
                return Response(
                    {"data": None, "recruiters": None}, status=status.HTTP_200_OK
                )

            organization = Organization.objects.get(manager=request.user)

            organization_recruiters = (
                CustomUser.objects.filter(recruiting_organization__in=organization)
                .exclude(id=recruiter.id)
                .distinct()
            )

            recruiters_list = []
            for recruiter in organization_recruiters:
                recruiters_list.append(
                    {"recruiter_name": recruiter.username, "id": recruiter.id}
                )

            for job_location in recruiter_jobs:

                assigned_recruiters = job_location.assigned_to.all()
                assigned_list = []
                for member in assigned_recruiters:
                    assigned_list.append(
                        {"recruiter_name": member.username, "id": member.id}
                    )

                job_details_json.append(
                    {
                        "job_title": job_location.job_id.job_title,
                        "job_id": job_location.job_id.id,
                        "job_locaiton": job_location.job_location,
                        "resumes_sent": JobApplication.objects.filter(
                            job_location__job_id=job_location.id, sender=recruiter
                        ).count(),
                        "assigned_list": assigned_list,
                    }
                )

            return Response(
                {"data": job_details_json, "recruiters": recruiters_list},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveRecruiter(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            rec_id = request.GET.get("rec_id")
            if not rec_id:
                return Response(
                    {"error": "Recruiter ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

                    applications = JobApplication.objects.filter(
                        job_id=job.id, attached_to=recruiter_to_remove
                    )
                    for application in applications:
                        application.attached_to = new_recruiter
                        application.save()

                    # write email functionality here
                    receiver = new_recruiter.email
                    subject = f"Job post reassigned to you "
                    message = """
THis is the new job post reassigned to you
"""
                    send_custom_mail(subject=subject, body=message, to_email=[receiver])

                recruiter_to_remove.delete()

            return Response(
                {"message": "Recruiter removed and jobs reassigned successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print("Error in RemoveRecruiter:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PostOnLinkedIn(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            job_id = request.GET.get("job_id")
            if not job_id:
                return Response(
                    {"error": "Job Id required"}, status=status.HTTP_400_BAD_REQUEST
                )
            job = JobPostings.objects.get(id=job_id)
            if job.approval_status == False:
                return Response(
                    {"error": "Job must be approved before posting it on linkedin"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if job.is_linkedin_posted:
                return Response(
                    {"error": "Already posted on linkedin"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if job.status == "closed":
                return Response(
                    {"error": "Jobpost is closed, unable to post"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                linkedin_connection = LinkedinIntegrations.objects.get(
                    agency__manager=request.user
                )
            except Exception as e:
                return Response(
                    {
                        "error": "You are not connected to linkedin, go to profile and add your account"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if linkedin_connection.token_expires_at <= timezone.now():
                return Response(
                    {
                        "error": "Your LinkedIn session has expired. Please reconnect your account from your profile.",
                        "reason": "TOKEN_EXPIRED",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            token = linkedin_connection.access_token
            urn = linkedin_connection.organization_urn

            job_title = job.job_title
            job_description = job.job_description
            job_primary_skills = SkillMetricsModel.objects.filter(
                job_id=job, is_primary=True
            ).values("id", "skill_name")
            job_secondary_skills = SkillMetricsModel.objects.filter(
                job_id=job, is_primary=False
            ).values("id", "skill_name")
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
                        "shareCommentary": {"text": post_content},
                        "shareMediaCategory": "NONE",  # Use "IMAGE" or "ARTICLE" if needed
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response_org = requests.post(
                "https://api.linkedin.com/v2/ugcPosts", headers=headers, json=data
            )

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
                            "shareCommentary": {"text": post_content},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                }

                response_personal = requests.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers=personal_headers,
                    json=personal_data,
                )

                if response_personal.status_code == 201:
                    job.is_linkedin_posted_personal = True
                    job.save()
                    return Response(
                        {
                            "message": "Successfully posted on LinkedIn Organization and your Personal profile."
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {
                            "message": "Successfully posted on LinkedIn Organization, but failed to post on your Personal profile.",
                            "personal_error_details": response_personal.json(),
                        },
                        status=status.HTTP_200_OK,
                    )

            else:
                return Response(
                    {
                        "error": "Failed to post on LinkedIn",
                        "details": response_org.json(),
                    },
                    status=response_org.status_code,
                )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IsManagerLinkedVerifiedView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            manager = request.user
            try:
                manager_linkedin = LinkedinIntegrations.objects.get(
                    agency__manager=manager
                )
            except LinkedinIntegrations.DoesNotExist:
                return Response({"status": False}, status=status.HTTP_200_OK)

            if (
                manager_linkedin.token_expires_at
                and manager_linkedin.token_expires_at < timezone.now()
            ):

                state = str(manager_linkedin.agency.id)
                auth_url = (
                    f"https://www.linkedin.com/oauth/v2/authorization?"
                    f"response_type=code&client_id={settings.LINKEDIN_CLIENT_ID}"
                    f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
                    f"&scope=w_member_social%20rw_organization_admin%20w_organization_social"
                    f"&state={state}"
                )
                return Response(
                    {
                        "status": False,
                        "expired": True,
                        "auth_url": auth_url,
                        "message": "LinkedIn access token expired. Please re-authenticate.",
                    },
                    status=status.HTTP_200_OK,
                )

            # ✅ Token still valid
            return Response(
                {"status": manager_linkedin.is_linkedin_connected},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print("Error in IsManagerLinkedVerifiedView:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            user = request.user
            agency = Organization.objects.get(manager=user)

            with transaction.atomic():
                try:
                    agency_linkedin = LinkedinIntegrations.objects.get(agency=agency)

                except LinkedinIntegrations.DoesNotExist:
                    agency_linkedin = LinkedinIntegrations.objects.create(
                        agency=agency,
                    )

                state = str(agency.id)
                request.session["linkedin_auth_state"] = state

                LINKEDIN_REDIRECT_URI = (
                    f"{os.environ.get('frontendurl')}/linkedin/callback"
                )

                auth_url = (
                    f"https://www.linkedin.com/oauth/v2/authorization?"
                    f"response_type=code&client_id={settings.LINKEDIN_CLIENT_ID}"
                    f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
                    f"&scope=w_member_social%20rw_organization_admin%20w_organization_social"
                    f"&state={agency.id}"
                )
                return Response({"url": auth_url}, status=status.HTTP_200_OK)

        except Exception as e:
            print("Error in RemoveRecruiter:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LinkedINCallBackView(APIView):
    def get(self, request):
        try:
            code = request.GET.get("code")
            agency_id = request.GET.get("state")
            error = request.GET.get("error")

            if error:
                return Response(
                    {"message": "Authorization denied by user.", "status": False},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not code or not agency_id:
                return Response(
                    {
                        "message": "Missing code or state in the request.",
                        "status": False,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
                return Response(
                    {
                        "message": "Failed to retrieve access token from LinkedIn.",
                        "details": token_response.json(),
                        "status": False,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")

            if not access_token:
                return Response(
                    {"message": "Access token not found in response.", "status": False},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch organizations (pages) the user has admin access to
            orgs_response = requests.get(
                "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if orgs_response.status_code != 200:
                return Response(
                    {
                        "message": "Failed to fetch LinkedIn organizations.",
                        "details": orgs_response.json(),
                        "status": False,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            org_data = orgs_response.json()
            elements = org_data.get("elements", [])

            if not elements:
                return Response(
                    {
                        "message": "No LinkedIn Page found for this account.",
                        "reason": "NO_PAGE",
                        "status": False,
                    },
                    status=status.HTTP_200_OK,
                )

            organization_urn = elements[0].get("organizationalTarget")
            if not organization_urn:
                return Response(
                    {"message": "Organization URN not found.", "status": False},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Save token and organization info
            try:
                agency_linkedin = LinkedinIntegrations.objects.get(agency=agency_id)
            except LinkedinIntegrations.DoesNotExist:
                return Response(
                    {
                        "message": "LinkedinIntegration record not found for this agency.",
                        "status": False,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            agency_linkedin.access_token = access_token
            agency_linkedin.token_expires_at = timezone.now() + timedelta(
                seconds=int(expires_in)
            )
            agency_linkedin.organization_urn = organization_urn
            agency_linkedin.is_linkedin_connected = True
            agency_linkedin.save()

            return Response(
                {
                    "message": "Agency connected to LinkedIn successfully.",
                    "status": True,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print("Callback Error:", str(e))
            return Response(
                {
                    "message": "Unexpected error occurred.",
                    "error": str(e),
                    "status": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class RecSummaryMetrics(APIView):
    permission_classes = [IsManager]

    def get(self, request, *args, **kwargs):
        rctr_id = request.GET.get("rctr_id")

        try:
            rctr_obj = CustomUser.objects.get(id=rctr_id)
        except ObjectDoesNotExist:
            return Response({"error": "Recruiter not found"}, status=404)

        jobs_assigned = AssignedJobs.objects.filter(assigned_to=rctr_obj)
        total_jobs_assigned = jobs_assigned.count()

        interviews = InterviewSchedule.objects.filter(rctr=rctr_obj)
        interviews_count = interviews.count()

        applications = JobApplication.objects.filter(attached_to=rctr_obj)
        applications_count = applications.count()

        selected_candidates = SelectedCandidates.objects.filter(
            application__attached_to=rctr_id
        )

        pending_candidates_count = selected_candidates.filter(
            joining_status="pending"
        ).count()

        joined_candidates_count = selected_candidates.filter(
            joining_status="joined"
        ).count()

        candidates_on_processing = applications.filter(status="processing")[:10]
        candidates_data = []
        for candidate in candidates_on_processing:

            candidates_data.append(
                {
                    "candidate_name": candidate.resume.candidate_name,
                    "role": candidate.job_location.job_id.job_title,
                    "status": candidate.status,
                    "profile": None,
                }
            )

        cards_data = {
            "application_count": applications_count,
            "interviews_count": interviews_count,
            "job_postings_count": total_jobs_assigned,
            "pending_candidates_count": pending_candidates_count,
            "joined_candidates_count": joined_candidates_count,
        }

        interview_data = []
        for interview in interviews:
            interview_data.append(
                {
                    "scheduled_date": interview.scheduled_date,
                    "profile": (
                        interview.interviewer.name.profile.url
                        if interview.interviewer.name.profile
                        else None
                    ),
                    "job_title": interview.job_location.job_id.job_title,
                    "scheduled_time": f"{interview.from_time} - {interview.to_time}",
                    "candidate_name": interview.candidate.candidate_name,
                    "from_time": interview.from_time,
                    "to_time": interview.to_time,
                    "round_num": interview.round_num,
                    "id": interview.id,
                    "interviewer_name": interview.interviewer.name.username,
                }
            )

        job_data = []
        for assigned_job in jobs_assigned:
            applications = JobApplication.objects.filter(
                job_location=assigned_job.job_location
            )
            job = assigned_job.job_id
            job_location = assigned_job.job_location
            joined = 0
            for application in applications:
                try:
                    selected_candidate = SelectedCandidates.objects.get(
                        application=application, joining_status="joined"
                    )
                    joined += 1
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

        return Response(
            {
                "cards_data": cards_data,
                "on_processing": candidates_data,
                "interviews": interview_data,
                "jobs_data": job_data,
            },
            status=status.HTTP_200_OK,
        )


class ManagerResumeBankView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            applications = JobApplication.all_objects.filter(
                job_location__job_id__organization__manager=request.user
            ).select_related("resume", "job_location__job_id")

            candidate_data = {}

            for app in applications:
                email = app.resume.candidate_email

                if email not in candidate_data:
                    candidate_data[email] = {
                        "resume": app.resume.resume.url if app.resume.resume else None,
                        "candidate_name": app.resume.candidate_name,
                        "candidate_email": email,
                        "job_count": 0,
                        "jobs": [],
                    }

                candidate_data[email]["job_count"] += 1
                candidate_data[email]["jobs"].append(
                    {
                        "job_title": app.job_location.job_id.job_title,
                        "status": app.status,
                    }
                )

            candidate_data = list(candidate_data.values())
            paginator = TenResultsPagination()
            page = paginator.paginate_queryset(candidate_data, request)

            recruiters = list(
                Organization.objects.get(manager=request.user).recruiters.values_list(
                    "email", "username"
                )
            )

            applications_list = []
            for application in applications:
                application_status = application.status
                if application_status == "selected":
                    try:
                        application_status = SelectedCandidates.objects.get(
                            application=application
                        ).joining_status
                    except SelectedCandidates.DoesNotExist:
                        pass
                applications_list.append(
                    {
                        "status": application_status,
                        "attached_to": application.attached_to.email,
                    }
                )

            selectedPlan = OrganizationPlan.objects.get(
                organization__manager=request.user
            ).plan
            storage_feature = PlanFeature.objects.get(
                feature__code="storage", plan=selectedPlan
            )
            storage_limit = storage_feature.limit

            return paginator.get_paginated_response(
                {
                    "resumes": page,
                    "storage": get_resume_storage_usage(request.user),
                    "applications": applications_list,
                    "recruiters": recruiters,
                    "storage_limit": storage_limit,
                }
            )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ConnectionRequests(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            connection_id = request.GET.get("connection_id")
            if connection_id:
                pass

            requests = ClientOrganizations.objects.filter(
                organization__manager=request.user, approval_status="pending"
            )
            requests_list = []
            for connection_request in requests:
                requests_list.append(
                    {
                        "company_name": connection_request.client.name_of_organization,
                        "client_name": connection_request.client.user.username,
                        "client_email": connection_request.client.user.email,
                        "id": connection_request.id,
                    }
                )
            return Response({"data": requests_list}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeleteResumes(APIView):
    permission_classes = [IsManager]

    def delete(self, request):
        try:
            organization = Organization.objects.get(manager=request.user)
            emails = request.data.get("candidate_emails")
            for email in emails:
                with transaction.atomic():
                    applications = JobApplication.all_objects.filter(
                        resume__candidate_email=email,
                        job_location__job_id__organization=organization,
                    )

                    resumes_to_check = [
                        app.resume for app in applications if app.resume
                    ]

                    applications.delete()

                    for resume in resumes_to_check:
                        if resume is None or not resume.resume:
                            continue

                        is_still_used = JobApplication.all_objects.filter(
                            resume=resume
                        ).exists()

                        if not is_still_used:
                            try:
                                file_path = os.path.join(
                                    settings.MEDIA_ROOT, resume.resume.name
                                )
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception as file_err:
                                logger.error(
                                    f"Failed to delete resume file: {file_err}"
                                )

                            resume.delete()

                    remaining_apps = JobApplication.all_objects.filter(
                        resume__candidate_email=email
                    )
                    if not remaining_apps.exists():
                        try:
                            user = CustomUser.objects.get(email=email)
                            user.delete()
                        except ObjectDoesNotExist:
                            pass

            return Response(
                {"message": "Candidates removed successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(str(e))
            return Response(
                {"error": "An error occurred while deleting candidates."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ExtendDeadlineView(APIView):
    permission_classes = [IsManager]

    def put(self, request, id):
        try:
            job = JobPostings.objects.get(id=id)

            if job.organization.manager != request.user:
                return Response(
                    {"error": "You are not eligible to change the deadline"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            extended_time = request.data.get("new_deadline")
            if not extended_time:
                return Response(
                    {"error": "Deadline is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                formatted_date = datetime.strptime(extended_time, "%Y-%m-%d").date()
            except ValueError:
                formatted_date = datetime.fromisoformat(extended_time).date()

            job.extended_deadline = formatted_date
            job.save()

            return Response(
                {"message": "Request sent to client successfully"},
                status=status.HTTP_200_OK,
            )
        except JobPostings.DoesNotExist:
            return Response(
                {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(str(e))
            return Response(
                {"error": "An error occurred while updating deadline."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobsExportCsv(APIView):
    def get(self, request):
        try:
            organization = Organization.objects.get(manager=request.user)
            job_posts = JobPostings.objects.filter(organization=organization)

            client_usernames = job_posts.values_list(
                "username__username", flat=True
            ).distinct()
            clients = ClientDetails.objects.filter(user__username__in=client_usernames)

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="jobs_export.csv"'

            writer = csv.writer(response)
            writer.writerow(
                [
                    "Organization Name",
                    "Client Name",
                    "Client Contact",
                    "Client Email",
                    "Number of Jobs",
                    "Last Job",
                    "Last Collaborated On",
                ]
            )

            for client in clients:
                jobs = job_posts.filter(username=client.user)
                latest_job = jobs.order_by("-created_at").first()
                jobs_count = jobs.count()
                writer.writerow(
                    [
                        client.name_of_organization,
                        client.user.username,
                        client.contact_number,
                        client.user.email,
                        jobs_count,
                        latest_job.job_title if latest_job else "",
                        (
                            latest_job.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if latest_job
                            else ""
                        ),
                    ]
                )

            return response

        except Exception as e:
            logger.error(str(e))
            return Response(
                {"error": "An error occurred while exporting CSV."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HoldJobView(APIView):
    permission_classes = [IsManager]

    def put(self, request, job_id):
        try:
            job = JobPostings.objects.get(id=job_id)

            success = update_job_to_hold(job.id)
            if success:
                return Response(
                    {
                        "message": f"Job '{job.job_title}' and its locations have been put on hold successfully."
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Failed to update one or more locations for this job."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ObjectDoesNotExist:
            logger.error(f"Job with ID {job_id} not found.")
            return Response(
                {"error": "Job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Error while putting job {job_id} on hold: {e}")
            return Response(
                {"error": "An unexpected error occurred while updating the job."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RemoveFromHold(APIView):
    permission_classes = [IsManager]

    def put(self, request, job_id):
        try:
            job = JobPostings.objects.get(id=job_id)
            job.status = "opened"
            job.save()
            return Response(
                {"message": "Job removed from hold successfully"},
                status=status.HTTP_200_OK,
            )
        except ObjectDoesNotExist:
            logger.error(f"Job with ID {job_id} not found.")
            return Response(
                {"error": "Job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Error while putting job {job_id} on hold: {e}")
            return Response(
                {"error": "An unexpected error occurred while updating the job."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OldClientTerms(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            first_connection = (
                ClientOrganizations.objects.filter(organization__manager=request.user)
                .order_by("created_at")
                .first()
            )
            print(first_connection.id, " is the frist connection")
            first_connection_terms = ClientOrganizationTerms.objects.filter(
                client_organization=first_connection.id, is_negotiated=False
            )
            print(first_connection_terms, " are teh terms")
            terms_list = []
            for terms in first_connection_terms:
                terms_list.append(
                    {
                        "service_fee": terms.service_fee,
                        "ctc_range": terms.ctc_range,
                        "service_fee_type": terms.service_fee_type,
                        "interest_percentage": terms.interest_percentage,
                        "replacement_clause": terms.replacement_clause,
                        "payment_within": terms.payment_within,
                        "invoice_after": terms.invoice_after,
                    }
                )

            return Response({"data": terms_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error while fetching the terms: {e}")
            return Response(
                {"error": "An unexpected error occurred while fetching the terms."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AgencyBankDetails(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            organziation = Organization.objects.get(manager=request.user)
            bank_details = {
                "bank_name": organziation.bank_name,
                "bank_holder_name": organziation.bank_holder_name,
                "account_number": organziation.account_number,
                "ifsc_code": organziation.ifsc_code,
                "udaan_number": organziation.udaan_number,
                "msme_number": organziation.msme_number,
            }

            return Response({"data": bank_details}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error while fetching the bank details : {e}")
            return Response(
                {"error": "An unexpected error while fetching the bank details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request):
        try:
            organziation = Organization.objects.get(manager=request.user)
            data = request.data

            organziation.account_number = data.get(
                "account_number", organziation.account_number
            )
            organziation.bank_name = data.get("bank_name", organziation.bank_name)
            organziation.bank_holder_name = data.get(
                "bank_holder_name", organziation.bank_holder_name
            )
            organziation.ifsc_code = data.get("ifsc_code", organziation.ifsc_code)
            organziation.udaan_number = data.get(
                "udaan_number", organziation.udaan_number
            )
            organziation.msme_number = data.get(
                "msme_number", organziation.udaan_number
            )

            organziation.save()

            return Response(
                {"message": "Organization details saved successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception(f"Error while updating the bank details : {e}")
            return Response(
                {"error": "An unexpected error while updating the bank details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClientOrganizationsSeenView(APIView):

    def get(self, request):
        """
        GET -> Return count of unseen ClientOrganizations
        """
        count = ClientOrganizations.objects.filter(
            is_seen=False,  # Only unseen records
            organization__manager=request.user,
            approval_status="pending",
        ).count()
        print("count", count)

        return Response({"unseen_count": count}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        POST -> Mark all unseen ClientOrganizations as seen
        """
        updated = ClientOrganizations.objects.filter(
            is_seen=False, organization__manager=request.user
        ).update(is_seen=True)
        return Response({"updated_records": updated}, status=status.HTTP_200_OK)


class AgencyNavBaarCounts(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        """
        GET -> Return count of unseen nav itemss count
        """

        # here i need count for the ClientOrganizations as shown below and also and pending job posts from the
        all_jobs = JobPostings.objects.filter(
            organization__manager=request.user, approval_status="pending"
        )

        count = ClientOrganizations.objects.filter(
            is_seen=False, organization__manager=request.user, approval_status="pending"
        ).count()
        print("count", count)

        return Response({"unseen_count": count}, status=status.HTTP_200_OK)


class ManagerRecruitersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            # Fetch the organization managed by the current user
            try:
                organization = Organization.objects.get(manager=user)
            except Organization.DoesNotExist:
                return Response(
                    {"error": "Organization not found for this manager"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get recruiters from the organization relation
            recruiters = organization.recruiters.all()

            # Use existing serializer
            serializer = CustomUserSerializer(recruiters, many=True)

            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangeRecruiterView(APIView):
    permission_classes = [IsManager]

    def put(self, request):
        print("hi")


class JobEditByClientView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            request_id = request.GET.get("id")

            if request_id:
                # We need to fetch from JobPostingsEditedVersion now
                try:
                    edit_version = JobPostingsEditedVersion.objects.get(id=request_id)
                except JobPostingsEditedVersion.DoesNotExist:
                    return Response(
                        {"error": "Edit request not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                job = edit_version.job_id

                # Verify Organization Ownership
                if job.organization.manager != user:
                    return Response(
                        {"error": "Unauthorized access to this request"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                from app.serializers import JobPostingsSerializer

                job_serializer = JobPostingsSerializer(job)

                edit_fields = JobPostEditFields.objects.filter(edit_id=edit_version)

                # Transform to a dictionary for the frontend
                filtered_edit_request = {}
                for field in edit_fields:
                    # Attempt to parse JSON if it looks like a list or dict (e.g. job_locations)
                    val = field.field_value
                    if val and (val.startswith("[") or val.startswith("{")):
                        try:
                            import json

                            val = json.loads(val)
                        except:
                            pass
                    filtered_edit_request[field.field_name] = val

                return Response(
                    {"job": job_serializer.data, "edit_request": filtered_edit_request},
                    status=status.HTTP_200_OK,
                )

            else:
                try:
                    organization = Organization.objects.get(manager=user)
                    # Fetch pending edits created by Clients for this organization's jobs
                    edit_requests = JobPostingsEditedVersion.objects.filter(
                        job_id__organization=organization, status="pending"
                    ).exclude(user=user)

                    data = []
                    for req in edit_requests:
                        data.append(
                            {
                                "id": req.id,
                                "job_id": (
                                    req.job_id.jobcode
                                    if hasattr(req.job_id, "jobcode")
                                    else req.job_id.id
                                ),
                                "job_title": req.job_id.job_title,
                                "edited_by": req.user.username,
                                "edited_at": req.created_at,
                                "edit_status": req.status,
                                "edit_reason": "Client Edit Request",
                            }
                        )

                    return Response({"data": data}, status=status.HTTP_200_OK)
                except Organization.DoesNotExist:
                    return Response({"data": []}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e), "traceback": traceback.format_exc()},
                status=status.HTTP_400_BAD_REQUEST,
            )


class JobEditRequestActionView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            request_id = request.data.get("request_id")
            status_update = request.data.get("status")  # 'accepted' or 'rejected'
            accepted_fields = request.data.get(
                "accepted_fields", []
            )  # list of field names if partial

            if not request_id or not status_update:
                return Response(
                    {"error": "request_id and status are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # Use the new model
                edit_version = JobPostingsEditedVersion.objects.get(id=request_id)
            except JobPostingsEditedVersion.DoesNotExist:
                return Response(
                    {"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND
                )

            job = edit_version.job_id

            # Verify Organization Ownership
            if job.organization.manager != request.user:
                return Response(
                    {"error": "Unauthorized access to this request"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            with transaction.atomic():
                if status_update == "rejected":
                    edit_version.status = "rejected"
                    edit_version.save()
                    JobPostEditFields.objects.filter(edit_id=edit_version).update(
                        status="rejected"
                    )

                elif status_update == "accepted":
                    edit_version.status = "accepted"
                    edit_version.save()

                    edit_fields = JobPostEditFields.objects.filter(edit_id=edit_version)

                    fields_to_process = (
                        [f for f in edit_fields if f.field_name in accepted_fields]
                        if accepted_fields
                        else edit_fields
                    )

                    for field in fields_to_process:
                        field_name = field.field_name
                        new_value = field.field_value

                        field.status = "accepted"
                        field.save()

                        if field_name == "job_locations":
                            # Handle Job Locations Update
                            import json

                            try:
                                locations_list = json.loads(new_value)
                                from app.models import JobLocationsModel

                                existing_locations = {
                                    loc.location: loc
                                    for loc in JobLocationsModel.objects.filter(
                                        job_id=job
                                    )
                                }
                                processed_locations = set()

                                for loc_data in locations_list:
                                    loc_name = loc_data.get("location")
                                    if not loc_name:
                                        continue

                                    job_type_val = loc_data.get("job_type", "office")
                                    if job_type_val not in [
                                        "remote",
                                        "hybrid",
                                        "office",
                                    ]:
                                        job_type_val = "office"

                                    pos_val = loc_data.get("positions", 0)

                                    if loc_name in existing_locations:
                                        loc_obj = existing_locations[loc_name]
                                        loc_obj.job_type = job_type_val
                                        loc_obj.positions = pos_val
                                        loc_obj.save()
                                        processed_locations.add(loc_name)
                                    else:
                                        JobLocationsModel.objects.create(
                                            job_id=job,
                                            location=loc_name,
                                            job_type=job_type_val,
                                            positions=pos_val,
                                        )
                                        processed_locations.add(loc_name)

                                # Delete locations that are no longer in the request
                                for loc_name, loc_obj in existing_locations.items():
                                    if loc_name not in processed_locations:
                                        loc_obj.delete()
                            except Exception as loc_e:
                                print(f"Error updating locations: {loc_e}")

                        elif new_value is not None:
                            if hasattr(job, field_name):
                                setattr(job, field_name, new_value)

                # Clear the flag as action is taken
                job.is_edited_by_client = False
                job.save()

            # Send Notifications
            try:
                subject = (
                    f"Job Edit Request {status_update.capitalize()}: {job.job_title}"
                )
                message = f"The manager has {status_update} the edit request for job '{job.job_title}'."
                category = (
                    Notifications.CategoryChoices.ACCEPT_JOB_EDIT
                    if status_update == "accepted"
                    else Notifications.CategoryChoices.REJECT_JOB_EDIT
                )

                create_notification(
                    request.user, job.username, subject, message, category
                )

                recruiters = (
                    AssignedJobs.objects.filter(job_id=job)
                    .values_list("assigned_to", flat=True)
                    .distinct()
                )
                for recruiter_id in recruiters:
                    if recruiter_id:
                        recruiter = CustomUser.objects.get(id=recruiter_id)
                        create_notification(
                            request.user, recruiter, subject, message, category
                        )

                interviewers = (
                    InterviewerDetails.objects.filter(job_id=job)
                    .values_list("name", flat=True)
                    .distinct()
                )
                for interviewer_id in interviewers:
                    if interviewer_id:
                        interviewer = CustomUser.objects.get(id=interviewer_id)
                        create_notification(
                            request.user, interviewer, subject, message, category
                        )
            except Exception as notify_e:
                print(f"Notification Error: {notify_e}")

            return Response(
                {"message": f"Job edit request {status_update}"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e), "traceback": traceback.format_exc()},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AgencyTermsWithClientAgreedView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            print("user :", user)
            client_id = request.query_params.get("id")
            print("client: ", client_id)
            if not client_id:
                # print("id is missing")
                return Response(
                    {"error": "Client ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            client_organization = ClientOrganizations.objects.filter(
                client_id=client_id, organization__manager=user
            ).first()

            if not client_organization:
                return Response(
                    {"error": "Client organisation not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            terms = ClientOrganizationTerms.objects.filter(
                client_organization=client_organization
            )
            terms_data = ClientOrganizationTermsSerializer(terms, many=True).data

            # Include negotiated terms if they exist and are accepted
            try:
                negotiated = NegotiationRequests.objects.filter(
                    client_organization=client_organization, status="accepted"
                ).first()
                if negotiated:
                    today = date.today()
                    # Check if negotiated terms are not expired
                    if not negotiated.expiry_date or negotiated.expiry_date >= today:
                        # Append negotiated terms to the list
                        # Using a manual dict to match the terms format
                        terms_data.append(
                            {
                                "id": negotiated.id,
                                "ctc_range": negotiated.ctc_range,
                                "service_fee": negotiated.service_fee,
                                "service_fee_type": negotiated.service_fee_type,
                                "replacement_clause": negotiated.replacement_clause,
                                "invoice_after": negotiated.invoice_after,
                                "payment_within": negotiated.payment_within,
                                "interest_percentage": negotiated.interest_percentage,
                                "is_negotiated": True,
                                "description": negotiated.description,
                                "connection_id": client_organization.id,
                            }
                        )
            except Exception as neg_e:
                print(f"Error fetching negotiated terms: {neg_e}")

            return Response(
                {"terms": terms_data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ManagerReplacementRequestsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        try:
            user = request.user
            replacements = ReplacementCandidates.objects.filter(
                replacement_with__job_location__job_id__organization__manager=user,
                status="pending_manager_approval",
            ).select_related(
                "replacement_with__job_location__job_id__organization",
                "replacement_with__resume",
                "replacement_with__selected_candidates",
            )

            replacements_list = []
            for replacement in replacements:
                job = replacement.replacement_with.job_location.job_id
                replacements_list.append(
                    {
                        "job_title": job.job_title,
                        "organization_name": job.organization.name,
                        "candidate_name": replacement.replacement_with.resume.candidate_name,
                        "agreed_ctc": getattr(
                            replacement.replacement_with.selected_candidates,
                            "ctc",
                            None,
                        ),
                        "job_id": job.id,
                        "job_location_id": replacement.replacement_with.job_location.id,
                        "joining_date": getattr(
                            replacement.replacement_with.selected_candidates,
                            "joining_date",
                            None,
                        ),
                        "replacement_id": replacement.id,
                        "client_name": job.username.username,
                    }
                )

            return Response(replacements_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReplacementActionView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        try:
            replacement_id = request.data.get("replacement_id")
            action = request.data.get("action")  # 'accept' or 'reject'

            replacement = ReplacementCandidates.objects.get(id=replacement_id)
            selected_candidate = SelectedCandidates.objects.get(
                application=replacement.replacement_with
            )
            job_post = replacement.replacement_with.job_location.job_id
            job_location = replacement.replacement_with.job_location

            if action == "accept":
                with transaction.atomic():
                    replacement.status = "pending"
                    replacement.save()

                    selected_candidate.replacement_status = "pending"
                    selected_candidate.save()

                    job_location.status = "opened"
                    job_location.save()
                    job_post.status = "opened"
                    job_post.save()

                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category=Notifications.CategoryChoices.REPLACEMENT_ACCEPTED,
                        subject=f"Replacement Request Accepted",
                        message=f"Agency manager has accepted your replacement request for {replacement.replacement_with.resume.candidate_name} in job: {job_post.job_title}. The job has been reopened.",
                    )

                    job_post_log(
                        job_post.id,
                        f"Replacement Request for the jobpost :{job_post.job_title} accepted by manager {request.user.username}",
                    )

                return Response(
                    {"message": "Replacement request accepted"},
                    status=status.HTTP_200_OK,
                )

            elif action == "reject":
                with transaction.atomic():
                    reason = request.data.get("reason", "No reason provided")
                    replacement.status = "incomplete"
                    replacement.save()

                    selected_candidate.replacement_status = "no"
                    selected_candidate.save()

                    Notifications.objects.create(
                        sender=request.user,
                        receiver=job_post.username,
                        category=Notifications.CategoryChoices.REPLACEMENT_REJECTED,
                        subject=f"Replacement Request Rejected",
                        message=f"Agency manager has rejected your replacement request for {replacement.replacement_with.resume.candidate_name} in job: {job_post.job_title}. Reason: {reason}",
                    )

                    job_post_log(
                        job_post.id,
                        f"Replacement Request for the jobpost :{job_post.job_title} rejected by manager {request.user.username}. Reason: {reason}",
                    )

                return Response(
                    {"message": "Replacement request rejected"},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

        except ReplacementCandidates.DoesNotExist:
            return Response(
                {"error": "Replacement request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
