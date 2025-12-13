import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
import random

from models import Character, GameSystem, WORKOUT_MULTIPLIERS

def get_rpg_loading_msg():
    messages = [
        "🎲 Zarlar Atılıyor...",
        "⚔️ Kılıç Bileniyor...",
        "📜 Parşömenler Okunuyor...",
        "🧪 İksir Karıştırılıyor...",
        "🐉 Ejderha Uykusundan Uyanıyor...",
        "🧙‍♂️ Büyü Hazırlanıyor...",
        "🛡️ Kalkan Parlatılıyor...",
        "👣 İzler Sürülüyor...",
        "👹 Boss Stratejisi Kuruluyor...",
        "✨ Mana Toplanıyor..."
    ]
    return random.choice(messages)

# Page Config
st.set_page_config(page_title="Levent Fitness RPG", page_icon="⚔️", layout="wide")

# Custom CSS for "Premium" look & Mobile Optimization
st.markdown("""
<style>
    /* Mobile Optimization: Reduce wrapper padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Existing Premium Styles */
    .stProgress > div > div > div > div {
        background-color: #f63366;
    }
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- Helper Functions ---
def load_user(name, password):
    chars = GameSystem.load_characters()
    if name in chars:
        char = chars[name]
        if char.check_password(password):
            st.session_state.current_user = char
            return True, "Giriş Başarılı"
        return False, "Hatalı Şifre"
    return False, "Kullanıcı Bulunamadı"

def create_user(name, char_class, password, email, avatar_id):
    # Use explicit keyword arguments to avoid TypeError
    new_char = Character(
        name=name, 
        char_class=char_class, 
        password=password, 
        email=email, 
        avatar_id=avatar_id
    )
    GameSystem.save_character(new_char)
    st.session_state.current_user = new_char

def save_current_user():
    if st.session_state.current_user:
        GameSystem.save_character(st.session_state.current_user)

# --- Views ---

def admin_dashboard_view():
    st.title("👨‍🏫 Eğitmen Kontrol Paneli")
    
    if st.button("Çıkış Yap"):
        st.session_state.current_user = None
        st.rerun()
        
    chars = GameSystem.load_characters()
    if not chars:
        st.warning("Henüz hiç öğrenci kaydı yok.")
        return

    # Sidebar: Manuel Hediye Dağıt
    with st.sidebar:
        st.header("🎁 Hediye Dağıt")
        st.info("Herhangi bir öğrenciye anında XP gönder.")
        
        student_names = list(chars.keys())
        selected_student = st.selectbox("Öğrenci Seç", student_names)
        gift_message = st.text_input("Mesaj", "Harika gidiyorsun!")
        gift_xp_amount = st.number_input("XP Miktarı", min_value=10, value=100, step=10)
        
        if st.button("Hediyeyi Gönder"):
            target_char = chars[selected_student]
            target_char.log_activity("Gift", f"🎁 {gift_message}", gift_xp_amount)
            GameSystem.save_character(target_char)
            st.success(f"{selected_student} kişisine {gift_xp_amount} XP gönderildi!")
            st.rerun()

    # Data Preparation
    data = []
    for char in chars.values():
        data.append({
            "İsim": char.name,
            "Email": getattr(char, 'email', '-'),
            "Seviye": char.level,
            "XP": char.xp,
            "STR": char.stats.get("STR", 0),
            "AGI": char.stats.get("AGI", 0),
            "VIT": char.stats.get("VIT", 0),
            "WIS": char.stats.get("WIS", 0),
            "Son Aktivite": char.history[-1]['date'][:16] if char.history else "Yok"
        })
    df = pd.DataFrame(data)

    # Top Metrics
    m1, m2 = st.columns(2)
    m1.metric("Toplam Öğrenci", len(df))
    m2.metric("Ortalama Seviye", f"{df['Seviye'].mean():.1f}")

    # Main Table
    tab_list, tab_approve = st.tabs(["📊 Genel Durum", "📝 Onay Bekleyenler"])

    with tab_list:
        st.dataframe(df, use_container_width=True)

        # Charts
        st.subheader("Seviye Dağılımı")
        try:
             fig_lvl = px.histogram(df, x='Seviye', title='Seviye Dağılımı', nbins=15)
             st.plotly_chart(fig_lvl, use_container_width=True)
        except:
             st.info("Grafik için yeterli veri yok.")

    with tab_approve:
        st.subheader("Onay Bekleyen Aktiviteler")
        pending_found = False
        for char_name, char in chars.items():
            for i, activity in enumerate(char.history):
                if activity.get("status") == "pending":
                    pending_found = True
                    with st.expander(f"{char_name} - {activity['type']} ({activity['date'][:16]})"):
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            img_path = activity.get("proof_image")
                            if img_path and os.path.exists(img_path):
                                st.image(img_path, caption="Kanıt")
                            else:
                                st.warning("Dosya bulunamadı veya silinmiş.")
                        with col_info:
                            st.write(f"**Açıklama:** {activity['description']}")
                            
                            # Eğer Extra görev ise Puanlama Arayüzü Göster
                            # Tüm Görevler İçin Puanlama Arayüzü (Esnek Ödül Sistemi)
                            st.markdown("### 🎓 Puanlama & Onay")
                            
                            # Mevcut ödülleri varsayılan değer olarak al
                            default_xp = int(activity.get('xp_reward', 0))
                            stats = activity.get('stat_rewards', {})
                            default_str = int(stats.get('STR', 0))
                            default_agi = int(stats.get('AGI', 0))
                            default_vit = int(stats.get('VIT', 0))
                            default_wis = int(stats.get('WIS', 0))

                            c_xp, c_str, c_agi = st.columns(3)
                            grade_xp = c_xp.number_input("XP Ödülü", min_value=0, value=default_xp, step=5, key=f"xp_{activity['id']}_{i}")
                            grade_str = c_str.number_input("STR", min_value=0, value=default_str, key=f"str_{activity['id']}_{i}")
                            grade_agi = c_agi.number_input("AGI", min_value=0, value=default_agi, key=f"agi_{activity['id']}_{i}")
                            
                            c_vit, c_wis, c_btn = st.columns(3)
                            grade_vit = c_vit.number_input("VIT", min_value=0, value=default_vit, key=f"vit_{activity['id']}_{i}")
                            grade_wis = c_wis.number_input("WIS", min_value=0, value=default_wis, key=f"wis_{activity['id']}_{i}")
                            
                            with c_btn:
                                st.write("") # Spacer
                                st.write("")
                                # Butonları yan yana koymak için alt kolonlar
                                b_col1, b_col2 = st.columns(2)
                                with b_col1:
                                    if st.button("✅ Onayla", key=f"grade_{activity['id']}_{i}", use_container_width=True):
                                        # Değerleri güncelle
                                        activity['xp_reward'] = grade_xp
                                        activity['stat_rewards'] = {
                                            "STR": grade_str,
                                            "AGI": grade_agi,
                                            "VIT": grade_vit,
                                            "WIS": grade_wis
                                        }
                                        # Onayla
                                        char.approve_activity(activity['id'])
                                        GameSystem.save_character(char)
                                        st.success(f"Onaylandı! {grade_xp} XP verildi.")
                                        st.rerun()
                                with b_col2:
                                    if st.button("❌ Reddet", key=f"rej_{activity['id']}_{i}", use_container_width=True):
                                        char.reject_activity(activity['id'])
                                        GameSystem.save_character(char)
                                        st.error("Reddedildi.")
                                        st.rerun()
                            
                            # Teselli / Hediye Bölümü
                            with st.expander("🎁 Teselli / Hediye Gönder"):
                                gift_msg = st.text_input("Mesaj", "Çaban yeterli! Bir dahakine yaparsın.", key=f"msg_{activity['id']}_{i}")
                                gift_xp = st.number_input("Hediye XP", min_value=1, value=25, key=f"xp_gift_{activity['id']}_{i}")
                                
                                if st.button("Reddet & Hediye Gönder", key=f"gift_{activity['id']}_{i}"):
                                    # 1. Orijinal aktiviteyi reddet
                                    char.reject_activity(activity['id'])
                                    # 2. Hediye aktivitesi ekle (Otomatik onaylı)
                                    char.log_activity("Gift", f"🎁 Öğretmen Hediyesi: {gift_msg}", gift_xp)
                                    GameSystem.save_character(char)
                                    st.success("Hediye gönderildi!")
                                    st.rerun()
        if not pending_found:
            st.info("Bekleyen onay yok.")

def onboarding_view():
    # Compact Header with Icon on top (Zoomed out for mobile view)
    st.markdown("""
        <div style='zoom: 0.6; text-align: center; margin-top: -20px; margin-bottom: 20px;'>
            <div style='font-size: 40px;'>⚔️</div>
            <h3 style='margin:0; padding:0;'>Fitness RPG'ye Hoşgeldiniz</h3>
            <p style='font-size: 14px; color: gray; margin:0;'>Macerana başlamak için giriş yap veya katıl.</p>
        </div>
    """, unsafe_allow_html=True)

    # Wrap the rest of the content (columns) in a zoomed div equivalent
    st.markdown("""
        <style>
            div[data-testid="column"] {
                zoom: 0.60;
            }
        </style>
    """, unsafe_allow_html=True)

    # Columns: Login (Left/Top) - Register (Right/Bottom)
    col_login, col_register = st.columns(2)
    
    with col_login:
        st.markdown("##### 🔓 Giriş Yap")
        with st.form("login_form"):
            existing_name = st.text_input("Kahraman Adı", placeholder="Adınız")
            existing_password = st.text_input("Şifre", type="password", placeholder="****")
            login_submitted = st.form_submit_button("Giriş", use_container_width=True)
            
            if login_submitted:
                success, msg = load_user(existing_name, existing_password)
                if success:
                    st.session_state.current_user = GameSystem.load_characters().get(existing_name)
                    st.success(f"{msg} - Hoşgeldin!")
                    st.rerun()
                else:
                    st.error(msg)
    
    with col_register:
        st.markdown("##### 🛡️ Maceraya Katıl")
        with st.form("new_char_form"):
            name = st.text_input("Kahraman Adı", placeholder="Yeni İsim")
            email = st.text_input("E-Posta Adresi", placeholder="ornek@email.com")
            password = st.text_input("Şifre Belirle", type="password", placeholder="****")
            
            # Cinsiyet Seçimi (Sınıf gizlendi)
            gender = st.radio("Cinsiyet", ["Erkek", "Kadın"], horizontal=True)
            
            submitted = st.form_submit_button("Başla", use_container_width=True)
            if submitted:
                if name and password:
                    chars = GameSystem.load_characters()
                    if name in chars:
                        st.warning("Bu isim zaten alındı!")
                    else:
                        # Varsayılan Sınıf: Savaşçı (Sistemin çalışması için gerekli)
                        char_class = "Savaşçı" 
                        
                        gender_map = {"Erkek": "male", "Kadın": "female"}
                        slug_gender = gender_map.get(gender, "male")
                        
                        # Avatar ID: warrior_male veya warrior_female
                        final_avatar_id = f"warrior_{slug_gender}"
                        
                        create_user(name, char_class, password, email, final_avatar_id)
                        st.rerun()
                else:
                    st.error("Lütfen tüm alanları doldurun.")

    # Admin Login at the very bottom
    st.write("")
    with st.expander("👨‍🏫 Eğitmen Girişi"):
        admin_pass = st.text_input("Yönetici Şifresi", type="password")
        if st.button("Yönetici Giriş"):
            if admin_pass == "admin123":
                st.session_state.current_user = "ADMIN"
                st.rerun()
            else:
                st.error("Hatalı Şifre")


def dashboard_view():
    char = st.session_state.current_user
    
    # Global Dashboard CSS for compact mobile spacing
    st.markdown("""
        <style>
            /* Headers reset */
            h1, h2, h3, h4, h5, p { margin: 0px !important; padding: 0px !important; }
            /* Force horizontal layout on mobile for specific containers */
            [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                align-items: center !important;
            }
            /* Hide scrollbars */
            ::-webkit-scrollbar { width: 0px; height: 0px; }
            
            /* Compact Columns */
            div[data-testid="column"] { min-width: 0px !important; flex: 1 1 0px !important; }
            
            /* Logout Button Style (High Contrast / Universal) */
            .logout-btn {
                background-color: #ffffff;
                color: #31333F !important; /* Dark text for visibility on white */
                text-decoration: none;
                font-size: 13px;
                padding: 3px 10px;
                border-radius: 4px;
                border: 1px solid #d6d6d8;
                display: inline-block;
                line-height: 1.4;
                transition: all 0.2s;
                font-weight: 500;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .logout-btn:hover {
                border-color: #ff4b4b;
                color: #ff4b4b !important;
                background-color: #f0f2f6;
            }
        </style>
        <div style='zoom: 0.60;'> <!-- Global Zoom -->
    """, unsafe_allow_html=True)
    
    # --- Flex Header Row ---
    
    # Hesaplamalar
    xp_next = char.level * 1000
    xp_pct = min(100, int((char.xp / xp_next) * 100))
    
    # HTML Header
    # Avatar & Identity
    avatar_path = char.get_avatar_image()
    
    # HTML Header with embedded image
    import base64
    def get_img_base64(path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return "" # Fallback logic needed if wanted

    img_b64 = get_img_base64(avatar_path)
    # If image not found locally, use a generic placeholder or the old dicebear logic if desired.
    img_src = f"data:image/png;base64,{img_b64}" if img_b64 else "https://api.dicebear.com/7.x/adventurer/svg?seed=" + char.name

    st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: space-between; background: #fff; padding: 12px 16px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; flex-wrap: wrap; gap: 15px; border: 1px solid #f0f0f0;">
<!-- SOL: İsim ve Bilgi -->
<div style="display: flex; align-items: center; gap: 15px;">
    {f'<img src="{img_src}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;">' if img_b64 else ''}
<div style="line-height: 1.4;">
<div style="font-weight: 800; font-size: 22px; color: #1f2937; letter-spacing: -0.5px;">{char.name}</div>
<div style="font-size: 13px; color: #6b7280; font-weight: 500; display: flex; align-items: center; gap: 6px;">
<span style="background:#eef2ff; color:#4f46e5; padding: 2px 8px; border-radius: 6px; font-weight:600;">Lvl {char.level}</span>
<span>{char.char_class}</span>
</div>
</div>
</div>
<!-- SAĞ: Çıkış Butonu -->
<div>
<a href="?logout=true" target="_self" class="logout-btn" style="padding: 8px 18px; font-size: 14px; border: 1px solid #fee2e2; color: #dc2626 !important; background: linear-gradient(to bottom, #fff, #fef2f2); border-radius: 8px; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05); white-space: nowrap;">Çıkış</a>
</div>
</div>
<!-- XP Bar (Kırmızı - İstenilen Stil) -->
<div style="margin-bottom: 25px; padding: 0 5px;">
<div style="display: flex; justify-content: space-between; font-size: 12px; color: #4b5563; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
<span>XP İlerlemesi</span>
<span>{char.xp} / {xp_next} XP (%{xp_pct})</span>
</div>
<div style="width: 100%; height: 14px; background-color: #e5e7eb; border-radius: 10px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.06);">
<div style="width: {xp_pct}%; height: 100%; background: linear-gradient(90deg, #ef4444, #b91c1c); border-radius: 10px; transition: width 0.6s ease-out; box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);"></div>
</div>
<!-- Stats Row (Small Text) -->
<div style="display: flex; gap: 15px; font-size: 11px; color: #6b7280; font-weight: 600; margin-top: 8px; justify-content: flex-end;">
    <span>💪 STR: {char.stats.get('STR', 0)}</span>
    <span>💨 AGI: {char.stats.get('AGI', 0)}</span>
    <span>❤️ VIT: {char.stats.get('VIT', 0)}</span>
    <span>🧙‍♂️ WIS: {char.stats.get('WIS', 0)}</span>
</div>
</div>
""", unsafe_allow_html=True)

    # Hidden logical logout check
    query_params = st.query_params
    if "logout" in query_params:
        st.session_state.current_user = None
        st.query_params.clear()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True) # Close zoom div
    
    # --- Task Board ---
    
    st.markdown("<div style='zoom: 0.9;'>", unsafe_allow_html=True)
    # Tabs...
        
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Günlük", "Antrenman", "Beslenme", "Boss Savaşı", "✨ Extra"])
    
    with tab1:
        st.subheader("Günlük Görevler")
        
        # Vertical Layout: Water First
        with st.container(border=True):
            st.markdown("##### 💧 Su Tüketimi")
            st.caption("Su hayattır! Hedefini seç.")
            
            water_tiers = {
                "250ml - Başlangıç Yudumu": {"xp": 5, "vit": 1},
                "500ml - Sabah İksiri": {"xp": 10, "vit": 2},
                "750ml - Doğa Pınarı": {"xp": 15, "vit": 3},
                "1 LT - Su Matarası": {"xp": 25, "vit": 5},
                "2 LT - Nehir Ruhu": {"xp": 50, "vit": 10},
                "3 LT - Okyanus Efendisi": {"xp": 100, "vit": 20},
            }
            
            w_selection = st.selectbox("Miktar Seç", list(water_tiers.keys()))
            w_data = water_tiers[w_selection]
            st.info(f"🎁 **Ödül:** {w_data['xp']} XP, +{w_data['vit']} VIT")
            
            with st.form("water_form"):
                if st.form_submit_button("İçtim!"):
                    with st.spinner(get_rpg_loading_msg()):
                        desc_text = f"Su Tüketimi: {w_selection}"
                        char.log_activity("Hydration", desc_text, w_data['xp'], {"VIT": w_data['vit']})
                        save_current_user()
                        st.toast(f"Yarasın! {w_selection} içildi. 💧", icon="✅")
                        st.success(f"Yarasın! +{w_data['xp']} XP, +{w_data['vit']} VIT")
                        time.sleep(1)
                        st.rerun()

        # Vertical Layout: Steps Second
        with st.container(border=True):
            st.markdown("##### 🚶 Adım Görevleri")
            st.caption("Yürümek keşfetmektir!")
            
            walk_tiers = {
                "7k Adım - Devriye Gezintisi": {"xp": 30, "agi": 5},
                "10k Adım - Hazine Avı": {"xp": 50, "agi": 10},
                "15k Adım - Efsanevi Yolculuk": {"xp": 100, "agi": 15},
            }
            
            walk_selection = st.selectbox("Hedef Seç", list(walk_tiers.keys()))
            walk_data = walk_tiers[walk_selection]
            st.info(f"🎁 **Ödül:** {walk_data['xp']} XP, +{walk_data['agi']} AGI")
            st.caption("💡 **İpucu:** Fotoğraf yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.")
            
            with st.form("walk_form"):
                walk_proof = st.file_uploader("Adım Sayar (Opsiyonel - Extra Puan İçin)", type=["jpg", "png"], key="walk_proof")
                
                if st.form_submit_button("Tamamladım"):
                    with st.spinner(get_rpg_loading_msg()):
                        image_path = None
                        if walk_proof:
                            if not os.path.exists("uploads"):
                                os.makedirs("uploads")
                            image_path = os.path.join("uploads", walk_proof.name)
                            with open(image_path, "wb") as f:
                                f.write(walk_proof.getbuffer())
                        
                        desc_text = f"Yürüyüş: {walk_selection}"
                        
                        char.log_activity("Cardio", desc_text, walk_data['xp'], {"AGI": walk_data['agi']}, proof_image=image_path)
                        save_current_user()
                        
                        if image_path:
                            st.toast("Kanıtlı yürüyüş gönderildi! Hoca puanlayacak. 👣", icon="⏳")
                            st.info("Onaya gönderildi! Ekstra puan beklenebilir. ⏳")
                        else:
                             st.toast("Yürüyüş kaydedildi! 👣", icon="✅")
                             st.success(f"Tebrikler! +{walk_data['xp']} XP kazandın.")
                             
                        time.sleep(1)
                        st.rerun()

    with tab5:
        st.subheader("✨ Extra Aktivite")
        st.info("Sınırları zorladın mı? Kendine özel bir başarı mı kazandın? Buradan paylaş, eğitmenin seni ödüllendirsin!")
        st.caption("💡 **İpucu:** Fotoğraf/Video yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.")
        
        with st.form("extra_form"):
            extra_desc = st.text_area("Ne yaptın?", "Örn: 30 gün boyunca her sabah 5'te kalktım. / Yeni bir jonglörlük numarası öğrendim.")
            extra_proof = st.file_uploader("Kanıt Fotoğrafı/Videosu (Opsiyonel)", type=["png", "jpg", "jpeg", "mp4"])
            
            submitted = st.form_submit_button("Gönder")
            if submitted:
                if extra_desc:
                    with st.spinner(get_rpg_loading_msg()):
                        image_path = None
                        if extra_proof:
                            if not os.path.exists("uploads"):
                                os.makedirs("uploads")
                            image_path = os.path.join("uploads", extra_proof.name)
                            with open(image_path, "wb") as f:
                                f.write(extra_proof.getbuffer())
                            
                        char.log_activity("Extra", extra_desc, 0, {}, proof_image=image_path)
                        save_current_user()
                        
                        if image_path:
                            st.toast("Efsanevi hareket kanıtla gönderildi! ✨", icon="🌟")
                            st.success("Harika! Kanıtlı aktivite gönderildi. Eğitmen ekstra puan verebilir! 🌟")
                        else:
                            st.toast("Extra aktivite beyanı alındı! ✨", icon="📝")
                            st.success("Aktivite gönderildi! Eğitmen değerlendirecek.")

                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.error("Lütfen en azından bir açıklama yaz.")

    with tab2:
        st.subheader("Antrenman Kaydı")
        st.info("Yaptığın antrenmanı gir ve güçlen!")
        st.caption("💡 **İpucu:** Fotoğraf yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.")
        
        st.caption("💡 **İpucu:** Fotoğraf yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.")
        
        with st.form("workout_form"):
            # Dinamik antrenman tipleri
            w_type = st.selectbox("Tip", list(WORKOUT_MULTIPLIERS.keys()))
            duration = st.number_input("Süre (Dakika)", min_value=10, value=45, step=5)
            desc = st.text_input("Açıklama", "Örn: Bacak günü, 5km koşu...")
            proof_file = st.file_uploader("Kanıt Fotoğrafı Yükle (Opsiyonel)", type=["png", "jpg", "jpeg"])
            
            # Canlı Hesaplama Gösterimi (Form içinde state yenilenmediği için submit sonrası veya dışarıda göstermek lazım ama form içinde static kalır. 
            # Kullanıcıya bilgi vermek için st.info statik kalabilir veya form dışına alabiliriz. 
            # Form kısıtlaması nedeniyle şimdilik form içine bilgi notu ekleyelim ama dinamik olmayabilir.)
            # Streamlit formlarında submit olmadan değer değişince rerun olmaz. O yüzden tahmini değerleri sabit gösteriyoruz.
            
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                with st.spinner(get_rpg_loading_msg()):
                    # Merkezi hesaplama
                    xp_reward, stat_reward = Character.calculate_workout_rewards(w_type, duration)
                    
                    # Save Image
                    image_path = None
                    if proof_file:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", proof_file.name)
                        with open(image_path, "wb") as f:
                            f.write(proof_file.getbuffer())

                    # Activity Log
                    act_type = w_type.split(" ")[0] # "Ağırlık", "Kardiyo" vs.
                    char.log_activity(act_type, f"{desc} ({duration} dk)", xp_reward, stat_reward, proof_image=image_path)
                    save_current_user()
                    
                    if proof_file:
                        st.toast("Antrenman onaya gönderildi! Hocan puanlayacak. 💪", icon="⏳")
                        st.info("Aktivite onaya gönderildi! Ekstra puan şansı. ⏳")
                    else:
                        st.toast(f"Antrenman kaydedildi! +{xp_reward} XP 🔥", icon="✅")
                        st.success(f"Harika iş! +{xp_reward} XP ve statlarını geliştirdin.")
                        
                    time.sleep(1.5)
                    st.rerun()

    with tab3:
        st.subheader("🍎 Sağlıklı Beslenme")
        st.info("Sağlıklı bir öğün tüket, **+150 XP** ve **+5 VIT** kazan!")
        st.caption("💡 **İpucu:** Fotoğraf yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.")
        
        with st.form("nutrition_form"):
            meal_type = st.selectbox("Öğün", ["Kahvaltı", "Öğle Yemeği", "Akşam Yemeği", "Ara Öğün"])
            meal_desc = st.text_input("Menü", "Örn: Izgara Tavuk ve Salata")
            meal_proof = st.file_uploader("Öğün Fotoğrafı (Opsiyonel)", type=["png", "jpg", "jpeg"])
            
            meal_submit = st.form_submit_button("Afiyet Olsun")
            
            if meal_submit:
                with st.spinner(get_rpg_loading_msg()):
                    image_path = None
                    if meal_proof:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", meal_proof.name)
                        with open(image_path, "wb") as f:
                            f.write(meal_proof.getbuffer())

                    # Ödül: 150 XP, +5 VIT (Base)
                    char.log_activity("Nutrition", f"{meal_type}: {meal_desc}", 150, {"VIT": 5}, proof_image=image_path)
                    save_current_user()
                    
                    if image_path:
                        st.toast("Afiyet olsun! Fotoğraflı öğün onaya gitti. 🥗", icon="⏳")
                        st.info("Fotoğraf yüklendi. Hoca ekstra puan verebilir! ⏳")
                    else:
                        st.toast("Afiyet olsun! Öğün kaydedildi. 🥗", icon="🍽️")
                        st.success("Öğün işlendi! +5 VIT, +150 XP")

                    time.sleep(1)
                    st.rerun()

    with tab4:
        st.subheader("👹 Boss Savaşı: Titanların Yükselişi")
        st.info("Kilona göre kaderini seç! Haftalık en büyük meydan okuma.")
        
        # Kilo Girişi
        user_weight = st.number_input("Vücut Ağırlığı (kg)", min_value=40, value=70, step=1)
        
        t1_target = int(user_weight * 0.5)
        t2_target = int(user_weight * 1.0)
        t3_target = int(user_weight * 1.5)
        
        boss_options = {
            "Seviye 1: Demir Çırak (0.5x)": {
                "desc": f"Hedef: {t1_target}kg ile Bench/Squat/Deadlift/LatPull",
                "xp": 500, 
                "stats": {"STR": 5, "VIT": 5},
                "target_kg": t1_target
            },
            "Seviye 2: Çelik Muhafız (1.0x)": {
                "desc": f"Hedef: {user_weight}kg ile Bench/Squat/Deadlift/LatPull",
                "xp": 1500, 
                "stats": {"STR": 15, "VIT": 10},
                "target_kg": user_weight
            },
            "Seviye 3: Titanyum Titan (1.5x)": {
                "desc": f"Hedef: {t3_target}kg ile Bench/Squat/Deadlift/LatPull",
                "xp": 3000, 
                "stats": {"STR": 30, "VIT": 20},
                "target_kg": t3_target
            }
        }
        
        selected_boss = st.radio("Zorluk Seç", list(boss_options.keys()))
        boss_data = boss_options[selected_boss]
        
        st.markdown(f"""
        ### 📜 {selected_boss.split(':')[1]}
        **Görev:** {boss_data['desc']}
        
        **Ödüller:**
        - 🌟 **{boss_data['xp']} XP**
        - 💪 **+{boss_data['stats']['STR']} STR**
        - ❤️ **+{boss_data['stats']['VIT']} VIT**
        
        💡 **İpucu:** Video/Fotoğraf yüklersen eğitmeninden **EKSTRA** XP ve Stat ödülleri kazanabilirsin! Yoksa standart ödülü alırsın.
        """)
        
        with st.form("boss_form"):
            boss_desc = st.text_input("Zafer Notu", f"{boss_data['target_kg']}kg başardım!")
            boss_proof = st.file_uploader("Kanıt (Video/Fotoğraf) - Opsiyonel", type=["png", "jpg", "jpeg", "mp4"])
            boss_submit = st.form_submit_button("⚔️ Saldırıya Başla")
            
            if boss_submit:
                with st.spinner(get_rpg_loading_msg()):
                    image_path = None
                    if boss_proof:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", boss_proof.name)
                        with open(image_path, "wb") as f:
                            f.write(boss_proof.getbuffer())

                    # Activity Log
                    activity_text = f"Boss Savaşı: {selected_boss} - {boss_desc}"
                    char.log_activity("BossFight", activity_text, boss_data['xp'], boss_data['stats'], proof_image=image_path)
                    save_current_user()
                    
                    if image_path:
                        st.toast("Kaderin mühürlendi! Kanıtlı zafer yollandı. 👹", icon="⚔️")
                        st.success(f"Saldırı başarılı! Kanıt gönderildi. ({boss_data['xp']} XP)")
                    else:
                        st.toast("Zafer beyanı alındı! 👹", icon="⚔️")
                        st.success(f"Saldırı başarılı! ({boss_data['xp']} XP)")

                    time.sleep(1.5)
                    st.rerun()

    # History Log
    with st.expander("📝 Maceran Günlüğü (Son 5 Aktivite)"):
        if char.history:
            for h in reversed(char.history[-5:]):
                status_icon = "✅"
                if h.get("status") == "pending":
                    status_icon = "⏳"
                elif h.get("status") == "rejected":
                    status_icon = "❌"
                
                xp_text = f"+{h.get('xp_reward', h.get('xp_gained', 0))} XP"
                st.text(f"{status_icon} {h['date'][:16]} - {h['description']} ({xp_text})")
        else:
            st.caption("Henüz bir kayıt yok.")

# --- Main App Logic ---

if st.session_state.current_user == "ADMIN":
    admin_dashboard_view()
elif st.session_state.current_user:
    dashboard_view()
else:
    onboarding_view()
