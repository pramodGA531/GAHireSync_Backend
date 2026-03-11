from ..models import *
from ..serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist


class JobInterviewCalendarAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id=None):
        user = request.user
        role = user.role

        query = Q()

        # Basic role-based organization/user filtering
        if role == "manager":
            try:
                org = Organization.objects.get(manager=user)
                query &= Q(job_location__job_id__organization=org)
            except Organization.DoesNotExist:
                return Response(
                    {"error": "Organization not found for manager"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif role == "client":
            try:
                # Client is linked via 'username' in JobPostings
                query &= Q(job_location__job_id__username=user)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif role == "interviewer":
            # Interviewer sees assigned interviews
            query &= Q(interviewer__name=user)

        elif role == "recruiter":
            # Recruiter sees interviews they scheduled
            query &= Q(rctr=user)

        else:
            return Response(
                {"error": "Unauthorized role"}, status=status.HTTP_403_FORBIDDEN
            )

        # Apply job_id filter if provided
        if job_id:
            query &= Q(job_location__job_id=job_id)

        interviews = (
            InterviewSchedule.objects.filter(query)
            .select_related("candidate", "interviewer__name", "job_location__job_id")
            .prefetch_related("rctr")
            .distinct()
        )

        interview_data = []
        for interview in interviews:
            interview_data.append(
                {
                    "id": interview.id,
                    "candidate_name": (
                        interview.candidate.candidate_name
                        if interview.candidate
                        else "N/A"
                    ),
                    "interviewer_name": (
                        interview.interviewer.name.username
                        if interview.interviewer
                        else "N/A"
                    ),
                    "round_num": interview.round_num,
                    "status": interview.status,
                    "scheduled_date": interview.scheduled_date.strftime("%Y-%m-%d") if interview.scheduled_date else "1970-01-01",
                    "from_time": interview.from_time.strftime("%H:%M:%S") if interview.from_time else "00:00:00",
                    "to_time": interview.to_time.strftime("%H:%M:%S") if interview.to_time else "00:00:00",
                    "meet_link": interview.meet_link,
                    "job_title": interview.job_location.job_id.job_title if interview.job_location else "N/A",
                    "profile": (
                        interview.interviewer.name.profile.url
                        if interview.interviewer and interview.interviewer.name.profile
                        else None
                    ),
                }
            )

        return Response(interview_data, status=status.HTTP_200_OK)
