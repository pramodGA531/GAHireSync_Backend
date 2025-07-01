from django.http import JsonResponse
from app.models import *
from django.utils.timezone import now, timedelta
from django.core.mail import  EmailMessage
from app.utils import *
import logging
from datetime import date
from RTMAS_BACKEND import settings
from collections import defaultdict

logger = logging.getLogger(__name__) 
from_mail = settings.DEFAULT_FROM_EMAIL
today = date.today()


def invoice_validate(request=None):
    """Validates and generates invoices for joined candidates."""
    
    joined_candidates = SelectedCandidates.objects.filter(joining_status="joined")
    yesterday = now().date() - timedelta(days=1)  

    for joined_candidate in joined_candidates: 
        application = joined_candidate.application
        job = application.job_location.job_id
        try:
            terms = JobPostTerms.objects.get(job_id=job.id)

            joining_date = joined_candidate.joining_date  
            invoice_date = joining_date + timedelta(days=terms.invoice_after)

            invoice_exists = InvoiceGenerated.objects.filter(application=application).first()
            if invoice_exists:
                logger.info(f"Invoice already exists for application {application.id}, sending reminder...")
                invoice_reminder(job, application, joined_candidate, invoice_exists)  
            else:
                # if invoice_date == yesterday:  
                if 1==1:
                    try:
                        invoice_generated = InvoiceGenerated.objects.create(
                            application=application,
                            organization=job.organization,
                            organization_email=job.organization.manager.email if hasattr(job, 'organization') and hasattr(job.organization, 'manager') else None,
                            client=job.username,
                            client_email=job.username.email if hasattr(job, 'username') else None,
                            terms_id=terms.id
                        )
                        logger.info(f"Invoice generated for application {application.id}")

                        # Pass the newly created invoice to the reminder function
                        # invoice_reminder(job, application, joined_candidate, invoice_generated)

                        # Send invoice
                        calculate_send_invoice(job, application,"generate",invoice_generated)
                    except Exception as e:
                        logger.error(f"Error creating invoice for application {application.id}: {e}")
        except JobPostTerms.DoesNotExist:
            logger.warning(f"No terms found for job {job.id}")

    return JsonResponse({"status": "success"}, safe=False) if request else None

def remainders():
    print("fetch the all requests what are the img messages need to remaind")
    
    
def calculate_send_invoice(job,application,method,invoice):

    context=create_invoice_context(invoice)
    if method=="generate":
        subject=f"Invoice is generated here" 
        clientemail="ameerpotuganti2@gmail.com"
    else:
         subject=f"Invoice Reminder" 
         clientemail="ameerpotuganti2@gmail.com"

    sendemailTemplate(
                subject,
                'invoice.html',
                context,
                [clientemail]
            )

    

def invoice_reminder(job, application, selected_candidate, invoice):
    """Sends a reminder email if the invoice was created 7 days ago."""
    
    # reminder_date = invoice.created_at.date() + timedelta(days=7) => this is for production
    reminder_date =  invoice.created_at.date() 
    # yesterday=now().date()-timedelta(days=1)
    today=now().date()
    
    print(f"Invoice created on: {invoice.created_at.date()}, Reminder Date: {reminder_date}, todays's Date: {today}")

    if reminder_date == today:
        calculate_send_invoice(job, application, 'reminder', invoice)
    else:
        print("No reminder needed today.")

    # print("Job:", job)
    # print("Application:", application)
    # print("Selected Candidate:", selected_candidate)
    # print("Invoice:", invoice)


