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

# --- FIXED RIDEBOSS ULTRA LUXURY CSS ---
st.markdown("""
    <style>
    /* 1. CORE ENGINE & AMBIENT GLOW BUBBLES */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    .stApp { 
        background-color: #07090d;
        background-image: 
            radial-gradient(at 15% 15%, rgba(59, 130, 246, 0.18) 0px, transparent 40%),
            radial-gradient(at 85% 20%, rgba(37, 99, 235, 0.12) 0px, transparent 35%),
            radial-gradient(at 50% 85%, rgba(29, 78, 216, 0.1) 0px, transparent 45%);
        color: #e2e8f0; 
        font-family: 'Outfit', sans-serif;
    }

    /* 2. HEADER & HAMBURGER FIX */
    /* Make the header area transparent so the button stays visible but the bar is 'gone' */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: white !important;
    }
    
    /* Ensure the hamburger icon is bright and visible */
    header[data-testid="stHeader"] svg {
        fill: #3b82f6 !important;
    }

    /* 3. SIDEBAR - INDUSTRIAL NAV TILES */
    section[data-testid="stSidebar"] {
        background: rgba(13, 16, 23, 0.98) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 14px 18px !important;
        border-radius: 6px;
        margin-bottom: 10px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        color: #64748b;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255, 255, 255, 0.06);
        color: #ffffff;
        transform: translateX(8px);
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] [data-checked="true"] {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, rgba(30, 41, 59, 0) 100%) !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
        border-left: 4px solid #3b82f6 !important;
        color: #ffffff !important;
    }

    /* 4. ULTRA GLASS CARDS & METRICS */
    .status-card, [data-testid="metric-container"] { 
        background: rgba(17, 25, 40, 0.6) !important;
        backdrop-filter: blur(12px) saturate(160%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 24px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    }

    /* 5. THE BLUE NOTIFICATION BAR */
    .notification-bar { 
        background: linear-gradient(90deg, #1e40af 0%, #3b82f6 50%, #1e40af 100%);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 12px 30px; 
        border-radius: 50px; 
        color: #ffffff; 
        font-size: 0.85rem; 
        font-weight: 800; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        margin-bottom: 40px; 
        text-align: center;
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.4);
    }

    /* 6. INPUTS & FORM ELEMENTS */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea {
        background-color: #0f172a !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
    }

    /* 7. BUTTONS */
    .stButton>button { 
        background: #1e293b;
        border: 1px solid #334155; 
        border-radius: 8px; 
        color: #ffffff; 
        font-weight: 700;
        text-transform: uppercase;
        width: 100%;
        transition: 0.3s;
    }

    .stButton>button:hover { 
        background: #3b82f6;
        box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
    }

    /* 8. LIVE U-FLOW MONITOR */
    .monitor-container { 
        background: #000000; 
        border: 2px solid #1e293b;
        border-radius: 20px; 
        box-shadow: 0 0 50px rgba(0,0,0,0.9);
        height: 650px;
    }

    .monitor-row { 
        background: rgba(255,255,255,0.02);
        margin: 12px;
        padding: 24px;
        border-radius: 12px;
    }

    .monitor-plate { 
        font-size: 42px; 
        font-weight: 900; 
        color: #ffffff; 
        letter-spacing: 3px;
    }

    .monitor-status { 
        background: #fbbf24;
        color: #000;
        padding: 3px 12px;
        border-radius: 4px;
        font-weight: 900;
    }

    /* Clean up */
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
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

        # 13. PROMOTIONS TABLE (NEW - FOR VIP CODES)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS promotions (
                code TEXT PRIMARY KEY, 
                discount_pc REAL, 
                status TEXT DEFAULT 'ACTIVE', 
                created_for_plate TEXT,
                created_at TEXT
            )
        """))

        # 14. SYSTEM SETTINGS (NEW - FOR VIP RULES)
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key TEXT PRIMARY KEY, 
                setting_value TEXT
            )
        """))
        
        # Seed Default Settings (Defaults: 10 visits = 20% off)
        s.execute(text("""
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES ('vip_milestone', '10'), ('vip_discount', '20')
            ON CONFLICT (setting_key) DO NOTHING
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
    Returns a list of active staff in a department who are NOT currently in any bay.
    """
    # 1. Get names of staff currently working on a car in live_bays
    busy_df = conn.query("SELECT staff FROM live_bays WHERE staff IS NOT NULL", ttl=0)
    busy_list = busy_df['staff'].tolist() if not busy_df.empty else []
    
    # 2. Get all verified staff in department
    query = "SELECT username FROM users WHERE dept = :d AND status = 'ACTIVE' AND verified = 1"
    try:
        staff_df = conn.query(query, params={"d": dept_name}, ttl=0)
        if staff_df.empty:
            return []
        
        all_dept_staff = staff_df['username'].tolist()
        
        # 3. Filter: Only return staff NOT in the busy_list
        return [s for s in all_dept_staff if s not in busy_list]
    except:
        return []

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
        "MEMBERSHIPS",
        "INVENTORY & STAFF",
        "MARKETING & PROMOS", 
        "CRM & RETENTION", 
        "NOTIFICATIONS"
    ]
elif st.session_state.user_dept == "RECEPTIONIST":
    menu = [
        "COMMAND CENTER",
        "MEMBERSHIPS",
        "LIVE U-FLOW", 
        "MY EARNINGS",
        "CRM & RETENTION",
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
# 4. COMMAND CENTER (TRANSACTION HUB) - CLEAN VERSION
# ==============================================================================
if choice == "COMMAND CENTER":
    st.header("🏁 COMMAND CENTER")
    
    # --- NEW: FAST SCAN SECTION ---
    st.subheader("💳 QUICK SCAN / CARD SEARCH")
    scan_input = st.text_input("SCAN CARD OR TYPE SERIAL", placeholder="e.g., RB-1001", key="membership_scanner").strip()
    
    # Initialize default values for auto-fill
    d_plate, d_name, d_phone = "", "", ""
    auto_payment = "Moniepoint POS" # Default

    if scan_input:
        m_data = conn.query("SELECT plate FROM memberships WHERE card_serial=:s", params={"s": scan_input}, ttl=0)
        if not m_data.empty:
            found_plate = m_data.iloc[0]['plate']
            c_data = conn.query("SELECT * FROM customers WHERE plate=:p", params={"p": found_plate}, ttl=0)
            if not c_data.empty:
                d_plate = c_data.iloc[0]['plate']
                d_name = c_data.iloc[0]['name']
                d_phone = c_data.iloc[0]['phone']
                auto_payment = "Gold Card Credit"
                st.success(f"✅ Card Linked to {d_plate} ({d_name})")
            else:
                st.error("Card found, but no customer record exists for that plate.")
        else:
            st.error("Invalid Card Serial or Unregistered Card.")

    st.markdown("---")
    mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
    st.markdown("---")
    
    cust_data = conn.query("SELECT * FROM customers", ttl=0)
    search_options = ["NEW CUSTOMER"]
    if not cust_data.empty:
        search_options += [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
    
    search_selection = st.selectbox("SEARCH EXISTING CLIENT", search_options, key="cc_search_bar_main")
    
    if search_selection != "NEW CUSTOMER":
        p_key = search_selection.split(" - ")[0]
        match = cust_data[cust_data['plate'] == p_key].iloc[0]
        d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

    col1, col2 = st.columns(2)
    with col1:
        plate = st.text_input("PLATE NUMBER", value=d_plate).upper()
        v_type = st.selectbox("VEHICLE TYPE", ["Sedan", "SUV", "Truck", "Crossover", "Bike", "Other"])
        name = st.text_input("CLIENT NAME", value=d_name)
        c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
        phone_val = d_phone[3:] if d_phone and len(d_phone) > 3 else ""
        phone_raw = st.text_input("PHONE (No leading zero)", value=phone_val)
        full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}" if not d_phone else d_phone

    with col2:
        total_price = 0.0
        item_summary = ""
        lounge_items_sold = []
        staff_assigned = "UNKNOWN"
        transaction_type = mode
        discount_amount = 0.0
        applied_code = None
        base_total = 0.0
        
        if mode == "CAR WASH":
            selected = st.multiselect("SERVICES", list(SERVICES.keys()))
            is_promo = st.checkbox("🎟️ COMPLIMENTARY (FREE WASH)")
            base_total = sum([SERVICES[s] for s in selected]) if selected else 0.0
            st.write("---")
            promo_code_input = st.text_input("ENTER PROMO CODE (Optional)").strip()
            
            if promo_code_input:
                p_query = "SELECT * FROM promotions WHERE code=:c AND status='ACTIVE'"
                p_res = conn.query(p_query, params={"c": promo_code_input}, ttl=0)
                if not p_res.empty:
                    code_plate = p_res.iloc[0]['created_for_plate']
                    disc_pc = p_res.iloc[0]['discount_pc']
                    if code_plate == plate:
                        st.success(f"✅ CODE APPLIED: {disc_pc}% OFF")
                        discount_amount = base_total * (disc_pc / 100)
                        applied_code = promo_code_input
                    else:
                        st.error(f"❌ Code belongs to vehicle {code_plate}")
                else:
                    st.error("❌ Invalid or Used Code")

            if is_promo:
                total_price = 0.0
                transaction_type = "PROMO"
            else:
                total_price = base_total - discount_amount
            item_summary = ", ".join(selected)

            bays_query = "SELECT COUNT(*) FROM live_bays WHERE status NOT IN ('WAITING')"
            res_bays = conn.query(bays_query, ttl=0)
            active_bays_count = res_bays.iloc[0].iloc[0] if not res_bays.empty else 0
            free_staff = get_free_staff_by_dept("WET BAY")
            
            if active_bays_count >= 3:
                st.warning(f"🚨 ALL 3 BAYS BUSY. Auto-adding to WAITING LIST.")
                staff_assigned = "WAITING LIST"
            elif not free_staff:
                st.warning("⚠️ NO WET BAY STAFF AVAILABLE.")
                staff_assigned = "WAITING LIST"
            else:
                staff_assigned = st.selectbox("ASSIGN WET BAY DETAILER", free_staff)
        
        else:
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
            staff_assigned = st.session_state.user_name

        if discount_amount > 0:
            st.caption(f"SUBTOTAL: ₦{base_total:,}")
            st.caption(f"DISCOUNT: -₦{discount_amount:,}")
        st.markdown(f"### TOTAL: ₦{total_price:,}")
        
        pay_options = ["Moniepoint POS", "Bank Transfer", "Cash", "Gold Card Credit"]
        default_pay_index = pay_options.index(auto_payment) if auto_payment in pay_options else 0
        pay_method = st.selectbox("PAYMENT METHOD", pay_options, index=default_pay_index)

    @st.dialog("CONFIRM TRANSACTION")
    def confirm_transaction_dialog():
        st.warning("Please verify details:")
        st.write(f"**Customer:** {name} ({plate})")
        st.write(f"**Total:** ₦{total_price:,}")
        if pay_method == "Gold Card Credit":
            m_res = conn.query("SELECT balance_washes FROM memberships WHERE plate=:p", params={"p": plate}, ttl=0)
            if not m_res.empty:
                bal = m_res.iloc[0]['balance_washes']
                if bal <= 1: st.error(f"⚠️ LOW BALANCE: {bal} remaining!")

        if st.button("CONFIRM & AUTHORIZE", type="primary", use_container_width=True):
            can_proceed = True
            low_bal = False
            final_sales_total = total_price
            transaction_type_final = transaction_type
            
            if pay_method == "Gold Card Credit":
                m_res = conn.query("SELECT balance_washes FROM memberships WHERE plate=:p", params={"p": plate}, ttl=0)
                if not m_res.empty and m_res.iloc[0]['balance_washes'] > 0:
                    new_bal = int(m_res.iloc[0]['balance_washes']) - 1
                    with conn.session as s:
                        s.execute(text("UPDATE memberships SET balance_washes=:nb WHERE plate=:p"), {"nb": new_bal, "p": plate})
                        s.commit()
                    final_sales_total = 0.0
                    transaction_type_final = "MEMBERSHIP"
                    if new_bal <= 1: low_bal = True
                else:
                    st.error("Insufficient Balance.")
                    can_proceed = False

            if can_proceed:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                initial_status = "WAITING" if staff_assigned == "WAITING LIST" else "WET BAY"
                db_staff_val = "PENDING" if staff_assigned == "WAITING LIST" else staff_assigned
                
                try:
                    with conn.session as s:
                        final_staff_for_log = staff_assigned
                        if mode == "CAR WASH":
                            hist_q = s.execute(text("SELECT staff FROM live_bays WHERE plate=:p"), {"p": plate}).fetchone()
                            prev_staff = hist_q[0] if hist_q else None
                            if prev_staff and prev_staff not in ["PENDING", staff_assigned]:
                                final_staff_for_log = f"{prev_staff} & {staff_assigned}"

                        res = s.execute(text("""
                            INSERT INTO sales (plate, services, total, method, staff, timestamp, type, status) 
                            VALUES (:p, :svc, :tot, :meth, :st, :ts, :typ, 'COMPLETED') RETURNING id
                        """), {"p": plate, "svc": item_summary, "tot": float(final_sales_total), "meth": pay_method, "st": final_staff_for_log, "ts": now, "typ": transaction_type_final})
                        new_sales_id = res.fetchone()[0]
                        
                        if applied_code: s.execute(text("UPDATE promotions SET status='USED' WHERE code=:c"), {"c": applied_code})
                        
                        s.execute(text("""
                            INSERT INTO customers (plate, name, phone, visits, last_visit) 
                            VALUES (:p, :n, :ph, 1, :lv)
                            ON CONFLICT (plate) DO UPDATE SET visits = customers.visits + 1, last_visit = :lv, name = :n, phone = :ph
                        """), {"p": plate, "n": name, "ph": full_phone, "lv": now.split()[0]})

                        if mode == "CAR WASH":
                            s.execute(text("""
                                INSERT INTO live_bays (plate, status, entry_time, staff, vehicle_type, service_detail) 
                                VALUES (:p, :stat, :t, :s, :vt, :sd)
                                ON CONFLICT (plate) DO UPDATE SET status=:stat, entry_time=:t, staff=:s, service_detail=:sd
                            """), {"p": plate, "stat": initial_status, "t": now, "s": db_staff_val, "vt": v_type, "sd": item_summary})
                        else:
                            for item, qty in lounge_items_sold:
                                s.execute(text("UPDATE inventory SET stock = stock - :q WHERE item = :i"), {"q": qty, "i": item})
                        s.commit()
                    
                    st.session_state['last_receipt'] = {"id": new_sales_id, "mode": transaction_type_final, "name": name, "plate": plate, "phone": full_phone, "items": item_summary, "total": final_sales_total, "staff": final_staff_for_log, "date": now, "low_bal": low_bal}
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    if st.button(f"AUTHORIZE {transaction_type} TRANSACTION", use_container_width=True):
        if mode == "CAR WASH" and not staff_assigned: st.error("Staff issue.")
        elif (plate or mode == "LOUNGE") and (mode == "LOUNGE" or (mode == "CAR WASH" and item_summary)):
            confirm_transaction_dialog()

    # --- RECEIPT RENDERING (Kept inside Command Center) ---
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
        </div>
        """, unsafe_allow_html=True)
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            receipt_payload = {"id": r["id"], "date": r["date"], "plate": r["plate"], "items": r["items"], "total": r["total"]}
            receipt_url = f"?print_receipt={urllib.parse.quote(json.dumps(receipt_payload))}"
            st.markdown(f'<a href="{receipt_url}" target="_blank"><button style="width:100%; height:3.5em; background:black; color:white; font-weight:bold; cursor:pointer;">🖨️ PRINT RECEIPT</button></a>', unsafe_allow_html=True)
        with c_p2:
            if st.button("CLOSE & DISMISS"):
                del st.session_state['last_receipt']
                st.rerun()

