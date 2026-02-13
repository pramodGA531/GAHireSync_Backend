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
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
from app.utils import generate_invoice
from django.db.models import Q
from ..utils import *
from django.http import JsonResponse
from django.core.files.base import File
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


# Recruiter Profile


# print("generate_invoice",generate_invoice)


class RecruiterProfileView(APIView):

    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            user = request.user
            user = CustomUser.objects.get(username=user).id
            print(user)
            try:
                recruiter_profile = RecruiterProfile.objects.get(name=user)

            except RecruiterProfile.DoesNotExist:
                return Response(
                    {"error": "Recruiter Profile does not exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            recruiter_serializer = RecruiterProfileSerializer(recruiter_profile)
            return Response(
                {"data": recruiter_serializer.data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            print(str(e))
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Sending Candidate profile to the Job post
class CandidateResumeView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsRecruiter]

    def post(self, request):
        try:
            job_id = request.GET.get("id")
            if not job_id:
                return Response(
                    {"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            job_assigned = AssignedJobs.objects.get(id=job_id)
            job = job_assigned.job_id

            if job.status == "closed":
                return Response(
                    {"error": "Job post is closed, unable to share the applications"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            receiver = job.username

            data = request.data
            user = request.user

            date_string = data.get("date_of_birth", "")

            if date_string in ["", None, "null"]:
                date_of_birth = None
            else:
                try:
                    date_of_birth = datetime.strptime(date_string, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Please use YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            primary_skills = json.loads(data.get("primary_skills", "[]"))

            job_primary = SkillMetricsModel.objects.filter(
                job_id=job_id, is_primary=True
            )

            secondary_skills = json.loads(data.get("secondary_skills", "[]"))

            current_ctc = data.get("current_ctc")
            if current_ctc == "null":
                current_ctc = 0.0

            if job_primary and not primary_skills:
                return Response(
                    {"error": "Primary skills are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                resumes = CandidateResume.objects.filter(
                    candidate_email=data.get("candidate_email")
                )
                application = JobApplication.objects.get(
                    job_location__job_id=job, resume__in=resumes
                )

                if application:
                    return Response(
                        {"error": "Job application already posted for this email id"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except JobApplication.DoesNotExist:
                resume = None
                application = JobApplication.objects.filter(
                    resume__candidate_email=data.get("candidate_email")
                ).first()
                if application:
                    resume = application.resume.resume.name

                candidate_resume = CandidateResume.objects.create(
                    resume=resume if resume else request.FILES["resume"],
                    candidate_name=data.get("candidate_name"),
                    candidate_email=data.get("candidate_email"),
                    contact_number=data.get("contact_number"),
                    alternate_contact_number=data.get("alternate_contact_number", ""),
                    other_details=data.get("other_details", ""),
                    current_organisation=data.get("current_organization", ""),
                    current_job_location=data.get("current_job_location", ""),
                    current_job_type=data.get("current_job_type", ""),
                    date_of_birth=date_of_birth,
                    experience=data.get("experience", ""),
                    current_ctc=current_ctc,
                    expected_ctc=data.get("expected_ctc", ""),
                    notice_period=data.get("notice_period", 0.0),
                    job_status=data.get("job_status", ""),
                    joining_days_required=data.get("joining_days_required", ""),
                    highest_qualification=data.get("highest_qualification"),
                )

                for skill in primary_skills:
                    skill_metric = CandidateSkillSet.objects.create(
                        candidate=candidate_resume,
                        skill_name=skill[0],
                        skill_metric=skill[1],
                        is_primary=True,
                    )

                    if skill[1] == "experience":
                        skill_metric.metric_value = skill[4]
                    elif skill[1] == "rating":
                        skill_metric.metric_value = skill[2]
                    else:
                        try:
                            skill_metric.metric_value = skill[5]
                        except IndexError:
                            skill_metric.metric_value = ""

                    skill_metric.save()

                for skill in secondary_skills:
                    skill_metric = CandidateSkillSet.objects.create(
                        candidate=candidate_resume,
                        skill_name=skill[0],
                        skill_metric=skill[1],
                        is_primary=False,
                    )

                    if skill[1] == "experience":
                        skill_metric.metric_value = skill[4]
                    elif skill[1] == "rating":
                        skill_metric.metric_value = skill[2]
                    else:
                        try:
                            skill_metric.metric_value = skill[5]
                        except IndexError:
                            skill_metric.metric_value = ""

                    skill_metric.save()

                job_application = JobApplication.objects.create(
                    resume=candidate_resume,
                    job_location=job_assigned.job_location,
                    status="pending",
                    sender=user,
                    attached_to=user,
                    receiver=receiver,
                )

                link = f"{frontend_url}/client/get-resumes/{job.id}"
                message = f"""

Dear {job.username.username},

A candidate profile has been submitted for {job.job_title} by {request.user.username}. Please review the details and provide feedback.
🔗 {link}

Best,
HireSync Team
"""
                send_custom_mail(
                    f"New Candidate Submitted – {job.job_title}",
                    message,
                    {job.username.email},
                )
                job_profile_log(
                    job_application.id,
                    f"Candidate profile '{candidate_resume.candidate_name}' "
                    f"({candidate_resume.candidate_email}) submitted for job '{job.job_title}' "
                    f"by recruiter '{request.user.username}'.",
                )
                Notifications.objects.create(
                    sender=request.user,
                    category=Notifications.CategoryChoices.SEND_APPLICATION,
                    receiver=job.username,
                    subject=f"Resumes Sent for the Role: {job.job_title}",
                    message=(
                        f"📄 Resumes Submitted\n\n"
                        f"Profiles have been sent for your job post: **{job.job_title}**.\n\n"
                        f"Please review the submitted resumes and provide feedback accordingly.\n\n"
                        f"Your feedback is important to proceed with the next steps.\n\n"
                        f"id::{job.id}"  # used in frontend to generate a clickable Link
                        f"link::'client/get-resumes/'"
                    ),
                )

                return Response(
                    {"message": "Resume added successfully"},
                    status=status.HTTP_201_CREATED,
                )

        except JobPostings.DoesNotExist:
            return Response(
                {"error": "Job not found."}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllScheduledInterviews(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            all_interviews = (
                InterviewSchedule.objects.filter(rctr__in=[request.user])
                .exclude(status__in=["pending"])
                .select_related("interviewer", "candidate")
            )

            interviews_list = []

            for interview in all_interviews:
                interviews_list.append(
                    {
                        "interviewer_name": interview.interviewer.name.username,
                        "candidate_name": interview.candidate.candidate_name,
                        "status": interview.status,
                        "scheduled_date": interview.scheduled_date,
                        "from_time": interview.from_time,
                        "to_time": interview.to_time,
                        "id": interview.id,
                        "round_num": interview.round_num,
                        "job_title": interview.job_location.job_id.job_title,
                        "job_id": interview.job_location.job_id.id,
                    }
                )

            return Response(interviews_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Scheduling the interview
class ScheduleInterview(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            if not request.GET.get("application_id"):
                user = request.user
                pending_arr = []
                applications = JobApplication.objects.filter(
                    attached_to=user, status="processing"
                )
                for application in applications:
                    if (
                        application.next_interview
                        and application.next_interview.status != "pending"
                    ):
                        continue
                    interviewer_instance = InterviewerDetails.objects.filter(
                        job_id=application.job_location.job_id,
                        round_num=application.round_num,
                    ).first()
                    interviewer = (
                        interviewer_instance.name.username
                        if interviewer_instance
                        else "Not Assigned"
                    )
                    pending_arr.append(
                        {
                            "application_id": application.id,
                            "job_title": application.job_location.job_id.job_title,
                            "round_num": application.round_num,
                            "candidate_name": application.resume.candidate_name,
                            "next_interview": (
                                application.next_interview.scheduled_date
                                if application.next_interview
                                else None
                            ),
                            "from_time": (
                                application.next_interview.from_time
                                if application.next_interview
                                else None
                            ),
                            "to_time": (
                                application.next_interview.to_time
                                if application.next_interview
                                else None
                            ),
                            "status": (
                                application.next_interview.status
                                if application.next_interview
                                else None
                            ),
                            "scheduled_date": (
                                application.next_interview.scheduled_date
                                if application.next_interview
                                else None
                            ),
                            "job_location": application.job_location.location,
                            "location_status": application.job_location.status,
                            "interviewer_name": interviewer,
                            "job_id": application.job_location.job_id.id,
                        }
                    )

                return Response(pending_arr, status=status.HTTP_200_OK)

            else:
                application_id = request.GET.get("application_id")

                try:
                    application = JobApplication.objects.get(id=application_id)
                except JobApplication.DoesNotExist:
                    return Response(
                        {"error": "Job Application Does not exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if application.status == "pending":
                    return Response(
                        {"error": "Client is'nt shortlisted this application"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    next_interview_details = InterviewerDetails.objects.get(
                        job_id=application.job_location.job_id.id,
                        round_num=application.round_num,
                    )

                except InterviewerDetails.DoesNotExist:
                    return Response(
                        {
                            "error": f"{application.round_num} Interviewer Details for this round Does not exist"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                application_details = {
                    "interviewer_name": next_interview_details.name.username,
                    "interviewer_email": next_interview_details.name.email,
                    "candidate_name": application.resume.candidate_name,
                    "candidate_email": application.resume.candidate_email,
                    "candidate_contact": application.resume.contact_number,
                    "candidate_alternate_contact": application.resume.alternate_contact_number,
                    "job_title": application.job_location.job_id.job_title,
                    "job_ctc": application.job_location.job_id.ctc,
                    "application_id": application.id,
                    "interview_type": next_interview_details.type_of_interview,
                    "interview_mode": next_interview_details.mode_of_interview,
                }

                return Response(application_details, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            if not request.GET.get("application_id"):
                return Response(
                    {"error": "Application ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            rctr = request.user
            application_id = request.GET.get("application_id")
            application = JobApplication.objects.get(id=application_id)
            interviewer = InterviewerDetails.objects.get(
                job_id=application.job_location.job_id, round_num=application.round_num
            )
            scheduled_date = request.data.get("scheduled_date")
            from_time = request.data.get("from_time")
            to_time = request.data.get("to_time")
            meet_link = request.data.get("meet_link", "")

            # Checking all interviews at that time for the interviewer
            overlapping_interviews = InterviewSchedule.objects.filter(
                interviewer__name=interviewer.name, scheduled_date=scheduled_date
            ).filter(Q(from_time__lt=to_time, to_time__gt=from_time))

            if overlapping_interviews.exists():
                raise ValidationError(
                    "The interview timing overlaps with another scheduled interview."
                )

            interviewer_interviews = InterviewSchedule.objects.filter(
                interviewer=interviewer,
                scheduled_date=scheduled_date,
                from_time=from_time,
                to_time=to_time,
            )

            if interviewer_interviews.exists():
                return Response(
                    {
                        "error": "Interviewer has scheduled another interview at the same time, please schedule after some time"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if scheduled_date is None:
                return Response(
                    {"error": "Please select date and time"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                next_scheduled_interview = InterviewSchedule.objects.create(
                    # rctr=rctr,
                    candidate=application.resume,
                    interviewer=interviewer,
                    scheduled_date=scheduled_date,
                    job_location=application.job_location,
                    meet_link=meet_link,
                    from_time=from_time,
                    to_time=to_time,
                    round_num=application.round_num,
                    status="scheduled",
                )
                next_scheduled_interview.rctr.set([rctr])
                application.next_interview = next_scheduled_interview
                application.save()
                start_datetime = f"{scheduled_date}T{from_time}Z"
                end_datetime = f"{scheduled_date}T{to_time}Z"

                interviewer_email = interviewer.name.email
                candidate_email = application.resume.candidate_email

                google_calendar_link = f"""
            https://www.google.com/calendar/render?action=TEMPLATE
            &text=Interview+Scheduled
            &details=Your+interview+is+scheduled+from+{from_time}+to+{to_time}
            &location={meet_link}
            &dates={start_datetime}/{end_datetime}
            """.replace(
                    "\n", ""
                ).replace(
                    " ", ""
                )

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
                <p>Best Regards,<br>{application.attached_to.username}</p>
            </body>
            </html>
            """

            send_custom_mail(
                subject="Next Interview Scheduled",
                body="Your interview details...",
                to_email=[interviewer_email, candidate_email],
            )

            ClientDetail = ClientDetails.objects.get(
                user=application.job_location.job_id.username
            )

            customCand = CustomUser.objects.get(
                email=application.resume.candidate_email
            )
            Notifications.objects.create(
                sender=request.user,
                receiver=customCand,
                category=Notifications.CategoryChoices.SCHEDULE_INTERVIEW,
                subject=f"Interview Scheduled for {application.job_location.job_id.job_title} ",
                message=(
                    f"Interview Scheduled\n\n"
                    f"Your interview has been scheduled on {scheduled_date}.\n"
                    f"Round Number: {interviewer.round_num}\n"
                    f"Role: {application.job_location.job_id.job_title}\n"
                    f"Interviewer: {interviewer.name.username}\n"
                    f"Type of Interview: {interviewer.type_of_interview}\n"
                    f"Mode of Interview: {interviewer.mode_of_interview}\n\n"
                    f"Interview Link: {meet_link}\n"
                    f"Please check the details here: link::candidate/upcoming_interviews/"
                ),
            )
            Notifications.objects.create(
                sender=request.user,
                receiver=interviewer.name,
                category=Notifications.CategoryChoices.SCHEDULE_INTERVIEW,
                subject=f"Interview Scheduled with {customCand.username}",
                message=(
                    f"Interview Assignment\n\n"
                    f"You have been scheduled to conduct an interview with {customCand.username}.\n"
                    f"Scheduled Date: {scheduled_date}\n"
                    f"Role: {application.job_location.job_id.job_title}\n"
                    f"Round Number: {interviewer.round_num}\n"
                    f"Type of Interview: {interviewer.type_of_interview}\n"
                    f"Mode of Interview: {interviewer.mode_of_interview}\n\n"
                    f"Interview Link: {meet_link}\n"
                    f"Please update the status of interviewhere: link::interviewer/interviews/upcoming"
                ),
            )
            job_profile_log(
                application.id,
                f"Interview scheduled for candidate '{customCand.username}' ({customCand.email}) "
                f"by recruiter '{request.user.username}'.\n"
                f"Interviewer: {interviewer.name.username}\n"
                f"Round: {interviewer.round_num}\n"
                f"Type: {interviewer.type_of_interview}\n"
                f"Mode: {interviewer.mode_of_interview}\n"
                f"Date: {scheduled_date} ({from_time} - {to_time})\n"
                f"Meet Link: {meet_link if meet_link else 'Not provided'}",
            )

            return Response(
                {"message": "Next Interview Scheduled Successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):

        try:
            data = request.data
            scheduled_id = data.get("interview_scheduled_id")
            scheduled_date = data.get("scheduled_date")
            from_time = data.get("from_time")
            to_time = data.get("to_time")
            meet_link = data.get("meet_link")

            app = InterviewSchedule.objects.get(id=scheduled_id)

            app.scheduled_date = scheduled_date
            app.from_time = from_time
            app.to_time = to_time
            app.meet_link = meet_link
            app.status = "scheduled"
            app.save()

            return Response(
                {"message": "Interview rescheduled successfully."},
                status=status.HTTP_200_OK,
            )

        except InterviewSchedule.DoesNotExist:
            return Response(
                {"error": "Application not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetIntervieweRemarks(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            interview_schedule_id = request.GET.get("interview_id")
            interview_remarks = CandidateEvaluation.objects.get(
                interview_schedule__id=interview_schedule_id
            )
            remarks_json = {
                "primary_skills_rating": interview_remarks.primary_skills_rating,
                "secondary_skills_rating": interview_remarks.secondary_skills_ratings,
                "remarks": interview_remarks.remarks,
                "status": interview_remarks.status,
            }

            return Response(remarks_json, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Getting the next round details
class NextRoundInterviewDetails(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "You are not authenticated"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            job_id = request.GET.get("id")
            if not job_id:
                return Response(
                    {"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                job = JobPostings.objects.get(id=job_id)

            except JobPostings.DoesNotExist:
                return Response(
                    {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            resume_id = request.GET.get("resume_id")

            if not resume_id:
                return Response(
                    {"error": "Resume ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                job_application = JobApplication.objects.get(
                    resume_id=resume_id, job_id=job
                )
            except JobApplication.DoesNotExist:
                return Response(
                    {"error": "Job application not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            next_round = (
                job_application.round_num + 1 if job_application.round_num else 1
            )

            try:
                next_interview_details = InterviewerDetails.objects.get(
                    job_id=job_id, round_num=next_round
                )
                serializer = InterviewerDetailsSerializer(next_interview_details)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except InterviewerDetails.DoesNotExist:
                return Response(
                    {"message": "There are no further rounds"},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            print(str(e))
            return Response(
                {"error": "An error occurred while processing your request"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Screening, analysis , generate questionere for the candidate Resume


class GenerateQuestions(APIView):
    def get(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = AssignedJobs.objects.get(id=job_id, job_id__organization=org).job_id
            questions = generate_questions_with_gemini(job)
            return Response(questions, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)


class SendQuestionsToInterviewer(APIView):
    def post(self, request, job_id):
        try:
            questions = request.data.get("questions", [])
            if not questions:
                return Response(
                    {"detail": "No questions provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            # We need the JobPostings object to find interviewers
            # Assuming job_id here refers to the AssignedJobs ID from the frontend URL context?
            # Let's check GenerateQuestions:
            # job = AssignedJobs.objects.get(id=job_id, job_id__organization=org).job_id

            # Replicate the logic to get the actual Job object
            job_posting = AssignedJobs.objects.get(
                id=job_id, job_id__organization=org
            ).job_id

            # Fetch interviewers for this job
            interviewers = InterviewerDetails.objects.filter(job_id=job_posting)

            if not interviewers.exists():
                return Response(
                    {"detail": "No interviewers assigned to this job."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            recipient_list = [
                interviewer.name.email
                for interviewer in interviewers
                if interviewer.name.email
            ]

            if not recipient_list:
                return Response(
                    {"detail": "No interviewers have valid email addresses."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success = send_questions_mail(
                job_posting.job_title, questions, recipient_list
            )

            if success:
                return Response(
                    {
                        "message": f"Questions sent to {len(recipient_list)} interviewers."
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"detail": "Failed to send email."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except AssignedJobs.DoesNotExist:
            return Response(
                {"detail": "Job not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            print(f"Error in SendQuestionsToInterviewer: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyseResume(APIView):
    def post(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = AssignedJobs.objects.get(id=job_id, job_id__organization=org).job_id
            resume = request.FILES.get("resume")
            resume = extract_text_from_file(resume)
            analysis = analyse_resume(job, resume)
            return Response(analysis, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"detail": str(e)}, status=status.HTTP_200_OK)


class ScreenResume(APIView):
    def post(self, request, job_id):
        try:
            print(request.data)
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = JobPostings.objects.get(id=job_id, organization=org)
            resume = request.FILES.get("resume")
            resume = extract_text_from_file(resume)
            analysis = screen_profile_ai(job, resume)
            return Response(analysis, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class ReConfirmResumes(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            job_applications = JobApplication.objects.filter(
                attached_to=request.user, status="selected"
            )
            selected_candidates = SelectedCandidates.objects.filter(
                application__in=job_applications
            )
            candidates_list = []
            for candidate in selected_candidates:
                job_post = candidate.application.job_location.job_id
                selected_candidate_json = {
                    "job_title": job_post.job_title,
                    "job_description": job_post.job_description,
                    "client_name": job_post.username.username,
                    "accepted_ctc": candidate.ctc,
                    "joining_date": candidate.joining_date,
                    "candidate_name": candidate.candidate.name.username,
                    "selected_candidate_id": candidate.id,
                    "actual_ctc": job_post.ctc,
                    "recruiter_acceptance": candidate.recruiter_acceptance,
                    "candidate_acceptance": candidate.candidate_acceptance,
                    "reconfirmed_by_recruiter": candidate.reconfirmed_by_recruiter,
                    "candidate_joining_status": candidate.joining_status,
                }
                candidates_list.append(selected_candidate_json)

            return Response(candidates_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class AcceptReconfirmResumes(APIView):
    # Here I need to generate the invoices for now monday need to send or create via celery library
    permission_classes = [IsRecruiter]

    def post(self, request):
        print("calling accept")
        try:
            id = request.GET.get("selected_candidate_id")
            selected_candidate = SelectedCandidates.objects.get(id=id)
            selected_candidate.recruiter_acceptance = True
            selected_candidate.reconfirmed_by_recruiter = True
            selected_candidate.save()
            application = selected_candidate.application
            print("application", application)
            job_posting = application.job_location.job_id
            print("job_posting", job_posting)

            # here I need to fetch the application id with that id terms and conditions need and org,client details too

            return Response(
                {"message": "Reconfirmed successfully", "ok": True},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RejectReconfirmResumes(APIView):
    permission_classes = [IsRecruiter]

    def post(self, request):
        print("calling reject")
        try:
            id = request.GET.get("selected_candidate_id")
            selected_candidate = SelectedCandidates.objects.get(id=id)
            selected_candidate.feedback = request.data.get("feedback")
            selected_candidate.recruiter_acceptance = False
            selected_candidate.reconfirmed_by_recruiter = False
            selected_candidate.save()

            return Response(
                {"message": "Feedback sent to client successfully", "ok": True},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RecAssignedJobsView(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            user = request.user

            jobs_assigned = AssignedJobs.objects.filter(
                assigned_to=user, job_id__approval_status="accepted"
            )

            job_postings_list = []
            for job_assigned in jobs_assigned:
                applications = JobApplication.objects.filter(
                    job_location=job_assigned.job_location, attached_to=user
                )
                onhold = applications.filter(status="hold").count()
                rejected = applications.filter(status="rejected").count()
                pending = applications.filter(status="pending").count()
                selected = applications.filter(status="selected").count()

                incoming_applications = JobApplication.objects.filter(
                    job_location=job_assigned.job_location,
                    attached_to=None,
                    sender=None,
                ).count()

                job = job_assigned.job_id
                job_postings_list.append(
                    {
                        "job_title": job.job_title,
                        "client_name": (
                            job.username.username if hasattr(job, "username") else ""
                        ),
                        "status": job.status,
                        "location_status": job_assigned.job_location.status,
                        "num_of_positions": job_assigned.job_location.positions,
                        "onhold": onhold,
                        "rejected": rejected,
                        "pending": pending,
                        "selected": selected,
                        "incoming": incoming_applications,
                        "deadline": job.job_close_duration,
                        "assigned_id": job_assigned.id,
                        "job_id": job_assigned.job_id.id,
                        "location": job_assigned.job_location.location,
                        "is_edited_by_client": job.is_edited_by_client,
                    }
                )

            return Response({"data": job_postings_list}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecCompleteJob(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request, job_id):
        try:
            job = JobPostings.objects.get(id=job_id)
            serializer = JobPostingsSerializer(job)

            return Response({"jd": serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f" {str(e)}")
            return Response(
                {"detail": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
            )


class RecJobDetails(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request, job_id):
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job = AssignedJobs.objects.get(id=job_id, job_id__organization=org).job_id
            serializer = JobPostingsSerializer(job)

            resume_count = JobApplication.objects.filter(
                job_location__job_id=job, attached_to=user
            ).count()

            try:
                summary = summarize_jd(job)
            except:
                summary = ""
            return Response(
                {
                    "jd": serializer.data,
                    "summary": summary,
                    "count": resume_count,
                    "job_status": job.status,
                    "can_add_new": can_upload_new(org.id),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f" {str(e)}")
            return Response(
                {"detail": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
            )


class OrganizationApplications(APIView):
    permission_classes = [IsRecruiter]
    pagination_class = TenResultsPagination

    def get(self, request):
        try:
            job_id = request.GET.get("job_id")
            if request.GET.get("application_id"):
                try:
                    application_id = request.GET.get("application_id")
                    application = JobApplication.objects.get(id=application_id)
                    resume = application.resume
                    application_json = {
                        "candidate_name": resume.candidate_name,
                        "candidate_email": resume.candidate_email,
                        "date_of_birth": str(resume.date_of_birth),
                        "contact_number": resume.contact_number,
                        "alternate_contact_number": resume.alternate_contact_number,
                        "job_status": resume.job_status,
                        "experience": (
                            float(resume.experience) if resume.experience else None
                        ),  # Convert Decimal to float
                        "other_details": resume.other_details,
                        "current_ctc": (
                            float(resume.current_ctc) if resume.current_ctc else None
                        ),  # Convert Decimal to float
                        "expected_ctc": (
                            float(resume.expected_ctc) if resume.expected_ctc else None
                        ),  # Convert Decimal to float
                        "notice_period": resume.notice_period,
                        "highest_qualification": resume.highest_qualification,
                        "current_organization": resume.current_organisation,
                        "current_job_location": resume.current_job_location,
                        "current_job_type": resume.current_job_type,
                        "joining_days_required": resume.joining_days_required,
                        "resume": (
                            resume.resume.url if resume.resume else None
                        ),  # Get URL of the file
                    }
                    return JsonResponse(
                        application_json,
                        json_dumps_params={"ensure_ascii": False},
                        safe=False,
                    )  # Ensure encoding is handled properly
                except JobApplication.DoesNotExist:
                    return Response(
                        {"error": "Application not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                except Exception as e:
                    print(str)
                    return Response(
                        {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                recruiter_id = request.user.id
                organization = Organization.objects.filter(
                    recruiters__id=recruiter_id
                ).first()
                job_postings = JobPostings.objects.filter(
                    organization=organization
                ).exclude(id=job_id)
                organization_applications = JobApplication.objects.filter(
                    job_location__job_id__in=job_postings
                ).exclude(status="selected")

                application_list = []
                paginator = self.pagination_class()
                paginated_applications = paginator.paginate_queryset(
                    organization_applications, request
                )
                for application in paginated_applications:
                    application_json = {
                        "candidate_name": application.resume.candidate_name,
                        "job_department": application.job_location.job_id.job_department,
                        "status": application.status,
                        "application_id": application.id,
                        "cand_number": application.resume.contact_number,
                        "job_title": application.job_location.job_id.job_title,
                        "resume_url": application.resume.resume.url,
                        "resume_name": application.resume.resume.name,
                    }
                    application_list.append(application_json)

                return paginator.get_paginated_response(application_list)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_200_OK)


class ResumesSent(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            assigned_id = request.GET.get("job_id")

            org = Organization.objects.filter(recruiters__id=user.id).first()
            if not org:
                return Response({"error": "Organization not found"}, status=404)

            # Base query: applications handled by this recruiter
            applications = JobApplication.all_objects.filter(attached_to=user)

            if assigned_id:
                # If a specific assigned job is requested, filter by it
                job_assigned = AssignedJobs.objects.filter(
                    job_id__organization=org, assigned_to=user, id=assigned_id
                ).first()

                if not job_assigned:
                    return Response(
                        {"error": "Job posting not found or not assigned to you"},
                        status=404,
                    )

                applications = applications.filter(
                    job_location=job_assigned.job_location
                )

            applications_data = [
                {
                    "candidate_name": app.resume.candidate_name,
                    "email": app.resume.candidate_email,
                    "contact_number": app.resume.contact_number,
                    "status": app.status,
                    "app_sent_date": app.created_at,
                    "application_id": app.id,
                    "application_closed": app.is_closed,
                    "job_title": app.job_location.job_id.job_title,
                    "client_name": (
                        app.job_location.job_id.username.username
                        if hasattr(app.job_location.job_id.username, "username")
                        else str(app.job_location.job_id.username)
                    ),
                    "job_id": app.job_location.job_id.id,
                }
                for app in applications
            ]

            job_edit_status = False
            if assigned_id:
                job_assigned = AssignedJobs.objects.filter(id=assigned_id).first()
                if job_assigned:
                    job_edit_status = job_assigned.job_id.is_edited_by_client

            return Response(
                {
                    "applications": applications_data,
                    "is_edited_by_client": job_edit_status,
                },
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RecruiterAllAlerts(APIView):
    def get(self, request):
        try:
            all_alerts = Notifications.objects.filter(seen=False, receiver=request.user)
            assign_job = 0
            shortlist_candidate = 0
            promote_candidate = 0
            reject_candidate = 0
            select_candidate = 0
            join_candidate = 0
            accepted_ctc = 0
            candidate_accepted = 0
            candidate_rejected = 0
            candidate_left = 0
            schedule_interview = 0

            for alert in all_alerts:
                if alert.category == Notifications.CategoryChoices.ASSIGN_JOB:
                    assign_job += 1
                elif (
                    alert.category
                    == Notifications.CategoryChoices.SHORTLIST_APPLICATION
                ):
                    shortlist_candidate += 1
                elif alert.category == Notifications.CategoryChoices.PROMOTE_CANDIDATE:
                    promote_candidate += 1
                elif alert.category == Notifications.CategoryChoices.SCHEDULE_INTERVIEW:
                    schedule_interview += 1
                elif alert.category == Notifications.CategoryChoices.REJECT_CANDIDATE:
                    reject_candidate += 1
                elif alert.category == Notifications.CategoryChoices.SELECT_CANDIDATE:
                    select_candidate += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_JOINED:
                    join_candidate += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPTED_CTC:
                    accepted_ctc += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_ACCEPTED:
                    candidate_accepted += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_REJECTED:
                    candidate_rejected += 1
                elif alert.category == Notifications.CategoryChoices.CANDIDATE_LEFT:
                    candidate_left += 1

            # Job counts
            active_jobs = AssignedJobs.objects.filter(
                assigned_to=request.user,
                job_id__status="Open",
                job_id__approval_status="accepted",
            ).count()
            history_jobs = AssignedJobs.objects.filter(
                assigned_to=request.user,
                job_id__status="Closed",
                job_id__approval_status="accepted",
            ).count()

            # Application counts
            to_schedule = (
                JobApplication.objects.filter(
                    attached_to=request.user,
                    status="processing",
                )
                .filter(
                    Q(next_interview__isnull=True) | Q(next_interview__status="pending")
                )
                .filter(is_closed=False)
                .count()
            )
            already_scheduled = (
                JobApplication.objects.filter(
                    attached_to=request.user,
                    next_interview__isnull=False,
                    is_closed=False,
                )
                .exclude(next_interview__status="pending")
                .count()
            )

            # Reconfirmation counts
            reconfirm = SelectedCandidates.objects.filter(
                application__attached_to=request.user,
                application__status="selected",
                reconfirmed_by_recruiter=False,
                application__job_location__job_id__approval_status="accepted",
            ).count()

            # Replacement counts
            replacement = ReplacementCandidates.objects.filter(
                replacement_with__attached_to=request.user, status="pending"
            ).count()

            data = {
                "assign_job": assign_job,
                "shortlist_candidate": shortlist_candidate,
                "promote_candidate": promote_candidate,
                "reject_candidate": reject_candidate,
                "select_candidate": select_candidate,
                "join_candidate": join_candidate,
                "accepted_ctc": accepted_ctc,
                "candidate_accepted": candidate_accepted,
                "candidate_rejected": candidate_rejected,
                "candidate_left": candidate_left,
                "schedule_interview": schedule_interview,
                "total_alerts": all_alerts.count(),
                "active_jobs": active_jobs,
                "history_jobs": history_jobs,
                "to_schedule": to_schedule,
                "already_scheduled": already_scheduled,
                "reconfirm": reconfirm,
                "replacement": replacement,
            }

            return Response({"data": data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IncomingApplicationsView(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            assigned_job_id = request.GET.get("job_id")
            location = request.GET.get("location")
            application_id = request.GET.get("application_id")

            if not assigned_job_id:
                return Response(
                    {"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            assigned_job = AssignedJobs.objects.get(id=assigned_job_id)

            if application_id:
                try:
                    application = JobApplication.objects.get(id=application_id)
                    resume = application.resume

                    if application.sender or application.attached_to:
                        return Response(
                            {"error": "Application is already assigned"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    application_json = {
                        "id": application.id,
                        "resume_id": resume.id,
                        "candidate_name": resume.candidate_name,
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
                    }

                    primary_skills = SkillMetricsModel.objects.filter(
                        job_id=application.job_location.job_id, is_primary=True
                    ).values("skill_name")
                    secondary_skills = SkillMetricsModel.objects.filter(
                        job_id=application.job_location.job_id, is_primary=False
                    ).values("skill_name")

                    return Response(
                        {
                            "data": application_json,
                            "primary_skills": primary_skills,
                            "secondary_skills": secondary_skills,
                            "location_status": application.job_location.status,
                        },
                        status=status.HTTP_200_OK,
                    )

                except JobApplication.DoesNotExist:
                    print(str(e))
                    return Response(
                        {"error": "Application not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            applications = JobApplication.objects.filter(
                job_location__location=location,
                job_location=assigned_job.job_location,
                sender=None,
                attached_to=None,
            )

            serializer = IncomingApplicationSerializer(applications, many=True)
            return Response(
                {
                    "applications": serializer.data,
                    "is_edited_by_client": assigned_job.job_id.is_edited_by_client,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print(str(e))
            return Response(
                {"error": "Something went wrong. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        try:
            application_id = request.data.get("application_id")
            decision = request.data.get("decision")  # 'accepted' or 'rejected'

            if not application_id or not decision:
                return Response(
                    {"error": "application_id and decision are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if decision not in ["accepted", "rejected"]:
                return Response(
                    {"error": "Invalid decision value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application = JobApplication.objects.get(id=application_id)

            if application.sender or application.attached_to:
                return Response(
                    {"error": "Application is already assigned"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application.status = decision
            application.sender = request.user
            application.attached_to = request.user
            application.save()

            return Response(
                {"success": f"Application {decision} successfully"},
                status=status.HTTP_200_OK,
            )

        except JobApplication.DoesNotExist:
            return Response(
                {"error": "Application not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AcceptIncomingApplication(APIView):
    permission_classes = [IsRecruiter]

    def put(self, request):
        try:
            application_id = request.GET.get("id")

            data = request.data
            resume = JobApplication.objects.get(id=application_id).resume

            primary_skills = data.get("primary_skills", [])
            secondary_skills = data.get("secondary_skills", [])

            def update_skills(skills, is_primary):
                for skill in skills:
                    skill_name = skill.get("skill_name")
                    rating = skill.get("rating")
                    if skill_name is not None and rating is not None:
                        skill_obj = CandidateSkillSet.objects.filter(
                            candidate=resume,
                            skill_name=skill_name,
                            is_primary=is_primary,
                        ).first()
                        if skill_obj:
                            skill_obj.metric_value = str(rating)
                            skill_obj.save()
                        else:
                            CandidateSkillSet.objects.create(
                                candidate=resume,
                                skill_name=skill_name,
                                is_primary=is_primary,
                                skill_metric="rating",
                                metric_value=str(rating),
                            )

            update_skills(primary_skills, is_primary=True)
            update_skills(secondary_skills, is_primary=False)

            application = get_object_or_404(JobApplication, id=application_id)
            application.status = "pending"
            application.sender = request.user
            application.attached_to = request.user
            application.receiver = application.job_location.job_id.username
            application.save()

            return Response(
                {"message": "Data updated successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectIncomingApplication(APIView):
    permission_classes = [IsRecruiter]

    def put(self, request):
        try:
            application_id = request.GET.get("id")
            if not application_id:
                return Response(
                    {"error": "Application ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application = get_object_or_404(JobApplication, id=application_id)

            feedback = request.data.get("feedback", "")

            application.status = "rejected"
            application.feedback = feedback
            application.sender = request.user
            application.receiver = application.job_id.username
            application.attached_to = request.user
            application.save()

            return Response(
                {"message": "Application rejected successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReopenApplication(APIView):
    def put(self, request):
        try:
            application_id = request.GET.get("application_id")
            application = JobApplication.all_objects.get(id=application_id)
            application.is_closed = False
            application.save()
            return Response(
                {"message": "Application Reopened successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ViewCompleteCandidate(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            application_id = request.GET.get("application_id")
            application = JobApplication.objects.get(id=application_id)
            candidate_applications = JobApplication.all_objects.filter(
                resume__candidate_email=application.resume.candidate_email
            )
            applications_data = []
            for candidate_application in candidate_applications:
                applications_data.append(
                    {
                        "job_title": candidate_application.job_location.job_id.job_title,
                        "status": candidate_application.status,
                        "round_number": candidate_application.round_num,
                        "next_interview": (
                            candidate_application.next_interview.scheduled_date
                            if candidate_application.next_interview
                            else None
                        ),
                        "created_at": candidate_application.created_at,
                        "is_closed": candidate_application.is_closed,
                    }
                )
            candidate_data = {
                "applications_data": applications_data,
                "candidate_resume": application.resume.resume.url,
                "candidate_name": application.resume.candidate_name,
                "contact": application.resume.contact_number,
                "alternate_contact": application.resume.alternate_contact_number,
                "candidate_email": application.resume.candidate_email,
                "current_organization": application.resume.current_organisation,
                "currect_ctc": application.resume.current_ctc,
                "current_job_location": application.resume.current_job_location,
                "expected_ctc": application.resume.expected_ctc,
                "experience": application.resume.experience,
                "date_of_birth": application.resume.date_of_birth,
            }
            return Response({"data": candidate_data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReplacementsRequestedToRecruiter(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        try:
            replacements = ReplacementCandidates.objects.filter(
                replacement_with__attached_to=request.user, status="pending"
            )
            replacements_list = []
            for replacement in replacements:
                application = replacement.replacement_with
                job = application.job_location.job_id
                selected_candidate = SelectedCandidates.objects.get(
                    application=application
                )
                replacements_list.append(
                    {
                        "job_id": job.id,
                        "job_title": job.job_title,
                        "candidate_name": application.resume.candidate_name,
                        "accepted_ctc": selected_candidate.ctc,
                        "joining_date": selected_candidate.joining_date,
                        "left_reason": selected_candidate.left_reason,
                        "left_on": selected_candidate.resigned_date,
                        "application_id": application.id,
                        "replacement_id": replacement.id,
                        "replacement_status": replacement.status,
                    }
                )

            return Response({"data": replacements_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.fatal(f"Error in fetching replacements", e)
            return Response(
                {"error": "Error in fetching replacements"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
