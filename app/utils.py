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
from celery.app.control import Control
from decimal import Decimal, InvalidOperation
from django.utils.encoding import force_bytes
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
frontend_url = os.environ["FRONTENDURL"]


def generate_passwrord(length=15):
    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def extract_text_from_file(file):
    if file.name.endswith(".pdf"):
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text()
        pdf.close()
        return text
    elif file.name.endswith(".docx"):
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    else:
        return "Unsupported file format. Please upload a PDF or DOCX file."


def summarize_jd(jd):
    model = genai.GenerativeModel("gemini-2.5-flash")

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
    model = genai.GenerativeModel("gemini-2.5-flash")

    job_title = jd.job_title
    job_description = (
        jd.job_description.strip()
        if jd.job_description
        else "Not provided or insufficiently detailed"
    )
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
        return {
            "error": "Invalid response format from AI. Extracted JSON was: "
            + clean_json_text
        }


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
    model = genai.GenerativeModel("gemini-2.5-flash")

    job_title = jd.job_title
    job_description = (
        jd.job_description.strip()
        if jd.job_description
        else "No detailed job description provided."
    )
    years_of_experience = jd.years_of_experience
    primary_skills = jd.get_primary_skills_list()
    secondary_skills = jd.get_secondary_skills_list()
    qualifications = (
        jd.qualifications.strip() if jd.qualifications else "Not specified."
    )
    job_location = jd.job_location
    job_type = jd.job_type
    job_level = jd.job_level

    skills = (
        ", ".join(primary_skills + secondary_skills)
        if (primary_skills or secondary_skills)
        else "Not specified."
    )

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


def send_questions_mail(job_title, questions, recipients):
    """
    Sends the generated interview questions to the specified recipients asynchronously.
    """
    from .tasks import send_celery_mail

    subject = f"Interview Questions for {job_title}"

    # Format questions into HTML
    questions_html = ""
    for idx, q in enumerate(questions, 1):
        questions_html += f"""
        <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #eee; border-radius: 8px; background-color: #fafafa;">
            <p><strong>Q{idx}: {q.get('question_text', '')}</strong></p>
            <p style="color: #555; font-style: italic;">Expected Answer: {q.get('correct_answer', '')}</p>
        </div>
        """

    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #071C50;">Generated Interview Questions</h2>
        <p>Here are the AI-generated questions for the role <strong>{job_title}</strong>.</p>
        
        <div style="margin-top: 20px;">
            {questions_html}
        </div>
        
        <p style="margin-top: 30px; font-size: 12px; color: #888;">
            Generated by HireSync AI
        </p>
    </body>
    </html>
    """

    try:
        if settings.ENVIRONMENT == "localhost":
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)
            return True
        else:
            from .tasks import send_html_email_task

            send_html_email_task.delay(subject, html_message, recipients)
            return True
    except Exception as e:
        print(f"Failed to send questions email: {e}")
        return False


def analyse_resume(jd, resume):
    model = genai.GenerativeModel("gemini-2.0-flash")
    # print(settings.GEMINI_API_KEY)
    job_title = jd.job_title
    job_description = (
        jd.job_description.strip()
        if jd.job_description
        else "No detailed job description provided."
    )
    years_of_experience = jd.years_of_experience
    qualifications = (
        jd.qualifications.strip() if jd.qualifications else "Not specified."
    )
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
        Evaluate the candidate's resume against the job description for the role **'{job_title}'**.
        
        **Job Description Details:**  
        {job_description}  

        **Target Profile:**
        - **Primary Skills:** {", ".join(primary_skill_list)}
        - **Secondary Skills:** {", ".join(secondary_skill_list)}
        - **Experience:** At least {years_of_experience} years
        - **Qualifications:** {qualifications}
        
        **Candidate Resume:**  
        {resume}  

        ### Instructions:
        Analyze the resume and provide a structured JSON response suitable for a recruiter dashboard.
        
        **Output Schema (JSON):**
        ```json
        {{
            "skills": [
                {{
                    "field_name": "Skill or Criterion Name",
                    "score": "Score/10 (e.g. '8/10')",
                    "reason": "Brief justification for the score"
                }}
            ],
            "overall_resume_score": {{
                "score": "Score/100 (e.g. '85/100')",
                "reason": "Concise summary of overall fit, highlighting key strengths and major gaps."
            }}
        }}
        ```

        **Requirements:**
        1. **Skills Analysis**: Evaluate 3-5 key criteria (e.g., Primary Skills, Experience, relevant Tools).
        2. **Overall Score**: Provide a single compatibility score out of 100.
        3. **Strict JSON**: Return ONLY the JSON object. Do not include markdown formatting like ```json ... ``` if possible, but if you do, it will be cleaned.
    """

    try:
        response = model.generate_content(prompt)
        ai_response = response.text

        # extracted_json_str = extract_json(ai_response) # extract_json is defined earlier in utils.py
        # Reuse the existing extract_json helper if available, or just implement inline cleaning if needed.
        # Looking at file context, extract_json is defined at line 125.

        clean_json_text = extract_json(ai_response)
        parsed_response = json.loads(clean_json_text)

        return parsed_response  # Return dict, let DRF handle serialization

    except Exception as e:
        print(f"Error in analyse_resume: {e}")
        # Return a fallback error structure
        return {
            "skills": [],
            "overall_resume_score": {
                "score": "0/100",
                "reason": f"AI Analysis failed: {str(e)}",
            },
        }


