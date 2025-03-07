import secrets
import string
import json
import google.generativeai as genai
from django.conf import settings
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
import fitz
from django.template.loader import render_to_string
from docx import Document
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import six
from django.core.mail import send_mail
from .models import *
from decimal import Decimal

genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_passwrord(length=15):
    alphabet = string.ascii_letters + string.digits 
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def extract_text_from_file(file):
    if file.name.endswith('.pdf'):
        pdf = fitz.open(stream=file.read(), filetype='pdf')
        text = ''
        for page in pdf:
            text += page.get_text()
        pdf.close()
        return text
    elif file.name.endswith('.docx'):
        doc = Document(file)
        text = ''
        for paragraph in doc.paragraphs:
            text += paragraph.text + '\n'
        return text
    else:
        return "Unsupported file format. Please upload a PDF or DOCX file."


def summarize_jd(jd):
    model = genai.GenerativeModel("gemini-1.5-flash")

    
    job_title = jd.job_title
    job_department = jd.job_department
    job_description = jd.job_description.strip() if jd.job_description else None
    years_of_experience = jd.years_of_experience
    ctc = jd.ctc
    rounds_of_interview = jd.rounds_of_interview
    job_location = jd.job_location
    job_type = jd.job_type
    job_level = jd.job_level
    qualifications = jd.qualifications
    timings = jd.timings
    other_benefits = jd.other_benefits
    working_days = jd.working_days_per_week
    rotational_shift = "Yes" if jd.rotational_shift else "No"
    bond_details = jd.bond

    
    prompt = (
        f"Summarize the job posting for the role '{job_title}' in the '{job_department}' department. "
        f"The purpose of this summary is to help recruiters quickly understand the key aspects of the role and how to evaluate candidates effectively. "
        f"Base your summary on the following details:\n\n"
        f"Job Description: {job_description if job_description else 'Not provided or not detailed enough'}\n\n"
        f"Additional Job Details:\n"
        f"- Years of Experience: {years_of_experience} years.\n"
        f"- Compensation (CTC): {ctc}.\n"
        f"- Rounds of Interview: {rounds_of_interview}.\n"
        f"- Job Location: {job_location}.\n"
        f"- Job Type: {job_type}.\n"
        f"- Job Level: {job_level}.\n"
        f"- Required Qualifications: {qualifications}.\n"
        f"- Working Hours/Timings: {timings}.\n"
        f"- Other Benefits: {other_benefits if other_benefits else 'None specified'}.\n"
        f"- Working Days per Week: {working_days}.\n"
        f"- Rotational Shift: {rotational_shift}.\n"
        f"- Bond Details: {bond_details}.\n\n"
        f"Instructions:\n"
        f"1. If the job description is well-detailed, use it to infer the role's responsibilities.\n"
        f"2. If the job description is missing or unclear, infer responsibilities based on the job title, department, and other details provided.\n"
        f"3. Highlight key qualifications and requirements for screening candidates.\n"
        f"4. Provide other critical details recruiters should focus on during evaluation.\n\n"
        f"Return the summary as a numbered list."
    )

    
    response = model.generate_content(prompt)
    output = response.text  

    return output


def remove_first_last_line(input_string):
    lines = input_string.splitlines()
    if len(lines) <= 2:
        return ""  
    return "\n".join(lines[1:-1])

def generate_questions_with_gemini(jd):
    model = genai.GenerativeModel("gemini-1.5-flash")

    job_title = jd.job_title
    job_description = jd.job_description.strip() if jd.job_description else None
    years_of_experience = jd.years_of_experience
    primary_skills = jd.get_primary_skills_list()
    secondary_skills = jd.get_secondary_skills_list()

    skills = ", ".join(primary_skills + secondary_skills)

    prompt = (
        f"Generate 10 to 15 text-based questions to help a recruiter evaluate candidates for the job role '{job_title}'."
        f"based on the following job description and skills.\n\n"
        f"Job Description: {job_description if job_description else 'Not provided or insufficiently detailed'}\n\n"
        f"Skills required: {skills if skills else 'Not provided or insufficiently detailed'}\n\n"
        f"Years of experience required: {years_of_experience} years.\n\n"
        f"Generate the questions focusing on:\n"
        f"1. Validating the candidate’s experience and qualifications in the field.\n"
        f"2. Assessing problem-solving, critical thinking, and role-specific responsibilities.\n"
        f"3. Ensuring the candidate can effectively apply their knowledge in real-world scenarios.\n\n"
        f"4. Ensuring the candidate had all the skills mentioned.\n\n"
        f"Return the output as a list of dictionaries in the following format:\n\n"
        f"[{{\n"
        f"  'question_text': 'Your question here?',\n"
        f"  'correct_answer': 'Example answer here'\n"
        f"}}]"
    )

    response = model.generate_content(prompt)
    questions_output = response.text  
    questions_output = remove_first_last_line(questions_output)
    questions_output = json.loads(questions_output)
    
    return questions_output


