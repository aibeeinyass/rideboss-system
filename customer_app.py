import streamlit as st
import pandas as pd
from datetime import datetime
import time
from sqlalchemy import text

# ==============================================================================
# RIDEBOSS CLIENT - ULTRA EDITION
# ==============================================================================

st.set_page_config(
    page_title="My RideBoss", 
    page_icon="🚘",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION (Shared with Admin App) ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("⚠️ Connection Error. The server might be sleeping.")
    st.stop()

# --- ULTRA CSS STYLING (Mobile-First & Dark Mode) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap');
    
    .stApp { 
        background-color: #050505;
        font-family: 'Outfit', sans-serif;
        color: #e0e0e0;
    }
    
    /* GLASSMORPHISM CARD */
    .glass-card {
        background: rgba(30, 30, 30, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    }

    /* MEMBERSHIP CARD (CSS MAGIC) */
    .member-card {
        border-radius: 20px;
        padding: 25px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 15px 35px -5px rgba(0,0,0,0.8);
        height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.3s ease;
    }
    .member-card:hover { transform: translateY(-5px); }
    
    .card-tier-Gold { background: linear-gradient(135deg, #FFD700 0%, #B8860B 100%); color: black; }
    .card-tier-Platinum { background: linear-gradient(135deg, #E5E4E2 0%, #303030 100%); color: black; }
    .card-tier-Silver { background: linear-gradient(135deg, #C0C0C0 0%, #708090 100%); color: white; }

    .card-chip {
        width: 50px; height: 35px;
        background: linear-gradient(135deg, #d4af37 0%, #996515 100%);
        border-radius: 6px;
        border: 1px solid rgba(0,0,0,0.2);
    }

    /* NEON ACTION BUTTONS */
    .stButton button {
        background: #00d4ff !important;
        color: #000 !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 16px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        box-shadow: 0 0 15px #00d4ff;
        transform: scale(1.02);
    }
    
    /* CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a1a;
        border-radius: 8px;
        padding: 10px 20px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00d4ff !important;
        color: black !important;
        font-weight: bold;
    }

    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'cust_phone' not in st.session_state: st.session_state.cust_phone = None
if 'cust_name' not in st.session_state: st.session_state.cust_name = None
if 'active_plate' not in st.session_state: st.session_state.active_plate = None

# ==============================================================================
# 1. AUTHENTICATION (PHONE NUMBER GATEWAY)
# ==============================================================================
if not st.session_state.cust_phone:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # You can replace this with st.image("logo.png") if you have one
    st.markdown("<h1 style='text-align: center; color: #00d4ff;'>RIDEBOSS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Premium Auto Care Concierge</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        phone_input = st.text_input("Mobile Number", placeholder="080...", help="Enter the number registered with us")
        
        if st.button("ACCESS MY GARAGE", use_container_width=True):
            clean_phone = phone_input.replace(" ", "").strip()
            
            # Query Logic
            q = "SELECT * FROM customers WHERE phone LIKE :p"
            try:
                df = conn.query(q, params={"p": f"%{clean_phone}%"}, ttl=0)
                
                if not df.empty:
                    st.session_state.cust_phone = df.iloc[0]['phone']
                    st.session_state.cust_name = df.iloc[0]['name']
                    st.session_state.active_plate = df.iloc[0]['plate']
                    st.toast(f"Welcome back, {df.iloc[0]['name']}!", icon="👋")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Number not found. Please visit the front desk to register.")
            except Exception as e:
                st.error("Database unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.stop()

# ==============================================================================
# 2. MAIN APP INTERFACE
# ==============================================================================

# --- SIDEBAR: MULTI-CAR MANAGEMENT ---
with st.sidebar:
    st.markdown(f"### 👋 Hi, {st.session_state.cust_name}")
    st.caption("Manage your fleet")
    
    # Fetch all cars owned by this phone number
    my_cars = conn.query("SELECT plate FROM customers WHERE phone = :p", params={"p": st.session_state.cust_phone}, ttl=0)
    car_list = my_cars['plate'].tolist()
    
    selected_plate = st.radio("Active Vehicle", car_list, index=car_list.index(st.session_state.active_plate) if st.session_state.active_plate in car_list else 0)
    
    if selected_plate != st.session_state.active_plate:
        st.session_state.active_plate = selected_plate
        st.rerun()

    st.divider()
    
    # Add New Car Logic
    with st.expander("➕ Link New Vehicle"):
        with st.form("add_car_form"):
            new_plate = st.text_input("Plate Number").upper()
            if st.form_submit_button("Add Vehicle"):
                if new_plate:
                    try:
                        with conn.session as s:
                            s.execute(text("""
                                INSERT INTO customers (plate, name, phone, visits, last_visit) 
                                VALUES (:pl, :nm, :ph, 0, :lv)
                                ON CONFLICT (plate) DO UPDATE SET phone=:ph
                            """), {
                                "pl": new_plate, "nm": st.session_state.cust_name, 
                                "ph": st.session_state.cust_phone, "lv": datetime.now().strftime("%Y-%m-%d")
                            })
                            s.commit()
                        st.success("Vehicle Added!")
                        st.rerun()
                    except:
                        st.error("Error adding vehicle.")

    if st.button("Logout", type="secondary"):
        st.session_state.cust_phone = None
        st.rerun()

# --- HEADER AREA ---
c1, c2 = st.columns([4, 1])
with c1:
    st.markdown(f"<h2 style='margin:0; padding:0;'>{st.session_state.active_plate}</h2>", unsafe_allow_html=True)
    st.caption("Tap 'Request Wash' to book.")
with c2:
    if st.button("↻"): st.rerun()

st.markdown("---")

# --- NAVIGATION TABS ---
tab_home, tab_book, tab_mem, tab_hist = st.tabs(["LIVE STATUS", "REQUEST WASH", "MEMBERSHIP", "HISTORY"])

# ------------------------------------------------------------------------------
# TAB 1: LIVE STATUS (THE "PIZZA TRACKER")
# ------------------------------------------------------------------------------
with tab_home:
    # Check if car is in live_bays
    live_status = conn.query("SELECT * FROM live_bays WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if not live_status.empty:
        status_row = live_status.iloc[0]
        current_status = status_row['status']
        staff_assigned = status_row['staff']
        service_name = status_row['service_detail']
        
        # Determine Progress %
        progress = 0
        status_color = "#3498db"
        
        if current_status == "WAITING": 
            progress = 10
            msg = "🕒 Waiting in Queue"
        elif current_status == "WET BAY": 
            progress = 50
            msg = "💦 Washing in Progress"
        elif current_status == "DRY BAY": 
            progress = 80
            msg = "💨 Drying & Polishing"
        elif current_status == "READY": 
            progress = 100
            msg = "✅ Ready for Pickup"
            status_color = "#2ecc71"

        # RENDER TRACKER
        st.markdown(f"""
            <div class='glass-card' style='border-left: 5px solid {status_color};'>
                <h3 style='color:{status_color}; margin-top:0;'>{msg}</h3>
                <p><strong>Service:</strong> {service_name}</p>
                <p><strong>Specialist:</strong> {staff_assigned}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.progress(progress)
        
        if current_status == "READY":
            st.balloons()
            st.info("Your key is waiting at the reception.")
            
    else:
        # IDLE STATE
        st.markdown("""
            <div class='glass-card' style='text-align: center; opacity: 0.8;'>
                <h3>💤 Vehicle Idle</h3>
                <p>Your vehicle is not currently in our shop.</p>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 2: REQUEST WASH (DIGITAL BOOKING)
# ------------------------------------------------------------------------------
with tab_book:
    st.markdown("### 📅 Book a Slot")
    
    with st.container():
        # Get Prices
        prices_df = conn.query("SELECT service, price, vehicle_type FROM wash_prices", ttl=0)
        
        # Form
        v_type = st.selectbox("Select Vehicle Type", ["Sedan", "SUV", "Truck", "Crossover", "Bike"])
        
        # Filter available services
        available_svcs = prices_df[prices_df['vehicle_type'] == v_type]
        
        if not available_svcs.empty:
            svc_options = {f"{r['service']} - ₦{r['price']:,.0f}": r['service'] for i, r in available_svcs.iterrows()}
            selected_label = st.selectbox("Choose Service Package", list(svc_options.keys()))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("📢 NOTIFY RECEPTION", use_container_width=True):
                real_svc_name = svc_options[selected_label]
                
                # Insert Notification for Admin
                timestamp = datetime.now().strftime("%H:%M:%S")
                notif_msg = f"📱 APP REQUEST: {st.session_state.active_plate} wants {real_svc_name} ({v_type})"
                
                try:
                    with conn.session as s:
                        s.execute(text("INSERT INTO notifications (message, timestamp) VALUES (:m, :t)"), 
                                  {"m": notif_msg, "t": timestamp})
                        
                        # --- INSERTED CODE START ---
                        s.execute(text("""
                            INSERT INTO live_bays (plate, status, service_detail, staff, entry_time) 
                            VALUES (:pl, 'APP_PENDING', :svc, 'Reviewing', :tm)
                            ON CONFLICT (plate) DO UPDATE SET status = 'APP_PENDING'
                        """), {
                            "pl": st.session_state.active_plate,
                            "svc": real_svc_name,
                            "tm": timestamp
                        })
                        # --- INSERTED CODE END ---
                        
                        s.commit()
                    
                    st.success("Request Sent! Please drive to the entrance.")
                except Exception as e:
                    st.error(f"Could not send request: {e}")
        else:
            st.warning("No pricing data available for this vehicle type.")

# ------------------------------------------------------------------------------
# TAB 3: MEMBERSHIP (DIGITAL WALLET)
# ------------------------------------------------------------------------------
with tab_mem:
    mem_data = conn.query("SELECT * FROM memberships WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if not mem_data.empty:
        row = mem_data.iloc[0]
        card_type = row.get('card_type', 'Silver')
        serial = row.get('card_serial', '0000')
        bal = row['balance_washes']
        
        # Determine CSS class for gradient
        tier_class = "Silver"
        if "Gold" in card_type: tier_class = "Gold"
        elif "Platinum" in card_type: tier_class = "Platinum"
        
        st.markdown(f"""
            <div class="member-card card-tier-{tier_class}">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div class="card-chip"></div>
                    <div style="text-align:right; font-weight:900; opacity:0.8;">RIDEBOSS<br>VIP</div>
                </div>
                <div style="text-align:center; font-family:monospace; font-size: 22px; letter-spacing: 3px; font-weight: bold;">
                    •••• •••• {serial[-4:]}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:end; font-size:12px;">
                    <div>
                        <div style="opacity:0.7;">OWNER</div>
                        <div style="font-size:14px; font-weight:bold;">{st.session_state.cust_name[:15].upper()}</div>
                    </div>
                    <div>
                         <div style="opacity:0.7;">BALANCE</div>
                        <div style="font-size:20px; font-weight:900;">{bal} WASHES</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No active membership found.")
        st.markdown("Visit the reception to upgrade to **Gold** or **Platinum**.")

# ------------------------------------------------------------------------------
# TAB 4: HISTORY & RECEIPTS
# ------------------------------------------------------------------------------
with tab_hist:
    st.markdown("### Past Services")
    
    hist_df = conn.query("""
        SELECT timestamp, services, total 
        FROM sales 
        WHERE plate = :p 
        ORDER BY id DESC LIMIT 5
    """, params={"p": st.session_state.active_plate}, ttl=0)
    
    if not hist_df.empty:
        for i, row in hist_df.iterrows():
            with st.container():
                st.markdown(f"""
                    <div style="padding: 10px; border-bottom: 1px solid #333;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold; color:#00d4ff;">{row['services']}</span>
                            <span style="font-weight:bold;">₦{row['total']:,.0f}</span>
                        </div>
                        <div style="color:#888; font-size: 12px;">{row['timestamp']}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("No history available yet.")
