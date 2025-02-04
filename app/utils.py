import secrets
import string
import json
import google.generativeai as genai
from django.conf import settings
import fitz
from django.template.loader import render_to_string
from docx import Document
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

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

# def generate_invoice_document(context):
#     buffer = io.BytesIO()

#     client_name = context.get('client_name')
#     agency_name = context['agency_name']
#     job_title = context['job_title']
#     ctc = context['ctc']
#     invoice_id = context['invoice_id']
#     date = context['date']
#     email = context['email']
    

#     agreed_terms = [
#         ["Service Fee", f"{context["service_fee"]}"],
#         ["Invoice After", f"{context['invoice_after']} days"],
#         ["Payment Within", f"{context['payment_within']} days"],
#         ["Replacement Clause", f"{context['replacement_clause']} "],
#         ["Interest Percentage", f"{context.get("interest_percentage", 0)}% per month "]
#     ]

#     total_amount = (ctc * 10) / 100  # Assuming 10% service fee

#     p = canvas.Canvas(buffer, letter)
#     width, height = letter

#     # Header Section
#     p.setFont("Helvetica-Bold", 20)
#     p.drawString(250, height - 50, f"Invoice")
#     p.setFont("Helvetica", 15)
#     p.drawString(200, height - 80, f"Invoice {invoice_id} | Date {date}")

#     # Client Details
#     p.setFont("Helvetica-Bold", 10)
#     p.drawString(50, height - 120, "Agency Name ")
#     p.drawString(50, height - 140, "Client Name ")
#     p.drawString(50, height - 160, "Email ")
#     p.drawString(50, height - 180, "Job Title ")
#     p.drawString(50, height - 200, "Job CTC ")

#     p.setFont("Helvetica", 10)
#     p.drawString(120, height - 120, f":  {agency_name}")
#     p.drawString(120, height - 140, f":  {client_name}")
#     p.drawString(120, height - 160, f":  {email}")
#     p.drawString(120, height - 180, f":  {job_title}")
#     p.drawString(120, height - 200, f":  {ctc} LPA")

#     # Agreed Terms Table
#     p.setFillColorRGB(0.243, 0.341, 0.271)
#     p.setFont("Helvetica", 15)
#     p.drawString(50, height - 230, "Agreed Terms")

#     p.setFillColorRGB(0, 0, 0)
#     p.setFont("Helvetica", 10)

#     table_data = [["Term", "Details"]] + agreed_terms
#     table = Table(table_data, colWidths=[200, 200])
#     table.setStyle(TableStyle([
#         ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
#         ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
#         ("ALIGN", (0, 0), (-1, -1), "LEFT"),
#         ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#         ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
#         ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
#         ("GRID", (0, 0), (-1, -1), 1, colors.black),
#     ]))

#     # Draw the table at a specific position
#     table.wrapOn(p, width, height)
#     table.drawOn(p, 50, height - 350)

#     # Total Amount
#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(50, height - 400, f"Total Amount: ₹ {total_amount:.2f} LPA")

#     # Footer Section
#     p.setFont("Helvetica", 10)
#     p.setFillColorRGB(0.3, 0.3, 0.3)
#     p.drawString(50, 50, "Thank you for your business!")
#     p.drawString(50, 35, "For any queries, contact us at support@gaconsultancy.com")

#     p.showPage()
#     p.save()

#     return buffer