def generate_invoice(context):
    html_content = render_to_string("invoice.html", context=context)
    return html_content


class EmailVerificatioinTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_verified)
        )


email_verification_token = EmailVerificatioinTokenGenerator()


def calculate_profile_percentage(candidate):

    fields_to_check = [
        "profile",
        "about",
        "email",
        "first_name",
        "middle_name",
        "last_name",
        "communication_address",
        "current_salary",
        "expected_salary",
        "joining_details",
        "permanent_address",
        "phone_num",
        "date_of_birth",
        "designation",
        "linked_in",
        "instagram",
        "facebook",
        "blood_group",
        "experience_years",
        "skills",
    ]

    total_fields = len(fields_to_check)
    filled_fields = sum(1 for field in fields_to_check if getattr(candidate, field))

    # Base profile percentage calculation
    base_profile_completion = (filled_fields / total_fields) * 80

    # Additional weightage for documents and education
    document_completion = (
        10 if CandidateDocuments.objects.filter(candidate=candidate).exists() else 0
    )
    education_completion = (
        10 if CandidateEducation.objects.filter(candidate=candidate).exists() else 0
    )

    # Calculate total profile completion
    profile_completion = (
        base_profile_completion + document_completion + education_completion
    )

    return round(profile_completion, 2)


class TenResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 10


def calculate_invoice_amounts(selected_candidate, terms, client_gst, org_gst):
    ctc_in_lakhs = Decimal(str(selected_candidate.ctc))
    ctc_in_actual = ctc_in_lakhs * Decimal("100000")

    service_fee = (Decimal(str(terms.service_fee)) / Decimal("100")) * ctc_in_actual

    def get_state_from_gst(gst_number):
        state_code = gst_number[:2]
        return state_code

    client_state = get_state_from_gst(client_gst)
    org_state = get_state_from_gst(org_gst)

    if client_state == org_state:
        sgst = (Decimal("9") / Decimal("100")) * service_fee
        cgst = (Decimal("9") / Decimal("100")) * service_fee
        igst = Decimal("0")  # No IGST if same state
    else:
        sgst = Decimal("0")
        cgst = Decimal("0")
        igst = (Decimal("18") / Decimal("100")) * service_fee

    total_amount = service_fee + sgst + cgst + igst

    # Prepare the dictionary to return the values
    result = {
        "ctc": round(selected_candidate.ctc, 2),
        "service_fee": round(service_fee, 2),
        "sub_total": round(service_fee, 2),
        "sgst": round(sgst, 2),
        "cgst": round(cgst, 2),
        "igst": round(igst, 2),
        "total_amount": round(total_amount, 2),
    }

    return result


def create_invoice_context(invoice_id):
    invoice = InvoiceGenerated.objects.get(id=invoice_id)
    organization = invoice.organization
    job = invoice.selected_candidate.application.job_location.job_id
    client_details = invoice.client
    selected_candidate = invoice.selected_candidate
    terms = invoice.terms_id

    context = {
        "url": settings.BACKEND_URL,  # from settings backendurl  .env have backendurl="http://localhost:8000"
        "invoice_id": invoice.invoice_code,
        "date": invoice.created_at.date(),
        "service_provider_name": organization.name,
        "candidate_name": selected_candidate.candidate.name,
        "client_name": job.username.username,
        "client_email": job.username.email,
        "job_title": job.job_title,
        "buyer_address": client_details.company_address,
        "buyer_gst_no": client_details.gst_number,
        "buyer_contact_number": client_details.contact_number,
        "service_provider_address": job.organization.company_address,
        "service_provider_gstin": job.organization.gst_number,
        "service_provider_contact_person": job.organization.manager,
        "service_provider_email": job.organization.manager.email,
        "service_provider_mobile": job.organization.contact_number,
        "service_description": "HSNCODE:9983",
        "date_of_joining": selected_candidate.joining_date,
        "ctc": selected_candidate.ctc,
        "service_fee_percentage": terms.service_fee,
        "service_fee": invoice.terms_id.service_fee,
        "sub_total": invoice.sub_total,
        "cgst": invoice.cgst,
        "sgst": invoice.sgst,
        "igst": invoice.igst,
        "total_amount": invoice.final_price,
        "payment_within": terms.payment_within,
        "service_fee_percentage": terms.service_fee,
        "invoice_after": terms.invoice_after,
        "replacement_clause": terms.replacement_clause,
        # "email": job.username.email
    }
    return context