# ==============================================================================
# X. MEMBERSHIP HUB (SEPARATE SECTION)
# ==============================================================================
elif choice == "MEMBERSHIPS":
    st.header("💳 MEMBERSHIP HUB")
    mem_action = st.radio("SELECT ACTION", ["ISSUE NEW CARD", "TOP-UP EXISTING CARD"], horizontal=True)
    st.markdown("---")

    if mem_action == "ISSUE NEW CARD":
        st.caption("Link a new physical card to a vehicle")
        m_plate = st.text_input("VEHICLE PLATE").upper()
        m_serial = st.text_input("CARD SERIAL NUMBER (Scan/Type)", placeholder="e.g., RB-1001")
        tier = st.selectbox("CARD TIER", ["Silver (5 Washes)", "Gold (10 Washes)", "Platinum (25 Washes)"])
        card_sale_price = st.number_input("CARD SALE PRICE (₦)", min_value=0.0, step=500.0)
        m_pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"], key="new_mem_pay")
        qty = 5
        if "Gold" in tier: qty = 10
        elif "Platinum" in tier: qty = 25
        
        @st.dialog("CONFIRM CARD ISSUANCE")
        def confirm_issue():
            st.warning(f"Confirm receipt of ₦{card_sale_price:,} via {m_pay_method}?")
            if st.button("YES, PAYMENT RECEIVED - ACTIVATE", use_container_width=True, type="primary"):
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO memberships (plate, balance_washes, card_type, sale_price, card_serial, status) 
                        VALUES (:p, :b, :c, :s, :ser, 'ACTIVE')
                        ON CONFLICT (plate) DO UPDATE SET balance_washes=:b, card_type=:c, sale_price=:s, card_serial=:ser, status='ACTIVE'
                    """), {"p": m_plate, "b": qty, "c": tier, "s": card_sale_price, "ser": m_serial})
                    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    s.execute(text("""
                        INSERT INTO sales (plate, services, total, method, staff, timestamp, type, status) 
                        VALUES (:p, :svc, :tot, :meth, :st, :ts, :typ, 'COMPLETED')
                    """), {"p": m_plate, "svc": f"NEW CARD: {tier}", "tot": card_sale_price, "meth": m_pay_method, "st": st.session_state.user_name, "ts": now_ts, "typ": "CARDS"})
                    receptionist = st.session_state.user_name
                    res_p = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": receptionist}).fetchone()
                    if res_p and res_p[0] > 0:
                        comm_amt = card_sale_price * (res_p[0] / 100)
                        s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"), {"u": receptionist, "a": comm_amt, "r": f"NEW_CARD:{m_plate}", "t": now_ts})
                    s.commit()
                st.success(f"Linked {m_serial} to {m_plate}!")
                st.rerun()

        if st.button("ISSUE CARD", use_container_width=True):
            if m_plate and m_serial: confirm_issue()
            else: st.error("Missing fields.")

    else:
        st.caption("Add washes to an existing card")
        t_input = st.text_input("SCAN CARD OR ENTER PLATE").upper()
        t_washes = st.number_input("WASHES TO ADD", min_value=1, value=10)
        t_price = st.number_input("TOP-UP AMOUNT (₦)", min_value=0.0, step=500.0)
        t_pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"], key="topup_pay")

        @st.dialog("CONFIRM TOP-UP")
        def confirm_topup():
            st.warning(f"Confirm receipt of ₦{t_price:,} for {t_washes} washes?")
            if st.button("CONFIRM PAYMENT & ADD WASHES", use_container_width=True, type="primary"):
                try:
                    with conn.session as s:
                        result = s.execute(text("UPDATE memberships SET balance_washes = balance_washes + :qty WHERE plate = :t OR card_serial = :t"), {"qty": t_washes, "t": t_input})
                        if result.rowcount == 0:
                            st.error("Card not found.")
                            return 
                        receptionist = st.session_state.user_name
                        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                        s.execute(text("""
                            INSERT INTO sales (plate, services, total, method, staff, timestamp, type, status) 
                            VALUES (:p, :svc, :tot, :meth, :st, :ts, :typ, 'COMPLETED')
                        """), {"p": t_input, "svc": f"TOP-UP: {t_washes} Washes", "tot": t_price, "meth": t_pay_method, "st": receptionist, "ts": now_ts, "typ": "CARDS"})
                        res_p = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": receptionist}).fetchone()
                        if res_p and res_p[0] > 0:
                            comm_amt = t_price * (res_p[0] / 100)
                            s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"), {"u": receptionist, "a": comm_amt, "r": f"TOPUP:{t_input}", "t": now_ts})
                        s.commit()
                    st.success("Top-up Complete!")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

        if st.button("AUTHORIZE TOP-UP", use_container_width=True):
            if t_input: confirm_topup()
            else: st.error("Scan card first.")


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
                .status-waiting {{ color: #FF3B30 !important; }}
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
                status_class = "status-waiting" if row['status'] == "WAITING" else ""
                monitor_html += f"""
                <div class="monitor-row">
                    <div class="monitor-plate">{row['plate']}<br><span style="font-size:18px; color:#555;">{row['vehicle_type']}</span></div>
                    <div style="flex:1; padding-left:40px;"><div class="monitor-svc">SERVICE: {row['service_detail']}</div></div>
                    <div class="monitor-meta">
                        <div class="monitor-status {status_class}">{row['status']}</div>
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
            
        # Count active bays for limit logic
        active_wet = len(live_cars[live_cars['status'] == 'WET BAY'])
        active_dry = len(live_cars[live_cars['status'] == 'DRY BAY'])
            
        for idx, row in live_cars.iterrows():
            # Calculate time spent
            try:
                entry_dt = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M")
                time_spent = (datetime.now() - entry_dt).seconds // 60
            except:
                time_spent = 0
            
            # Border color: Waiting (Grey), Normal (Blue), Overdue (Red)
            if row['status'] == "WAITING":
                border_color = "#555555"
            else:
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
                # --- WAITING LIST TO WET BAY LOGIC ---
                if row['status'] == "WAITING":
                    if active_wet < 3:
                        with st.popover("ASSIGN TO WET BAY"):
                            wet_staff = get_free_staff_by_dept("WET BAY")
                            new_wet_detailer = st.selectbox("Assign Detailer", wet_staff if wet_staff else ["NO FREE STAFF"], key=f"wait_wet_{idx}")
                            if st.button("Move to Wet Bay", key=f"move_wet_{idx}"):
                                if new_wet_detailer != "NO FREE STAFF":
                                    with conn.session as s:
                                        s.execute(text("UPDATE live_bays SET status='WET BAY', staff=:s WHERE plate=:p"), {"s": new_wet_detailer, "p": row['plate']})
                                        s.commit()
                                    st.rerun()
                    else:
                        st.caption("🚨 WET BAYS FULL (3/3)")

                # --- WET TO DRY LOGIC ---
                if row['status'] == "WET BAY":
                    if active_dry < 3:
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
                    else:
                        if st.button("PARK (DRY FULL)", key=f"park_{idx}"):
                             with conn.session as s:
                                s.execute(text("UPDATE live_bays SET status='WAITING', staff='PENDING', wet_staff_history=:ws WHERE plate=:p"), {"ws": row['staff'], "p": row['plate']})
                                s.commit()
                             st.rerun()

                # --- RELEASE LOGIC (DRY BAY ONLY) ---
                if row['status'] == "DRY BAY":
                    if st.button(f"RELEASE {row['plate']}", key=f"rel_{idx}"):
                        # 1. Fetch the sale details
                        sale_data = conn.query("SELECT total, services, type FROM sales WHERE plate=:p ORDER BY id DESC LIMIT 1", params={"p": row['plate']}, ttl=0)
                        
                        if not sale_data.empty:
                            sale_total = float(sale_data.iloc[0]['total'])
                            sale_type = sale_data.iloc[0]['type']
                            services_run = sale_data.iloc[0]['services'].split(", ")
                            
                            if sale_total == 0 and sale_type != "PROMO":
                                commissionable_value = sum([SERVICES.get(s, 0) for s in services_run])
                            else:
                                commissionable_value = sale_total

                            current_staff = row['staff']
                            prev_staff = row['wet_staff_history']
                            staff_to_pay = [s for s in [current_staff, prev_staff] if s and str(s).lower() != 'none' and str(s).strip() != '']
                            
                            # Create label for the financial record
                            report_names = f"{prev_staff} & {current_staff}" if prev_staff and prev_staff != current_staff else current_staff

                            with conn.session as s:
                                # Update the sales table to replace WAITING LIST with actual staff names
                                s.execute(text("""
                                    UPDATE sales 
                                    SET staff = :actual 
                                    WHERE plate = :p AND (staff = 'WAITING LIST' OR staff = 'PENDING')
                                """), {"actual": report_names, "p": row['plate']})

                                for s_member in staff_to_pay:
                                    p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": s_member}).fetchone()
                                    if p_res and p_res[0] > 0 and commissionable_value > 0:
                                        comm_amt = commissionable_value * (float(p_res[0]) / 100)
                                        s.execute(text("""
                                            INSERT INTO earnings_log (username, amount, ref_plate, timestamp) 
                                            VALUES (:u, :a, :r, :t)
                                        """), {"u": s_member, "a": comm_amt, "r": str(row['plate']), "t": datetime.now()})
                                s.commit()

                        # 2. Capture WhatsApp Info
                        cust_info = conn.query("SELECT name, phone FROM customers WHERE plate=:p", params={"p": row['plate']}, ttl=0)
                        if not cust_info.empty:
                            c_name = cust_info.iloc[0]['name']
                            c_phone = cust_info.iloc[0]['phone']
                            wa_msg = f"Hi {c_name}, your vehicle ({row['plate']}) is ready for pickup! Thank you for choosing RideBoss Autos."
                            st.session_state.wa_pending = {"url": format_whatsapp(c_phone, wa_msg), "plate": row['plate']}

                        # 3. Complete Release
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
        # REWRITTEN QUERY: Uses permanent records only
        perf_query = """
            SELECT staff_member, COUNT(*) as tasks, SUM(revenue_impact) as revenue_impact
            FROM (
                SELECT staff AS staff_member, total AS revenue_impact 
                FROM sales 
                WHERE staff IS NOT NULL AND staff != ''
                
                UNION ALL
                
                SELECT username AS staff_member, 0 AS revenue_impact 
                FROM earnings_log 
                WHERE username IS NOT NULL AND username != ''
            ) AS combined_data
            GROUP BY staff_member
            ORDER BY tasks DESC
        """
        try:
            perf_df = conn.query(perf_query, ttl=0)
            
            # Check if we actually have rows with tasks > 0
            if not perf_df.empty and perf_df['tasks'].sum() > 0:
                st.bar_chart(perf_df.set_index('staff_member')['tasks'])
                st.dataframe(
                    perf_df, 
                    use_container_width=True,
                    column_config={
                        "staff_member": "Staff Name",
                        "tasks": "Total Activities",
                        "revenue_impact": st.column_config.NumberColumn("Direct Sales (₦)", format="₦%.2f")
                    }
                )
            else:
                st.warning("📊 No activity recorded yet. Ensure staff are assigned during checkout and 'Released' in the U-Flow.")
        except Exception as e:
            # This will now show the actual error if it fails again
            st.error(f"Performance Query Error: {e}")



