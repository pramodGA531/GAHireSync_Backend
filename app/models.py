from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.postgres.fields import ArrayField
import decimal
from django.utils import timezone

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

        # Ensure superusers have a default role if not provided
        if "role" not in extra_fields:
            extra_fields["role"] = (
                "admin"  # or any default role you consider appropriate
            )

        return self.create_user(email, username, password, **extra_fields)


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
    email_token = models.CharField(max_length=20 , null=False, default='')
    is_verified = models.BooleanField(default=False)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    
    def __str__(self):
        return self.username
    
class ClientDetails(models.Model):
    username = models.CharField(max_length=100)
    email = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name_of_organization = models.CharField(max_length=200)
    designation = models.TextField()
    contact_number = models.IntegerField()
    website_url = models.URLField()
    gst= models.CharField(max_length=100)
    company_pan = models.CharField(max_length=20)
    company_address = models.TextField()
    

    
def currencyInIndiaFormat(n):
  d = decimal.Decimal(str(n))
  if d.as_tuple().exponent < -2:
    s = str(n)
  else:
    s = '{0:.2f}'.format(n)
  l = len(s)
  i = l-1
  res = ''
  flag = 0
  k = 0
  while i>=0:
    if flag==0:
      res = res + s[i]
      if s[i]=='.':
        flag = 1
    elif flag==1:
      k = k + 1
      res = res + s[i]
      if k==3 and i-1>=0:
        res = res + ','
        flag = 2
        k = 0
    else:
      k = k + 1
      res = res + s[i]
      if k==2 and i-1>=0:
        res = res + ','
        flag = 2
        k = 0
    i = i - 1
  return res[::-1]

class JobPostings(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"}
    )
    job_title = models.CharField(max_length=255,default='')
    job_department = models.CharField(max_length=100,default='')
    job_description = models.TextField()
    primary_skills = models.TextField()
    secondary_skills = models.TextField(blank=True, null=True)
    years_of_experience = models.IntegerField()
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    # interviewers = models.TextField()
    # interviewer_emails = models.TextField(default='')
    job_location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=100,default='')
    job_level = models.CharField(max_length=100, default='')
    qualifications = models.TextField(default='')
    timings = models.CharField(max_length=100,default='')
    other_benefits = models.TextField(default='')
    working_days_per_week = models.IntegerField(default=5)
    decision_maker = models.CharField(max_length=100, default='')
    bond = models.TextField(max_length=255, default='')
    rotational_shift = models.BooleanField()
    status = models.CharField(max_length=10,default = 'opened')
    is_approved = models.BooleanField(default=True)
    is_assigned = models.ForeignKey(CustomUser, related_name='assigned_jobs',on_delete=models.CASCADE, limit_choices_to={"role": "staff"},null=True,default='')


    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []

    def get_secondary_skills_list(self):
        return self.secondary_skills.split(",") if self.secondary_skills else []

    # def get_interviewers(self):
    #     return self.interviewers.split(",") if self.interviewers else []

    def get_currency(self):
       return currencyInIndiaFormat(self.ctc)

    def __str__(self):
        return self.job_title
    

class InterviewerDetails(models.Model):
    FACE ='face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    MODE_OF_INTERVIEW = [
       (FACE,'face_to_face'),
       (ONLINE,'online'),
       (TELEPHONE,'telephone'),
    ]

    job_id = models.ForeignKey(JobPostings,on_delete=models.CASCADE)
    round_num = models.IntegerField(default=0)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    type_of_interview = models.CharField(max_length=20,choices=MODE_OF_INTERVIEW)

    def __str__(self):
        return self.name

    