logger = logging.getLogger(__name__)


def sendemailTemplate(subject, template_name, context, recipient_list):
    """
    Sends an HTML email. Synchronous on localhost, Asynchronous on others.
    """
    try:
        if settings.ENVIRONMENT == "localhost":
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                subject, text_content, settings.DEFAULT_FROM_EMAIL, recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            logger.info(f"Email sent successfully to: {', '.join(recipient_list)}")
            return True
        else:
            from .tasks import send_template_email_task

            send_template_email_task.delay(
                subject, template_name, context, recipient_list
            )
            return True
    except Exception as e:
        logger.error(
            f"Failed to send template email to {', '.join(recipient_list)}. Error: {e}"
        )
        return False


def send_custom_mail(subject, body, to_email):
    """
    Sends a basic email. Synchronous on localhost, Asynchronous on others.
    """
    try:
        if settings.ENVIRONMENT == "localhost":
            from_email = settings.DEFAULT_FROM_EMAIL
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to_email if isinstance(to_email, list) else [to_email],
            )
            email.send(fail_silently=False)
        else:
            from .tasks import send_celery_mail

            send_celery_mail.delay(subject, body, to_email)
    except Exception as e:
        print(f"Failed to send custom email: {e}")


def send_email_verification_link(user, signup, role, password=None):
    print(
        f"[EMAIL-VERIFY] Generating link for user={user.email}, signup={signup}, role={role}"
    )
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{frontend_url}/verify-email/{uid}/{token}/"
    print(f"[EMAIL-VERIFY] Created verification link: {link}")

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

        if role == "client":
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

        if role == "manager":
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your account on HireSync has been successfully created.

This is your unique organisation code : {user.organization.org_code}. Please keep it safe and share it with your team members and clients to access your organization.

You can now manage your job posts seamlessly.


Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""

        if role == "recruiter":
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your recruiter account on HireSync has been successfully created.

You can now send applications/schedule interviews seamlessly.

Email : {user.email}
Password : {password}

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == "interviewer":
            subject = f"Welcome to HireSync – Your Account is Ready!"
            message = f"""

Dear {user.username},

Congratulations! Your interviewer account on HireSync has been successfully created.

You can now send conduct interviews seamlessly.

Email : {user.email}
Password : {password}

Verify your account 
🔗 {link}

Need assistance? Contact us at support@hiresync.com.
Best,
HireSync Team

"""
        if role == "candidate":
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
        if role == "accountant":
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

    print(
        f"[EMAIL-VERIFY] Sending custom email to {user.email} with subject: {subject}"
    )
    send_custom_mail(
        subject=subject,
        body=message,
        to_email=[user.email],
    )


def convert_pdf_to_images(request):
    # resume_path = request.GET.get('resume')
    pdf_url = request.GET.get(
        "resume"
    )  # e.g., "media/88/resume.pdf" or "/media/88/resume.pdf"

    if not pdf_url:
        return JsonResponse({"error": "Missing resume path"}, status=400)

    # Remove '/media/' from the URL and join with MEDIA_ROOT
    pdf_rel_path = pdf_url.replace("/media/", "").replace("media/", "")
    pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_rel_path)

    if not os.path.exists(pdf_path):
        raise Http404("Resume file not found.")

    # Output folder for generated images
    output_folder_uuid = str(uuid.uuid4())
    output_folder = os.path.join(
        settings.MEDIA_ROOT, "resume_images", output_folder_uuid
    )
    os.makedirs(output_folder, exist_ok=True)

    try:
        images = convert_from_path(pdf_path, dpi=150)
    except Exception as e:
        return JsonResponse({"error": f"Failed to convert PDF: {str(e)}"}, status=500)

    # Generate image URLs relative to MEDIA_URL
    image_urls = []
    for i, image in enumerate(images):
        image_filename = f"page_{i + 1}.jpg"
        image_path = os.path.join(output_folder, image_filename)
        image.save(image_path, "JPEG")

        relative_url = os.path.join(
            settings.MEDIA_URL, "resume_images", output_folder_uuid, image_filename
        )
        image_urls.append(relative_url)

    return JsonResponse({"images": image_urls})


