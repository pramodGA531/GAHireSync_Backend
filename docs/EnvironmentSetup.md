# GA Hiresync – Full Environment Setup Guide

This document provides **complete setup instructions** for running the **Backend (Django)** and **Frontend (React)** of GA Hiresync.  
It includes **Celery**, **Docker**, **Environment Variables**, and commands to get everything running.

---

## 🛠️ Backend Setup (Django)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-repo>/ga-hiresync.git
cd ga-hiresync/backend
```


### 2️⃣ Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate      # For Linux/Mac
venv\Scripts\activate         # For Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r .requirements.txt
```


### 4️⃣ Setup Environment Variables
```bash
SECRET_KEY='3knfsd@!v=9p%8s@_$qttk'
DB_NAME='rtmas'
DB_USER='postgres'
DB_PASSWORD='12312'
DB_HOST='localhost'
DB_PORT='5433'
EMAIL_ID='kal23k2323iswerwr2r23r32mail.com'
EMAIL_PASSWORD='dbfopassworx'
apiurl='http://recruitment.gaorgsync.com'
environment='localhost'
LINKEDIN_CLIENT_ID='86p6yunklw1f9h'
LINKEDIN_CLIENT_SECRET='WPL_AP1.tOaYgyJh6HD262Zk.1knlLA=='
SIGNING_KEY='sI3k6dN6eQh6wYz9CwFzG2jM5pR7tUwXzAeD7gSjWnZr4u7z'
GEMINI_API_KEY='AIzaSyDdx7YY6AcBYTt4AaJb_0PjTN8_5CUIDwk'
frontendurl='http://localhost:3000'
backendurl='http://localhost:8000'
FRONTENDURL='http://localhost:3000'
```

### 5️⃣ Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```


### 6️⃣ Create Superuser
```bash
python manage.py createsuperuser
```


### 7️⃣ Start Django Server
```bash
python manage.py runserver
```

### 8️⃣ Run Celery and Celery Beat

```bash
celery -A backend_app worker -l info
celery -A backend_app beat -l info
```


 
### 9️⃣ Docker Setup (Backend)
```bash
docker-compose up --build
```


---

# 💻 Frontend Setup (React)


### 1️⃣ Navigate to Frontend

```bash
cd ../frontend
```



### 2️⃣ Install Dependencies
```bash
npm install
```



### 3️⃣ Setup Environment Variables
```bash
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_GOOGLE_AI_API_KEY=aefijjafaweef w;efjfw
```


### 4️⃣ Start React App
```bash
npm start
```





Github handling

There are 2 repo one for frontend and other for backend.
At present there are no branches. 



Integrations

Linkedin Integration through API
Gemini Integration through API
