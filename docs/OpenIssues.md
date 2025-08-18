### 🚧 GA Hiresync – Open Issues & Roadmap

This document outlines the key **pending features** to be completed before launch and highlights potential **future enhancements** for GA Hiresync.

---

#### ✅ Pending Features (Before Launch)

##### 🔢 Pricing Module
- Implement storage tracking: how to store resumes efficiently and calculate usage per agency. This needs brainstorming and technical comparison with other platforms.
- Add-on functionalities for email usage:
  - Track the number of emails sent per agency.
  - Send alerts when email quota is nearing completion.
  - Implement logic for top-up emails and plan upgrades.
- Integrate pricing logic across the platform with proper billing and usage metrics.

##### 📊 Dashboards
- Redesign and redevelop dashboards for **every user role** (Agency Manager, Recruiter, Client, Interviewer).
- Focus on performance, clarity, and usability tailored to each role.

##### 🌐 Website – New Pages & Updates
- Redevelop the redesigned website using the new dark theme.
- Add new feature pages:  
  - **Functional Features**
  - **Pricing**
- Update existing pages to reflect the latest platform capabilities.

##### 🔁 Replacement Logic
- Revisit and refactor current replacement logic where necessary.
- Perform thorough testing with edge cases and document the flow.

##### 🔔 Notification Module
- Add remaining notifications (currently missing due to evolving logic).
- Group and handle notifications by categories in the sidebar for every role.
- Create `notification.py` to mirror the structure of `emails.py` and centralize notification logic.
- Upgrade from HTTP polling to **WebSocket-based notifications** for better performance and real-time delivery.

##### 📬 Email Functionality
- Use **message brokers** (Redis/RabbitMQ) for sending emails asynchronously to reduce request time.
- Refactor all email content templates:
  - Include branding (agency logo, GA Hiresync footer).
  - Ensure consistent design and tone.
- Centralize email templates in a single file: `app/emails.py` (create it if it doesn't exist).
- Use the existing `customSendEmail` function in `utils.py` for sending all emails.

##### 🧾 Invoice Module
- Re-audit the invoice generation and its Celery-based workflow.
- Add GST fields for agencies:
  - Create an account details page for agency accountants to enter GST and billing info.
- Ensure GST details are incorporated in the final invoice PDF.

---

#### 🚀 Future Enhancements

##### Tutorials
- Add the tutorials about how to use this application. 
- Create the blogs and docs for tutorials.


##### Agency manager adding the new clients. 
- Manager can directly add their clients, without using any agency code. 
- Create an account for the client, if doesnot exist. Else display the client details.
- 


##### Inapp video nudges.
- Add some nudges to the application for the initial users. 
- Give the detailed explanation of every button (also with skip button).

##### Recruiter Credits Module, Incentive Module
- Track the recruiter, track every activity of viewing the profile, downloading the profile.
- Based on the performance of the recruiter, calculate the incentive for that recruiter (need more brainstorming discussions).

##### 💬 Chat Module
- Start building chat functionality using WebSockets.
- Define access controls (who can chat with whom):
  - Example: Recruiter ↔ Candidate, Client ↔ Agency Manager, etc.
- Create basic UI using existing design system components.

##### 🔗 LinkedIn Page Posting
- Currently posting as a simple post on the company page using LinkedIn API.
- In future, apply for advanced API access to post directly as **Job Posts**.
- Consider encryption and secure storage of LinkedIn credentials (see enhancements below).

##### 💡 UI Enhancements
- Understand user workflows and update UI components accordingly.
- Reuse core components:
  - `AppTable.js`
  - `DatePicker.js`
  - `AppCalendar.js`
- Create common reusable components instead of relying on third-party libraries (e.g., avoid `AntD Modals`, `AntD Messages`).
- Improve mobile responsiveness and accessibility (a11y).


##### API Integrations
- Integrate Hiresync API with proctored test
- Get summary of the candidates of the test , along with AI based review

##### 🛠 Admin Pricing Panel
- Develop admin pages to manage:
  - Pricing plans
  - Email/storage quotas
  - Customer analytics
- Build dashboards using charts to monitor usage, revenue, and plan upgrades.

##### 📆 Google Calendar Integration
- Auto-sync the following with users' Google Calendars:
  - Job post deadlines (for clients and agencies)
  - Interview schedules (for interviewers, recruiters, and candidates)
- Ensure proper consent and secure OAuth storage.

##### 📱 WhatsApp Integration
- Enable WhatsApp interactions:
  - Clients can create job posts via chat
  - Candidates and interviewers receive interview alerts
  - Agencies can send personalized reminders or prompts to clients


##### AI / ML Integrations
- Generating job creation fields
- Resume parsing
- Questions Generation


---








