from .models import *


class JobApplication(models.Model):
    SELECTED = 'selected'
    REJECTED = 'rejected'
    HOLD = 'hold'
    PENDING = 'pending'
    PROCESSING = 'processing'
    ACCEPTED = 'accepted'
    APPLIED = 'applied'
    JOBCLOSED = 'job_closed'
    

    STATUS = [
        (SELECTED, 'selected'),
        (REJECTED, 'rejected'),
        (HOLD, 'hold'),
        (PENDING, 'pending'),
        (PROCESSING, 'processing'),
        (JOBCLOSED, 'job_closed'),
    ]

    id = models.AutoField(primary_key=True)
    resume = models.ForeignKey(CandidateResume, on_delete=models.CASCADE, related_name="job_application")
    job_location = models.ForeignKey(JobLocationsModel, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices= STATUS, default='applied')
    attached_to = models.ForeignKey(CustomUser, related_name="sent_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "recruiter"})
    receiver = models.ForeignKey(CustomUser, related_name="received_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "client"})
    message = models.TextField(null=True, blank=True)
    round_num = models.IntegerField(default=0)
    next_interview = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE, blank=True, default=None,null=True)
    application_date = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(blank= True,default= None ,  null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now = True,)
    sender = models.ForeignKey(CustomUser, related_name='Actual_sender', on_delete=models.CASCADE, null=True, limit_choices_to={'role':"recruiter"})
    is_incoming = models.BooleanField(default=False)
    is_closed = models.BooleanField(default = False)
    objects = ActiveApplicationsManager() 
    all_objects = models.Manager()
    class Meta:
        unique_together = ('job_location','resume')
        default_manager_name = 'objects'

    def __str__(self):
        return f"{self.resume.candidate_name} applied for {self.job_location.job_id.job_title}"
    




class CandidateResume(models.Model):
    PERMANENT = 'permanent'
    CONTRACT = 'contract'
    WORKING = 'working'
    NOT_WORKING = 'not_working'
    SERVING_NOTICE = 'serving_notice'

    EMPLOYMENT_TYPE_CHOICES = [
        (PERMANENT, 'Permanent'),
        (CONTRACT, 'Contract'),
    ]

    JOB_STATUS = [
        (WORKING, 'working'),
        (NOT_WORKING, 'not_working'),
        (SERVING_NOTICE, 'serving_notice'),
    ]

    id = models.AutoField(primary_key=True)
    resume = models.FileField(upload_to='Resumes/')
    candidate_name = models.CharField(max_length=100)
    candidate_email = models.EmailField(null=True, )
    contact_number = models.CharField(max_length=15, null=True,)
    alternate_contact_number = models.CharField(max_length=15, null=True, blank=True)
    other_details = models.CharField(max_length=100, null=True, blank=True, )
    current_organisation = models.CharField(max_length=100, null=True, blank=True)
    current_job_location = models.CharField(max_length=100, null=True, blank=True)
    current_job_type = models.CharField(max_length=50, null=True, blank=True, choices=EMPLOYMENT_TYPE_CHOICES, default=PERMANENT)
    date_of_birth = models.DateField(null=True, blank=True)
    experience = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    expected_ctc = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    notice_period = models.IntegerField(default=0)
    job_status = models.CharField(max_length=30, choices=JOB_STATUS)
    highest_qualification = models.CharField(max_length=255,blank=True, default='B Tech')
    joining_days_required = models.IntegerField(default="7")

    def __str__(self):
        return self.candidate_name

class CandidateSkillSet(models.Model):
    candidate = models.ForeignKey(CandidateResume, on_delete=models.CASCADE, related_name='skills')
    is_primary = models.BooleanField(default=False)
    skill_name = models.CharField(max_length=100)
    skill_metric = models.CharField(max_length=50)
    metric_value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.candidate.candidate_name}'s skill {self.skill_name}"
    



