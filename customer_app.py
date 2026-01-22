import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
import time

# ==============================================================================
# 1. APP CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="RideBoss Concierge",
    page_icon="🏎️",
    layout="centered", # vital for mobile feel
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION ---
# Uses the same connection string as your backend
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("System Offline. Please try again later.")
    st.stop()

# --- CSS: THE PREMIUM MOBILE THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    /* GLOBAL */
    .stApp {
        background-color: #05070a;
        font-family: 'Outfit', sans-serif;
        color: #e2e8f0;
    }
    
    /* HIDE STREAMLIT CHROME */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* STATUS TRACKER CARD */
    .tracker-container {
        background: linear-gradient(145deg, #0f1219, #05070a);
        border: 1px solid #1f2937;
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.1);
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    
    .tracker-pulse {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 5px;
        background: linear-gradient(90deg, #05070a, #00d4ff, #05070a);
        animation: loading 2s infinite;
    }
    
    @keyframes loading {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

    .status-big {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -1px;
        margin: 10px 0;
    }
    
    .plate-badge {
        background: #1e293b;
        color: #94a3b8;
        padding: 5px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 1px;
    }

    /* UPSELL CARDS */
    .upsell-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: transform 0.2s;
    }
    .upsell-card:active {
        transform: scale(0.98);
        background: rgba(0, 212, 255, 0.05);
    }
    
    /* INPUT FIELDS */
    .stTextInput input {
        background-color: #0f1219 !important;
        border: 1px solid #334155 !important;
        color: white !important;
        border-radius: 12px !important;
        height: 50px;
        font-size: 1.2rem;
        text-align: center;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    /* BUTTONS */
    div.stButton > button {
        background: #00d4ff;
        color: #000;
        font-weight: 800;
        border: none;
        border-radius: 12px;
        height: 50px;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
    }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #0f1219;
        border-radius: 10px;
        color: #fff;
        flex: 1; /* Equal width tabs */
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b;
        border: 1px solid #00d4ff;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SESSION & LOGIC HELPERS
# ==============================================================================

if 'user_plate' not in st.session_state:
    st.session_state.user_plate = None

def login_user(plate):
    """
    Validates plate against the Customers table.
    """
    clean_plate = plate.upper().strip()
    # Check if plate exists in customer history OR is currently in the bay
    # We check 'live_bays' first as they might be a new walk-in not yet in 'customers'
    # but usually your backend adds them to customers on entry.
    
    query = "SELECT * FROM customers WHERE plate = :p"
    df = conn.query(query, params={"p": clean_plate}, ttl=0)
    
    if not df.empty:
        st.session_state.user_plate = clean_plate
        st.rerun()
    else:
        # Check if they are in live bay (new customer case)
        live_df = conn.query("SELECT * FROM live_bays WHERE plate = :p", params={"p": clean_plate}, ttl=0)
        if not live_df.empty:
            st.session_state.user_plate = clean_plate
            st.rerun()
        else:
            st.toast("🚫 Plate not found. Please check in at reception first.", icon="🚫")

def logout():
    st.session_state.user_plate = None
    st.rerun()

# ==============================================================================
# 3. SCREEN 1: SMART LOGIN
# ==============================================================================

if not st.session_state.user_plate:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True) # Ensure this file exists
        except:
            st.markdown("<h1 style='text-align:center; color:#00d4ff;'>RIDEBOSS</h1>", unsafe_allow_html=True)

    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-weight:300;'>TRACK YOUR SERVICE</h3>", unsafe_allow_html=True)
    
    plate_input = st.text_input("Enter Plate Number", placeholder="ABC-123", label_visibility="collapsed")
    
    if st.button("ACCESS MY VEHICLE"):
        if len(plate_input) > 2:
            login_user(plate_input)
        else:
            st.warning("Please enter a valid plate number.")
    
    st.markdown("""
        <div style='text-align:center; margin-top:50px; color:#475569; font-size:0.8rem;'>
            SECURE CLIENT PORTAL<br>Victoria Island, Lagos
        </div>
    """, unsafe_allow_html=True)
    st.stop()


# ==============================================================================
# 4. SCREEN 2: THE DASHBOARD
# ==============================================================================

# --- HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f"<h2 style='margin:0;'>Hi, Client</h2>", unsafe_allow_html=True)
    st.caption(f"Vehicle: {st.session_state.user_plate}")
with c2:
    if st.button("EXIT", key="logout_btn"):
        logout()

st.markdown("---")

# --- MAIN TABS ---
tab_live, tab_history, tab_rewards = st.tabs(["⚡ LIVE STATUS", "📜 HISTORY", "💎 VIP CLUB"])

# --- TAB 1: LIVE TRACKER (THE CORE FEATURE) ---
with tab_live:
    # Query Live Status
    live_data = conn.query("SELECT * FROM live_bays WHERE plate = :p", params={"p": st.session_state.user_plate}, ttl=0)
    
    if not live_data.empty:
        row = live_data.iloc[0]
        status = row['status'] # WAITING, WET BAY, DRY BAY, READY
        staff = row['staff']
        service = row['service_detail']
        
        # MAPPING STATUS TO VISUALS
        progress = 0
        status_msg = "Checking In..."
        pulse_class = ""
        
        if status == "WAITING":
            progress = 10
            status_msg = "IN QUEUE"
            color_code = "#f59e0b" # Orange
        elif status == "WET BAY":
            progress = 40
            status_msg = "WASHING"
            color_code = "#3b82f6" # Blue
            pulse_class = "tracker-pulse"
        elif "DRY" in status: # DRY BAY or DRY_WAITING
            progress = 75
            status_msg = "DETAILING"
            color_code = "#a855f7" # Purple
            pulse_class = "tracker-pulse"
        elif status == "READY":
            progress = 100
            status_msg = "READY TO GO"
            color_code = "#22c55e" # Green
            
        # 1. THE PIZZA TRACKER CARD
        st.markdown(f"""
            <div class="tracker-container">
                <div class="{pulse_class}"></div>
                <span class="plate-badge">{st.session_state.user_plate}</span>
                <div class="status-big" style="color: {color_code}">{status_msg}</div>
                <div style="color: #94a3b8; font-size: 0.9rem;">Current Stage: {status}</div>
                <div style="margin-top: 15px; font-size: 0.8rem; color: #64748b;">
                    Handling your vehicle: <strong style="color:white">{staff}</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.progress(progress / 100)
        
        # 2. UPSELL / MODIFICATION ENGINE
        if status != "READY":
            st.markdown("### 🛠️ While you wait...")
            st.caption("Request add-ons directly to the bay.")
            
            # Upsell Options
            upsells = [
                {"name": "Spray Wax Polish", "price": 3000, "icon": "✨"},
                {"name": "Engine Steam Clean", "price": 5000, "icon": "💨"},
                {"name": "Interior Fragrance", "price": 1000, "icon": "🌸"}
            ]
            
            for item in upsells:
                uc1, uc2 = st.columns([3, 1])
                with uc1:
                    st.markdown(f"**{item['icon']} {item['name']}**")
                    st.caption(f"Add for ₦{item['price']:,}")
                with uc2:
                    # Unique key needed for buttons inside loop
                    if st.button("ADD", key=f"add_{item['name']}"):
                        with conn.session as s:
                            s.execute(text("""
                                INSERT INTO service_requests (plate, request_item, status) 
                                VALUES (:p, :i, 'PENDING')
                            """), {"p": st.session_state.user_plate, "i": item['name']})
                            s.commit()
                        st.toast(f"Request sent for {item['name']}!", icon="✅")
        
        # 3. FEEDBACK LOOP (Only if READY)
        else:
            st.success("Your vehicle is ready for pickup!")
            st.markdown("### ⭐ Rate this Wash")
            
            with st.form("rating_form"):
                stars = st.slider("Rating", 1, 5, 5)
                comment = st.text_area("Any comments?", placeholder="Great shine!")
                
                if st.form_submit_button("SUBMIT REVIEW"):
                    with conn.session as s:
                        s.execute(text("""
                            INSERT INTO reviews (plate, rating, comment) 
                            VALUES (:p, :r, :c)
                        """), {"p": st.session_state.user_plate, "r": stars, "c": comment})
                        s.commit()
                    st.toast("Thank you for your feedback!", icon="❤️")

    else:
        st.info("No active service session found.")
        st.markdown("""
            <div style="text-align:center; padding: 40px; color: #64748b;">
                <h1>💤</h1>
                <p>Your vehicle is not currently in the shop.</p>
            </div>
        """, unsafe_allow_html=True)

# --- TAB 2: DIGITAL HISTORY ---
with tab_history:
    st.markdown("### 🗓️ Service Log")
    
    # Query History
    hist_query = """
    SELECT timestamp, services, total, staff 
    FROM sales 
    WHERE plate = :p 
    ORDER BY id DESC
    """
    history_df = conn.query(hist_query, params={"p": st.session_state.user_plate}, ttl=0)
    
    if not history_df.empty:
        total_spend = history_df['total'].sum()
        st.metric("Total Lifetime Spend", f"₦{total_spend:,.0f}")
        
        for idx, row in history_df.iterrows():
            with st.expander(f"{row['timestamp']} - ₦{row['total']:,}"):
                st.write(f"**Services:** {row['services']}")
                st.write(f"**Detailer:** {row['staff']}")
                st.caption("Receipt ID: Verified")
    else:
        st.write("No history found.")

# --- TAB 3: LOYALTY & VIP ---
with tab_rewards:
    st.markdown("### 💎 Loyalty Status")
    
    # Check Visits or Membership
    mem_df = conn.query("SELECT * FROM memberships WHERE plate = :p", params={"p": st.session_state.user_plate}, ttl=0)
    cust_df = conn.query("SELECT visits FROM customers WHERE plate = :p", params={"p": st.session_state.user_plate}, ttl=0)
    
    # 1. Gold Card Balance
    if not mem_df.empty:
        m_row = mem_df.iloc[0]
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #FFD700 0%, #B8860B 100%); 
                        color: black; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
                <h3 style="margin:0;">{m_row['card_type']} MEMBER</h3>
                <h1 style="font-size: 3.5rem; margin: 0; font-weight: 900;">{m_row['balance_washes']}</h1>
                <p>WASHES REMAINING</p>
                <small>{m_row['plate']}</small>
            </div>
        """, unsafe_allow_html=True)
    
    # 2. Visit Counter
    visits = cust_df.iloc[0]['visits'] if not cust_df.empty else 0
    next_milestone = ((visits // 10) + 1) * 10
    washes_left = next_milestone - visits
    
    st.write(f"**Visit Count:** {visits}")
    st.progress(visits % 10 / 10)
    st.caption(f"{washes_left} more visits until your next VIP Reward!")

    # 3. Active Promo Codes
    promos = conn.query("SELECT code, discount_pc FROM promotions WHERE created_for_plate=:p AND status='ACTIVE'", 
                       params={"p": st.session_state.user_plate}, ttl=0)
    
    if not promos.empty:
        st.markdown("### 🎁 Active Rewards")
        for _, p_row in promos.iterrows():
            st.markdown(f"""
                <div style="border: 1px dashed #00d4ff; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px;">
                    <div style="color: #00d4ff; font-weight: bold; font-size: 1.2rem;">{p_row['discount_pc']}% OFF</div>
                    <div style="font-family: monospace; font-size: 1.5rem; background: #1e293b; display: inline-block; padding: 5px 15px; border-radius: 5px; margin-top: 5px;">
                        {p_row['code']}
                    </div>
                    <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #64748b;">Show this to cashier</p>
                </div>
            """, unsafe_allow_html=True)
