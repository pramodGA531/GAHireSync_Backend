from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.postgres.fields import ArrayField


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

    def __str__(self):
        return self.username


class JobPostings(models.Model):
    username = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "client"}
    )
    job_description = models.TextField()
    primary_skills = models.TextField()
    secondary_skills = models.TextField(blank=True, null=True)
    years_of_experience = models.IntegerField(default=0)
    ctc = models.CharField(max_length=50)
    rounds_of_interview = models.IntegerField()
    interviewers = models.TextField()
    job_location = models.CharField(max_length=100)

    def get_primary_skills_list(self):
        return self.primary_skills.split(",") if self.primary_skills else []

    def get_secondary_skills_list(self):
        return self.secondary_skills.split(",") if self.secondary_skills else []

    def get_interviewers(self):
        return self.interviewers.split(",") if self.interviewers else []

    def __str__(self):
        return self.job_description


class TermsAndConditions(models.Model):
    username = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, limit_choices_to={"role": "manager"}
    )
    terms_and_conditions = models.TextField(default="")
