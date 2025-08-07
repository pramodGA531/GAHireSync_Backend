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
    recruiters = CustomUserSerializer(many=True, read_only=True)
    # manager = CustomUserSerializer(queryset=CustomUser.objects.all())  

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

class ClientOrganziationSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()
    client = ClientDetailsSerializer()

    class Meta:
        model = ClientOrganizations
        fields = '__all__'

class NegotiationSerializer(serializers.ModelSerializer):
    client_organization = ClientOrganziationSerializer()
    class Meta:
        model = NegotiationRequests
        fields = '__all__' 

class InterviewerDetailsSerializer(serializers.ModelSerializer):
    
    name = CustomUserSerializer()
    class Meta:
        model = InterviewerDetails
        fields = '__all__'  

class SkillMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillMetricsModel
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLocationsModel
        fields = '__all__'

class AssignedJobsSerializer(serializers.ModelSerializer):
    class Meta:
        models = AssignedJobs
        fields = '__all__'


class JobPostingsSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SerializerMethodField()
    username = CustomUserSerializer()
    organization = OrganizationSerializer()
    selectedCandidatesCount = serializers.SerializerMethodField()  
    onHoldCount = serializers.SerializerMethodField()
    rejectedCount = serializers.SerializerMethodField()
    pendingCount = serializers.SerializerMethodField()
    locations = LocationSerializer(many= True, read_only = True, source = 'joblocationsmodel_set')
    interview_details = InterviewerDetailsSerializer(many=True, read_only=True, source='interviewerdetails_set')
    skills = SkillMetricSerializer(many=True)
    
    
    class Meta:
        model = JobPostings
        fields = '__all__'

    def get_selectedCandidatesCount(self, obj):
        return SelectedCandidates.objects.filter(application__job_location__job_id=obj).count()

    def get_onHoldCount(self, obj):
        return SelectedCandidates.objects.filter(application__status='onHold', application__job_location__job_id=obj).count()

    def get_rejectedCount(self, obj):
        return SelectedCandidates.objects.filter(application__status='rejected', application__job_location__job_id=obj).count()

    def get_pendingCount(self, obj):
        return SelectedCandidates.objects.filter(application__status='pending', application__job_location__job_id=obj).count()
    
    def get_assigned_to(self, obj):
        job_id = obj.id
        assigned_jobs = AssignedJobs.objects.filter(
            job_location__job_id=job_id
        ).prefetch_related('assigned_to', 'job_location')

        result = []

        for assigned_job in assigned_jobs:
            location_name = assigned_job.job_location.location

            for recruiter in assigned_job.assigned_to.all():
                result.append({
                    "id": recruiter.id,
                    "username": recruiter.username,
                    "email": recruiter.email,
                    "location": location_name,
                })

        return result
    
   
    def to_representation(self, instance):
        data = super().to_representation(instance)
        primary_skills = []
        secondary_skills = []
        for skill in data['skills']:
            if (skill.get('is_primary', True)):
                primary_skills.append(skill)
            else:
                secondary_skills.append(skill)

        data['primary_skills'] = primary_skills
        data['secondary_skills'] = secondary_skills

        del data['skills']
        return data
    
class CandidateJobpostSerializer(serializers.ModelSerializer):

    skills = SkillMetricSerializer(many=True)
    locations = LocationSerializer(many=True, read_only = True, source = 'joblocationsmodel_set' )
    interview_details = InterviewerDetailsSerializer(many=True, read_only = True, source = 'interviewerdetails_set')

    class Meta:
        model = JobPostings
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        primary_skills = []
        secondary_skills = []
        for skill in data['skills']:
            if skill.get('is_primary') == True:
                primary_skills.append(skill)
            else:
                secondary_skills.append(skill)
            
        data['primary_skills'] = primary_skills
        data['secondary_skills'] = secondary_skills

        del data['skills']
        return data

class CandidateResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateResume
        fields = '__all__'  



class JobApplicationSerializer(serializers.ModelSerializer):
    # job_id = JobPostingsSerializer()
    # resume = CandidateResumeWithoutContactSerializer()
    
    class Meta:
        model = JobApplication
        fields = '__all__'  

class CandidateSkillSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateSkillSet
        fields = '__all__'

class CandidateResumeWithoutContactSerializer(serializers.ModelSerializer):

    job_application = JobApplicationSerializer( read_only = True)
    skills = CandidateSkillSetSerializer(many=True)

    class Meta: 
        model = CandidateResume
        exclude = ('contact_number','alternate_contact_number','candidate_email')
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        primary_skills = []
        secondary_skills = []
        for skill in data['skills']:
            if (skill.get('is_primary', True)):
                primary_skills.append(skill)
            else:
                secondary_skills.append(skill)

        data['primary_skills'] = primary_skills
        data['secondary_skills'] = secondary_skills

        del data['skills']
        return data


class JobApplicationSerializer(serializers.ModelSerializer):
    job_id = JobPostingsSerializer()
    resume = CandidateResumeSerializer()
    # cand_id=CandidateResumeWithoutContactSerializer()
    sender=CustomUserSerializer()
    attached_to = CustomUserSerializer()
    receiver=CustomUserSerializer()
    class Meta:
        model = JobApplication
        fields = '__all__'  
        
