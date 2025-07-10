import secrets
import string
import json
import google.generativeai as genai
from django.conf import settings
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives, EmailMessage
import fitz
from django.template.loader import render_to_string
from docx import Document
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
import six
from rest_framework.pagination import PageNumberPagination
from .models import *
from decimal import Decimal
import re
import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
from pdf2image import convert_from_path
import uuid
from django.http import JsonResponse, Http404
from django.db.models import Q


genai.configure(api_key=settings.GEMINI_API_KEY)
frontend_url = os.environ['FRONTENDURL']


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

    print(output, " is the output")
    return output


def remove_first_last_line(input_string):
    lines = input_string.splitlines()
    if len(lines) <= 2:
        return ""  
    return "\n".join(lines[1:-1])

def extract_json(response_text):
    """Extract JSON content from the response, handling cases where it's inside a code block."""
    match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
    return match.group(1) if match else response_text

def generate_questions_with_gemini(jd):
    model = genai.GenerativeModel("gemini-1.5-flash")

    job_title = jd.job_title
    job_description = jd.job_description.strip() if jd.job_description else "Not provided or insufficiently detailed"
    years_of_experience = jd.years_of_experience

    primary_skills = SkillMetricsModel.objects.filter(job_id=jd, is_primary=True)
    secondary_skills = SkillMetricsModel.objects.filter(job_id=jd, is_primary=False)

    primary_skill_list = [
        f"- {skill.skill_name} (Metric: {skill.metric_type}, Value: {skill.metric_value})"
        for skill in primary_skills
    ] or ["- No primary skills provided"]

    secondary_skill_list = [
        f"- {skill.skill_name} (Metric: {skill.metric_type}, Value: {skill.metric_value})"
        for skill in secondary_skills
    ] or ["- No secondary skills provided"]

    prompt = (
        f"Generate 10 to 15 text-based questions to help a recruiter evaluate candidates for the job role '{job_title}'.\n\n"
        f"**Job Description:**\n{job_description}\n\n"
        f"**Primary Skills Required:**\n" + "\n".join(primary_skill_list) + "\n\n"
        f"**Secondary Skills Required:**\n" + "\n".join(secondary_skill_list) + "\n\n"
        f"**Years of Experience Required:** {years_of_experience} years.\n\n"
        f"### Instructions for Question Generation:\n"
        f"1. Validate the candidate’s experience and qualifications.\n"
        f"2. Assess problem-solving, critical thinking, and role-specific knowledge.\n"
        f"3. Ensure the candidate can apply their knowledge in real-world scenarios.\n"
        f"4. Verify the candidate possesses the mentioned skills.\n\n"
        f"### Output Format:\n"
        f"Return a list of dictionaries in the following format:\n"
        f"[\n"
        f"  {{\n"
        f"    'question_text': 'Your question here?',\n"
        f"    'correct_answer': 'Example answer here'\n"
        f"  }}\n"
        f"]"
    )

    response = model.generate_content(prompt)
    
    # Extract and clean JSON from response
    raw_output = response.candidates[0].content.parts[0].text
    clean_json_text = extract_json(raw_output)

    try:
        questions_output = json.loads(clean_json_text)
        return questions_output
    except json.JSONDecodeError:
        return {"error": "Invalid response format from AI. Extracted JSON was: " + clean_json_text}


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
    qualifications = jd.qualifications.strip() if jd.qualifications else "Not specified."
    job_type = jd.job_type
    job_level = jd.job_level
    primary_skills = SkillMetricsModel.objects.filter(job_id=jd, is_primary=True)
    secondary_skills = SkillMetricsModel.objects.filter(job_id=jd, is_primary=False)

    primary_skill_list = [
        f"- {skill.skill_name} (Metric: {skill.metric_type}, Value: {skill.metric_value})"
        for skill in primary_skills
    ] or ["- No primary skills provided"]

    secondary_skill_list = [
        f"- {skill.skill_name} (Metric: {skill.metric_type}, Value: {skill.metric_value})"
        for skill in secondary_skills
    ] or ["- No secondary skills provided"]

    prompt = f"""
        Evaluate the candidate's resume against the job description for the role **'{job_title}'** and provide the following insights:

### 1. **Compatibility Score**  
Provide a score out of 100 indicating how well the resume matches the job description. Consider factors such as skills, experience, and qualifications.

### 2. **Areas of Alignment**  
Highlight the strengths of the candidate in relation to the job description, including:  
   - **Primary Skills:** {primary_skill_list}  
   - **Secondary Skills:** {secondary_skill_list}  
   - **Experience:** At least {years_of_experience} years  
   - **Qualifications:** {qualifications}  
   - **Other key requirements** from the job description  

For each skill, provide:
   - **Field Name**
   - **Score (out of 10)**
   - **Reason for the score**

### 3. **Areas of Mismatch or Gaps**  
Identify missing skills, qualifications, or areas where the resume falls short of the job requirements.

### 4. **Suitability Summary**  
Provide a concise summary of the candidate’s overall suitability for the role, considering factors such as:  
   - **Job Type:** {job_type}  
   - **Job Level:** {job_level}  
   - **Overall Fit:** Should the candidate be shortlisted for an interview? Why or why not?

Ensure the evaluation is structured, objective, and avoids excessive verbosity.

---

#### **Job Description Details:**  
{job_description}  

#### **Candidate Resume:**  
{resume}  
    """
    response = model.generate_content(prompt)
    ai_response = response.text
    
    parsed_response = parse_ai_response(ai_response)
    return json.dumps(parsed_response, indent=2)


