from rest_framework.serializers import ModelSerializer, Serializer
from .models import CustomUser, JobPostings, TermsAndConditions
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
        fields = ["username", "email", "password", "role"]
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
            "job_description",
            "primary_skills",
            "secondary_skills",
            "years_of_experience",
            "ctc",
            "rounds_of_interview",
            "interviewers",
            "job_location",
        ]

    def create(self, validated_data):
        # User will be assigned in the view
        return JobPostings.objects.create(**validated_data)


class GetAllJobPostsSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = JobPostings
        fields = "__all__"

    def get_username(self, obj):
        return obj.username.username

# class ParticularJobPostSerializer(serializers.ModelSerializer):
#     username = serializers.SerializerMethodField()
#     class Meta:
#         model = JobPostings
#         fields

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

        