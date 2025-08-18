### GA Hiresync – Complete Application Flow

---

#### Roles and Their Functionalities

##### 1. **Agency Manager**
- **Responsibilities:**
  - Connects with clients and manages organization-level tasks.
  - Approves, edits, or rejects job posts created by clients.
  - Assigns approved job posts to recruiters based on location.
  - Tracks recruiter performance and ensures jobs are filled.
  - Handles terms negotiation requests from clients.
  - Oversees overall hiring pipeline and closing of job posts.

---

##### 2. **Agency Recruiters**
- **Responsibilities:**
  - Receives assigned job posts and job locations from the Agency Manager.
  - Uses tools like **Gemini API** for parsing resumes and finding matching candidates.
  - Submits applications for job posts and locations.
  - Schedules interviews between candidates and interviewers.
  - Tracks the candidate's status from processing to joining.
  - Manages replacements when candidates leave.

---

##### 3. **Client**
- **Responsibilities:**
  - Connects with the organization using a unique organization code.
  - Reviews and approves or negotiates **terms and conditions**.
  - Creates job posts after approval of terms.
  - Reviews applications submitted by recruiters:
    - Shortlist, reject, or hold applications.
    - Select candidates, negotiate or finalize offers.
  - Updates joining status and reports candidate exits (for replacement eligibility).

---

##### 4. **Interviewer**
- **Responsibilities:**
  - Receives scheduled interview notifications.
  - Conducts interviews and updates interview status (next round or rejection).
  - Provides feedback for each interview round.

---

##### 5. **Candidate**
- **Responsibilities:**
  - Applies through the GA Hiresync job board or is added by recruiters.
  - Receives notifications about shortlist status, interviews, and offers.
  - Can accept, reject, or negotiate joining offers.
  - Tracks application status through the candidate portal.

---

##### 6. **Accountant**
- **Responsibilities:**
  - Monitors invoices automatically generated when candidates join.
  - Alerts clients for pending payments.
  - Ensures financial tracking between client and organization.

---

##### 7. **Admin**
- **Responsibilities:**
  - Handles global platform activities.
  - Manages blog approvals and ticket resolutions.
  - Oversees non-role-specific administrative functions.

---

#### **End-to-End Application Flow**

##### **Step 1 – Client and Organization Setup**
- Client connects to the organization.
- Organization defines **terms and conditions** (CTC ranges, clauses).
- Client approves or negotiates terms (Agency Manager handles negotiations).
- If approved → client proceeds to job post creation.

##### **Step 2 – Job Post Creation and Approval**
- Client creates job post with:
  - Job details  
  - Skills  
  - Interview requirements  
- Agency Manager:
  - Approves → Moves to recruiters.
  - Edits → Sends back to client for confirmation.
  - Rejects → Stops the process.

##### **Step 3 – Recruiter Actions**
- Manager assigns job posts to recruiters (by location).
- Recruiters parse resumes (Gemini API) and submit applications.
- Candidates can also directly apply via job board.

##### **Step 4 – Application Shortlisting**
- Applications have statuses:
  - **Pending**, **Processing**, **Rejected**, **Hold**, **Selected**, **Accepted**, **Joined**, **Replacement**.
- Client reviews applications:
  - Shortlist → Moves to **Processing**.
  - Reject → Status set to **Rejected** (with reason).
- Notifications sent to recruiter and candidate on every status change.

##### **Step 5 – Interview Process**
- Recruiter schedules interview with interviewer and candidate.
- Interview rounds conducted.
- Interviewer updates feedback and round results.
- Application stays **Processing** until rounds are completed.
- Post-interview → Application moves to **Hold**.

##### **Step 6 – Final Selection and Joining**
- Client selects candidate → **Selected** status.
- Candidate responds:
  - Accepts → **Accepted** status.
  - Rejects / Negotiates → Agency Manager/Client approves or declines negotiation.
- On joining date:
  - Client updates status → **Joined**.
  - Position closes automatically.
- Accountant monitors invoice generation.

##### **Step 7 – Replacement Flow**
- If candidate leaves:
  - Client updates reason.
  - Eligibility for replacement checked.
  - If eligible → Job post reopens.
  - Recruiter finds replacement until filled.

---

### **Mermaid Diagram – Complete Flow**

```mermaid
flowchart TD

    subgraph CLIENT[Client]
        C1[Connects to Organization]
        C2[Approves / Negotiates Terms]
        C3[Creates Job Post]
        C4[Shortlists / Rejects Applications]
        C5[Selects Candidate]
        C6[Updates Joining Status / Replacement]
    end

    subgraph AGENCY_MANAGER[Agency Manager]
        M1[Handles Negotiations]
        M2[Approves / Edits / Rejects Job Post]
        M3[Assigns Job Post to Recruiters]
        M4[Monitors Job Closure]
    end

    subgraph RECRUITER[Agency Recruiter]
        R1[Receives Job Post]
        R2[Parses Resume using Gemini]
        R3[Submits Applications]
        R4[Schedules Interviews]
        R5[Tracks Candidate till Joining]
        R6[Handles Replacement Candidates]
    end

    subgraph INTERVIEWER[Interviewer]
        I1[Receives Interview Schedule]
        I2[Conducts Interviews]
        I3[Updates Status for Each Round]
    end

    subgraph CANDIDATE[Candidate]
        CA1[Applies via Job Board or Recruiter]
        CA2[Receives Notifications]
        CA3[Attends Interviews]
        CA4[Accepts / Rejects Offers]
        CA5[Joins Organization]
    end

    subgraph ACCOUNTANT[Accountant]
        AC1[Tracks Invoices]
        AC2[Sends Payment Reminders]
    end

    subgraph ADMIN[Admin]
        AD1[Approves Blogs]
        AD2[Handles Tickets]
    end

    %% Connections
    CLIENT -->|Negotiate Terms| AGENCY_MANAGER
    AGENCY_MANAGER -->|Approve Terms| CLIENT
    CLIENT -->|Create Job Post| AGENCY_MANAGER
    AGENCY_MANAGER -->|Approve / Assign| RECRUITER
    RECRUITER -->|Submit Applications| CLIENT
    CLIENT -->|Shortlist / Reject| RECRUITER
    CLIENT -->|Schedule Interviews| RECRUITER
    RECRUITER -->|Coordinate Interview| INTERVIEWER
    INTERVIEWER -->|Feedback| RECRUITER
    CLIENT -->|Select Candidate| RECRUITER
    RECRUITER -->|Notify Candidate| CANDIDATE
    CANDIDATE -->|Accept / Reject Offer| CLIENT
    CLIENT -->|Update Joining Status| ACCOUNTANT
    ACCOUNTANT -->|Invoice Tracking| CLIENT
    CLIENT -->|Candidate Left / Replacement| RECRUITER
    ADMIN -->|Support System| CLIENT
    ADMIN -->|Support System| AGENCY_MANAGER

    classDef default fill:#d9e6f2,stroke:#4d648d,stroke-width:1px;
    classDef green fill:#b9f6ca,stroke:#1b5e20,stroke-width:1px;
    classDef yellow fill:#fff59d,stroke:#f57f17,stroke-width:1px;
    classDef red fill:#ff8a80,stroke:#b71c1c,stroke-width:1px;

    class CLIENT,AGENCY_MANAGER,RECRUITER,INTERVIEWER,CANDIDATE,ACCOUNTANT,ADMIN default

```