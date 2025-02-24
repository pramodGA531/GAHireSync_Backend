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
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.timezone import now,is_aware, make_naive


class AgencyDashboardAPI(APIView):
    permission_classes = [IsManager]
    def get(self, request):
        try:
            user = request.user
            agency_name = Organization.objects.get(manager = user).name

            approval_pending = JobPostings.objects.filter(organization__name = agency_name, approval_status='pending').count()
            interviews_scheduled = JobApplication.objects.filter(job_id__organization__name=agency_name).exclude(next_interview=None).count()
            recruiter_allocation_pending = JobPostings.objects.filter(organization__name=agency_name, assigned_to=None).count()
            jobpost_edit_requests = JobPostingsEditedVersion.objects.filter(organization__name=agency_name).count()  
            opened_jobs = JobPostings.objects.filter(organization__name=agency_name, status='opened').count()

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
                "opened_jobs": opened_jobs
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
                    print(job.assigned_to)
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
                print("error here", str(e))
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
class OrgJobEdits(APIView):
    def get(self, request):
        try:
            user = request.user
            print('user is ', user)
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
        data = request.data
        username = request.user
        id = request.GET.get('id')
        # print(" is the job id")
        # if(id != data.get('job_post_id')):
        #     return Response({"details":"job post details are not matching"}, status = status.HTTP_400_BAD_REQUEST)
        organization = Organization.objects.filter(org_code=data.get('organization_code')).first()
        job = JobPostings.objects.get(id = id)
        if not username or username.role != 'manager':
            return Response({"detail": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST)

        if not organization:
            return Response({"detail": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not job:
            return Response({"detail":"Invalid Job ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            job_edited_post = JobPostingsEditedVersion.objects.get(id=id)
            if(job_edited_post) and job_edited_post.status != 'pending':
                job_edited_post.delete()
                InterviewerDetailsEditedVersion.objects.filter(job_id=id).delete()
        except JobPostingsEditedVersion.DoesNotExist:
            pass

        try:
            with transaction.atomic():
                interview_rounds = data.get('interview_details', [])
                client = JobPostings.objects.get(id=id).username
                client_email=client.email
                
                print("client",client)
                job_posting = JobPostingsEditedVersion.objects.create(
                    id = job,
                    username = client,
                    edited_by=username,
                    organization=organization,
                    job_title=data.get('job_title', ''),
                    job_department=data.get('job_department'),
                    job_description=data.get('job_description'),
                    primary_skills=data.get('primary_skills'),
                    secondary_skills=data.get('secondary_skills'),
                    years_of_experience=data.get('years_of_experience','Not Specified'),
                    ctc=data.get('ctc',"Not Specified"),
                    rounds_of_interview = len(interview_rounds),
                    job_locations=data.get('job_locations'),
                    job_type=data.get('job_type'),
                    job_level=data.get('job_level'),
                    qualifications=data.get('qualifications'),
                    timings=data.get('timings'),
                    other_benefits=data.get('other_benefits'),
                    working_days_per_week=data.get('working_days_per_week'),
                    decision_maker=data.get('decision_maker'),
                    decision_maker_email=data.get('decision_maker_email'),
                    bond=data.get('bond'),
                    rotational_shift = data.get('rotational_shift') == "yes",
                    age = data.get('age'),
                    gender = data.get('gender'), 
                    industry = data.get('industry'),
                    differently_abled = data.get('differently_abled'),
                    visa_status = data.get('visa_status'),
                    time_period = data.get('time_period'),
                    notice_period = data.get('notice_period'),
                    notice_time = data.get('notice_time',''),
                    qualification_department = data.get('qualification_department'),
                    languages = data.get('languages'),
                    num_of_positions = data.get('num_of_positions'),
                    job_close_duration  = data.get('job_close_duration'),
                    status = 'pending'
                )

                if interview_rounds:
                    for round_data in interview_rounds:
                        print(round_data)
                        name = CustomUser.objects.get(username = round_data.get('name').get('username'))
                        InterviewerDetailsEditedVersion.objects.create(
                            job_id=job_posting,
                            round_num=round_data.get('round_num'),
                            name=name,
                            type_of_interview=round_data.get('type_of_interview', ''),
                            mode_of_interview=round_data.get('mode_of_interview'),
                        )
                        
                client_message = f"""
                We would like to inform you that there has been a request to edit the job posting for "{job_posting.job_title}" with the following details:

                Please review the requested changes and update the job posting accordingly.

                Thank you for using our platform.

                Best regards,  
                The Recruitment Team
                """

                send_mail(
                    subject="Upadte In Job Posting",
                    message=client_message,
                    from_email='',
                    recipient_list=[client_email]
                )
            return Response(
                {"detail": "Job post and interview rounds edit request sent successfully"},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )



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

                subject = "Account Created on HireSync"
                message = f"""
Dear {username},

Welcome to HireSync! Your recruiter account has been successfully created.

Here are your account details:
Username: {username}
Email: {email}
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
                    from_email='',
                    recipient_list=[email],
                    fail_silently=False,
                )

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

                return Response({"detail": "Recruiters Assigned Successfully"}, status=status.HTTP_200_OK)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"detail": "One or more recruiters not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)



# Get All Recruiters 
class RecruitersList(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)

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
            print(request.user)

            if not jobs.exists():
                return Response({"noJobs": True}, status=status.HTTP_200_OK)
            
            invoices = []

            for job in jobs:
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
                # buffer = generate_invoice(context)
                # buffer.seek(0)

                # pdf_base64 = base64.b64encode(buffer.read()).decode('utf-8')

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

            print(recruiters_list)

            recent_activities = []
            resumes = JobApplication.objects.filter(sender__in=all_recruiters).order_by('-updated_at')[:6]
            for resume in resumes:
                task = ""
                if resume.status == 'pending':
                    task = f"{resume.resume.candidate_name}'s Resume is sent to {resume.job_id.job_title}"
                elif resume.status == 'processing' and resume.next_interview:
                    task = f"New meeting scheduled for {resume.resume.candidate_name}"
                

                time_diff = now() - resume.updated_at
                print(time_diff.seconds)
                if time_diff.seconds < 60:
                    thumbnail = f"Updated {time_diff.seconds} seconds ago"
                elif time_diff.seconds < 3600:
                    thumbnail = f"Updated {time_diff.seconds // 60} minutes ago"
                elif time_diff.seconds < 86400:
                    thumbnail = f"Updated {time_diff.seconds // 3600} hours ago"
                else:
                    thumbnail = f"Updated {time_diff.days} days ago"                                        


                recent_activities.append({
                    "name": resume.sender.username,
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