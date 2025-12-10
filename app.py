import streamlit as st
import pandas as pd
import plotly.express as px
from models import Character, GameSystem
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import os

# Page Config
st.set_page_config(page_title="Fitness RPG", page_icon="⚔️", layout="wide")

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

def create_user(name, char_class, password, avatar_id):
    new_char = Character(name, char_class, password, avatar_id)
    GameSystem.save_character(new_char)
    st.session_state.current_user = new_char

def save_current_user():
    if st.session_state.current_user:
        GameSystem.save_character(st.session_state.current_user)

# --- Views ---

def admin_dashboard_view():
    st.title("👨‍🏫 Öğretmen Kontrol Paneli")
    
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
            "Sınıf": char.char_class,
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
    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Öğrenci", len(df))
    m2.metric("Ortalama Seviye", f"{df['Seviye'].mean():.1f}")
    m3.metric("En Popüler Sınıf", df['Sınıf'].mode()[0] if not df.empty else "-")

    # Main Table
    tab_list, tab_approve = st.tabs(["📊 Genel Durum", "📝 Onay Bekleyenler"])

    with tab_list:
        st.dataframe(df, use_container_width=True)

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Sınıf Dağılımı")
            fig_class = px.pie(df, names='Sınıf', title='Sınıf Tercihleri')
            st.plotly_chart(fig_class, use_container_width=True)
        
        with c2:
            st.subheader("Seviye Dağılımı")
            fig_lvl = px.bar(df, x='İsim', y='Seviye', color='Sınıf', title='Öğrenci Seviyeleri')
            st.plotly_chart(fig_lvl, use_container_width=True)

    with tab_approve:
        st.subheader("Onay Bekleyen Aktiviteler")
        pending_found = False
        for char_name, char in chars.items():
            for activity in char.history:
                if activity.get("status") == "pending":
                    pending_found = True
                    with st.expander(f"{char_name} - {activity['type']} ({activity['date'][:16]})"):
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            if activity.get("proof_image"):
                                st.image(activity["proof_image"], caption="Kanıt")
                            else:
                                st.warning("Görsel Yok")
                        with col_info:
                            st.write(f"**Açıklama:** {activity['description']}")
                            
                            # Eğer Extra görev ise Puanlama Arayüzü Göster
                            if activity['type'] == "Extra":
                                st.markdown("### 🎓 Puanlama")
                                c_xp, c_str, c_agi = st.columns(3)
                                grade_xp = c_xp.number_input("XP Ödülü", min_value=0, value=100, step=50, key=f"xp_{activity['id']}")
                                grade_str = c_str.number_input("STR", min_value=0, value=0, key=f"str_{activity['id']}")
                                grade_agi = c_agi.number_input("AGI", min_value=0, value=0, key=f"agi_{activity['id']}")
                                
                                c_vit, c_wis, c_btn = st.columns(3)
                                grade_vit = c_vit.number_input("VIT", min_value=0, value=0, key=f"vit_{activity['id']}")
                                grade_wis = c_wis.number_input("WIS", min_value=0, value=0, key=f"wis_{activity['id']}")
                                
                                with c_btn:
                                    st.write("") # Spacer
                                    st.write("")
                                    if st.button("🌟 Puanla ve Onayla", key=f"grade_{activity['id']}"):
                                        # Değerleri güncelle
                                        activity['xp_reward'] = grade_xp
                                        activity['stat_rewards'] = {
                                            "STR": grade_str,
                                            "AGI": grade_agi,
                                            "VIT": grade_vit,
                                            "WIS": grade_wis
                                        }
                                        # Onayla (Güncellenmiş değerlerle işlenir)
                                        char.approve_activity(activity['id'])
                                        GameSystem.save_character(char)
                                        st.success(f"Puanlandı! {grade_xp} XP verildi.")
                                        st.rerun()

                            else:
                                # Standart Görevler İçin
                                st.write(f"**Ödül:** {activity['xp_reward']} XP")
                                
                                b1, b2 = st.columns(2)
                                with b1:
                                    if st.button("✅ Onayla", key=f"app_{activity['id']}"):
                                        char.approve_activity(activity['id'])
                                        GameSystem.save_character(char)
                                        st.success("Onaylandı!")
                                        st.rerun()
                                with b2:
                                    if st.button("❌ Reddet", key=f"rej_{activity['id']}"):
                                        char.reject_activity(activity['id'])
                                        GameSystem.save_character(char)
                                        st.error("Reddedildi.")
                                        st.rerun()
                            
                            # Teselli / Hediye Bölümü
                            with st.expander("🎁 Teselli / Hediye Gönder"):
                                gift_msg = st.text_input("Mesaj", "Çaban yeterli! Bir dahakine yaparsın.", key=f"msg_{activity['id']}")
                                gift_xp = st.number_input("Hediye XP", min_value=1, value=25, key=f"xp_{activity['id']}")
                                
                                if st.button("Reddet & Hediye Gönder", key=f"gift_{activity['id']}"):
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
    # Compact Header with Icon on top (büyük boşluklar olmadan)
    st.markdown("""
        <div style='text-align: center; margin-top: -20px; margin-bottom: 20px;'>
            <div style='font-size: 40px;'>⚔️</div>
            <h3 style='margin:0; padding:0;'>Fitness RPG'ye Hoşgeldiniz</h3>
            <p style='font-size: 14px; color: gray; margin:0;'>Macerana başlamak için giriş yap veya katıl.</p>
        </div>
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
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    with col_register:
        st.markdown("##### 🛡️ Maceraya Katıl")
        with st.form("new_char_form"):
            name = st.text_input("Kahraman Adı", placeholder="Yeni İsim")
            password = st.text_input("Şifre Belirle", type="password", placeholder="****")
            
            # Compact Class Selection
            c1, c2 = st.columns(2)
            with c1:
                char_class = st.selectbox("Sınıf", ["Savaşçı", "Korucu", "Keşiş"], label_visibility="collapsed")
            with c2:
                gender = st.radio("Cinsiyet", ["Erkek", "Kadın"], horizontal=True, label_visibility="collapsed")
            
            # Class info (Very compact)
            if char_class == "Savaşçı":
                st.caption("⚔️ Güç ve Hipertrofi")
            elif char_class == "Korucu":
                st.caption("🏹 Dayanıklılık ve Esneklik")
            elif char_class == "Keşiş":
                st.caption("🧘 Mobilite ve Zihin")
                
            submitted = st.form_submit_button("Başla", use_container_width=True)
            if submitted:
                if name and password:
                    chars = GameSystem.load_characters()
                    if name in chars:
                        st.warning("Bu isim zaten alındı!")
                    else:
                        class_map = {"Savaşçı": "warrior", "Korucu": "ranger", "Keşiş": "monk"}
                        gender_map = {"Erkek": "male", "Kadın": "female"}
                        slug_class = class_map.get(char_class, "warrior")
                        slug_gender = gender_map.get(gender, "male")
                        final_avatar_id = f"{slug_class}_{slug_gender}"
                        create_user(name, char_class, password, final_avatar_id)
                        st.rerun()
                else:
                    st.error("Eksik bilgi.")

    # Admin Login at the very bottom
    st.write("")
    with st.expander("👨‍🏫 Öğretmen Girişi"):
        admin_pass = st.text_input("Yönetici Şifresi", type="password")
        if st.button("Yönetici Giriş"):
            if admin_pass == "admin123":
                st.session_state.current_user = "ADMIN"
                st.rerun()
            else:
                st.error("Hatalı Şifre")


def dashboard_view():
    char = st.session_state.current_user
    
    # Header
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        # Avatar Görseli (Dinamik)
        avatar_path = char.get_avatar_image()
        if os.path.exists(avatar_path):
            st.image(avatar_path, width=150)
        else:
            # Fallback
            st.image("https://api.dicebear.com/7.x/adventurer/svg?seed=" + char.name, width=100)
    with c2:
        st.title(f"{char.name} - Lvl {char.level} {char.char_class}")
        # XP Bar
        xp_needed = char.level * 1000
        progress = min(char.xp / xp_needed, 1.0)
        st.progress(progress, text=f"XP: {char.xp} / {xp_needed}")
    with c3:
        if st.button("Çıkış Yap"):
            st.session_state.current_user = None
            st.rerun()

    # Main Content
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### 📊 İstatistikler")
        
        # Radar Chart
        stats = char.stats
        df = pd.DataFrame(dict(
            r=list(stats.values()),
            theta=list(stats.keys())
        ))
        fig = px.line_polar(df, r='r', theta='theta', line_close=True)
        fig.update_traces(fill='toself', line_color='#f63366')
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(max(stats.values()) + 10, 20)], showticklabels=False)
            ),
            margin=dict(l=10, r=10, t=10, b=10),
            height=180,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("### 🏆 Başarılar")
        if char.level >= 5:
            st.success("🎖️ Çırak Rozeti")
        if char.level >= 10:
            st.success("🎖️ Usta Rozeti")
        if char.level < 5:
            st.caption("Daha fazla rozet için seviye atla!")

    with col_right:
        st.markdown("### 📜 Görev Panosu")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Günlük", "Antrenman", "Beslenme", "Boss Savaşı", "✨ Extra"])
        
        with tab1:
            st.subheader("Günlük Görevler")
            col_daily1, col_daily2 = st.columns(2)
            
            with col_daily1:
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
                        # Su için fotoğraf istemiyoruz
                        if st.form_submit_button("İçtim!"):
                            # Dynamic Description inside log
                            desc_text = f"Su Tüketimi: {w_selection}"
                            # Kanıt olmadığı için proof_image=None gider, otomatik onaylanır.
                            char.log_activity("Hydration", desc_text, w_data['xp'], {"VIT": w_data['vit']})
                            save_current_user()
                            st.success(f"Yarasın! +{w_data['xp']} XP, +{w_data['vit']} VIT")
                            st.balloons()
                            st.rerun()

            with col_daily2:
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
                    
                    with st.form("walk_form"):
                        walk_proof = st.file_uploader("Adım Sayar", type=["jpg", "png"], key="walk_proof")
                        
                        if st.form_submit_button("Tamamladım"):
                            if walk_proof:
                                if not os.path.exists("uploads"):
                                    os.makedirs("uploads")
                                img_path = os.path.join("uploads", walk_proof.name)
                                with open(img_path, "wb") as f:
                                    f.write(walk_proof.getbuffer())
                                
                                desc_text = f"Yürüyüş: {walk_selection}"
                                char.log_activity("Cardio", desc_text, walk_data['xp'], {"AGI": walk_data['agi']}, proof_image=img_path)
                                save_current_user()
                                st.info("Onaya gönderildi! ⏳")
                                st.rerun()
                            else:
                                st.error("Lütfen fotoğraf yükle!")

        with tab5:
            st.subheader("✨ Extra Aktivite")
            st.info("Sınırları zorladın mı? Kendine özel bir başarı mı kazandın? Buradan paylaş, eğitmenin seni ödüllendirsin!")
            
            with st.form("extra_form"):
                extra_desc = st.text_area("Ne yaptın?", "Örn: 30 gün boyunca her sabah 5'te kalktım. / Yeni bir jonglörlük numarası öğrendim.")
                extra_proof = st.file_uploader("Kanıt Fotoğrafı/Videosu", type=["png", "jpg", "jpeg", "mp4"])
                
                submitted = st.form_submit_button("Gönder")
                if submitted:
                    if extra_desc and extra_proof:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", extra_proof.name)
                        with open(image_path, "wb") as f:
                            f.write(extra_proof.getbuffer())
                            
                        # XP ve Stat ödülleri 0 olarak gönderilir, hoca belirleyecek
                        char.log_activity("Extra", extra_desc, 0, {}, proof_image=image_path)
                        save_current_user()
                        st.success("Harika! Eğitmenine gönderildi. Puanlamasını bekle. 🌟")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Lütfen açıklama yaz ve kanıt yükle.")

        with tab2:
            st.subheader("Antrenman Kaydı")
            st.info("Yaptığın antrenmanı gir ve güçlen!")
            
            with st.form("workout_form"):
                w_type = st.selectbox("Tip", ["Ağırlık (STR)", "Kardiyo (AGI)", "Yoga/Esneme (WIS)", "HIIT (AGI)"])
                duration = st.number_input("Süre (Dakika)", min_value=10, value=45)
                desc = st.text_input("Açıklama", "Örn: Bacak günü, 5km koşu...")
                proof_file = st.file_uploader("Kanıt Fotoğrafı Yükle", type=["png", "jpg", "jpeg"])
                
                submitted = st.form_submit_button("Kaydet")
                if submitted:
                    base_xp = duration * 2 # Basit formül
                    stat_reward = {}
                    
                    if "STR" in w_type:
                        stat_reward["STR"] = 20
                        stat_reward["WIS"] = 5
                        act_type = "Strength"
                    elif "AGI" in w_type:
                        stat_reward["AGI"] = 20
                        stat_reward["WIS"] = 5
                        act_type = "Cardio"
                    elif "WIS" in w_type:
                        stat_reward["WIS"] = 20
                        stat_reward["VIT"] = 5
                        act_type = "Mobility"
                        
                    # Save Image
                    image_path = None
                    if proof_file:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", proof_file.name)
                        with open(image_path, "wb") as f:
                            f.write(proof_file.getbuffer())

                    char.log_activity(act_type, desc, base_xp, stat_reward, proof_image=image_path)
                    save_current_user()
                    
                    if proof_file:
                        st.info("Aktivite onaya gönderildi! ⏳")
                    else:
                        st.success(f"Aktivite kaydedildi! +{base_xp} XP") # Kanıtsızsa direkt onaylı (şimdilik)
                    st.rerun()

        with tab3:
            st.subheader("🍎 Sağlıklı Beslenme")
            st.info("Sağlıklı bir öğün tüket, **+150 XP** ve **+5 VIT** kazan!")
            
            with st.form("nutrition_form"):
                meal_type = st.selectbox("Öğün", ["Kahvaltı", "Öğle Yemeği", "Akşam Yemeği", "Ara Öğün"])
                meal_desc = st.text_input("Menü", "Örn: Izgara Tavuk ve Salata")
                meal_proof = st.file_uploader("Öğün Fotoğrafı", type=["png", "jpg", "jpeg"])
                
                meal_submit = st.form_submit_button("Afiyet Olsun")
                
                if meal_submit:
                    if meal_proof:
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        image_path = os.path.join("uploads", meal_proof.name)
                        with open(image_path, "wb") as f:
                            f.write(meal_proof.getbuffer())

                        # Ödül: 150 XP, +5 VIT
                        char.log_activity("Nutrition", f"{meal_type}: {meal_desc}", 150, {"VIT": 5}, proof_image=image_path)
                        save_current_user()
                        st.info("Öğün onaya gönderildi! +5 VIT, +150 XP (Onaylanınca)")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Lütfen öğünün fotoğrafını yükle!")

        with tab4:
            st.subheader("👹 Boss Savaşı: Titanların Yükselişi")
            st.info("Kilona göre kaderini seç! Haftalık en büyük meydan okuma.")
            
            # Kilo Girişi
            user_weight = st.number_input("Vücut Ağırlığı (kg)", min_value=40, value=70, step=1)
            
            # Hedef Hesaplama
            t1_target = int(user_weight * 0.5)
            t2_target = int(user_weight * 1.0)
            t3_target = int(user_weight * 1.5)
            
            # Boss Seçenekleri
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
            """)
            
            with st.form("boss_form"):
                boss_desc = st.text_input("Zafer Notu", f"{boss_data['target_kg']}kg başardım!")
                boss_proof = st.file_uploader("Kanıt (Video/Fotoğraf)", type=["png", "jpg", "jpeg", "mp4"])
                boss_submit = st.form_submit_button("⚔️ Saldırıya Başla")
                
                if boss_submit:
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
                        
                        st.success(f"Saldırı başarılı! Ödül onaya gönderildi. ({boss_data['xp']} XP)")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Boss savaşı için kanıt yüklemek zorunludur! Hile yok savaşçı!")

    # History Log
    with st.expander("📝 Maceran Günlüğü (Son 5 Aktivite)"):
        if char.history:
            for h in reversed(char.history[-5:]):
                status_icon = "✅"
                if h.get("status") == "pending":
                    status_icon = "⏳"
                elif h.get("status") == "rejected":
                    status_icon = "❌"
                
                xp_text = f"+{h.get('xp_reward', h.get('xp_gained', 0))} XP" # Compatibility with old/new keys
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