class JobPostingEdited(models.Model):

    PENDING = 'pending'
    REJECTED = 'rejected'
    APPROVED = 'approved'

    STATUS = [
       (PENDING,'pending'),
       (REJECTED,'rejected'),
       (APPROVED,'approved'),
    ]
    id= models.OneToOneField(JobPostings,on_delete=models.CASCADE,primary_key=True)
    username = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"}
    )
    job_title = models.CharField(max_length=255,default='')
    job_department = models.CharField(max_length=100,default='')
    job_description = models.TextField()
    primary_skills = models.TextField()
    secondary_skills = models.TextField(blank=True, null=True)
    years_of_experience = models.IntegerField()
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    job_location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=100,default='')
    job_level = models.CharField(max_length=100, default='')
    qualifications = models.TextField(default='')
    timings = models.CharField(max_length=100,default='')
    other_benefits = models.TextField(default='')
    working_days_per_week = models.IntegerField(default=5)
    decision_maker = models.CharField(max_length=100, default='')
    bond = models.TextField(max_length=255, default='')
    rotational_shift = models.BooleanField()
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    message = models.TextField(default='')
    # is_approved = models.BooleanField(default=True)
    # is_assigned = models.ForeignKey(CustomUser, related_name='assigned_to',on_delete=models.CASCADE, limit_choices_to={"role": "staff"},null=True,default='')

    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []

    def get_secondary_skills_list(self):
        return self.secondary_skills.split(",") if self.secondary_skills else []

    def get_interviewers(self):
        return self.interviewers.split(",") if self.interviewers else []

    def get_currency(self):
       return currencyInIndiaFormat(self.ctc)

    def __str__(self):
        return self.job_title


class TermsAndConditions(models.Model):
    username = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "manager"}
    )
    terms_and_conditions = models.TextField(default="")

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
        (WORKING , 'working'),
        (NOT_WORKING, 'not_working'),
        (SERVING_NOTICE , 'serving_notice'),
    ]

    ACCEPTED = 'accepted'
    REJECTED =  'rejected'
    HOLD =  'hold'
    PENDING =   'pending'
    ROUND1 = 'round1'
    ROUND2 = 'round2'
    ROUND3 = 'round3'
    ROUND4 = 'round4'
    ROUND5 = 'round5'
    SHORTLISTED = 'shortlisted'


    APPLICATION_STATUS =[
        (ACCEPTED , 'accepted'),
        (REJECTED, 'rejected'),
        (HOLD,'hold'),
        (PENDING, 'pending'),
        (ROUND1, 'round1'),
        (ROUND2, 'round2'),
        (ROUND3, 'round3'),
        (ROUND4, 'round4'),
        (ROUND5, 'round5'),
        (SHORTLISTED,'shortlisted'),
    ]

    resume = models.FileField(upload_to='Resumes/')
    job_id = models.ForeignKey(JobPostings, related_name="resumes", on_delete=models.CASCADE)
    candidate_name = models.CharField(max_length=40, null=True, default='')
    candidate_email = models.EmailField(null=True, default='')
    contact_number = models.CharField(max_length=15, null=True, default='')  # Changed to CharField to support international phone numbers
    alternate_contact_number = models.CharField(max_length=15, null=True, blank=True)
    other_details = models.CharField(max_length=100, null=True, blank=True, default='')  # Made it optional with blank=True
    sender = models.ForeignKey(CustomUser, related_name="sent_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "recruiter"})
    receiver = models.ForeignKey(CustomUser, related_name="received_resumes", on_delete=models.CASCADE, null=True, limit_choices_to={"role": "client"})
    message = models.TextField(null=True, blank=True)  # Made it optional with blank=True
    current_organisation = models.CharField(max_length=100, null=True, default='')
    current_job_location = models.CharField(max_length=100, null=True, default='')
    current_job_type = models.CharField(max_length=50, choices=EMPLOYMENT_TYPE_CHOICES, default=PERMANENT)
    date_of_birth = models.DateField(null=True)
    total_years_of_experience = models.IntegerField( null=True, blank=True)  # Total years of experience can be in decimal
    # years_of_experience_in_cloud = models.Field(max_digits=5, decimal_places=2, null=True, blank=True)  # Years of experience in cloud can be in decimal
    skillset = models.JSONField(null=True, blank=True)  # Skillset can be stored as text
    job_status = models.CharField(max_length=20, null=True, choices=JOB_STATUS)
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Current CTC can be in decimal
    expected_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Expected CTC can be in decimal
    notice_period = models.CharField(max_length=50, null=True, blank=True)  # Notice period can be stored as text
    joining_days_required = models.IntegerField(null=True, blank=True)  # Number of days required for joining
    highest_qualification = models.CharField(max_length=100, null=True, blank=True)   # Alternate contact number can be stored as text
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    on_hold = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS,null=True )

    class Meta:
        constraints =[
           models.UniqueConstraint(
              fields=['job_id','candidate_email'] , name='unique_job_id_candidate_email_constraint'
           )
        ]

    def __str__(self):
        return f"{self.candidate_name}'s Resume"
    
