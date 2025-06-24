from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import uuid
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
    INTERVIEWER = 'interviewer'
    ACCOUNTANT='accountant'

    ROLE_CHOICES = [
        (ADMIN, "admin"),
        (CANDIDATE, "candidate"),
        (RECRUITER, "recruiter"),
        (CLIENT, "client"),
        (MANAGER, "manager"),
        (INTERVIEWER, "interviewer"),
        (ACCOUNTANT,"accountant"),
    ]

    username = models.CharField(max_length=150, null=False, blank=False, unique=False)
    email = models.EmailField(unique=True)
    profile = models.ImageField(upload_to='Users/Profile/', null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="admin")
    credit = models.IntegerField(default=0)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE, null=True, blank=True)
    is_verified = models.BooleanField(default = False)
    is_first_login = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']


    def __str__(self):
        return self.username


# Organization Model
class Organization(models.Model):
    name = models.CharField(max_length=255)
    org_code = models.CharField(max_length=255,unique=True)
    contact_number = models.CharField(max_length=255,unique=True)
    website_url = models.CharField(max_length=255,unique=True)
    gst_number = models.CharField(max_length=255,blank=True)
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
    gst_number = models.CharField(max_length=100, blank=True)
    company_pan = models.CharField(max_length=20)
    company_address = models.TextField()
    interviewers = models.ManyToManyField(CustomUser, related_name="client_interviewers", blank=True)
    def __str__(self):
        return self.name_of_organization



# Job Postings Model
class JobPostings(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"})
    jobcode = models.CharField(max_length=40,default='jcd0')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255,)
    job_department = models.CharField(max_length=100,)
    job_description = models.TextField()
    years_of_experience = models.TextField(max_length=100)
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    job_type = models.CharField(max_length=100, )
    probation_type = models.CharField(max_length=20, blank=True)  
    probation_period = models.CharField(max_length=30, blank=True) 
    job_level = models.CharField(max_length=100, blank=True )
    qualifications = models.TextField()
    timings = models.CharField(max_length=100 )
    other_benefits = models.TextField( blank=True, null= True)
    working_days_per_week = models.IntegerField( blank=True, null=True)
    decision_maker = models.CharField(max_length=100,  blank=True)
    decision_maker_email = models.CharField(max_length=100,  blank=True)
    bond = models.TextField(max_length=255, blank=True )
    rotational_shift = models.BooleanField()
    status = models.CharField(max_length=10, default='opened')     
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    age = models.CharField(max_length=255 )
    gender = models.CharField(max_length = 30, blank=True) 
    visa_status = models.CharField(max_length=100, )
    passport_availability = models.CharField(max_length=50,)
    time_period = models.CharField(max_length=50 ,default=" ",blank=True )
    notice_period = models.CharField(max_length=30,)
    notice_time = models.CharField(max_length=30, default=" ",blank=True)
    industry = models.CharField(max_length=40 ,)
    differently_abled = models.CharField(max_length=40, blank=True)
    languages = models.CharField(max_length=100, blank=True)
    job_close_duration = models.DateField(null=True)
    approval_status = models.CharField(max_length=10,default="pending",)
    reason = models.TextField(default="" , null=True, blank=True)
    is_linkedin_posted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username', 'jobcode') 
     
    
    def get_languages(self):
        return self.languages.split(",") if self.languages else []

    def __str__(self):
        return self.job_title
    

class JobLocationsModel(models.Model):
    REMOTE = 'remote'
    HYBRID = 'hybrid'
    OFFICE = 'office'

    WORK_CHOICES = [
        (REMOTE, 'remote'),
        (HYBRID, 'hybrid'),
        (OFFICE, 'office'),
    ]

    job_id = models.ForeignKey(JobPostings, on_delete= models.CASCADE)
    location = models.CharField(max_length=50)
    job_type = models.CharField(max_length=10, choices=WORK_CHOICES)
    positions = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.job_id.job_title} - {self.location}"
    

class AssignedJobs(models.Model):
    job_location = models.ForeignKey(JobLocationsModel, on_delete=models.CASCADE)
    assigned_to = models.ManyToManyField(CustomUser, related_name='assigned_jobs',  limit_choices_to={"role": "recruiter"},  blank=True)
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    
    def __str__(self):
        assigned_names = ", ".join(user.get_full_name() or user.username for user in self.assigned_to.all())
        return f"{self.job_location.job_id.job_title} - {self.job_location.location} is assigned to [{assigned_names}]"



