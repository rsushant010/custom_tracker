# To run this app:
# 1. Save the code as 'app.py'.
# 2. Make sure you have the required libraries: pip install streamlit pandas plotly
# 3. Run from your terminal: streamlit run app.py

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime, timedelta, date, time

# --- DEFAULT TARGETS ---
# This dictionary is the single source of truth for default targets.
# Updated to separate Aptitude and Reasoning
DEFAULT_TARGETS = {
    "Math": (1.5, 9.0),
    "Strength of Materials": (1.0, 6.0),
    "Theory of Machines": (1.0, 6.0),
    "Machine Design": (1.0, 6.0),
    "Thermodynamics": (1.0, 6.0),
    "Fluid": (1.0, 6.0),
    "Heat Transfer": (1.0, 6.0),
    "Aptitude": (0.75, 4.5),
    "Reasoning": (0.75, 4.5),
    "P&I": (1.0, 6.0)
}

# --- NEW --- Default personal targets
DEFAULT_PERSONAL_TARGETS = {
    "wakeup": time(7, 45),
    "sleep": time(0, 40),
    "pushups": 50
}


# --- DATABASE SETUP ---

# Connect to the SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('study_tracker.db', check_same_thread=False)
c = conn.cursor()

# Function to create the necessary tables
def create_tables():
    """Creates all required tables in the database if they don't exist."""
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS study_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            log_date TEXT,
            subject TEXT,
            subsection TEXT,
            duration REAL,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_targets (
            username TEXT,
            subject TEXT,
            weekly_target REAL,
            PRIMARY KEY (username, subject),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_targets (
            username TEXT,
            subject TEXT,
            target_date TEXT,
            daily_target REAL,
            PRIMARY KEY (username, subject, target_date),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS revision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            log_date TEXT,
            subject TEXT,
            review_notes TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            log_date TEXT,
            wakeup_time TEXT,
            sleep_time TEXT,
            pushups INTEGER,
            UNIQUE(username, log_date),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_targets (
            username TEXT,
            target_date TEXT,
            wakeup_target TEXT,
            sleep_target TEXT,
            pushups_target INTEGER,
            PRIMARY KEY (username, target_date),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    conn.commit()

# --- PASSWORD HASHING ---

def make_hashes(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Checks if a password matches its hashed version."""
    if make_hashes(password) == hashed_text:
        return True
    return False



# --- USER AUTHENTICATION & DATA FUNCTIONS ---

def set_default_targets(username):
    """Sets the default study targets for a new user."""
    for subject, (daily, weekly) in DEFAULT_TARGETS.items():
        set_weekly_target(username, subject, weekly)

def add_user(username, password):
    """Adds a new user and sets their default targets."""
    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, make_hashes(password)))
    conn.commit()
    set_default_targets(username)

def login_user(username, password):
    """Logs in a user by checking their credentials."""
    c.execute('SELECT * FROM users WHERE username =?', (username,))
    data = c.fetchall()
    if data:
        return check_hashes(password, data[0][1])
    return False

def add_study_log(username, log_date, subject, subsection, duration):
    """Adds a new study log entry."""
    c.execute('INSERT INTO study_log(username, log_date, subject, subsection, duration) VALUES (?,?,?,?,?)',
              (username, log_date, subject, subsection, duration))
    conn.commit()

def get_user_logs(username):
    """Retrieves all study logs for a user."""
    c.execute('SELECT id, log_date, subject, subsection, duration FROM study_log WHERE username =?', (username,))
    return pd.DataFrame(c.fetchall(), columns=['ID', 'Date', 'Subject', 'Type', 'Duration'])

# --- NEW --- Functions to update and delete logs
def update_study_log(log_id, log_date, subject, subsection, duration):
    """Updates an existing study log entry."""
    c.execute('UPDATE study_log SET log_date=?, subject=?, subsection=?, duration=? WHERE id=?',
              (log_date, subject, subsection, duration, log_id))
    conn.commit()

def delete_study_log(log_id):
    """Deletes a study log entry by its ID."""
    c.execute('DELETE FROM study_log WHERE id=?', (log_id,))
    conn.commit()

def get_logs_by_date(username, date_str):
    """Retrieves study logs for a user on a specific date."""
    c.execute('SELECT subject, subsection, duration FROM study_log WHERE username =? AND log_date =?', (username, date_str))
    return pd.DataFrame(c.fetchall(), columns=['Subject', 'Type', 'Duration'])

def set_weekly_target(username, subject, weekly_target):
    """Sets or updates a weekly study target."""
    c.execute('INSERT OR REPLACE INTO weekly_targets (username, subject, weekly_target) VALUES (?, ?, ?)',
              (username, subject, weekly_target))
    conn.commit()

def get_weekly_targets(username):
    """Retrieves all weekly targets for a user."""
    c.execute('SELECT subject, weekly_target FROM weekly_targets WHERE username =?', (username,))
    df = pd.DataFrame(c.fetchall(), columns=['Subject', 'Weekly Target'])
    for subject, (_, weekly) in DEFAULT_TARGETS.items():
        if subject not in df['Subject'].values:
            df.loc[len(df)] = {'Subject': subject, 'Weekly Target': weekly}
    return df


def set_daily_target(username, subject, target_date, daily_target):
    """Sets or updates a daily study target."""
    c.execute('INSERT OR REPLACE INTO daily_targets (username, subject, target_date, daily_target) VALUES (?, ?, ?, ?)',
              (username, subject, target_date, daily_target))
    conn.commit()

def get_daily_targets_for_date(username, target_date):
    """Retrieves all daily targets for a user for a specific date, falling back to global defaults."""
    c.execute('SELECT subject, daily_target FROM daily_targets WHERE username =? AND target_date =?', (username, target_date))
    df = pd.DataFrame(c.fetchall(), columns=['Subject', 'Daily Target'])
    for subject, (daily, _) in DEFAULT_TARGETS.items():
        if subject not in df['Subject'].values:
            df.loc[len(df)] = {'Subject': subject, 'Daily Target': daily}
    return df


def add_revision_log(username, log_date, subject, notes):
    """Adds a new revision log entry."""
    c.execute('INSERT INTO revision_log (username, log_date, subject, review_notes) VALUES (?,?,?,?)',
              (username, log_date, subject, notes))
    conn.commit()

def get_revision_logs_by_date(username, date_str):
    """Retrievis revision logs for a user on a specific date."""
    c.execute('SELECT subject, review_notes FROM revision_log WHERE username =? AND log_date =?', (username, date_str))
    return pd.DataFrame(c.fetchall(), columns=['Subject', 'Review Notes'])

def add_personal_log(username, log_date, wakeup_time, sleep_time, pushups):
    """Adds or updates a personal log entry for a specific date."""
    c.execute('INSERT OR REPLACE INTO personal_log (username, log_date, wakeup_time, sleep_time, pushups) VALUES (?,?,?,?,?)',
              (username, log_date, wakeup_time, sleep_time, pushups))
    conn.commit()

def get_personal_log_by_date(username, date_str):
    """Retrieves personal log for a user on a specific date."""
    c.execute('SELECT wakeup_time, sleep_time, pushups FROM personal_log WHERE username =? AND log_date =?', (username, date_str))
    data = c.fetchone()
    if data:
        return {"wakeup": data[0], "sleep": data[1], "pushups": data[2]}
    return None

def set_personal_target(username, target_date, wakeup_target, sleep_target, pushups_target):
    """Sets or updates personal targets for a specific date."""
    c.execute('INSERT OR REPLACE INTO personal_targets (username, target_date, wakeup_target, sleep_target, pushups_target) VALUES (?,?,?,?,?)',
              (username, target_date, wakeup_target, sleep_target, pushups_target))
    conn.commit()

def get_personal_targets_for_date(username, target_date_str):
    """Retrieves personal targets for a date, falling back to defaults."""
    c.execute('SELECT wakeup_target, sleep_target, pushups_target FROM personal_targets WHERE username =? AND target_date =?', (username, target_date_str))
    data = c.fetchone()
    if data:
        return {
            "wakeup": datetime.strptime(data[0], '%H:%M').time(),
            "sleep": datetime.strptime(data[1], '%H:%M').time(),
            "pushups": data[2]
        }
    return DEFAULT_PERSONAL_TARGETS

def format_time_delta(delta):
    """Formats a timedelta object into a readable string like '+15m' or '-1h 5m'."""
    if delta.total_seconds() == 0:
        return "On time"
    sign = "+" if delta.total_seconds() < 0 else "-"
    delta = abs(delta)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{sign}{hours}h {minutes}m"
    return f"{sign}{minutes}m"

# --- NEW FEATURE --- Function to calculate study streak
def calculate_streak(username):
    """Calculates the user's current study streak."""
    c.execute("SELECT DISTINCT log_date FROM study_log WHERE username=? ORDER BY log_date DESC", (username,))
    dates = [datetime.strptime(d[0], "%Y-%m-%d").date() for d in c.fetchall()]
    if not dates:
        return 0
    
    streak = 0
    today = date.today()
    
    # Check if today is in the log dates
    if today in dates:
        streak += 1
        yesterday = today - timedelta(days=1)
        while yesterday in dates:
            streak += 1
            yesterday -= timedelta(days=1)
    # Check if yesterday is in the log dates (if today is not)
    elif (today - timedelta(days=1)) in dates:
        streak = 1
        yesterday = today - timedelta(days=2)
        while yesterday in dates:
            streak += 1
            yesterday -= timedelta(days=1)
            
    return streak

# --- PLOTTING FUNCTION ---
def generate_pie_chart(df, title):
    """Generates a Plotly pie chart with detailed labels."""
    if not df.empty and df['Duration'].sum() > 0:
        df_grouped = df.groupby('Subject')['Duration'].sum().reset_index()
        fig = px.pie(df_grouped, values='Duration', names='Subject', title=title, hole=0.4)
        fig.update_traces(
            texttemplate='%{label}<br>%{value:.1f} hrs<br>(%{percent})',
            textposition='inside',
            pull=[0.05] * len(df_grouped)
        )
        fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')
        return fig
    return None

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Advanced Study Tracker", layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
        <style>
            .block-container { padding-top: 1.5rem; }
            div[data-testid="stRadio"] > label { font-size: 1.1em; font-weight: 600; }
            div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { font-size: 1em; }
        </style>
    """, unsafe_allow_html=True)

    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if 'username' not in st.session_state: st.session_state['username'] = ""

    st.sidebar.header("👤 User Authentication")
    choice = st.sidebar.selectbox("Menu", ["Login", "SignUp"])

    if choice == "Login":
        if not st.session_state['logged_in']:
            username = st.sidebar.text_input("Username", key="login_user")
            password = st.sidebar.text_input("Password", type='password', key="login_pass")
            if st.sidebar.button("Login"):
                create_tables()
                if login_user(username, password):
                    st.session_state.update({'logged_in': True, 'username': username})
                    st.rerun()
                else:
                    st.sidebar.warning("Incorrect Username/Password")
        else:
            st.sidebar.success(f"Logged In as {st.session_state['username']}")
            if st.sidebar.button("Logout"):
                st.session_state.update({'logged_in': False, 'username': ""})
                st.rerun()
    elif choice == "SignUp":
        st.sidebar.subheader("Create New Account")
        new_user = st.sidebar.text_input("Username", key="signup_user")
        new_password = st.sidebar.text_input("Password", type='password', key="signup_pass")
        if st.sidebar.button("SignUp"):
            create_tables()
            try:
                add_user(new_user, new_password)
                st.sidebar.success("Account created! Please login.")
            except sqlite3.IntegrityError:
                st.sidebar.warning("Username already exists.")
            except Exception as e:
                st.sidebar.error(f"An error occurred: {e}")

    if st.session_state['logged_in']:
        engineering_subjects = ["Strength of Materials", "Theory of Machines", "Fluid", "Thermodynamics", "P&I", "Heat Transfer", "Machine Design"]
        basic_subjects = ["Math", "Aptitude", "Reasoning"]
        all_subjects = sorted(engineering_subjects + basic_subjects)

        st.sidebar.header("📝 Log New Session")
        subject_category = st.sidebar.selectbox("Category", ["Engineering", "Basic"])

        with st.sidebar.form(key='study_form', clear_on_submit=True):
            subject_options = engineering_subjects if subject_category == "Engineering" else basic_subjects
            subject = st.selectbox("Subject", subject_options)
            log_date_input = st.date_input("Date", datetime.now())
            subsection = st.radio("Type", ["Theory", "Numerical"], horizontal=True)
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=10.0, step=0.5, format="%.1f")

            if st.form_submit_button(label='Log Study Session'):
                add_study_log(st.session_state['username'], log_date_input.strftime("%Y-%m-%d"), subject, subsection, duration)
                st.sidebar.success(f"Logged {duration} hrs for {subject}.")
                st.rerun()

        st.header(f"Welcome back, {st.session_state['username']}! 👋")
        st.markdown("---")

        tabs = st.tabs(["🚀 Dashboard", "📊 Daily Analysis", "🎯 Target Analysis", "✍️ Set Targets", "💡 Recommendations", "🗓️ Weekly Revision", "💪 Personal", "📚 Full History & Edit"])
        df_all = get_user_logs(st.session_state['username'])
        if not df_all.empty:
            df_all['Date'] = pd.to_datetime(df_all['Date'])

        with tabs[0]: # Dashboard
            st.subheader("Your Study Dashboard")
            if not df_all.empty:
                total_hours = df_all['Duration'].sum()
                top_subject = df_all.groupby('Subject')['Duration'].sum().idxmax()
                today = date.today()
                start_of_week = today - timedelta(days=today.weekday())
                hours_this_week = df_all[df_all['Date'].dt.date >= start_of_week]['Duration'].sum()
                
                # --- NEW FEATURE --- Calculate Streak
                current_streak = calculate_streak(st.session_state['username'])

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Hours Studied 🕒", f"{total_hours:.2f} hrs")
                col2.metric("Top Subject 🏆", top_subject)
                col3.metric("Hours This Week 🗓️", f"{hours_this_week:.2f} hrs")
                col4.metric("Current Study Streak 🔥", f"{current_streak} Days")
                
                st.markdown("---")
                
                # --- NEW FEATURE --- 30-Day Trend Chart
                st.subheader("📈 Your 30-Day Study Trend")
                thirty_days_ago = date.today() - timedelta(days=30)
                df_last_30_days = df_all[df_all['Date'].dt.date >= thirty_days_ago]
                df_trend = df_last_30_days.groupby(df_last_30_days['Date'].dt.date)['Duration'].sum().reset_index()
                df_trend = df_trend.rename(columns={'Date': 'Date', 'Duration': 'Hours Studied'})
                st.line_chart(df_trend, x='Date', y='Hours Studied')

                st.markdown("---")
                st.subheader("📊 Overall Analysis at a Glance")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    fig = generate_pie_chart(df_all, "Overall Distribution")
                    if fig: st.plotly_chart(fig, use_container_width=True)
                with col_b:
                    fig = generate_pie_chart(df_all[df_all['Type'] == 'Theory'], "Theory Distribution")
                    if fig: st.plotly_chart(fig, use_container_width=True)
                with col_c:
                    fig = generate_pie_chart(df_all[df_all['Type'] == 'Numerical'], "Numerical Distribution")
            else:
                st.info("Log your first study session to see your dashboard!")

        with tabs[1]: # Daily Analysis
            st.subheader("Day-wise Analysis")
            analysis_date = st.date_input("Select a date to analyze", datetime.now(), key="daily_date")
            df_daily = get_logs_by_date(st.session_state['username'], analysis_date.strftime("%Y-%m-%d"))
            if not df_daily.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    fig = generate_pie_chart(df_daily, f"Overall ({analysis_date.strftime('%b %d')})")
                    if fig: st.plotly_chart(fig, use_container_width=True)
                with col2:
                    fig = generate_pie_chart(df_daily[df_daily['Type'] == 'Theory'], "Theory")
                    if fig: st.plotly_chart(fig, use_container_width=True)
                with col3:
                    fig = generate_pie_chart(df_daily[df_daily['Type'] == 'Numerical'], "Numerical")
                    if fig: st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No study data found for {analysis_date.strftime('%Y-%m-%d')}.")

        with tabs[2]: # Target Analysis
            st.subheader("Target vs. Actual Performance")
            analysis_date_daily = st.date_input("Select a date for daily target analysis", datetime.now(), key="target_date")
            df_daily_targets = get_daily_targets_for_date(st.session_state['username'], analysis_date_daily.strftime("%Y-%m-%d"))
            df_day_logs = get_logs_by_date(st.session_state['username'], analysis_date_daily.strftime("%Y-%m-%d")).groupby('Subject')['Duration'].sum().reset_index()
            df_day_analysis = pd.merge(df_daily_targets, df_day_logs, on="Subject", how="left").fillna(0).rename(columns={'Duration': 'Actual Hours'})
            df_melted_daily = df_day_analysis.melt(id_vars='Subject', value_vars=['Daily Target', 'Actual Hours'], var_name='Metric', value_name='Hours')
            fig_daily = px.bar(df_melted_daily, x='Subject', y='Hours', color='Metric', barmode='group', title=f"Daily Target Progress ({analysis_date_daily.strftime('%b %d')})", text_auto='.1f')
            fig_daily.update_traces(textposition='outside')
            st.plotly_chart(fig_daily, use_container_width=True)

            st.markdown("---")
            weekly_analysis_date = st.date_input("Select a date to view its week's progress", datetime.now(), key="weekly_target_date")
            start_of_week = weekly_analysis_date - timedelta(days=weekly_analysis_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            df_in_week = df_all[(df_all['Date'].dt.date >= start_of_week) & (df_all['Date'].dt.date <= end_of_week)] if not df_all.empty else pd.DataFrame(columns=df_all.columns)
            df_weekly_logs = df_in_week.groupby('Subject')['Duration'].sum().reset_index()
            df_weekly_targets = get_weekly_targets(st.session_state['username'])
            df_weekly_analysis = pd.merge(df_weekly_targets, df_weekly_logs, on="Subject", how="left").fillna(0).rename(columns={'Duration': 'Actual Hours'})
            df_melted_weekly = df_weekly_analysis.melt(id_vars='Subject', value_vars=['Weekly Target', 'Actual Hours'], var_name='Metric', value_name='Hours')
            fig_weekly = px.bar(df_melted_weekly, x='Subject', y='Hours', color='Metric', barmode='group', title=f"Weekly Target Progress ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')})", text_auto='.1f')
            fig_weekly.update_traces(textposition='outside')
            st.plotly_chart(fig_weekly, use_container_width=True)

        with tabs[3]: # Set Targets
            st.subheader("Set Your Study Targets")
            target_date_selector = st.date_input("Select a date to set daily targets", datetime.now(), key="set_target_date")
            df_daily_targets = get_daily_targets_for_date(st.session_state['username'], target_date_selector.strftime("%Y-%m-%d"))
            daily_targets_dict = {row['Subject']: row['Daily Target'] for _, row in df_daily_targets.iterrows()}
            df_weekly_targets = get_weekly_targets(st.session_state['username'])
            weekly_targets_dict = {row['Subject']: row['Weekly Target'] for _, row in df_weekly_targets.iterrows()}

            with st.form("targets_form"):
                st.markdown(f"**Daily Targets for {target_date_selector.strftime('%Y-%m-%d')}**")
                new_daily_targets = {}
                col1, col2 = st.columns(2)
                subjects_col1, subjects_col2 = all_subjects[::2], all_subjects[1::2]
                with col1:
                    for subject in subjects_col1:
                        default_daily = daily_targets_dict.get(subject, DEFAULT_TARGETS.get(subject, (1.0, 5.0))[0])
                        new_daily_targets[subject] = st.number_input(f"{subject}", 0.0, value=default_daily, key=f"d_{subject}", step=0.5)
                with col2:
                    for subject in subjects_col2:
                        default_daily = daily_targets_dict.get(subject, DEFAULT_TARGETS.get(subject, (1.0, 5.0))[0])
                        new_daily_targets[subject] = st.number_input(f"{subject}", 0.0, value=default_daily, key=f"d_{subject}_2", step=0.5)

                st.markdown("---")
                st.markdown("**Overall Weekly Targets**")
                new_weekly_targets = {}
                w_col1, w_col2 = st.columns(2)
                with w_col1:
                    for subject in subjects_col1:
                        default_weekly = weekly_targets_dict.get(subject, DEFAULT_TARGETS.get(subject, (1.0, 5.0))[1])
                        new_weekly_targets[subject] = st.number_input(f"{subject}", 0.0, value=default_weekly, key=f"w_{subject}", step=0.5)
                with w_col2:
                    for subject in subjects_col2:
                        default_weekly = weekly_targets_dict.get(subject, DEFAULT_TARGETS.get(subject, (1.0, 5.0))[1])
                        new_weekly_targets[subject] = st.number_input(f"{subject}", 0.0, value=default_weekly, key=f"w_{subject}_2", step=0.5)

                if st.form_submit_button("Save All Targets"):
                    for subject, daily_target in new_daily_targets.items():
                        set_daily_target(st.session_state['username'], subject, target_date_selector.strftime("%Y-%m-%d"), daily_target)
                    for subject, weekly_target in new_weekly_targets.items():
                        set_weekly_target(st.session_state['username'], subject, weekly_target)
                    st.success("Your targets have been saved!")
                    st.rerun()

        with tabs[4]: # Recommendations
            st.subheader("💡 Personalized Study Recommendations")
            if not df_all.empty:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🎯 Weekly Target Adherence")
                    start_of_week_dt = date.today() - timedelta(days=date.today().weekday())
                    df_weekly_logs = df_all[df_all['Date'].dt.date >= start_of_week_dt].groupby('Subject')['Duration'].sum().reset_index()
                    df_weekly_targets = get_weekly_targets(st.session_state['username'])
                    df_weekly_analysis = pd.merge(df_weekly_targets, df_weekly_logs, on="Subject", how="left").fillna(0)
                    df_weekly_analysis['Gap'] = df_weekly_analysis['Weekly Target'] - df_weekly_analysis['Duration']
                    behind_subjects = df_weekly_analysis[df_weekly_analysis['Gap'] > 0].sort_values(by='Gap', ascending=False)
                    if not behind_subjects.empty:
                        st.warning("Focus Areas for This Week:")
                        for _, row in behind_subjects.head(3).iterrows():
                            st.write(f"- **{row['Subject']}**: You're **{row['Gap']:.1f} hours** behind your weekly goal.")
                    else:
                        st.success("Excellent! You're on track with all weekly targets!")
                with col2:
                    st.markdown("#### 🗓️ Consistency Check")
                    seven_days_ago = date.today() - timedelta(days=7)
                    days_studied = df_all[df_all['Date'].dt.date >= seven_days_ago]['Date'].dt.date.nunique()
                    st.metric(label="Study Days (Last 7 Days)", value=f"{days_studied} / 7")
                    if days_studied >= 5:
                        st.success("Great consistency! Keep up the momentum.")
                    else:
                        st.info("Try shorter, daily sessions to build a stronger habit.")

        with tabs[5]: # Weekly Revision
            st.subheader("🗓️ Weekly Revision")
            is_sunday = datetime.now().weekday() == 6
            if is_sunday: st.success("It's Sunday! A perfect day for your weekly revision.")
            with st.form("revision_form"):
                revision_date = st.date_input("Revision Date", datetime.now(), disabled=not is_sunday)
                revision_data = {}
                for subject in all_subjects:
                    revised = st.checkbox(subject, key=f"rev_{subject}")
                    notes = st.text_area("Review Notes", key=f"notes_{subject}", height=50, placeholder=f"Key takeaways for {subject}...")
                    if revised: revision_data[subject] = notes
                if st.form_submit_button("Save Revision Log"):
                    if revision_data:
                        for subject, notes in revision_data.items():
                            add_revision_log(st.session_state['username'], revision_date.strftime("%Y-%m-%d"), subject, notes)
                        st.success("Revision log saved successfully!")
                    else:
                        st.warning("Please select at least one subject you revised.")
            st.markdown("---")
            st.markdown("#### Past Revision Logs")
            past_sunday = st.date_input("Select a past Sunday to review", date.today() - timedelta(days=date.today().weekday() + 1))
            if past_sunday.weekday() != 6:
                st.error("Please select a Sunday.")
            else:
                df_revision = get_revision_logs_by_date(st.session_state['username'], past_sunday.strftime("%Y-%m-%d"))
                if not df_revision.empty:
                    st.dataframe(df_revision, use_container_width=True)
                else:
                    st.info(f"No revision log found for {past_sunday.strftime('%Y-%m-%d')}.")

        with tabs[6]: # Personal
            st.subheader("💪 Personal Wellness Tracker")
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("Log Your Daily Metrics", expanded=True):
                    with st.form("personal_log_form", clear_on_submit=False):
                        p_log_date = st.date_input("Date", key="p_log_date")
                        p_wakeup_time = st.time_input("Wake Up Time", time(8, 0))
                        p_sleep_time = st.time_input("Sleep Time", time(0, 0))
                        p_pushups = st.number_input("Number of Pushups", min_value=0, step=1)
                        if st.form_submit_button("Log Metrics"):
                            add_personal_log(st.session_state['username'], p_log_date.strftime("%Y-%m-%d"), p_wakeup_time.strftime("%H:%M"), p_sleep_time.strftime("%H:%M"), p_pushups)
                            st.success(f"Personal metrics logged for {p_log_date.strftime('%Y-%m-%d')}!")
                            st.rerun()
            with col2:
                st.markdown("#### Analysis Report")
                analysis_p_date = st.date_input("Select Date for Analysis", key="p_analysis_date")
                actuals = get_personal_log_by_date(st.session_state['username'], analysis_p_date.strftime("%Y-%m-%d"))
                targets = get_personal_targets_for_date(st.session_state['username'], analysis_p_date.strftime("%Y-%m-%d"))
                if actuals:
                    m_col1, m_col2, m_col3 = st.columns(3)
                    actual_wakeup = datetime.strptime(actuals['wakeup'], '%H:%M').time()
                    target_wakeup = targets['wakeup']
                    delta_wakeup = datetime.combine(date.min, target_wakeup) - datetime.combine(date.min, actual_wakeup)
                    m_col1.metric(label=f"Wake Up (T: {target_wakeup.strftime('%H:%M')})", value=actual_wakeup.strftime('%H:%M'), delta=format_time_delta(delta_wakeup))
                    actual_sleep = datetime.strptime(actuals['sleep'], '%H:%M').time()
                    target_sleep = targets['sleep']
                    delta_sleep = datetime.combine(date.min, target_sleep) - datetime.combine(date.min, actual_sleep)
                    m_col2.metric(label=f"Sleep (T: {target_sleep.strftime('%H:%M')})", value=actual_sleep.strftime('%H:%M'), delta=format_time_delta(delta_sleep))
                    actual_pushups = actuals['pushups']
                    target_pushups = targets['pushups']
                    delta_pushups = actual_pushups - target_pushups
                    m_col3.metric(label=f"Pushups (T: {target_pushups})", value=str(actual_pushups), delta=f"{delta_pushups:+}")
                else:
                    st.info(f"No personal data logged for {analysis_p_date.strftime('%Y-%m-%d')}.")
            st.markdown("---")
            with st.expander("Set & Visualize Daily Personal Targets"):
                with st.form("personal_target_form"):
                    p_target_date = st.date_input("Select date to set targets for", key="p_target_date")
                    current_targets = get_personal_targets_for_date(st.session_state['username'], p_target_date.strftime("%Y-%m-%d"))
                    st.markdown("##### Adjust Your Goals")
                    t_col1, t_col2 = st.columns(2)
                    with t_col1:
                        t_wakeup = st.time_input("Wake Up Target", value=current_targets['wakeup'])
                    with t_col2:
                        t_sleep = st.time_input("Sleep Target", value=current_targets['sleep'])
                    t_pushups = st.slider("Pushups Target", min_value=0, max_value=100, step=5, value=current_targets['pushups'])
                    if st.form_submit_button("Save Personal Targets"):
                        set_personal_target(st.session_state['username'], p_target_date.strftime("%Y-%m-%d"), t_wakeup.strftime("%H:%M"), t_sleep.strftime("%H:%M"), t_pushups)
                        st.success(f"Personal targets saved for {p_target_date.strftime('%Y-%m-%d')}!")
                        st.rerun()

        with tabs[7]: # Full History & Edit
            st.subheader("📚 Full Study History & Edit Logs")
            if not df_all.empty:
                st.dataframe(df_all[['Date', 'Subject', 'Type', 'Duration']].sort_values(by='Date', ascending=False), use_container_width=True)
                
                # --- NEW FEATURE --- Edit/Delete Functionality
                st.markdown("---")
                st.markdown("#### ✏️ Modify a Log Entry")
                
                # Create a list of log entries for the selectbox
                log_options = [f"{row['ID']}: {row['Date'].strftime('%Y-%m-%d')} - {row['Subject']} ({row['Duration']} hrs)" for index, row in df_all.iterrows()]
                selected_log_str = st.selectbox("Select a log to modify", [""] + log_options)

                if selected_log_str:
                    log_id_to_edit = int(selected_log_str.split(':')[0])
                    selected_log_data = df_all[df_all['ID'] == log_id_to_edit].iloc[0]

                    with st.form("edit_log_form"):
                        st.write(f"**Editing Log ID: {log_id_to_edit}**")
                        
                        edit_date = st.date_input("Date", value=selected_log_data['Date'].date())
                        
                        # Set index for subject and type dropdowns correctly
                        subject_index = all_subjects.index(selected_log_data['Subject']) if selected_log_data['Subject'] in all_subjects else 0
                        type_index = ["Theory", "Numerical"].index(selected_log_data['Type']) if selected_log_data['Type'] in ["Theory", "Numerical"] else 0

                        edit_subject = st.selectbox("Subject", all_subjects, index=subject_index)
                        edit_type = st.radio("Type", ["Theory", "Numerical"], index=type_index, horizontal=True)
                        edit_duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=10.0, step=0.5, value=selected_log_data['Duration'])

                        col_update, col_delete = st.columns(2)
                        with col_update:
                            if st.form_submit_button("Update Log"):
                                update_study_log(log_id_to_edit, edit_date.strftime("%Y-%m-%d"), edit_subject, edit_type, edit_duration)
                                st.success(f"Log ID {log_id_to_edit} has been updated.")
                                st.rerun()
                        
                        with col_delete:
                            confirm_delete = st.checkbox("Confirm Deletion", key="delete_confirm")
                            if st.form_submit_button("Delete Log"):
                                if confirm_delete:
                                    delete_study_log(log_id_to_edit)
                                    st.success(f"Log ID {log_id_to_edit} has been deleted.")
                                    st.rerun()
                                else:
                                    st.warning("Please check the confirmation box to delete.")

            else:
                st.info("Your study history is empty.")

    else:
        st.title("🎓 Advanced Study Task Manager")
        st.info("Please log in or sign up using the sidebar to access your dashboard.")
        st.image("https://placehold.co/800x400/E0F2F7/333333?text=Welcome+to+Your+Study+Tracker", use_container_width=True)

if __name__ == '__main__':
    main()
