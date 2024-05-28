from django.db import models
# from django.contrib.auth.models import AbstractUser
# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Ensure superusers have a default role if not provided
        if 'role' not in extra_fields:
            extra_fields['role'] = 'admin'  # or any default role you consider appropriate

        return self.create_user(email, username, password, **extra_fields)
    
class CustomUser(AbstractUser):
    
    ADMIN = 'admin'
    CANDIDATE = 'candidate'
    RECRUITER = 'recruiter'
    CLIENT = 'client'

    ROLE_CHOICES = [
        (ADMIN, 'admin'),
        (CANDIDATE , 'candidate'),
        (RECRUITER, 'recruiter'),
        (CLIENT , 'client'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username
    

