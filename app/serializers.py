from rest_framework import serializers
from .models import *
from datetime import datetime
from dateutil.relativedelta import relativedelta

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


class ClientDetailsInterviewersSerializer(serializers.ModelSerializer):
    interviewers = CustomUserSerializer(many=True,read_only = True)

    class Meta:
        model = ClientDetails
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
    name = CustomUserSerializer()
    class Meta:
        model = InterviewerDetails
        fields = '__all__'  

class JobPostingsSerializer(serializers.ModelSerializer):
    assigned_to = CustomUserSerializer(many=True)
    username = CustomUserSerializer()
    organization = OrganizationSerializer()
    interview_details = InterviewerDetailsSerializer(many=True, read_only=True, source='interviewerdetails_set')
    
    class Meta:
        model = JobPostings
        fields = '__all__'  


class ClientJobPostingsSerializer(serializers.ModelSerializer):
    assigned_to = CustomUserSerializer(many=True)
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

class PrimarySkillSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrimarySkillSet
        fields = ['skill','years_of_experience']

class SecondarySkillSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondarySkillSet
        fields = ['skill','years_of_experience']


class JobApplicationSerializer(serializers.ModelSerializer):
    # job_id = JobPostingsSerializer()
    # resume = CandidateResumeWithoutContactSerializer()
    
    class Meta:
        model = JobApplication
        fields = '__all__'  


class CandidateResumeWithoutContactSerializer(serializers.ModelSerializer):
    primary_skills = PrimarySkillSetSerializer(many=True, read_only  = True)
    secondary_skills = SecondarySkillSetSerializer(many = True, read_only = True)
    job_application = JobApplicationSerializer( read_only = True)
    class Meta: 
        model = CandidateResume
        exclude = ('contact_number','alternate_contact_number','candidate_email')

class JobApplicationSerializer(serializers.ModelSerializer):
    job_id = JobPostingsSerializer()
    # cand_id=CandidateResumeWithoutContactSerializer()
    
    class Meta:
        model = JobApplication
        fields = '__all__'  
        
class InterviewScheduleSerializer(serializers.ModelSerializer):
    interviewer = InterviewerDetailsSerializer()
    candidate = serializers.StringRelatedField()
    job_id = serializers.PrimaryKeyRelatedField(queryset=JobPostings.objects.all())
    
    class Meta:
        model = InterviewSchedule
        fields = ['id', 'candidate', 'interviewer', 'job_id', 'round_num', 'status_display']
    
    

class CandidateEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvaluation
        fields = '__all__'  

class ClientTermsAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientTermsAcceptance
        fields = '__all__'  

class InterviewDetailsEditedSerializer(serializers.ModelSerializer):
    name = CustomUserSerializer(read_only = True)
    class Meta:
        model = InterviewerDetailsEditedVersion
        fields = '__all__'

class JobPostEditedSerializer(serializers.ModelSerializer):
    interview_details  = InterviewDetailsEditedSerializer(many=True, read_only=True, source='interviewerdetailseditedversion_set')
    edited_by_username = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPostingsEditedVersion
        fields = '__all__'

    def get_edited_by_username(self,obj):
        return obj.edited_by.username if obj.edited_by else None
    
    

class JobPostEditedSerializerMinFields(serializers.ModelSerializer):
    edited_by_username = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    organization_code = serializers.SerializerMethodField()
    class Meta:
        model = JobPostingsEditedVersion
        fields = ['id', 'job_title', 'organization','edited_by','created_at','status', 'edited_by_username','organization_name','organization_code' ]

    def get_edited_by_username(self,obj):
        return obj.edited_by.username if obj.edited_by else None
    
    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None
    
    def get_organization_code(self,obj):
        return obj.organization.org_code if obj.organization else None

class JobPostUpdateSerializer(serializers.ModelSerializer):

    notice_time = serializers.CharField(required=False, allow_blank=True)
    time_period = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = JobPostings
        fields = [
            "organization",
            "job_title",
            "job_department",
            "job_description",
            "primary_skills",
            "secondary_skills",
            "years_of_experience",
            "ctc",
            "rounds_of_interview",
            "job_locations",
            "job_type",
            "job_level",
            "qualifications",
            "qualification_department",
            "timings",
            "other_benefits",
            "working_days_per_week",
            "decision_maker",
            "decision_maker_email",
            "bond",
            "rotational_shift",
            "age",
            "gender",
            "visa_status",
            "time_period",
            "notice_period",
            "notice_time",
            "industry",
            "differently_abled",
            "languages",
            "num_of_positions",
            "job_close_duration",
        ]


class CandidateProfileSerializer(serializers.ModelSerializer):
    name = CustomUserSerializer()
    class Meta:
        model = CandidateProfile
        fields ='__all__'

    def create(self, validated_data):
        custom_user_data = validated_data.pop('name')

        if isinstance(custom_user_data, CustomUser):
            user = custom_user_data
        else:
            try:
                user = CustomUser.objects.get(pk=custom_user_data)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"name": "Invalid user ID. User does not exist."})

        candidate_profile = CandidateProfile.objects.create(name=user, **validated_data)
        return candidate_profile
    
class InterviewScheduleSerializer(serializers.ModelSerializer):
    interviewer = InterviewerDetailsSerializer()
    candidate=CandidateResumeSerializer()
    class Meta:
        model = InterviewSchedule
        fields = ['interviewer', 'schedule_date',"candidate"]

class CandidateCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model= CandidateCertificates
        fields = '__all__'

class CandidateExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateExperiences
        fields = '__all__'
class CandidateEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEducation
        fields = '__all__'

class RecruiterProfileSerializer(serializers.ModelSerializer):
    name = CustomUserSerializer(read_only = True)
    class Meta:
        model = RecruiterProfile
        fields = '__all__'


class CandidateEducationSerializer2(serializers.ModelSerializer):
    result = serializers.SerializerMethodField()
    class Meta:
        model = CandidateEducation
        fields = ['result']
    
    def get_result(self, obj):
        return f"{obj.field_of_study} - {obj.institution_name}"

class CandidateExperienceSerializer2(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()

    class Meta:
        model = CandidateExperiences
        fields = ['company_name','duration']

    def get_duration(self,obj):
        from_date = obj.from_date
        to_date = datetime.today().date() if obj.is_working == True else obj.to_date

        if to_date is None:
            return "Ongoing"  

        diff = relativedelta(to_date, from_date)
        return f"{diff.years} years, {diff.months} months"