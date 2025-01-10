from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        return self.create_user(email, username, password, **extra_fields)


# Custom User Model
class CustomUser(AbstractUser):
    ADMIN = "admin"
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    CLIENT = "client"
    MANAGER = "manager"

    ROLE_CHOICES = [
        (ADMIN, "admin"),
        (CANDIDATE, "candidate"),
        (RECRUITER, "recruiter"),
        (CLIENT, "client"),
        (MANAGER, "manager"),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="user")
    credit = models.IntegerField(default=0)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE, null=True, blank=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.username


# Organization Model
class Organization(models.Model):
    name = models.CharField(max_length=255)
    org_code = models.CharField(max_length=255,unique=True)
    contact_number = models.CharField(max_length=255,unique=True)
    website_url = models.CharField(max_length=255,unique=True)
    gst_number = models.CharField(max_length=255,unique=True)
    company_pan = models.CharField(max_length=255,unique=True)
    company_address = models.CharField(max_length=255,unique=True)
    is_subscribed = models.BooleanField(default=False)
    manager = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="managing_organization")
    recruiters = models.ManyToManyField(CustomUser, related_name="recruiting_organization", blank=True,null=True)

    def __str__(self):
        return self.name


# Organization Terms Model
class OrganizationTerms(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="terms")
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    replacement_clause = models.IntegerField(default=90)
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Terms for {self.organization.name}"


# User Profile Model
class UserProfile(models.Model):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'

    GENDER_CHOICES = [
        (MALE, 'male'),
        (FEMALE, 'female'),
        (OTHER, 'other'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30, null=True, )
    last_name = models.CharField(max_length=30, null=True, )
    gender = models.CharField(max_length=15, choices=GENDER_CHOICES)
    address = models.TextField(null=True, )
    phone_number = models.CharField(max_length=15, null=True, )

    def __str__(self):
        return f"Profile of {self.user.username}"


# Client Details Model
class ClientDetails(models.Model):
    username = models.CharField(max_length=100)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name_of_organization = models.CharField(max_length=200)
    designation = models.TextField()
    contact_number = models.BigIntegerField()
    website_url = models.CharField(max_length=255)
    gst_number = models.CharField(max_length=100)
    company_pan = models.CharField(max_length=20)
    company_address = models.TextField()

    def __str__(self):
        return self.name_of_organization


# Job Postings Model
class JobPostings(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"})
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255, )
    job_department = models.CharField(max_length=100, )
    job_description = models.TextField()
    primary_skills = models.TextField()
    secondary_skills = models.TextField(blank=True, null=True)
    years_of_experience = models.TextField(max_length=100)
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    job_locations = models.CharField(max_length=100)
    job_type = models.CharField(max_length=100, )
    job_level = models.CharField(max_length=100, )
    qualifications = models.TextField()
    timings = models.CharField(max_length=100 )
    other_benefits = models.TextField()
    working_days_per_week = models.IntegerField(default=5)
    decision_maker = models.CharField(max_length=100, )
    decision_maker_email = models.CharField(max_length=100, )
    bond = models.TextField(max_length=255, )
    rotational_shift = models.BooleanField()
    status = models.CharField(max_length=10, default='opened')
    is_approved = models.BooleanField(default=True)
    is_assigned = models.ForeignKey(CustomUser, related_name='assigned_jobs', on_delete=models.CASCADE, limit_choices_to={"role": "recruiter"}, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    age = models.CharField(max_length=255 , default = "")
    gender = models.CharField(max_length = 100 , default = "")
    visa_status = models.CharField(max_length=100, default=  "")
    time_period = models.CharField(max_length=50 , default="")
    qualification_department = models.CharField(max_length=50, default= '')
    notice_period = models.CharField(max_length=30, default="")
    notice_time = models.CharField(max_length=30, default="")
    industry = models.CharField(max_length=40 , default = "")
    differently_abled = models.CharField(max_length=40, default=" ")
    languages = models.CharField(max_length=100 , default=" ")


    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []

    def get_secondary_skills_list(self):
        return self.secondary_skills.split(",") if self.secondary_skills else []
    
    def get_locations(self):
        return self.job_locations.split(",") if self.job_locations else []
    
    def get_languages(self):
        return self.languages.split(",") if self.languages else []

    def __str__(self):
        return self.job_title
    

class JobPostingsEditedVersion(models.Model):
    id = models.ForeignKey(JobPostings, on_delete= models.CASCADE, primary_key=True)
    edited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "manager"})
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, default="")
    job_title = models.CharField(max_length=255, )
    job_department = models.CharField(max_length=100, )
    job_description = models.TextField()
    primary_skills = models.TextField()
    secondary_skills = models.TextField(blank=True, null=True)
    years_of_experience = models.TextField(max_length=100)
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    job_locations = models.CharField(max_length=100)
    job_type = models.CharField(max_length=100, )
    job_level = models.CharField(max_length=100, )
    qualifications = models.TextField()
    timings = models.CharField(max_length=100 )
    other_benefits = models.TextField()
    working_days_per_week = models.IntegerField(default=5)
    decision_maker = models.CharField(max_length=100, )
    decision_maker_email = models.CharField(max_length=100, )
    bond = models.TextField(max_length=255, )
    rotational_shift = models.BooleanField()
    age = models.CharField(max_length=255 , default = "")
    gender = models.CharField(max_length = 100 , default = "")
    visa_status = models.CharField(max_length=100, default=  "")
    time_period = models.CharField(max_length=50 , default="")
    qualification_department = models.CharField(max_length=50, default= '')
    notice_period = models.CharField(max_length=30, default="")
    notice_time = models.CharField(max_length=30, default="")
    industry = models.CharField(max_length=40 , default = "")
    differently_abled = models.CharField(max_length=40, default=" ")
    languages = models.CharField(max_length=100 , default=" ")
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []

    def get_secondary_skills_list(self):
        return self.secondary_skills.split(",") if self.secondary_skills else []
    
    def get_locations(self):
        return self.job_locations.split(",") if self.job_locations else []
    
    def get_languages(self):
        return self.languages.split(",") if self.languages else []

    def __str__(self):
        return self.job_title