def parse_ai_response(ai_text):
    lines = ai_text.split("\n")
    skills_data = []
    overall_score = None
    overall_reason = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "Compatibility Score:" in line:
            overall_score = line.split(":")[-1].strip()
        elif any(keyword in line for keyword in ["Primary Skills", "Secondary Skills", "Experience", "Qualifications", "Other Key Requirements"]):
            parts = line.split(":", 1)
            if len(parts) < 2:
                continue  # Skip malformed lines
                
            field_name = parts[0].strip()
            score_info = parts[1].strip()
            score = "Not provided"
            reason = "No detailed reason provided."
            
            if "(" in score_info:
                score_parts = score_info.split("(")
                if len(score_parts) > 1:
                    score = score_parts[0].strip()
            
            skills_data.append({"field_name": field_name, "score": score, "reason": reason})
        elif "Overall Fit:" in line:
            overall_reason = line.split(":", 1)[-1].strip()
    
    return {
        "skills": skills_data,
        "overall_resume_score": {
            "score": overall_score if overall_score else "Not provided",
            "reason": overall_reason
        }
    }


def generate_invoice(context):
    html_content = render_to_string("invoice.html",context=context)
    return html_content

class EmailVerificatioinTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_verified)
    
email_verification_token = EmailVerificatioinTokenGenerator()


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


class TenResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10
    
    
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
        "service_provider_contact_person":job.organization.manager, 
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
        html_content = render_to_string(template_name, context)

        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject, 
            text_content, 
            settings.DEFAULT_FROM_EMAIL,  
            recipient_list
        )

        email.attach_alternative(html_content, "text/html")
        email.send()
        logger.info(f"Email sent successfully to: {', '.join(recipient_list)}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {', '.join(recipient_list)}. Error: {e}")
        return False

def send_custom_mail(subject, body, to_email):
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



def send_email_verification_link(user, signup, role, password = None):

    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    link = f"{frontend_url}/verify-email/{uid}/{token}/" 

    if signup == False: 
        message = f"""

    Dear {user.username},

    Welcome to HireSync! To complete your registration, please verify your email address by clicking the link below:
    🔗 {link}

    If you didn’t sign up, please disregard this email. Need assistance? Reach out at support@hiresync.com.

    Best,
    HireSync Team

    """
    subject = "Verify Your Email – Welcome to HireSync"
    
    if signup: 

        if role == 'client':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your client account on HireSync has been successfully created.
You can now post jobs seamlessly.

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team
    