class JobPostingsEditedVersion(models.Model):
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    PENDING = 'pending'

    STATUS_CHOICES = [
        (ACCEPTED,'accepted'),
        (REJECTED,'rejected'),
        (PENDING,'pending'),
    ]
    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE)
    version_number = models.IntegerField(editable=False, default=1)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    base_version = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        if not self.pk:
            latest = JobPostingsEditedVersion.objects.filter(job_id=self.job_id).order_by('-version_number').first()
            self.version_number = (latest.version_number + 1) if latest else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Edit version for job post {self.job_id.job_title}"

class JobPostEditFields(models.Model):
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    PENDING = 'pending'

    STATUS_CHOICES = [
        (ACCEPTED,'accepted'),
        (REJECTED,'rejected'),
        (PENDING,'pending'),
    ]

    edit_id = models.ForeignKey(JobPostingsEditedVersion, on_delete= models.CASCADE)
    field_name = models.CharField(max_length=50)
    field_value = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def clean(self):
        from django.apps import apps
        job_post_fields = [field.name for field in JobPostings._meta.get_fields()]
        if self.field_name not in job_post_fields:
            raise ValidationError(f"'{self.field_name}' is not a valid field of JobPostings model.")

    def save(self, *args, **kwargs):
        self.full_clean()  # This will call the clean() method before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Edit request for field {self.field_name}"


class SkillMetricsModel(models.Model):

    job_id = models.ForeignKey(JobPostings, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.CharField(max_length=50,)
    is_primary = models.BooleanField(default=False)
    metric_type = models.CharField(max_length=100, )
    metric_value = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.job_id.job_title}-{self.skill_name}-{self.metric_type}"
    
class SkillMetricsModelEdited(models.Model):
    METRIC_CHOICES = [
        ('rating', 'rating'),
        ('experience', 'experience'),
    ]
    job_id = models.ForeignKey(JobPostingsEditedVersion, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.CharField(max_length=50,)
    is_primary = models.BooleanField(default=False)
    metric_value = models.CharField(max_length=100, blank=True)
    metric_type = models.CharField(max_length=100, choices=METRIC_CHOICES)

    def __str__(self):
        return f"{self.skill_name}-{self.metric_type}"

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
    name = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role":"interviewer"})
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW)
    type_of_interview = models.CharField(max_length=35, choices = TYPE_OF_INTERVIEW)

    def __str__(self):
        return self.name.username
    
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
    name = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role":"interviewer"})
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW)
    type_of_interview = models.CharField(max_length=35, choices = InterviewerDetails.TYPE_OF_INTERVIEW)

    def __str__(self):
        return self.name.username


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
    highest_qualification = models.CharField(max_length=50,blank=True, default='B Tech')
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
    
class JobPostTerms(models.Model):
    job_id = models.OneToOneField(JobPostings, on_delete=models.CASCADE)
    description = models.TextField(default ='')
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    replacement_clause = models.IntegerField(default=90)
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)


    def is_valid(self):
        return self.valid_until >= timezone.now()
    
    def __str__(self):
        return f"{self.job_id.job_title}'s terms and conditions"

# Interview Schedule Model
class InterviewSchedule(models.Model):
    SCHEDULED = 'scheduled'
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    RESCHEDULE = 'reschedule'

    STATUS_CHOICES = [
        (SCHEDULED, 'scheduled'),
        (PENDING, 'pending'),
        (COMPLETED, 'completed'),
        (CANCELLED ,'cancelled'),
        (RESCHEDULE, 'reschedule'),
    ]
    id = models.AutoField(primary_key=True)
    candidate = models.ForeignKey(CandidateResume, on_delete=models.CASCADE, blank=True, null= True)
    rctr = models.ManyToManyField(CustomUser, blank=True)
    interviewer = models.ForeignKey(InterviewerDetails, on_delete=models.CASCADE,)
    scheduled_date = models.DateField(null= True, blank=True, )
    from_time = models.TimeField(null=True, blank=True,default="00:00:00" )
    to_time = models.TimeField(null=True, blank=True,default="00:00:00" )
    job_location = models.ForeignKey(JobLocationsModel, on_delete=models.CASCADE)
    meet_link = models.URLField(null=True, blank=True)
    round_num = models.IntegerField(default=0)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES, default='scheduled')

    def __str__(self):
        return f"Interview scheduled for {self.candidate.candidate_name} at {self.scheduled_date}"
    
    
