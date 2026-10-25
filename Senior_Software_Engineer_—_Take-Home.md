# Senior Software Engineer — Take-Home Exercise

## Event Calendar for Tabletop Game Events

**Timebox: 3 hours.** We don't expect polish everywhere — we expect good judgment about where to spend your time. AI tools (Claude, Copilot, ChatGPT, etc.) are allowed and expected; see the AI policy below.

### Scenario

We run organized play for trading card games. A store organizer needs a small web app to schedule in-store game events and let players register for them.

### Requirements

**1. Event creation**
An organizer can create an event with at minimum: a name, a game type, a date and start time, and a player capacity. Events must support a capacity of up to 30 players.

**2. Game types & templates**
The app must support at least 3 trading card games. One of them must be **Magic: The Gathering**; pick the other two yourself. Implement game types as a lightweight _template_ system, not hard-coded strings: each game template should drive at least two event properties (for example: available play formats, default event duration, default/max capacity, minimum players to start the event). Design it so a 4th game could be added without touching core event logic.

**3. Calendar view**
Display scheduled events on a calendar so an organizer can see what's happening on a given day. A month grid or a grouped-by-day agenda list are both acceptable. Using a calendar library is fine.

**4. Calendar invite**
An event page must offer a downloadable calendar invite (`.ics` file) for that event, with correct title, start/end time, and location, importable into Google Calendar or Outlook.

**5. Registration with QR code**
Each event gets a registration link, and the event page displays a QR code encoding that link. Scanning it takes a player to a simple registration form (name is enough). Registration must be **capacity-enforced**: once the event is full, further registrations are rejected with a clear message — enforce this on the server, not just in the UI.

### Deliverables

1. Use GitHub, GitLab, BitBucket or some other public git repository host to host your code repo. Do not send us a zip/tar bundle of your project.
2. A `README.md` containing:
   - How to run it locally (one or two commands preferred; `docker compose up` or a seed script is a plus).
   - **Design write-up (~1 page)** answering:
     - How did you determine and enforce how many people can attend an event? Where does capacity live, and what happens under concurrent registrations for the last seat?
     - How does your template system work, and what would adding a 4th game (or a non-card game) require?
     - What did you deliberately cut or fake to stay in the timebox, and what would you build next?
   - **AI usage note (a few sentences):** which tools you used and for what, and one example of AI output you rejected or had to fix.

### Constraints & guidance

- Any language/framework. Any storage (in-memory, SQLite, etc. — no hosted DB required).
- No auth required. Assume one organizer; players are anonymous until they register.
- Don't build: payments, email sending, recurring events, editing/cancelling events, admin dashboards.
- Prioritize: a working end-to-end flow (create event → see it on calendar → scan/click QR → register → event fills up) over visual polish.
- If you run out of time, ship what works and say so in the README — an honest cut list beats a broken feature.

### What we evaluate

| Area            | What we look for                                                                                            |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| Data modeling   | Event/template/registration entities; capacity as a first-class, enforced constraint                        |
| Template design | Genuine extensibility vs. if/else on game names                                                             |
| Correctness     | Capacity enforcement at the API layer; sensible handling of the full-event and duplicate-registration cases |
| Judgment        | Scope cuts, library choices (QR and ICS should be libraries, not hand-rolled), commit history               |
| Communication   | README clarity and quality of the design write-up                                                           |
| AI leverage     | Effective use of AI without accepting broken or bloated output                                              |

We do **not** evaluate: CSS polish, deployment
