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

class InterviewerDashboardView(APIView):
    permission_classes = [IsInterviewer]

    def get(self, request):
        try:
            user = request.user
            today = timezone.localdate()
            interviewer_details = InterviewerDetails.objects.filter(name = user)
            todays_interviews = InterviewSchedule.objects.filter(
                interviewer__in=interviewer_details,
                scheduled_date=today
            ).select_related('candidate', 'job_id')

            todays_interviews_list = []
            today_events = []
            for interview in todays_interviews:
                # Today's Interview List
                todays_interviews_list.append({
                    "candidate_name": interview.candidate.candidate_name,
                    "job_title": interview.job_id.job_title,
                    "round_num": interview.round_num,
                    "from_time": interview.from_time.strftime("%I:%M %p"),  # Formatting time like '09:30 AM'
                    "to_time": interview.to_time.strftime("%I:%M %p"),
                    "interview_id": interview.id,
                    "status":interview.status,
                })

                # Events list for Calendar view
                today_events.append({
                    "id": interview.id,
                    "title": f"Interview with {interview.candidate.candidate_name}",
                    "startTime": interview.from_time.strftime("%I:%M %p"),
                    "endTime": interview.to_time.strftime("%I:%M %p"),
                    "type": "processing" if interview.status == 'pending' else 'success'
                })

            # Fetch missed interviews (pending status and scheduled before today)
            missed_interviews = InterviewSchedule.objects.filter(
                interviewer__in=interviewer_details,
                scheduled_date__lt=today,
                status='pending'
            ).select_related('candidate', 'job_id')

            missed_interviews_list = []
            for interview in missed_interviews:
                missed_interviews_list.append({
                    "candidate_name": interview.candidate.candidate_name,
                    "job_title": interview.job_id.job_title,
                    "round_num": interview.round_num,
                    "from_time": interview.from_time.strftime("%I:%M %p"),
                    "to_time": interview.to_time.strftime("%I:%M %p"),
                    "interview_id": interview.id,
                })

            # Total assigned and completed interviews
            assigned_interviews = InterviewSchedule.objects.filter(interviewer__in = interviewer_details)
            total_assigned = assigned_interviews.count()
            total_completed = assigned_interviews.filter(status='completed').count()

            data = {
                "assigned": total_assigned,
                "completed": total_completed
            }

            # Final response
            return Response({
                "data": data,
                "missed_interviews": missed_interviews_list,
                "today_interviews": todays_interviews_list,
                "events": today_events
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Log the error for debugging
            print(f"Error in InterviewerDashboardView: {str(e)}")
            return Response(
                {"error": "Something went wrong. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
   

class ScheduledInterviewsView(APIView):
    permission_classes = [IsInterviewer]
    pagination_class = TenResultsPagination
    
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
                            "job_department": scheduled_interview.job_id.job_department,
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
               
                interviews = InterviewSchedule.objects.filter(interviewer__name = request.user )

                scheduled_list = []
                for interview in interviews:
                    application_by_resume = JobApplication.objects.filter(resume=interview.candidate).first()

                    application_by_interview = JobApplication.objects.filter(next_interview=interview).first()

                    id = interview.id
                    scheduled_date = interview.scheduled_date
                    round_of_interview = interview.round_num
                    timings = f"{interview.from_time} - {interview.to_time}"
                    job_id = interview.job_id.id
                    job_title = interview.job_id.job_title

                    if application_by_interview:
                        candidate_name = application_by_interview.resume.candidate_name
                        statuss = application_by_interview.status
                        application_id = application_by_interview.id
                    elif application_by_resume:
                        candidate_name = application_by_resume.resume.candidate_name
                        statuss = "completed"  
                        application_id = application_by_resume.id
                    else:
                        # Fallback if no application found
                        candidate_name = interview.candidate.candidate_name
                        statuss = "completed"
                        application_id = None  

                    scheduled_list.append({
                        "interview_id": id,
                        "job_id": job_id,
                        "job_title": job_title,
                        "candidate_name": candidate_name,
                        "round_of_interview": round_of_interview,
                        "scheduled_date": scheduled_date,
                        "timings": timings,
                        "status": statuss,
                        "application_id": application_id,
                    })

                paginator = self.pagination_class()
                paginated_data = paginator.paginate_queryset(scheduled_list,request)

                return paginator.get_paginated_response(paginated_data)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)

class CompletedInterviewsView(APIView):
    permission_classes = [IsInterviewer]
    pagination_class = TenResultsPagination

    def get(self, request):
        try:
            user = request.user
            interviews = InterviewerDetails.objects.filter(name = user)
            scheduled_interviews = InterviewSchedule.objects.filter(interviewer__in = interviews, status = 'completed')
            evaluations = CandidateEvaluation.objects.filter(interview_schedule__in = scheduled_interviews)
            evaluation_list = []
            for evaluation in evaluations:
                evaluation_list.append({
                    "job_title": evaluation.job_id.job_title,
                    "round_num": evaluation.interview_schedule.round_num,
                    "mode_of_interview": evaluation.interview_schedule.interviewer.mode_of_interview,
                    "candidate_name": evaluation.job_application.resume.candidate_name,
                    "scheduled_date": evaluation.interview_schedule.scheduled_date,
                    "primary_skills_rating":evaluation.primary_skills_rating,
                    "secondary_skills_rating": evaluation.secondary_skills_ratings,
                    "remarks": evaluation.remarks,
                    "evaluation_id": evaluation.id
                })
            
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset( evaluation_list, request)
            return paginator.get_paginated_response(paginated_data)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)

class MissedInterviewsView(APIView):
    permission_classes = [IsInterviewer]
    pagination_class = TenResultsPagination

    def get(self, request):
        try:
            today = timezone.localdate()
            time = timezone.localtime()
            user = request.user
            interviews = InterviewerDetails.objects.filter(name = user)
            scheduled_interviews = InterviewSchedule.objects.filter(interviewer__in = interviews, status = 'pending', scheduled_date__lte = today, to_time__lte = time )
            interviews_list = []
            for interview in scheduled_interviews:
                interviews_list.append({
                    "job_title": interview.job_id.job_title,
                    "round_num": interview.round_num,
                    "mode_of_interview": interview.interviewer.mode_of_interview,
                    "candidate_name": interview.candidate.candidate_name,
                    "scheduled_date": interview.scheduled_date,
                    "scheduled_timings": f"{interview.from_time} - {interview.to_time}",
                    "interview_id": interview.id
                })
            
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset( interviews_list, request)
            return paginator.get_paginated_response(paginated_data)
        
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
            
            skills = job.skills.all()
            skills_json = {
                "primary_skills": [
                    {"skill_name": skill.skill_name, "skill_metric": skill.metric_type}
                    for skill in job.skills.all() if skill.is_primary
                ],
                "secondary_skills": [
                    {"skill_name": skill.skill_name, "skill_metric": skill.metric_type}
                    for skill in job.skills.all() if not skill.is_primary
                ]
            }


            resume_id = request.GET.get('resume_id')
            
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
        try:
            resume_id = int(request.GET.get('id'))
            round_num = int(request.GET.get('round_num'))
            remarks = request.data.get("remarks")
            if remarks == '':
                return Response({"error":"Please enter remarks and promote the candidate"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                application = JobApplication.objects.get(resume__id = resume_id)
            except JobApplication.DoesNotExist:
                print("query doesnot exist")
                return Response({"error":"Job application matching query doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)

            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)
            candidate = CandidateProfile.objects.get(name__username = application.resume.candidate_name)

            remarks = CandidateEvaluation.objects.create(
                primary_skills_rating = primary_skills,
                secondary_skills_ratings = secondary_skills,
                candidate = candidate,
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
            customCand=CustomUser.objects.get(email=candidate.email)
            
            Notifications.objects.create(
    sender=request.user,
    category = Notifications.CategoryChoices.SCHEDULE_INTERVIEW,
    receiver=application.sender,
    subject=f"Candidate {customCand.username} has been qualified for the next round {application.job_id.job_title}",
    message=(
        f"Candidate Promotion Notice\n\n"
        f"Client: {request.user.username}\n"
        f"Position: {application.job_id.job_title}\n\n"
        f"The candidate {customCand.username} has successfully cleared round {application.round_num}. "
        f"Please schedule interview {application.round_num + 1} availability of candidate and interviewer\n\n"
        f"link::recruiter/schedule_applications/"
    )
)
            
            
            Notifications.objects.create(
    sender=request.user,
    receiver=customCand,
    category = Notifications.CategoryChoices.PROMOTE_CANDIDATE,
    subject=f"Congratulations {customCand.username}! You have qualified for the next round for the role {application.job_id.job_title}",
    message=(
        f"Interview Progress Update\n\n"
        f"Dear {customCand.username},\n\n"
        f"Congratulations! You have successfully cleared round {application.round_num} "
        f"for the position of {application.job_id.job_title}.\n\n"
        f"We will be scheduling your next interview (Round {application.round_num + 1}) soon. "
        f"Our team will contact you regarding your availability.\n\n"
        f"Stay tuned!\n\n"
    )
)
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

            primary_skills = request.data.get('primary_skills', '')
            secondary_skills = request.data.get('secondary_skills', '')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)

            candidate = CandidateProfile.objects.get(name__username = application.resume.candidate_name)

            remarks = CandidateEvaluation.objects.create(
                primary_skills_rating = primary_skills,
                secondary_skills_ratings = secondary_skills,
                candidate = candidate,
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
            
            customCand=CustomUser.objects.get(email=candidate.email)
            
            Notifications.objects.create(
                    sender=request.user,
                    category = Notifications.CategoryChoices.REJECT_CANDIDATE,
                    receiver=application.sender,
                    subject=f"Candidate {customCand.username} is rejected for the role {application.job_id.job_title}",
                    message = (
    f"Candidate Rejection Notice\n\n"
    f"Client: {request.user.username}\n"
    f"Position: {application.job_id.job_title}\n\n"
    f"{request.user.username} has conducted the interview for round {application.next_interview.round_num} "
    f"with the submitted candidate {customCand.username} for the position of {application.job_id.job_title}, "
    f"and has decided not to move forward with them at this time.\n\n"
    f"link::recruiter/postings/"
)
)
            
            Notifications.objects.create(
    sender=request.user,
    receiver=customCand,
    category = Notifications.CategoryChoices.REJECT_CANDIDATE,
    subject=f"Update on your application for the role {application.job_id.job_title}",
    message=(
        f"Application Update\n\n"
        f"Dear {customCand.username},\n\n"
        f"We appreciate your interest in the {application.job_id.job_title} position.\n\n"
        f"After careful consideration following your interview for round {application.next_interview.round_num}, "
        f"we regret to inform you that we will not be moving forward with your application at this time.\n\n"
    )
)
            return Response({"message":"Rejected successfully"},status = status.HTTP_201_CREATED)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)


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


            remarks = request.data.get('remarks')
            print(remarks, " are the remarks")
            if remarks == None:
                return Response({"error":"Please enter remarks"}, status=status.HTTP_400_BAD_REQUEST)

            num_of_postings_completed = JobApplication.objects.filter(job_id = application.job_id, status = 'selected').count()
            req_postings = JobPostings.objects.get(id= application.job_id.id).num_of_positions

            if(num_of_postings_completed >= req_postings):
                return Response({"error":"All job openings are filled"}, status=status.HTTP_400_BAD_REQUEST)
            

            primary_skills = request.data.get('primary_skills')
            secondary_skills = request.data.get('secondary_skills')
            remarks = request.data.get('remarks', "")
            score = request.data.get('score', 0)
            
            candidate = CandidateProfile.objects.get(name__username = application.resume.candidate_name)

            with transaction.atomic():

                remarks_candidate = CandidateEvaluation.objects.create(
                    primary_skills_rating = primary_skills,
                    secondary_skills_ratings = secondary_skills,
                    candidate = candidate,
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
                customCand=CustomUser.objects.get(email=candidate.email)
                
                Notifications.objects.create(
    sender=request.user,
    receiver=customCand,
    category = Notifications.CategoryChoices.ONHOLD_CANDIDATE,
    subject=f"Update on your application for the role {application.job_id.job_title}",
    message=(
        f"Application Update\n\n"
        f"Dear {customCand.username},\n\n"
        f"We appreciate your interest in the {application.job_id.job_title} position with {request.user.username}.\n\n"
        f"We are pleased to inform you that you have successfully cleared all rounds of the interview process.\n\n"
        f"Your profile is now under final review for the last call.\n"
        f"Our team will get back to you shortly with the final update.\n\n"
        f"Thank you for your patience and continued interest.\n\n"
        f"Best wishes,\n"
    )
)
                Notifications.objects.create(
    sender=request.user,
    receiver=application.job_id.username,
    category = Notifications.CategoryChoices.SELECT_CANDIDATE,
    subject=f"Profile cleared all interviews for {application.job_id.job_title} — Final Confirmation Needed",
    message=(
        f"Application Update\n\n"
        f"Position: {application.job_id.job_title}\n\n"
        f"The candidate {customCand.username} has successfully completed all rounds of interviews for the "
        f"position of {application.job_id.job_title}.\n\n"
        f"Please review the candidate’s profile and provide your final decision regarding their selection.\n\n"
        f"link::client/candidates/"
    )
)           
                
                Notifications.objects.create(
    sender=request.user,
    category = Notifications.CategoryChoices.SELECT_CANDIDATE,
    receiver=application.sender,
    subject=f"Candidate {customCand.username} has cleared all interviews for the role {application.job_id.job_title}",
    message=(
        f"Candidate Progress Update\n\n"
        f"Client: {request.user.username}\n"
        f"Position: {application.job_id.job_title}\n\n"
        f"{request.user.username} has completed all interview rounds with the candidate {customCand.username} "
        f"for the position of {application.job_id.job_title}.\n\n"
        f"The candidate has successfully cleared all interviews and their profile is now under final review by the client.\n"
        f"Kindly follow up with the client for the final decision.\n\n"
        f"link::recruiter/postings/"
    )
)
                
                applications_selected  = JobApplication.objects.filter(job_id = application.job_id).filter(status  = 'selected').count()
                job_postings_req = JobPostings.objects.get(id = application.job_id.id).num_of_positions

                if applications_selected >= job_postings_req:
                    return self.sendAlert(application.job_id.id)

            return Response({"message":"Candidate selected"},status = status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        

class InterviewerAllAlerts(APIView):
    def get(self, request):
        try:
            all_notifications = Notifications.objects.filter(seen = False, receiver = request.user)
            new_jobs = 0 
            scheduled_interviews = 0
            for notification in all_notifications:
                if notification.category == 'assign_interviewer':
                    new_jobs+=1
                else:
                    scheduled_interviews+=1

            data = {
                "new_jobs":new_jobs,
                "scheduled_interviews":scheduled_interviews
            }
            return Response({"data":data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)