# Job Application Model
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
    resume = models.OneToOneField(CandidateResume, on_delete=models.CASCADE, related_name="job_application")
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
    class Meta:
        unique_together = ('job_location','resume')

    def __str__(self):
        return f"{self.resume.candidate_name} applied for {self.job_location.job_id.job_title}"



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

    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    PENDING = 'pending'

    STATUS_CHOICES = [
        (ACCEPTED, 'accepted'),
        (PENDING, 'pending'),
        (REJECTED, 'rejected')
    ]
    
    client = models.ForeignKey(ClientDetails, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="negotiation_client_terms")
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    replacement_clause = models.IntegerField(default=90)
    description = models.TextField(default = '', blank=True, null=True)
    invoice_after = models.IntegerField(default=30)
    payment_within = models.IntegerField(default=7)
    interest_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    requested_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    accepted_date = models.DateTimeField(auto_now=True)
    reason = models.TextField(null=True, default="", blank=True)

    def __str__(self):
        return f"negotiation by {self.client.name_of_organization}"


# Candidate profile model to store all the candidate details
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
    
class RecruiterProfile(models.Model):
    name = models.ForeignKey(CustomUser, on_delete= models.CASCADE, related_name="recruiter_profiles")
    alloted_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='alloted_to')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='workng_in')

    def __str__(self):
        return self.name.username

class SelectedCandidates(models.Model):
    JOINING_STATUS_CHOICES = [
        ('joined', 'joined'),
        ('not_joined', 'not_joined'),
        ('resign','resign'),
        ('left', 'left'),
        ('pending','pending'),
        ('rejected', 'rejected'),
    ]

    REPLACEMENT_STATUS_CHOICES = [
        ('no', 'no'),
        ('pending', 'pending'),
        ('completed','completed'),
        ('incomplete','incomplete')
    ]
    
    CANDIDATE_ACCEPTANCE_CHOICES=[
        ('accepted','accepted'),
        ('rejected','rejected'),
        ('pending','pending'),
    ]
    
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name= 'selected_candidates')
    ctc = models.DecimalField(max_digits=10, decimal_places=2)
    joining_date = models.DateField()
    resigned_date = models.DateField(null=True, blank=True)
    other_benefits = models.CharField(max_length=250, blank=True)
    joining_status = models.CharField(max_length=20, choices=JOINING_STATUS_CHOICES,default='pending')
    candidate_acceptance = models.CharField(max_length= 20,choices=CANDIDATE_ACCEPTANCE_CHOICES,default='pending')
    recruiter_acceptance = models.BooleanField(default=True)
    feedback  = models.CharField(max_length=250, blank=True)
    left_reason = models.CharField(max_length=200, blank=True)
    edit_request=models.CharField(max_length=200,blank=True)
    client_accept_request=models.BooleanField(default=False)
    is_replacement_eligible = models.BooleanField(default= False)
    replacement_status = models.CharField(max_length=50, default='no', choices=REPLACEMENT_STATUS_CHOICES)
    is_replaced = models.BooleanField(default=False)

    def __str__(self):
        return self.application.resume.candidate_name
    
class InvoiceGenerated(models.Model):
    PENDING = 'Pending'
    PAID = 'Paid'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
    ]

    application = models.ForeignKey('JobApplication', on_delete=models.CASCADE,null=True,blank=True)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE,null=True,blank=True)
    client =models.ForeignKey('CustomUser', on_delete=models.CASCADE,null=True,blank=True)
    organization_email = models.EmailField()
    payment_transaction_id=models.CharField(null=True,blank=True,default="null",max_length=20)
    client_email = models.EmailField()
    terms_id = models.IntegerField()
    payment_method=models.CharField(null=True,blank=True,default="null",max_length=20)
    payment_verification = models.BooleanField("Payment Verified", default=False)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING 
    )
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"Invoice for Application {self.application_id} - {self.client_email} ({self.status})"


class Accountants(models.Model):
    organization=models.OneToOneField(Organization,on_delete=models.CASCADE,null=True,blank=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="accountant")
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class ReplacementCandidates(models.Model):
    replacement_with = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name='replacement_with', limit_choices_to={"status":"left"})
    replaced_by = models.OneToOneField(JobApplication,on_delete= models.CASCADE, related_name='replaced_by', null=True, blank=True)
    replacement_within = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=15, default='pending', choices=SelectedCandidates.REPLACEMENT_STATUS_CHOICES)

    def __str__(self):
        return f"{self.replacement_with.resume.candidate_name}'s resume replace"


