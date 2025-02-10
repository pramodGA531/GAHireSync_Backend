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

from django.shortcuts import get_object_or_404
from ..utils import *


# View all the scheduled interviews
class ScheduledInterviewsView(APIView):
    permission_classes = [IsInterviewer]
    
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
   
# Get all the primary skills, secondary skills of the job post , to give the rating

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


# Get Previous Interview Remarks for every candidate
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


# Handling Candidate after completion of interview

# Promote Candidate to next round
class PromoteCandidateView(APIView):
    def post(self, request):
        # print(request.data.get("meet_link"))
        try:
            resume_id = request.GET.get('id')
            round_num = request.GET.get('round_num')
           
            application = JobApplication.objects.get(resume = resume_id)

            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)

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
            application.round_num = round_num+1
            application.next_interview = None
            application.status = 'processing'
            application.save()

            return Response({"message":"Next Interview for this application Scheduled successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

# Reject Candidate 
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

# Directly shortlist the candidate and send the notification to the client, recruiter
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