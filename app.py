import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import time
import json
import io
from PIL import Image
from sqlalchemy import text

# ==============================================================================
# RIDEBOSS ULTRA - POSTGRESQL MIGRATION (PART 1)
# ==============================================================================
# System: Car Wash Management System & HR Portal
# Database: PostgreSQL (Supabase)
# Migration Date: 2026
# ==============================================================================

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="RideBoss Autos HQ", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATABASE CONNECTION SETUP ---
# MIGRATION NOTE: Replaced sqlite3.connect with st.connection for PostgreSQL
# Ensure your .streamlit/secrets.toml contains the [connections.postgresql] block
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

# --- CSS STYLING (EXPANDED FOR VISUAL CLARITY) ---
st.markdown("""
    <style>
    /* MAIN APP STYLING */
    .stApp { 
        background-color: #050505; 
        color: #E0E0E0; 
        font-family: 'Inter', sans-serif; 
    }
    
    /* SIDEBAR STYLING */
    [data-testid="stSidebar"] { 
        background-color: #0A0A0A; 
        border-right: 1px solid #222; 
    }
    
    /* STATUS CARD COMPONENT */
    .status-card { 
        background: #0F0F0F; 
        padding: 25px; 
        border-radius: 2px; 
        border-left: 4px solid #00d4ff; 
        margin-bottom: 15px; 
        border-top: 1px solid #1A1A1A; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* NOTIFICATION BAR COMPONENT */
    .notification-bar { 
        background: #00d4ff22; 
        padding: 12px; 
        border-bottom: 1px solid #00d4ff; 
        color: #00d4ff; 
        font-size: 0.85em; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        margin-bottom: 30px; 
    }
    
    /* CUSTOM BUTTON STYLING */
    .stButton>button { 
        border-radius: 0px; 
        letter-spacing: 2px; 
        font-size: 0.8em; 
        text-transform: uppercase; 
        background-color: transparent; 
        border: 1px solid #333; 
        color: white; 
        height: 3em; 
        transition: 0.4s; 
        width: 100%; 
    }
    
    .stButton>button:hover { 
        border-color: #00d4ff; 
        color: #00d4ff; 
        background-color: #00d4ff11; 
        cursor: pointer;
    }
    
    /* MONITOR / FLIGHT BOARD SCROLLING EFFECTS */
    .monitor-container { 
        background: #000; 
        border: 2px solid #222; 
        border-radius: 10px; 
        height: 700px; 
        overflow: hidden; 
        position: relative; 
    }
    
    .scroll-content { 
        position: absolute; 
        width: 100%; 
        animation: scrollUp 40s linear infinite; 
        will-change: transform; 
    }
    
    @keyframes scrollUp { 
        0% { transform: translateY(100%); } 
        100% { transform: translateY(-100%); } 
    }
    
    .scroll-content:hover { 
        animation-play-state: paused; 
    }
    
    .monitor-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        padding: 30px; 
        border-bottom: 2px solid #222; 
        background: #050505; 
    }
    
    .monitor-plate { 
        font-size: 55px; 
        font-weight: 900; 
        color: #00d4ff; 
        font-family: 'Courier New', monospace; 
    }
    
    .monitor-status { 
        font-size: 18px; 
        color: #FFD700; 
        font-weight: bold; 
    }
    
    .monitor-meta { 
        text-align: right; 
    }
    
    .monitor-staff { 
        font-size: 20px; 
        color: #888; 
        text-transform: uppercase; 
    }
    
    .monitor-svc { 
        color: #00d4ff; 
        font-style: italic; 
        font-size: 16px; 
    }

    /* INPUT FIELD STYLING */
    div[data-baseweb="input"] > div {
        background-color: #111;
        color: white;
        border-radius: 0px;
        border: 1px solid #333;
    }
    div[data-baseweb="select"] > div {
        background-color: #111;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE INITIALIZATION FUNCTION ---
def init_db():
    """
    Creates tables if they do not exist using PostgreSQL syntax.
    MIGRATION NOTE:
    1. Changed INTEGER PRIMARY KEY AUTOINCREMENT to SERIAL PRIMARY KEY.
    2. Changed BLOB to BYTEA.
    3. Used session.execute(text(...)) for DDL commands.
    """
    with conn.session as s:
        # 1. USERS TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT, 
                role TEXT, 
                dept TEXT, 
                status TEXT DEFAULT 'ACTIVE', 
                verified INTEGER DEFAULT 0
            )
        """))
        
        # 2. CUSTOMERS TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS customers (
                plate TEXT PRIMARY KEY, 
                name TEXT, 
                phone TEXT, 
                visits INTEGER, 
                last_visit TEXT
            )
        """))
        
        # 3. SALES TABLE (Note: SERIAL for Auto ID)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY, 
                plate TEXT, 
                services TEXT, 
                total REAL, 
                method TEXT, 
                staff TEXT, 
                timestamp TEXT, 
                type TEXT
            )
        """))
        
        # 4. NOTIFICATIONS TABLE (Note: SERIAL for Auto ID)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY, 
                message TEXT, 
                timestamp TEXT
            )
        """))
        
        # 5. LIVE BAYS TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS live_bays (
                plate TEXT PRIMARY KEY, 
                status TEXT, 
                entry_time TEXT, 
                staff TEXT, 
                vehicle_type TEXT, 
                service_detail TEXT, 
                wet_staff_history TEXT
            )
        """))
        
        # 6. INVENTORY TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                item TEXT PRIMARY KEY, 
                stock REAL, 
                unit TEXT, 
                price REAL
            )
        """))
        
        # 7. WASH PRICES TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS wash_prices (
                service TEXT PRIMARY KEY, 
                price REAL
            )
        """))
        
        # 8. EXPENSES TABLE (Note: SERIAL for Auto ID)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY, 
                description TEXT, 
                amount REAL, 
                timestamp TEXT
            )
        """))
        
        # 9. MEMBERSHIPS TABLE
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS memberships (
                plate TEXT PRIMARY KEY, 
                balance_washes INTEGER, 
                card_type TEXT, 
                sale_price REAL DEFAULT 0.0
            )
        """))
        
        # 10. STAFF PROFILES (Note: BYTEA for Image)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS staff_profiles (
                username TEXT PRIMARY KEY, 
                full_name TEXT, 
                phone TEXT, 
                address TEXT, 
                nin TEXT, 
                bank_name TEXT, 
                account_no TEXT, 
                id_type TEXT, 
                id_image BYTEA
            )
        """))
        
        # 11. STAFF PAYROLL CONFIG
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS staff_payroll_config (
                username TEXT PRIMARY KEY, 
                base_salary REAL DEFAULT 0.0, 
                bonus_pc REAL DEFAULT 0.0
            )
        """))
        
        # 12. EARNINGS LOG (Note: SERIAL for Auto ID)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS earnings_log (
                id SERIAL PRIMARY KEY, 
                username TEXT, 
                amount REAL, 
                ref_plate TEXT, 
                timestamp TEXT
            )
        """))
        
        s.commit()

# --- SEED INITIAL DATA ---
def seed_data():
    """
    Populates the database with initial admin and inventory data.
    Uses SQLAlchemy parameterized queries (:key).
    """
    with conn.session as s:
        # Seed Admin
        s.execute(text("""
            INSERT INTO users (username, password, role, dept, status, verified) 
            VALUES (:u, :p, :r, :d, :s, :v)
            ON CONFLICT (username) DO NOTHING
        """), {"u": "admin", "p": "0000", "r": "MANAGER", "d": "MANAGEMENT", "s": "ACTIVE", "v": 1})
        
        # Seed Inventory
        inv_items = [
            {"item": "Car Shampoo", "stock": 10.0, "unit": "Gallons", "price": 0.0},
            {"item": "Coke", "stock": 50.0, "unit": "Cans", "price": 500.0},
            {"item": "Water", "stock": 100.0, "unit": "Bottles", "price": 200.0}
        ]
        for i in inv_items:
            s.execute(text("""
                INSERT INTO inventory (item, stock, unit, price)
                VALUES (:item, :stock, :unit, :price)
                ON CONFLICT (item) DO NOTHING
            """), i)
        
        # Seed Wash Prices
        # Check count first
        count_res = s.execute(text("SELECT COUNT(*) FROM wash_prices")).scalar()
        if count_res == 0:
            initial_services = [
                {"s": "Standard Wash", "p": 5000},
                {"s": "Executive Detail", "p": 15000},
                {"s": "Engine Steam", "p": 10000},
                {"s": "Ceramic Wax", "p": 25000},
                {"s": "Interior Deep Clean", "p": 12000}
            ]
            for svc in initial_services:
                s.execute(text("INSERT INTO wash_prices VALUES (:s, :p)"), svc)
                
        s.commit()

# Execute Initialization
init_db()
seed_data()

# --- UTILITY FUNCTIONS ---

def add_event(msg):
    """
    Logs an event to the notifications table.
    """
    now = datetime.now().strftime("%H:%M:%S")
    full_msg = f"{now} | {msg}"
    with conn.session as s:
        s.execute(
            text("INSERT INTO notifications (message, timestamp) VALUES (:m, :t)"),
            {"m": full_msg, "t": now}
        )
        s.commit()

def format_whatsapp(phone, message):
    """
    Formats a phone number and message into a WhatsApp API link.
    """
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

def get_free_staff_by_dept(dept_name):
    """
    Returns a list of active, verified staff in a department who are not currently busy.
    """
    # Get busy staff from live_bays
    busy_df = conn.query("SELECT staff FROM live_bays", ttl=0)
    busy_list = busy_df['staff'].tolist() if not busy_df.empty else []
    
    # Get all verified staff in department
    query = "SELECT username FROM users WHERE dept = :d AND status = 'ACTIVE' AND verified = 1"
    try:
        staff_df = conn.query(query, params={"d": dept_name}, ttl=0)
        return staff_df['username'].tolist() if not staff_df.empty else []
    except:
        return []
    
    # Filter
    return [s for s in all_dept if s not in busy_list]

def calculate_payouts(username):
    """
    Calculates payroll metrics: Base Salary, Daily Comm, Monthly Comm, Yearly Comm, and Total.
    """
    # Fetch base salary
    # FIX: Removed text() wrapper from conn.query call
    query_conf = "SELECT base_salary FROM staff_payroll_config WHERE username=:u"
    res = conn.query(query_conf, params={"u": username}, ttl=0)
    base = res.iloc[0]['base_salary'] if not res.empty else 0.0
    
    # Fetch commissions log
    # FIX: Removed text() wrapper from conn.query call
    query_log = "SELECT * FROM earnings_log WHERE username=:u"
    df_comm = conn.query(query_log, params={"u": username}, ttl=0)
    
    daily_comm = 0.0
    monthly_comm = 0.0
    yearly_comm = 0.0
    
    if not df_comm.empty:
        # Ensure timestamp is datetime
        df_comm['timestamp'] = pd.to_datetime(df_comm['timestamp'])
        now = datetime.now()
        
        # Calculate Aggregates
        daily_comm = df_comm[df_comm['timestamp'].dt.date == now.date()]['amount'].sum()
        monthly_comm = df_comm[
            (df_comm['timestamp'].dt.month == now.month) & 
            (df_comm['timestamp'].dt.year == now.year)
        ]['amount'].sum()
        yearly_comm = df_comm[df_comm['timestamp'].dt.year == now.year]['amount'].sum()
    
    return base, daily_comm, monthly_comm, yearly_comm, (base + monthly_comm)

# --- SPECIAL PRINT RENDERER (UNTOUCHED LOGIC) ---
# This block handles the print request by intercepting query params
query_params = st.query_params
if "print_receipt" in query_params:
    try:
        receipt_data = json.loads(query_params["print_receipt"])
        st.markdown(f"""
            <style>
                @media print {{
                    body {{ background: white !important; }}
                    .stApp {{ background: white !important; }}
                    [data-testid="stSidebar"], header, .stButton {{ display: none !important; }}
                }}
                .print-wrap {{ 
                    background: white; 
                    color: black; 
                    padding: 30px; 
                    font-family: 'Courier New', Courier, monospace; 
                    max-width: 400px; 
                    margin: auto; 
                    border: 2px solid black; 
                }}
                .print-header {{ 
                    text-align: center; 
                    border-bottom: 2px solid black; 
                    padding-bottom: 10px; 
                    margin-bottom: 15px; 
                }}
                .print-row {{ 
                    display: flex; 
                    justify-content: space-between; 
                    margin: 5px 0; 
                    font-size: 14px; 
                }}
                .print-divider {{ 
                    border-top: 1px dashed black; 
                    margin: 15px 0; 
                }}
                .print-total {{ 
                    border-top: 2px solid black; 
                    margin-top: 10px; 
                    padding-top: 10px; 
                    font-weight: bold; 
                    font-size: 22px; 
                    display: flex; 
                    justify-content: space-between; 
                }}
                .footer {{ 
                    text-align: center; 
                    font-size: 12px; 
                    margin-top: 30px; 
                    border-top: 1px solid black; 
                    padding-top: 10px; 
                }}
            </style>
            <div class="print-wrap">
                <div class="print-header">
                    <h1 style="margin:0; font-size:24px; color: black !important;">RIDEBOSS AUTOS</h1>
                    <p style="margin:0; font-size:12px; letter-spacing:2px; color: black !important;">PREMIUM DETAILING & LOUNGE</p>
                </div>
                <div class="print-row"><span>REF NO:</span> <span>#RB{receipt_data['id']}</span></div>
                <div class="print-row"><span>DATE:</span> <span>{receipt_data['date']}</span></div>
                <div class="print-row"><span>PLATE:</span> <b>{receipt_data['plate']}</b></div>
                <div class="print-divider"></div>
                <div style="min-height: 100px;">
                    <p style="font-size:12px; margin-bottom:5px;">SERVICES RENDERED:</p>
                    <p style="font-size:16px; font-weight:bold;">{receipt_data['items']}</p>
                </div>
                <div class="print-total"><span>TOTAL</span><span>₦{receipt_data['total']:,}</span></div>
                <div class="footer">THANK YOU FOR YOUR PATRONAGE<br>www.ridebossautos.com</div>
            </div>
            <script>window.print();</script>
        """, unsafe_allow_html=True)
        st.stop() # Stop execution to only show receipt
    except Exception as e:
        st.error(f"Receipt Generation Error: {e}")
        st.stop()

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False
if 'user_role' not in st.session_state: 
    st.session_state.user_role = None
if 'user_name' not in st.session_state: 
    st.session_state.user_name = None
if 'user_dept' not in st.session_state: 
    st.session_state.user_dept = None
if 'last_receipt' not in st.session_state:
    st.session_state.last_receipt = None
if 'wa_pending' not in st.session_state:
    st.session_state.wa_pending = None

# --- LOGIN SYSTEM ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center; letter-spacing:10px; margin-top:100px;'>RIDEBOSS LOGIN</h1>", unsafe_allow_html=True)
    _, log_col, _ = st.columns([1,1,1])
    
    with log_col:
        st.markdown("""
        <div style="background:#111; padding:20px; border:1px solid #333;">
            <p style="text-align:center; color:#666;">SECURE ACCESS GATEWAY</p>
        </div>
        """, unsafe_allow_html=True)
        
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password")
        
        if st.button("ACCESS SYSTEM"):
            # The query string
            login_query = "SELECT * FROM users WHERE username = :u AND password = :p AND status = 'ACTIVE'"
            
            # This line must be indented (4 spaces or 1 tab) to be inside the button click
            try:
                df = conn.query(login_query, params={"u": u, "p": p}, ttl=0)
                
                if not df.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_role = df.iloc[0]['role']
                    st.session_state.user_dept = df.iloc[0]['dept']
                    st.session_state.user_name = u
                    st.success("Access Granted. Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid Credentials. Access Denied.")
            except Exception as e:
                st.error(f"System connection error: {e}")
                
    st.stop()

# --- STAFF INDUCTION GATE (NEW FEATURE) ---
# Check verification status
v_query = "SELECT verified FROM users WHERE username = :u"
v_df = conn.query(v_query, params={"u": st.session_state.user_name}, ttl=0)
is_verified = v_df.iloc[0]['verified'] if not v_df.empty else 0

if st.session_state.user_role == "STAFF" and is_verified == 0:
    st.markdown("<h2 style='text-align:center; color:#00d4ff;'>RIDEBOSS INDUCTION</h2>", unsafe_allow_html=True)
    st.info("Please complete your verification details to unlock the system.")
    
    with st.form("staff_verification_form"):
        col1, col2 = st.columns(2)
        with col1:
            fn = st.text_input("Full Legal Name")
            ph = st.text_input("Phone Number")
            addr = st.text_area("Residential Address")
        with col2:
            nin = st.text_input("NIN (11 Digits)", max_chars=11)
            bn = st.text_input("Bank Name")
            acc = st.text_input("Account Number")
        
        st.markdown("---")
        st.write("IDENTITY VERIFICATION")
        id_type = st.selectbox("Document Type", ["National ID Card", "Drivers License", "International Passport"])
        id_file = st.file_uploader("Upload Clear Photo of ID", type=['jpg', 'png', 'jpeg'])

        if st.form_submit_button("SUBMIT FOR VERIFICATION"):
            if len(nin) != 11 or not nin.isdigit():
                st.error("Invalid NIN. Please provide exactly 11 digits.")
            elif fn and ph and addr and nin and bn and acc and id_file:
                # Process Image for PostgreSQL BYTEA
                # read() returns bytes, which SQLAlchemy handles for BYTEA
                img_bytes = id_file.getvalue()
                
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO staff_profiles 
                        (username, full_name, phone, address, nin, bank_name, account_no, id_type, id_image) 
                        VALUES (:u, :fn, :ph, :ad, :nin, :bn, :acc, :idt, :img)
                        ON CONFLICT (username) DO UPDATE 
                        SET full_name=:fn, phone=:ph, address=:ad, nin=:nin, bank_name=:bn, account_no=:acc, id_type=:idt, id_image=:img
                    """), {
                        "u": st.session_state.user_name,
                        "fn": fn, "ph": ph, "ad": addr, "nin": nin, 
                        "bn": bn, "acc": acc, "idt": id_type, "img": img_bytes
                    })
                    s.commit()
                
                st.success("Details submitted! Awaiting Manager Approval.")
                st.info("Log out and wait for your manager to verify your account.")
            else:
                st.error("Please fill all fields and upload ID.")
    
    if st.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# --- LOAD SYSTEM CONFIGURATION ---
