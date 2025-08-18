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
import json

# --- DEFAULT TARGETS (Now used as suggestions) ---
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

DEFAULT_SUBJECTS_SETUP = {
    'Subject': ["Math", "Strength of Materials", "Theory of Machines", "Machine Design", "Thermodynamics", "Fluid", "Heat Transfer", "Aptitude", "Reasoning", "P&I"],
    'Category': ["Core", "Engineering", "Engineering", "Engineering", "Engineering", "Engineering", "Engineering", "Core", "Core", "Engineering"]
}

# --- UPDATED: Default personal goals setup with Units ---
DEFAULT_PERSONAL_SETUP = {
    'Metric': ['Wake Up', 'Sleep', 'Pushups', 'Reading'],
    'Type': ['Time', 'Time', 'Number', 'Number'],
    'Target': ['07:30', '23:30', '50', '20'],
    'Unit': ['', '', '', 'pages']
}


# --- DATABASE SETUP ---
conn = sqlite3.connect('study_tracker.db', check_same_thread=False)
c = conn.cursor()

def update_db_schema():
    """Updates the database schema with new columns if they don't exist to prevent errors."""
    try:
        c.execute("PRAGMA table_info(personal_targets)")
        columns = [col[1] for col in c.fetchall()]
        if 'unit' not in columns:
            c.execute("ALTER TABLE personal_targets ADD COLUMN unit TEXT")
            conn.commit()
    except sqlite3.Error:
        pass

