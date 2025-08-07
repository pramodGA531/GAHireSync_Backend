# GA Hiresync – Modules Overview

This document outlines the **core modules**, their purpose, and functionality within the GA Hiresync application. It also highlights **future enhancements** for system improvement.

---

## 1️⃣ Authentication Module
- **Signup/Access:**
  - **Agency Manager** and **Client** can **sign up** through the application.
  - **Agency Manager**:
    - Fills necessary details and selects a suitable **plan** during signup.
    - **Organization details** stored in `Organizations Model`.
    - **Manager details** stored in `CustomUser Model`.
  - **Client**:
    - Can **sign up directly** without any payment.
    - After login, can **add multiple interviewers** (stored in `ClientDetails Model` and `CustomUser Model`).
- **Additional Roles**:
  - Agency Manager can **add recruiters** and **one accountant** via dashboard (limited by selected plan).
  - **Candidate account** automatically created once shortlisted.
  - **Admin** can log in for managing blogs and tickets.
- **Authentication Flow**:
  - **Single login page** throughout the application.
  - Accessible via website: [GA Hiresync](www.gahiresync.com).
- **Data Storage**:
  - All users stored in `CustomUser Model` along with their **role**.

---

## 2️⃣ Client ↔️ Manager Connection & Terms Approval
- **Connection:**
  - Client connects to Agency Manager using a **unique agency code**.
  - Currently, the client manually requests the code (outside application).
  - Input code on “Create Job Post” page → approval request sent to manager.
- **Manager Actions:**
  - Approves client based on **terms & conditions** stored in `ClientOrganizationTerms Model`.
  - Differentiated by **CTC range**.
- **Negotiation:**
  - Clients can **negotiate terms** based on CTC.
  - Negotiated terms stored in `NegotiatedTerms Model`.
  - Loop continues until manager approves negotiation.
- **Connection Tracking:**
  - `ClientOrganization Model` stores approval status.
- **Future Enhancement:**
  - Agency Manager can **add clients directly** from their dashboard (similar to adding recruiters).

---

## 3️⃣ Job Post Creation Module
- **Job Data Storage:**
  - `JobPostings Model` → all job details, raised by client, received by manager.
- **Interview Management:**
  - `InterviewerDetails Model` → interviewer assignments per job.
- **Locations:**
  - `JobLocation Model` → job locations, number of positions, job type per location.
- **Skill Requirements:**
  - `SkillSet Model` → required skills for job post:
    - `is_primary = True` → primary skills.
    - `is_primary = False` → secondary skills.

---

## 4️⃣ Job Post Editing Module
- **Editing Process:**
  - `EditJobPost Model` → stores fields modified by client.
  - Clients can:
    - Approve edits.
    - Add new edit requests.
  - Differentiated as:
    - **Version** and **Base version** in models.
- **Notes:**
  - Detailed explanation available in `models.py`.

---

## 5️⃣ Job Post Handling & Application Management Module
- **Manager Tasks:**
  - Approves job posts.
  - Posts job automatically on **Job Board**.
  - Assigns recruiters based on location.
- **Recruiters:**
  - Handle applications, conduct interviews, schedule rounds.
- **Detailed Flow:**
  - See **JobPostFlow** and **JobApplicationFlow** for end-to-end process.

---

## 6️⃣ Notification Module
- **Current Behavior:**
  - Notifications categorized by type and **receiver** stored in `Notifications Model`.
  - Categories used to label **menu items** in sidebar.
- **Future Enhancements:**
  - **Redesign notifications** for better menu label control.
  - Shift from `HTTP` polling to **WebSockets** for real-time updates.

---

## 7️⃣ Celery Module
- **Purpose:**
  - Handles **automatic scheduling** for background tasks.
  - Celery and Celery Beat used for periodic tasks.
- **Documentation:**
  - Detailed explanation available in `Views.md`.

---

## 8️⃣ Resume Parsing & AI Functionalities
- **Recruiter Tools:**
  - Parse resumes and score them.
  - Generate interview questions based on job post.
- **Implementation:**
  - Uses **Gemini API** on backend.
  - API keys securely stored in `.env` file.

---

## 9️⃣ LinkedIn Integration Module
- **Storage:**
  - `LinkedInCred Model` → agency’s LinkedIn credentials.
  - GA Hiresync’s own LinkedIn credentials also stored.
- **Functionality:**
  - Allows **automatic posting** of job posts on:
    - Agency’s LinkedIn account.
    - GA Hiresync LinkedIn page.

---

## 🔟 Job Board Module
- **Public Access:**
  - Lists all client-created job posts.
  - **No login required** for candidates.
- **Application:**
  - Candidates can apply directly.
  - Application is sent to recruiter linked to job post and client.

---

## 1️⃣1️⃣ Website Module
- **Purpose:**
  - Static pages providing information about GA Hiresync.
- **Pending Updates:**
  - Feature pages.
  - Pricing pages.

---

## 1️⃣2️⃣ Invoice Module
- **Generation:**
  - Invoices automatically generated once **candidate joins** client’s company.
- **Terms:**
  - Generated based on **pre-approved terms**.

---

## 1️⃣3️⃣ Pricing Module
- **Functionality:**
  - Defines **plans** with features.
- **Notes:**
  - Started with basic features.
  - Detailed explanation in `Views` file.
- **Future Enhancement:**
  - Expand features and pricing capabilities.

---

## 1️⃣4️⃣ Draft Module
- **Purpose:**
  - Allows saving **job post drafts**.
  - Prevents loss of data during post creation.

---

## 1️⃣5️⃣ Blogs Module
- **Visibility:**
  - All blogs are **publicly visible**.
- **Admin Role:**
  - Creates blogs via dashboard.
  - Uses **Quill Editor** for content.
  - Supports simple text and HTML.
- **Usage:**
  - Enhances product visibility and knowledge sharing.

---

## 1️⃣6️⃣ Ticket Module (Support System)
- **Purpose:**
  - Users can **raise support tickets** via dashboard.
- **Admin Panel:**
  - Admin resolves issues and provides guidance.
  - Includes **chat panel** for real-time user-admin interaction.

---

## 🚀 Future Enhancements & Advancements

- Agency Manager can **add clients directly** (dashboard feature).
- **Notification module redesign** for improved menu labeling.
- Switch to **real-time notifications** via **WebSockets**.
- Expand **Pricing module** with more features and flexible plans.
- Connect **Job Board** with the main JobBoard application.
- Update  **Linkedin** postings to directly post as new job (want to get API from linkedin)
- Add **feature pages** and **pricing pages** to website.
- Improve **resume parsing AI** with advanced scoring models.
- Upgrade **Celery-based scheduling** with more automation rules.
- Integrating with 

---
