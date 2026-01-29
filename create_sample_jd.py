from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, y, "Job Description Sample")
    y -= 30
    
    c.setFont("Helvetica", 12)
    
    data = {
        "Job Title": "Senior Software Engineer",
        "Job Type": "Full Time",
        "Industry": "Information Technology",
        "Job Department": "Engineering",
        "Job Level": "Senior",
        "Job Description": "We are looking for a skilled Senior Software Engineer to join our team. You will be responsible for developing high-quality software solutions.",
        "CTC": "20-25 LPA",
        "Notice Period": "30 days (Need to serve notice)",
        "Notice Time": "30 Days",
        "Qualifications": "B.Tech in Computer Science",
        "Languages": "English, Hindi",
        "Working Days Per Week": "5",
        "Timings": "Day Shift (9AM to 6PM)",
        "Visa Status": "Not Required",
        "Gender": "No Mention",
        "Differently Abled": "No",
        "Bond": "None",
        "Other Benefits": "Health Insurance, Stock Options",
        "Passport Availability": "Required",
        "Decision Maker": "Hiring Manager",
        "Decision Maker Email": "hiring@example.com",
        "Age Limit": "24-35 years",
        "Rotational Shift": "No",
        "Probation Period": "3 Months",
        "Probation Type": "Paid",
        "Years of Experience": "4-6 years",
        "Time Period": "Permanent",
        "Skills": "Python, Django, React, JavaScript, SQL, AWS, Docker"
    }
    
    for key, value in data.items():
        if y < 40:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 12)
            
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y, f"{key}:")
        
        # Simple text wrapping for long descriptions
        if len(key) + len(value) > 80 or key == "Job Description":
             c.setFont("Helvetica", 12)
             y -= 15
             c.drawString(40, y, value)
        else:
            c.setFont("Helvetica", 12)
            c.drawString(150, y, value)
            
        y -= 25

    c.save()
    print(f"PDF created: {filename}")

if __name__ == "__main__":
    create_pdf("Sample_JD_Test.pdf")
