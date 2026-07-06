import streamlit as st
import json
from datetime import datetime
from api_client import ConciergeApiClient

# Setup page layout
st.set_page_config(
    page_title="Personal Concierge AI",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS styles
try:
    with open("frontend/style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    pass

# Initialize API Client
# Points to localhost backend API
API_URL = "http://localhost:8000/api"
client = ConciergeApiClient(base_url=API_URL)

# --- Session State Management ---
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "household_id" not in st.session_state:
    st.session_state.household_id = None
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "dashboard_refresh" not in st.session_state:
    st.session_state.dashboard_refresh = 0

def trigger_refresh():
    st.session_state.dashboard_refresh += 1

# --- Auto-Login Demo Household for Immediate Public Accessibility ---
# Ensures the app doesn't block users with a hard login wall
def perform_auto_demo_login():
    if not st.session_state.token:
        # Attempt to login as demo user
        login_res = client.login("demo_user", "demo_pass_123")
        if "access_token" in login_res:
            st.session_state.token = login_res["access_token"]
            st.session_state.username = login_res["username"]
            st.session_state.household_id = login_res["household_id"]
        else:
            # If demo user does not exist, register them
            reg_res = client.register("demo_user", "demo_pass_123", "Demo Family Household")
            if "id" in reg_res:
                login_res = client.login("demo_user", "demo_pass_123")
                if "access_token" in login_res:
                    st.session_state.token = login_res["access_token"]
                    st.session_state.username = login_res["username"]
                    st.session_state.household_id = login_res["household_id"]

perform_auto_demo_login()

# --- Sidebar UI ---
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    st.markdown("### 🔒 Personal Concierge")
    st.markdown("</div>", unsafe_allow_html=True)

    # Auth Panel
    if st.session_state.token:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write(f"Logged in as: **{st.session_state.username}**")
        st.write(f"Household ID: **{st.session_state.household_id}**")
        
        # Display demo alert if auto-logged in
        if st.session_state.username == "demo_user":
            st.warning("Running in public Demo Household. Switch user to isolate your data.")
            
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.username = None
            st.session_state.household_id = None
            st.session_state.active_session_id = None
            st.session_state.chat_history = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        auth_mode = st.tabs(["Login", "Register"])
        
        # Login Tab
        with auth_mode[0]:
            login_user = st.text_input("Username", key="login_username")
            login_pass = st.text_input("Password", type="password", key="login_password")
            if st.button("Log In", use_container_width=True):
                res = client.login(login_user, login_pass)
                if "access_token" in res:
                    st.session_state.token = res["access_token"]
                    st.session_state.username = res["username"]
                    st.session_state.household_id = res["household_id"]
                    st.session_state.active_session_id = None
                    st.session_state.chat_history = []
                    st.success("Welcome back!")
                    st.rerun()
                else:
                    st.error(res.get("message", "Login failed"))
                    
        # Register Tab
        with auth_mode[1]:
            reg_user = st.text_input("Username", key="reg_username")
            reg_pass = st.text_input("Password", type="password", key="reg_password")
            reg_house = st.text_input("Household/Family Name", placeholder="e.g. The Smiths", key="reg_house")
            if st.button("Register Account", use_container_width=True):
                res = client.register(reg_user, reg_pass, reg_house or "My Household")
                if "id" in res:
                    st.success("Registered successfully! Logging in...")
                    login_res = client.login(reg_user, reg_pass)
                    if "access_token" in login_res:
                        st.session_state.token = login_res["access_token"]
                        st.session_state.username = login_res["username"]
                        st.session_state.household_id = login_res["household_id"]
                        st.session_state.active_session_id = None
                        st.session_state.chat_history = []
                        st.rerun()
                else:
                    st.error(res.get("message", "Registration failed"))
        st.markdown("</div>", unsafe_allow_html=True)

    # Chat Session Manager (if logged in)
    if st.session_state.token:
        st.markdown("---")
        st.markdown("### 💬 Conversations")
        
        # New Chat Button
        if st.button("+ New Conversation", use_container_width=True):
            new_sess = client.create_session()
            if "id" in new_sess:
                st.session_state.active_session_id = new_sess["id"]
                st.session_state.chat_history = []
                st.rerun()
                
        # List of past conversations
        sessions = client.list_sessions()
        if sessions:
            for s in sessions:
                session_label = f"💬 {s['title']}"
                is_active = (s["id"] == st.session_state.active_session_id)
                
                # Active styling or standard selection
                if is_active:
                    st.markdown(f"**{session_label}** (current)")
                else:
                    if st.button(session_label, key=f"session_btn_{s['id']}", use_container_width=True):
                        st.session_state.active_session_id = s["id"]
                        st.session_state.chat_history = client.get_session_history(s["id"])
                        st.rerun()
        else:
            st.info("No past conversations.")

# --- Main App Interface ---
st.markdown("<div class='main-title'>Personal Concierge Assistant</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='privacy-badge'>🔒 AES-256 Field-Level Encryption Active at Rest for Household Privacy</div>", 
    unsafe_allow_html=True
)
st.write("")

if not st.session_state.token:
    st.info("Please login or register to use the Personal Concierge. (Demo Household will load automatically if backend is active)")
else:
    # 3 Main Tabs: Chat, Logistics Dashboard, Privacy Audit
    tab1, tab2, tab3 = st.tabs([
        "💬 Conversational Assistant", 
        "📊 Logistics Dashboards", 
        "🛡️ Privacy & Transparency Center"
    ])

    # ------------------ Tab 1: Chat interface ------------------
    with tab1:
        st.markdown("### Chat with your Assistant")
        st.caption("Ask your assistant in natural language to manage your medication doses, track party guest lists, or schedule garden tasks.")

        # Ensure active session exists
        if not st.session_state.active_session_id:
            sessions = client.list_sessions()
            if sessions:
                st.session_state.active_session_id = sessions[0]["id"]
                st.session_state.chat_history = client.get_session_history(sessions[0]["id"])
            else:
                new_sess = client.create_session()
                if "id" in new_sess:
                    st.session_state.active_session_id = new_sess["id"]
                    st.session_state.chat_history = []

        # Display conversational chat history
        chat_container = st.container(height=450)
        with chat_container:
            history = client.get_session_history(st.session_state.active_session_id)
            for msg in history:
                with st.chat_message(msg["sender"]):
                    st.markdown(msg["text"])

        # Chat user input
        if prompt := st.chat_input("How can I help you today?"):
            # Display user message instantly
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # Call backend message processing
            with st.spinner("Processing request..."):
                response_msg = client.send_message(st.session_state.active_session_id, prompt)
                
            # Display response
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(response_msg.get("text", "Error: No response returned."))
            st.rerun()

    # ------------------ Tab 2: Structured Dashboard ------------------
    with tab2:
        st.markdown("### Household Logistics Dashboard")
        st.caption("Interact directly with structured records managed by your Concierge.")

        skill_tab1, skill_tab2, skill_tab3 = st.tabs([
            "💊 Medication Tracker", 
            "🎉 Event & Guest List", 
            "🌿 Garden Schedule"
        ])

        # Sub-tab: Medication Tracker
        with skill_tab1:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### Tracked Medications")
                meds_res = client.list_medications()
                if meds_res.get("status") == "success":
                    meds = meds_res.get("medications", [])
                    if meds:
                        for m in meds:
                            # Glass card for each medication
                            active_str = "🟢 Active" if m["active"] else "⚪ Inactive"
                            taken_str = f"Last Dose: **{m['last_taken'].split('T')[0] if m['last_taken'] else 'Never'}**"
                            notes_str = f"Notes: *{m['last_taken_notes']}*" if m.get("last_taken_notes") else ""
                            
                            st.markdown(
                                f"""
                                <div class='glass-card'>
                                    <h5>💊 {m['name']} <span style='font-size:0.8rem; float:right;'>{active_str}</span></h5>
                                    <p style='margin:0.2rem 0;'>Dosage: <strong>{m['dosage']}</strong> | Schedule: <strong>{m['schedule']}</strong></p>
                                    <p style='margin:0.2rem 0; font-size:0.9rem; color:#94a3b8;'>{taken_str} {notes_str}</p>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            # Log dose button
                            btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                            with btn_col1:
                                if m["active"] and st.button("Log Dose Taken", key=f"take_med_{m['id']}"):
                                    res = client.take_medication(m["id"])
                                    st.success(res.get("message", "Logged successfully!"))
                                    st.rerun()
                            with btn_col2:
                                if m["active"] and st.button("Stop Tracking", key=f"stop_med_{m['id']}"):
                                    res = client.deactivate_medication(m["id"])
                                    st.success(res.get("message", "Stopped successfully!"))
                                    st.rerun()
                    else:
                        st.info("No medications are currently being tracked. Ask the agent: 'Track medication Advil 200mg daily'")
                else:
                    st.error(f"Failed to fetch medications: {meds_res.get('message')}")

            with col2:
                st.markdown("#### Quick Add Medication")
                with st.form("add_med_form", clear_on_submit=True):
                    med_name = st.text_input("Medication Name")
                    med_dose = st.text_input("Dosage", placeholder="e.g. 500mg, 1 tablet")
                    med_sched = st.text_input("Schedule/Frequency", placeholder="e.g. daily, every 12 hours")
                    if st.form_submit_button("Track Medication", use_container_width=True):
                        if med_name and med_dose and med_sched:
                            res = client.add_medication(med_name, med_dose, med_sched)
                            if res.get("status") == "success":
                                st.success(res.get("message"))
                                st.rerun()
                            else:
                                st.error(res.get("message", "Error adding medication"))
                        else:
                            st.warning("Please fill in all fields")

        # Sub-tab: Guest List
        with skill_tab2:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### Planned Events & Guests")
                events_res = client.list_events()
                if events_res.get("status") == "success":
                    events = events_res.get("events", [])
                    if events:
                        for ev in events:
                            event_date_fmt = datetime.fromisoformat(ev["event_date"]).strftime('%B %d, %Y')
                            
                            st.markdown(
                                f"""
                                <div class='glass-card'>
                                    <h5>🎉 {ev['event_name']}</h5>
                                    <p style='margin:0.2rem 0; font-size:0.9rem; color:#94a3b8;'>Date: <strong>{event_date_fmt}</strong></p>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            # Show guests table
                            guests = ev.get("guests", [])
                            if guests:
                                # Convert guest list into pandas dataframe or styled layout
                                rsvp_counts = {"Attending": 0, "Declined": 0, "Pending": 0}
                                for g in guests:
                                    status = g["status"]
                                    if status in rsvp_counts:
                                        rsvp_counts[status] += 1
                                
                                st.write(f"Invite Status: **{rsvp_counts['Attending']} Attending** | **{rsvp_counts['Declined']} Declined** | **{rsvp_counts['Pending']} Pending**")
                                
                                for g in guests:
                                    badge_color = "#34d399" if g["status"] == "Attending" else "#f87171" if g["status"] == "Declined" else "#fbbf24"
                                    g_col1, g_col2, g_col3 = st.columns([2, 1, 1])
                                    g_col1.write(f"👤 {g['name']} ({g['email'] or 'No Email'})")
                                    g_col2.markdown(f"<span style='color:{badge_color}; font-weight:bold;'>{g['status']}</span>", unsafe_allow_html=True)
                                    
                                    # RSVP change buttons
                                    with g_col3:
                                        rsvp_choice = st.selectbox("Update", ["Update RSVP", "Attending", "Declined", "Pending"], key=f"rsvp_sel_{g['id']}", label_visibility="collapsed")
                                        if rsvp_choice != "Update RSVP":
                                            client.update_guest_rsvp(ev["id"], g["name"], rsvp_choice)
                                            st.rerun()
                            else:
                                st.caption("No guests added yet. Invite guests to build the list.")
                            st.markdown("---")
                    else:
                        st.info("No events scheduled. Ask the agent: 'Create event Summer Party on 2026-08-10'")
                else:
                    st.error(f"Failed to fetch events: {events_res.get('message')}")

            with col2:
                st.markdown("#### Create Event & Invite Guests")
                with st.expander("Create New Event", expanded=True):
                    with st.form("create_event_form", clear_on_submit=True):
                        ev_name = st.text_input("Event Name")
                        ev_date = st.date_input("Event Date", value=datetime.now())
                        if st.form_submit_button("Create Event", use_container_width=True):
                            if ev_name:
                                res = client.create_event(ev_name, ev_date.isoformat())
                                if res.get("status") == "success":
                                    st.success(res.get("message"))
                                    st.rerun()
                                else:
                                    st.error(res.get("message", "Error creating event"))
                            else:
                                st.warning("Event Name is required")
                                
                with st.expander("Add Guest to Invite List", expanded=True):
                    events_list = []
                    events_id_map = {}
                    if events_res.get("status") == "success":
                        for ev in events_res.get("events", []):
                            name_val = ev["event_name"]
                            events_list.append(name_val)
                            events_id_map[name_val] = ev["id"]
                            
                    if events_list:
                        with st.form("add_guest_form", clear_on_submit=True):
                            selected_ev = st.selectbox("Select Event", events_list)
                            guest_n = st.text_input("Guest Name")
                            guest_e = st.text_input("Guest Email (Optional)")
                            guest_status = st.selectbox("Initial Invite Status", ["Pending", "Attending", "Declined"])
                            
                            if st.form_submit_button("Add Guest", use_container_width=True):
                                if guest_n:
                                    ev_id = events_id_map[selected_ev]
                                    res = client.add_guest(ev_id, guest_n, guest_e, guest_status)
                                    if res.get("status") == "success":
                                        st.success(res.get("message"))
                                        st.rerun()
                                    else:
                                        st.error(res.get("message"))
                                else:
                                    st.warning("Guest Name is required")
                    else:
                        st.caption("Create an event first to invite guests.")

        # Sub-tab: Garden Schedule
        with skill_tab3:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### Garden Schedule & Tasks")
                garden_res = client.list_garden_tasks()
                if garden_res.get("status") == "success":
                    tasks = garden_res.get("tasks", [])
                    if tasks:
                        # Split completed vs pending
                        pending_tasks = [t for t in tasks if not t["completed"]]
                        completed_tasks = [t for t in tasks if t["completed"]]
                        
                        st.write(f"Pending tasks: **{len(pending_tasks)}** | Completed: **{len(completed_tasks)}**")
                        
                        if pending_tasks:
                            st.markdown("##### 📅 Due/Upcoming Tasks")
                            # Sort by due date
                            pending_tasks.sort(key=lambda x: x["due_date"])
                            for t in pending_tasks:
                                due_dt = datetime.fromisoformat(t["due_date"])
                                due_fmt = due_dt.strftime('%B %d, %Y')
                                days_left = (due_dt.date() - datetime.now().date()).days
                                
                                due_color = "#f87171" if days_left < 0 else "#fbbf24" if days_left == 0 else "#94a3b8"
                                status_text = "OVERDUE" if days_left < 0 else "TODAY" if days_left == 0 else f"in {days_left} days"
                                
                                g_col1, g_col2 = st.columns([3, 1])
                                g_col1.markdown(
                                    f"""
                                    <div class='glass-card' style='margin-bottom:0.5rem; padding:0.8rem;'>
                                        <strong>{t['task_type']} {t['plant_name']}</strong> <br/>
                                        <span style='font-size:0.8rem; color:{due_color};'>Due: {due_fmt} ({status_text})</span>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                                with g_col2:
                                    st.write("") # padding
                                    if st.button("Mark Complete", key=f"comp_task_{t['id']}", use_container_width=True):
                                        res = client.complete_garden_task(t["id"])
                                        st.success(res.get("message", "Task completed!"))
                                        st.rerun()
                        
                        if completed_tasks:
                            st.write("")
                            with st.expander("Completed Tasks History"):
                                for t in completed_tasks:
                                    st.write(f"✅ {t['task_type']} {t['plant_name']} (Scheduled for {t['due_date'].split('T')[0]})")
                    else:
                        st.info("No garden tasks scheduled. Ask the agent: 'Water the Roses tomorrow'")
                else:
                    st.error(f"Failed to fetch garden tasks: {garden_res.get('message')}")

            with col2:
                st.markdown("#### Schedule Garden Work")
                with st.form("add_garden_form", clear_on_submit=True):
                    plant_n = st.text_input("Plant / Area Name", placeholder="e.g. Tomatoes, Front Lawn")
                    task_t = st.selectbox("Task Type", ["Water", "Prune", "Harvest", "Plant", "Fertilize", "Weed"])
                    due_d = st.date_input("Scheduled Date", value=datetime.now())
                    
                    if st.form_submit_button("Schedule Task", use_container_width=True):
                        if plant_n:
                            res = client.add_garden_task(plant_n, task_t, due_d.isoformat())
                            if res.get("status") == "success":
                                st.success(res.get("message"))
                                st.rerun()
                            else:
                                st.error(res.get("message"))
                        else:
                            st.warning("Plant Name is required")

    # ------------------ Tab 3: Security & Privacy Center ------------------
    with tab3:
        st.markdown("### Privacy, Safety, and Transparency Dashboard")
        st.caption("Under the hood: View what the agent knows, check data portability, and audit security records.")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 🔍 Active Data & Encryption Status")
            trans_res = client.get_transparency_summary()
            if "household_info" in trans_res:
                info = trans_res["household_info"]
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <h5>Household Name: {info['name']}</h5>
                        <p style='margin:0.2rem 0;'>Associated Accounts: <code>{', '.join(info['created_users'])}</code></p>
                        <p style='margin:0.2rem 0; color:#34d399;'>🛡️ AES-256 field-level encryption active using household-scoped keys derived via PBKDF2.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Show database point tallies
                points = trans_res.get("data_points", {})
                st.write("**Stored Entities Breakdown:**")
                st.write(f"- Conversations History count: **{points.get('conversations', 0)}** messages streams")
                st.write(f"- Medication trackers active: **{points.get('medication_records', 0)}** rows")
                st.write(f"- Event invitees: **{points.get('invitees', 0)}** guest rows")
                st.write(f"- Garden schedules: **{points.get('garden_schedules', 0)}** tasks")
                
            else:
                st.warning("Unable to fetch transparency reports.")

            st.markdown("#### 💾 Data Portability & Rights")
            st.write("Retrieve your stored files or permanently erase your digital trace instantly.")
            
            # Export data button
            if st.button("Export Decrypted Data (JSON)", use_container_width=True):
                export_res = client.export_data()
                if "household_name" in export_res:
                    st.download_button(
                        label="Download Full Plain-JSON Export",
                        data=json.dumps(export_res, indent=2),
                        file_name=f"concierge_export_{st.session_state.username}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    st.success("JSON data generated successfully. Click download button above.")
                else:
                    st.error("Failed to generate export file.")

            # Purge data button
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("<p style='color:#f87171;'>⚠️ Danger Zone</p>", unsafe_allow_html=True)
            if st.button("Purge Household Account & Data Permanently", type="secondary", use_container_width=True):
                purge_res = client.purge_data()
                if purge_res.get("status") == "success":
                    st.success(purge_res.get("message"))
                    st.session_state.token = None
                    st.session_state.username = None
                    st.session_state.household_id = None
                    st.session_state.active_session_id = None
                    st.session_state.chat_history = []
                    st.rerun()
                else:
                    st.error(purge_res.get("message", "Failed to purge data"))

        with col2:
            st.markdown("#### 🛡️ Privacy & Access Audit Logs")
            st.caption("A real-time audit trail logs every system action that accesses decrypted personal data.")
            
            audits = client.get_audit_logs()
            if audits:
                # Format into a table
                audit_rows = []
                for a in audits:
                    dt = datetime.fromisoformat(a["timestamp"].split(".")[0]).strftime('%Y-%m-%d %H:%M:%S')
                    action_color = "#60a5fa" if "READ" in a["action"] else "#34d399" if "WRITE" in a["action"] else "#f87171"
                    
                    audit_rows.append({
                        "Time (UTC)": dt,
                        "Action": a["action"],
                        "Resource Target": a["target_table"]
                    })
                st.table(audit_rows[:15]) # Show last 15 audits
            else:
                st.info("No audit activities recorded yet.")