def approve_job_post_manager():
    try:
        job_postings = JobPostings.objects.filter(
            approval_status='pending',
            created_at__date__lt=today
        )

        manager_group = defaultdict(list)
        
        for job in job_postings:
            manager_group[job.organization].append(job)

        for organization, jobs in manager_group.items():
            
            jobs_details=[
                f"- {job.job_title} (Client: {job.username.username})"
                for job in jobs
            ]

            jobs_list = "\n".join(jobs_details)


            subject = "Approve the job post - client is waiting for your response"
            message = f"""
Dear {organization.manager.username},

A job post submitted by the client 
{jobs_list}
is currently awaiting your approval.

Kindly review and take appropriate action to activate the job post. Your timely response ensures a smooth hiring process.

Best regards,  
GA Hiresync Team
"""
            recipients_list = [organization.manager.email]

            email = EmailMessage(
                subject=subject,
                body=message,
                to=recipients_list,
                from_email=from_mail
            )
            email.send(fail_silently=False)

    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_approve_negotation_request():
    try:
        negotiations= NegotiationRequests.objects.filter(status = 'pending',requested_date__date__lt = today )
        grouped_negotiations = defaultdict(list)

        for negotiation in negotiations:
            grouped_negotiations[negotiation.organization].append(negotiation)

        for organization, negotiations in grouped_negotiations.items():

            clients_requests = [
                f"- {negotiation.client.username}"
                for negotiation in negotiations
            ]

            clients_list = "\n".join(clients_requests)

            subject = f"Negotiation request by for creating job posts"
            body = f'''
Dear {organization.manager.username},

A negotiation request from the clients
{clients_list}
regarding a job post is still awaiting your response.

Please review and address the negotiation request at your earliest convenience to proceed further.

Sincerely,  
GA Hiresync Team


'''
            recipients_list = [negotiation.organization.manager.email]
            
            email = EmailMessage(
                subject=subject,
                body=body,
                to=recipients_list,
                from_email=from_mail
            )
            email.send(fail_silently=False)
            
    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_assign_job_post():
    try:
        job_postings = JobPostings.objects.filter(created_at__date__lt = today, approval_status = "approved", status = 'opened')
        for job in job_postings:
            job_locations = set(JobLocationsModel.objects.filter(job_id = job).values_list('location', flat=True))
            assigned_locations = set(AssignedJobs.objects.filter(job_id = job, ).values_list('job_location__location', flat=True))

            unassigned_locations = job_locations- assigned_locations
            location_list = ", ".join(unassigned_locations)

            subject = f"Recruiter allocation pending for job {job.job_title}"
            body = f'''
Dear {job.organization.manager.username},

The job post titled {job.job_title} with locations {location_list}  is pending assignment to a recruiter.

Please assign the job post to the appropriate recruiter to initiate candidate sourcing.

Warm regards,  
GA Hiresync Team

'''
            recipients_list = [job.organization.manager.email]      
            email = EmailMessage(
                subject=subject,
                body=body,
                to=recipients_list,
                from_email=from_mail
            )
            email.send(fail_silently=False)
            
        
    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_shortlist_application_client():
    try:
        applications = JobApplication.objects.filter(status='pending', created_at__date__lt = today , job_location__status = 'opened')
        grouped_applications = defaultdict(list)
        for application in applications:
            grouped_applications[application.receiver].append(application)

        for client, applications in grouped_applications.items():
            
            candidate_names = [
                f"- {app.resume.candidate_name} (Job: {app.job_location.job_id.job_title})"
                for app in applications
            ]
            candidate_list = "\n".join(candidate_names)

            subject = "Pending Job Application Responses"

            body = f'''
Dear {client.username},

You have the following job applications pending your action:

{candidate_list}

Recruiters are waiting for your response. Please review and take necessary action.

Best regards,  
{applications[0].sender.organization} Team
'''         
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail, 
                to=[client.email],
            )
            email.send(fail_silently=True)

    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_schedule_interview():
    try:
        applications = JobApplication.objects.filter(status = 'processing', next_interview = None, job_location__status = 'opened')
        grouped_applications = defaultdict(list)

        for application in applications:
            grouped_applications[application.attached_to].append(application)
        
        for attached_to, applications in grouped_applications.items():
            application_details= [
                f"- {app.resume.candidate_name} (Job: {application.job_location.job_id.job_title})"
                for app in applications
            ]

            application_list = "\n".join(application_details)

            subject = f"Schedule Interview Pending"
            body = f"""
Dear {attached_to.username},

Please schedule the interview for the shortlisted candidate(s

{application_list}

Timely interview scheduling ensures a seamless hiring experience.

Thank you,  
GA HireSync Team

"""
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail, 
                to=[attached_to.email],
            )
            email.send(fail_silently=True)

    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))
        

    

def process_interview_remarks():
    try:
        scheduled_interviews = InterviewSchedule.objects.filter(scheduled_date__lt = today,status = 'scheduled')
        grouped_interviews = defaultdict(list)
        logger.info(f" running this function {scheduled_interviews.count()} is the count of pending remarks")

        for interview in scheduled_interviews:
            grouped_interviews[interview.interviewer.name].append(interview)

        for interviewer, interviews in grouped_interviews.items():
            candidate_details = [
                f"- {interview.candidate.candidate_name} (Job: {interview.job_location.job_id.job_title})"
                for interview in interviews
            ]

            candidate_list = "\n".join(candidate_details)

            subject = "Add Interview Remarks"

            body = f"""

Dear {interviewer.username},

Your remarks for the recently conducted interview with candidates 
{candidate_list}
are still pending.

Please submit your feedback to help continue the evaluation process.

Kind regards,  
GA HireSync Team

"""
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail, 
                to=[interviewer.email],
            )
            email.send(fail_silently=True)

    except Exception as e:
        logger.error("Error in process interviews:", str(e))


