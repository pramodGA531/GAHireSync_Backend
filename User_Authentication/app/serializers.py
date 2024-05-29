from rest_framework.serializers import ModelSerializer,Serializer
from .models import CustomUser , JobPostings
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model() 

class LoginSerializer(Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        role = validated_data.get('role', 'admin')  # Default role if not provided
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            role=role,
        )
        user.set_password(validated_data['password'])
        user.save()

        return user
    
# class UsernameAsPK(serializers.PrimaryKeyRelatedField):
#     def to_internal_value(self, data):
#         try:
#             user = CustomUser.objects.get(username=data)
#             return user
#         except CustomUser.DoesNotExist:
#             raise serializers.ValidationError("User with username '{}' does not exist.".format(data))


# class JobPostingSerializer(serializers.ModelSerializer):
#     username = UsernameAsPK(queryset=CustomUser.objects.all())
#     class Meta:
#         model = JobPostings
#         fields = ["username","jobDescription","primary_skills","secondary_skills","years_of_experience","ctc","rounds_of_interview","interviewers","job_location"]
    
#     def create(self, validated_data):
#         return JobPostings.objects.create(**validated_data)
class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPostings
        fields = [
            "job_description", "primary_skills", "secondary_skills",
            "years_of_experience", "ctc", "rounds_of_interview", "interviewers", "job_location"
        ]

    def create(self, validated_data):
        # User will be assigned in the view
        return JobPostings.objects.create(**validated_data)