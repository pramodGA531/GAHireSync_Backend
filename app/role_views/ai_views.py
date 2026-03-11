# AI Job Processor View - Gemini 2.5 Flash Integration
# app/role_views/ai_views.py

import google.generativeai as genai
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from ..models import *
from ..permissions import *

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# System prompt for job form filling
SYSTEM_PROMPT = """You are an AI assistant helping users fill out a job posting form through conversation.

Available form fields and their types:
- job_title (text): Job title/position name
- job_department (text): Department name
- job_level (radio): Entry, Mid, Senior, Lead, Executive
- notice_period (radio): Serving notice, Need to serve notice, Immediate Joining
- notice_time (radio, conditional): If notice_period is 'Serving notice' or 'Need to serve notice'. Options: 15 Days, 30 Days, 45 Days, 2 Months, 6 Months
- job_type (radio): Full Time, Part Time, Intern, Consultant, Freelance  
- experience_min (number): Minimum years of experience
- experience_max (number): Maximum years of experience
- primary_skills (array): List of primary technical skills
- secondary_skills (array): List of secondary skills
- location (array): Job locations
- ctc_min (number): Minimum CTC in LPA
- ctc_max (number): Maximum CTC in LPA
- job_description (text): Detailed job description
- industry (text): Industry type
- languages (checkbox): Multi-select languages required (English, Hindi, etc.)
- qualifications (radio): Doctorate, UG, PG, Diploma, Intermediate, 6th-10th, 1st-5th, Uneducated
- rotational_shift (radio): Yes, No
- working_days_per_week (number): 1-7
- timings (text): Working hours/shift timings (e.g., "9 AM - 6 PM", "Flexible", "Night Shift")
- job_close_duration (calendar): Job application deadline (YYYY-MM-DD)
- probation_period (radio, if Full Time): None, 1 Month, 2 Months, 3 Months, 4 Months, 5 Months, 6 Months, 7 Months, 8 Months, 9 Months, 10 Months, 11 Months, 1 Year, 1 and half Year, 2 Years
- probation_type (radio, if Full Time): Paid, Unpaid
- time_period (radio, if Intern): 1 Month, 2 Months, 3 Months, 4 Months, 5 Months, 6 Months, 7 Months, 8 Months, 9 Months, 10 Months, 11 Months, 1 Year

Mandatory fields: job_title, job_department, job_level, notice_period, job_type, years_of_experience, primary_skills, job_locations, ctc, job_description, industry, languages, qualifications, rotational_shift, working_days_per_week, timings, job_close_duration.

Your task:
1. When user provides informal job description, set action='extract' and return ALL possible information in 'extracted_data'.
2. CRITICAL: ALWAYS extract and populate these THREE fields from the initial prompt - NEVER ask for them separately:
   - job_department: Infer from job_title (e.g., "Senior Developer" → department: "IT" or "Engineering")
   - industry: Infer from context (e.g., tech roles → "Information Technology", finance roles → "Banking & Finance")
   - job_description: Create a detailed, professional job description based on the job_title and other provided information
3. AUTOMATICALLY suggest relevant primary_skills and secondary_skills based on job_title during extraction. LIMIT to max 8 relevant skills each.
4. For missing mandatory fields (EXCEPT job_department, industry, job_description), set action='ask_field' and ask for them one by one.
5. IMPORTANT: Do NOT include 'extracted_data' in your response if action is NOT 'extract'. Do NOT re-extract fields already present and valid in 'current_form_data'.
6. Be CONCISE in your 'message'. Do not repeat what has already been added or confirmed. Just move to the next missing mandatory field.
7. If 'current_form_data' already has a value for a mandatory field, SKIP it and move to the next empty one.
8. When asking for fields (action='ask_field'):
   - For 'radio': Provide 'field_options' as an array of strings.
   - For 'checkbox': Provide 'field_options' as an array of strings.
   - For 'calendar': Instruct user to select a date.
   - For 'location' (specific handling): ALWAYS use action_type='checkbox' and provide 'field_options' from common Indian cities.
9. Once ALL mandatory fields are filled, provide a friendly thank you note and set action='complete'.

EXAMPLES for auto-extraction:
- User: "Need a senior developer" → department: "Engineering", industry: "Information Technology", description: "We are looking for a Senior Developer to join our engineering team..."
- User: "Hiring accountant" → department: "Finance", industry: "Accounting & Finance", description: "We are seeking an Accountant to manage financial records..."
- User: "Looking for marketing manager" → department: "Marketing", industry: "Marketing & Advertising", description: "We are hiring a Marketing Manager to lead our marketing initiatives..."

Response format (JSON) - MUST BE ONLY JSON, NO MARKDOWN TAGS:
{
  "action": "extract" | "ask_field" | "complete" | "message",
  "action_type": "radio" | "checkbox" | "calendar" | "none",
  "message": "Friendly AI message",
  "extracted_data": { 
     "job_title": "...",
     "job_department": "...",
     "job_level": "...",
     "notice_period": "...",
     "job_type": "...",
     "years_of_experience": [min, max],
     "ctc": [min, max],
     "job_description": "...",
     "job_locations": ["City1", "City2"],
     "primary_skills": ["Skill1", "Skill2"],
     "industry": "...",
     "languages": "...",
     "qualifications": "...",
     "rotational_shift": "Yes/No",
     "working_days_per_week": number,
     "job_close_duration": "..."
  },
  "field_name": "name_of_field_being_asked",
  "field_options": ["Option1", "Option2"]
}

Mandatory field details:
- job_title: String
- job_department: String
- job_level: String (Entry, Mid, Senior, Lead, Executive)
- notice_period: String (Immediate joining, Serving notice, Need to serve notice)
- job_type: String (Full Time, Part Time, Intern, Consultant, Freelance)
- years_of_experience: Array [min, max] or Object {min, max}. Numbers only.
- ctc: Array [min, max] or Object {min, max}. Numbers only (LPA).
- job_description: String (detailed)
- job_locations: Array of strings. Use action_type='checkbox'.
- primary_skills: Array of strings.
- industry: String
- languages: String
- qualifications: String
- rotational_shift: String ("Yes" or "No")
- working_days_per_week: Number (e.g. 5)
- job_close_duration: String (e.g. "30 days")
"""