class CandidateProfile(models.Model):
    profile = models.ImageField(upload_to='Candidate/Profile/', null=True, blank=True)
    name = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='candidate_name')
    about = models.TextField(blank=True)  
    email = models.EmailField(unique=True)  
    first_name = models.CharField(max_length=100, blank=True)  
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    communication_address = models.TextField(blank=True)
    current_salary = models.TextField(blank=True, default='50000')
    expected_salary = models.TextField(blank=True, default= '70000')
    joining_details= models.TextField(blank= True, default = 'Can join in 7 days')
    permanent_address = models.TextField(blank=True)
    phone_num = models.CharField(max_length=15, blank=True)  
    date_of_birth = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=50, blank=True)
    linked_in = models.URLField(null=True, blank=True)  
    instagram = models.URLField(null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    blood_group = models.CharField(max_length=10,blank=True)
    experience_years = models.CharField(max_length=30, blank=True)
    skills = models.TextField(blank=True)  
    current_company = models.CharField(max_length=200, blank=True)
    resume = models.FileField(upload_to='Candidate/Resumes/', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name.username

    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []
    
class CandidateEvaluation(models.Model):

    SELECTED = 'selected'
    REJECTED = 'rejected'
    HOLD = 'hold'
    PENDING = 'pending'

    STATUS = [
        (SELECTED, 'selected'),
        (REJECTED, 'rejected'),
        (HOLD, 'hold'),
        (PENDING, 'pending')
    ]

    id = models.AutoField(primary_key=True)
    job_application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    job_location = models.ForeignKey(JobLocationsModel, on_delete=models.CASCADE)
    interview_schedule = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    remarks = models.TextField(null=True, blank=True)
    round_num = models.IntegerField()
    primary_skills_rating = models.TextField(null=True)
    secondary_skills_ratings = models.TextField(null = True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=40, choices=STATUS, default='pending')
    class Meta:
        unique_together = ('job_application','round_num')

    def __str__(self):
        return f"Evaluation for {self.job_application.resume.candidate_name}"


class CandidateDocuments(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="candidate_documents")
    document_name = models.CharField(max_length=50)
    document = models.FileField(upload_to='Candidate/Documents', null=True, blank=True)

    def __str__(self):
        return f"{self.candidate.name.username}'s {self.document_name}"

class CandidateCertificates(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='candidate_certificates')
    certificate_name = models.CharField(max_length=50)
    certificate_image = models.FileField(upload_to='Candidate/Certificates/')

    def __str__(self):
        return f"{self.candidate.name.username}'s {self.certificate_name} certificate"

class CandidateExperiences(models.Model):
    WORKING = 'working'
    NOTWORKING = 'not_working'

    STATUS_CHOICES = [
        (WORKING,'working'),
        (NOTWORKING, 'not_working')
    ]

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='candidate_experience')
    role = models.CharField(max_length=50)
    job_type = models.CharField(max_length=50)
    company_name = models.CharField(max_length=100)
    from_date = models.DateField()
    is_working = models.BooleanField(default=False)
    to_date = models.DateField(null=True ,blank=True)
    reason_for_resignation = models.TextField(null=True,blank=True)
    relieving_letter  = models.FileField(upload_to='Candidate/Experience/Leter', null=True, blank=True)
    pay_slip1 = models.FileField(upload_to='Candidate/Experience/PaySlip1/', blank=True, null=True)
    pay_slip2 = models.FileField(upload_to='Candidate/Experience/PaySlip2/', blank=True, null=True)
    pay_slip3 = models.FileField(upload_to='Candidate/Experience/PaySlip3/', blank=True, null=True)

    def __str__(self):
        return f"{self.candidate.name.username} experience in {self.company_name}"


class CandidateEducation(models.Model):
    candidate = models.ForeignKey(CandidateProfile,on_delete=models.CASCADE, related_name='candidate_education')
    institution_name = models.CharField(max_length=150)
    grade = models.CharField(max_length=30)
    education_proof = models.FileField(upload_to='Candidate/Education')
    field_of_study = models.CharField(max_length=30, )
    start_date = models.DateField()
    end_date = models.DateField()
    degree = models.CharField(max_length=40)

    def __str__(self):
        return f"{self.candidate.name.username}-{self.field_of_study} education details"