wash_prices_df = conn.query("SELECT * FROM wash_prices", ttl=0)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"USER: **{st.session_state.user_name}**")
st.sidebar.caption(f"DEPT: {st.session_state.user_dept}")

# Define Menus based on Role/Dept
if st.session_state.user_role == "MANAGER":
    menu = [
        "COMMAND CENTER", 
        "LIVE U-FLOW", 
        "ONBOARD STAFF", 
        "BOSS HR", 
        "FINANCIALS", 
        "INVENTORY & STAFF", 
        "CRM & RETENTION", 
        "NOTIFICATIONS"
    ]
elif st.session_state.user_dept == "RECEPTIONIST":
    menu = [
        "COMMAND CENTER", 
        "LIVE U-FLOW", 
        "MY EARNINGS", 
        "NOTIFICATIONS"
    ]
else:
    # Wet/Dry Bay Staff only see this
    menu = [
        "LIVE U-FLOW", 
        "MY EARNINGS", 
        "NOTIFICATIONS"
    ]

choice = st.sidebar.radio("NAVIGATE", menu)
st.sidebar.markdown("---")

if st.sidebar.button("LOGOUT"):
    st.session_state.logged_in = False
    st.rerun()

# --- FACTORY RESET (MANAGER ONLY + SECRETS PROTECTED) ---
if st.session_state.user_role == "MANAGER":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔐 SYSTEM ADMIN")
    
    if "reset_mode" not in st.session_state:
        st.session_state.reset_mode = False

    if st.sidebar.button("⚠️ FACTORY RESET SYSTEM"):
        st.session_state.reset_mode = True

    if st.session_state.reset_mode:
        st.sidebar.warning("Master Admin Key Required")
        
        # 1. Password Input Field
        master_key_input = st.sidebar.text_input("Enter Master Key", type="password")
        
        # 2. Pull the key from Streamlit Secrets
        OWNER_PASSWORD = st.secrets["MASTER_KEY"]

        if st.sidebar.button("✅ CONFIRM: WIPE ALL DATA"):
            if master_key_input == OWNER_PASSWORD:
                try:
                    with conn.session as s:
                        # Get all table names
                        result = s.execute(text("""
                            SELECT tablename FROM pg_catalog.pg_tables 
                            WHERE schemaname = 'public';
                        """))
                        all_tables = [row[0] for row in result]

                        for table in all_tables:
                            if table == 'users':
                                # Keep yourself, delete the rest
                                s.execute(text("DELETE FROM users WHERE role != 'MANAGER'"))
                            else:
                                s.execute(text(f"DELETE FROM {table}"))
                                s.execute(text(f"ALTER SEQUENCE IF EXISTS {table}_id_seq RESTART WITH 1"))
                        
                        s.commit()
                    
                    st.session_state.reset_mode = False
                    st.sidebar.success("System Wiped!")
                    st.rerun()
                    
                except Exception as e:
                    st.sidebar.error(f"Reset Failed: {e}")
            else:
                st.sidebar.error("❌ INVALID MASTER KEY")

        if st.sidebar.button("❌ CANCEL"):
            st.session_state.reset_mode = False
            st.rerun()
            