def process_select_candidate_client():
    try:
        subject = "Update the status of the candidate"
        candidates_on_hold = JobApplication.objects.filter(status='hold', job_location__status = 'opened',updated_at__date__lt = today)
        grouped_applications = defaultdict(list)
        for application in candidates_on_hold:
            grouped_applications[application.receiver].append(application)

        for client, applications in grouped_applications.items():
            
            candidate_names = [
                f"- {app.resume.candidate_name} (Job: {app.job_location.job_id.job_title})"
                for app in applications
            ]
            candidate_list = "\n".join(candidate_names)

            body = f'''
Dear {client.username},

All interview rounds for candidate 
{candidate_list}
have been completed. Kindly confirm if you wish to move forward with the selection.

Your decision is required to complete the process.

Best regards,  
{application.sender.organization} Team
'''         
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail, 
                to=[client.email],
            )
            email.send(fail_silently=True)


    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_job_offer_candidate():
    try:
        subject = "Accept the job post"
        selected_candidates = SelectedCandidates.objects.filter(joining_status = "pending", application__job_location__status = 'opened',candidate_acceptance='pending' )
        for candidate in selected_candidates:
            candidate_details = candidate.candidate.name
            body = f"""
Dear {candidate_details.username},

You have received an offer for the position {candidate.application.job_location.job_id.job_title}. Please confirm your acceptance and joining date.

Your prompt response is appreciated.

Sincerely,  
{candidate.application.job_location.job_id.organization.manager.username} Team

"""
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail, 
                to=[candidate_details.email],
            )
            email.send(fail_silently=True)
            
    except Exception as e:
        logger.error("Error in activate_job_post:", str(e))


def process_update_profile_candidate():
    try:
        threshold_date = now() - timedelta(days=5)

        candidates = CandidateProfile.objects.filter(updated_at__lt=threshold_date)

        for candidate in candidates:
            subject = "Reminder: Please update your candidate profile"
            body = f'''
Dear {candidate.name.username},

We noticed that your candidate profile hasn't been updated recently.

Keeping your profile up-to-date helps recruiters find the right match for you.

Please take a few minutes to log in and update your details such as:
- Skills
- Current & Expected Salary
- Experience and Designation
- Resume

Update your profile here: [YourProfileLink]

Thank you,  
[Your System Name] Team
'''
        email = EmailMessage(
                subject = subject,
                body=body,
                from_email=from_mail,
                to=[candidate.email]
        )
        email.send(fail_silently=False)

    except Exception as e:
        logger.error("Error in update_profile_candidate: %s", str(e))

def process_job_deadline():
    try:
        five_days = timezone.now() + timedelta(days=5)

        jobs = JobPostings.objects.filter(
            status='opened',
            job_close_duration__lt=five_days
        )

        grouped_postings = defaultdict(list)     
        grouped_recruiters = defaultdict(list)   

        for job in jobs:
            grouped_postings[job.organization].append(job)

            assigned_jobs = AssignedJobs.objects.filter(
                job_id=job,
                job_location__status='opened',
            ).prefetch_related('assigned_to')  

            for assign in assigned_jobs:
                for recruiter in assign.assigned_to.all():
                    grouped_recruiters[recruiter].append((assign.job_id, assign.job_location))

        # Notify Organizations
        for organization, job_list in grouped_postings.items():
            jobs_text = "\n".join(
                f"- {job.job_title} (Deadline: {job.job_close_duration.strftime('%Y-%m-%d')})"
                for job in job_list
            )

            subject = "Upcoming Job Post Deadlines"
            body = f"""
Dear {organization.manager.username},

The following job posts are approaching their deadlines:

{jobs_text}

Please ensure that all necessary actions are completed before their closing dates.

Thank you,  
GA Hiresync Team
"""

            EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail,
                to=[organization.manager.email]
            ).send(fail_silently=True)

        # Notify Recruiters
        for recruiter, job_locations in grouped_recruiters.items():
            jobs_text = "\n".join(
                f"- {job.job_title} (Location: {location.location}, Deadline: {job.job_close_duration.strftime('%Y-%m-%d')})"
                for job, location in job_locations
            )

            subject = "Jobs Nearing Deadline Assigned to You"
            body = f"""
Dear {recruiter.username},

The following job assignments allocated to you are approaching their deadlines:

{jobs_text}

Please take prompt actions to ensure closure before the deadline.

Regards,  
GA Hiresync Team
"""

            EmailMessage(
                subject=subject,
                body=body,
                from_email=from_mail,
                to=[recruiter.email]
            ).send(fail_silently=True)

    except Exception as e:
        logger.error("Error in job_deadline: %s", str(e))

def process_confirm_joining_client():
    try:
        selected_candidates = SelectedCandidates.objects.filter(joining_status='pending',joining_date__lt = today )
        selected_candidate_groups = defaultdict(list)


        for candidate in selected_candidates:
            selected_candidate_groups[candidate.application.receiver].append(candidate)


        for client, candidates in selected_candidate_groups.items():


            candidate_details = [
                f"- {candidate} (Job: {candidate.application.job_location.job_id.job_title})" 
                for candidate in candidates
            ]

            candidate_list = "\n".join(candidate_details)

            subject = "Is Candidate joined"

            body = f'''
Dear {client.username},

Please confirm whether the candidates
{candidate_list}
has joined as per the scheduled date.

Your confirmation is important for record-keeping and invoicing.

Sincerely,  
GA Hiresync Team

'''
            email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=from_mail,
                    to = [client.email]
                )
            email.send(fail_silently=True)   

    except Exception as e:
        logger.error("Error in proccessing confirm joining: %s", str(e))
