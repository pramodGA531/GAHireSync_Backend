from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from .permissions import *
from .authentication_views import *
from .models import InvoiceGenerated
from rest_framework import status
from django.shortcuts import get_object_or_404
from .utils import *
from django.core.files.base import ContentFile
from django.http import JsonResponse
from collections import defaultdict
import requests
from django.http import HttpResponseRedirect
import html2text
from django.db.models import Count, Prefetch
from django.db import IntegrityError
from decimal import ROUND_HALF_UP




frontend_url = os.environ['FRONTENDURL']

class GetUserDetails(APIView):
    def get(self,request):
        try:
            user = request.user
            data = {
                'username' : user.username,
                'email' : user.email,
                'role' : user.role,
                "is_verified": user.is_verified,
                "profile":user.profile.url if user.profile else None,
            }
            return Response({'data':data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OrganizationTermsView(APIView):
    
    permission_classes = [IsAuthenticated]  

    def generate_unique_code(self, org_code, count):
        padded_count = str(count).zfill(4)
        return f"{org_code}+{padded_count}"

    def get(self, request):
        try:
            print("entered here")
            user = request.user
            organization = Organization.objects.filter(manager=user).first()

            if not organization:
                return Response({"error":"Organization doesnot found"},status=status.HTTP_400_BAD_REQUEST)
            
            connections = ClientOrganizations.objects.filter(organization = organization)
            print("enterd here")
            all_terms =[]
            for connection in connections:
                connection_terms = ClientOrganizationTerms.objects.filter(client_organization = connection)
                terms_list = []
                for terms in connection_terms:
                    terms_list.append({
                        "ctc_range": terms.ctc_range,
                        "service_fee": terms.service_fee,
                        "invoice_after": terms.invoice_after,
                        "interest_percentage": terms.interest_percentage,
                        "replacement_clause": terms.replacement_clause,
                        "payment_within": terms.payment_within,
                        "is_negotiated": terms.is_negotiated
                    })
                all_terms.append({
                    "client": connection.client.name_of_organization,
                    "client_name": connection.client.user.username,
                    "created_at": connection.created_at,
                    "terms": terms_list
                })

            return Response({"data":all_terms}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"{e}")
    
    def post(self, request):
        try:
            user = request.user
            organization = Organization.objects.filter(manager=user).first()
            if not organization:
                return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
            
            data = request.data
            organization_total_terms = OrganizationTerms.objects.filter(organization = organization).count()

            unique_code = data.get('unique_code')
            print(unique_code, " is the unique code")
            if unique_code == "" or unique_code == None:
                unique_code = self.generate_unique_code(organization.org_code, organization_total_terms)

            new_terms = OrganizationTerms.objects.create(
                organization=organization,
                service_fee=data.get("service_fee"),
                invoice_after=data.get("invoice_after"),
                payment_within=data.get("payment_within"),
                replacement_clause=data.get("replacement_clause"),
                interest_percentage=data.get("interest_percentage"),
                ctc_range=data.get("ctc_range"),
                unique_code= unique_code,
            )

            return Response({"message": "Organization terms added successfully", "id": new_terms.id}, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            if "unique_code" in str(e):
                return Response({"error": "unique_code already exists"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Database error: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 

    def put(self, request):
        try:
            user = request.user
            organization = Organization.objects.filter(manager = user).first()
            data = request.data
            organization_terms = get_object_or_404(OrganizationTerms, organization = organization, id = request.data.get('id'))
            if data.get('description'):
                organization_terms.description = data.get('description' , organization_terms.description)
                organization_terms.save()
                return Response({"message":"Organization description updated successfully"}, status = status.HTTP_200_OK)
            else:
                organization_terms.unique_code = data.get('unique_code', organization_terms.unique_code)
                organization_terms.service_fee = data.get('service_fee', organization_terms.service_fee)
                organization_terms.replacement_clause = data.get('replacement_clause', organization_terms.replacement_clause)
                organization_terms.invoice_after = data.get('invoice_after', organization_terms.invoice_after)
                organization_terms.payment_within = data.get('payment_within', organization_terms.payment_within)
                organization_terms.interest_percentage = data.get('interest_percentage', organization_terms.interest_percentage)
                organization_terms.save()

                return Response({"detail": "Organization terms updated successfully", "id": organization_terms.id}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class NegotiateTermsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == "manager":
            organization = Organization.objects.get(manager=user)
            negotiationrequests = NegotiationRequests.objects.filter(client_organization__organization = organization, status = 'pending')

        elif user.role == "client":
            client = ClientDetails.objects.get(user=user)
            negotiationrequests = NegotiationRequests.objects.filter(client_organization__client=client)
        else:
            return Response({"detail": "You are not authorized to access this page"}, status=status.HTTP_401_UNAUTHORIZED)
        
        
        serializer = NegotiationSerializer(negotiationrequests, many=True)
        return Response(serializer.data)
    

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.role != "client":
            return Response({"detail": "Only clients can create negotiation requests"}, status=status.HTTP_403_FORBIDDEN)
        
        connection_id = request.GET.get('connection_id')
        connection = ClientOrganizations.objects.get(id = connection_id)
        organization = connection.organization

        if not connection:
            return Response({"detail": "Invalid connection id"}, status=status.HTTP_400_BAD_REQUEST)

        try: 
            prev_negotiations = NegotiationRequests.objects.get(client_organization = connection)
            
            prev_negotiations.delete()
        except NegotiationRequests.DoesNotExist:
            pass


        raw_interest = request.data.get('interest_percentage')
        raw_service = request.data.get('service_fee')
 
        try:
            if raw_interest is not None:
                interest_percentage = Decimal(str(raw_interest)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP  
                )
                service_percentage = Decimal(str(raw_service)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                service_percentage = Decimal("0.00")
                interest_percentage = Decimal("0.00")
        except (InvalidOperation, TypeError):
            
            service_percentage = Decimal("0.00")
            interest_percentage = Decimal("0.00")


        print(interest_percentage, " ",service_percentage,  " is the interest percentage")
        # model_instance.interest_percentage = interest_percentage
        # model_instance.save()
        # interest_percentage = data.get('interest_percentage')

        try:
            data = request.data
            negotiation_request = NegotiationRequests.objects.create(
                client_organization = connection,
                ctc_range= data.get('ctc_range'),
                service_fee_type = data.get('service_fee_type'),
                service_fee=service_percentage,
                replacement_clause=data.get('replacement_clause'),
                invoice_after=data.get('invoice_after'),
                payment_within=data.get('payment_within'),
                interest_percentage=interest_percentage
            )
            negotiation_link = f"{frontend_url}/agency/negotiations/{negotiation_request.id}"
            manager_email_message = f"""

Dear {organization.manager.username},

A terms and conditions negotiation request has been submitted. Please review and take the necessary action.
🔗 {negotiation_link}

Best,
HireSync Team

"""
            send_custom_mail(subject="Job Post Terms & Conditions – Action Needed",body = manager_email_message, to_email=[organization.manager.email])
            
            Notifications.objects.create(
                        sender=request.user,
                        category = Notifications.CategoryChoices.NEGOTIATE_TERMS,
                        receiver=organization.manager,
                        subject="Negotiation Request",
                        message="You have received a new negotiation request.",
            )
            
            return Response({"detail": "Negotiation request created successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        data = request.data
        user = request.user

        if user.role != "manager":
            return Response({"detail": "Only managers can update negotiation requests"}, status=status.HTTP_403_FORBIDDEN)

        try:
            negotiation_request = NegotiationRequests.objects.get(id=data.get('id'))

            
            if data.get('status') == "accepted":
                negotiation_request.status = "accepted"
                negotiation_request.expiry_date = datetime.today().date() + timedelta(days=365)
                negotiation_request.save()

                
                # ClientOrganizationTerms.objects.create(
                #     client_organization = negotiation_request.client_organization,
                #     service_fee=negotiation_request.service_fee,
                #     replacement_clause=negotiation_request.replacement_clause,
                #     invoice_after=negotiation_request.invoice_after,
                #     payment_within=negotiation_request.payment_within,
                #     interest_percentage=negotiation_request.interest_percentage,
                #     is_negotiated = True
                # )

                link = f"{frontend_url}/client/postjob"    
                client_email_message = f"""
            
Dear {negotiation_request.client_organization.client.user.username},

Your terms negotiation request has been accepted. You can proceed with the next steps.
🔗 {link}
For any concerns, contact us at support@hiresync.com.

Best,
HireSync Team

                """

                send_custom_mail(subject="Job Terms & Conditions – Update",body=client_email_message, to_email=[negotiation_request.client_organization.client.user.email])
              
                
            elif data.get('status') == "rejected":
                negotiation_request.status = "rejected"
                reject_reason = data.get('reason')
                negotiation_request.reason = reject_reason
                negotiation_request.save()
                
                client_email_message = f"""
Dear {negotiation_request.client_organization.client.user.first_name},

Your terms negotiation request has been rejected. You can proceed with the next steps.

For any concerns, contact us at support@hiresync.com.

Best,
HireSync Team

"""
                send_custom_mail( subject="Job Terms & Conditions – Update",body=client_email_message,to_email=[negotiation_request.client_organization.client.user.email])
                
                #  accept notification  here i need to send the notification to the agency to the client find the emails of the client and the agency 
                

            else:
                return Response({"detail": "Invalid status provided. Please use 'accepted' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Negotiation request updated successfully"}, status=status.HTTP_200_OK)

        except NegotiationRequests.DoesNotExist:
            return Response({"detail": "Negotiation request not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class JobDetailsAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            job_id = request.GET.get('job_id')
            job_posting = JobPostings.objects.get(id=job_id)
            serializer = JobPostingsSerializer(job_posting)
            data = serializer.data
            client = ClientDetails.objects.get(user = job_posting.username)
            assigned_recruiters = AssignedJobs.objects.filter(job_location__job_id=job_id).prefetch_related('assigned_to', 'job_location')
            
            assigned_recruiters_map = {}
            data["client_website"] = client.website_url

            for assignment in assigned_recruiters:
                location_id = str(assignment.job_location.id)
                recruiter_ids = list(assignment.assigned_to.values_list('id', flat=True))

                if location_id in assigned_recruiters_map:
                    assigned_recruiters_map[location_id] = list(
                        set(assigned_recruiters_map[location_id] + recruiter_ids)
                    )
                else:
                    assigned_recruiters_map[location_id] = recruiter_ids    

            return Response({
                "job": data,
                "assigned_recruiters": assigned_recruiters_map
            }, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        

class CandidateJobDetailsAPIView(APIView):
    permission_classes = [IsCandidate]
    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            job_posting = JobPostings.objects.get(id=job_id)
            serializer = CandidateJobpostSerializer(job_posting)

            # assigned_recruiters = AssignedJobs.objects.filter(job_location__job_id=job_id).prefetch_related('assigned_to', 'job_location')
            
            # assigned_recruiters_map = {}

            # for assignment in assigned_recruiters:
            #     location_id = str(assignment.job_location.id)
            #     recruiter_ids = list(assignment.assigned_to.values_list('id', flat=True))

            #     if location_id in assigned_recruiters_map:
            #         assigned_recruiters_map[location_id] = list(
            #             set(assigned_recruiters_map[location_id] + recruiter_ids)
            #         )
            #     else:
            #         assigned_recruiters_map[location_id] = recruiter_ids    

            return Response({
                "job": serializer.data,
            }, status=status.HTTP_200_OK)

        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

        
class RecJobPostings(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs): 
        try:
            user = request.user if request.user.is_authenticated else None
            recruiter_id = request.GET.get("rctr_id")

            if not user and not recruiter_id:
                return Response({"detail": "User or recruiter ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            if recruiter_id:
                org = Organization.objects.filter(recruiters__id=recruiter_id).first()
                assigned_user = CustomUser.objects.filter(id=recruiter_id).first()
            else:
                org = Organization.objects.filter(recruiters__id=user.id).first()
                assigned_user = user


            if not org:
                return Response({"detail": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

            job_postings = JobPostings.objects.filter(organization=org, assigned_to=assigned_user)
            serializer = JobPostingsSerializer(job_postings, many=True)
          

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class GetResumeByApplicationId(APIView):

    def get(self, request, application_id, *args, **kwargs):
        try:
            job_application = JobApplication.objects.get(id=application_id)

            candidate_resume = job_application.resume

            resume_data = CandidateResumeWithoutContactSerializer(candidate_resume).data

            return Response(resume_data, status=status.HTTP_200_OK)

        except JobApplication.DoesNotExist:
            return Response({"detail": "Job application not found."}, status=status.HTTP_404_NOT_FOUND)


# Agency and Recruiter can see this candidate Profile
class ViewCandidateProfileAPI(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)

            candidate_id = request.GET.get('id')
            if not candidate_id:
                return Response({"error": "Candidate ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                candidate_profile = CandidateProfile.objects.get(id=candidate_id)
            except CandidateProfile.DoesNotExist:
                return Response({"error": "Candidate profile not found"}, status=status.HTTP_404_NOT_FOUND)

            education = CandidateEducation.objects.filter(candidate=candidate_profile)
            experience = CandidateExperiences.objects.filter(candidate=candidate_profile)

            experience_data = CandidateExperienceSerializer(experience, many=True)
            education_data = CandidateEducationSerializer(education, many=True)

            candidate_documents = CandidateDocuments.objects.filter(candidate=candidate_profile)
            
            salary_string = f"{candidate_profile.expected_salary} Expected / {candidate_profile.current_salary} Current"
            profile_percentage = calculate_profile_percentage(candidate_profile)

            if not  candidate_profile.skills == "": 

                candidate_data = {
                    "candidate_name": candidate_profile.name.username,
                    "skills": candidate_profile.skills if candidate_profile.skills else "",
                    "education": education_data.data,
                    "experience": experience_data.data,
                    "salary": salary_string,
                    "extra_info": candidate_profile.joining_details,
                    "candidate_phone": candidate_profile.phone_num,
                    "candidate_email": candidate_profile.email,
                    "candidate_location": candidate_profile.permanent_address,
                    "candidate_documents": list(candidate_documents.values()),
                    "profile_percentage": profile_percentage,
                }

            else : 
                candidate_data = None

            user = candidate_profile.name
            applied_jobs_list = []

            all_job_applications = JobApplication.objects.filter(resume__candidate_name=user)
            for job in all_job_applications:
                try:
                    job_id = job.job_id.id
                    title = JobPostings.objects.get(id=job_id).job_title
                    applied_jobs_list.append({"job_id": job_id, "title": title})
                except JobPostings.DoesNotExist:
                    continue  

            all_feedbacks = []
            candidate_evaluations = CandidateEvaluation.objects.filter(job_application__in=all_job_applications)
            for feedback in candidate_evaluations:
                if feedback.remarks:
                    try:
                        interviewer_name = feedback.interview_schedule.interviewer.name.username
                    except AttributeError:
                        interviewer_name = "Unknown"
                    all_feedbacks.append({
                        "interviewer_name": interviewer_name,
                        "feedback": feedback.remarks
                    })

            return Response({
                "feedback": all_feedbacks,
                "applied_jobs": applied_jobs_list,
                "candidate_data": candidate_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CandidateStatusForJobView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        job_id = request.GET.get("job_id")
        candidate_id = request.GET.get("candidate_id")

        if not job_id or not candidate_id:
            return Response({"error": "Job ID and Candidate ID are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job_details = get_object_or_404(JobPostings, id=job_id)
            candidate = get_object_or_404(CandidateProfile, id=candidate_id)

            is_new_position = not JobPostings.objects.filter(job_title=job_details.job_title, organization__manager=request.user).exclude(id=job_id).exists()

            candidate_skills = set(candidate.skills.split(",")) if candidate.skills else set()
            job_skills = set(job_details.primary_skills.split(",") + job_details.secondary_skills.split(","))
            
            matched_skills = list(candidate_skills & job_skills)
            unmatched_skills = list(job_skills - candidate_skills)

            job_application = JobApplication.objects.filter(resume__candidate_name=candidate.name, job_id=job_id).first()
            if not job_application:
                return Response({"error": "Candidate has not applied for this job"}, status=status.HTTP_404_NOT_FOUND)
            
            num_of_rounds =InterviewerDetails.objects.filter(id = job_id).count()
            total_rounds = [
                'Shortlisted',
            ]
            for i in range(1,num_of_rounds+1):
                total_rounds.append(f"Round-{i}")
            total_rounds.append("Rejected")
            total_rounds.append("Selected")

            if job_application.status == "rejected":
                selected_round = "Rejected"
            else:
                selected_round = f"Round-{job_application.round_num}" if job_application.round_num else "Not Assigned"

            next_interview = getattr(job_application, 'next_interview', None)
            interview_data = {
                "next_round_time": next_interview.schedule_date if next_interview else None,
                "interviewer": next_interview.interviewer.name.username if next_interview else None,
                "meet_link": next_interview.meet_link if next_interview else None,
                "interview_type": next_interview.interviewer.type_of_interview if next_interview else None,
                "interview_mode": next_interview.interviewer.mode_of_interview if next_interview else None,
            }

            response_data = {
                "current_stage": job_application.status,
                "recruiter_name": job_application.attached_to.username if job_application.attached_to else None,
                "num_of_rounds": InterviewerDetails.objects.filter(job_id=job_details).count(),
                "matched_skills": matched_skills,
                "unmatched_skills": unmatched_skills,
                "new_position": is_new_position,
                "job_experience": job_details.years_of_experience,
                "job_graduation": job_details.qualifications,
                "num_of_positions": job_details.num_of_positions,
                "created_by": job_details.username.username,
                "created_at": job_details.created_at,
                "all_rounds" : total_rounds,
                "selected_round": selected_round,
                **interview_data,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotificationToUpdateProfileView(APIView):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            
            candidate_id = request.GET.get('id')

            if not candidate_id:
                return Response({"error":"Candidate Id is not sent"}, status= status.HTTP_400_BAD_REQUEST)

            try:
                candidate_email =  CandidateProfile.objects.get(id = candidate_id).email
            except CandidateProfile.DoesNotExist:
                return Response({"error":"Candidate Profile Does Not Exists"}, status=status.HTTP_400_BAD_REQUEST)
            message = """
Your Profile is not updated yet!
Please update the profile
Interviewers are waiting to check your profile
"""

            subject = "Update your profile - HireSync!"
            try:
                send_custom_mail(subject=subject, body=message, to_email=[candidate_email])

                return Response({"message":"Notification Sent Successfully"}, status=status.HTTP_200_OK)
            
            except Exception as e:
                print(str(e))
                return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(str(e))
            return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class Invoices(APIView):
    def get(self, request):
        try:
            invoices = []
            html_list = []

            if request.user.role == "client":
                invoices = InvoiceGenerated.objects.filter(client__user=request.user, 
                                                        #    scheduled_date__lt = timezone.now()
                                                           )
                for invoice in invoices:
                    invoice.invoice_status = 'sent'
                    invoice.save()
                    context = create_invoice_context(invoice.id)
                    html = generate_invoice(context)
                    html_list.append({"invoice": invoice, "html": html})

                invoice_data = [{"invoice_code": invoice.invoice_code, "payment_status": invoice.payment_status,"scheduled_at": invoice.scheduled_date, "org_email":invoice.organization.manager.email, "html": html["html"],"payment_verification":invoice.payment_verification} 
                                for invoice, html in zip(invoices, html_list)]
                return Response({"invoices": invoice_data}, status=status.HTTP_200_OK)

            elif request.user.role == "manager":
                invoices = InvoiceGenerated.objects.filter(organization__manager__email=request.user.email)
                for invoice in invoices:
                    context = create_invoice_context(invoice.id)
                    html = generate_invoice(context)
                    html_list.append({"invoice": invoice, "html": html})
                accountants = Accountants.objects.filter(organization__manager=request.user)
                if not accountants.exists():
                    return Response({"message": "No accountants found for this organization"}, status=status.HTTP_404_NOT_FOUND)
                serializer = AccountantsSerializer(accountants, many=True)

                if invoices:
                    invoice_data = [{"invoice_code": invoice.invoice_code,"scheduled_date":invoice.scheduled_date.date(), "invoice_status":invoice.invoice_status,"payment_status": invoice.payment_status, "client_email": invoice.client.user.email,"org_email":invoice.organization.manager.email, "html": html["html"],"payment_verification":invoice.payment_verification} 
                                for invoice, html in zip(invoices, html_list)]
                else:
                    invoice_data = []
                    
                return Response({"invoices": invoice_data, "accountants": serializer.data}, status=status.HTTP_200_OK)


            elif request.user.role == "accountant":
                accountant=Accountants.objects.get(user=request.user)
                if accountant:
                    invoices = InvoiceGenerated.objects.filter(organization=accountant.organization)
                    for invoice in invoices:
                        context = create_invoice_context(invoice)
                        html = generate_invoice(context)
                        html_list.append({"invoice": invoice, "html": html})

            else:
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

            if invoices:
                invoice_data = [{"invoice_code": invoice.invoice_code, "payment_status": invoice.payment_status,"scheduled_at": invoice.scheduled_date, "org_email":invoice.organization.manager.email, "html": html["html"],"payment_verification":invoice.payment_verification} 
                                for invoice, html in zip(invoices, html_list)]
                return Response({"invoices": invoice_data}, status=status.HTTP_200_OK)

            return Response({"error": "No invoices found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"{e}")
    
    def put(self, request):
        invoice_id = request.data.get('invoice_id')
    
        if not invoice_id:
            return Response({"error": "invoice_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            invoice = InvoiceGenerated.objects.get(id=invoice_id)
        except InvoiceGenerated.DoesNotExist:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
    
        if request.user.role == "client":
            payment_transaction_id = request.data.get('payment_transaction_id')
            payment_method = request.data.get('payment_method')
    
            if not payment_transaction_id or not payment_method:
                return Response({"error": "Both payment_transaction_id and payment_method are required."},
                                status=status.HTTP_400_BAD_REQUEST)
    
            invoice.status = "Paid"
            invoice.payment_transaction_id = payment_transaction_id
            invoice.payment_method = payment_method
            invoice.save()
            return Response({"message": "Invoice marked as paid by client."}, status=status.HTTP_200_OK)
    
        elif request.user.role == "accountant":
            # Accountant verifies payment
            payment_verification = request.data.get('payment_verification')
            if payment_verification is None:
                return Response({"error": "payment_verification field is required."},
                                status=status.HTTP_400_BAD_REQUEST)
    
            invoice.payment_verification = payment_verification
            invoice.save()
            return Response({"message": "Invoice payment verified by accountant."}, status=status.HTTP_200_OK)
    
        else:
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
        
class BasicApplicationDetails(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, application_id):
        try:
            try:
                application = JobApplication.objects.get(id=application_id)
            except JobApplication.DoesNotExist:
                return Response({"error": "Job Application not found"}, status=status.HTTP_404_NOT_FOUND)

            resume_details = application.resume
            if not resume_details:
                return Response({"error": "No resume details associated with this application"}, status=status.HTTP_404_NOT_FOUND)

            application_json = {
                "candidate_name": resume_details.candidate_name,
                "expected_ctc": resume_details.expected_ctc,
                "current_ctc": resume_details.current_ctc,
                "experience": resume_details.experience,
                "job_status": resume_details.job_status,
                "job_type": resume_details.current_job_type,
                "notice_period": resume_details.notice_period,
                "resume": resume_details.resume.url if resume_details.resume else None,
                "application_id": application.id,
            }

            return Response(application_json, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AddProfileView(APIView):
    def post(self, request):
        try:
            user = request.user
            profile_image = request.FILES.get("profile")

            if not profile_image:
                return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)


            if not profile_image.name.endswith(('.png', '.jpg', '.jpeg')):
                return Response({"error": "Invalid file format. Use JPG or PNG."}, status=status.HTTP_400_BAD_REQUEST)

            user.profile.save(profile_image.name, ContentFile(profile_image.read()))
            user.save()

            return Response({"message": "Profile picture updated successfully!", "profile": user.profile.url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class RaiseTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            ticket_id = request.GET.get('ticket_id')

            if ticket_id:
                try:
                    ticket = Tickets.objects.get(id=ticket_id)
                    replies = Messages.objects.filter(ticket_id = ticket.id)
                    replies_list = []
                    for reply in replies:
                        replies_list.append(
                            
                            {
                                "is_raised_by":reply.is_user_raised_by,
                                "name": reply.ticket_id.raised_by.username if reply.is_user_raised_by else reply.ticket_id.assigned_to.username,
                                "message": reply.message,
                                "attachment": reply.attachment.url if reply.attachment else None,
                                "attachment_name": reply.attachment.name if reply.attachment else None,
                                "created_at": reply.created_at,
                            }
                        )

                    return Response({
                        "id":ticket.id,
                        "category": ticket.category,
                        "raised_by": ticket.raised_by.username,
                        "description": ticket.description,
                        "assigned_to": ticket.assigned_to.username if ticket.assigned_to else None,
                        "status": ticket.status,
                        "replies_list": replies_list,
                        "created_at": ticket.created_at,
                        "attachments": ticket.attachments.url if ticket.attachments else None,
                        "attachment_name": ticket.attachments.name if ticket.attachments else None,
                    }, status=status.HTTP_200_OK)
                except Tickets.DoesNotExist:
                    return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)


            is_sent = request.GET.get('isSent')
            if is_sent == "true":
                all_tickets = Tickets.objects.filter(raised_by=user)
            else:
                all_tickets = Tickets.objects.filter(assigned_to=user)
            ticket_list = []


            for ticket in all_tickets:
                ticket_list.append({
                    "id": ticket.id,
                    "raised_by": ticket.raised_by.username,
                    "category": ticket.category,
                    "description": ticket.description,
                    "assigned_to": ticket.assigned_to.username if ticket.assigned_to else None,
                    "status": ticket.status,
                    "created_at": ticket.created_at,
                })

            return Response(ticket_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        try:

            user = request.user
            data = request.POST
            attachment = request.FILES.get('attachment')

            new_ticket = Tickets.objects.create(
                raised_by = user,
                category = data.get('category'),
                description = data.get('description'),
                status = 'pending',
                priority = 'medium',
                assigned_to = CustomUser.objects.get(role='admin')                
            )

            if attachment:
                new_ticket.attachments = attachment
                new_ticket.save()

            return Response({"message":"Ticket Raised successfully"}, status=status.HTTP_200_OK)
        

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class UpdateStatus(APIView):
    def put(self, request):
        try:
            ticket_id = request.GET.get('ticket_id')
            if not ticket_id:
                return Response({"error":"Ticket ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            ticket = Tickets.objects.get(id = ticket_id)
            ticket.status = "completed"
            ticket.save()
            return Response({"message":"Ticket status updated successfully"}, status = status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HandleReplies(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            user = request.user
            ticket_id = request.GET.get('ticket_id')
            data = request.data

            ticket = Tickets.objects.get(id = ticket_id)

            reply = Messages.objects.create(
                ticket_id = ticket,
                message = data.get('message',''),
                is_user_raised_by  = True if ticket.raised_by == user else False,
                attachment = data.get('attachment','')

            )

            return Response({"message":"Response saved successfully"}, status = status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class HandleTicketView(APIView):
    def get(self, request):
        try:
            user = request.user
            ticket_id = request.GET.get('ticket_id')

            if ticket_id:
                try:
                    ticket = Tickets.objects.get(id=ticket_id, assigned_to=user)
                    return Response({
                        "id":ticket.id,
                        "category": ticket.category,
                        "description": ticket.description,
                        "raised_by": ticket.raised_by.username,
                        "status": ticket.status,
                        "created_at": ticket.created_at,
                        "updated_at": ticket.updated_at,
                        "resolved_at" : ticket.resolved_at,
                        "attachments": ticket.attachments.url if ticket.attachments else None,
                        "attachment_name": ticket.attachments.name if ticket.attachments else None,
                    }, status=status.HTTP_200_OK)
                except Tickets.DoesNotExist:
                    return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)


            all_tickets = Tickets.objects.filter(assigned_to=user)
            ticket_list = []

            for ticket in all_tickets:
                ticket_list.append({
                    "id": ticket.id,
                    "category": ticket.category,
                    "description": ticket.description,
                    "raised_by": ticket.raised_by.username,
                    "status": ticket.status,
                    "created_at": ticket.created_at,
                    "attachments": ticket.attachments.url if ticket.attachments else None,
                    "attachment_name": ticket.attachments.name if ticket.attachments else None,
                })

            return Response(ticket_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
    def post(self, request):
        try:
            ticket_id = request.GET.get('ticket_id')
            if not ticket_id:
                return Response({"error": "Ticket ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                ticket = Tickets.objects.get(id=ticket_id)
            except Tickets.DoesNotExist:
                return Response({"error": "Ticket does not exist"}, status=status.HTTP_404_NOT_FOUND)

            data = request.data
            ticket.status = data.get('status', ticket.status) 
            ticket.save()
            return Response({"message": "Reply sent successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class BlogPostView(APIView):
    def get(self, request):
        blog_id = request.GET.get('blog_id')

        if blog_id:
            try:
                blog_post = BlogPost.objects.get(id=blog_id)
                serializer = BlogPostSerializer(blog_post)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except BlogPost.DoesNotExist:
                return Response({'detail': 'Blog not found'}, status=status.HTTP_404_NOT_FOUND)

        # If no blog_id, return all approved blogs with tags
        blog_posts = BlogPost.objects.filter(is_approved=True).order_by('-created_at')
        serializer = BlogPostSerializer(blog_posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def post(self, request):
        user = request.user
        is_approved = user.role == 'admin'
        title = request.data.get('title')
        author = request.data.get('author')
        content = request.data.get('content')
        thumbnail = request.data.get('thumbnail')
        
        # Handle tags input safely
        raw_tags = request.data.get('tags', [])
        
        tag_list = []
        if isinstance(raw_tags, str):
            try:
                # If it's a stringified list like '["consulting", "agency"]'
                import ast
                parsed_tags = ast.literal_eval(raw_tags)
                if isinstance(parsed_tags, list):
                    tag_list = [tag.strip().lower() for tag in parsed_tags]
                else:
                    # Fallback: comma-separated
                    tag_list = [tag.strip().lower() for tag in raw_tags.split(',') if tag.strip()]
            except:
                # If not a list, fallback to comma-separated
                tag_list = [tag.strip().lower() for tag in raw_tags.split(',') if tag.strip()]
        elif isinstance(raw_tags, list):
            tag_list = [tag.strip().lower() for tag in raw_tags]
    
        # Create the blog post
        blog_post = BlogPost.objects.create(
            user=user,
            title=title,
            author=author,
            content=content,
            thumbnail=thumbnail,
            is_approved=is_approved
        )
    
        # Create or get tags and assign to blog post
        for tag_name in tag_list:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            blog_post.tags.add(tag)
    
        return Response({'message': 'Blog post created successfully'}, status=status.HTTP_201_CREATED)

class AdminGetBlogs(APIView):
    def get(self, request):
        try:
            user = request.user
            if not user.role == 'admin':
                return Response({"error":"Your are not allowed to run this view"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not request.GET.get('blog_id'):
                all_blogs = BlogPost.objects.all()
                serialized_data = BlogPostSerializer(all_blogs, many = True)

                return Response(serialized_data.data, status=status.HTTP_200_OK)

            else:
                blog_id = request.GET.get('blog_id')
                blog = BlogPost.objects.get(id = blog_id)
                serialized_data = BlogPostSerializer(blog)

                return Response(serialized_data.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class MyBlogs(APIView):
    def get(self, request):
        try:
            user = request.user
            if request.GET.get('blog_id'):
                blog = BlogPost.objects.get(id = request.GET.get('blog_id'))
                blog_data = BlogPostSerializer(blog)
                return Response(blog_data.data, status=status.HTTP_200_OK)
                
            all_blogs = BlogPost.objects.filter(user = user) 
            all_blogs_data = BlogPostSerializer(all_blogs, many=True)
            return Response(all_blogs_data.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ApproveBlogPost(APIView):
    def get(self, request):
        try:
            if not request.user.role == 'admin':
                return Response({"error":"You are not allowed to run this view"}, status =status.HTTP_400_BAD_REQUEST)
            
            if request.GET.get('blog_id'):
                blog = BlogPost.objects.get(id = request.GET.get('blog_id'))
                blog_data = BlogPostSerializer(blog)
                return Response(blog_data.data, status=status.HTTP_200_OK)
            
            blogs = BlogPost.objects.filter(is_approved = False)
            blog_data = BlogPostSerializer(blogs, many=True)
            return Response(blog_data.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            user = request.user
            if not user.role == 'admin':
                return Response({"error":"Your are not allowed to run this view"}, status=status.HTTP_400_BAD_REQUEST)
            
            blog_id = request.GET.get('blog_id')

            try:
                blog = BlogPost.objects.get(id = blog_id)
    
            except BlogPost.DoesNotExist:
                return Response({"error":"Cant process the request, blog post not available"},status=status.HTTP_400_BAD_REQUEST)

            blog.is_approved = True
            blog.save()
            return Response({"message":"Blog post approved successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class GetJobPostTerms(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        try:
            client = request.user

            # Fetch all jobs created by this client
            jobs = JobPostings.objects.filter(username=client)

            job_terms_list = []

            for job in jobs:
                try:
                    # Get the single term for each job
                    job_post_terms = JobPostTerms.objects.filter(job_id=job)
                    job_terms_list.append({
                        'job_id':job.id,
                        'status':job.status,
                        'organization':job.organization.name,
                        'job_title': job.job_title,
                        'term_id': term.id,
                        'term_description': term.description,
                        'service_fee': term.service_fee,
                        'invoice_after': term.invoice_after,
                        'payment_within': term.payment_within,
                        'interest_percentage': term.interest_percentage,
                        'created_at': term.created_at,
                    } for term in job_post_terms)

                except JobPostTerms.DoesNotExist:
                    # Skip if a job doesn't have associated terms
                    continue

            return Response({'data': job_terms_list}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class GetNotifications(APIView):
    def get(self, request):
        try:
            count_param = request.query_params.get('count', None)

            # If count is requested, filter for unseen notifications and return the count
            if count_param is not None:
                unseen_notifications_count = Notifications.objects.filter(receiver=request.user, seen=False).count()
                return Response({'count': unseen_notifications_count}, status=status.HTTP_200_OK)

            # Otherwise, return all notifications for the user
            notifications = Notifications.objects.filter(receiver=request.user)
            serializer = NotificationsSerializer(notifications, many=True)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def put(self, request):
        try:
            notification_ids = request.data.get('notification_ids', [])

            notifications = Notifications.objects.filter(
                id__in=notification_ids,
                receiver=request.user
            )

            if notifications.exists():
                notifications.update(seen=True)
                return Response({'data': "Successfully updated"}, status=status.HTTP_200_OK)
            else:
                return Response({'data': "No matching notifications found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class AllApplicationsForJob(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            job_id = request.GET.get('job_id')
            recruiter_id = request.GET.get('recruiter_id')
            job = JobPostings.objects.get(id=job_id)

            if recruiter_id:
                recruiter = CustomUser.objects.get(id = recruiter_id)
                applications = JobApplication.objects.filter(job_location__job_id=job.id, attached_to = recruiter)
            else:
                applications = JobApplication.objects.filter(job_location__job_id=job.id)

            applications_list = []
            for application in applications:
                applications_list.append({
                    "candidate_name": application.resume.candidate_name,
                    "application_id": application.id,
                    "last_updated": application.updated_at,
                    "status": application.status,
                    "round_num": application.round_num,
                    "location": application.job_location.location,
                })

            locations_instance = JobLocationsModel.objects.filter( job_id = job)
            locations = list(locations_instance.values_list('location', flat=True))

            num_of_positions = 0
            for location in locations_instance:
                num_of_positions+= location.positions

            job_details = {
                "job_title": job.job_title,
                "job_type": job.job_type,
                "deadline": job.job_close_duration,
                "client_name": job.username.username,
                "locations": locations,
                "num_of_positions": num_of_positions,
            }

            pending_list = []
            selected_list = []
            rejected_list = []
            hold_list = []
            round_wise_processing = {}

            total_rounds = job.rounds_of_interview or 0
            for i in range(1, total_rounds + 1):
                round_key = f"round_{i}"
                round_wise_processing[round_key] = []

            for application in applications_list:
                status_val = application["status"]
                round_num = application["round_num"]

                if status_val == 'pending':
                    pending_list.append(application)
                elif status_val == 'selected':
                    selected_list.append(application)
                elif status_val == 'rejected':
                    rejected_list.append(application)
                elif status_val == 'hold':
                    hold_list.append(application)
                elif status_val == 'processing':
                    round_key = f"round_{round_num}"
                    if round_key not in round_wise_processing:
                        round_wise_processing[round_key] = []
                    round_wise_processing[round_key].append(application)

            response_data = {
                "job_details": job_details,
                "pending": pending_list,
                "selected": selected_list,
                "rejected": rejected_list,
                "processing": round_wise_processing,
                "hold": hold_list,
                "locations":locations,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def check_notifications(request):
    try:
        count = Notifications.objects.count()
        return JsonResponse({'status': 'ok', 'count': count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
        
class ChangePassword(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request,):
            user = request.user
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            confirm_password = request.data.get('confirm_password')
            if old_password and new_password and confirm_password:
                if new_password != confirm_password:
                    return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
                if user.check_password(old_password):
                    user.set_password(new_password)
                    user.save()
                    return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
               
            else:
                return Response({"error": " Old password,New password and confirm password are required"}, status=status.HTTP_400)
                                    
class NotificationStatusChange(APIView):
    def put(self, request):
        try:
            user = request.user
            category = request.data.get('category')
            
            if(type(category) == list):
                notifications = Notifications.objects.filter(receiver = user, seen = False, category__in = category)
            else:
                notifications = Notifications.objects.filter(receiver = user,seen = False, category = category)

            for notification in notifications:
                notification.seen = True
                notification.save()
            return Response({"message":"Status updated successfully"}, status = status.HTTP_200_OK)
        
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class CompleteApplicationDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self , request):
        try:

            application_id = request.GET.get('application_id')
            application = JobApplication.objects.get(id = application_id)

            candidate_evaluations = CandidateEvaluation.objects.filter(job_application  = application)
            candidate_evaluation_json = []

            primary_skills = CandidateSkillSet.objects.filter(candidate = application.resume, is_primary = True)
            primary_skill_json = []
            for skill in primary_skills:
                primary_skill_json.append({
                    "skill_name": skill.skill_name,
                    "skill_type": skill.skill_metric,
                    "value": skill.metric_value
                })

            secondary_skills = CandidateSkillSet.objects.filter(candidate = application.resume, is_primary = False)
            secondary_skill_json = []
            for skill in secondary_skills:
                secondary_skill_json.append({
                    "skill_name": skill.skill_name,
                    "skill_type": skill.skill_metric,
                    "value": skill.metric_value
                })

            upcoming_interview = None

            if application.next_interview != None:
                upcoming_interview = application.next_interview
            
            if upcoming_interview !=None:
                next_interview_json = {
                    "interviewer_name": upcoming_interview.interviewer.name.username,
                    "interview_date": upcoming_interview.scheduled_date,
                    "interview_time":f"{upcoming_interview.from_time} - {upcoming_interview.to_time}" 
                }

            else:
                next_interview_json = {}
            

            candidate_evaluation_json = defaultdict(list)

            for candidate in candidate_evaluations:
                candidate_evaluation_json[candidate.round_num].append({
                    "primary_skills_rating": json.dumps(candidate.primary_skills_rating),
                    "secondary_skills_rating": json.dumps(candidate.secondary_skills_ratings),
                    "remarks": candidate.remarks,
                    "interviewer_name": candidate.interview_schedule.interviewer.name.username,
                    "status": candidate.status,
                })

            candidate_evaluation_json = dict(candidate_evaluation_json)
            job = application.job_location.job_id

            application_json = {
                "application_id":application.id,
                "job_title":job.job_title,
                "job_department":job.job_department,
                "rounds_of_interview" : job.rounds_of_interview,
                "current_round": application.round_num,
                "deadline":job.job_close_duration,
                "candidate_name": application.resume.candidate_name,
                "candidate_email": application.resume.candidate_email,
                "candidate_phone": application.resume.contact_number,
                "application_status": application.status,
                "upcoming_interview": next_interview_json,
                "primary_skills":primary_skill_json,
                "secondary_skills": secondary_skill_json,
                "current_ctc": application.resume.current_ctc,
                "expected_ctc" : application.resume.expected_ctc,
                "current_job": application.resume.current_organisation,
                "current_job_location": application.resume.current_job_location,
                "current_job_type": application.resume.current_job_type,
                "highest_qualification": application.resume.highest_qualification,
                "date_of_birth": application.resume.date_of_birth,
                "notice_period": application.resume.notice_period,
                "joining_days_required": application.resume.joining_days_required,
                "resume": application.resume.resume.url if application.resume.resume != None else "",
                "created_at": application.created_at,
                "other_details":application.resume.other_details,
                "candidate_evaluation": candidate_evaluation_json,
                "job_location": application.job_location.location,
            }

            return Response({"application_data": application_json}, status=status.HTTP_200_OK)


        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LinkedInRedirectView(APIView):
    def get(self, request):
        try:
            code = request.GET.get("code")
            state = request.GET.get("state")

            redirect_url = f"http://localhost:8000/hiresync/generate-linkedincode/callback/"

            # Optional: validate state if using session
            # if state != request.session.get("linkedin_oauth_state"):
            #     return Response({"message": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)

            if not code:
                return Response({"message": "Missing authorization code.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            token_response = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_url,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                }
            )

            if token_response.status_code != 200:
                return Response({
                    "message": "Failed to retrieve access token from LinkedIn.",
                    "details": token_response.json(),
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")  

            if not access_token:
                return Response({"message": "Access token not found in response.", "status": False}, status=status.HTTP_400_BAD_REQUEST)

            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            orgs_response = requests.get(
                "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if orgs_response.status_code != 200:
                return Response({
                    "message": "Failed to fetch LinkedIn organizations.",
                    "details": orgs_response.json(),
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            org_data = orgs_response.json()
            elements = org_data.get("elements", [])

            if not elements:
                return Response({
                    "message": "No LinkedIn Page found for this account.",
                    "reason": "NO_PAGE",
                    "status": False
                }, status=status.HTTP_200_OK)

            organization_urn = elements[0].get("organizationalTarget")

            if not organization_urn:
                return Response({
                    "message": "Organization URN not found.",
                    "status": False
                }, status=status.HTTP_400_BAD_REQUEST)

            # Save to DB
            HiresyncLinkedinCred.objects.create(
                organization_urn=organization_urn,
                access_token=access_token,
                token_expires_at=expires_at,
            )

            return Response({
                "message": "LinkedIn credentials saved successfully.",  
                "organization_urn": organization_urn,
                "access_token": access_token,
                "expires_at": expires_at,
                "status": True
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateLinkedInTokens(APIView):
    def get(self, request):
        try:
            state = str(uuid.uuid4())  
            request.session['linkedin_oauth_state'] = state

            redirect_url = f"http://localhost:8000/hiresync/generate-linkedincode/callback/"  

            auth_url = (
                f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&client_id={settings.LINKEDIN_CLIENT_ID}"
                f"&redirect_uri={redirect_url}"
                f"&scope=w_member_social%20rw_organization_admin%20w_organization_social"
                f"&state={state}"
            )
            return HttpResponseRedirect(auth_url)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class FetchAllJobs(APIView):
    def get(self, request):
        try:
            jobs = JobPostings.objects.filter(status = 'opened')
            jobs_list = []
            for job in jobs:
                locations = list(JobLocationsModel.objects.filter(job_id = job.id).values_list('location', flat=True))
                jobs_list.append({
                    "job_title": job.job_title,
                    "job_description": html2text.html2text(job.job_description),
                    "experience": job.years_of_experience,
                    "job_locations": locations,
                    "job_type": job.job_type,
                    "ctc":job.ctc,
                    "job_level": job.job_level,
                    "status": job.status,
                    "id": job.id,
                    "created_at": job.created_at,
                    "agency_name": job.organization.name,
                }
                )
            return Response({"jobs_data":jobs_list}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class SendApplicationDetailsView(APIView):
    def post(self, request):
        try:
            data = request.data
            job_id = request.GET.get('job_id')
            location = request.data.get('location')
            
            location_instance = JobLocationsModel.objects.get(job_id = job_id,location = location)

            if not job_id:
                return Response({"error":"Jobid is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            email = data.get('candidate_email')
            
            if JobApplication.objects.filter(job_location__job_id__id=job_id, resume__candidate_email=email).exists():
                return Response(
                    {"error": "An application with this email is already sent, wait for the response"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            

            with transaction.atomic():
                candidate_resume = CandidateResume.objects.create(
                    resume= data.get('resume'),
                    candidate_name  = data.get('candidate_name'),
                    candidate_email = data.get('candidate_email'),
                    contact_number = data.get('contact_number'),
                    alternate_contact_number = data.get('alternate_contact_number', ''),
                    other_details = data.get('other_details', ''),
                    current_organisation = data.get('current_organization', ''),
                    current_job_location = data.get('current_job_location',''),
                    current_job_type = data.get('current_job_type', ''),
                    date_of_birth = data.get('date_of_birth'),
                    experience = data.get('experience'),
                    current_ctc = data.get('current_ctc',0.0),
                    expected_ctc = data.get('expected_ctc',0.0),
                    notice_period = data.get('notice_period',0),
                    job_status = data.get('job_status'),
                    highest_qualification = data.get('highest_qualification'),
                    joining_days_required = data.get('joining_days_required'),
                )

                job_application = JobApplication.objects.create(
                    resume = candidate_resume,
                    job_location = location_instance,
                    status = 'candidate_applied',
                    is_incoming = True
                )

            return Response({"message":"Application sent successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
class UpdateJoiningDate(APIView):
    permission_classes = [IsClient]
    def put(self, request):
        try:
            selected_candidate_id = request.GET.get('candidate_id')
            selected_candidate = SelectedCandidates.objects.get(id = selected_candidate_id)
            joining_date = request.data.get('updated_date')
            selected_candidate.joining_date = joining_date
            selected_candidate.save()
            # send maiil to recruiter and candidate that the joining date is updates
            return Response({"message":"Joining date updated successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            print("Error:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class UpdateCandidateLeft(APIView):
    permission_classes = [IsClient]

    def put(self, request):
        try:
            selected_candidate_id = request.GET.get('candidate_id')
            want_new_candidate = request.data.get('want_new_candidate', False)

            if not selected_candidate_id:
                return Response({"error": "Missing candidate_id in query params."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                selected_candidate = SelectedCandidates.objects.get(id=selected_candidate_id)
            except SelectedCandidates.DoesNotExist:
                return Response({"error": "Selected candidate not found."}, status=status.HTTP_404_NOT_FOUND)

            # Update statuses
            selected_candidate.joining_status = 'left'
            selected_candidate.application.status = 'left'
            selected_candidate.left_reason = "Candidate did not join on the joining date"

            selected_candidate.application.save()
            selected_candidate.save()

            # Handle reopening if requested
            if str(want_new_candidate).lower() == "true":
                reopen_joblocation(selected_candidate.application.job_location.id)
                return Response({"message": "Job reopened successfully."}, status=status.HTTP_200_OK)

            return Response({"message": "Candidate left status updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            print("Error:", str(e))
            return Response({"error": "Internal server error: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FetchPlans(APIView):
    def get(self, request):
        try:
            plans = Plan.objects.all()
            plans_list = []
            for plan in plans:
                plans_list.append({
                    "name": plan.name,
                    "price": plan.price,
                    "duration": plan.duration_days,
                    "id":plan.id,
                })
            return Response({"data":plans_list}, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class UpgradeRequestMail(APIView):
    def get(self, request):
        try:
            organization_id = request.GET.get('org_id')
            if not organization_id:
                return Response({"error": "Organization ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)

            try:
                client = ClientDetails.objects.get(user=request.user)
            except ClientDetails.DoesNotExist:
                return Response({"error": "Client details not found for the user."}, status=status.HTTP_404_NOT_FOUND)

            subject = f"Client Request: Job Post Limit Reached"
            body = f"""
Dear {organization.manager.get_full_name() or organization.manager.username},

Your client {client.user.get_full_name() or client.user.username} attempted to create a new job post, but your current plan has reached the job posting limit.

Please consider upgrading the plan to allow further job postings.

Thank you,
HireSync Platform
"""
  
            send_custom_mail(subject= subject , body=body, to_email=[organization.manager.email])
            return Response({"messaeg":"Plan upgradation request sent successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)