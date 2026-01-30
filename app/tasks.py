# app_name/tasks.py

from celery import shared_task
from app.role_views.celery_views import *
from django.core.mail import EmailMessage


import time
from django.conf import settings

# @shared_task
# def my_function():
#     print(f'Function executed at {time.strftime("%Y-%m-%d %H:%M:%S")}')


@shared_task
def invoice_generated():
    print(f"Invoice is generated at {time.strftime('%Y-%m-%d %H:%M:%S')}")


@shared_task
def daily_tasks_runner():
    invoice_validate()


@shared_task
def remainders_task():
    print("here is remainders tasks called bro ")
    # remainders()


@shared_task(bind=True)
def approve_job_post_10_AM(self):
    try:
        approve_job_post_manager()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def send_celery_mail(self, subject, body, to_email):
    try:
        from_email = settings.DEFAULT_FROM_EMAIL

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=to_email if isinstance(to_email, list) else [to_email],
        )
        email.send(fail_silently=False)

    except Exception as e:
        print(f"Failed to send email: {e}")


@shared_task(bind=True)
def send_template_email_task(self, subject, template_name, context, recipient_list):
    """
    Asynchronous version of sendemailTemplate
    """
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.core.mail import EmailMultiAlternatives

    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject, text_content, settings.DEFAULT_FROM_EMAIL, recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Failed to send template email: {e}")
        return False


@shared_task(bind=True)
def send_html_email_task(self, subject, html_message, recipient_list):
    """
    Sends an HTML email asynchronously.
    """
    from django.core.mail import EmailMessage

    try:
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list if isinstance(recipient_list, list) else [recipient_list],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Failed to send HTML email: {e}")
        return False


@shared_task(bind=True)
def add_interview_remarks(self):
    try:
        process_interview_remarks()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def shortlist_application(self):
    try:
        process_shortlist_application_client()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def approve_negotation_request(self):
    try:
        process_approve_negotation_request()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def assign_job_post(self):
    try:
        process_assign_job_post()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def schedule_interview(self):
    try:
        process_schedule_interview()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def select_candidate_client(self):
    try:
        process_select_candidate_client()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def job_offer_candidate(self):
    try:
        process_job_offer_candidate()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def update_profile_candidate(self):
    try:
        process_update_profile_candidate()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def job_deadline(self):
    try:
        process_job_deadline()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def confirm_joining_client(self):
    try:
        process_confirm_joining_client()
        return "Job approval task executed successfully"
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Job approval task failed: {e}"


@shared_task(bind=True)
def notify_invoice_client_task(self, invoice_id):
    try:
        invoice = InvoiceGenerated.objects.get(id=invoice_id)

        if (
            getattr(invoice, "is_canceled", False)
            or invoice.invoice_status == InvoiceGenerated.SENT
        ):
            return "Invoice is canceled or already sent"

        subject = f"Invoice Reminder: Application #{invoice.application_id}"
        message = f"""Dear {invoice.client.email},

This is a reminder for your invoice of ₹{invoice.final_price} scheduled on {invoice.scheduled_date}.
"""

        send_custom_mail(subject, body=message, to_email=[invoice.client.user.email])

        invoice.invoice_status = InvoiceGenerated.SENT
        invoice.save()

        return "Invoice notification sent successfully"

    except InvoiceGenerated.DoesNotExist:
        return f"Invoice with ID {invoice_id} does not exist"

    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Retrying due to error: {e}"
