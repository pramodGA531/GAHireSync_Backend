from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.models import JobPostings, CustomUser, Organization
from rest_framework.permissions import IsAuthenticated
from app.permissions import IsAdmin
class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdmin]
    

    def get(self, request):
        try:
            total_jobs = JobPostings.objects.count()
            total_clients = CustomUser.objects.filter(role='client').count()
            total_agencies = Organization.objects.count()

            data = {
                "total_jobs": total_jobs,
                "total_clients": total_clients,
                "total_agencies": total_agencies
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
