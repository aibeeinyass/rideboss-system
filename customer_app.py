import streamlit as st
import pandas as pd
from datetime import datetime
import time
from sqlalchemy import text

# ==============================================================================
# RIDEBOSS CLIENT - CUSTOMER PORTAL
# Connects to the same PostgreSQL Backend as the Admin App
# ==============================================================================

st.set_page_config(
    page_title="My RideBoss", 
    page_icon="🚘",
    layout="centered", # Mobile-first feel
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION (Shared with Admin App) ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("⚠️ Server Connection Error. Please try again later.")
    st.stop()

# --- HIGH-END CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap');
    
    .stApp { 
        background-color: #000000;
        font-family: 'Outfit', sans-serif;
        color: white;
    }
    
    /* GLASSMORPHISM CARD STYLES */
    .glass-card {
        background: rgba(20, 20, 20, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* MEMBERSHIP CARD - GOLD/PLATINUM LOOK */
    .member-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
        border-radius: 20px;
        padding: 25px;
        position: relative;
        overflow: hidden;
        border: 1px solid #444;
        box-shadow: 0 10px 40px -10px rgba(0,0,0,0.8);
        height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .card-tier-Gold { background: linear-gradient(135deg, #FFD700 0%, #B8860B 100%); color: black; }
    .card-tier-Platinum { background: linear-gradient(135deg, #E5E4E2 0%, #505050 100%); color: black; }
    .card-tier-Silver { background: linear-gradient(135deg, #C0C0C0 0%, #708090 100%); color: white; }

    .card-chip {
        width: 50px; height: 35px;
        background: linear-gradient(135deg, #d4af37 0%, #996515 100%);
        border-radius: 5px;
        margin-bottom: 20px;
        border: 1px solid rgba(0,0,0,0.2);
    }

    /* NEON BUTTONS */
    .stButton button {
        background: #00d4ff !important;
        color: black !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px !important;
        text-transform: uppercase;
    }
    
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE MANAGEMENT ---
if 'cust_phone' not in st.session_state: st.session_state.cust_phone = None
if 'cust_name' not in st.session_state: st.session_state.cust_name = None
if 'active_plate' not in st.session_state: st.session_state.active_plate = None

# ==============================================================================
# 1. AUTHENTICATION (PHONE NUMBER LOGIN)
# ==============================================================================
if not st.session_state.cust_phone:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.image("logo.png", width=200) # Ensure you have the logo file
    st.title("Welcome Back.")
    st.caption("Access your garage, bookings, and membership.")
    
    with st.form("login_form"):
        phone_input = st.text_input("Enter your Phone Number", placeholder="e.g. 08012345678")
        submitted = st.form_submit_button("ENTER GARAGE", use_container_width=True)
        
        if submitted:
            # CLEAN PHONE INPUT (Remove spaces, basic validation)
            clean_phone = phone_input.replace(" ", "").strip()
            
            # DATABASE CALL: Check if this phone exists in customers table
            # We use ILIKE for partial matching or exact matching logic
            q = "SELECT * FROM customers WHERE phone LIKE :p"
            df = conn.query(q, params={"p": f"%{clean_phone}%"}, ttl=0)
            
            if not df.empty:
                st.session_state.cust_phone = df.iloc[0]['phone']
                st.session_state.cust_name = df.iloc[0]['name']
                # Default to the first car found
                st.session_state.active_plate = df.iloc[0]['plate'] 
                st.rerun()
            else:
                st.error("Number not found. Please register at the front desk first.")
    
    st.info("ℹ️ First time? Visit RideBoss Victoria Island to create your profile.")
    st.stop()

# ==============================================================================
# 2. MAIN APP INTERFACE
# ==============================================================================

# --- SIDEBAR: MULTI-CAR MANAGEMENT ---
with st.sidebar:
    st.header(f"Hey, {st.session_state.cust_name}")
    st.write("My Garage")
    
    # FETCH ALL CARS LINKED TO THIS PHONE
    my_cars = conn.query("SELECT plate, visits FROM customers WHERE phone = :p", params={"p": st.session_state.cust_phone}, ttl=0)
    
    # 1. Car Switcher
    car_list = my_cars['plate'].tolist()
    selected_plate = st.radio("Active Vehicle", car_list, index=car_list.index(st.session_state.active_plate) if st.session_state.active_plate in car_list else 0)
    st.session_state.active_plate = selected_plate
    
    st.divider()
    
    # 2. Add New Car Logic
    with st.expander("➕ Add Another Vehicle"):
        with st.form("add_car"):
            new_plate = st.text_input("Plate Number").upper()
            if st.form_submit_button("Link Vehicle"):
                if new_plate:
                    try:
                        with conn.session as s:
                            # Insert new row with SAME Name/Phone but NEW Plate
                            s.execute(text("""
                                INSERT INTO customers (plate, name, phone, visits, last_visit) 
                                VALUES (:pl, :nm, :ph, 0, :lv)
                                ON CONFLICT (plate) DO UPDATE SET phone=:ph
                            """), {
                                "pl": new_plate, 
                                "nm": st.session_state.cust_name, 
                                "ph": st.session_state.cust_phone,
                                "lv": datetime.now().strftime("%Y-%m-%d")
                            })
                            s.commit()
                        st.success("Vehicle Added!")
                        st.rerun()
                    except Exception as e:
                        st.error("Could not add vehicle.")

    if st.button("Logout"):
        st.session_state.cust_phone = None
        st.rerun()

# --- TOP NAV ---
# Simple Clean Header
c1, c2 = st.columns([3, 1])
c1.markdown(f"### 🚘 {st.session_state.active_plate}")
c1.caption("Start your engine.")
if c2.button("↻"): st.rerun()

# --- TABBED NAVIGATION ---
tab_home, tab_book, tab_mem, tab_hist = st.tabs(["HOME", "REQUEST WASH", "MEMBERSHIP", "HISTORY"])

# ------------------------------------------------------------------------------
# TAB 1: HOME (LIVE STATUS)
# ------------------------------------------------------------------------------
with tab_home:
    # DATABASE CALL: Check live_bays for the active plate
    live_status = conn.query("SELECT * FROM live_bays WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if not live_status.empty:
        status_row = live_status.iloc[0]
        stat_msg = status_row['status']
        staff_msg = status_row['staff']
        
        # DYNAMIC VISUALS BASED ON STATUS
        if stat_msg == "READY":
            st.success("✅ YOUR VEHICLE IS READY!")
            st.markdown("""
                <div class='glass-card' style='border-left: 5px solid #2ecc71;'>
                    <h3>Ready for Pickup</h3>
                    <p>Your vehicle has been detailed and is waiting at the exit bay.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            # Active Washing Animation Placeholder
            st.info(f"💦 CURRENTLY IN: {stat_msg}")
            percent = 10
            if stat_msg == "WET BAY": percent = 40
            elif stat_msg == "DRY BAY": percent = 80
            
            st.progress(percent, text=f"Work in progress by {staff_msg}")
            st.markdown(f"**Service:** {status_row['service_detail']}")
            
    else:
        st.markdown("""
            <div class='glass-card'>
                <h3 style='margin:0;'>Vehicle is Idle</h3>
                <p style='color:#888;'>Not currently in the shop.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Marketing Banner
        st.markdown("#### 🎁 Offers for you")
        promos = conn.query("SELECT * FROM promotions WHERE created_for_plate = :p AND status='ACTIVE'", params={"p": st.session_state.active_plate}, ttl=0)
        if not promos.empty:
            code = promos.iloc[0]['code']
            disc = promos.iloc[0]['discount_pc']
            st.markdown(f"""
                <div style="background: linear-gradient(45deg, #FFD700, #FDB931); color:black; padding:15px; border-radius:10px;">
                    <strong>👑 VIP REWARD AVAILABLE!</strong><br>
                    Use code <h1>{code}</h1> for {disc}% OFF your next wash.
                </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("No active rewards. Visit us to earn points!")

# ------------------------------------------------------------------------------
# TAB 2: REQUEST WASH (BOOKING)
# ------------------------------------------------------------------------------
with tab_book:
    st.subheader("Book a Service")
    
    # 1. Fetch Prices from DB
    prices_df = conn.query("SELECT service, price, vehicle_type FROM wash_prices", ttl=0)
    
    # 2. Select Vehicle Type (to filter prices)
    v_type = st.selectbox("Vehicle Size", ["Sedan", "SUV", "Truck", "Crossover", "Bike"])
    
    # 3. Filter Services
    available_svcs = prices_df[prices_df['vehicle_type'] == v_type]
    
    if available_svcs.empty:
        st.warning("Please contact support for pricing.")
    else:
        # Create a dictionary for the dropdown
        svc_dict = {f"{row['service']} (₦{row['price']:,.0f})": row['service'] for i, row in available_svcs.iterrows()}
        selected_svc_label = st.selectbox("Choose Service", list(svc_dict.keys()))
        selected_svc_name = svc_dict[selected_svc_label]
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📅 NOTIFY TEAM I'M COMING", use_container_width=True):
            # Write to NOTIFICATIONS table so Admin sees it in "Command Center"
            msg = f"🔔 BOOKING REQUEST: {st.session_state.active_plate} is requesting {selected_svc_name} ({v_type})."
            ts = datetime.now().strftime("%H:%M:%S")
            
            with conn.session as s:
                s.execute(text("INSERT INTO notifications (message, timestamp) VALUES (:m, :t)"), {"m": msg, "t": ts})
                s.commit()
            
            st.success("Request Sent! We'll be ready for you.")
            st.balloons()

# ------------------------------------------------------------------------------
# TAB 3: MEMBERSHIP (THE CARD)
# ------------------------------------------------------------------------------
with tab_mem:
    st.subheader("Membership Card")
    
    # DATABASE CALL: Fetch membership info
    mem_data = conn.query("SELECT * FROM memberships WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if mem_data.empty:
        st.markdown("""
            <div style='text-align:center; padding:40px; border:1px dashed #444; border-radius:15px;'>
                <h3>No Membership Found</h3>
                <p>Buy a Silver, Gold, or Platinum card at the counter to save money on washes!</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        row = mem_data.iloc[0]
        card_type = row.get('card_type', 'Silver') # Default to silver if null
        serial = row.get('card_serial', '0000')
        bal = row['balance_washes']
        
        # Clean up card type string for CSS class (e.g. "Gold (10 Washes)" -> "Gold")
        css_class = "Silver"
        if "Gold" in card_type: css_class = "Gold"
        elif "Platinum" in card_type: css_class = "Platinum"
        
        # RENDER THE CARD
        st.markdown(f"""
            <div class="member-card card-tier-{css_class}">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div class="card-chip"></div>
                    <div style="text-align:right; font-weight:900; opacity:0.7;">RIDEBOSS<br>PREMIUM</div>
                </div>
                
                <div style="text-align:center; font-family:monospace; font-size: 24px; letter-spacing: 4px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    •••• •••• •••• {serial[-4:] if len(serial) > 4 else serial}
                </div>
                
                <div style="display:flex; justify-content:space-between; align-items:end; font-size:12px;">
                    <div>
                        <div style="opacity:0.7; font-size:10px;">HOLDER NAME</div>
                        <div style="font-size:14px; font-weight:bold;">{st.session_state.cust_name.upper()}</div>
                    </div>
                    <div>
                         <div style="opacity:0.7; font-size:10px;">BALANCE</div>
                        <div style="font-size:18px; font-weight:900;">{bal} WASHES</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if bal < 2:
            st.error(f"⚠️ Low Balance ({bal}). Please top up soon.")

# ------------------------------------------------------------------------------
# TAB 4: HISTORY
# ------------------------------------------------------------------------------
with tab_hist:
    st.subheader("Service History")
    
    hist_df = conn.query("""
        SELECT timestamp, services, total, staff 
        FROM sales 
        WHERE plate = :p 
        ORDER BY id DESC LIMIT 10
    """, params={"p": st.session_state.active_plate}, ttl=0)
    
    if hist_df.empty:
        st.info("No history yet.")
    else:
        for i, row in hist_df.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['services']}**")
                c1.caption(f"📅 {row['timestamp']} | 👨‍🔧 {row['staff']}")
                c2.write(f"**₦{row['total']:,.0f}**")
                st.divider()