class Tickets(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    raised_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tickets_raised")
    category = models.CharField(max_length=50)  
    description = models.TextField(default='')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tickets_assigned", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    attachments = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)   

    def __str__(self):
        return f"Ticket ({self.category}) - {self.status} - Raised by {self.raised_by.username}"
    

class Messages(models.Model):
    ticket_id = models.ForeignKey(Tickets, on_delete=models.CASCADE)
    is_user_raised_by = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now=True)
    attachment= models.FileField(upload_to="ticket_attachements/", null=True, blank=True)

    def __str__(self):
        return f"Ticket {self.ticket_id}"
    
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
class BlogPost(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    tags = models.ManyToManyField(Tag, blank=True)
    author=models.CharField(max_length=255,default="ameer")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thumbnail = models.ImageField(upload_to='blog_thumbnails')
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title


class Notifications(models.Model):
    
    # Here in these we Missed the 1) Action Need Field 2) Action (Boolean Field) 3) Action taken Time
    
    # Here I need that to track the requests that if the request are trigger any of the Action then Need To change that requests action for the remainders that would give the appropriate remainders if based on the actions if the action is done then no need to do send the remainder if the action is not done then we need to Send the Remainders 
    
    class CategoryChoices(models.TextChoices):
        NEGOTIATE_TERMS = 'negotiated_terms','NegotiatedTerms'                  #manager
        REJECT_TERMS = 'reject_terms','RejectTerms'                             #client
        ACCEPT_TERMS = 'accept_terms', 'AcceptTerms'                            #client
        CREATE_JOB = 'create_job','CreateJob'                                   #manager
        ASSIGN_INTERVIEWER = 'assign_interviewer','AssignInterviewer'          #interviewer
        ACCEPT_JOB = 'accept_job','AcceptJob'                                   #client
        EDIT_JOB = 'edit_job','EditJob'                                         #client
        ACCEPT_JOB_EDIT = 'accept_job_edit', 'AcceptJobEdit'                    #manager
        REJECT_JOB_EDIT = 'reject_job_edit', 'RejectJobEdit'                    #manager
        PARTIAL_EDIT = 'partial_job_edit', "PartialJobEdit"                     #manager
        REJECT_JOB = 'reject_job','RejectJob'                                   #client
        ASSIGN_JOB = 'assign_job', 'AssignJob'                                  #recruiter
        SEND_APPLICATION = 'send_application','SendApplication'                 #client
        SHORTLIST_APPLICATION = 'shortlist_application','ShortlistApplication'  #recruiter
        SCHEDULE_INTERVIEW = 'schedule_interview','ScheduleInterview'           #interviewer, candidate
        PROMOTE_CANDIDATE = 'promote_candidate', 'PromoteCandidate'             #candidate, recruiter
        REJECT_CANDIDATE = 'reject_candidate', 'RejectCandidate'                #candidate, recruite    r
        ONHOLD_CANDIDATE = 'onhold_candidate', 'OnHoldCandidate'                #client
        SELECT_CANDIDATE =  'select_candidate', 'SelectCandidate'               #client, recruiter
        ACCEPTED_CTC = 'accepted_ctc', 'AcceptedCTC'                            #candidate, recruiter
        CANDIDATE_ACCEPTED = 'candidate_accepted', 'CandidateAccepted'          #client, recruiter
        CANDIDATE_REJECTED = 'candidate_rejected', 'CandidateRejected'          #client, recruiter
        CANDIDATE_LEFT = 'candidate_left', 'CandidateLeft'                      #recruiter, manager  
        CANDIDATE_JOINED = 'candidate_joined', 'CandidateJoined'                #recruiter, manager

 
    sender = models.ForeignKey(CustomUser, related_name='sent_notifications', on_delete=models.CASCADE, default=1)
    receiver = models.ForeignKey(CustomUser, related_name='received_notifications', on_delete=models.CASCADE,null=True, blank=True)
    subject = models.CharField(max_length=255)
    seen = models.BooleanField(default=False) # If Not Seen Then Need 
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=60, choices=CategoryChoices.choices, null=True, blank=True)

    def __str__(self):
        return f"From {self.sender} to {self.receiver}: {self.subject}"



class LinkedinIntegrations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Organization, on_delete=models.CASCADE)
    linkedin_user_id = models.CharField(max_length=255, blank=True, null=True)  
    organization_urn = models.CharField(max_length=255, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)  
    token_expires_at = models.DateTimeField(blank=True, null=True)
    is_linkedin_connected = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agency Linkedin Integration"
        verbose_name_plural = "Agency Linkedin Integrations"

    def __str__(self):
        return self.agency.name
    

class HiresyncLinkedinCred(models.Model):
    organization_urn = models.CharField(max_length=255, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)  
    token_expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Hiresync Integration"