# --- TOP NOTIFICATION FEED ---
latest_note = conn.query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", ttl=0)
message_text = latest_note.iloc[0]['message'] if not latest_note.empty else "SYSTEM READY"
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {message_text}</div>', unsafe_allow_html=True)

# ==============================================================================
# 1. COMMAND CENTER (TRANSACTION HUB)
# ==============================================================================
if choice == "COMMAND CENTER":
    tab_trans, tab_mem = st.tabs(["NEW TRANSACTION", "REGISTER MEMBERSHIP"])
    
    with tab_trans:
        mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
        st.markdown("---")
        
        # Load Customer Data for Search
        cust_data = conn.query("SELECT * FROM customers", ttl=0)
        
        # Build Search Options
        search_options = ["NEW CUSTOMER"]
        if not cust_data.empty:
            search_options += [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
        
        search_selection = st.selectbox("SEARCH EXISTING CLIENT", search_options)
        
        # Pre-fill data if existing customer selected
        d_plate, d_name, d_phone = "", "", ""
        if search_selection != "NEW CUSTOMER":
            p_key = search_selection.split(" - ")[0]
            # Use Pandas filtering on the fetched dataframe
            match = cust_data[cust_data['plate'] == p_key].iloc[0]
            d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

        col1, col2 = st.columns(2)
        with col1:
            plate = st.text_input("PLATE NUMBER", value=d_plate).upper()
            v_type = st.selectbox("VEHICLE TYPE", ["Sedan", "SUV", "Truck", "Crossover", "Bike", "Other"])
            name = st.text_input("CLIENT NAME", value=d_name)
            c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
            
            # Handle phone number format
            phone_val = d_phone[3:] if d_phone and len(d_phone) > 3 else ""
            phone_raw = st.text_input("PHONE (No leading zero)", value=phone_val)
            
            full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}" if not d_phone else d_phone

        with col2:
            # FIX: Initialize variables before use to prevent NameError
            total_price = 0.0
            item_summary = ""
            lounge_items_sold = []
            staff_assigned = "UNKNOWN"
            
            if mode == "CAR WASH":
                selected = st.multiselect("SERVICES", list(SERVICES.keys()))
                
                # Upsell Logic
                if selected and "Standard Wash" in selected and "Ceramic Wax" not in selected:
                    st.warning("💡 PROMPT: Ask client if they want Ceramic Wax for long-lasting shine!")
                
                total_price = sum([SERVICES[s] for s in selected])
                item_summary = ", ".join(selected)

                # Staff Assignment Logic
                free_staff = get_free_staff_by_dept("WET BAY")
                if not free_staff:
                    st.error("⚠️ NO WET BAY STAFF AVAILABLE")
                    staff_assigned = "NO FREE STAFF"
                else:
                    staff_assigned = st.selectbox("ASSIGN WET BAY DETAILER", free_staff)
            
            else:
                # LOUNGE MODE
                st.subheader("LOUNGE ORDER")
                inv_data = conn.query("SELECT * FROM inventory", ttl=0)
                inv_dict = dict(zip(inv_data['item'], inv_data['price']))
                stock_dict = dict(zip(inv_data['item'], inv_data['stock']))
                
                lounge_items = st.multiselect("SELECT ITEMS", list(inv_dict.keys()))
                
                for item in lounge_items:
                    qty = st.number_input(f"Qty: {item}", min_value=1, max_value=int(stock_dict.get(item, 0)))
                    lounge_items_sold.append((item, qty))
                    total_price += (inv_dict[item] * qty)
                
                item_summary = ", ".join([f"{q}x {i}" for i, q in lounge_items_sold])
                staff_assigned = st.session_state.user_name # Receptionist serves lounge

            st.markdown(f"### TOTAL: ₦{total_price:,}")
            pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash", "Gold Card Credit"])

        if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
            if staff_assigned == "NO FREE STAFF" and mode == "CAR WASH":
                st.error("Cannot authorize. No available staff in the Wet Bay.")
            elif (plate or mode == "LOUNGE") and (mode == "LOUNGE" or (mode == "CAR WASH" and item_summary)):
                
                can_proceed = True
                low_bal = False
                final_sales_total = total_price
                
                # Handle Gold Card Credit Logic
                if pay_method == "Gold Card Credit":
                    # FIX: Removed text() wrapper from conn.query
                    q_mem = "SELECT balance_washes FROM memberships WHERE plate=:p"
                    m_res = conn.query(q_mem, params={"p": plate}, ttl=0)
                    
                    if not m_res.empty and m_res.iloc[0]['balance_washes'] > 0:
                        new_bal = int(m_res.iloc[0]['balance_washes']) - 1
                        
                        # Update Membership Balance
                        with conn.session as s:
                            s.execute(text("UPDATE memberships SET balance_washes=:nb WHERE plate=:p"), {"nb": new_bal, "p": plate})
                            s.commit()
                            
                        final_sales_total = 0.0
                        if new_bal <= 1: low_bal = True
                    else:
                        st.error("No active card or zero balance for this plate.")
                        can_proceed = False

                if can_proceed:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_sales_id = 0
                    
                    # Transaction Block
                    with conn.session as s:
                        # 1. Insert into Sales (PostgreSQL returns ID via RETURNING)
                        # MIGRATION NOTE: Used RETURNING id to get the ID for the receipt
                        res = s.execute(
                            text("""
                                INSERT INTO sales (plate, services, total, method, staff, timestamp, type) 
                                VALUES (:p, :svc, :tot, :meth, :st, :ts, :typ) 
                                RETURNING id
                            """), 
                            {
                                "p": plate, "svc": item_summary, "tot": final_sales_total, 
                                "meth": pay_method, "st": staff_assigned, "ts": now, "typ": mode
                            }
                        )
                        new_sales_id = res.fetchone()[0]
                        
                        # 2. Update Customer (Upsert)
                        # Check visits
                        curr_v_res = s.execute(text("SELECT visits FROM customers WHERE plate=:p"), {"p": plate}).fetchone()
                        curr_visits = curr_v_res[0] if curr_v_res else 0
                        
                        s.execute(text("""
                            INSERT INTO customers (plate, name, phone, visits, last_visit) 
                            VALUES (:p, :n, :ph, :v, :lv)
                            ON CONFLICT (plate) DO UPDATE 
                            SET visits = :v, last_visit = :lv, name = :n, phone = :ph
                        """), {
                            "p": plate, "n": name, "ph": full_phone, 
                            "v": curr_visits + 1, "lv": now.split()[0]
                        })

                        # 3. Mode Specific Updates
                        if mode == "CAR WASH":
                            # Insert into Live Bays
                            # MIGRATION NOTE: wet_staff_history is initialized as NULL (None)
                            s.execute(text("""
                                INSERT INTO live_bays 
                                (plate, status, entry_time, staff, vehicle_type, service_detail, wet_staff_history) 
                                VALUES (:p, 'WET BAY', :t, :s, :vt, :sd, NULL)
                                ON CONFLICT (plate) DO UPDATE 
                                SET status='WET BAY', entry_time=:t, staff=:s, service_detail=:sd
                            """), {
                                "p": plate, "t": now, "s": staff_assigned, 
                                "vt": v_type, "sd": item_summary
                            })
                        else:
                            # Update Inventory
                            for item, qty in lounge_items_sold:
                                s.execute(text("UPDATE inventory SET stock = stock - :q WHERE item = :i"), {"q": qty, "i": item})
                        
                        s.commit()
                    
                    # Store receipt in session state
                    st.session_state['last_receipt'] = {
                        "id": new_sales_id, 
                        "mode": mode, 
                        "name": name, 
                        "plate": plate, 
                        "phone": full_phone,
                        "items": item_summary, 
                        "total": final_sales_total, 
                        "staff": staff_assigned, 
                        "date": now, 
                        "low_bal": low_bal
                    }
                    
                    add_event(f"{mode} AUTH: {plate if plate else 'Lounge'} via {pay_method}")
                    st.rerun()
