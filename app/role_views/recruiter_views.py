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


# Recruiter Profile


class RecruiterProfileView(APIView):

    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            user = request.user
            user = CustomUser.objects.get(username = user).id
            print(user)
            try:
                recruiter_profile = RecruiterProfile.objects.get(name = user)
            
            except RecruiterProfile.DoesNotExist:
                return Response({"error":"Recruiter Profile does not exists"}, status=status.HTTP_400_BAD_REQUEST)
            
            recruiter_serializer = RecruiterProfileSerializer(recruiter_profile)
            return Response({"data":recruiter_serializer.data}, status= status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# Sending Candidate profile to the Job post
class CandidateResumeView(APIView):
    parser_classes = (MultiPartParser, FormParser)


    def post(self, request):
        try:
            job_id = request.GET.get('id')
            if not job_id:
                return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            if not user or user.role != 'recruiter':
                return Response({"error": "You are not allowed to handle this request"}, status=status.HTTP_403_FORBIDDEN)

            job = JobPostings.objects.get(id=job_id)
            receiver = job.username

            if 'resume' not in request.FILES:
                return Response({"error": "Resume file is required."}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data
            date_string = data.get('date_of_birth', '')

            try:
                date_of_birth = datetime.strptime(date_string, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Please use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
            primary_skills = json.loads(data.get('primary_skills', '[]'))
            secondary_skills = json.loads(data.get('secondary_skills', '[]'))

            if not primary_skills:
                return Response({"error": "Primary skills are required"}, status=status.HTTP_400_BAD_REQUEST)

            if JobApplication.objects.filter(
                job_id=job, resume__candidate_email=data.get('candidate_email')
            ).exists():
                return Response({"error": "Candidate application is submitted previously"}, status=status.HTTP_400_BAD_REQUEST)

            #check job application of this user, with this id
            try:
                resumes =  CandidateResume.objects.filter(candidate_name = data.get('candidate_name'))
                application = JobApplication.objects.get(job_id = job_id, resume__in = resumes)

                if application:
                    return Response({"error":"Job application already posted for this email id"}, status=status.HTTP_400_BAD_REQUEST)
            except JobApplication.DoesNotExist:

            # Create a CandidateResume instance
                candidate_resume = CandidateResume.objects.create(
                    resume=request.FILES['resume'],
                    candidate_name=data.get('candidate_name'),
                    candidate_email = data.get('candidate_email'),
                    contact_number=data.get('contact_number'),
                    alternate_contact_number=data.get('alternate_contact_number', ''),
                    other_details=data.get('other_details', ''),
                    current_organisation=data.get('current_organization', ''),
                    current_job_location=data.get('current_job_location', ''),
                    current_job_type=data.get('current_job_type', ''),
                    date_of_birth=date_of_birth,
                    experience=data.get('experience', ''),
                    current_ctc=data.get('current_ctc', ''),
                    expected_ctc=data.get('expected_ctc', ''),
                    notice_period=data.get('notice_period', ''),
                    job_status=data.get('job_status', ''),
                )

                # Add Primary Skills
                for skill, experience in primary_skills:
                    PrimarySkillSet.objects.create(
                        candidate=candidate_resume,
                        skill=skill,
                        years_of_experience=experience,
                    )

                # Add Secondary Skills
                for skill, experience in secondary_skills:
                    SecondarySkillSet.objects.create(
                        candidate=candidate_resume,
                        skill=skill,
                        years_of_experience=experience,
                    )

                # Create Job Application
                JobApplication.objects.create(
                    resume=candidate_resume,
                    job_id=job,
                    status='pending',
                    sender=user,
                    receiver=receiver,
                )

                return Response({"message": "Resume added successfully"}, status=status.HTTP_201_CREATED)

        except JobPostings.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 

# Scheduling the interview
class ScheduleInterview(APIView):
    permission_classes = [IsRecruiter]
    def get(self, request):
        try:
            if not request.GET.get('application_id'):
                user = request.user
                pending_arr = []
                applications = JobApplication.objects.filter(sender = user, status = 'processing')
                for application in applications:
                    pending_arr.append({
                        "application_id" : application.id,
                        "job_title" : application.job_id.job_title,
                        "round_num" : application.round_num,
                        "candidate_name": application.resume.candidate_name ,
                        "next_interview": application.next_interview.scheduled_date if application.next_interview else None,
                    })
                
                return Response(pending_arr, status=status.HTTP_200_OK)

            else:
                application_id = request.GET.get('application_id')

                try:
                    application = JobApplication.objects.get(id = application_id)
                except JobApplication.DoesNotExist:
                    return Response({"error":"Job Application Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
                
                if application.status == 'pending':
                    return Response({"error":"Client is'nt shortlisted this application"}, status = status.HTTP_400_BAD_REQUEST)

                try:
                    next_interview_details = InterviewerDetails.objects.get(job_id = application.job_id.id, round_num = application.round_num)

                except InterviewerDetails.DoesNotExist:
                    return Response({"error":f"{application.round_num} Interviewer Details for this round Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
                
                application_details = {
                    "interviewer_name": next_interview_details.name.username,
                    "interviewer_email": next_interview_details.name.email,
                    "candidate_name": application.resume.candidate_name,
                    "candidate_email": application.resume.candidate_email,
                    "candidate_contact": application.resume.contact_number,
                    "candidate_alternate_contact": application.resume.alternate_contact_number,
                    "job_title" : application.job_id.job_title,
                    "job_ctc" : application.job_id.ctc,
                    "application_id": application.id,
                }

                return Response(application_details, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            if not request.GET.get('application_id'):
                return Response({"error": "Application ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            application_id = request.GET.get('application_id')
            application = JobApplication.objects.get(id = application_id)
            interviewer = InterviewerDetails.objects.get(job_id = application.job_id, round_num = application.round_num)
            scheduled_date = request.data.get('scheduled_date')
            from_time = request.data.get('from_time')
            to_time = request.data.get('to_time')
            meet_link = request.data.get('meet_link','')

            if(scheduled_date is None):
                return Response({"error":"Please select date and time"}, status = status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():

                next_scheduled_interview = InterviewSchedule.objects.create(
                    candidate = application.resume,
                    interviewer = interviewer,
                    scheduled_date = scheduled_date,
                    job_id = application.job_id,
                    meet_link = meet_link,
                    from_time = from_time,
                    to_time = to_time,
                    round_num = application.round_num,
                    status = 'pending'
                )

                application.next_interview = next_scheduled_interview
                application.save()


                start_datetime = f"{scheduled_date}T{from_time}Z"
                end_datetime = f"{scheduled_date}T{to_time}Z"

                print(start_datetime, end_datetime)

                google_calendar_link = f"""
            https://www.google.com/calendar/render?action=TEMPLATE
            &text=Interview+Scheduled
            &details=Your+interview+is+scheduled+from+{from_time}+to+{to_time}
            &location={meet_link}
            &dates={start_datetime}/{end_datetime}
            """.replace("\n", "").replace(" ", "")

                interviewer_email = interviewer.name.email
                candidate_email = application.resume.candidate_email

                message = f"""
Your next interview is scheduled successfully,
Scheduled date and time is {scheduled_date }  from {from_time} to {to_time}
Please be ready by that time

**Join Here:** {meet_link}

[Click here to Add to Google Calendar]({google_calendar_link})

Best Regards,  
{application.sender.username}
"""             
                
                google_calendar_link = f"""
            https://www.google.com/calendar/render?action=TEMPLATE
            &text=Interview+Scheduled
            &details=Your+interview+is+scheduled+from+{from_time}+to+{to_time}
            &location={meet_link}
            &dates={start_datetime}/{end_datetime}
            """.replace("\n", "").replace(" ", "")

            # HTML Email Content with a Button
            html_message = f"""
            <html>
            <body>
                <p>Your next interview is scheduled successfully.</p>
                <p><strong>Scheduled date and time:</strong> {scheduled_date} from {from_time} to {to_time}</p>
                <p><strong>Join Here:</strong> <a href="{meet_link}" target="_blank">{meet_link}</a></p>
                <p>
                    <a href="{google_calendar_link}" style="background-color:#007BFF; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; font-size:16px; display:inline-block;">
                        Add to Google Calendar
                    </a>
                </p>
                <p>Best Regards,<br>{application.sender.username}</p>
            </body>
            </html>
            """

            send_mail(
                subject="Next Interview Scheduled",
                message="Your interview details...",
                html_message=html_message,  # Send HTML content
                recipient_list=[interviewer_email, candidate_email],
                from_email=''
            )

            return Response({"message": "Next Interview Scheduled Successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Getting the next round details
class NextRoundInterviewDetails(APIView):
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
    


# Screening, analysis , generate questionere for the candidate Resume

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
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        