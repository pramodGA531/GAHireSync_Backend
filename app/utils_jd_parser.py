import google.generativeai as genai
import os
import json
from .utils import extract_text_from_file

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def parse_job_description(file_obj):
    """
    Parses a PDF or DOCX job description file using Gemini to extract structured data.
    Arg:
        file_obj: The uploaded file object
    Returns:
        dict: Extracted fields (job_title, job_description, experience, etc.)
    """
    try:
        # 1. Extract Text
        text = extract_text_from_file(file_obj)
        
        if not text or "Unsupported file format" in text:
            print("Failed to extract text from file.")
            return {}

        # 2. Use Gemini to structure the data
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        You are an expert HR assistant. Your task is to extract structured information from the following Job Description text.
        
        Please extract the following fields and return them in a strict valid JSON format. 
        Do not include markdown formatting (like ```json ... ```) in the response, just the raw JSON string.

        Fields to extract:
        - job_title: The specific role title.
        - job_description: A summary or the full description if concise.
        - years_of_experience: e.g., "3-5 years", "2+ years".
        - skills: A comma-separated list or string of key skills.
        - ctc: The salary or package information (e.g., "12-15 LPA").
        - job_type: e.g., "Full-time", "Contract", "Intern".
        - working_days_per_week: Number or description.
        - industry: The industry domain.
        - qualifications: Educational requirements (e.g., "B.Tech", "MBA").
        - notice_period: e.g., "Immediate", "30 days".
        - location: Job location if available. 
        - job_department: The department (e.g., "Engineering", "Sales").
        - job_level: e.g., "Junior", "Senior", "Mid-level".
        - timings: Shift timings (e.g., "Day Shift", "9AM-6PM").
        - languages: Required languages (e.g., "English", "Hindi").
        - gender: Gender preference if mentioned (e.g., "Male", "Female", "No Mention").
        - differently_abled: "Yes" if mentioned, else "".
        - visa_status: Visa requirements if mentioned.
        - passport_availability: Passport requirement if mentioned.
        - probation_period: e.g. "3 months", "6 months".
        - probation_type: e.g. "Paid", "Unpaid".
        - bond: Bond details if mentioned.
        - other_benefits: Any benefits mentioned.
        - decision_maker: Name or role of decision maker.
        - decision_maker_email: Email of decision maker.
        - age: Age limit if mentioned (e.g., "20-30 years").
        - rotational_shift: "Yes" or "No".
        - time_period: Contract or intern duration if applicable.
        
        If a field is not found, return an empty string "" for that field.

        Job Description Text:
        {text[:10000]} 
        """
        # Limit text length to avoid token limits if necessary, though 2.5 flash has large context.

        response = model.generate_content(prompt)
        print(response)
        response_text = response.text.strip()
        
        # Clean up if the model adds markdown code blocks despite instructions
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        structured_data = json.loads(response_text)
        return structured_data

    except Exception as e:
        print(f"Error parsing JD with Gemini: {e}")
        return {}