# ==============================================================================
# 6. FINANCIALS (INTELLIGENCE CENTER) - FIXED & ACCURATE
# ==============================================================================
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    st.title("📊 FINANCIAL INTELLIGENCE CENTER")
    st.markdown("---")
    
    tab_fin, tab_cards_hub = st.tabs(["📈 REVENUE ANALYTICS", "💳 MEMBERSHIP REGISTRY"])
    
    with tab_fin:
        # --- Analytics Control Panel ---
        with st.container():
            col_f1, col_f2 = st.columns([1, 2])
            view_scope = col_f1.radio("**REPORTING SCOPE**", ["DAILY", "MONTHLY", "YEARLY"], horizontal=True)
            
            # Data Loading
            # We ONLY pull revenue from 'sales' to avoid double counting. 
            # The 'memberships' table is now only for managing access, not counting money.
            sales_raw = conn.query("SELECT * FROM sales", ttl=0)
            exp_raw = conn.query("SELECT * FROM expenses", ttl=0)
            
            # Convert timestamps
            sales_raw['timestamp'] = pd.to_datetime(sales_raw['timestamp'])
            exp_raw['timestamp'] = pd.to_datetime(exp_raw['timestamp'])
            
            now = datetime.now()
            label = ""
            
            # Filtering Logic
            if view_scope == "DAILY":
                selected_date = col_f2.date_input("📅 SELECT DAY", now.date())
                f_sales = sales_raw[sales_raw['timestamp'].dt.date == selected_date]
                f_exps = exp_raw[exp_raw['timestamp'].dt.date == selected_date]
                label = f"DAILY PERFORMANCE: {selected_date}"
                
            elif view_scope == "MONTHLY":
                months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                selected_month_name = col_f2.selectbox("🗓️ SELECT MONTH", months, index=now.month-1)
                selected_month = months.index(selected_month_name) + 1
                
                f_sales = sales_raw[(sales_raw['timestamp'].dt.month == selected_month) & (sales_raw['timestamp'].dt.year == now.year)]
                f_exps = exp_raw[(exp_raw['timestamp'].dt.month == selected_month) & (exp_raw['timestamp'].dt.year == now.year)]
                label = f"MONTHLY PERFORMANCE: {selected_month_name} {now.year}"
                
            else:
                current_year = now.year
                year_options = list(range(2024, current_year + 1))
                selected_year = col_f2.selectbox("📂 SELECT YEAR", year_options, index=len(year_options)-1)
                
                f_sales = sales_raw[sales_raw['timestamp'].dt.year == selected_year]
                f_exps = exp_raw[exp_raw['timestamp'].dt.year == selected_year]
                label = f"ANNUAL PERFORMANCE: {selected_year}"

        # --- Financial Summary Board ---
        # BREAKDOWN BY TYPE (Accurate Single Source)
        # We look for specific strings in the 'type' or 'services' column
        rev_wash = f_sales[f_sales['type'] == 'CAR WASH']['total'].sum()
        rev_lounge = f_sales[f_sales['type'] == 'LOUNGE']['total'].sum()
        
        # New: Calculate Card Revenue from Sales Table (looks for type='CARDS')
        rev_cards = f_sales[f_sales['type'] == 'CARDS']['total'].sum()
        
        total_revenue = f_sales['total'].sum() # Should match sum of above
        total_exp = f_exps['amount'].sum()
        net_profit = total_revenue - total_exp

        st.info(f"#### {label}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("WASH", f"₦{rev_wash:,}")
        m2.metric("LOUNGE", f"₦{rev_lounge:,}")
        m3.metric("CARDS", f"₦{rev_cards:,}") # Now accurate
        m4.metric("EXPENSES", f"₦{total_exp:,}")
        m5.metric("NET PROFIT", f"₦{net_profit:,}", delta=float(net_profit))
        
        # --- Visualization ---
        st.markdown("### 📊 Revenue Breakdown")
        chart_data = pd.DataFrame({
            'Category': ['Wash', 'Lounge', 'Cards', 'Expenses'], 
            'Amount': [rev_wash, rev_lounge, rev_cards, total_exp]
        })
        st.bar_chart(chart_data.set_index('Category'))
        
        # --- Detail Tabs ---
        det_tab1, det_tab2 = st.tabs(["🧾 Transaction Log", "💸 Expense Management"])
        with det_tab1:
            st.dataframe(f_sales, use_container_width=True)
            csv = f_sales.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DOWNLOAD REPORT", csv, f"RideBoss_{label}.csv", "text/csv")
            
        with det_tab2:
            with st.form("expense_form"):
                e_desc = st.text_input("Expense Description")
                e_amt = st.number_input("Amount (₦)", min_value=0.0)
                if st.form_submit_button("LOG EXPENSE"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO expenses (description, amount, timestamp) VALUES (:d, :a, :t)"), 
                                  {"d": e_desc, "a": e_amt, "t": datetime.now().strftime("%Y-%m-%d")})
                        s.commit()
                    st.success("Expense Recorded Successfully!")
                    st.rerun()

    with tab_cards_hub:
        # --- Header & Search ---
        head_col, search_col = st.columns([1, 1])
        with head_col:
            st.subheader("📋 MEMBERSHIP REGISTRY")
        with search_col:
            search_query = st.text_input("🔍 Search Registry", placeholder="Enter Plate or Serial...", key="search_cards_hub")
        
        # We load memberships here strictly for management, NOT for financial totals
        m_df = conn.query("SELECT * FROM memberships", ttl=0)
        
        if m_df.empty:
            st.warning("No Active Memberships found.")
        else:
            if search_query:
                m_df = m_df[
                    m_df['plate'].str.contains(search_query, case=False, na=False) | 
                    m_df['card_serial'].astype(str).str.contains(search_query, case=False, na=False)
                ]

            # Summary Bar
            total_cards = len(m_df)
            total_washes = m_df['balance_washes'].sum()
            stat1, stat2, stat3 = st.columns([1,1,2])
            stat1.metric("Total Members", total_cards)
            stat2.metric("Owed Washes", f"{int(total_washes)}")
            st.markdown("---")

            # --- Styled List Header ---
            h1, h2, h3, h4 = st.columns([2, 1.5, 1, 1])
            h1.markdown("**MEMBER / IDENTITY**")
            h2.markdown("**STATUS & BALANCE**")
            h3.markdown("**REFILL**")
            h4.markdown("**MANAGE**")
            st.markdown('<div style="margin-top: -10px;"><hr></div>', unsafe_allow_html=True)

            # --- Membership Row Display ---
            for idx, row in m_df.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
                    
                    # Column 1: Identity
                    serial_disp = row.get('card_serial', 'N/A')
                    c1.markdown(f"🚗 **{row['plate']}**")
                    c1.caption(f"SERIAL: {serial_disp}")
                    
                    # Column 2: Status & Balance
                    bal = row['balance_washes']
                    status_color = "green" if bal > 2 else "orange" if bal > 0 else "red"
                    c2.markdown(f":{status_color}[**{bal} Washes**]")
                    c2.caption(f"Tier: {row['card_type']}")
                    
                    # Column 3: Quick Refill
                    if c3.button(f"➕ REFILL", key=f"up_{idx}", use_container_width=True):
                        top_up_qty = 5
                        if "Gold" in row['card_type']: top_up_qty = 10
                        elif "Platinum" in row['card_type']: top_up_qty = 25
                        
                        with conn.session as s:
                            # 1. Update Balance
                            s.execute(text("UPDATE memberships SET balance_washes = balance_washes + :q WHERE plate=:p"), 
                                      {"q": top_up_qty, "p": row['plate']})
                            
                            # 2. Log Sale (CRITICAL FOR FINANCIALS)
                            receptionist = st.session_state.user_name
                            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                            # We must insert into sales so it shows in the chart above
                            # (Note: In your 'Membership' tab you handle the payment logic, 
                            # this 'Refill' button is a quick-action shortcut. 
                            # Ideally, payment should be verified, but we log 0 or the tier price here?)
                            
                            # Assuming this button implies a paid refill:
                            # Retrieve price based on tier (approx logic)
                            # Ideally, you should fetch the price, but we will use the stored sale_price
                            refill_price = row['sale_price'] 
                            
                            s.execute(text("""
                                INSERT INTO sales (plate, services, total, method, staff, timestamp, type, status) 
                                VALUES (:p, :svc, :tot, :meth, :st, :ts, :typ, 'COMPLETED')
                            """), {
                                "p": row['plate'], "svc": f"QUICK REFILL: {top_up_qty}", "tot": refill_price,
                                "meth": "CASH", "st": receptionist, "ts": now_ts, "typ": "CARDS"
                            })

                            # 3. Staff Commission
                            p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), 
                                              {"u": receptionist}).fetchone()
                            
                            if p_res and p_res[0] > 0:
                                comm_amt = refill_price * (p_res[0] / 100)
                                s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"), 
                                          {"u": receptionist, "a": comm_amt, "r": f"TOPUP:{row['plate']}", "t": now_ts})
                            s.commit()
                        st.success(f"Added {top_up_qty} washes!")
                        st.rerun()

                    # Column 4: Delete
                    if c4.button(f"🗑️", key=f"del_{idx}", use_container_width=True):
                        with conn.session as s:
                            s.execute(text("DELETE FROM memberships WHERE plate=:p"), {"p": row['plate']})
                            s.commit()
                        st.rerun()
                    
                    st.markdown('<hr style="margin: 0px;">', unsafe_allow_html=True)

