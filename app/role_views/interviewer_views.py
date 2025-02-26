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
                            "scheduled_date": scheduled_interview.scheduled_date,
                            "from_time": scheduled_interview.from_time,
                            "to_time": scheduled_interview.to_time,
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
                    scheduled_date = interview.scheduled_date
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
                        "schedule_date":scheduled_date,
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

            resume_id = request.GET.get('resume_id')
            print(resume_id)
            application = JobApplication.objects.get(resume__id = resume_id)

            application_round = application.round_num
            job_post_rounds = application.job_id.rounds_of_interview

            if(application_round < job_post_rounds):
                has_next_round = True
            else:
                has_next_round = False

            return Response({"data":skills_json, "has_next_round":has_next_round}, status=status.HTTP_200_OK)

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
            application = JobApplication.objects.get(resume = resume)
            application_id  = application.id
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
            resume_id = int(request.GET.get('id'))
            round_num = int(request.GET.get('round_num'))
            try:
                application = JobApplication.objects.get(resume__id = resume_id)
            except JobApplication.DoesNotExist:
                print("query doesnot exist")
                return Response({"error":"Job application matching query doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)

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
            application.round_num = round_num+1
            application.next_interview = None
            application.status = 'processing'
            application.save()

            return Response({"message":"Candidate promoted to nexts round successfully"},status = status.HTTP_201_CREATED)
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
class SelectCandidate(APIView):
    permission_classes = [IsInterviewer]

    def sendAlert(self, job_id):
        try:
            try:
                job_post = JobPostings.objects.get(id = job_id)
            except JobPostings.DoesNotExist:
                return Response({"error":'Job posting does not exists'},status= status.HTTP_400_BAD_REQUEST)

            client_email = job_post.username.email
            manager_email = job_post.organization.manager.email
            recruiters_emails = job_post.assigned_to.values_list('email', flat=True)

            subject = f"JOB POST {job_post.job_title} ALL OPENINGS ARE COMPLETED"
            client_message = '''
All openings of the given job post are completed successfully,
If you want to recruit more people for the same job post , please go through the below link and give the number of positions you want
link here

Thankyou for choosing hiresync,
Best Regards, 
Kalki,
HireSync.
'''         

            organization_recruiters_message = f'''
All openings for the job post {job_post.job_title} are filled successfully
Client will inform you if they want more job posts
Thank you for choosing hiresync

Best Regards,
Kalki,
HireSync.
'''
            send_mail(
                subject=subject,
                message=client_message,
                from_email='',
                recipient_list=[client_email]
            )

            send_mail(
                subject=subject,
                message=organization_recruiters_message,
                from_email='',
                recipient_list=[manager_email, recruiters_emails]
            )

            return Response({"message":"Candidate Selected Successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            resume_id = request.GET.get('id')
            round_num = request.GET.get('round_num')
            application = JobApplication.objects.get(resume = resume_id)


            num_of_postings_completed = JobApplication.objects.filter(job_id = application.job_id, status = 'selected').count()
            req_postings = JobPostings.objects.get(id= application.job_id.id).num_of_positions

            if(num_of_postings_completed >= req_postings):
                return Response({"error":"All job openings are filled"}, status=status.HTTP_400_BAD_REQUEST)
            

            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)


            with transaction.atomic():

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
                application.status = 'hold'
                application.next_interview = None
                application.save()

                applications_selected  = JobApplication.objects.filter(job_id = application.job_id).filter(status  = 'selected').count()
                job_postings_req = JobPostings.objects.get(id = application.job_id.id).num_of_positions

                if applications_selected >= job_postings_req:
                    return self.sendAlert(application.job_id.id)

            return Response({"message":"Candidate selected"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)