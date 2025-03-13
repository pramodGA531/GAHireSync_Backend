from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.conf import settings 
from django.core.mail import send_mail
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from .permissions import *
from .authentication_views import *
from .models import InvoiceGenerated
from rest_framework import status
from django.shortcuts import get_object_or_404
from .utils import *


class GetUserDetails(APIView):
    def get(self,request):
        try:
            user = request.user
            data = {
                'username' : user.username,
                'email' : user.email,
                'role' : user.role,
                "is_verified": user.is_verified,
            }
            return Response({'data':data},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcceptJobPostView(APIView):
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({"error": "User is not authenticated"}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.role != 'manager':  
                return Response({"error": "You are not allowed to run this view"}, status=status.HTTP_403_FORBIDDEN)
            
            job_id = int(request.GET.get('id'))
            print(job_id, "is the id")
            if not job_id:
                return Response({"error": "Job post id is required"}, status=status.HTTP_400_BAD_REQUEST) 
            
            accept = request.query_params.get('accept')


            try:
                job_post = JobPostings.objects.get(id = job_id)
                if accept:
                    job_post.approval_status  = "accepted"
                else:
                    job_post.approval_status  = "rejected"

                job_post.save()
                return Response({"message":"Job post updated successfully"}, status=status.HTTP_200_OK)
            except JobPostings.DoesNotExist:
                return Response({"error":"Job post does not exists"}, status = status.HTTP_400_BAD_REQUEST)


        except Exception as e:
            print("error is ",str(e))
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
     

class OrganizationTermsView(APIView):
    permission_classes = [IsAuthenticated]   

    def get(self, request):
        user = request.user
        organization = Organization.objects.filter(manager=user).first()

        if not organization:
            return render(request, "error.html", {"message": "Organization not found"})
        
        values = request.GET.get('values')
        if values:
            try:
                organization_terms = OrganizationTerms.objects.get(organization = organization)
                serializer = OrganizationTermsSerializer(organization_terms)
            except OrganizationTerms.DoesNotExist:
                return Response({"error":"Organization Terms does not exist"}, status = status.HTTP_400_BAD_REQUEST)
            return Response({"data":serializer.data}, status=status.HTTP_200_OK)

        organization_terms, _ = OrganizationTerms.objects.get_or_create(organization=organization)
        serializer = OrganizationTermsSerializer(organization_terms)
        data = serializer.data

        context = {
            "service_fee": data.get("service_fee"),
            "invoice_after": data.get("invoice_after"),
            "payment_within": data.get("payment_within"),
            "replacement_clause": data.get("replacement_clause"),
            "interest_percentage": data.get("interest_percentage"),
            "data":data
        }

        return render(request, "organizationTerms.html", context)



    def put(self, request):
        try:
            user = request.user
            organization = Organization.objects.filter(manager = user).first()
            organization_terms = get_object_or_404(OrganizationTerms, organization = organization)
            data = request.data
            if data.get('description'):
                organization_terms.description = data.get('description' , organization_terms.description)
                organization_terms.save()
                return Response({"message":"Organization description updated successfully"}, status = status.HTTP_200_OK)
            else:
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
            negotiationrequests = NegotiationRequests.objects.filter(organization=organization)
        elif user.role == "client":
            client = ClientDetails.objects.get(user=user)
            negotiationrequests = NegotiationRequests.objects.filter(client=client)
        else:
            return Response({"detail": "You are not authorized to access this page"}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = NegotiationSerializer(negotiationrequests, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.role != "client":
            return Response({"detail": "Only clients can create negotiation requests"}, status=status.HTTP_403_FORBIDDEN)

        client = ClientDetails.objects.get(user=user)
        code = request.data.get('code')
        organization = Organization.objects.filter(org_code=code).first()

        if not organization:
            return Response({"detail": "Invalid organization code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = request.data

            negotiation_request = NegotiationRequests.objects.create(
                client=client,
                organization=organization,
                service_fee=data.get('service_fee'),
                replacement_clause=data.get('replacement_clause'),
                invoice_after=data.get('invoice_after'),
                payment_within=data.get('payment_within'),
                interest_percentage=data.get('interest_percentage')
            )

            
            client_email_message = f"""
Dear {client.user.first_name},

Your negotiation request has been successfully submitted to {organization.name}. The details of your request are as follows:

**Service Fee:** {data.get('service_fee')}
**Replacement Clause:** {data.get('replacement_clause')}
**Invoice After:** {data.get('invoice_after')} days
**Payment Within:** {data.get('payment_within')} days
**Interest Percentage:** {data.get('interest_percentage')}%
We will notify you as soon as the organization manager reviews your request.

Best regards,  
The Negotiation Team
"""

            
            manager_email_message = f"""
Dear {organization.manager.first_name},

A new negotiation request has been submitted by {client.user.first_name} {client.user.last_name} from {organization.name}. Here are the details:

**Service Fee:** {data.get('service_fee')}
**Replacement Clause:** {data.get('replacement_clause')}
**Invoice After:** {data.get('invoice_after')} days
**Payment Within:** {data.get('payment_within')} days
**Interest Percentage:** {data.get('interest_percentage')}%

Please review this request at your earliest convenience.

Best regards,  
The Negotiation Team
"""

            
            send_mail(
                subject="Negotiation Request Submitted",
                message=client_email_message,
                from_email='',
                recipient_list=[client.user.email]
            )

            send_mail(
                subject="New Negotiation Request Received",
                message=manager_email_message,
                from_email='',
                recipient_list=[organization.manager.email]
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
                negotiation_request.is_accepted = True
                negotiation_request.save()

                
                ClientTermsAcceptance.objects.create(
                    client=negotiation_request.client,
                    organization=negotiation_request.organization,
                    service_fee=negotiation_request.service_fee,
                    replacement_clause=negotiation_request.replacement_clause,
                    invoice_after=negotiation_request.invoice_after,
                    payment_within=negotiation_request.payment_within,
                    interest_percentage=negotiation_request.interest_percentage
                )

                
                client_email_message = f"""
Dear {negotiation_request.client.user.first_name},

Your negotiation request with {negotiation_request.organization.name} has been accepted. Here are the agreed terms:

**Service Fee:** {negotiation_request.service_fee}
**Replacement Clause:** {negotiation_request.replacement_clause}
**Invoice After:** {negotiation_request.invoice_after} days
**Payment Within:** {negotiation_request.payment_within} days
**Interest Percentage:** {negotiation_request.interest_percentage}%

Thank you for negotiating with us. We look forward to a successful collaboration.

Best regards,  
{negotiation_request.organization.name} Team
                """
                send_mail(
                    subject="Negotiation Request Accepted",
                    message=client_email_message,
                    from_email="",
                    recipient_list=[negotiation_request.client.user.email]
                )

            elif data.get('status') == "rejected":
                negotiation_request.is_accepted = False
                negotiation_request.save()

                
                client_email_message = f"""
Dear {negotiation_request.client.user.first_name},

We regret to inform you that your negotiation request with {negotiation_request.organization.name} has been rejected.

Please feel free to reach out to discuss any other possible terms.

Best regards,  
{negotiation_request.organization.name} Team
                """
                send_mail(
                    subject="Negotiation Request Rejected",
                    message=client_email_message,
                    from_email="",
                    recipient_list=[negotiation_request.client.user.email]
                )

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
            return Response(serializer.data, status=status.HTTP_200_OK)
        except JobPostings.DoesNotExist:
            return Response({"detail": "Job posting not found"}, status=status.HTTP_404_NOT_FOUND)

class JobEditStatusAPIView(APIView):
    def get(self, request):
        try:
            job_id = request.GET.get('id')
            job_edit_post = JobPostingsEditedVersion.objects.get(id=job_id)
            return Response({"status":job_edit_post.status}, status=status.HTTP_200_OK)
        except JobPostingsEditedVersion.DoesNotExist:
            return Response({'notFound':"Job edit post not found"},status= status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"error":str(e)},status= status.HTTP_400_BAD_REQUEST)
        
class RecJobPostings(APIView):
    def get(self, request,*args, **kwargs): 
        try:
            user = request.user
            org = Organization.objects.filter(recruiters__id=user.id).first()
            job_postings = JobPostings.objects.filter(organization=org, assigned_to = user)
            serializer = JobPostingsSerializer(job_postings,many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

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
                "recruiter_name": job_application.sender.username if job_application.sender else None,
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
                send_mail( 
                    subject=subject,
                    message= message,
                    recipient_list=[candidate_email],
                    from_email='',
                )

                return Response({"message":"Notification Sent Successfully"}, status=status.HTTP_200_OK)
            
            except Exception as e:
                print(str(e))
                return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(str(e))
            return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class Invoices(APIView):
    def get(self, request):
        # Print the user's role and user object for debugging
        print(f"User Role: {request.user.role}")
        print(f"User: {request.user}")

        invoices = []
        html_list = []

        if request.user.role == "client":
            # Clients can only see their own invoices based on their email
            invoices = InvoiceGenerated.objects.filter(client=request.user)
            for invoice in invoices:
                context = create_invoice_context(invoice)
                html = generate_invoice(context)
                html_list.append({"invoice": invoice, "html": html})

        elif request.user.role == "manager":
            # Managers can see all invoices related to their organization
            invoices = InvoiceGenerated.objects.filter(organization_email=request.user.email)
            for invoice in invoices:
                context = create_invoice_context(invoice)
                html = generate_invoice(context)
                html_list.append({"invoice": invoice, "html": html})

        elif request.user.role == "accountant":
            # Accountants can also see all invoices related to their organization
            accountant=Accountants.objects.get(user=request.user)
            print(accountant.organization)
            if accountant:
                invoices = InvoiceGenerated.objects.filter(organization=accountant.organization)
                for invoice in invoices:
                    context = create_invoice_context(invoice)
                    html = generate_invoice(context)
                    html_list.append({"invoice": invoice, "html": html})

        else:
            # If the user's role is not recognized, deny access
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        # If invoices exist, return them along with the generated HTML
        if invoices:
            # Prepare the invoice data for the response, along with the generated HTML for each invoice
            invoice_data = [{"id": invoice.id, "status": invoice.status, "client_email": invoice.client_email,"org_email":invoice.organization_email, "html": html["html"]} 
                            for invoice, html in zip(invoices, html_list)]
            return Response({"invoices": invoice_data}, status=status.HTTP_200_OK)

        # If no invoices found, return a not found message
        return Response({"message": "No invoices found."}, status=status.HTTP_404_NOT_FOUND)
    def put(self, request):
        # Print the user's role and user object for debugging
        print(f"User Role: {request.user.role}")
        print(f"User: {request.user}")
        if not request.user.role=="accountant":
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
        invoice_id = request.data.get('invoice_id')
        payment_transaction_id = request.data.get('payment_transaction_id')

        # Ensure that both the invoice ID and payment transaction ID are provided
        if not invoice_id or not payment_transaction_id:
            return Response({"error": "Both invoice_id and payment_transaction_id are required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            invoice = InvoiceGenerated.objects.get(id=invoice_id)
            invoice.status="Paid"
            invoice.payment_transaction_id = payment_transaction_id
            invoice.save()

            # Return a success response
            return Response({"message": "Invoice updated successfully."}, status=status.HTTP_200_OK)

        except InvoiceGenerated.DoesNotExist:
            # If invoice is not found, return an error response
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        
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
            }

            return Response(application_json, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
