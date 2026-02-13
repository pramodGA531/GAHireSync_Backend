import json
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from app.models import TOPUP, SMSUsage
from app.sms_service import send_sms


@csrf_exempt
def send_custom_sms(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    org_id = data.get("org_id")
    message = data.get("message")

    if not org_id or not message:
        return JsonResponse({"error": "org_id and message are required"}, status=400)

    try:
        from app.models import Organization

        target_org = Organization.objects.get(id=org_id)
        to = target_org.contact_number
        if not to.startswith("+"):
            to = f"+91{to}"  # Default to India if no code
    except Organization.DoesNotExist:
        return JsonResponse({"error": "Target organization not found"}, status=404)

    sender_org = getattr(request.user, "organization", None)
    if not sender_org:
        return JsonResponse(
            {"error": "Sender has no associated organization"}, status=403
        )

    try:
        # 1️⃣ Get active topup
        topup = TOPUP.objects.filter(organization=sender_org).latest("created_at")

        # 2️⃣ Get usage
        usage, _ = SMSUsage.objects.get_or_create(organization=sender_org, topup=topup)

        # 3️⃣ QUOTA CHECK
        if usage.remaining_sms <= 0:
            return JsonResponse(
                {"success": False, "message": "SMS limit exhausted"}, status=403
            )

        # 4️⃣ SANDBOX MODE (NO REAL SMS)
        if getattr(settings, "SANDBOX_MODE", False):
            return JsonResponse(
                {
                    "success": True,
                    "sandbox": True,
                    "sent_message": message,
                    "remaining_sms": usage.remaining_sms,
                }
            )

        # 5️⃣ SEND REAL SMS
        result = send_sms(to=to, message=message)

        # 6️⃣ UPDATE USAGE
        if result.get("success"):
            usage.sms_count += 1
            usage.save(update_fields=["sms_count"])
            return JsonResponse(
                {
                    "success": True,
                    "sid": result.get("sid"),
                    "remaining_sms": usage.remaining_sms,
                }
            )
        else:
            return JsonResponse(
                {"success": False, "error": result.get("error")}, status=500
            )

    except TOPUP.DoesNotExist:
        return JsonResponse(
            {"error": "No active topup found for sender organization"}, status=403
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
