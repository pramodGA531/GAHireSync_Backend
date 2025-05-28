from django.http import JsonResponse
from app.models import SelectedCandidates, JobPostTerms, InvoiceGenerated, ClientDetails,CandidateProfile,Organization
from django.utils.timezone import now, timedelta
from django.core.mail import send_mail, EmailMessage
from app.utils import generate_invoice,sendemailTemplate,calculate_invoice_amounts,create_invoice_context
import logging

logger = logging.getLogger(__name__)  # Use Django logging instead of print()


def invoice_validate(request=None):
    """Validates and generates invoices for joined candidates."""
    
    joined_candidates = SelectedCandidates.objects.filter(joining_status="joined")
    yesterday = now().date() - timedelta(days=1)  

    for joined_candidate in joined_candidates: 
        application = joined_candidate.application
        job = application.job_id
        try:
            # Get job terms
            terms = JobPostTerms.objects.get(job_id=job.id)
            logger.info(f"Terms found for job {job.id}: {terms}")

            # Get joining date and calculate invoice date
            joining_date = joined_candidate.joining_date  
            invoice_date = joining_date + timedelta(days=terms.invoice_after)
            logger.info(f"Joining date: {joining_date}, Invoice date: {invoice_date}, Yesterday: {yesterday}")

            # Check if invoice already exists
            invoice_exists = InvoiceGenerated.objects.filter(application=application).first()
            if invoice_exists:
                logger.info(f"Invoice already exists for application {application.id}, sending reminder...")
                invoice_reminder(job, application, joined_candidate, invoice_exists)  # Added parameter
            else:
                # if invoice_date == yesterday:  # Correct condition to generate invoice
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
    # This function is called every day at 8:00 AM to send reminders for invoices that
    # are due today or have been due in the past 7 days but haven't been sent
    print("fetch the all requests what are the img messages need to remaind")
    
    
def calculate_send_invoice(job,application,method,invoice):
    # print("Fetching organization_email and client_email for invoice.")
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
    
    # print(f"Invoice email sent to {clientemail}")
    

def invoice_reminder(job, application, selected_candidate, invoice):
    """Sends a reminder email if the invoice was created 7 days ago."""
    
    # reminder_date = invoice.created_at.date() + timedelta(days=7) => this is for production
    reminder_date =  invoice.created_at.date() 
    # yesterday=now().date()-timedelta(days=1)
    today=now().date()
    
    print(f"Invoice created on: {invoice.created_at.date()}, Reminder Date: {reminder_date}, todays's Date: {today}")

    if reminder_date == today:
        print("Sending reminder email...")
        calculate_send_invoice(job, application, 'reminder', invoice)
    else:
        print("No reminder needed today.")

    # print("Job:", job)
    # print("Application:", application)
    # print("Selected Candidate:", selected_candidate)
    # print("Invoice:", invoice)