# ... continue part 2
    with tab_mem:
        st.subheader("ACTIVATE MEMBERSHIP CARD")
        m_plate = st.text_input("SCAN/ENTER PLATE FOR CARD").upper()
        tier = st.selectbox("CARD TIER", ["Silver (5 Washes)", "Gold (10 Washes)", "Platinum (25 Washes)"])
        card_sale_price = st.number_input("CARD SALE PRICE (₦)", min_value=0.0)
        
        # Determine Wash Quantity
        qty = 5
        if "Gold" in tier: qty = 10
        elif "Platinum" in tier: qty = 25
        
        if st.button("ISSUE CARD"):
            if m_plate:
                # 1. Upsert Membership
                # MIGRATION NOTE: Postgres uses ON CONFLICT instead of INSERT OR REPLACE
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO memberships (plate, balance_washes, card_type, sale_price) 
                        VALUES (:p, :b, :c, :s)
                        ON CONFLICT (plate) DO UPDATE 
                        SET balance_washes=:b, card_type=:c, sale_price=:s
                    """), {"p": m_plate, "b": qty, "c": tier, "s": card_sale_price})
                    
                    # 2. Commission Logic for Receptionist
                    receptionist = st.session_state.user_name
                    
                    # Fetch bonus percentage
                    res_p = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": receptionist}).fetchone()
                    
                    if res_p and res_p[0] > 0:
                        comm_amt = card_sale_price * (res_p[0] / 100)
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        s.execute(text("""
                            INSERT INTO earnings_log (username, amount, ref_plate, timestamp) 
                            VALUES (:u, :a, :r, :t)
                        """), {
                            "u": receptionist, "a": comm_amt, 
                            "r": f"NEW_CARD:{m_plate}", "t": now_str
                        })
                    
                    s.commit()
                
                add_event(f"CARD ISSUED: {tier} to {m_plate}")
                st.success(f"Activated {tier} for {m_plate}!")
            else:
                st.error("Plate number required.")
                

    # --- RECEIPT MODAL LOGIC ---
    if 'last_receipt' in st.session_state and st.session_state.last_receipt:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div style="background: white; color: black; padding: 40px; max-width: 500px; margin: 20px auto; border: 1px solid #ddd; border-top: 10px solid black;">
            <div style="text-align: center; border-bottom: 2px solid black; padding-bottom: 20px; margin-bottom: 20px;">
                <h2 style="color: black !important; margin: 0; letter-spacing: 5px;">RIDEBOSS</h2>
                <p style="color: #666 !important; font-size: 12px; margin: 0;">OFFICIAL TRANSACTION SUMMARY</p>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-weight: bold;">REFERENCE:</span> <span>#RB-{r['id']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-weight: bold;">DATE:</span> <span>{r['date']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
                <span style="font-weight: bold;">VEHICLE:</span> <span style="background: black; color: white; padding: 2px 8px;">{r['plate']}</span>
            </div>
            
            <div style="border: 1px solid black; padding: 15px; margin-bottom: 30px;">
                <small style="color: #888; font-weight: bold;">DESCRIPTION</small><br>
                <div style="font-size: 18px; margin-top: 5px;">{r['items']}</div>
            </div>

            <div style="display: flex; justify-content: space-between; border-top: 2px solid black; padding-top: 15px;">
                <span style="font-size: 18px; font-weight: bold;">AMOUNT PAID</span>
                <span style="font-size: 22px; font-weight: 900;">₦{r['total']:,}</span>
            </div>
            <p style="text-align: center; margin-top: 40px; font-size: 10px; color: #999; letter-spacing: 2px;">AUTHENTIC RIDEBOSS DOCUMENT</p>
        </div>
        """, unsafe_allow_html=True)
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            # Construct URL for the Print Renderer
            receipt_payload = { 
                "id": r["id"], "date": r["date"], "plate": r["plate"], 
                "items": r["items"], "total": r["total"] 
            }
            receipt_url = f"?print_receipt={urllib.parse.quote(json.dumps(receipt_payload))}"
            
            st.markdown(f'''
                <a href="{receipt_url}" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; height:3.5em; border:2px solid black; background:black; color:white; font-weight:bold; cursor:pointer; text-transform:uppercase; letter-spacing:2px;">
                        🖨️ PRINT RECEIPT
                    </button>
                </a>
            ''', unsafe_allow_html=True)
            
        with c_p2:
            if st.button("CLOSE & DISMISS"):
                del st.session_state['last_receipt']
                st.rerun()

