# app_name/tasks.py

from celery import shared_task
from app.role_views.celery_views import invoice_validate 
import time

# @shared_task
# def my_function():
#     print(f'Function executed at {time.strftime("%Y-%m-%d %H:%M:%S")}')

@shared_task
def invoice_generated():
    print(f"Invoice is generated at {time.strftime('%Y-%m-%d %H:%M:%S')}")


@shared_task
def daily_tasks_runner():
    invoice_validate()
    

   