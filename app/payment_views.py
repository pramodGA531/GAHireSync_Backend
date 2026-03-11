import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Plan, OrganizationPlan, Organization
from django.utils import timezone
from datetime import timedelta
from .utils import send_payment_success_email
import os


class RazorpayOrderView(APIView):
    def post(self, request):
        plan_id = request.data.get("plan_id")
        try:
            plan = Plan.objects.get(id=plan_id)
            client = razorpay.Client(
                auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
            )

            # Razorpay amount is in paise (1 INR = 100 paise)
            data = {
                "amount": int(plan.price * 100),
                "currency": "INR",
                "receipt": f"receipt_plan_{plan_id}",
                "payment_capture": 1,
            }
            order = client.order.create(data=data)
            return Response(order, status=status.HTTP_200_OK)
        except Plan.DoesNotExist:
            return Response(
                {"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RazorpayVerificationView(APIView):
    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")
        organization_id = request.data.get("organization_id")
        plan_id = request.data.get("plan_id")

        client = razorpay.Client(
            auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        )

        try:
            # Verify signature
            params_dict = {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
            client.utility.verify_payment_signature(params_dict)

            # Update organization plan
            organization = Organization.objects.get(id=organization_id)
            plan = Plan.objects.get(id=plan_id)

            # Find the pending plan or create new
            org_plan, created = OrganizationPlan.objects.get_or_create(
                organization=organization,
                plan=plan,
                payment_status="pending",
                defaults={
                    "expiry_date": timezone.now() + timedelta(days=plan.duration_days)
                },
            )

            org_plan.payment_status = "paid"
            org_plan.is_active = True
            org_plan.payment_reference = razorpay_payment_id
            org_plan.amount_paid = plan.price
            org_plan.save()

            # Send success email
            try:
                send_payment_success_email(organization.manager, plan, org_plan)
            except Exception as e:
                print(f"Failed to send payment success email: {str(e)}")

            return Response(
                {"message": "Payment verified and plan activated"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": "Payment verification failed: " + str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