# Interviewer Details Model
class InterviewerDetails(models.Model):
    FACE = 'face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    MODE_OF_INTERVIEW = [
        (FACE, 'face_to_face'),
        (ONLINE, 'online'),
        (TELEPHONE, 'telephone'),
    ]

    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    round_num = models.IntegerField()
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW, null=True, blank=True)
    type_of_interview = models.CharField(max_length=35, default='')

    def __str__(self):
        return self.name
    
class InterviewerDetailsEditedVersion(models.Model):
    FACE = 'face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    MODE_OF_INTERVIEW = [
        (FACE, 'face_to_face'),
        (ONLINE, 'online'),
        (TELEPHONE, 'telephone'),
    ]

    job_id = models.ForeignKey(JobPostingsEditedVersion, on_delete=models.CASCADE)
    round_num = models.IntegerField()
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW, default='')
    type_of_interview = models.CharField(max_length=35, default='')

    def __str__(self):
        return self.name


# Candidate Resume Model
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

    resume = models.FileField(upload_to='Resumes/')
    job_id = models.ForeignKey(JobPostings, related_name="resumes", on_delete=models.CASCADE)
    candidate_name = models.CharField(max_length=40, null=True, )
    candidate_email = models.EmailField(null=True, )
    contact_number = models.CharField(max_length=15, null=True, )
    alternate_contact_number = models.CharField(max_length=15, null=True, blank=True)
    other_details = models.CharField(max_length=100, null=True, blank=True, )
    sender = models.ForeignKey(CustomUser, related_name="sent_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "recruiter"})
    receiver = models.ForeignKey(CustomUser, related_name="received_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "client"})
    message = models.TextField(null=True, blank=True)
    current_organisation = models.CharField(max_length=100, null=True, blank=True)
    current_job_location = models.CharField(max_length=100, null=True, blank=True)
    current_job_type = models.CharField(max_length=50, null=True, blank=True, choices=EMPLOYMENT_TYPE_CHOICES, default=PERMANENT)
    date_of_birth = models.DateField(null=True, blank=True)
    experience = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    notice_period = models.IntegerField(default=0)
    job_status = models.CharField(max_length=30, choices=JOB_STATUS, default=WORKING)

    def __str__(self):
        return self.candidate_name


# Job Application Model
class JobApplication(models.Model):
    resume = models.ForeignKey(CandidateResume, on_delete=models.CASCADE)
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Applied')
    application_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resume.candidate_name} applied for {self.job_id.job_title}"


# Interview Schedule Model
class InterviewSchedule(models.Model):
    candidate_resume = models.ForeignKey(CandidateResume, on_delete=models.CASCADE)
    interviewer = models.ForeignKey(InterviewerDetails, on_delete=models.CASCADE)
    schedule_date = models.DateTimeField()
    mode_of_interview = models.CharField(max_length=20, choices=InterviewerDetails.MODE_OF_INTERVIEW)
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='Scheduled')

    def __str__(self):
        return f"Interview scheduled for {self.candidate_resume.candidate_name}"


# Candidate Evaluation Model
class CandidateEvaluation(models.Model):
    interview_schedule = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    remarks = models.TextField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Evaluation for {self.interview_schedule.candidate_resume.candidate_name}"


# Terms Acceptance Model
class ClientTermsAcceptance(models.Model):
    client = models.ForeignKey(ClientDetails, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="client_terms")
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    replacement_clause = models.IntegerField(default=90)
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    accepted_date = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()


    def is_valid(self):
        return self.valid_until >= timezone.now()

    def save(self, *args, **kwargs):
        if not self.valid_until:
            accepted_date = timezone.now()
            self.valid_until = accepted_date + timedelta(days=180)
        super(ClientTermsAcceptance, self).save(*args, **kwargs)

    def __str__(self):
        return f"Terms accepted by {self.client.name_of_organization}"



class NegotiationRequests(models.Model):
    client = models.ForeignKey(ClientDetails, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="negotiation_client_terms")
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    replacement_clause = models.IntegerField(default=90)
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    requested_date = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)
    accepted_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"negotiation by {self.client.name_of_organization}"