class JobPostingDraftVersion(models.Model):
    username = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"})
    jobcode = models.CharField(max_length=40, default='jcd0', blank=True)
    current_step = models.IntegerField(default=1)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True)
    job_department = models.CharField(max_length=100, blank=True)
    job_description = models.TextField(blank=True)
    years_of_experience = models.CharField(max_length=100, blank=True)
    ctc = models.CharField(max_length=50, blank=True)
    rounds_of_interview = models.IntegerField(blank=True, null=True)
    job_type = models.CharField(max_length=100, blank=True)
    time_period = models.CharField(max_length=50, default="", blank=True)
    probation_period = models.CharField(max_length=30, blank=True)
    probation_type = models.CharField(max_length=20, blank=True)
    job_level = models.CharField(max_length=100, blank=True)
    qualifications = models.TextField(blank=True)
    timings = models.CharField(max_length=100, blank=True)
    other_benefits = models.TextField(blank=True)
    working_days_per_week = models.IntegerField(default=5, blank=True, null=True)
    decision_maker = models.CharField(max_length=100, blank=True)
    decision_maker_email = models.CharField(max_length=100, blank=True)
    bond = models.CharField(max_length=255, blank=True)
    rotational_shift = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default='opened', blank=True)
    assigned_to = models.ManyToManyField(CustomUser, related_name='assigned_jobs_draft', limit_choices_to={"role": "recruiter"}, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    age = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=100, blank=True)
    visa_status = models.CharField(max_length=100, blank=True)
    passport_availability = models.CharField(max_length=50, blank=True)
    qualification_department = models.CharField(max_length=50, blank=True)
    notice_period = models.CharField(max_length=30, blank=True)
    notice_time = models.CharField(max_length=30, default="", blank=True)
    industry = models.CharField(max_length=40, blank=True)
    differently_abled = models.CharField(max_length=40, blank=True)
    languages = models.CharField(max_length=100, blank=True)
    job_close_duration = models.DateField(null=True, blank=True)
    approval_status = models.CharField(max_length=10, default="pending", blank=True)
    reason = models.TextField(default="", null=True, blank=True)
    is_linkedin_posted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username', 'jobcode')

    def get_languages(self):
        return self.languages.split(",") if self.languages else []

    def __str__(self):
        return self.job_title or "Untitled Draft"

    
class JobLocationsDraftVersion(models.Model):
    REMOTE = 'remote'
    HYBRID = 'hybrid'
    OFFICE = 'office'

    WORK_CHOICES = [
        (REMOTE, 'remote'),
        (HYBRID, 'hybrid'),
        (OFFICE, 'office'),
    ]

    job = models.ForeignKey(JobPostingDraftVersion, on_delete=models.CASCADE, related_name='locations')
    location = models.CharField(max_length=50, blank=True)
    job_type = models.CharField(max_length=10, choices=WORK_CHOICES, blank=True)
    positions = models.IntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return f"{self.job.job_title or 'Draft'} - {self.location}"


class SkillMetricsDraftVersion(models.Model):
    job = models.ForeignKey(JobPostingDraftVersion, on_delete=models.CASCADE, related_name="skill_metrics")
    skill_name = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(default=False)
    metric_type = models.CharField(max_length=100, blank=True)
    metric_value = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.job.job_title or 'Draft'} - {self.skill_name or 'Unnamed'}"

    
class InterviewerDetailsDraftVersion(models.Model):
    FACE = 'face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    MODE_OF_INTERVIEW = [
        (FACE, 'Face to Face'),
        (ONLINE, 'Online'),
        (TELEPHONE, 'Telephone'),
    ]

    TECHNICAL = 'technical'
    NONTECHNICAL = 'non-technical'
    ASSIGNMENT = 'assignment'

    TYPE_OF_INTERVIEW = [
        (TECHNICAL, 'Technical'),
        (NONTECHNICAL, 'Non-Technical'),
        (ASSIGNMENT, 'Assignment'),
    ]

    job = models.ForeignKey(JobPostingDraftVersion, on_delete=models.CASCADE, related_name="interviewers")
    round_num = models.IntegerField(default=0, blank=True, null=True)
    name = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "interviewer"}, blank=True, null=True)
    mode_of_interview = models.CharField(max_length=20, choices=MODE_OF_INTERVIEW, blank=True)
    type_of_interview = models.CharField(max_length=35, choices=TYPE_OF_INTERVIEW, blank=True)

    def __str__(self):
        return self.name.username if self.name else "Unnamed Interviewer"