def get_resume_storage_usage(manager_user):
    total_size_bytes = 0

    # Get all resumes under the manager's org
    applications = JobApplication.all_objects.filter(
        job_location__job_id__organization__manager=manager_user
    ).select_related("resume")

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
        "total_size_bytes": total_size_bytes,
        "total_size_mb": total_size_mb,
        "total_files": len(seen_files),
    }


def get_invoice_terms(selected_application_id):
    from decimal import Decimal

    selected_application = SelectedCandidates.objects.get(id=selected_application_id)
    job = selected_application.application.job_location.job_id
    job_terms = JobPostTerms.objects.filter(job_id=job)

    selected_ctc = float(selected_application.ctc)

    def parse_ctc_range(ctc_range_str):
        try:  # get the range from terms
            print(ctc_range_str, " is the ctc range")
            clean_range = ctc_range_str.replace("LPA", "").replace(" ", "")
            min_str, max_str = clean_range.split("-")
            return float(min_str), float(max_str)
        except Exception as e:
            raise ValueError(f"Invalid CTC range format: '{ctc_range_str}'")

    try:
        negotiated_terms = job_terms.get(is_negotiated=True)
        min_ctc, max_ctc = parse_ctc_range(negotiated_terms.ctc_range)

        if selected_ctc <= max_ctc:  # checks that ctc comes under which range in terms
            service_fee = float(negotiated_terms.service_fee)
            invoice_amount = round((selected_ctc * 100000) * (service_fee / 100), 2)
            cgst = 0
            sgst = 0
            final_price = 0

            return {
                "source": "negotiated",
                "selected_ctc": selected_ctc,
                "service_fee_percent": service_fee,
                "invoice_amount": invoice_amount,
                "terms_id": negotiated_terms.id,
                "cgst": cgst,
                "sgst": sgst,
                "final_price": final_price,
            }
    except JobPostTerms.DoesNotExist:
        pass

    # Step 2: Try matching from regular terms
    fallback_terms = job_terms.filter(is_negotiated=False)

    for term in fallback_terms:
        try:
            min_ctc, max_ctc = parse_ctc_range(term.ctc_range)
            if min_ctc <= selected_ctc <= max_ctc:
                service_fee_type = term.service_fee_type
                service_fee = float(term.service_fee)
                if service_fee_type == "percentage":
                    invoice_amount = round(
                        (selected_ctc * 100000) * (service_fee / 100), 2
                    )
                else:
                    invoice_amount = service_fee

                cgst = 0
                sgst = 0
                final_price = 0

                return {
                    "source": "standard",
                    "selected_ctc": selected_ctc,
                    "service_fee_percent": service_fee,
                    "invoice_amount": invoice_amount,
                    "terms_id": term.id,
                    "cgst": cgst,
                    "sgst": sgst,
                    "final_price": final_price,
                }
        except Exception as e:
            continue

    return {"error": "No applicable service fee terms for the selected CTC"}


def get_gst_calculation(invoice_amount):
    print("need fetch the gst numbers for both the agency and the client ")


def update_location_to_hold(location_id):
    try:
        location = JobLocationsModel.objects.get(id=location_id)
        location.status = "hold"

        applications = JobApplication.objects.filter(
            Q(job_location=location.id), ~Q(status__in=["rejected", "selected"])
        )

        for application in applications:
            application.next_interview = None
            application.is_closed = True
            application.save(update_fields=["next_interview", "is_closed"])

        location.save(update_fields=["status"])
        return True

    except ObjectDoesNotExist:
        return False
    except Exception as e:
        print(f"Error updating location {location_id} to hold: {e}")
        return False


def update_job_to_hold(job_id):
    try:
        job = JobPostings.objects.get(id=job_id)

        with transaction.atomic():
            locations = JobLocationsModel.objects.filter(job_id=job)

            for location in locations:
                if not update_location_to_hold(location.id):
                    raise Exception(f"Failed to update location {location.id}")

            job.status = "hold"
            job.save(update_fields=["status"])
            return True

    except ObjectDoesNotExist:
        print(f"Job with ID {job_id} not found.")
        return False
    except Exception as e:
        print(f"Error updating job {job_id} to hold: {e}")
        return False