def screen_profile_ai(jd, resume):
    """
    Screen a candidate's resume against the provided JobPostings object and generate targeted interview questions.

    Args:
        jd (JobPostings): The job posting object containing job details.
        resume (str): The candidate's resume in text format.

    Returns:
        str: A list of targeted interview questions with ideal answers based on the alignment between
             the resume and the job description.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    job_title = jd.job_title
    job_description = jd.job_description.strip() if jd.job_description else "No detailed job description provided."
    years_of_experience = jd.years_of_experience
    primary_skills = jd.get_primary_skills_list()
    secondary_skills = jd.get_secondary_skills_list()
    qualifications = jd.qualifications.strip() if jd.qualifications else "Not specified."
    job_location = jd.job_location
    job_type = jd.job_type
    job_level = jd.job_level

    skills = ", ".join(primary_skills + secondary_skills) if (primary_skills or secondary_skills) else "Not specified."

    prompt = f"""
        Evaluate the candidate's resume against the job description for the role '{job_title}' and generate targeted interview questions. Provide:  
        1. 25 to 40 interview questions tailored to both the resume and the job description.  
        2. For each question, provide an expected or ideal answer based on the alignment between the resume and the job description.  

        The questions should assess:  
        - Relevant skills: {skills}.  
        - Minimum experience of {years_of_experience} years or more.  
        - Qualifications: {qualifications}.  
        - Knowledge of industry-specific tools, practices, and methodologies.  
        - Behavioral and situational problem-solving abilities based on the job description and resume.  
        - Theoretical understanding of key technologies, frameworks, or methodologies (e.g., "What is RESTful API design?" or "Explain the importance of unit testing").  
        - Address gaps or missing qualifications to evaluate areas where the candidate might need improvement.  

        Ensure:  
        - Theoretical questions test the candidate's understanding of fundamentals.  
        - Situational questions evaluate practical application.  

        **Job Description Details:**  
        {job_description}  

        **Candidate Resume:**  
        {resume}  
        """

    response = model.generate_content(prompt)

    return response.text



def analyse_resume(jd, resume):
    model = genai.GenerativeModel("gemini-1.5-flash")

    job_title = jd.job_title
    job_description = jd.job_description.strip() if jd.job_description else "No detailed job description provided."
    years_of_experience = jd.years_of_experience
    primary_skills = jd.get_primary_skills_list()
    secondary_skills = jd.get_secondary_skills_list()
    qualifications = jd.qualifications.strip() if jd.qualifications else "Not specified."
    job_location = jd.job_location
    job_type = jd.job_type
    job_level = jd.job_level

    
    skills = ", ".join(primary_skills + secondary_skills) if (primary_skills or secondary_skills) else "Not specified."

    
    prompt = f"""
        Evaluate the candidate's resume against the job description for the role '{job_title}' and provide the following insights:

        1. **Compatibility Score**: Provide a score out of 100 for how well the resume matches the job description.
        2. **Areas of Alignment**: Highlight where the candidate's resume aligns with the job description, including:
            - Required skills: {skills}.
            - Experience: {years_of_experience} years or more.
            - Qualifications: {qualifications}.
            - Role-specific requirements from the job description.
        3. **Areas of Mismatch or Gaps**: Identify missing skills, qualifications, or areas where the resume doesn't meet the job requirements.
        4. **Suitability Summary**: Provide a concise summary of the candidate's overall suitability for the role, 
            considering the job location ({job_location}), job type ({job_type}), and job level ({job_level}).

        Ensure the evaluation is clear, relevant, and avoids verbose or unnecessary details.

        **Job Description Details:**  
        {job_description}

        **Candidate Resume:**  
        {resume}
    """

    
    response = model.generate_content(prompt)

    
    return response.text


def generate_invoice(context):
    html_content = render_to_string("invoice.html",context=context)
    return html_content

class EmailVerificatioinTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_verified)
    
email_verification_token = EmailVerificatioinTokenGenerator()


def send_email_verification_link(user,domain):

    print("enteredd")
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # domain = get_current_site(request).domain
    link = f"http://{domain}/verify-email/{uid}/{token}/"  
    message = f"""


Dear {user.username},

Welcome to **HireSync!** 🎉  
You're just one step away from getting started.

Please verify your email address by clicking the link below:

🔗 **[Verify My Email]({link})**

⚠️ *This link will expire in 20 minutes.*

If you didn’t sign up for HireSync, please ignore this email.

