import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from app.models import TOPUP, WhatsAppUsage, ClientDetails
from app.whatsapp_service import send_whatsapp


@csrf_exempt
def send_custom_whatsapp(request):
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
        # Get active topup (simplified logic)
        topup = TOPUP.objects.filter(organization=sender_org).latest("created_at")

        # Get or create usage
        usage, _ = WhatsAppUsage.objects.get_or_create(
            organization=sender_org, topup=topup
        )

        # Quota check
        if usage.remaining_whatsapp <= 0:
            return JsonResponse(
                {"success": False, "message": "WhatsApp limit exhausted"}, status=403
            )

        # Send WhatsApp
        result = send_whatsapp(to, message)

        if result.get("success"):
            usage.whatsapp_count += 1
            usage.save(update_fields=["whatsapp_count"])
            return JsonResponse(
                {
                    "success": True,
                    "sid": result.get("sid"),
                    "remaining_whatsapp": usage.remaining_whatsapp,
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
