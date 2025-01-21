from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
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
    recruiters = models.ManyToManyField(CustomUser, related_name="recruiting_organization", blank=True)

    def __str__(self):
        return self.name


# Organization Terms Model
class OrganizationTerms(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="terms")
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    description = models.TextField(default ='')
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
    age = models.CharField(max_length=255 )
    gender = models.CharField(max_length = 100 ,)
    visa_status = models.CharField(max_length=100, )
    time_period = models.CharField(max_length=50 ,default=" ",blank=True )
    qualification_department = models.CharField(max_length=50,)
    notice_period = models.CharField(max_length=30,)
    notice_time = models.CharField(max_length=30, default=" ",blank=True)
    industry = models.CharField(max_length=40 ,)
    differently_abled = models.CharField(max_length=40,)
    languages = models.CharField(max_length=100 ,)
    num_of_positions = models.IntegerField(default=1)
    job_close_duration = models.DateField(null=True)

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
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    PENDING = 'pending'

    STATUS_CHOICES = [
        (ACCEPTED,'accepted'),
        (REJECTED,'rejected'),
        (PENDING,'pending'),
    ]

    id = models.ForeignKey(JobPostings, on_delete= models.CASCADE,primary_key=True)
    username = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role":"client"},related_name="job_post_by_client")
    edited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "manager"},related_name="job_post_edited_by_manager")
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
    age = models.CharField(max_length=255 , )
    gender = models.CharField(max_length = 100 , )
    visa_status = models.CharField(max_length=100, )
    time_period = models.CharField(max_length=50 , default=" ",blank=True)
    qualification_department = models.CharField(max_length=50,)
    notice_period = models.CharField(max_length=30,default=" ",blank=True )
    notice_time = models.CharField(max_length=30, default=" ")
    industry = models.CharField(max_length=40 , )
    differently_abled = models.CharField(max_length=40, )
    languages = models.CharField(max_length=100 , )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    status = models.TextField(choices=STATUS_CHOICES, default='pending')
    num_of_positions = models.IntegerField(default= 1)
    job_close_duration = models.DateField(null=True)

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

    TECHNICAL = 'technical'
    NONTECHNICAL = 'non-technical'
    ASSIGNMENT = 'assignment'

    TYPE_OF_INTERVIEW = [
        (TECHNICAL , 'technical'),
        (NONTECHNICAL , 'non-technical'),
        (ASSIGNMENT , 'assignment'),
    ]

    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    round_num = models.IntegerField(default=0)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW)
    type_of_interview = models.CharField(max_length=35, choices = TYPE_OF_INTERVIEW)

    def __str__(self):
        return self.name
    
class InterviewerDetailsEditedVersion(models.Model):
    FACE = 'face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    TECHNICAL = 'technical'
    NONTECHNICAL = 'non-technical'
    ASSIGNMENT = 'assignment'

    MODE_OF_INTERVIEW = [
        (FACE, 'face_to_face'),
        (ONLINE, 'online'),
        (TELEPHONE, 'telephone'),
    ]

    job_id = models.ForeignKey(JobPostingsEditedVersion, on_delete=models.CASCADE)
    round_num = models.IntegerField()
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW)
    type_of_interview = models.CharField(max_length=35, choices = InterviewerDetails.TYPE_OF_INTERVIEW)

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

    id = models.AutoField(primary_key=True)
    resume = models.FileField(upload_to='Resumes/')
    # job_id = models.ForeignKey(JobPostings, related_name="resumes", on_delete=models.CASCADE)
    candidate_name = models.CharField(max_length=40, null=True, )
    candidate_email = models.EmailField(null=True, )
    contact_number = models.CharField(max_length=15, null=True, )
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

    def __str__(self):
        return self.candidate_name

class PrimarySkillSet(models.Model):
    id = models.AutoField(primary_key=True)
    candidate = models.ForeignKey(CandidateResume,on_delete=models.CASCADE)
    skill = models.CharField(max_length=30)
    years_of_experience = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.candidate.candidate_name} skill {self.skill}"
class SecondarySkillSet(models.Model):
    id = models.AutoField(primary_key=True)
    candidate = models.ForeignKey(CandidateResume,on_delete=models.CASCADE)
    skill = models.CharField(max_length=30)
    years_of_experience = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.candidate.candidate_name} skill {self.skill}"


# Interview Schedule Model
class InterviewSchedule(models.Model):
    SCHEDULED = 'scheduled'
    PENDING = 'pending'
    COMPLETED = 'completed'

    STATUS_CHOICES = [
        (SCHEDULED, 'scheduled'),
        (PENDING, 'pending'),
        (COMPLETED, 'completed')
    ]
    id = models.AutoField(primary_key=True)
    interviewer = models.ForeignKey(InterviewerDetails, on_delete=models.CASCADE)
    schedule_date = models.DateTimeField(null= True, blank=True)
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    round_num = models.IntegerField(default=0)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES, default='scheduled')

    def __str__(self):
        return f"Interview scheduled for "
    
    
# Job Application Model
class JobApplication(models.Model):
    SELECTED = 'selected'
    REJECTED = 'rejected'
    HOLD = 'hold'
    PENDING = 'pending'
    PROCESSING = 'processing'
    APPLIED = 'applied'

    STATUS = [
        (SELECTED, 'selected'),
        (REJECTED, 'rejected'),
        (HOLD, 'hold'),
        (PENDING, 'pending'),
        (APPLIED ,'applied'),
        (PROCESSING, 'processing'),
    ]
    id = models.AutoField(primary_key=True)
    resume = models.ForeignKey(CandidateResume, on_delete=models.CASCADE)
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices= STATUS, default='applied')
    sender = models.ForeignKey(CustomUser, related_name="sent_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "recruiter"})
    receiver = models.ForeignKey(CustomUser, related_name="received_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "client"})
    message = models.TextField(null=True, blank=True)
    round_num = models.IntegerField(default=0)
    next_interview = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE, blank=True, default=None,null=True)
    application_date = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(blank= True,default= None ,  null=True)

    class Meta:
        unique_together = ('job_id','resume')

    def __str__(self):
        return f"{self.resume.candidate_name} applied for {self.job_id.job_title}"



# Candidate Evaluation Model
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
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    interview_schedule = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    remarks = models.TextField(null=True, blank=True)
    round_num = models.IntegerField()
    primary_skills_rating = models.TextField(null=True)
    secondary_skills_ratings = models.TextField(null = True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=40, choices=STATUS, default='pending')
    class Meta:
        unique_together = ('job_id','job_application','round_num')

    def __str__(self):
        return f"Evaluation for {self.job_application.resume.candidate_name}"


# Terms Acceptance Model
class ClientTermsAcceptance(models.Model):
    
    client = models.ForeignKey(ClientDetails, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="client_terms")
    description = models.TextField(default ='')
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
    description = models.TextField(default = '')
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    requested_date = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)
    accepted_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"negotiation by {self.client.name_of_organization}"