# ==============================================================================
# 2. LIVE U-FLOW (MONITORING SYSTEM)
# ==============================================================================
elif choice == "LIVE U-FLOW":
    # 1. Initialize notification state so it doesn't crash if accessed directly
    if 'wa_pending' not in st.session_state:
        st.session_state.wa_pending = None

    view_mode = st.radio("VIEW MODE", ["Management controls", "External Flight Board"], horizontal=True)
    
    # Fetch Live Data
    live_cars = conn.query("SELECT * FROM live_bays", ttl=0)
    
    if view_mode == "External Flight Board":
        # 1. FIXED FULLSCREEN BUTTON (Targets the Parent Window)
        st.button("📺 ACTIVATE FULLSCREEN", on_click=None, use_container_width=True, help="Click to expand to TV view")
        
        st.markdown("""
            <script>
                // This script runs in the parent context to bypass iframe sandbox
                const doc = window.parent.document;
                const button = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('ACTIVATE FULLSCREEN'));
                
                if (button) {
                    button.onclick = function() {
                        const elem = doc.documentElement;
                        if (!doc.fullscreenElement) {
                            elem.requestFullscreen().catch(err => {
                                console.error(`Error attempting to enable full-screen mode: ${err.message}`);
                            });
                        } else {
                            doc.exitFullscreen();
                        }
                    };
                }
            </script>
        """, unsafe_allow_html=True)

        # 2. HIDE UI
        st.markdown("<style>header, footer, .stAppDeployButton {display:none !important;}</style>", unsafe_allow_html=True)
        
        # 3. FLIGHT BOARD DISPLAY WITH CLOCK
        st.markdown("<h1 style='text-align:center; color:#00d4ff; margin:0;'>WORKFLOW MONITOR</h1>", unsafe_allow_html=True)
        
        if live_cars.empty:
            st.info("ALL BAYS CLEAR.")
        else:
            # Generating HTML for the Scrolling Monitor with Clock overlay
            monitor_html = f"""
            <style>
                body {{ background-color: #050505; margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }}
                .monitor-container {{ background: #000; height: 100vh; width: 100%; position: relative; overflow: hidden; }}
                
                .clock-overlay {{
                    position: absolute; top: 10px; right: 20px; text-align: right;
                    color: white; font-family: monospace; z-index: 100; background: rgba(0,0,0,0.5);
                    padding: 10px; border-radius: 8px; border: 1px solid #222;
                }}
                #time {{ font-size: 32px; color: #00d4ff; font-weight: bold; }}
                #date {{ font-size: 16px; color: #888; }}

                .scroll-content {{ position: absolute; width: 100%; animation: scrollUp 30s linear infinite; }}
                @keyframes scrollUp {{ 0% {{ transform: translateY(100%); }} 100% {{ transform: translateY(-100%); }} }}
                .monitor-row {{ display: flex; justify-content: space-between; align-items: center; padding: 30px; border-bottom: 2px solid #222; background: #050505; color: white; }}
                .monitor-plate {{ font-size: 50px; font-weight: 900; color: #00d4ff; font-family: 'Courier New', monospace; line-height: 1; }}
                .monitor-status {{ font-size: 18px; color: #FFD700; font-weight: bold; text-transform: uppercase; }}
                .monitor-meta {{ text-align: right; }}
                .monitor-staff {{ font-size: 20px; color: #888; text-transform: uppercase; }}
                .monitor-svc {{ color: #00d4ff; font-style: italic; font-size: 22px; }}
            </style>

            <div class="monitor-container">
                <div class="clock-overlay">
                    <div id="time"></div>
                    <div id="date"></div>
                </div>
                <div class="scroll-content">"""
            
            # Duplicate data to create seamless scroll loop
            scroll_data = pd.concat([live_cars, live_cars])
            
            for _, row in scroll_data.iterrows():
                monitor_html += f"""
                <div class="monitor-row">
                    <div class="monitor-plate">{row['plate']}<br><span style="font-size:18px; color:#555;">{row['vehicle_type']}</span></div>
                    <div style="flex:1; padding-left:40px;"><div class="monitor-svc">SERVICE: {row['service_detail']}</div></div>
                    <div class="monitor-meta">
                        <div class="monitor-status">{row['status']}</div>
                        <div class="monitor-staff">ASSIGNED: {row['staff']}</div>
                    </div>
                </div>"""
            
            monitor_html += """
                </div>
            </div>

            <script>
                function updateClock() {
                    var now = new Date();
                    var h = now.getHours().toString().padStart(2, '0');
                    var m = now.getMinutes().toString().padStart(2, '0');
                    var s = now.getSeconds().toString().padStart(2, '0');
                    document.getElementById('time').innerHTML = h + ':' + m + ':' + s;
                    document.getElementById('date').innerHTML = now.toDateString().toUpperCase();
                }
                setInterval(updateClock, 1000);
                updateClock();
            </script>
            """
            import streamlit.components.v1 as components
            components.html(monitor_html, height=800)
    else:
        # --- MANAGEMENT CONTROLS ---
        
        # PERSISTENT WHATSAPP NOTIFICATION BOX
        if st.session_state.wa_pending:
            st.markdown(f"""
                <div style="background-color:#050505; border:2px solid #25D366; padding:20px; border-radius:10px; margin-bottom:20px; text-align:center;">
                    <h3 style="color:#25D366; margin:0;">Vehicle Released: {st.session_state.wa_pending['plate']}</h3>
                    <p style="color:white; margin:10px 0;">Click below to send the ready prompt to the customer.</p>
                    <a href="{st.session_state.wa_pending['url']}" target="_blank" style="text-decoration:none;">
                        <button style="background-color:#25D366; color:white; padding:15px 40px; border:none; border-radius:8px; font-weight:bold; cursor:pointer; width:100%; font-size:16px;">
                            📲 SEND WHATSAPP MESSAGE
                        </button>
                    </a>
                </div>
            """, unsafe_allow_html=True)
            if st.button("❌ DISMISS NOTIFICATION", use_container_width=True):
                st.session_state.wa_pending = None
                st.rerun()
            st.divider()

        # RENDER CAR LIST
        if live_cars.empty:
            st.info("No vehicles currently in the bays.")
            
        for idx, row in live_cars.iterrows():
            # Calculate time spent
            try:
                entry_dt = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M")
                time_spent = (datetime.now() - entry_dt).seconds // 60
            except:
                time_spent = 0
                
            border_color = "#00d4ff" if time_spent < 40 else "#FF3B30"
            
            st.markdown(f'<div class="status-card" style="border-left: 10px solid {border_color};">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### {row['plate']} ({row['vehicle_type']})")
                st.write(f"**SERVICES:** {row['service_detail']}")
                st.write(f"**ZONE:** {row['status']}")
            with c2:
                st.write(f"**DETAILER:** {row['staff']}")
                st.write(f"**ELAPSED:** {time_spent} mins")
            with c3:
                # --- WET TO DRY LOGIC ---
                if row['status'] == "WET BAY":
                    with st.popover("TO DRY BAY"):
                        dry_staff = get_free_staff_by_dept("DRY BAY")
                        new_dry_detailer = st.selectbox("Assign Dry Bay", dry_staff if dry_staff else ["NO FREE STAFF"], key=f"dry_{idx}")
                        
                        if st.button("Confirm Handover", key=f"hnd_{idx}"):
                            if new_dry_detailer != "NO FREE STAFF":
                                with conn.session as s:
                                    s.execute(text("""
                                        UPDATE live_bays 
                                        SET status='DRY BAY', staff=:ns, wet_staff_history=:ws 
                                        WHERE plate=:p
                                    """), {
                                        "ns": new_dry_detailer, "ws": row['staff'], "p": row['plate']
                                    })
                                    s.commit()
                                add_event(f"{row['plate']} moved to Dry Bay")
                                st.rerun()
                
                # --- AUTOMATED COMMISSION RELEASE LOGIC ---
                if st.button(f"RELEASE {row['plate']}", key=f"rel_{idx}"):
                    # 1. Fetch the latest sale amount for this plate
                    sale_data = conn.query("SELECT total FROM sales WHERE plate=:p ORDER BY id DESC LIMIT 1", params={"p": row['plate']}, ttl=0)
                    
                    if not sale_data.empty:
                        # Ensure numeric types for calculation
                        sale_total = float(sale_data.iloc[0]['total'])
                        current_staff = row['staff']
                        prev_staff = row['wet_staff_history']
                        
                        # Filter out empty or 'None' staff entries
                        staff_to_pay = [s for s in [current_staff, prev_staff] if s and str(s).lower() != 'none' and str(s).strip() != '']
                        
                        with conn.session as s:
                            for s_member in staff_to_pay:
                                # Look up this specific staff's bonus percentage
                                p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": s_member}).fetchone()
                                
                                # Only insert if staff has a config and bonus > 0
                                if p_res and p_res[0] is not None and p_res[0] > 0:
                                    comm_amt = sale_total * (float(p_res[0]) / 100)
                                    
                                    # POSTGRES FIX: Use native datetime object, not a string
                                    s.execute(text("""
                                        INSERT INTO earnings_log (username, amount, ref_plate, timestamp) 
                                        VALUES (:u, :a, :r, :t)
                                    """), {
                                        "u": s_member, 
                                        "a": comm_amt, 
                                        "r": str(row['plate']), 
                                        "t": datetime.now() 
                                    })
                            s.commit()

                    # 2. WhatsApp Notification Setup
                    cust_info = conn.query("SELECT name, phone FROM customers WHERE plate=:p", params={"p": row['plate']}, ttl=0)
                    if not cust_info.empty:
                        c_name = cust_info.iloc[0]['name']
                        c_phone = cust_info.iloc[0]['phone']
                        wa_msg = f"Hi {c_name}, your vehicle ({row['plate']}) is ready for pickup! Thank you for choosing RideBoss Autos."
                        st.session_state.wa_pending = {
                            "url": format_whatsapp(c_phone, wa_msg),
                            "plate": row['plate']
                        }

                    # 3. Final Removal from Live Bays
                    with conn.session as s:
                        s.execute(text("DELETE FROM live_bays WHERE plate=:p"), {"p": row['plate']})
                        s.commit()
                        
                    add_event(f"RELEASED: {row['plate']}")
                    st.rerun()

                    # 2. Capture WhatsApp Info BEFORE deleting car
                    # FIX: Removed text() wrapper from conn.query call
                    cust_info = conn.query("SELECT name, phone FROM customers WHERE plate=:p", params={"p": row['plate']}, ttl=0)
                    
                    if not cust_info.empty:
                        c_name = cust_info.iloc[0]['name']
                        c_phone = cust_info.iloc[0]['phone']
                        wa_msg = f"Hi {c_name}, your vehicle ({row['plate']}) is ready for pickup! Thank you for choosing RideBoss Autos."
                        
                        # Set the sticky notification data
                        st.session_state.wa_pending = {
                            "url": format_whatsapp(c_phone, wa_msg),
                            "plate": row['plate']
                        }

                    # 3. Complete Release (Delete from Live Bays)
                    with conn.session as s:
                        s.execute(text("DELETE FROM live_bays WHERE plate=:p"), {"p": row['plate']})
                        s.commit()
                        
                    add_event(f"{row['plate']} Released.")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 3. ONBOARD STAFF (MANAGER ONLY)
# ==============================================================================
elif choice == "ONBOARD STAFF" and st.session_state.user_role == "MANAGER":
    st.subheader("STAFF ONBOARDING")
    
    with st.form("new_staff"):
        s_name = st.text_input("Full Name")
        s_pass = st.text_input("Login Password", type="password")
        s_role = st.selectbox("System Role", ["STAFF", "MANAGER"])
        s_dept = st.selectbox("Department", ["WET BAY", "DRY BAY", "RECEPTIONIST", "MANAGEMENT"])
        
        if st.form_submit_button("ONBOARD STAFF"):
            if s_name and s_pass:
                # Default Verified=0 for staff
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO users (username, password, role, dept, status, verified) 
                        VALUES (:u, :p, :r, :d, 'ACTIVE', 0)
                        ON CONFLICT (username) DO UPDATE 
                        SET password=:p, role=:r, dept=:d
                    """), {
                        "u": s_name, "p": s_pass, "r": s_role, "d": s_dept
                    })
                    s.commit()
                st.success(f"{s_name} added to {s_dept}.")
                st.rerun()
                
    st.write("---")
    st.subheader("CURRENT STAFF DIRECTORY")
    
    current_staff_df = conn.query("SELECT username, dept, role, status, verified FROM users", ttl=0)
    st.dataframe(current_staff_df, use_container_width=True)
    
    target_staff = st.selectbox("Select Staff Member to Manage", ["None"] + current_staff_df['username'].tolist())
    
    if st.button("DEACTIVATE STAFF") and target_staff != "None":
        with conn.session as s:
            s.execute(text("UPDATE users SET status='INACTIVE' WHERE username=:u"), {"u": target_staff})
            s.commit()
        st.success(f"Deactivated {target_staff}")
        st.rerun()

# ==============================================================================
# 4. BOSS HR PORTAL (MANAGER ONLY)
# ==============================================================================
elif choice == "BOSS HR" and st.session_state.user_role == "MANAGER":
    st.subheader("BOSS HUMAN RESOURCES")
    
    hr_t1, hr_t2, hr_t3 = st.tabs(["PENDING APPROVALS", "ACTIVE STAFF DOSSIERS", "SALARY CONFIG"])
    
    with hr_t1:
        # PENDING VERIFICATIONS
        # Bypass conn.query to avoid serialization errors with binary image data
        query_pending = """
            SELECT * FROM staff_profiles 
            WHERE username IN (SELECT username FROM users WHERE verified=0)
        """
        with conn.session as s:
            res_pending = s.execute(text(query_pending))
            pending_staff = pd.DataFrame(res_pending.fetchall(), columns=res_pending.keys())
        
        if pending_staff.empty:
            st.info("No pending verifications.")
        else:
            for idx, row in pending_staff.iterrows():
                with st.expander(f"REVIEW: {row['username']} ({row['full_name']})"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if row['id_image']:
                            try:
                                # Postgres returns binary as bytes or memoryview
                                img_data = row['id_image']
                                if isinstance(img_data, memoryview):
                                    img_data = img_data.tobytes()
                                image = Image.open(io.BytesIO(img_data))
                                st.image(image, caption=row['id_type'], use_container_width=True)
                            except Exception as e:
                                st.error(f"Display Error: {e}")
                    with c2:
                        st.write(f"**NIN:** {row['nin']}")
                        st.write(f"**Address:** {row['address']}")
                        st.write(f"**Bank:** {row['bank_name']} - {row['account_no']}")
                        
                        if st.button("APPROVE & VERIFY", key=f"app_{idx}"):
                            with conn.session as s:
                                s.execute(text("UPDATE users SET verified=1 WHERE username=:u"), {"u": row['username']})
                                s.execute(text("""
                                    INSERT INTO staff_payroll_config (username, base_salary, bonus_pc) 
                                    VALUES (:u, 0, 0)
                                    ON CONFLICT (username) DO NOTHING
                                """), {"u": row['username']})
                                s.commit()
                            st.success(f"Verified {row['username']}!")
                            st.rerun()

    with hr_t2:
        # ACTIVE STAFF TABLE
        active_staff = conn.query("SELECT username FROM users WHERE verified=1 AND role='STAFF'", ttl=0)
        st.dataframe(active_staff, use_container_width=True)
        
        staff_list = active_staff['username'].tolist() if not active_staff.empty else []
        selected_staff = st.selectbox("SELECT STAFF TO VIEW FULL DETAILS", ["-- Select --"] + staff_list)
        
        if selected_staff != "-- Select --":
            # Fetch profile using session to avoid caching errors with image
            with conn.session as s:
                res_prof = s.execute(text("SELECT * FROM staff_profiles WHERE username=:u"), {"u": selected_staff})
                s_prof = pd.DataFrame(res_prof.fetchall(), columns=res_prof.keys())
            
            if not s_prof.empty:
                row = s_prof.iloc[0]
                base, d_com, m_com, y_com, total_m = calculate_payouts(selected_staff)
                
                st.markdown("---")
                col_d1, col_d2 = st.columns([1, 2])
                with col_d1:
                    if row['id_image']:
                        try:
                            img_data = row['id_image']
                            if isinstance(img_data, memoryview):
                                img_data = img_data.tobytes()
                            image = Image.open(io.BytesIO(img_data))
                            st.image(image, caption=f"{selected_staff}'s ID")
                        except:
                            st.warning("ID Image format incompatible.")
                with col_d2:
                    st.markdown(f"### {row['full_name']}")
                    st.write(f"**Phone:** {row['phone']}")
                    st.write(f"**NIN:** {row['nin']}")
                    st.write(f"**Bank:** {row['bank_name']} | {row['account_no']}")
                    st.info(f"💰 BASE SALARY: ₦{base:,} | BONUS %: SET IN CONFIG")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Daily Bonus", f"₦{d_com:,}")
                    m2.metric("Monthly Bonus", f"₦{m_com:,}")
                    m3.metric("Yearly Bonus", f"₦{y_com:,}")
                    st.success(f"**ESTIMATED PAYOUT THIS MONTH:** ₦{total_m:,}")

    with hr_t3:
        # SALARY CONFIG
        st.write("Configure Payroll Parameters")
        all_staff_df = conn.query("SELECT username FROM users WHERE role='STAFF'", ttl=0)
        all_staff_list = all_staff_df['username'].tolist() if not all_staff_df.empty else []
        
        config_staff = st.selectbox("Select Staff to Config", ["-- Select --"] + all_staff_list)
        
        if config_staff != "-- Select --":
            # Direct query without text() wrapper inside conn.query
            curr = conn.query("SELECT base_salary, bonus_pc FROM staff_payroll_config WHERE username=:u", params={"u": config_staff}, ttl=0)
            
            curr_base = curr.iloc[0]['base_salary'] if not curr.empty else 0.0
            curr_bon = curr.iloc[0]['bonus_pc'] if not curr.empty else 0.0
            
            with st.form("sal_conf"):
                new_base = st.number_input("Monthly Base Salary (₦)", value=float(curr_base))
                new_bon = st.number_input("Commission Percentage per Car (%)", value=float(curr_bon))
                
                if st.form_submit_button("UPDATE PAYROLL CONFIG"):
                    with conn.session as s:
                        s.execute(text("""
                            INSERT INTO staff_payroll_config (username, base_salary, bonus_pc) 
                            VALUES (:u, :bs, :bp)
                            ON CONFLICT (username) DO UPDATE 
                            SET base_salary=:bs, bonus_pc=:bp
                        """), {"u": config_staff, "bs": new_base, "bp": new_bon})
                        s.commit()
                    st.success(f"Payroll updated for {config_staff}")
                    st.rerun()

# ==============================================================================
# 5. INVENTORY & STAFF (MANAGER ONLY)
# ==============================================================================
elif choice == "INVENTORY & STAFF" and st.session_state.user_role == "MANAGER":
    t1, t2, t3 = st.tabs(["Lounge Inventory", "Wash Price List", "Staff Performance"])
    
    with t1:
        with st.form("new_item"):
            ni_name = st.text_input("Item Name")
            ni_stock = st.number_input("Stock", min_value=0.0)
            ni_unit = st.text_input("Unit")
            ni_price = st.number_input("Price (₦)", min_value=0.0)
            
            if st.form_submit_button("ADD/UPDATE"):
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO inventory (item, stock, unit, price) 
                        VALUES (:i, :s, :u, :p)
                        ON CONFLICT (item) DO UPDATE 
                        SET stock=:s, unit=:u, price=:p
                    """), {"i": ni_name, "s": ni_stock, "u": ni_unit, "p": ni_price})
                    s.commit()
                st.rerun()
                
        inv_data = conn.query("SELECT * FROM inventory", ttl=0)
        st.dataframe(inv_data, use_container_width=True)
        
    with t2:
        st.subheader("EDIT SERVICES & PRICES")
        edit_svc_list = list(SERVICES.keys())
        svc_to_edit = st.selectbox("Select Service to Modify", ["-- ADD NEW --"] + edit_svc_list)
        
        current_price_val = 0.0
        current_name_val = ""
        
        if svc_to_edit != "-- ADD NEW --":
            current_name_val = svc_to_edit
            current_price_val = SERVICES[svc_to_edit]
            
        with st.form("svc_form"):
            new_name = st.text_input("Service Name", value=current_name_val)
            new_price = st.number_input("Service Price (₦)", value=float(current_price_val))
            
            sub_col1, sub_col2 = st.columns(2)
            
            if sub_col1.form_submit_button("SAVE SERVICE"):
                with conn.session as s:
                    if svc_to_edit != "-- ADD NEW --" and new_name != svc_to_edit:
                        s.execute(text("DELETE FROM wash_prices WHERE service=:s"), {"s": svc_to_edit})
                    
                    s.execute(text("""
                        INSERT INTO wash_prices (service, price) 
                        VALUES (:n, :p)
                        ON CONFLICT (service) DO UPDATE SET price=:p
                    """), {"n": new_name, "p": new_price})
                    s.commit()
                st.rerun()
                
            if svc_to_edit != "-- ADD NEW --":
                if sub_col2.form_submit_button("DELETE SERVICE"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM wash_prices WHERE service=:s"), {"s": svc_to_edit})
                        s.commit()
                    st.rerun()
                    
    with t3:
        st.subheader("STAFF RANKING (TOTAL TASKS)")
        # This query "taps" into both staff columns from your sales table
        perf_query = """
            SELECT staff_member, COUNT(*) as tasks, SUM(total) as revenue_impact
            FROM (
                SELECT staff as staff_member, total FROM sales WHERE staff IS NOT NULL AND staff != ''
                UNION ALL
                SELECT dry_staff as staff_member, 0 FROM sales WHERE dry_staff IS NOT NULL AND dry_staff != ''
            ) AS combined_data
            GROUP BY staff_member
            ORDER BY tasks DESC
        """
        try:
            perf_df = conn.query(perf_query, ttl=0)
            if not perf_df.empty:
                st.bar_chart(perf_df.set_index('staff_member')['tasks'])
                st.dataframe(
                    perf_df, 
                    use_container_width=True,
                    column_config={
                        "staff_member": "Staff Name",
                        "tasks": "Cars Handled",
                        "revenue_impact": st.column_config.NumberColumn("Revenue (Wet Bay)", format="₦%.2f")
                    }
                )
            else:
                st.info("No performance data yet.")
        except:
            st.info("Performance system ready. Data will appear as soon as cars are released.")
# ==============================================================================
# 6. FINANCIALS (INTELLIGENCE CENTER)
# ==============================================================================
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    st.subheader("FINANCIAL INTELLIGENCE CENTER")
    tab_fin, tab_cards_hub = st.tabs(["TRANSPARENT REVENUE", "MEMBERSHIP HUB"])
    
    with tab_fin:
        col_f1, col_f2 = st.columns([1, 2])
        view_scope = col_f1.radio("REPORTING SCOPE", ["DAILY", "MONTHLY", "YEARLY"], horizontal=True)
        
        # Load raw data into Pandas for flexible filtering without complex SQL
        sales_raw = conn.query("SELECT * FROM sales", ttl=0)
        exp_raw = conn.query("SELECT * FROM expenses", ttl=0)
        m_sales_raw = conn.query("SELECT plate, card_type, sale_price FROM memberships", ttl=0)
        
        # Add dummy timestamp for membership sales since table doesn't have one (per requirements)
        # Assuming membership sales count towards current year for simplicity or added date logic
        m_sales_raw['timestamp'] = datetime.now() 
        
        # Convert timestamps
        sales_raw['timestamp'] = pd.to_datetime(sales_raw['timestamp'])
        exp_raw['timestamp'] = pd.to_datetime(exp_raw['timestamp'])
        
        now = datetime.now()
        label = ""
        
        # Filtering Logic
        if view_scope == "DAILY":
            selected_date = col_f2.date_input("SELECT DAY", now.date())
            f_sales = sales_raw[sales_raw['timestamp'].dt.date == selected_date]
            f_exps = exp_raw[exp_raw['timestamp'].dt.date == selected_date]
            label = f"REPORT FOR {selected_date}"
            # Cards don't have date tracking in this schema, so exclude from daily
            card_total = 0 
            
        elif view_scope == "MONTHLY":
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            selected_month_name = col_f2.selectbox("SELECT MONTH", months, index=now.month-1)
            selected_month = months.index(selected_month_name) + 1
            
            f_sales = sales_raw[(sales_raw['timestamp'].dt.month == selected_month) & (sales_raw['timestamp'].dt.year == now.year)]
            f_exps = exp_raw[(exp_raw['timestamp'].dt.month == selected_month) & (exp_raw['timestamp'].dt.year == now.year)]
            label = f"REPORT FOR {selected_month_name} {now.year}"
            # Assume cards count for the running year, or show all if simpler
            card_total = m_sales_raw['sale_price'].sum() # Showing total lifetime card sales as per original logic approximation
            
        else:
            current_year = now.year
            year_options = list(range(2024, current_year + 1))
            selected_year = col_f2.selectbox("SELECT YEAR", year_options, index=len(year_options)-1)
            
            f_sales = sales_raw[sales_raw['timestamp'].dt.year == selected_year]
            f_exps = exp_raw[exp_raw['timestamp'].dt.year == selected_year]
            label = f"ANNUAL REPORT {selected_year}"
            card_total = m_sales_raw['sale_price'].sum()

        rev_wash = f_sales[f_sales['type'] == 'CAR WASH']['total'].sum()
        rev_lounge = f_sales[f_sales['type'] == 'LOUNGE']['total'].sum()
        total_exp = f_exps['amount'].sum()
        net_profit = (rev_wash + rev_lounge + card_total) - total_exp

        st.markdown(f"### {label}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("WASH REVENUE", f"₦{rev_wash:,}")
        m2.metric("LOUNGE REVENUE", f"₦{rev_lounge:,}")
        m3.metric("CARD SALES (LIFETIME)", f"₦{card_total:,}")
        m4.metric("EXPENSES", f"₦{total_exp:,}")
        m5.metric("NET PROFIT/LOSS", f"₦{net_profit:,}", delta=net_profit, delta_color="normal")
        
        st.markdown("---")
        chart_data = pd.DataFrame({
            'Category': ['Wash', 'Lounge', 'Cards', 'Expenses'], 
            'Amount': [rev_wash, rev_lounge, card_total, total_exp]
        })
        st.bar_chart(chart_data.set_index('Category'))
        
        st.subheader("Detailed Transaction Log")
        st.dataframe(f_sales, use_container_width=True)
        
        csv = f_sales.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DOWNLOAD FILTERED REPORT (CSV)", csv, f"RideBoss_{view_scope}_{label}.csv", "text/csv")
        
        with st.expander("LOG NEW EXPENSE"):
            e_desc = st.text_input("Description")
            e_amt = st.number_input("Amount", min_value=0.0)
            if st.button("LOG EXPENSE"):
                with conn.session as s:
                    s.execute(text("INSERT INTO expenses (description, amount, timestamp) VALUES (:d, :a, :t)"), 
                              {"d": e_desc, "a": e_amt, "t": datetime.now().strftime("%Y-%m-%d")})
                    s.commit()
                st.success("Expense Logged.")
                st.rerun()

    with tab_cards_hub:
        m_df = conn.query("SELECT * FROM memberships", ttl=0)
        
        if m_df.empty:
            st.info("No Active Memberships")
            
        for idx, row in m_df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['plate']}** ({row['card_type']})")
                c2.write(f"Bal: {row['balance_washes']} left")
                
                # Top Up Button
                if c3.button(f"TOP UP {row['plate']}", key=f"up_{idx}"):
                    # 1. Update Balance (Reset to standard pack size or add? Original code set to 10/fixed)
                    # Let's derive top up amount based on card type string
                    top_up_qty = 5
                    if "Gold" in row['card_type']: top_up_qty = 10
                    elif "Platinum" in row['card_type']: top_up_qty = 25
                    
                    with conn.session as s:
                        s.execute(text("UPDATE memberships SET balance_washes = :b WHERE plate=:p"), 
                                  {"b": top_up_qty, "p": row['plate']})
                    
                        # 2. Log Commission
                        receptionist = st.session_state.user_name
                        p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), 
                                          {"u": receptionist}).fetchone()
                        
                        if p_res and p_res[0] > 0:
                            comm_amt = row['sale_price'] * (p_res[0] / 100)
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            s.execute(text("""
                                INSERT INTO earnings_log (username, amount, ref_plate, timestamp) 
                                VALUES (:u, :a, :r, :t)
                            """), {
                                "u": receptionist, "a": comm_amt, 
                                "r": f"REFILL:{row['plate']}", "t": now_str
                            })
                        s.commit()
                        
                    st.success(f"Refilled {row['plate']} & Commission Logged!")
                    st.rerun()

                # Delete Button
                if c4.button(f"DELETE {row['plate']}", key=f"del_{idx}"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM memberships WHERE plate=:p"), {"p": row['plate']})
                        s.commit()
                    st.rerun()
                
                st.markdown("---")     

# ==============================================================================
# 7. CRM & RETENTION
# ==============================================================================
elif choice == "CRM & RETENTION" and st.session_state.user_role == "MANAGER":
    st.subheader("RETENTION PANEL")
    cust_df = conn.query("SELECT * FROM customers", ttl=0)
    
    if cust_df.empty:
        st.info("No customer data available.")
    else:
        for idx, row in cust_df.iterrows():
            try:
                # Convert the stored string date back to a Python object
                last_v = datetime.strptime(row['last_visit'], "%Y-%m-%d")
                days_since = (datetime.now() - last_v).days
                
                # Determine status color
                color = "#00d4ff" if days_since < 7 else "#FFD700" if days_since < 14 else "#FF3B30"
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                        <div style='padding:10px; border-left: 4px solid {color}; background:#111; margin-bottom:5px;'>
                            <b style='color:white;'>{row['name']}</b> <span style='color:#888;'>[{row['plate']}]</span><br>
                            <small style='color:{color};'>{days_since} days since last visit</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # ONLY show the button if it's been 7 days or more
                    if days_since >= 7:
                        msg = f"Hello {row['name']}, we noticed your car ({row['plate']}) hasn't been to RideBoss in {days_since} days! Ready for a fresh shine? We're open today!"
                        wa_link = format_whatsapp(row['phone'], msg)
                        
                        # Use a link button for the WhatsApp API
                        st.markdown(f"""
                            <a href="{wa_link}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366; color:white; padding:10px; text-align:center; font-size:12px; font-weight:bold; border-radius:5px;">
                                    REACH OUT
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
            except Exception as e:
                # Skip rows with invalid date formats
                continue
elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM HISTORY")
    notes = conn.query('SELECT timestamp as "TIME", message as "EVENT" FROM notifications ORDER BY id DESC LIMIT 50', ttl=0)
    st.table(notes)

# ==============================================================================
# 8. MY EARNINGS (STAFF VIEW)
# ==============================================================================
elif choice == "MY EARNINGS":
    st.subheader(f"EARNINGS DASHBOARD: {st.session_state.user_name}")
    base, d_com, m_com, y_com, total_m = calculate_payouts(st.session_state.user_name)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("COMMISSION (TODAY)", f"₦{d_com:,}")
    col2.metric("COMMISSION (THIS MONTH)", f"₦{m_com:,}")
    col3.metric("TOTAL PAYOUT (BASE + BONUS)", f"₦{total_m:,}")
    
    st.write("### RECENT EARNINGS LOG")
    # FIX: Removed text() wrapper from conn.query call
    e_log = conn.query("""
        SELECT timestamp, ref_plate, amount 
        FROM earnings_log 
        WHERE username=:u 
        ORDER BY id DESC LIMIT 20
    """, params={"u": st.session_state.user_name}, ttl=0)
    
    st.table(e_log)