Best regards,  
**The HireSync Team**  
HireSync Inc.
"""
    send_mail(
        subject="Verify Your Email - HireSync",
        message=message,
        from_email="your-email@example.com",
        recipient_list=[user.email],
    )



def calculate_profile_percentage(candidate):
           
        fields_to_check = [
            'profile', 'about', 'email', 'first_name', 'middle_name', 'last_name',
            'communication_address', 'current_salary', 'expected_salary', 'joining_details',
            'permanent_address', 'phone_num', 'date_of_birth', 'designation', 'linked_in',
            'instagram', 'facebook', 'blood_group', 'experience_years', 'skills'
        ]
        
        total_fields = len(fields_to_check)
        filled_fields = sum(1 for field in fields_to_check if getattr(candidate, field))
        
        # Base profile percentage calculation
        base_profile_completion = (filled_fields / total_fields) * 80  
        
        # Additional weightage for documents and education
        document_completion = 10 if CandidateDocuments.objects.filter(candidate=candidate).exists() else 0
        education_completion = 10 if CandidateEducation.objects.filter(candidate=candidate).exists() else 0
        
        # Calculate total profile completion
        profile_completion = base_profile_completion + document_completion + education_completion
        
        return round(profile_completion, 2)
    
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

# Set up logging (you can also configure this in your Django settings)
logger = logging.getLogger(__name__)

def sendemailTemplate(subject, template_name, context, recipient_list):
    """
    Sends an HTML email with a text alternative.

    :param subject: The subject of the email
    :param template_name: The name of the template for the email content
    :param context: The context to render the template
    :param recipient_list: List of recipients to send the email to
    :return: True if email is sent, False otherwise
    """
    try:
        # Render the HTML content using the template and context
        html_content = render_to_string(template_name, context)

        # Generate plain text version of the email (for email clients that don't support HTML)
        text_content = strip_tags(html_content)

        # Create the email message
        email = EmailMultiAlternatives(
            subject, 
            text_content, 
            settings.DEFAULT_FROM_EMAIL,  # Use the default sender email from settings
            recipient_list
        )

        # Attach the HTML content as an alternative
        email.attach_alternative(html_content, "text/html")

        # Send the email
        email.send()

        # Log the success
        logger.info(f"Email sent successfully to: {', '.join(recipient_list)}")

        return True

    except Exception as e:
        # Log the error with details for debugging
        logger.error(f"Failed to send email to {', '.join(recipient_list)}. Error: {e}")

        return False
    
def calculate_invoice_amounts(selected_candidate, terms, client_gst, org_gst):
    ctc_in_lakhs = Decimal(str(selected_candidate.ctc))  
    ctc_in_actual = ctc_in_lakhs * Decimal('100000') 
    
    service_fee = (Decimal(str(terms.service_fee)) / Decimal('100')) * ctc_in_actual 
    
    def get_state_from_gst(gst_number):
        state_code = gst_number[:2]
        return state_code

    client_state = get_state_from_gst(client_gst)
    org_state = get_state_from_gst(org_gst)

    if client_state == org_state:
        sgst = (Decimal('9') / Decimal('100')) * service_fee
        cgst = (Decimal('9') / Decimal('100')) * service_fee
        igst = Decimal('0')  # No IGST if same state
    else:
        sgst = Decimal('0')
        cgst = Decimal('0')
        igst = (Decimal('18') / Decimal('100')) * service_fee  
        
    total_amount = service_fee + sgst + cgst + igst
    
    
    # Prepare the dictionary to return the values
    result = {
        "ctc": round(selected_candidate.ctc,2), 
        "service_fee": round(service_fee,2),  
        "sub_total": round(service_fee,2), 
        "sgst": round(sgst,2), 
        "cgst": round(cgst,2), 
        "igst": round(igst,2), 
        "total_amount": round(total_amount,2) 
    }
    
    return result

def create_invoice_context(invoice):
      # create_invoice_context(invoice)
    organization=invoice.organization
    job=invoice.application.job_id
    client_details = ClientDetails.objects.get(user = invoice.client)
    selected_candidate=SelectedCandidates.objects.get(application=invoice.application)
    terms=JobPostTerms.objects.get(job_id=invoice.application.job_id)
    result=calculate_invoice_amounts(selected_candidate,terms,client_details.gst_number,organization.gst_number)

    # Prepare invoice context
    context = {
        "url":"backend.hirsync",# make this dynamic 
        "invoice_id": f"{invoice.organization_id}/{invoice.client_id}/{invoice.id}/{invoice.created_at.date()}",  
        "date":invoice.created_at.date(),
        "service_provider_name": job.organization.name,
        "candidate_name":selected_candidate.candidate.name,
        "client_name": job.username.username,
        "client_email": job.username.email,
        "job_title": job.job_title,
        "buyer_address":client_details.company_address,
        "buyer_gst_no":client_details.gst_number,
        "buyer_contact_number":client_details.contact_number,
        "service_provider_address":job.organization.company_address,
        "service_provider_gstin":job.organization.gst_number,
        "service_provider_contact_person":job.organization.manager, #make this dynamic
        "service_provider_email":job.organization.manager.email,
        "service_provider_mobile":job.organization.contact_number,
        "service_description":"HSNCODE:9983",
        "date_of_joining":selected_candidate.joining_date,
        "ctc": selected_candidate.ctc, 
        "service_fee_percentage":terms.service_fee,
        "service_fee":result["service_fee"],
        "sub_total":result["sub_total"],
        "cgst":result["cgst"],
        "sgst":result["sgst"],
        "igst":result["igst"],
        # "date": now().date(), 
        "total_amount":result["total_amount"],
        # "payment_within": 32,
        # "service_fee_percentage":terms.interest_percentage,
        # "invoice_after": 12,
        # "replacement_clause": 23,
        # "email": job.username.email
    }
    return context
  

