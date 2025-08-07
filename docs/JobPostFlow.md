### Flow of Job Post

1. **Client Connection**
   - Initially, the client connects to the organization to create a job opening.

2. **Terms and Conditions**
   - When the organization accepts the client, it needs to fill out the **terms and conditions** for the CTC range (up to 1–100 LPA).
   - A notification is automatically sent to the client for review.

3. **Client Approval or Negotiation**
   - To create a job post, the client must approve the terms and conditions.
   - Alternatively, the client can **negotiate** the terms:
     - Client fills out the **CTC range** and remaining terms.
     - Notification is automatically sent to the agency manager.
     - Daily notifications continue until the agency manager takes action.
   - **Negotiation Outcome:**
     - If approved → client can proceed with creating the job post.
     - If rejected → client cannot create the job post with those terms.

4. **Job Post Creation**
   - Client creates the job post including:
     - **Job details**
     - **Skill details**
     - **Interview details**

5. **Agency Actions on Job Post**
   - Agency can:
     - **Approve** – job post moves forward.
     - **Edit** – edit request is sent back to the client:
       - Client reviews and approves edits or adds new fields.
       - Edited post returns to agency for final approval/rejection.
       - (No multiple edit cycles after this round.)
     - **Reject** – agency must provide a reason.
   - Automatic notifications are triggered for every action.

6. **Assigning Job Post**
   - If approved, the agency manager assigns the job post to recruiters **based on locations**.
   - Multiple recruiters can be assigned to:
     - A single location, or
     - A single job post.

7. **Application Submission**
   - Recruiters submit applications for specific job locations.
   - *(Application flow has its own detailed chart for clarity.)*

8. **Closing Job Locations and Posts**
   - Once all positions for a specific location are filled:
     - The **location status** is automatically marked as **closed**.
   - When all locations of a job post are closed:
     - The **job post status** is automatically **closed**.
   - Status of ongoing applications is updated to **closed** accordingly.

9. **Candidate Replacement**
   - If a selected candidate leaves:
     - Replacement is provided to the client based on eligibility and reason.
     - If replacement is approved:
       - Job post is **reopened**.
     - Client can:
       - Select from **previous applications**, or
       - Request **new applications** from the organization.





#### Go through this flowchart in mermade editor for visual representation.
```mermaid

flowchart TD
    A[Client connects to Organization]:::default --> B[Organization sets Terms & Conditions]:::default
    B --> C[Notification sent to Client]:::default
    
    C --> D[Client approves Terms]:::green
    C --> E[Client negotiates Terms]:::yellow

    E --> F[Notification to Agency Manager]:::default
    F --> G[Agency Manager approves Negotiation]:::green
    F --> H[Agency Manager rejects Negotiation]:::red

    D --> I[Client creates Job Post]:::default
    G --> I
    H --> Z[Client cannot create Job Post with these Terms]:::red

    I --> J[Job Post includes Job details, Skills, Interview details]:::default
    J --> K[Agency reviews Job Post]:::default
    
    K --> L[Agency approves]:::green
    K --> M[Agency requests edits]:::yellow
    K --> N[Agency rejects with reason]:::red

    M --> O[Client reviews and approves edits or adds new fields]:::yellow
    O --> P[Edited post sent back to Agency]:::default
    P --> L
    P --> N

    L --> Q[Assign Job Post to Recruiters based on Locations]:::default
    Q --> R[Multiple Recruiters can be assigned]:::default

    R --> S[Recruiters submit Applications per Location]:::default
    S --> T[Positions filled for a Location]:::green
    T --> U[Location status set to Closed]:::green
    U --> V[All Locations Closed → Job Post Closed]:::green
    V --> W[Applications status updated to Closed]:::green

    W --> X[If Candidate leaves]:::default
    X --> Y[Replacement eligibility check]:::default
    Y --> |Approved| AA[Job Post Reopened]:::yellow
    Y --> |Rejected| AB[No replacement provided]:::red
    
    AA --> AC[Client can select from Old Applications or Request New Applications]:::default

    classDef default fill:#d9e6f2,stroke:#4d648d,stroke-width:1px;
    classDef green fill:#b9f6ca,stroke:#1b5e20,stroke-width:1px;
    classDef yellow fill:#fff59d,stroke:#f57f17,stroke-width:1px;
    classDef red fill:#ff8a80,stroke:#b71c1c,stroke-width:1px;
```