def create_tables():
    """Creates all required tables in the database if they don't exist."""
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS study_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, log_date TEXT,
            subject TEXT, subsection TEXT, duration REAL,
            FOREIGN KEY(username) REFERENCES users(username)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_targets (
            username TEXT, subject TEXT, weekly_target REAL,
            PRIMARY KEY (username, subject), FOREIGN KEY(username) REFERENCES users(username)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_targets (
            username TEXT, subject TEXT, target_date TEXT, daily_target REAL,
            PRIMARY KEY (username, subject, target_date), FOREIGN KEY(username) REFERENCES users(username)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS revision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, log_date TEXT,
            subject TEXT, review_notes TEXT, FOREIGN KEY(username) REFERENCES users(username)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, log_date TEXT,
            metrics TEXT, -- Storing metrics as a JSON string
            UNIQUE(username, log_date), FOREIGN KEY(username) REFERENCES users(username)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_targets (
            username TEXT, metric_name TEXT, metric_type TEXT,
            target_value TEXT, unit TEXT,
            PRIMARY KEY (username, metric_name)
        )''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, subject TEXT, category TEXT,
            UNIQUE(username, subject)
        )''')
    conn.commit()

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- USER & SUBJECT DATA FUNCTIONS ---
def add_user(username, password):
    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, make_hashes(password)))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM users WHERE username =?', (username,))
    data = c.fetchall()
    return check_hashes(password, data[0][1]) if data else False

def add_user_subject(username, subject, category):
    c.execute('INSERT OR IGNORE INTO user_subjects (username, subject, category) VALUES (?,?,?)', (username, subject, category))
    conn.commit()

def get_user_subjects(username):
    c.execute('SELECT id, subject, category FROM user_subjects WHERE username =?', (username,))
    return pd.DataFrame(c.fetchall(), columns=['id', 'Subject', 'Category'])

def update_user_subject(subject_id, new_subject, new_category):
    c.execute('UPDATE user_subjects SET subject=?, category=? WHERE id=?', (new_subject, new_category, subject_id))
    conn.commit()

def delete_user_subject(subject_id):
    c.execute('DELETE FROM user_subjects WHERE id=?', (subject_id,))
    conn.commit()

def check_setup_complete(username):
    c.execute('SELECT COUNT(*) FROM user_subjects WHERE username=?', (username,))
    return c.fetchone()[0] > 0

# --- LOGGING & TARGET FUNCTIONS ---
def add_study_log(username, log_date, subject, subsection, duration):
    c.execute('INSERT INTO study_log(username, log_date, subject, subsection, duration) VALUES (?,?,?,?,?)',
              (username, log_date, subject, subsection, duration))
    conn.commit()

def get_user_logs(username):
    c.execute('SELECT id, log_date, subject, subsection, duration FROM study_log WHERE username =?', (username,))
    return pd.DataFrame(c.fetchall(), columns=['ID', 'Date', 'Subject', 'Type', 'Duration'])

def update_study_log(log_id, log_date, subject, subsection, duration):
    c.execute('UPDATE study_log SET log_date=?, subject=?, subsection=?, duration=? WHERE id=?',
              (log_date, subject, subsection, duration, log_id))
    conn.commit()

def delete_study_log(log_id):
    c.execute('DELETE FROM study_log WHERE id=?', (log_id,))
    conn.commit()

def get_logs_by_date(username, date_str):
    c.execute('SELECT subject, subsection, duration FROM study_log WHERE username =? AND log_date =?', (username, date_str))
    return pd.DataFrame(c.fetchall(), columns=['Subject', 'Type', 'Duration'])

def set_weekly_target(username, subject, weekly_target):
    c.execute('INSERT OR REPLACE INTO weekly_targets (username, subject, weekly_target) VALUES (?, ?, ?)',
              (username, subject, weekly_target))
    conn.commit()

def get_weekly_targets(username):
    user_subjects_df = get_user_subjects(username)
    if user_subjects_df.empty:
        return pd.DataFrame(columns=['Subject', 'Weekly Target'])
    c.execute('SELECT subject, weekly_target FROM weekly_targets WHERE username =?', (username,))
    df = pd.DataFrame(c.fetchall(), columns=['Subject', 'Weekly Target'])
    merged_df = pd.merge(user_subjects_df[['Subject']], df, on='Subject', how='left').fillna(0)
    return merged_df

def set_daily_target(username, subject, target_date, daily_target):
    c.execute('INSERT OR REPLACE INTO daily_targets (username, subject, target_date, daily_target) VALUES (?, ?, ?, ?)',
              (username, subject, target_date, daily_target))
    conn.commit()

def get_daily_targets_for_date(username, target_date):
    user_subjects_df = get_user_subjects(username)
    if user_subjects_df.empty:
        return pd.DataFrame(columns=['Subject', 'Daily Target'])
    c.execute('SELECT subject, daily_target FROM daily_targets WHERE username =? AND target_date =?', (username, target_date))
    df = pd.DataFrame(c.fetchall(), columns=['Subject', 'Daily Target'])
    merged_df = pd.merge(user_subjects_df[['Subject']], df, on='Subject', how='left').fillna(0)
    return merged_df

def add_revision_log(username, log_date, subject, notes):
    c.execute('INSERT INTO revision_log (username, log_date, subject, review_notes) VALUES (?,?,?,?)', (username, log_date, subject, notes))
    conn.commit()

def get_revision_logs_by_date(username, date_str):
    c.execute('SELECT subject, review_notes FROM revision_log WHERE username =? AND log_date =?', (username, date_str))
    return pd.DataFrame(c.fetchall(), columns=['Subject', 'Review Notes'])

def add_personal_log(username, log_date, metrics):
    for key, value in metrics.items():
        if isinstance(value, time):
            metrics[key] = value.strftime('%H:%M')
    c.execute('INSERT OR REPLACE INTO personal_log (username, log_date, metrics) VALUES (?,?,?)', (username, log_date, json.dumps(metrics)))
    conn.commit()

def get_personal_log_by_date(username, date_str):
    c.execute('SELECT metrics FROM personal_log WHERE username =? AND log_date =?', (username, date_str))
    data = c.fetchone()
    return json.loads(data[0]) if data else None

def get_all_personal_logs(username):
    c.execute('SELECT log_date, metrics FROM personal_log WHERE username =?', (username,))
    records = []
    for date_str, metrics_str in c.fetchall():
        metrics = json.loads(metrics_str)
        metrics['Date'] = date_str
        records.append(metrics)
    return pd.DataFrame(records)

def set_personal_target(username, metric_name, metric_type, target_value, unit):
    c.execute('INSERT OR REPLACE INTO personal_targets (username, metric_name, metric_type, target_value, unit) VALUES (?,?,?,?,?)', (username, metric_name, metric_type, str(target_value), unit))
    conn.commit()

def get_personal_targets(username):
    c.execute('SELECT metric_name, metric_type, target_value, unit FROM personal_targets WHERE username =?', (username,))
    targets = {}
    for row in c.fetchall():
        targets[row[0]] = {'type': row[1], 'target': row[2], 'unit': row[3]}
    return targets

def delete_personal_target(username, metric_name):
    c.execute('DELETE FROM personal_targets WHERE username =? AND metric_name =?', (username, metric_name))
    conn.commit()

def format_time_delta(delta):
    if delta.total_seconds() == 0: return "On time"
    sign = "+" if delta.total_seconds() < 0 else "-"
    delta = abs(delta)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours}h {minutes}m" if hours > 0 else f"{sign}{minutes}m"

def calculate_streak(username):
    c.execute("SELECT DISTINCT log_date FROM study_log WHERE username=? ORDER BY log_date DESC", (username,))
    dates = [datetime.strptime(d[0], "%Y-%m-%d").date() for d in c.fetchall()]
    if not dates: return 0
    streak, today = 0, date.today()
    if today in dates:
        streak, yesterday = 1, today - timedelta(days=1)
        while yesterday in dates:
            streak += 1; yesterday -= timedelta(days=1)
    elif (today - timedelta(days=1)) in dates:
        streak, yesterday = 1, today - timedelta(days=2)
        while yesterday in dates:
            streak += 1; yesterday -= timedelta(days=1)
    return streak

# --- PLOTTING FUNCTIONS ---
def generate_pie_chart(df, title, name_col='Subject'):
    if not df.empty and df['Duration'].sum() > 0:
        df_grouped = df.groupby(name_col)['Duration'].sum().reset_index()
        fig = px.pie(df_grouped, values='Duration', names=name_col, title=title, hole=0.4)
        fig.update_traces(texttemplate='%{label}<br>%{value:.1f} hrs<br>(%{percent})', textposition='inside', pull=[0.05] * len(df_grouped))
        fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide', showlegend=False)
        return fig
    return None

# --- ONBOARDING WIZARD ---
def run_setup_wizard(username):
    st.header("👋 Welcome! Let's set up your Study Tracker.")
    
    if 'setup_step' not in st.session_state:
        st.session_state.setup_step = 1

    if st.session_state.setup_step == 1:
        st.subheader("Step 1: Choose Your Setup Style")
        setup_choice = st.radio("How would you like to begin?", ("Start with a Recommended Setup (for Students)", "Start with a Custom Setup (from scratch)"), horizontal=True, key="setup_choice")
        if st.button("Next: Customize Subjects"):
            if setup_choice == "Start with a Recommended Setup (for Students)":
                df = pd.DataFrame(DEFAULT_SUBJECTS_SETUP)
                df['Daily Target (hrs)'] = df['Subject'].apply(lambda s: DEFAULT_TARGETS.get(s, (1.0, 5.0))[0])
                df['Weekly Target (hrs)'] = df['Subject'].apply(lambda s: DEFAULT_TARGETS.get(s, (1.0, 5.0))[1])
                st.session_state.setup_subjects = df
            else:
                st.session_state.setup_subjects = pd.DataFrame(columns=['Subject', 'Category', 'Daily Target (hrs)', 'Weekly Target (hrs)'])
            st.session_state.setup_step = 2
            st.rerun()

    if st.session_state.setup_step == 2:
        st.subheader("Step 2: Define Your Subjects & Set Initial Targets")
        st.info("You can edit the table below directly. Add your subjects, categorize them, and set your initial daily and weekly study goals.")
        st.data_editor(st.session_state.setup_subjects, key="subjects_editor", num_rows="dynamic", use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Setup Style"):
                st.session_state.setup_step = 1; st.rerun()
        with col2:
            if st.button("Next: Set Personal Goals ➡️"):
                st.session_state.setup_subjects = pd.DataFrame(st.session_state.subjects_editor)
                if not st.session_state.setup_subjects.empty:
                    st.session_state.setup_step = 3
                    if 'personal_metrics' not in st.session_state:
                        st.session_state.personal_metrics = pd.DataFrame(DEFAULT_PERSONAL_SETUP)
                    st.rerun()
                else:
                    st.warning("Please add at least one subject.")

    if st.session_state.setup_step == 3:
        st.subheader("Step 3: Customize Your Personal Wellness Tracker")
        st.info("Define personal goals you want to track. Edit the defaults, add your own, and specify units for numerical goals!")
        st.data_editor(
            st.session_state.personal_metrics,
            key="personal_editor",
            column_config={ "Type": st.column_config.SelectboxColumn("Type", options=["Time", "Number"]) },
            num_rows="dynamic", use_container_width=True
        )

        if st.button("✅ Complete Setup", type="primary"):
            final_subjects = pd.DataFrame(st.session_state.subjects_editor).dropna(how='all').drop_duplicates(subset=['Subject'])
            today_str = date.today().strftime("%Y-%m-%d")
            for _, row in final_subjects.iterrows():
                add_user_subject(username, row['Subject'], row['Category'])
                set_weekly_target(username, row['Subject'], row['Weekly Target (hrs)'])
                set_daily_target(username, row['Subject'], today_str, row['Daily Target (hrs)'])
            
            final_personal = pd.DataFrame(st.session_state.personal_editor).dropna(how='all').drop_duplicates(subset=['Metric'])
            for _, row in final_personal.iterrows():
                set_personal_target(username, row['Metric'], row['Type'].lower(), row['Target'], row['Unit'])

            st.success("All set! Your dashboard is ready. 🎉")
            for key in ['setup_step', 'setup_subjects', 'personal_metrics', 'subjects_editor', 'personal_editor']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Advanced Study Tracker", layout="wide", initial_sidebar_state="expanded")
    st.markdown("""<style>.block-container{padding-top:1.5rem;}div[data-testid="stRadio"]>label{font-size:1.1em;font-weight:600;}div[data-testid="stMetric"] div[data-testid="stMetricDelta"]{font-size:1em;}</style>""", unsafe_allow_html=True)

    update_db_schema()
    
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if 'username' not in st.session_state: st.session_state['username'] = ""
    if 'last_selected_subject' not in st.session_state:
        st.session_state.last_selected_subject = {}

    st.sidebar.header("👤 User Authentication")
    choice = st.sidebar.selectbox("Menu", ["Login", "SignUp"])

    if choice == "Login":
        if not st.session_state['logged_in']:
            username = st.sidebar.text_input("Username", key="login_user")
            password = st.sidebar.text_input("Password", type='password', key="login_pass")
            if st.sidebar.button("Login"):
                create_tables()
                if login_user(username, password):
                    st.session_state.update({'logged_in': True, 'username': username}); st.rerun()
                else:
                    st.sidebar.warning("Incorrect Username/Password")
        else:
            st.sidebar.success(f"Logged In as {st.session_state['username']}")
            if st.sidebar.button("Logout"):
                st.session_state.clear(); st.rerun()
    elif choice == "SignUp":
        st.sidebar.subheader("Create New Account")
        new_user = st.sidebar.text_input("Username", key="signup_user")
        new_password = st.sidebar.text_input("Password", type='password', key="signup_pass")
        if st.sidebar.button("SignUp"):
            create_tables()
            try:
                add_user(new_user, new_password); st.sidebar.success("Account created! Please login to begin setup.")
            except sqlite3.IntegrityError:
                st.sidebar.warning("Username already exists.")

    if st.session_state.get('logged_in'):
        username = st.session_state['username']
        
        if not check_setup_complete(username):
            run_setup_wizard(username); return

        user_subjects_df = get_user_subjects(username)
        all_subjects = sorted(user_subjects_df['Subject'].tolist())
        categories = sorted(user_subjects_df['Category'].unique().tolist())

        st.sidebar.header("📝 Log New Session")
        selected_category = st.sidebar.selectbox("Category", categories)
        
        with st.sidebar.form(key='study_form', clear_on_submit=True):
            subject_options = sorted(user_subjects_df[user_subjects_df['Category'] == selected_category]['Subject'].tolist())
            
            last_subject = st.session_state.last_selected_subject.get(selected_category)
            subject_index = 0
            if last_subject and last_subject in subject_options:
                subject_index = subject_options.index(last_subject)

            subject = st.selectbox("Subject", subject_options, index=subject_index)
            
            log_date_input = st.date_input("Date", datetime.now())
            subsection = st.radio("Type", ["Theory", "Numerical"], horizontal=True)
            duration = st.number_input("Duration (in hours)", 0.25, 10.0, step=0.25, format="%.2f")

            if st.form_submit_button(label='Log Study Session'):
                st.session_state.last_selected_subject[selected_category] = subject
                add_study_log(username, log_date_input.strftime("%Y-%m-%d"), subject, subsection, duration)
                st.sidebar.success(f"Logged {duration} hrs for {subject}."); st.rerun()
        
        with st.sidebar.expander("🗓️ Log Weekly Revision"):
            is_sunday = datetime.now().weekday() == 6
            if is_sunday:
                st.info("It's Sunday! Time to log your revision.")
            with st.form("sidebar_revision_form"):
                revision_subject = st.selectbox("Subject", all_subjects, key="sidebar_rev_sub")
                notes = st.text_area("Review Notes", key="sidebar_rev_notes", height=100)
                if st.form_submit_button("Log Revision", disabled=not is_sunday):
                    add_revision_log(username, date.today().strftime("%Y-%m-%d"), revision_subject, notes)
                    st.success(f"Revision for {revision_subject} logged.")

        st.header(f"Welcome back, {username}! 👋")
        st.markdown("---")

        tabs = st.tabs(["🚀 Dashboard", "📊 Daily Analysis", "🎯 Target Analysis", "✍️ Set Targets", "💡 Recommendations", "🗓️ Weekly Revision", "💪 Personal", "📚 Full History & Edit", "⚙️ Manage Goals"])
        df_all = get_user_logs(username)
        if not df_all.empty:
            df_all['Date'] = pd.to_datetime(df_all['Date'])
        
        with tabs[0]: # Dashboard
            st.subheader("Your Study Dashboard")
            if not df_all.empty:
                total_hours, top_subject = df_all['Duration'].sum(), df_all.groupby('Subject')['Duration'].sum().idxmax()
                today, start_of_week = date.today(), date.today() - timedelta(days=date.today().weekday())
                hours_this_week = df_all[df_all['Date'].dt.date >= start_of_week]['Duration'].sum()
                current_streak = calculate_streak(username)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Hours Studied 🕒", f"{total_hours:.2f} hrs")
                col2.metric("Top Subject 🏆", top_subject)
                col3.metric("Hours This Week 🗓️", f"{hours_this_week:.2f} hrs")
                col4.metric("Current Study Streak 🔥", f"{current_streak} Days")
                st.markdown("---")
                st.subheader("📈 Your 30-Day Study Trend")
                thirty_days_ago = date.today() - timedelta(days=30)
                df_last_30_days = df_all[df_all['Date'].dt.date >= thirty_days_ago]
                df_trend = df_last_30_days.groupby(df_last_30_days['Date'].dt.date)['Duration'].sum().reset_index()
                df_trend = df_trend.rename(columns={'Date': 'Day', 'Duration': 'Hours Studied'})
                if not df_trend.empty:
                    st.bar_chart(df_trend.set_index('Day'))
                else:
                    st.info("Not enough data for a 30-day trend. Keep logging!")
                st.markdown("---")
                st.subheader("📊 Overall Analysis at a Glance")
                
                df_all_with_cat = pd.merge(df_all, user_subjects_df, on='Subject', how='left')
                
                g_col1, g_col2 = st.columns(2)
                with g_col1:
                    fig = generate_pie_chart(df_all_with_cat, "Subject Distribution")
                    if fig: st.plotly_chart(fig, use_container_width=True)
                with g_col2:
                    fig_cat = generate_pie_chart(df_all_with_cat, "Category Distribution", name_col='Category')
                    if fig_cat: st.plotly_chart(fig_cat, use_container_width=True)

                st.markdown("---")
                st.subheader("Subject Breakdown: Theory vs. Numerical")
                df_type_breakdown = df_all_with_cat[df_all_with_cat['Type'].isin(['Theory', 'Numerical'])]
                if not df_type_breakdown.empty:
                    fig_breakdown = px.bar(df_type_breakdown, x='Subject', y='Duration', color='Type', title='Overall Theory vs. Numerical Hours per Subject', barmode='group', text_auto='.1f')
                    fig_breakdown.update_traces(textposition='outside'); st.plotly_chart(fig_breakdown, use_container_width=True)
            else:
                st.info("Log your first study session to see your dashboard!")

        with tabs[1]: # Daily Analysis
            st.subheader("Day-wise Analysis")
            analysis_date = st.date_input("Select a date to analyze", datetime.now(), key="daily_date")
            df_daily = get_logs_by_date(username, analysis_date.strftime("%Y-%m-%d"))
            if not df_daily.empty:
                df_daily_with_cat = pd.merge(df_daily, user_subjects_df, on='Subject', how='left')
                st.subheader(f"Breakdown for {analysis_date.strftime('%b %d')}")
                df_daily_breakdown = df_daily_with_cat[df_daily_with_cat['Type'].isin(['Theory', 'Numerical'])]
                if not df_daily_breakdown.empty:
                    fig_daily_breakdown = px.bar(df_daily_breakdown, x='Subject', y='Duration', color='Type', title='Daily Theory vs. Numerical Hours', barmode='group', text_auto='.1f')
                    fig_daily_breakdown.update_traces(textposition='outside'); st.plotly_chart(fig_daily_breakdown, use_container_width=True)
                else:
                    st.info("No Theory or Numerical data logged for this day.")
            else:
                st.warning(f"No study data found for {analysis_date.strftime('%Y-%m-%d')}.")
        
        with tabs[2]: # Target Analysis
            st.subheader("Target vs. Actual Performance")
            analysis_date_daily = st.date_input("Select a date for daily target analysis", datetime.now(), key="target_date")
            df_daily_targets = get_daily_targets_for_date(username, analysis_date_daily.strftime("%Y-%m-%d"))
            df_day_logs = get_logs_by_date(username, analysis_date_daily.strftime("%Y-%m-%d")).groupby('Subject')['Duration'].sum().reset_index()
            df_day_analysis = pd.merge(df_daily_targets, df_day_logs, on="Subject", how="left").fillna(0).rename(columns={'Duration': 'Actual Hours'})
            df_melted_daily = df_day_analysis.melt(id_vars='Subject', value_vars=['Daily Target', 'Actual Hours'], var_name='Metric', value_name='Hours')
            fig_daily = px.bar(df_melted_daily, x='Subject', y='Hours', color='Metric', barmode='group', title=f"Daily Target Progress ({analysis_date_daily.strftime('%b %d')})", text_auto='.1f')
            fig_daily.update_traces(textposition='outside'); st.plotly_chart(fig_daily, use_container_width=True)
            st.markdown("---")
            weekly_analysis_date = st.date_input("Select a date to view its week's progress", datetime.now(), key="weekly_target_date")
            start_of_week = weekly_analysis_date - timedelta(days=weekly_analysis_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            df_in_week = df_all[(df_all['Date'].dt.date >= start_of_week) & (df_all['Date'].dt.date <= end_of_week)] if not df_all.empty else pd.DataFrame(columns=df_all.columns)
            df_weekly_logs = df_in_week.groupby('Subject')['Duration'].sum().reset_index()
            df_weekly_targets = get_weekly_targets(username)
            df_weekly_analysis = pd.merge(df_weekly_targets, df_weekly_logs, on="Subject", how="left").fillna(0).rename(columns={'Duration': 'Actual Hours'})
            df_melted_weekly = df_weekly_analysis.melt(id_vars='Subject', value_vars=['Weekly Target', 'Actual Hours'], var_name='Metric', value_name='Hours')
            fig_weekly = px.bar(df_melted_weekly, x='Subject', y='Hours', color='Metric', barmode='group', title=f"Weekly Target Progress ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')})", text_auto='.1f')
            fig_weekly.update_traces(textposition='outside'); st.plotly_chart(fig_weekly, use_container_width=True)

        with tabs[3]: # Set Targets
            st.subheader("Set Your Study Targets")
            target_date_selector = st.date_input("Select a date to set daily targets", datetime.now(), key="set_target_date")
            df_daily_targets = get_daily_targets_for_date(username, target_date_selector.strftime("%Y-%m-%d"))
            daily_targets_dict = {row['Subject']: row['Daily Target'] for _, row in df_daily_targets.iterrows()}
            df_weekly_targets = get_weekly_targets(username)
            weekly_targets_dict = {row['Subject']: row['Weekly Target'] for _, row in df_weekly_targets.iterrows()}
            with st.form("targets_form"):
                st.markdown(f"**Daily Targets for {target_date_selector.strftime('%Y-%m-%d')}**")
                new_daily_targets = {}
                col1, col2 = st.columns(2)
                subjects_col1, subjects_col2 = all_subjects[::2], all_subjects[1::2]
                with col1:
                    for subject in subjects_col1:
                        new_daily_targets[subject] = st.number_input(f"{subject}", 0.0, value=float(daily_targets_dict.get(subject, 0)), key=f"d_{subject}", step=0.25)
                with col2:
                    for subject in subjects_col2:
                        new_daily_targets[subject] = st.number_input(f"{subject}", 0.0, value=float(daily_targets_dict.get(subject, 0)), key=f"d_{subject}_2", step=0.25)
                st.markdown("---")
                st.markdown("**Overall Weekly Targets**")
                new_weekly_targets = {}
                w_col1, w_col2 = st.columns(2)
                with w_col1:
                    for subject in subjects_col1:
                        new_weekly_targets[subject] = st.number_input(f"{subject}", 0.0, value=float(weekly_targets_dict.get(subject, 0)), key=f"w_{subject}", step=0.5)
                with w_col2:
                    for subject in subjects_col2:
                        new_weekly_targets[subject] = st.number_input(f"{subject}", 0.0, value=float(weekly_targets_dict.get(subject, 0)), key=f"w_{subject}_2", step=0.5)
                if st.form_submit_button("Save All Targets"):
                    for subject, daily_target in new_daily_targets.items():
                        set_daily_target(username, subject, target_date_selector.strftime("%Y-%m-%d"), daily_target)
                    for subject, weekly_target in new_weekly_targets.items():
                        set_weekly_target(username, subject, weekly_target)
                    st.success("Your targets have been saved!"); st.rerun()

        with tabs[4]: # Recommendations
            st.subheader("💡 Personalized Study Recommendations")
            if not df_all.empty:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🎯 Weekly Target Adherence")
                    start_of_week_dt = date.today() - timedelta(days=date.today().weekday())
                    df_weekly_logs = df_all[df_all['Date'].dt.date >= start_of_week_dt].groupby('Subject')['Duration'].sum().reset_index()
                    df_weekly_targets = get_weekly_targets(username)
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
            if is_sunday:
                st.success("It's Sunday! A perfect day for your weekly revision.")
            with st.form("revision_form"):
                revision_date = st.date_input("Revision Date", datetime.now(), disabled=not is_sunday)
                revision_data = {}
                for subject in all_subjects:
                    revised = st.checkbox(subject, key=f"rev_{subject}")
                    notes = st.text_area("Review Notes", key=f"notes_{subject}", height=50, placeholder=f"Key takeaways for {subject}...")
                    if revised:
                        revision_data[subject] = notes
                if st.form_submit_button("Save Revision Log"):
                    if revision_data:
                        for subject, notes in revision_data.items():
                            add_revision_log(username, revision_date.strftime("%Y-%m-%d"), subject, notes)
                        st.success("Revision log saved successfully!")
                    else:
                        st.warning("Please select at least one subject you revised.")
            st.markdown("---")
            st.markdown("#### Past Revision Logs")
            past_sunday = st.date_input("Select a past Sunday to review", date.today() - timedelta(days=date.today().weekday() + 1))
            if past_sunday.weekday() != 6:
                st.error("Please select a Sunday.")
            else:
                df_revision = get_revision_logs_by_date(username, past_sunday.strftime("%Y-%m-%d"))
                if not df_revision.empty:
                    st.dataframe(df_revision, use_container_width=True)
                else:
                    st.info(f"No revision log found for {past_sunday.strftime('%Y-%m-%d')}.")

        with tabs[6]: # Personal
            st.subheader("💪 Personal Wellness Tracker")
            personal_targets = get_personal_targets(username)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                with st.expander("Log Your Daily Metrics", expanded=True):
                    with st.form("personal_log_form", clear_on_submit=True):
                        p_log_date = st.date_input("Date", key="p_log_date")
                        logged_metrics = {}
                        for name, details in personal_targets.items():
                            if details['type'] == 'time':
                                logged_metrics[name] = st.time_input(name, key=f"log_{name}")
                            else:
                                unit_str = f"({details['unit']})" if details['unit'] else ""
                                logged_metrics[name] = st.number_input(f"{name} {unit_str}", min_value=0, step=1, key=f"log_{name}")
                        
                        if st.form_submit_button("Log Metrics"):
                            add_personal_log(username, p_log_date.strftime("%Y-%m-%d"), logged_metrics)
                            st.success(f"Personal metrics logged for {p_log_date.strftime('%Y-%m-%d')}!"); st.rerun()
            with col2:
                st.markdown("#### Daily Analysis")
                analysis_p_date = st.date_input("Select Date for Analysis", key="p_analysis_date")
                actuals = get_personal_log_by_date(username, analysis_p_date.strftime("%Y-%m-%d"))
                
                if actuals:
                    all_metrics = list(personal_targets.items())
                    for i in range(0, len(all_metrics), 3):
                        metric_chunk = all_metrics[i:i+3]
                        metric_cols = st.columns(3)
                        for j, (name, details) in enumerate(metric_chunk):
                            actual_val = actuals.get(name)
                            if actual_val is None: continue
                            
                            target_val_str = details['target']
                            unit = details.get('unit', '')
                            
                            if details['type'] == 'time':
                                actual_time = datetime.strptime(actual_val, '%H:%M').time()
                                target_time = datetime.strptime(target_val_str, '%H:%M').time()
                                delta = datetime.combine(date.min, target_time) - datetime.combine(date.min, actual_time)
                                metric_cols[j].metric(label=f"{name} (T: {target_time.strftime('%H:%M')})", value=actual_time.strftime('%H:%M'), delta=format_time_delta(delta))
                            else:
                                try:
                                    actual_num = int(actual_val)
                                    target_num = int(target_val_str)
                                    delta = actual_num - target_num
                                    metric_cols[j].metric(label=f"{name} (T: {target_num} {unit})", value=f"{actual_num} {unit}", delta=f"{delta:+}")
                                except (ValueError, TypeError):
                                    metric_cols[j].metric(label=f"{name}", value=f"{actual_val} {unit}", delta="N/A")
                else:
                    st.info(f"No personal data logged for {analysis_p_date.strftime('%Y-%m-%d')}.")

            st.markdown("---")
            st.subheader("📈 Your 30-Day Personal Progress")
            df_personal_all = get_all_personal_logs(username)
            if not df_personal_all.empty:
                df_personal_all['Date'] = pd.to_datetime(df_personal_all['Date'])
                
                numerical_metrics = [name for name, details in personal_targets.items() if details['type'] == 'number']
                if numerical_metrics:
                    selected_metric = st.selectbox("Select a metric to visualize", numerical_metrics)
                    
                    df_metric_trend = df_personal_all[['Date', selected_metric]].dropna()
                    df_metric_trend[selected_metric] = pd.to_numeric(df_metric_trend[selected_metric])
                    
                    st.bar_chart(df_metric_trend.set_index('Date'))
                else:
                    st.info("You don't have any numerical personal goals to visualize.")
            else:
                st.info("Log some personal metrics to see your progress over time.")

        
        with tabs[7]: # Full History & Edit
            st.subheader("📚 Full Study History & Edit Logs")
            if not df_all.empty:
                st.dataframe(df_all[['Date', 'Subject', 'Type', 'Duration']].sort_values(by='Date', ascending=False), use_container_width=True)
                st.markdown("---")
                st.markdown("#### ✏️ Modify a Log Entry")
                log_options = [f"{row['ID']}: {row['Date'].strftime('%Y-%m-%d')} - {row['Subject']} ({row['Duration']} hrs)" for index, row in df_all.iterrows()]
                selected_log_str = st.selectbox("Select a log to modify", [""] + log_options)
                if selected_log_str:
                    log_id_to_edit = int(selected_log_str.split(':')[0])
                    selected_log_data = df_all[df_all['ID'] == log_id_to_edit].iloc[0]
                    with st.form("edit_log_form"):
                        st.write(f"**Editing Log ID: {log_id_to_edit}**")
                        edit_date = st.date_input("Date", value=selected_log_data['Date'].date())
                        subject_index = all_subjects.index(selected_log_data['Subject']) if selected_log_data['Subject'] in all_subjects else 0
                        type_index = ["Theory", "Numerical"].index(selected_log_data['Type']) if selected_log_data['Type'] in ["Theory", "Numerical"] else 0
                        edit_subject = st.selectbox("Subject", all_subjects, index=subject_index)
                        edit_type = st.radio("Type", ["Theory", "Numerical"], index=type_index, horizontal=True)
                        edit_duration = st.number_input("Duration (in hours)", 0.25, 10.0, step=0.25, value=selected_log_data['Duration'])
                        col_update, col_delete = st.columns(2)
                        with col_update:
                            if st.form_submit_button("Update Log"):
                                update_study_log(log_id_to_edit, edit_date.strftime("%Y-%m-%d"), edit_subject, edit_type, edit_duration)
                                st.success(f"Log ID {log_id_to_edit} has been updated."); st.rerun()
                        with col_delete:
                            if st.form_submit_button("Delete Log"):
                                delete_study_log(log_id_to_edit)
                                st.success(f"Log ID {log_id_to_edit} has been deleted."); st.rerun()
            else:
                st.info("Your study history is empty.")

        with tabs[8]: # Manage Goals
            st.subheader("⚙️ Manage Your Goals")
            
            with st.expander("Manage Study Subjects"):
                if not user_subjects_df.empty:
                    st.dataframe(user_subjects_df[['Subject', 'Category']], use_container_width=True)
                    st.markdown("---")
                    st.markdown("#### Edit or Delete a Subject")
                    subject_to_edit_id = st.selectbox("Select Subject to Edit", user_subjects_df['id'], format_func=lambda x: user_subjects_df[user_subjects_df['id'] == x]['Subject'].iloc[0])
                    if subject_to_edit_id:
                        subject_data = user_subjects_df[user_subjects_df['id'] == subject_to_edit_id].iloc[0]
                        with st.form("edit_subject_form"):
                            st.write(f"**Editing: {subject_data['Subject']}**")
                            new_name = st.text_input("New Subject Name", value=subject_data['Subject'])
                            new_cat = st.text_input("New Category Name", value=subject_data['Category'])
                            e_col1, e_col2 = st.columns(2)
                            with e_col1:
                                if st.form_submit_button("Update Subject"):
                                    update_user_subject(subject_to_edit_id, new_name, new_cat)
                                    st.success("Subject updated!"); st.rerun()
                            with e_col2:
                                if st.form_submit_button("Delete Subject"):
                                    delete_user_subject(subject_to_edit_id)
                                    st.warning("Subject deleted!"); st.rerun()
                st.markdown("---")
                st.markdown("#### Add a New Subject")
                with st.form("add_new_subject_form"):
                    a_col1, a_col2 = st.columns(2)
                    with a_col1:
                        new_subject_name = st.text_input("Subject Name")
                    with a_col2:
                        new_subject_cat = st.text_input("Category")
                    if st.form_submit_button("Add Subject"):
                        if new_subject_name and new_subject_cat:
                            add_user_subject(username, new_subject_name, new_subject_cat)
                            st.success(f"Added '{new_subject_name}' to your subjects."); st.rerun()
                        else:
                            st.warning("Please provide both subject name and category.")
            
            with st.expander("Manage Personal Goals"):
                personal_targets_df = pd.DataFrame.from_dict(personal_targets, orient='index').reset_index().rename(columns={'index': 'Metric', 'target': 'Target', 'unit': 'Unit', 'type': 'Type'})
                st.dataframe(personal_targets_df[['Metric', 'Type', 'Target', 'Unit']], use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Edit or Delete a Personal Goal")
                metric_to_edit = st.selectbox("Select Goal to Edit", personal_targets_df['Metric'])
                if metric_to_edit:
                    metric_data = personal_targets_df[personal_targets_df['Metric'] == metric_to_edit].iloc[0]
                    with st.form("edit_personal_form"):
                        st.write(f"**Editing: {metric_data['Metric']}**")
                        new_metric_name = st.text_input("New Goal Name", value=metric_data['Metric'])
                        new_metric_type = st.selectbox("Type", ["time", "number"], index=["time", "number"].index(metric_data['Type']))
                        new_target = st.text_input("New Target", value=metric_data['Target'])
                        new_unit = st.text_input("New Unit (if applicable)", value=metric_data['Unit'])
                        
                        ep_col1, ep_col2 = st.columns(2)
                        with ep_col1:
                            if st.form_submit_button("Update Goal"):
                                delete_personal_target(username, metric_to_edit)
                                set_personal_target(username, new_metric_name, new_metric_type, new_target, new_unit)
                                st.success("Personal goal updated!"); st.rerun()
                        with ep_col2:
                            if st.form_submit_button("Delete Goal"):
                                delete_personal_target(username, metric_to_edit)
                                st.warning("Personal goal deleted!"); st.rerun()

                st.markdown("---")
                st.markdown("#### Add a New Personal Goal")
                with st.form("add_new_personal_form"):
                    ap_col1, ap_col2 = st.columns(2)
                    with ap_col1:
                        new_personal_name = st.text_input("Goal Name")
                        new_personal_type = st.selectbox("Type", ["time", "number"])
                    with ap_col2:
                        new_personal_target = st.text_input("Target (e.g., 08:00 or 100)")
                        new_personal_unit = st.text_input("Unit (e.g., pages, mins)")
                    
                    if st.form_submit_button("Add Goal"):
                        if new_personal_name and new_personal_target:
                            set_personal_target(username, new_personal_name, new_personal_type, new_personal_target, new_personal_unit)
                            st.success(f"Added '{new_personal_name}' to your personal goals."); st.rerun()
                        else:
                            st.warning("Please provide a name and target for your goal.")

    else:
        st.title("🎓 Advanced Study Task Manager")
        st.info("Please log in or sign up using the sidebar to access your personalized dashboard.")
        st.image("https://placehold.co/800x400/E0F2F7/333333?text=Welcome+to+Your+Study+Tracker", use_container_width=True)

if __name__ == '__main__':
    main()
