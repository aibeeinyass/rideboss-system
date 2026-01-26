import streamlit as st
import pandas as pd
from datetime import datetime
import time
import requests # NEW: For Payment APIs
import random   # NEW: For generating Refs
from sqlalchemy import text

# ==============================================================================
# CONFIGURATION & API KEYS
# ==============================================================================
# ⚠️ SECURITY NOTE: In production, put these in st.secrets
PAYSTACK_SECRET_KEY = "sk_test_xxxxxxxxxxxxxxxxxxxx" 
DEMO_MODE = True  # Set to False to use real Paystack API

# --- MEMBERSHIP PRICING CONFIGURATION ---
MEMBERSHIP_PLANS = {
    "Silver Refill": {"price": 15000, "washes": 3, "tier": "Silver"},
    "Gold Membership": {"price": 50000, "washes": 12, "tier": "Gold"},
    "Platinum VIP": {"price": 120000, "washes": 30, "tier": "Platinum"},
}

# ==============================================================================
# RIDEBOSS CLIENT - ULTRA EDITION
# ==============================================================================

st.set_page_config(
    page_title="My RideBoss", 
    page_icon="🚘",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("⚠️ Connection Error. The server might be sleeping.")
    st.stop()

# --- ULTRA CSS STYLING ---
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

    /* MEMBERSHIP CARD */
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

    /* PAYMENT TABS */
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
    
    /* MOBILE META */
    viewport { width: device-width; initial-scale: 1; viewport-fit: cover; }
    ::-webkit-scrollbar { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'cust_phone' not in st.session_state: st.session_state.cust_phone = None
if 'cust_name' not in st.session_state: st.session_state.cust_name = None
if 'active_plate' not in st.session_state: st.session_state.active_plate = None
if 'pending_ref' not in st.session_state: st.session_state.pending_ref = None

# ==============================================================================
# HELPER: PAYMENT VERIFICATION LOGIC
# ==============================================================================
def verify_paystack_transaction(reference, plan_name):
    """
    Verifies payment with Paystack and Updates Database 
    Returns: (Success Boolean, Message String)
    """
    amount = MEMBERSHIP_PLANS[plan_name]['price']
    washes_to_add = MEMBERSHIP_PLANS[plan_name]['washes']
    new_tier = MEMBERSHIP_PLANS[plan_name]['tier']
    
    # 1. API VERIFICATION
    if not DEMO_MODE:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if data['data']['status'] != 'success':
                    return False, "Payment failed at gateway."
                # Check amount (Paystack is in kobo)
                if data['data']['amount'] < (amount * 100):
                    return False, "Amount mismatch."
            else:
                return False, "Could not connect to Gateway."
        except:
            return False, "Network Error."
    else:
        time.sleep(1) # Simulate network lag
        # In Demo Mode, we assume success if they clicked the button
        pass

    # 2. DATABASE UPDATE (The "Hybrid" Sync)
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        with conn.session as s:
            # A. Update Membership (Or Create if new)
            # We use Upsert logic: If plate exists, add balance. If not, insert.
            s.execute(text("""
                INSERT INTO memberships (plate, balance_washes, card_type, card_serial)
                VALUES (:p, :w, :t, 'APP-DIGITAL')
                ON CONFLICT (plate) 
                DO UPDATE SET 
                    balance_washes = memberships.balance_washes + :w,
                    card_type = :t
            """), {"p": st.session_state.active_plate, "w": washes_to_add, "t": new_tier})
            
            # B. Update Financials (Sales Table)
            # This ensures your Admin App Financial Tab updates instantly
            s.execute(text("""
                INSERT INTO sales (plate, services, total, method, staff, timestamp, type, status) 
                VALUES (:p, :svc, :tot, 'ONLINE_PAYMENT', 'Automated', :tm, 'MEMBERSHIP', 'PAID')
            """), {
                "p": st.session_state.active_plate,
                "svc": f"App Top-up: {plan_name}",
                "tot": amount,
                "tm": current_time
            })
            s.commit()
        return True, "Success"
    except Exception as e:
        return False, f"Database Error: {e}"

# ==============================================================================
# 1. AUTHENTICATION
# ==============================================================================
if not st.session_state.cust_phone:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #00d4ff;'>RIDEBOSS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Premium Auto Care Concierge</p><br>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        phone_input = st.text_input("Mobile Number", placeholder="080...", help="Enter the number registered with us")
        
        if st.button("ACCESS MY GARAGE", use_container_width=True):
            clean_phone = phone_input.replace(" ", "").strip()
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
                    st.error("Number not found. Please visit the front desk.")
            except:
                st.error("Database unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 2. MAIN APP INTERFACE
# ==============================================================================

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👋 Hi, {st.session_state.cust_name}")
    st.caption("Manage your fleet")
    my_cars = conn.query("SELECT plate FROM customers WHERE phone = :p", params={"p": st.session_state.cust_phone}, ttl=0)
    car_list = my_cars['plate'].tolist()
    
    # Handle if no cars found (rare edge case)
    if not car_list: car_list = ["NO VEHICLE"]
    
    current_index = 0
    if st.session_state.active_plate in car_list:
        current_index = car_list.index(st.session_state.active_plate)
        
    selected_plate = st.radio("Active Vehicle", car_list, index=current_index)
    
    if selected_plate != st.session_state.active_plate:
        st.session_state.active_plate = selected_plate
        st.rerun()

    st.divider()
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
                    except: st.error("Error adding vehicle.")
    if st.button("Logout", type="secondary"):
        st.session_state.cust_phone = None
        st.rerun()

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.markdown(f"<h2 style='margin:0; padding:0;'>{st.session_state.active_plate}</h2>", unsafe_allow_html=True)
    st.caption("Tap 'Request Wash' to book.")
with c2:
    if st.button("↻"): st.rerun()

st.markdown("---")

# --- NAVIGATION TABS ---
# Renamed TAB 3 to WALLET to indicate payment features
tab_home, tab_book, tab_mem, tab_hist = st.tabs(["LIVE STATUS", "REQUEST WASH", "WALLET & PAY", "HISTORY"])

# ------------------------------------------------------------------------------
# TAB 1: LIVE STATUS
# ------------------------------------------------------------------------------
with tab_home:
    live_status = conn.query("SELECT * FROM live_bays WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if not live_status.empty:
        status_row = live_status.iloc[0]
        current_status = status_row['status']
        staff_assigned = status_row['staff']
        service_name = status_row['service_detail']
        
        progress = 0
        status_color = "#3498db"
        msg = "🕒 Processing"
        
        if current_status == "APP_PENDING":
            progress = 5
            msg = "📲 Request Sent"
            status_color = "#f39c12" # Orange
        elif current_status == "WAITING": 
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
        st.markdown("""
            <div class='glass-card' style='text-align: center; opacity: 0.8;'>
                <h3>💤 Vehicle Idle</h3>
                <p>Your vehicle is not currently in our shop.</p>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 2: REQUEST WASH
# ------------------------------------------------------------------------------
with tab_book:
    st.markdown("### 📅 Book a Slot")
    
    with st.container():
        prices_df = conn.query("SELECT service, price, vehicle_type FROM wash_prices", ttl=0)
        v_type = st.selectbox("Select Vehicle Type", ["Sedan", "SUV", "Truck", "Crossover", "Bike"])
        available_svcs = prices_df[prices_df['vehicle_type'] == v_type]
        
        if not available_svcs.empty:
            svc_options = {f"{r['service']} - ₦{r['price']:,.0f}": r['service'] for i, r in available_svcs.iterrows()}
            selected_label = st.selectbox("Choose Service Package", list(svc_options.keys()))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("📢 NOTIFY RECEPTION", use_container_width=True):
                real_svc_name = svc_options[selected_label]
                timestamp = datetime.now().strftime("%H:%M:%S")
                notif_msg = f"📱 APP REQUEST: {st.session_state.active_plate} wants {real_svc_name} ({v_type})"
                
                try:
                    with conn.session as s:
                        s.execute(text("INSERT INTO notifications (message, timestamp) VALUES (:m, :t)"), 
                                  {"m": notif_msg, "t": timestamp})
                        
                        # Use vehicle_type column if it exists, otherwise prompt admin to add it
                        s.execute(text("""
                            INSERT INTO live_bays (plate, status, service_detail, staff, entry_time, vehicle_type) 
                            VALUES (:pl, 'APP_PENDING', :svc, 'Reviewing', :tm, :vt)
                            ON CONFLICT (plate) DO UPDATE SET status = 'APP_PENDING'
                        """), {
                            "pl": st.session_state.active_plate,
                            "svc": real_svc_name,
                            "tm": timestamp,
                            "vt": v_type
                        })
                        s.commit()
                    st.success("Request Sent! Drive to entrance.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("No pricing data available.")

# ------------------------------------------------------------------------------
# TAB 3: WALLET & MEMBERSHIP (UPDATED WITH CHECKOUT)
# ------------------------------------------------------------------------------
with tab_mem:
    # 1. FETCH CURRENT STATUS
    mem_data = conn.query("SELECT * FROM memberships WHERE plate = :p", params={"p": st.session_state.active_plate}, ttl=0)
    
    if not mem_data.empty:
        row = mem_data.iloc[0]
        card_type = row.get('card_type', 'Silver')
        serial = row.get('card_serial', 'DIGITAL')
        bal = row['balance_washes']
        
        tier_class = "Silver"
        if "Gold" in card_type: tier_class = "Gold"
        elif "Platinum" in card_type: tier_class = "Platinum"
        
        # DISPLAY CARD
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
        st.info("No active membership. Top up below to create one.")

    st.markdown("---")
    
    # 2. CHECKOUT / TOP-UP SECTION
    st.subheader("💳 Top Up / Upgrade")
    
    # Choose Plan
    plan_names = list(MEMBERSHIP_PLANS.keys())
    selected_plan = st.selectbox("Select Package", plan_names)
    
    plan_details = MEMBERSHIP_PLANS[selected_plan]
    st.caption(f"**Benefits:** {plan_details['washes']} Washes | **Tier:** {plan_details['tier']}")
    st.markdown(f"### Price: ₦{plan_details['price']:,.0f}")
    
    # PAY BUTTON LOGIC
    if st.button("PROCEED TO PAYMENT", type="primary", use_container_width=True):
        # Generate Unique Reference
        ref = f"RB-{random.randint(10000,99999)}-{int(time.time())}"
        st.session_state.pending_ref = {"ref": ref, "plan": selected_plan}
        
        # In Real Mode, this would redirect to Paystack Standard Checkout URL
        # We construct a URL or use st.link_button
        pass 

    # 3. VERIFICATION UI (Appears after "Proceed" is clicked)
    if st.session_state.pending_ref:
        curr_ref = st.session_state.pending_ref['ref']
        curr_plan = st.session_state.pending_ref['plan']
        
        st.markdown(f"""
            <div style="background: #111; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-top: 10px;">
                <p style="color: #888; font-size: 12px; margin:0;">TRANSACTION REFERENCE</p>
                <p style="font-family: monospace; font-size: 18px; color: #00d4ff; margin:0;">{curr_ref}</p>
                <hr style="border-color: #333;">
                <p style="font-size: 14px;">1. Click the link below to pay securely.</p>
                <p style="font-size: 14px;">2. Return here and click "I Have Paid".</p>
            </div>
        """, unsafe_allow_html=True)
        
        # THE PAYMENT LINK (Demo or Real)
        pay_url = "#"
        if DEMO_MODE:
            pay_url = "https://www.google.com" # Just a placeholder
            st.warning("⚠️ DEMO MODE: Click link, then click 'I Have Paid' below.")
        else:
            # Construct Paystack Payment Page URL (Simplified)
            # Ideally you use Paystack Initialize API to get authorization_url
            pay_url = "https://paystack.com/pay/your-custom-slug" 
            
        st.link_button(f"👉 PAY ₦{MEMBERSHIP_PLANS[curr_plan]['price']:,} NOW", pay_url)
        
        # VERIFY BUTTON
        if st.button("✅ I HAVE PAID (VERIFY)"):
            with st.spinner("Verifying Transaction..."):
                success, msg = verify_paystack_transaction(curr_ref, curr_plan)
                
                if success:
                    st.balloons()
                    st.success(f"PAYMENT SUCCESSFUL! {MEMBERSHIP_PLANS[curr_plan]['washes']} Washes Added.")
                    st.session_state.pending_ref = None # Reset
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Verification Failed: {msg}")

# ------------------------------------------------------------------------------
# TAB 4: HISTORY
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