def update_location_status(location_id):
    try:
        location_instance = JobLocationsModel.objects.get(id=location_id)
        location_instance.positions_closed += 1
        if location_instance.positions_closed == location_instance.positions:
            location_instance.status = "closed"
            applications = JobApplication.objects.filter(
                Q(job_location=location_id), ~Q(status__in=["rejected", "selected"])
            )

            for application in applications:
                application.next_interview = None
                application.is_closed = True
                application.save()

                # send mail here

        location_instance.save()
        job_locations = JobLocationsModel.objects.filter(
            job_id=location_instance.job_id
        )

        for location in job_locations:
            if location.status == "opened":
                return False

        job = JobPostings.objects.get(id=location_instance.job_id.id)
        job.status = "closed"
        job.save()
        return True

    except Exception as e:
        print(f"Error verifying job status: {str(e)}")
        return False


def reopen_joblocation(location_id):
    try:

        job_location = JobLocationsModel.objects.get(id=location_id)
        job_location.status = "opened"
        job_location.positions_closed = max(
            0, job_location.positions_closed - 1
        )  # prevent negative
        job_location.save()

        job = job_location.job_id
        job.status = "opened"
        job.save()

        return "Job location reopened successfully"

    except JobApplication.DoesNotExist:
        return "Joblocation not found."

    except Exception as e:
        print(f"Error updating candidate left status: {str(e)}")
        return False


def cancel_invoice_notification(invoice):

    try:
        task_record = InvoiceNotificationTask.objects.get(invoice=invoice)
        Control.revoke(task_record.task_id, terminate=True)
        task_record.delete()
        return True
    except InvoiceNotificationTask.DoesNotExist:
        return False


def safe_decimal(val):
    try:
        return Decimal(str(val)) if val is not None else Decimal("0.0")
    except InvalidOperation:
        raise ValueError(f"Invalid decimal value: {val}")


def get_selected_plan_limit(organization_id, feature_code):
    try:
        organization = Organization.objects.get(id=organization_id)
        org_plan = OrganizationPlan.objects.get(organization=organization)
        plan_feature = PlanFeature.objects.get(
            plan=org_plan.plan, feature__code=feature_code
        )
        return plan_feature.limit

    except OrganizationPlan.DoesNotExist:
        raise ValueError(f"No plan found for organization '{organization.name}'.")
    except MultipleObjectsReturned:
        raise ValueError(
            f"Multiple plans found for organization '{organization.name}', expected one."
        )
    except Organization.DoesNotExist:
        raise ValueError(f"Organization with ID {organization_id} does not exist.")
    except PlanFeature.DoesNotExist:
        raise ValueError(
            f"Feature '{feature_code}' is not available in the selected plan."
        )
    except MultipleObjectsReturned:
        raise ValueError(
            f"Multiple features found for code '{feature_code}' in the selected plan."
        )
    except Exception as e:
        raise ValueError(f"{str(e)}")


def can_upload_new(organization_id):
    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise ValueError(f"Organization with ID {organization_id} does not exist.")

    try:
        storage_used = get_resume_storage_usage(organization.manager)
        mb_used = storage_used.get("total_size_mb", 0)
        mb_limit = get_selected_plan_limit(organization_id, "storage")

        if mb_limit is None:
            raise ValueError("Storage limit not defined in the selected plan.")

        return mb_used < mb_limit
    except Exception as e:
        raise ValueError(f"{e}")


def can_add_recruiter(organization_id):
    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise ValueError(f"Organization with ID {organization_id} does not exist.")

    try:
        recruiters = organization.recruiters.all().count()
        allowed_recruiters = get_selected_plan_limit(organization_id, "recruiters")

        return recruiters < allowed_recruiters
    except Exception as e:
        raise ValueError(f"{e}")


def job_post_log(id, message):
    try:
        job_post_log = JobPostLog.objects.create(job_post_id=id, message=message)
    except Exception as e:
        print(f"An error occurred: {e}")


def job_profile_log(job_application_id, message):
    try:
        # Create log record
        log = JobProfileLog.objects.create(
            job_profile_id=job_application_id, message=message
        )
        print("Job Profile Log created:", log.message)
        return log
    except JobApplication.DoesNotExist:
        print(f"Error: JobApplication with id {job_application_id} does not exist.")
        return None
    except Exception as e:
        print(f"Unexpected error while creating JobProfileLog: {e}")
        return None


def create_notification(sender, receiver, subject, message, category):
    try:
        from .models import Notifications

        Notifications.objects.create(
            sender=sender,
            receiver=receiver,
            subject=subject,
            message=message,
            category=category,
        )
        return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False