class RoundDetails(models.Model):
    job_id = models.ForeignKey(JobPostings,on_delete=models.CASCADE)
    round_num = models.IntegerField(default=0)
    candidate = models.ForeignKey(CandidateResume,on_delete=models.CASCADE)
    feedback = models.TextField(default='')

    def __str__(self):
       return f"{self.candidate}'s feedback"

class Resume(models.Model):
    id = models.AutoField(primary_key=True)
    resume = models.FileField(upload_to='store/resumes/')

class InterviewsSchedule(models.Model):
    job_id = models.ForeignKey(JobPostings,on_delete=models.CASCADE)
    resume_id = models.ForeignKey(CandidateResume, on_delete=models.CASCADE)
    recruiter_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "recruiter"},default='')
    event_description = models.TextField()
    interview_time = models.DateTimeField(default='')
    round_num = models.IntegerField()

    def __str__(self):
       return self.resume_id
   

class InterviewerDetailsEdited(models.Model):
    FACE ='face_to_face'
    ONLINE = 'online'
    TELEPHONE = 'telephone'

    MODE_OF_INTERVIEW = [
       (FACE,'face_to_face'),
       (ONLINE,'online'),
       (TELEPHONE,'telephone'),
    ]

    job_id = models.ForeignKey(JobPostings,on_delete=models.CASCADE)
    round_num = models.IntegerField(default=0)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    type_of_interview = models.CharField(max_length=20,choices=MODE_OF_INTERVIEW)
    status = models.CharField(default = 'pending',max_length=20)
    edited_by = models.CharField(default='',max_length=20)

    def __str__(self):
       return f"${self.name} edited"

class ResumeBank(models.Model):
    MALE = 'male'
    FEMALE  = 'female'
    TRANSGENDER = 'transgender'

    GENDER = [
      (MALE,'male'),
      (FEMALE, 'female'),
      (TRANSGENDER,'transgender'),
    ]

    resume = models.FileField(upload_to='Resumes/')
    freeze = models.BooleanField(default=False)
    freeze_until = models.DateTimeField(null=True, blank=True)
    # candidate_name = models.CharField(max_length=40, null=True, default='')
    # candidate_email = models.EmailField(null=True, default='')
    # contact_number = models.CharField(max_length=15, null=True, default='') # Changed to CharField to support international phone numbers
    # alternate_contact_number = models.CharField(max_length=15, null=True, blank=True)
    position = models.CharField(max_length=50, null=True, default='')
    first_name = models.CharField(max_length=30, null=True, default='')
    last_name = models.CharField(max_length=30, null=True, default='')
    middle_name = models.CharField(max_length=30, null=True, default='')
    age = models.PositiveIntegerField( default=1)
    gender = models.CharField(max_length=15,choices=GENDER)
    address = models.TextField( null=True, default='')
    cover_letter = models.TextField( null=True, default='')
   
    def freeze_resume(self, days = 1):
       self.freeze =  True
       self.freeze_until = timezone.now() + timezone.timedelta(days=days)
       self.save()

    def is_frozen(self):
       return self.freeze_until is not None and self.freeze_until > timezone.now()

