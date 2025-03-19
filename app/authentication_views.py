from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
from .serializers import *
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.conf import settings 
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from datetime import datetime
from collections import Counter
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from .permissions import *


import base64
import jwt
import string 
import random
from django.contrib.auth.tokens import default_token_generator
from django.template import Template, Context
from django.shortcuts import get_object_or_404
from .utils import *

class VerifyEmailView(APIView):
    def get(self, request, uidb64, token):
        try:

            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(CustomUser, pk=uid)

            if email_verification_token.check_token(user, token):
                user.is_verified = True
                user.is_active = True
                user.save()
                return Response({"message": "Email verified successfully! You can now log in."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:    
            email = request.data.get('email')
            try:
                user = CustomUser.objects.get(email = email)
            except CustomUser.DoesNotExist:
                return Response({"error":"User with this email id does not exists"}, status= status.HTTP_400_BAD_REQUEST)
            if user.is_verified:
                return Response({"message":"Your email is already verified, try login"}, status=status.HTTP_200_OK)
            try:
                send_email_verification_link(user,domain="localhost:3000")
                return Response({"message":"Verification Link sent successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                print(str(e))
                return Response({"error":"Error sending verification email"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ClientSignupView(APIView):
    """
    API view to sign up a new client user.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        combined_values = request.data
        print("calling this view ")
        try:
            print("CustomUser.CLIENT table",CustomUser.CLIENT)
            with transaction.atomic():
                user_serializer = CustomUserSerializer(data={
                    'email': combined_values.get('email'),
                    'username': combined_values.get('username'),
                    'role': CustomUser.CLIENT,
                    'credit' : 50,
                    'password': combined_values.get('password')
                })
                print('user_serializer',user_serializer)
                if user_serializer.is_valid(raise_exception=True):
                    user = user_serializer.save()
                    user.set_password(combined_values.get('password'))
                    user.save()
                    
                    
                    client_data = {
                        'username': user.username,
                        'user': user.id,
                        'name_of_organization': combined_values.get('name_of_organization'),
                        'designation': combined_values.get('designation'),
                        'contact_number': combined_values.get('contact_number'),
                        'website_url': combined_values.get('website_url'),
                        'gst_number': combined_values.get('gst'),
                        'company_pan': combined_values.get('company_pan'),
                        'company_address': combined_values.get('company_address')
                    }
                    client_serializer = ClientDetailsSerializer(data=client_data)
                    
                    if client_serializer.is_valid(raise_exception=True):
                        client_serializer.save()
                        # subject = 'Welcome to Our Service!'
                        # message = 'Thank you for signing up with us.'

                        try:
                            send_email_verification_link(user, domain = "localhost:3000")
                        except Exception as e:
                            print(f"Error sending verification link: {str(e)}")

                            return Response(
                                {"error": "There was an issue sending the welcome email. Please try again later."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )

                    return Response({"message": "Verification link send successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AgencySignupView(APIView):
    """
    API view to sign up a new client user.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        combined_values = request.data
        org_code = combined_values.get('org_code')
        if Organization.objects.filter(org_code=org_code).exists():
            return Response({"error": "Organization with the give code already exists"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                user_serializer = CustomUserSerializer(data={
                    'email': combined_values.get('email'),
                    'username': combined_values.get('username'),
                    'role': CustomUser.MANAGER,
                    'credit' : 0,
                    'password': combined_values.get('password')
                })

                if user_serializer.is_valid(raise_exception=True):
                    user = user_serializer.save()
                    user.set_password(combined_values.get('password'))
                    user.save()
                    
                    
                    org_data = {
                        'name': combined_values.get('name'),
                        'org_code': combined_values.get('org_code'),
                        'contact_number': combined_values.get('contact_number'),
                        'website_url': combined_values.get('website_url'),
                        'gst_number': combined_values.get('gst'),
                        'company_pan': combined_values.get('company_pan'),
                        'company_address': combined_values.get('company_address'),
                        'manager': user.id,
                    }
                    org_serializer = OrganizationSerializer(data=org_data)
                    
                    if org_serializer.is_valid(raise_exception=True):
                        org_serializer.save()

                    try:
                        send_email_verification_link(user, domain = "localhost:3000")
                    except Exception as e:
                        print(f"Error sending verification link: {str(e)}")


#                     subject = "Agency Created Successfully on HireSync"
#                     message = f"""
# Dear {user.username},

# Your agency "{org_data['name']}" has been successfully created on HireSync.

# Organization Code: {org_data['org_code']}
# Username: {user.username}
# Email: {user.email}

# Please log in to the platform to explore the features and manage your agency:
# Login Link: https://hiresync.com/lpgin

# If you have any questions or need assistance, feel free to contact support.

# Regards,
# HireSync Team
# """
#                     send_mail(
#                         subject=subject,
#                         message=message,
#                         from_email='',
#                         recipient_list=[user.email],
#                         fail_silently=False,
#                     )


                    return Response({"message": "Verification link successfully sent to your mail"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if email is not None:
            email = email.strip()
        password = request.data.get("password")
        if password is not None:
            password = password.strip()
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if user.is_verified == False:
                return Response({"error":"Your email is not verified yet, please verify your email","not_verified":True},status=status.HTTP_400_BAD_REQUEST)
            
            user_details = {
                "username": user.username,
                "role":user.role,
                "id":user.id,
            }
            
            refresh = RefreshToken.for_user(user)
            # print(refresh)
            access_token = str(refresh.access_token)
            message = f"Successfully signed in. If not done by you please change your password."
            return Response({'access_token': access_token,'role':user.role, "user_details": user_details}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class VerifyTokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token not provided"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded_token = jwt.decode(token, settings.SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM])
            return Response({"valid": True, "decoded_token": decoded_token}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

class TokenRefreshView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        refresh = RefreshToken.for_user(request.user)
        access_token = str(refresh.access_token)
        return Response({'access_token': access_token}, status=status.HTTP_200_OK)


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

class ForgotPasswordAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_password_link = f"http://localhost:3000/reset/{uid}/{token}"

            email_template = """
Hi {{ user.username }},
Please click the link below to reset your password:
{{ reset_password_link }}
"""
            template = Template(email_template)
            context = Context({
                'user': user,
                'reset_password_link': reset_password_link,
            })
            print(reset_password_link)
            message = template.render(context)

            send_mail('Reset your password', message,'', [email])
            return Response({'success': 'Password reset email has been sent.'}, status = status.HTTP_200_OK)

class ResetPasswordAPIView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid token.'}, status=400)
        else:
            if default_token_generator.check_token(user, token):
                return Response({'uidb64': uidb64, 'token': token})
            else:
                return Response({'error': 'Invalid token.'}, status=400)

    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid token.'}, status=400)
        else:
            print(default_token_generator.check_token(user, token))
            if default_token_generator.check_token(user, token):
                new_password = request.data.get('password')
                user.set_password(new_password)
                user.save()
                message = f"Password successfully changed. If not done by you please change your password."
                send_mail(
                    'Password Changed',
                    message,
                    '',
                    [user.email],
                    fail_silently=False,
                )
                return Response({'success': 'Password has been reset successfully.'})
            else:
                return Response({'error': 'Invalid token.'}, status=400)

class changePassword(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')
        confirm_password = request.data.get('confirmPassword')

        if user.check_password(current_password):
            if new_password == confirm_password:
                user.set_password(new_password)
                user.save()
                message = f"Password successfully changed. If not done by you please change your password."
                send_mail(
                    'Password Changed',
                    message,
                    '',
                    [user.email],
                    fail_silently=False,
                )
                return Response({'success': True})
            else:
                return Response({'success': False, 'message': 'New passwords do not match.'})
        else:
            return Response({'success': False, 'message': 'Invalid current password.'})
