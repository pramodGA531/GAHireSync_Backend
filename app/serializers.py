from rest_framework.serializers import ModelSerializer, Serializer
from .models import *
from rest_framework import serializers
from django.contrib.auth import get_user_model
# from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

# from .models import CustomUser


User = get_user_model()


class LoginSerializer(Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "resume", "is_verified"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        role = validated_data.get("role", "admin")  # Default role if not provided
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            role=role,
        )
        
        user.set_password(validated_data["password"])
        user.save()

        return user
    

class JobPostingSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = JobPostings
        fields = [
            "id",
            "job_title",
            "job_description",
            "job_department",
            "primary_skills",
            "secondary_skills",
            "years_of_experience",
            "ctc",
            "rounds_of_interview",
            "job_location",
            "job_type",
            "job_level",
            "qualifications",
            "timings",
            "other_benefits",
            "working_days_per_week",
            "decision_maker",
            "bond",
            "rotational_shift",
        ]

    def create(self, validated_data):
        # validated_data['interviewers'] = ','.join(validated_data.get('interviewers', []))
        # validated_data['interviewer_emails'] = ','.join(validated_data.get('interviewer_emails', []))
        return JobPostings.objects.create(**validated_data)
    
class EditJobSerializer(serializers.ModelSerializer):
    # interviewers = serializers.ListField(
    #     child=serializers.CharField(max_length=100),
    #     allow_empty=True
    # )
    # interviewer_emails = serializers.ListField(
    #     child=serializers.EmailField(),
    #     allow_empty=True
    # )
    class Meta:
        model = JobPostingEdited
        fields = [
            "id",
            "job_title",
            "job_description",
            "job_department",
            "primary_skills",
            "secondary_skills",
            "years_of_experience",
            "ctc",
            "rounds_of_interview",
            # "interviewers",
            # "interviewer_emails",
            "job_location",
            "job_type",
            "job_level",
            "qualifications",
            "timings",
            "other_benefits",
            "working_days_per_week",
            "decision_maker",
            "bond",
            "rotational_shift",
        ]

        def create(self, validated_data):
            return JobPostingEdited.objects.create(**validated_data)

class GetAllJobPostsSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = JobPostings
        fields = "__all__"

    def get_username(self, obj):
        return obj.username.username
    
class GetAllJobPostEditSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = JobPostingEdited
        fields = "__all__"

    def get_username(self, obj):
        return obj.username.username

class TandC_Serializer(serializers.ModelSerializer):
    username = serializers.CharField(source="username.username", read_only=True)

    class Meta:
        model = TermsAndConditions
        fields = ["username", "terms_and_conditions"]

    def create(self, validated_data):
        return TermsAndConditions.objects.create(**validated_data)


class GetStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

        
class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateResume
        fields = ['id','resume','sender','receiver','job_id','candidate_name', 'candidate_email','contact_number',
                  'alternate_contact_number','current_organisation','current_job_location','current_job_type','date_of_birth',  
                  'total_years_of_experience','skillset','current_ctc',
                  'expected_ctc','notice_period','joining_days_required','highest_qualification','is_viewed','status']   

    def create(self, validated_data):
        return CandidateResume.objects.create(**validated_data)
    
class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['resume']

    def create(self, validated_data):
        return Resume.objects.create(**validated_data)
    
class JobTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostings
        fields = ['job_title']

class NumOfRoundsSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostings
        fields = ['rounds_of_interview']

class CandidateApplicationsSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    rounds_of_interview = serializers.SerializerMethodField()

    class Meta:
        model = CandidateResume
        fields = ['id', 'candidate_name','job_id', 'candidate_email', 'resume', 'job_title','status','rounds_of_interview']  # Add other fields as necessary

    def get_job_title(self, obj):
        return obj.job_id.job_title if obj.job_id else None
    
    def get_rounds_of_interview(self,obj):
        return obj.job_id.rounds_of_interview if obj.job_id else None
    

class InterviewManageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewsSchedule
        fields = '__all__'

    def create(self,validated_data):
        return InterviewsSchedule.objects.create(**validated_data)
    
class JobDetailsForInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostings
        fields = ['job_title','rounds_of_interview','id']

class InterviewerDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerDetails
        fields = '__all__'
    
    def create(self,validated_data):
        InterviewerDetails.objects.create(**validated_data)
    
class InterviewerDetailsEditedSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerDetailsEdited
        fields = '__all__'
    
    def create(self,validated_data):
        InterviewerDetailsEdited.objects.create(**validated_data)

class RoundsDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundDetails
        fields = '__all__'

    def create(self, validated_data):
        instance = RoundDetails.objects.create(**validated_data)
        return instance
    
class ResumeBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeBank
        fields = ['first_name','last_name','middle_name','resume']

    def create(self, validated_data):
        instance = ResumeBank.objects.create(**validated_data)
        return instance
    
class ClientSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDetails
        fields = '__all__'

    def create(self , validated_data):
        instance = ClientDetails.objects.create(**validated_data)
        return instance