class InterviewScheduleSerializer(serializers.ModelSerializer):
    interviewer = InterviewerDetailsSerializer()
    candidate = serializers.StringRelatedField()
    job_id = serializers.PrimaryKeyRelatedField(queryset=JobPostings.objects.all())
    
    class Meta:
        model = InterviewSchedule
        fields = ['id', 'candidate', 'interviewer', 'job_id', 'round_num', 'status_display','rctr']
    
    

class CandidateEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvaluation
        fields = '__all__'  

class InterviewDetailsEditedSerializer(serializers.ModelSerializer):
    name = CustomUserSerializer(read_only = True)
    class Meta:
        model = InterviewerDetailsEditedVersion
        fields = '__all__'

class SkillMetricsModelEditedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillMetricsModelEdited
        fields = '__all__'

class JobPostEditedSerializer(serializers.ModelSerializer):
    interview_details  = InterviewDetailsEditedSerializer(many=True, read_only=True, source='interviewerdetailseditedversion_set')
    edited_by_username = serializers.SerializerMethodField()
    skills = SkillMetricsModelEditedSerializer(many = True)
    
    class Meta:
        model = JobPostingsEditedVersion
        fields = '__all__'

    def get_edited_by_username(self,obj):
        return obj.edited_by.username if obj.edited_by else None
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        primary_skills = []
        secondary_skills = []
        for skill in data['skills']:
            if (skill.get('is_primary', True)):
                primary_skills.append(skill)
            else:
                secondary_skills.append(skill)

        data['primary_skills'] = primary_skills
        data['secondary_skills'] = secondary_skills

        del data['skills']
        return data
    
    
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
            "years_of_experience",
            "ctc",
            "rounds_of_interview",
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
            "passport_availability",
            "probation_type",
            "time_period",
            "notice_period",
            "notice_time",
            "industry",
            "differently_abled",
            "languages",
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
    rctr = CustomUserSerializer(many=True)
    
    class Meta:
        model = InterviewSchedule # JobPostingsSerializer
        fields = "__all__"

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
    
class SelectedCandidateSerialzier(serializers.ModelSerializer):
    application = JobApplicationSerializer()
    class Meta:
        model = SelectedCandidates
        fields = '__all__'
class AccountantsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accountants
        fields = ['id', 'email', 'username', 'created_at', 'organization'] 



class TagSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name']

    def get_name(self, obj):
        import ast
        try:
            val = ast.literal_eval(obj.name)
            if isinstance(val, list):
                return val[0]  # or return val if you want a list
            return val
        except:
            return obj.name
        
class BlogPostSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    tags = TagSerializer(many=True)  # Add this line to serialize related tags

    class Meta:
        model = BlogPost
        fields = '__all__'
        
class NotificationsSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()

    class Meta:
        model = Notifications
        fields = ['id', 'sender', 'receiver', 'subject', 'message', 'created_at','seen']
        
        
class IncomingApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='resume.candidate_name')
    candidate_email = serializers.EmailField(source='resume.candidate_email')
    date_of_birth = serializers.DateField(source='resume.date_of_birth')
    location_status = serializers.CharField(source= 'job_location.status')

    class Meta:
        model = JobApplication
        fields = ['id', 'candidate_name', 'candidate_email', 'date_of_birth', 'status', 'location_status']


class IncomingApplicationDetailSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='resume.candidate_name')
    candidate_email = serializers.EmailField(source='resume.candidate_email')
    date_of_birth = serializers.DateField(source='resume.date_of_birth')
    experience = serializers.CharField(source='resume.experience', required=False)
    current_ctc = serializers.CharField(source='resume.current_ctc', required=False)
    resume = serializers.FileField(source='resume.resume', required=False)

    class Meta:
        model = JobApplication
        fields = ['id', 'candidate_name', 'candidate_email', 'date_of_birth', 'experience', 'current_ctc', 'resume', 'status']

class JobPostingDraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostingDraftVersion
        fields = '__all__'
        read_only_fields = ['created_at']


class JobLocationsDraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLocationsDraftVersion
        fields = '__all__'


class SkillMetricsDraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillMetricsDraftVersion
        fields = '__all__'

class InterviewerDetailsDraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerDetailsDraftVersion
        fields = '__all__'


class FullJobDraftSerializer(serializers.ModelSerializer):
    locations = JobLocationsDraftVersionSerializer(many=True, required=False)
    skill_metrics = SkillMetricsDraftVersionSerializer(many=True, required=False)
    interviewers = InterviewerDetailsDraftVersionSerializer(many=True, required=False)

    class Meta:
        model = JobPostingDraftVersion
        fields = '__all__'

    def create(self, validated_data):
        locations_data = validated_data.pop('locations', [])
        skills_data = validated_data.pop('skill_metrics', [])
        interviewers_data = validated_data.pop('interviewers', [])

        job_draft = JobPostingDraftVersion.objects.create(**validated_data)

        for loc in locations_data:
            JobLocationsDraftVersion.objects.create(job=job_draft, **loc)

        for skill in skills_data:
            SkillMetricsDraftVersion.objects.create(job=job_draft, **skill)

        for interviewer in interviewers_data:
            InterviewerDetailsDraftVersion.objects.create(job=job_draft, **interviewer)

        return job_draft

    def update(self, instance, validated_data):
        # Optional: write update logic if needed
        return super().update(instance, validated_data)


class BlogImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogImage
        fields = ['id', 'image', 'image_url', 'uploaded_at']