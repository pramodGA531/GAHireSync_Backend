from rest_framework import serializers
from .models import *

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "role",
            "credit",
            "organization",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
        }


class OrganizationSerializer(serializers.ModelSerializer):
    recruiters = CustomUserSerializer(many=True,read_only=True)
    class Meta:
        model = Organization
        fields = '__all__'  


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'  

class ClientDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDetails
        fields = '__all__'  


class OrganizationTermsSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()
    
    class Meta:
        model = OrganizationTerms
        fields = '__all__'  

class NegotiationSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()
    client = ClientDetailsSerializer()
    class Meta:
        model = NegotiationRequests
        fields = '__all__' 

class InterviewerDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerDetails
        fields = '__all__'  

class JobPostingsSerializer(serializers.ModelSerializer):
    is_assigned = CustomUserSerializer()
    username = CustomUserSerializer()
    organization = OrganizationSerializer()
    interview_details = InterviewerDetailsSerializer(many=True, read_only=True, source='interviewerdetails_set')
    

    class Meta:
        model = JobPostings
        fields = '__all__'  



class CandidateResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateResume
        fields = '__all__'  

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = '__all__'  

class InterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedule
        fields = '__all__'  

class CandidateEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvaluation
        fields = '__all__'  

class ClientTermsAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientTermsAcceptance
        fields = '__all__'  

class JobPostEditedSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostingsEditedVersion
        fields = '__all__'

class JobPostEditedSerializerMinFields(serializers.ModelSerializer):
    class Meta:
        model = JobPostingsEditedVersion
        fields = ['id', 'job_title', 'organization','edited_by','created_at','is_accepted']


class InterviewDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerDetails
        fields = '__all__'