""" 
        if role == 'manager':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your account on HireSync has been successfully created.

You can now manage your job posts seamlessly.

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == 'recruiter':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your recruiter account on HireSync has been successfully created.

You can now send applications/schedule interviews seamlessly.

Password : {password}

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == 'interviewer':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your interviewer account on HireSync has been successfully created.

You can now send conduct interviews seamlessly.

Password : {password}

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == 'candidate':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your candidate account on HireSync has been successfully created.

You can now send apply jobs seamlessly.

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == 'accountant':
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your accountant account on HireSync has been successfully created.

You can now send apply jobs seamlessly.

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""

    send_custom_mail(
        subject=subject,
        body=message,
        to_email=[user.email],
    )
 



def convert_pdf_to_images(request):
    # resume_path = request.GET.get('resume')
    pdf_url = request.GET.get('resume')  # e.g., "media/88/resume.pdf" or "/media/88/resume.pdf"

    if not pdf_url:
        return JsonResponse({'error': 'Missing resume path'}, status=400)

    # Remove '/media/' from the URL and join with MEDIA_ROOT
    pdf_rel_path = pdf_url.replace('/media/', '').replace('media/', '')
    pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_rel_path)

    if not os.path.exists(pdf_path):
        raise Http404("Resume file not found.")

    # Output folder for generated images
    output_folder_uuid = str(uuid.uuid4())
    output_folder = os.path.join(settings.MEDIA_ROOT, 'resume_images', output_folder_uuid)
    os.makedirs(output_folder, exist_ok=True)

    try:
        images = convert_from_path(pdf_path, dpi=150)
    except Exception as e:
        return JsonResponse({'error': f'Failed to convert PDF: {str(e)}'}, status=500)

    # Generate image URLs relative to MEDIA_URL
    image_urls = []
    for i, image in enumerate(images):
        image_filename = f'page_{i + 1}.jpg'
        image_path = os.path.join(output_folder, image_filename)
        image.save(image_path, 'JPEG')

        relative_url = os.path.join(settings.MEDIA_URL, 'resume_images', output_folder_uuid, image_filename)
        image_urls.append(relative_url)

    return JsonResponse({"images": image_urls})


def get_resume_storage_usage(manager_user):
    total_size_bytes = 0

    # Get all resumes under the manager's org
    applications = JobApplication.objects.filter(
        job_location__job_id__organization__manager=manager_user
    ).select_related('resume')

    seen_files = set() 

    for app in applications:
        resume = app.resume
        if resume and resume.resume and resume.resume.name not in seen_files:
            try:
                file_path = os.path.join(settings.MEDIA_ROOT, resume.resume.name)
                if os.path.isfile(file_path):
                    total_size_bytes += os.path.getsize(file_path)
                    seen_files.add(resume.resume.name)
            except Exception as e:
                print(f"Error accessing file: {resume.resume.name}, {e}")

    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

    return {
        'total_size_bytes': total_size_bytes,
        'total_size_mb': total_size_mb,
        'total_files': len(seen_files)
    }
def get_invoice_terms(selected_application_id):
    from decimal import Decimal

    selected_application = SelectedCandidates.objects.get(id=selected_application_id)
    job = selected_application.application.job_location.job_id
    job_terms = JobPostTerms.objects.filter(job_id=job)

    selected_ctc = float(selected_application.ctc)

    def parse_ctc_range(ctc_range_str):
        try:
            clean_range = ctc_range_str.replace("LPA", "").replace(" ", "")
            min_str, max_str = clean_range.split("-")
            return float(min_str), float(max_str)
        except Exception as e:
            raise ValueError(f"Invalid CTC range format: '{ctc_range_str}'")

    # Step 1: Try negotiated terms first
    try:
        negotiated_terms = job_terms.get(is_negotiated=True)
        min_ctc, max_ctc = parse_ctc_range(negotiated_terms.ctc_range)

        if selected_ctc <= max_ctc:
            service_fee = float(negotiated_terms.service_fee)
            invoice_amount = round((selected_ctc * 100000) * (service_fee / 100), 2)

            return {
                "source": "negotiated",
                "selected_ctc": selected_ctc,
                "service_fee_percent": service_fee,
                "invoice_amount": invoice_amount,
                "terms": negotiated_terms
            }
    except JobPostTerms.DoesNotExist:
        pass  

    # Step 2: Try matching from regular terms
    fallback_terms = job_terms.filter(is_negotiated=False)

    for term in fallback_terms:
        try:
            min_ctc, max_ctc = parse_ctc_range(term.ctc_range)
            if min_ctc <= selected_ctc <= max_ctc:
                service_fee = float(term.service_fee)
                invoice_amount = round((selected_ctc * 100000) * (service_fee / 100), 2)

                return {
                    "source": "standard",
                    "selected_ctc": selected_ctc,
                    "service_fee_percent": service_fee,
                    "invoice_amount": invoice_amount,
                    "terms": term
                }
        except Exception as e:
            continue  # Skip invalid range terms

    # Step 3: No matching terms found
    return {"error": "No applicable service fee terms for the selected CTC"}



def update_location_status(location_id):
    try:
        location_instance = JobLocationsModel.objects.get(id = location_id)
        location_instance.positions_closed += 1
        if(location_instance.positions_closed == location_instance.positions):
            location_instance.status = 'closed'
            applications = JobApplication.objects.filter(
                Q(job_location=location_id), ~Q(status__in = ['rejected','selected'])
            )

            for application in applications:
                application.next_interview = None
                application.is_closed = True
                application.save()
                
                # send mail here


        location_instance.save()
        job_locations = JobLocationsModel.objects.filter(job_id=location_instance.job_id)

        for location in job_locations:
            if location.status == 'opened':
                return False 

        job = JobPostings.objects.get(id=location_instance.job_id.id)
        job.status = 'closed'
        job.save()
        return True  
    
    except Exception as e:
        print(f"Error verifying job status: {str(e)}")
        return False  


def reopen_joblocation(location_id):
    try:
        

        job_location = JobLocationsModel.objects.get(id = location_id)
        job_location.status = 'opened'
        job_location.positions_closed = max(0, job_location.positions_closed - 1)  # prevent negative
        job_location.save()

        job = job_location.job_id
        job.status = 'opened'
        job.save()

        return "Job location reopened successfully"
    
    except JobApplication.DoesNotExist:
        return "Joblocation not found."

    except Exception as e:
        print(f"Error updating candidate left status: {str(e)}")
        return False