# ==============================================================================
# 7. CRM & RETENTION
# ==============================================================================
elif choice == "CRM & RETENTION":
    st.subheader("CUSTOMER RETENTION PANEL")
    
    # Ensure necessary libraries are available for code generation
    import random
    import string

    # 1. Get System Rules (For VIP Logic)
    sett_df = conn.query("SELECT * FROM system_settings", ttl=0)
    try:
        vip_milestone = int(sett_df[sett_df['setting_key'] == 'vip_milestone'].iloc[0]['setting_value'])
        vip_discount = float(sett_df[sett_df['setting_key'] == 'vip_discount'].iloc[0]['setting_value'])
    except:
        vip_milestone = 10
        vip_discount = 20.0 # Default fallback

    # 2. Get customer data
    cust_df = conn.query("SELECT * FROM customers", ttl=0)
    
    if cust_df is None or cust_df.empty:
        st.info("No customer records found yet.")
    else:
        # --- NEW SEARCH BAR ---
        search_term = st.text_input("🔍 SEARCH CUSTOMER (PLATE OR NAME)", "").upper()
        
        # Apply filter if search term is provided
        if search_term:
            display_df = cust_df[
                (cust_df['plate'].str.contains(search_term, na=False)) | 
                (cust_df['name'].str.upper().str.contains(search_term, na=False))
            ]
        else:
            display_df = cust_df

        for idx, row in display_df.iterrows():
            try:
                # Calculate days since last visit
                if not row['last_visit']:
                    continue
                    
                last_v = datetime.strptime(str(row['last_visit']), "%Y-%m-%d")
                days_since = (datetime.now() - last_v).days
                visit_count = row['visits']

                # --- INTELLIGENCE LOGIC ---
                is_vip_milestone = (visit_count > 0) and (visit_count % vip_milestone == 0)
                
                # Logic-based coloring
                if is_vip_milestone:
                    color, status_text = "#E0AA3E", "👑 VIP MILESTONE REACHED"
                elif days_since < 7:
                    color, status_text = "#00d4ff", "Active"
                elif days_since < 14:
                    color, status_text = "#FFD700", "Needs Follow-up"
                else:
                    color, status_text = "#FF3B30", "At Risk"

                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # SMART FEATURE: Click the name popover to see full history
                    with st.popover(f"🔍 {row['name']} | {row['plate']}", use_container_width=True):
                        st.markdown(f"### Customer Details")
                        st.write(f"**Phone:** {row['phone']}")
                        st.write(f"**Total Visits:** {visit_count}")
                        st.write(f"**Last Visit:** {row['last_visit']}")
                        st.divider()
                        st.write("**Service History & Records**")
                        
                        # Fetch all past sales for this specific plate
                        history = conn.query("SELECT id, timestamp, services, total FROM sales WHERE plate = :p ORDER BY id DESC", params={"p": row['plate']}, ttl=0)
                        
                        if not history.empty:
                            for h_idx, h_row in history.iterrows():
                                h_col1, h_col2 = st.columns([3, 1])
                                h_col1.write(f"📅 {h_row['timestamp']} | ₦{h_row['total']:,}")
                                h_col1.caption(f"Services: {h_row['services']}")
                                
                                # Print Receipt for this specific historical visit
                                if h_col2.button("PRINT 🖨️", key=f"prnt_{row['plate']}_{h_row['id']}"):
                                    receipt_json = json.dumps({
                                        "id": h_row['id'],
                                        "date": h_row['timestamp'],
                                        "plate": row['plate'],
                                        "items": h_row['services'],
                                        "total": h_row['total']
                                    })
                                    st.query_params["print_receipt"] = receipt_json
                                    st.rerun()
                                st.divider()
                        else:
                            st.info("No detailed history found for this plate.")

                    st.markdown(f"""
                        <div style='padding:12px; border-radius:5px; border-left: 5px solid {color}; background:#1e1e1e; margin-bottom:8px; margin-top:-10px;'>
                            <small style='color:{color}; font-weight:bold;'>{days_since} days since last visit ({status_text})</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # --- DYNAMIC ACTION BUTTON ---
                    if is_vip_milestone:
                        # CHECK: Has a reward already been sent and is still active?
                        # This prevents the button from showing if they already have a code for this milestone.
                        existing_promo = conn.query(
                            "SELECT code FROM promotions WHERE created_for_plate=:p AND status='ACTIVE'", 
                            params={"p": row['plate']}
                        )
                        
                        if not existing_promo.empty:
                            # If they have an active code, show that instead of the button 
                            active_code = existing_promo.iloc[0]['code']
                            st.markdown(f"""
                                <div style="background-color:#1e1e1e; border:1px solid #E0AA3E; color:#E0AA3E; padding:10px; 
                                     text-align:center; border-radius:5px; font-size:12px;">
                                    <strong>REWARD ACTIVE</strong><br>{active_code}
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            # 👑 VIP BUTTON LOGIC: Generate code and send reward
                            if st.button("🎁 SEND REWARD", key=f"vip_{row['plate']}"):
                                # 1. Generate Unique Code
                                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                                new_code = f"RBA-VIP-{suffix}"
                                
                                # 2. Save to DB
                                with conn.session as s:
                                    s.execute(text("""
                                        INSERT INTO promotions (code, discount_pc, created_for_plate, created_at, status)
                                        VALUES (:c, :d, :p, :t, 'ACTIVE')
                                    """), {
                                        "c": new_code, "d": vip_discount, 
                                        "p": row['plate'], "t": datetime.now().strftime("%Y-%m-%d")
                                    })
                                    s.commit()
                                
                                # 3. Generate WhatsApp Link
                                msg = f"Congrats {row['name']}! You've hit {visit_count} visits at RideBoss! To celebrate, here is a {vip_discount}% OFF code for your next wash: *{new_code}*. See you soon!"
                                url = format_whatsapp(row['phone'], msg)
                                
                                # FIX: Use a visible button instead of blocked JavaScript
                                st.success(f"Generated: {new_code}")
                                st.markdown(f"""
                                    <a href="{url}" target="_blank" style="text-decoration:none;">
                                        <div style="background-color:#E0AA3E; color:black; padding:12px; text-align:center; 
                                             border-radius:5px; font-weight:bold; margin-top:5px; font-size:13px; box-shadow: 0px 0px 10px #E0AA3E;">
                                            👉 CLICK TO SEND CODE
                                        </div>
                                    </a>
                                """, unsafe_allow_html=True)
                                # Force rerun to hide the button immediately
                                st.rerun()

                    elif days_since >= 7:
                        # STANDARD RETENTION LOGIC
                        message = f"Hello {row['name']}! This is RideBoss. We noticed your car ({row['plate']}) hasn't been in for a wash in {days_since} days. We'd love to see you today!"
                        wa_url = format_whatsapp(row['phone'], message)
                        
                        st.markdown(f"""
                            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366; color:white; padding:12px; text-align:center; 
                                     border-radius:5px; font-weight:bold; margin-top:5px; font-size:13px;">
                                    WHATSAPP 📲
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
            except Exception as e:
                # Optional: print(e) for debugging if needed, otherwise continue
                continue

elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM HISTORY")
    notes = conn.query('SELECT timestamp as "TIME", message as "EVENT" FROM notifications ORDER BY id DESC LIMIT 50', ttl=0)
    st.table(notes)


# ==============================================================================
# NEW SECTION: MARKETING & PROMOS (MANAGER ONLY)
# ==============================================================================
elif choice == "MARKETING & PROMOS" and st.session_state.user_role == "MANAGER":
    st.subheader("📢 MARKETING ENGINE & VIP CONFIG")
    
    m_tab1, m_tab2 = st.tabs(["VIP RULES CONFIG", "ACTIVE PROMO CODES"])
    
    with m_tab1:
        st.markdown("""
            <div style="background:#111; padding:20px; border-left:4px solid #00d4ff;">
                <strong>HOW IT WORKS:</strong><br>
                The system automatically detects when a customer hits a "Milestone Visit" (e.g., 10th, 20th).
                It generates a unique code for that specific customer via WhatsApp.
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        # Fetch Current Settings
        sett_df = conn.query("SELECT * FROM system_settings", ttl=0)
        curr_milestone = "10"
        curr_disc = "20"
        
        if not sett_df.empty:
            # Safe parsing
            m_row = sett_df[sett_df['setting_key'] == 'vip_milestone']
            d_row = sett_df[sett_df['setting_key'] == 'vip_discount']
            if not m_row.empty: curr_milestone = m_row.iloc[0]['setting_value']
            if not d_row.empty: curr_disc = d_row.iloc[0]['setting_value']

        with st.form("vip_config_form"):
            new_milestone = st.number_input("Trigger Reward Every X Visits", value=int(curr_milestone))
            new_disc = st.number_input("Discount Percentage (%)", value=float(curr_disc))
            
            if st.form_submit_button("UPDATE MARKETING RULES"):
                with conn.session as s:
                    s.execute(text("UPDATE system_settings SET setting_value=:v WHERE setting_key='vip_milestone'"), {"v": str(new_milestone)})
                    s.execute(text("UPDATE system_settings SET setting_value=:v WHERE setting_key='vip_discount'"), {"v": str(new_disc)})
                    s.commit()
                st.success("Rules Updated! The CRM will now use these settings.")
                st.rerun()

    with m_tab2:
        st.write("### 🎫 GENERATED CODES TRACKER")
        codes_df = conn.query("SELECT * FROM promotions ORDER BY created_at DESC", ttl=0)
        
        if codes_df.empty:
            st.info("No promo codes generated yet.")
        else:
            st.dataframe(codes_df, use_container_width=True)

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
