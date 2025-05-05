from ..models import *
from ..permissions import *
from ..serializers import *
from ..authentication_views import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.conf import settings 
from django.core.mail import send_mail
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render

from django.shortcuts import get_object_or_404
from ..utils import *



# Complete Candidate Profile

# Candidate basic details
class CandidateProfileView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_profile_serializer = CandidateProfileSerializer(candidate_profile)
                return Response(candidate_profile_serializer.data, status = status.HTTP_200_OK)
            
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def put(self,request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                data = request.data

                skills = data.get('skills')
                
                date_str= data.get('date_of_birth', None)

                formatted_date = date_str
                

                profile = request.FILES.get('profile', None)
                resume = request.FILES.get('resume', None)
                input_data_json = {
                    "profile": profile,
                    "resume": resume,
                    "about" : data.get('about',""),
                    "first_name" : data.get('first_name',""),
                    "middle_name" : data.get('middle_name',''),
                    "last_name" : data.get('last_name',' '),
                    "communication_address" : data.get('communication_address',''),
                    "permanent_address": data.get('permanent_address',''),
                    "phone_num" : data.get('phone_num',''),
                    "date_of_birth": formatted_date,
                    "designation": data.get('designation',''),
                    "linked_in" : data.get('linked_in', None),
                    "instagram": data.get('instagram', None),
                    "facebook":data.get('facebook', None),
                    "blood_group": data.get('blood_group'),
                    "experience_years": data.get('experience_years',""),
                    "skills": skills,
                }
                
                candidate_profile_serializer = CandidateProfileSerializer(instance = candidate_profile, data = input_data_json, partial = True)

                if(candidate_profile_serializer.is_valid()):
                    candidate_profile_serializer.save()
                    return Response({"message":"Candidate Profile updated successfully"}, status = status.HTTP_200_OK)

                else:
                    print(candidate_profile_serializer.errors)
                    return Response({"error":candidate_profile_serializer.errors}, status = status.HTTP_400_BAD_REQUEST)

            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

# Candidate Experiences  Add or View  
class CandidateExperiencesView(APIView):
       
    parser_classes = (MultiPartParser, FormParser)
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateExperiences.objects.filter(candidate = candidate_profile)

                candidate_certificate_serializer = CandidateExperienceSerializer(candidate_certificates,many=True)
                return Response(candidate_certificate_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
            except CandidateCertificates.DoesNotExist:
                return Response({"message":"Candidate Doesnot Added any certificates"}, status= status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)

                experience = request.data
                if experience: 
                    CandidateExperiences.objects.create(
                        candidate = candidate_profile,
                        company_name= experience.get('company_name'),
                        role= experience.get('job_role'),
                        job_type = experience.get('job_type'),
                        from_date = experience.get('from_date'),
                        to_date = experience.get('to_date'),
                        is_working = True if experience.get('working') else False,
                        reason_for_resignation = experience.get('reason_for_resignation'),
                        relieving_letter = experience.get('relieving_letter',''),
                        pay_slip1 = experience.get('pay_slip1',''),
                        pay_slip2 = experience.get('pay_slip2',''),
                        pay_slip3 = experience.get('pay_slip3',''),
                    )

                    return Response({"error":"Candidate Experiences added successfully"}, status = status.HTTP_200_OK)
                
                else:
                    return Response({"error":"You haven't added any experiences"}, status = status.HTTP_400_BAD_REQUEST)
                
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            experience = get_object_or_404(CandidateExperiences, id=id)

            if experience.candidate.name.id == request.user.id:
                experience.delete()
                return Response({"message": "Candidate Experience deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             

# Candidate Ceritificates Add Or View
class CandidateCertificatesView(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateCertificates.objects.filter(candidate = candidate_profile)

                candidate_certificate_serializer = CandidateCertificateSerializer(candidate_certificates,many=True)
                return Response(candidate_certificate_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
            except CandidateCertificates.DoesNotExist:
                return Response({"message":"Candidate Doesnot Added any certificates"}, status= status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
    
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            
            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name=user)
            except CandidateProfile.DoesNotExist:
                return Response({"error": "Candidate profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            data = request.data
            if not data.get('certificate_name') or not data.get('certificate_image'):
                return Response({"error": "Both 'certificate_name' and 'certificate_image' are required"}, status=status.HTTP_400_BAD_REQUEST)

            certificate_name = data.get('certificate_name')
            certificate_image = data.get('certificate_image')

            if not hasattr(certificate_image, 'name') or not certificate_image.content_type.startswith('image/'):
                return Response({"error": "Invalid certificate image"}, status=status.HTTP_400_BAD_REQUEST)

            CandidateCertificates.objects.create(
                candidate=candidate_profile,
                certificate_name=certificate_name,
                certificate_image=certificate_image
            )

            return Response({"message": "Candidate certificate added successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            # Log the error for debugging
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            certificate = get_object_or_404(CandidateCertificates, id=id)

            if certificate.candidate.name.id == request.user.id:
                certificate.delete()
                return Response({"message": "Candidate Certificate deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Candidate Education Details Add or View
class CandidateEducationView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)

            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                candidate_certificates = CandidateEducation.objects.filter(candidate = candidate_profile)

                candidate_education_serializer = CandidateEducationSerializer(candidate_certificates,many=True)
                return Response(candidate_education_serializer.data, status=status.HTTP_200_OK)
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile doesnot exists"}, status=status.HTTP_400_BAD_REQUEST)
        except CandidateCertificates.DoesNotExist:
            return Response({"message":"Candidate Doesnot Added any education details"}, status= status.HTTP_200_OK)
        
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error":"User is not authenticated"}, status= status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error":"You are not allowed to run this"}, status = status.HTTP_400_BAD_REQUEST)



            user = request.user
            try:
                candidate_profile = CandidateProfile.objects.get(name = user)
                education = request.data
                print(education)
                if education:
                    
                        CandidateEducation.objects.create(
                            candidate = candidate_profile,
                            institution_name = education.get('institution_name'),
                            education_proof = education.get('education_proof'),
                            field_of_study = education.get('field_of_study'),
                            start_date = education.get('start_date'),
                            end_date = education.get('end_date'),
                            degree = education.get('degree'),
                            grade = education.get('grade'),
                        )

                        return Response({"error": "Your education details added successfully"}, status = status.HTTP_200_OK)
                
                else:
                    return Response({"error":"You haven't send any education details"}, status = status.HTTP_400_BAD_REQUEST)
                
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Cant find candidate profile"}, status = status.HTTP_400_BAD_REQUEST)   

        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status = status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        try: 
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to perform this action"}, status=status.HTTP_403_FORBIDDEN)

            id = request.GET.get('id')

            try:
                id = int(id)  
            except (TypeError, ValueError):
                return Response({"error": "Invalid ID"}, status=status.HTTP_400_BAD_REQUEST)

            education = get_object_or_404(CandidateEducation, id=id)

            if education.candidate.name.id == request.user.id:
                education.delete()
                return Response({"message": "Candidate Education deleted successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not allowed to delete this experience"}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Candidates List Of Applications
class CandidateApplicationsView(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not request.user.role == 'candidate':
                return Response({"error":"You are not allowed to run this view"}, status = status.HTTP_400_BAD_REQUEST)

            user = CustomUser.objects.get(username = request.user)
            candidate_resume = CandidateResume.objects.filter(candidate_name = user.username, candidate_email = user.email)
            applications= JobApplication.objects.filter(resume__in = candidate_resume)
            applications_serialized = JobApplicationSerializer(applications, many=True)
            return Response({"data":applications_serialized.data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

# Candidate Upcoming Interviews 
class CandidateUpcomingInterviews(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)
            
            if request.user.role != 'candidate':
                return Response({"error": "You are not allowed to run this"}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            
            candidate_profile = CandidateProfile.objects.get(name=user)

            applications = JobApplication.objects.filter(resume__candidate_name=candidate_profile)

            applications_json = []

            for application in applications:
                if application.next_interview is not None:
                    next_interview = application.next_interview
                    try:
                        application_json = {
                            "round_num": application.round_num,
                            "job_id": {
                                "id": application.job_id.id,
                                "job_title": application.job_id.job_title,
                                "company_name": application.job_id.username.username
                            },
                            "interviewer_name": next_interview.interviewer.name.username,
                            "scheduled_date_and_time": InterviewScheduleSerializer(next_interview).data,
                        }
                        applications_json.append(application_json)  
                    except Exception as e:
                        print(str(e))
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(applications_json, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class SelectedJobsCandidate(APIView):
    permission_classes = [IsCandidate]
    def get(self, request):
        try:
            selected_jobs = SelectedCandidates.objects.filter(candidate__name = request.user)
            selected_jobs_list = []
            for selected_job in selected_jobs:
                job = selected_job.application.job_id
                companyDetail=ClientDetails.objects.get(user=job.username)
                details_json = {
                    "job_title": job.job_title,
                    "job_description": job.job_description,# i need company name , agency code other_benefits,name_of_organization
                    "company":companyDetail.name_of_organization,
                    "org_code":job.organization.org_code,
                    "job_ctc": job.ctc,
                    "joining_status":selected_job.joining_status,
                    "agreed_ctc": selected_job.ctc,
                    "other_benfits":selected_job.other_benefits,
                    "joining_date": selected_job.joining_date,
                    "selected_candidate_id": selected_job.id,
                    "candidate_acceptance": selected_job.candidate_acceptance,
                    "recruiter_acceptance": selected_job.recruiter_acceptance,
                }
                selected_jobs_list.append(details_json)

            return Response(selected_jobs_list, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class CandidateAcceptJob(APIView):
    permission_classes = [IsCandidate]
    def get(self, request):
        print("calling the candidate")
        try:
            id = request.GET.get('selected_candidate_id')
            user = request.user
            selected_candidate = SelectedCandidates.objects.get(id= id)
            actual_user = selected_candidate.candidate.name

            if (user != actual_user):
                return Response({"error":"Users are not matching"}, status=status.HTTP_400_BAD_REQUEST)

            selected_candidate.candidate_acceptance = "accepted"
            selected_candidate.save()
            
            customCand =selected_candidate.candidate.name
            application=selected_candidate.application
            
            Notifications.objects.create(
    sender=request.user,
    receiver=application.sender,
    category = Notifications.CategoryChoices.CANDIDATE_ACCEPTED,
    subject=f"Hey, Recruiter Candidate Accepts the offer position {application.job_id.job_title}",
    message=(
        f"Offer Acceptance Notification\n\n"
        f"The candidate {customCand.username} has officially accepted the offer "
        f"for the position of {application.job_id.job_title}.\n\n"
        f"Joining Date: {selected_candidate.joining_date}\n"
        f"Agreed CTC: {selected_candidate.ctc}\n\n"
        f"Please follow up to confirm whether {customCand.username} has joined on the scheduled date.\n\n"
    )
)
            
            Notifications.objects.create(
    sender=request.user,
    receiver=application.job_id.username,
    category = Notifications.CategoryChoices.CANDIDATE_ACCEPTED,
    subject=f"Cand Accepted the offer role {application.job_id.job_title}",
    message=(
        f"Offer Acceptance Notification\n\n "
        f"The candidate {customCand.username} has officially accepted the offer "
        f"for the position of {application.job_id.job_title}.\n\n"
        f"Joining Date: {selected_candidate.joining_date}\n"
        f"Agreed CTC: {selected_candidate.ctc}\n\n"
        f"Kindly confirm on the joining day if the candidate has reported and completed the joining formalities.  \n\n"
    )
)
            
            
            
            return Response({"message":"Accepted and Reconfirmation notification sent to recruiter successfully"}, status = status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)   


class CandidateRejectJob(APIView):
    permission_classes = [IsCandidate]
    def post(self, request):
        try:
            id = request.GET.get('selected_candidate_id')
            user = request.user
            selected_candidate = SelectedCandidates.objects.get(id= id)
            actual_user = selected_candidate.candidate.name

            if (user != actual_user):
                return Response({"error":"Users are not matching"}, status=status.HTTP_400_BAD_REQUEST)
            
            selected_candidate.feedback = request.data.get('feedback')
            selected_candidate.save()

            return Response({"message":"Your feedback send to client successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)   
        
        

class CandidateReConfirmation(APIView):
    # print("CALLING THIS FUNCTION")
    permission_classes = [IsAuthenticated, IsCandidate]  # Ensure authentication

    def get(self, request):
        # print("CALLING THIS function")
        try:
            user = request.user  
            if not user.is_authenticated:
                return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
          
            # Fetch CandidateProfile linked to the user
            candidate_profile = CandidateProfile.objects.get(name=user)

            # Get selected candidates excluding accepted ones
            selected_candidates = SelectedCandidates.objects.filter(
                candidate=candidate_profile
            ).exclude(candidate_acceptance=True)

            if not selected_candidates.exists():
                return Response({
                    "message": "No pending candidate selections found.",
                    "job_details": []
                }, status=status.HTTP_200_OK)

            # Serialize data (returns a list of dictionaries)
            serialized_data = SelectedCandidateSerialzier(selected_candidates, many=True).data  

            # Fetch related job details
            job_details = [
                {
                    "job_title": sc.application.job_id.job_title if sc.application and sc.application.job_id else None,
                    "job_location": sc.application.job_id.job_locations if sc.application and sc.application.job_id else None,
                    "company_name": sc.application.job_id.username.username if sc.application and sc.application.job_id and sc.application.job_id.username else None,
                    "selected_candidate_id": item.get("id"),
                    "selected_candidate_ctc": item.get("ctc"),
                    "selected_candidate_joiningDate": item.get("joining_date"),
                    "status":item.get("candidate_acceptance"),
                }
                for sc, item in zip(selected_candidates, serialized_data)
            ]

            return Response({
                "job_details": job_details
            }, status=status.HTTP_200_OK)
            
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Candidate profile not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CandidateAllAlerts(APIView):
    def get(self, request):
        try:
            all_alerts = Notifications.objects.filter(seen=False, receiver=request.user)
            schedule_interview = 0
            promote_candidate = 0
            reject_candidate = 0
            select_candidate = 0
            accepted_ctc = 0

            for alert in all_alerts:
                if alert.category == Notifications.CategoryChoices.SCHEDULE_INTERVIEW:
                    schedule_interview += 1
                elif alert.category == Notifications.CategoryChoices.PROMOTE_CANDIDATE:
                    promote_candidate += 1
                elif alert.category == Notifications.CategoryChoices.REJECT_CANDIDATE:
                    reject_candidate += 1
                elif alert.category == Notifications.CategoryChoices.SELECT_CANDIDATE:
                    select_candidate += 1
                elif alert.category == Notifications.CategoryChoices.ACCEPTED_CTC:
                    accepted_ctc += 1

            data = {
                "schedule_interview": schedule_interview,
                "promote_candidate": promote_candidate,
                "reject_candidate": reject_candidate,
                "select_candidate": select_candidate,
                "accepted_ctc": accepted_ctc,
                "total_alerts": all_alerts.count()
            }

            return Response({"data":data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
