from django.http import JsonResponse
from django.utils.timezone import now
from app.models import SelectedCandidates

def invoice_validate(request=None):  # request=None allows calling it without an HTTP request
    joined_candidates = SelectedCandidates.objects.filter(joining_status="joined",)

    job_list = []  # Collect job details for response

    for joined_candidate in joined_candidates:
        application = joined_candidate.application  
        job = application.job_id  

        job_list.append(str(job))  
        print(f"Processing Job: {job.id}") 
        print(f"application: {application.id}")

    # Return response only if it's an HTTP request
    if request:
        return JsonResponse({"status": "success", "jobs": job_list}, safe=False)
