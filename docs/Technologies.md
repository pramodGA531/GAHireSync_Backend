## Technologies Used

GA HireSync is built using a modern full-stack architecture to ensure scalability, maintainability, and performance. Below are the primary technologies and tools used:

### **Backend**
- **Django** – Python web framework for rapid development and secure backend logic.  
  - **Version:** `5.0.6` 
  - **Features Used:** Django ORM, Middleware, Authentication System, Django REST Framework (for APIs), Celery (for messaging), Redis (message borker)  
- **Django REST Framework (DRF)** – Provides RESTful APIs to handle communication between frontend and backend.  
  - **Version:** `3.15.1`  
- **Python** – Core programming language for backend development.  
  - **Version:** `3.x`

### **Frontend**
- **React.js** – JavaScript library for building interactive UIs.  
  - **Version:** `18.x` *(replace if different)*  
  - **Bundler:** **Vite** (for fast builds and hot reloading)  
- **Ant Design / Material UI** *(if used)* – UI component library for consistent styling.  

### **Database**
- **PostgreSQL** – Relational database for storing structured application data.  
  - **Version:** `14.x` *(replace if different)*  
- **pgAdmin** *(optional)* – Database management and visualization tool.  

### **Authentication & Security**
- **JWT-based authentication** – Using Django SimpleJWT for secure token-based authentication.  
- **CSRF Protection** – Built-in Django protection for secure form submissions.  
- **Password Hashing** – Django’s built-in user session and password hashing mechanism.  

### **Caching / Queues**
- **Redis** *(if used)* – For caching and background task queues.  

### **Deployment & DevOps**
- **Docker** – Containerization for consistent deployment environments.  
- **Nginx** – Reverse proxy and load balancing.  
- **Gunicorn / uWSGI** – WSGI HTTP server for running Django apps.  
- **PM2** *(if used)* – Process management for frontend or Node-based services.  

### **Version Control**
- **Git & GitHub** – Source code management and version control.  

### **Others**
- **Celery** *(if used)* – Task scheduling and background jobs.  
- **Third-party APIs / Integrations** – (e.g., Google, AWS, payment gateways).  