class AIJobProcessorView(APIView):
    """
    Process user messages and help fill job posting form using Gemini AI
    """

    def post(self, request):
        try:
            user_message = request.data.get("message", "")
            conversation_history = request.data.get("history", [])
            current_form_data = request.data.get("formData", {})
            conversation_state = request.data.get("state", "idle")

            if not user_message:
                return Response(
                    {"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Initialize Gemini model
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",  # strictly use 2.5-flash model only
                generation_config={
                    "temperature": 0.1,  # even lower for stricter JSON
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 4096,
                    "response_mime_type": "application/json",
                },
            )

            # Build conversation context
            context = self._build_context(
                user_message,
                conversation_history,
                current_form_data,
                conversation_state,
            )

            # Get AI response
            response = model.generate_content(context)
            ai_response_text = response.text

            # Clean the response - remove markdown code blocks if present
            ai_response_text = ai_response_text.strip()
            if ai_response_text.startswith("```json"):
                # Remove ```json from start and ``` from end
                ai_response_text = ai_response_text[7:]  # Remove ```json
                if ai_response_text.endswith("```"):
                    ai_response_text = ai_response_text[:-3]  # Remove ```
                ai_response_text = ai_response_text.strip()
            elif ai_response_text.startswith("```"):
                # Remove ``` from start and end
                ai_response_text = ai_response_text[3:]
                if ai_response_text.endswith("```"):
                    ai_response_text = ai_response_text[:-3]
                ai_response_text = ai_response_text.strip()

            return Response({"response": ai_response_text}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": str(e),
                    "message": "Sorry, I encountered an error. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _build_context(self, user_message, history, form_data, state):
        """Build conversation context for Gemini"""

        context_parts = [SYSTEM_PROMPT]

        # Add current form data context
        if form_data:
            context_parts.append(f"\nCurrent form data: {json.dumps(form_data)}")

        # Add conversation history
        if history:
            context_parts.append("\nConversation history (last 5):")
            for msg in history[-5:]:  # Last 5 messages
                role = "User" if msg.get("type") == "user" else "AI"
                context_parts.append(f"{role}: {msg.get('text', '')}")

        # Add current state
        context_parts.append(f"\nCurrent state: {state}")

        # Add explicitly what is missing to avoid repetition
        # Flatten array fields for easier missing check
        flat_form_data = form_data.copy()
        if (
            isinstance(form_data.get("years_of_experience"), list)
            and len(form_data["years_of_experience"]) >= 2
        ):
            flat_form_data["experience_min"] = form_data["years_of_experience"][0]
            flat_form_data["experience_max"] = form_data["years_of_experience"][1]

        if isinstance(form_data.get("ctc"), list) and len(form_data["ctc"]) >= 2:
            flat_form_data["ctc_min"] = form_data["ctc"][0]
            flat_form_data["ctc_max"] = form_data["ctc"][1]

        mandatory_keys = [
            "job_title",
            "job_department",
            "job_level",
            "notice_period",
            "job_type",
            "years_of_experience",
            "primary_skills",
            "job_locations",
            "ctc",
            "job_description",
            "industry",
            "languages",
            "qualifications",
            "rotational_shift",
            "working_days_per_week",
            "timings",
            "job_close_duration",
        ]

        def is_empty(val):
            if val is None or val == "":
                return True
            if isinstance(val, (list, str)) and len(val) == 0:
                return True
            return False

        missing = [k for k in mandatory_keys if is_empty(flat_form_data.get(k))]
        if missing:
            context_parts.append(f"Missing mandatory fields: {', '.join(missing)}")
        else:
            context_parts.append("All mandatory fields are filled.")

        # Add user's current message
        context_parts.append(f"\nUser: {user_message}")

        # Add instruction based on state
        if state == "idle":
            context_parts.append(
                "\nInstruction: Extract job information from user's message and return in JSON format with action='extract'."
            )
        elif state == "confirming":
            if "yes" in user_message.lower() or "confirm" in user_message.lower():
                next_field = missing[0] if missing else None
                if next_field:
                    context_parts.append(
                        f"\nInstruction: User confirmed. The next missing field is '{next_field}'. DO NOT extract again. Ask for '{next_field}' with action='ask_field'."
                    )
                else:
                    context_parts.append(
                        "\nInstruction: User confirmed and all fields filled. Set action='complete'."
                    )
            else:
                context_parts.append(
                    "\nInstruction: User wants changes. Ask what they want to modify."
                )
        elif state == "asking":
            context_parts.append(
                "\nInstruction: User provided answer to your question. CRITICAL: You MUST include 'extracted_data' with the field and value. Then move to the next missing field with action='ask_field'. "
                "\nExample: If you asked 'What is the minimum CTC?' and user says '10', respond with: "
                '{"action": "ask_field", "extracted_data": {"ctc_min": 10}, "field_name": "ctc_max", "message": "What is the maximum CTC?", "action_type": "none"}'
                "\nFor experience: If user says '3' for min_experience, return extracted_data: {\"experience_min\": 3}"
                "\nFor CTC: If user says '15' for max CTC, return extracted_data: {\"ctc_max\": 15}"
            )

        return "\n".join(context_parts)


# Required fields definition
REQUIRED_FIELDS = {
    "job_title": {"type": "text", "label": "Job Title"},
    "job_department": {"type": "text", "label": "Department"},
    "job_level": {
        "type": "radio",
        "label": "Job Level",
        "options": ["Entry", "Mid", "Senior", "Lead", "Executive"],
    },
    "job_description": {"type": "text", "label": "Job Description"},
    "industry": {"type": "text", "label": "Industry"},
    "experience_min": {"type": "number", "label": "Minimum Experience (years)"},
    "working_days_per_week": {"type": "number", "label": "Working Days per Week"},
    "ctc_min": {"type": "number", "label": "Minimum CTC (LPA)"},
    "ctc_max": {"type": "number", "label": "Maximum CTC (LPA)"},
    "primary_skills": {"type": "checkbox", "label": "Primary Skills"},
    "location": {"type": "checkbox", "label": "Location"},
    "languages": {"type": "checkbox", "label": "Languages"},
    "notice_period": {
        "type": "radio",
        "label": "Notice Period",
        "options": ["Serving notice", "Need to serve notice", "Immediate Joining"],
    },
    "job_type": {
        "type": "radio",
        "label": "Job Type",
        "options": ["Full Time", "Part Time", "Intern", "Consultant", "Freelance"],
    },
    "qualifications": {
        "type": "radio",
        "label": "Qualifications",
        "options": [
            "Doctorate",
            "UG",
            "PG",
            "Diploma",
            "Intermediate",
            "6th-10th",
            "1st-5th",
            "Uneducated",
        ],
    },
    "rotational_shift": {
        "type": "radio",
        "label": "Rotational Shift",
        "options": ["Yes", "No"],
    },
    "job_close_duration": {"type": "calendar", "label": "Job close Deadline"},
}


class AIJobSummaryView(APIView):
    """
    Generate a comprehensive AI summary for a job post including logs, JD, and metadata.
    """

    permission_classes = [IsManager]

    def get(self, request, job_id):
        try:
            job = JobPostings.objects.get(id=job_id)
            logs = JobPostLog.objects.filter(job_post=job).order_by("-created_at")[:20]
            locations = JobLocationsModel.objects.filter(job_id=job)
            skills = SkillMetricsModel.objects.filter(job_id=job)
            interviewers = InterviewerDetails.objects.filter(job_id=job).select_related(
                "name"
            )

            # Prepare data for AI
            log_texts = [
                f"- {log.created_at.strftime('%Y-%m-%d %H:%M')}: {log.message}"
                for log in logs
            ]
            loc_texts = [
                f"- {loc.location} ({loc.positions} positions)" for loc in locations
            ]
            skill_texts = [
                f"- {s.skill_name} ({'Primary' if s.is_primary else 'Secondary'})"
                for s in skills
            ]
            interviewer_texts = [
                f"- {i.name.username} ({i.type_of_interview} round {i.round_num})"
                for i in interviewers
            ]

            prompt = f"""
Summarize the following job posting details into a professional and concise report for a recruiter/manager. 
Highlight the core requirements, current status, and significant recent activities.

JOB DETAILS:
Title: {job.job_title}
Department: {job.job_department}
Level: {job.job_level}
Type: {job.job_type}
Experience: {job.years_of_experience} years
CTC: {job.ctc} LPA
Description: {job.job_description}

LOCATIONS:
{chr(10).join(loc_texts) if loc_texts else "No locations specified"}

SKILLS:
{chr(10).join(skill_texts) if skill_texts else "No skills specified"}

INTERVIEW PANEL:
{chr(10).join(interviewer_texts) if interviewer_texts else "No interviewers assigned"}

RECENT ACTIVITY LOGS:
{chr(10).join(log_texts) if log_texts else "No recent activity logs"}

Please provide the summary in Markdown format with clear sections.
"""

            # Configure Gemini
            model = genai.GenerativeModel("gemini-2.5-flash")

            response = model.generate_content(prompt)

            return Response({"summary": response.text}, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response(
                {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AISkillGenerationView(APIView):
    """
    Fetch skills from Job Posting or generate skills for a given job role using Gemini AI
    """

    def post(self, request):
        ids = request.data.get("job_id")
        print(f"DEBUG: Received job_id {ids}")
        if not ids:
            return Response(
                {"skills": [], "message": "id is required"},
                status=status.HTTP_200_OK,
            )
        job_id = AssignedJobs.objects.get(id=ids).job_id
        print(f"DEBUG: Received job_id {job_id}")
        try:
            # SkillMetricsModel holds the skills for a job posting
            skills_query = SkillMetricsModel.objects.filter(job_id=job_id)
            skill_names = [s.skill_name for s in skills_query]
            print(
                f"DEBUG: Found {len(skill_names)} skills in DB for job {job_id} skills {skill_names}"
            )
            # Return unique skill names from the DB (empty list if none found)
            return Response(
                {"skills": list(set(skill_names))}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CandidateProfileMatchingSearchView(APIView):
    """
    Search for applications in the recruiter's organization and match them against required skills
    """

    def post(self, request):
        job_id = request.data.get(
            "job_id"
        )  # Provide the current job_id to exclude it from results
        required_skills = request.data.get("requiredSkills", [])

        if not required_skills:
            return Response(
                {"error": "requiredSkills is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # AI Skill Enhancement Logic
        rectified_skills = []
        suggested_skills = []
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"""
            Task: Rectify spelling mistakes in the following technical skills and suggest related highly relevant technical skills/technologies.
            Input Skills: {", ".join(required_skills)}

            Instructions:
            1. Correct any typos (e.g., 'pythn' -> 'Python').
            2. For example if 'AI' is mentioned, suggest related tech like 'Python', 'NumPy', 'TensorFlow', 'PyTorch' return only 3 most relevant for given skills.
            3. Return the response in strict JSON format:
            {{
                "rectified": ["corrected_skill1", "corrected_skill2"],
                "suggested": ["related_skill1", "related_skill2"]
            }}
            """
            response = model.generate_content(prompt)

            # Print token usage to console
            print(
                f"DEBUG: AI Enhancement - Prompt Tokens: {response.usage_metadata.prompt_token_count}"
            )
            print(
                f"DEBUG: AI Enhancement - Response Tokens: {response.usage_metadata.candidates_token_count}"
            )
            print(
                f"DEBUG: AI Enhancement - Total Tokens: {response.usage_metadata.total_token_count}"
            )

            content = response.text.replace("```json", "").replace("```", "").strip()
            ai_data = json.loads(content)
            rectified_skills = ai_data.get("rectified", [])
            suggested_skills = ai_data.get("suggested", [])
        except Exception as ai_err:
            print(f"AI Enhancement Error: {str(ai_err)}")

        try:
            recruiter_id = request.user.id
            organization = Organization.objects.filter(
                recruiters__id=recruiter_id
            ).first()

            if not organization:
                return Response(
                    {"error": "Organization not found for the user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            job_postings = JobPostings.objects.filter(organization=organization)
            if job_id:
                job_postings = job_postings.exclude(id=job_id)

            organization_applications = JobApplication.objects.filter(
                job_location__job_id__in=job_postings
            ).exclude(status="selected")

            # Use rectified skills for matching if available (replaces misspelled items)
            effective_skills = rectified_skills if rectified_skills else required_skills

            application_list = []
            for application in organization_applications:
                resume = application.resume
                if not resume:
                    continue

                # Fetch skills associated with the CandidateResume
                cand_skills = resume.skills.all()
                cand_skill_names = [s.skill_name.lower() for s in cand_skills]

                # Also fetch skills from CandidateProfile
                if resume.candidate_email:
                    profile = CandidateProfile.objects.filter(
                        email=resume.candidate_email
                    ).first()
                    if profile:
                        cps = profile.candidate_profile_skills.all()
                        for s in cps:
                            name_lower = s.skill_name.lower()
                            if name_lower not in cand_skill_names:
                                cand_skill_names.append(name_lower)

                        if profile.skills:
                            try:
                                parsed = json.loads(profile.skills)
                                if isinstance(parsed, list):
                                    for item in parsed:
                                        name = (
                                            item.get("label", item)
                                            if isinstance(item, dict)
                                            else item
                                        )
                                        if name.lower() not in cand_skill_names:
                                            cand_skill_names.append(name.lower())
                                else:
                                    for s in str(profile.skills).split(","):
                                        if s.strip().lower() not in cand_skill_names:
                                            cand_skill_names.append(s.strip().lower())
                            except:
                                for s in str(profile.skills).split(","):
                                    if s.strip().lower() not in cand_skill_names:
                                        cand_skill_names.append(s.strip().lower())

                # Compute match against effective_skills
                matched = 0
                matched_skills_list = []
                for req in effective_skills:
                    req_lower = req.lower()
                    if any(
                        req_lower == cand_s
                        or (len(req_lower) > 3 and req_lower in cand_s)
                        or (len(cand_s) > 3 and cand_s in req_lower)
                        for cand_s in cand_skill_names
                    ):
                        matched += 1
                        matched_skills_list.append(req)

                match_percentage = (
                    int((matched / len(effective_skills)) * 100)
                    if effective_skills
                    else 0
                )

                if match_percentage > 0:
                    application_json = {
                        "candidate_name": resume.candidate_name,
                        "job_department": (
                            application.job_location.job_id.job_department
                            if application.job_location
                            else ""
                        ),
                        "status": application.status,
                        "application_id": application.id,
                        "cand_number": resume.contact_number,
                        "job_title": (
                            application.job_location.job_id.job_title
                            if application.job_location
                            else ""
                        ),
                        "resume_url": resume.resume.url if resume.resume else None,
                        "resume_name": resume.resume.name if resume.resume else None,
                        "match_percentage": match_percentage,
                        "matched_skills": matched_skills_list,
                        "email": resume.candidate_email,
                    }
                    application_list.append(application_json)

            # Deduplicate by candidate email, keeping the best match
            seen_emails = {}
            for app in application_list:
                email = app.get("email")
                if not email:
                    email = f"{app['candidate_name']}_{app['cand_number']}"

                if (
                    email not in seen_emails
                    or app["match_percentage"] > seen_emails[email]["match_percentage"]
                ):
                    seen_emails[email] = app

            results = list(seen_emails.values())

            # Sort by match percentage in descending order
            results.sort(key=lambda x: x["match_percentage"], reverse=True)

            return Response(
                {
                    "results": results,
                    "rectified_skills": rectified_skills,
                    "suggested_skills": suggested_skills,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
