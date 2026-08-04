import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import io

# --- SUPABASE BAĞLANTISI ---
SUPABASE_URL = "https://zmamzsmfpspenhslskmq.supabase.co"

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_KEY = "BURAYA_SUPABASE_ANON_KEY_DEGERINI_YAZIN"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Diş Hekimi Hasta Takip", 
    page_icon="🦷", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS VE GÖRSEL TASARIM (DİŞ FİGÜRLERİ & RENK PALETİ) ---
st.markdown("""
    <style>
    /* Arka Plan Krem ve Diş Desenleri */
    .stApp {
        background-color: #fdfbf7;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="%231b2a4a" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.05"><path d="M12 2C8 2 6 5 6 8c0 3 1 6 2 9 1 2 1 4 2 5 1 0 1-2 2-4 1 2 1 4 2 4 1-1 1-3 2-5 1-3 2-6 2-9 0-3-2-6-6-6z"/></svg>');
        color: #000000;
    }
    
    /* Başlıklar ve Metinler */
    h1, h2, h3, h4, label, .stMarkdown {
        color: #1b2a4a !important;
    }

    /* Genel Buton Tasarımları (Lacivert Arka Plan, Krem Yazı) */
    .stButton>button {
        background-color: #1b2a4a !important;
        color: #fdfbf7 !important;
        border: 1px solid #1b2a4a !important;
        border-radius: 8px !important;
        height: 3rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #0d172a !important;
        color: #ffffff !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* Kırmızı Silme Butonları Özel Stili */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #c62828 !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* Form Elemanları */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE BAŞLATMA ---
if "user" not in st.session_state:
    st.session_state.user = None
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "ana_sayfa"
if "secili_hasta_id" not in st.session_state:
    st.session_state.secili_hasta_id = None
if "gecici_fotolar" not in st.session_state:
    st.session_state.gecici_fotolar = []
if "liste_acik" not in st.session_state:
    st.session_state.liste_acik = False

def sayfa_degistir(sayfa_kodu):
    st.session_state.sayfa = sayfa_kodu

# --- GİRİŞ & KAYIT EKRANI ---
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>🦷 Diş Hekimi Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #1b2a4a;'>Lütfen devam etmek için giriş yapın veya kayıt olun.</p>", unsafe_allow_html=True)
    
    tab_login, tab_register = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
    
    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("E-Posta Adresi")
            login_pass = st.text_input("Şifre", type="password")
            btn_login = st.form_submit_button("Giriş Yap")
            
            if btn_login:
                try:
                    res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                    st.session_state.user = res.user
                    st.toast("✅ Giriş başarılı!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Giriş Başarısız: {e}")
                    
    with tab_register:
        with st.form("register_form"):
            reg_name = st.text_input("İsim Soyisim")
            reg_email = st.text_input("E-Posta Adresi")
            reg_pass = st.text_input("Şifre", type="password")
            btn_register = st.form_submit_button("Kayıt Ol")
            
            if btn_register:
                if reg_name and reg_email and reg_pass:
                    try:
                        res = supabase.auth.sign_up({
                            "email": reg_email,
                            "password": reg_pass,
                            "options": {
                                "data": {
                                    "full_name": reg_name
                                }
                            }
                        })
                        st.success("✅ Kayıt başarılı! Şimdi 'Giriş Yap' sekmesinden giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Kayıt Başarısız: {e}")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")
                    
    st.stop() # Giriş yapılmadıysa uygulamanın geri kalanını yükleme

# --- OTURUM AÇILDIĞINDA ÜST KISIM (HOŞ GELDİNİZ VE ÇIKIŞ) ---
user_fullname = st.session_state.user.user_metadata.get("full_name", "Hekim")
user_id = st.session_state.user.id

col_welcome, col_logout = st.columns([3, 1])
with col_welcome:
    st.markdown(f"### 👋 Hoş geldiniz, **{user_fullname}**")
with col_logout:
    if st.button("🚪 Çıkış Yap", key="btn_logout", type="secondary"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.sayfa = "ana_sayfa"
        st.rerun()

# --- HER EKRANDA ANA SAYFAYA DÖN BUTONU ---
if st.session_state.sayfa != "ana_sayfa":
    if st.button("🏠 Ana Sayfaya Dön", key="btn_ana_sayfa_ust"):
        sayfa_degistir("ana_sayfa")
        st.rerun()

st.write("---")

# --- 1. ANA SAYFA ---
if st.session_state.sayfa == "ana_sayfa":
    st.markdown("<h2 style='text-align: center;'>🦷 Klinik Yönetim Paneli</h2>", unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True)
    
    # Yanal Yönde Ortalanmış Butonlar
    c_left, c_center, c_right = st.columns([1, 2, 1])
    with c_center:
        if st.button("➕ Yeni İşlem / Hasta Kaydı"):
            sayfa_degistir("yeni_islem_ana")
            st.rerun()
            
        if st.button("👤 Yeni Hasta Kayıt"):
            sayfa_degistir("yeni_hasta")
            st.rerun()
            
        if st.button("📋 Hasta Listesi"):
            sayfa_degistir("hasta_listesi")
            st.rerun()
            
        if st.button("⚙️ Ayarlar"):
            sayfa_degistir("ayarlar")
            st.rerun()

# --- 2. YENİ İŞLEM SAYFASI ---
elif st.session_state.sayfa == "yeni_islem_ana":
    st.subheader("💉 Yeni İşlem Ekle")
    
    # Sadece Giriş Yapan Kullanıcının Hastalarını Getir
    hastalar = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).order("ad_soyad").execute().data
    hasta_opsiyonlari = {"Yeni Hasta Oluştur": "YENI"}
    if hastalar:
        for h in hastalar:
            hasta_opsiyonlari[f"{h['ad_soyad']} ({h['telefon']})"] = h['id']
            
    secilen_hasta_label = st.selectbox("Hasta Seçin", list(hasta_opsiyonlari.keys()))
    secilen_hasta_id = hasta_opsiyonlari[secilen_hasta_label]
    
    yeni_ad, yeni_tel = "", ""
    if secilen_hasta_id == "YENI":
        c_a1, c_a2 = st.columns(2)
        yeni_ad = c_a1.text_input("Hasta Adı Soyadı")
        yeni_tel = c_a2.text_input("Telefon Numarası")

    islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
    
    turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
    turler = [t["tur_adi"] for t in turler_resp] if turler_resp else ["Dolgu", "Kanal Tedavisi", "Muayene", "Çekim"]
    secilen_tur = st.selectbox("Yapılan İşlem", turler)
    
    hekim_notu = st.text_area("Hekim Notları")
    
    st.write("---")
    st.write("📸 **Fotoğraf Ekle:**")
    
    col_cam, col_file = st.columns(2)
    with col_cam:
        cam_foto = st.camera_input("Kameradan Çek")
        if cam_foto and cam_foto not in st.session_state.gecici_fotolar:
            st.session_state.gecici_fotolar.append(cam_foto)
    with col_file:
        file_fotolar = st.file_uploader("Galeriden Seç (Çoklu)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if file_fotolar:
            for ff in file_fotolar:
                if ff not in st.session_state.gecici_fotolar:
                    st.session_state.gecici_fotolar.append(ff)

    if st.session_state.gecici_fotolar:
        st.write("**Eklenecek Fotoğraflar:**")
        cols = st.columns(3)
        for idx, foto in enumerate(st.session_state.gecici_fotolar):
            with cols[idx % 3]:
                st.image(foto, width=100)
                if st.button("Sil", key=f"f_sil_{idx}", type="secondary"):
                    st.session_state.gecici_fotolar.pop(idx)
                    st.rerun()

    if st.button("💾 İşlemi Kaydet"):
        final_hasta_id = secilen_hasta_id
        
        if secilen_hasta_id == "YENI":
            if yeni_ad and yeni_tel:
                h_res = supabase.table("hastalar").insert({
                    "ad_soyad": yeni_ad,
                    "telefon": yeni_tel,
                    "kullanici_id": user_id,
                    "kayit_tarihi": datetime.datetime.now().isoformat()
                }).execute()
                final_hasta_id = h_res.data[0]["id"]
            else:
                st.error("Lütfen Ad Soyad ve Telefon alanlarını doldurun.")
                st.stop()
                
        foto_url_listesi = []
        for foto in st.session_state.gecici_fotolar:
            dosya_adi = f"proc_{int(datetime.datetime.now().timestamp())}_{user_id[:5]}.png"
            supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.read())
            url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
            foto_url_listesi.append(url)

        islem_data = {
            "hasta_id": final_hasta_id,
            "kullanici_id": user_id,
            "islem_tarihi": islem_tarihi.isoformat(),
            "islem_turu": secilen_tur,
            "hekim_notu": hekim_notu,
            "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None
        }
        supabase.table("islemler").insert(islem_data).execute()
        
        st.toast("✅ İşlem kaydedildi!")
        st.session_state.gecici_fotolar = []
        st.rerun()

# --- 3. YENİ HASTA KAYIT SAYFASI ---
elif st.session_state.sayfa == "yeni_hasta":
    st.subheader("👤 Yeni Hasta Kaydı")
    
    with st.form("yeni_hasta_formu", clear_on_submit=True):
        col_sol, col_sag = st.columns([3, 1])
        with col_sol:
            ad_soyad = st.text_input("Hasta Adı Soyadı")
            cinsiyet = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Diğer"])
            dogum_tarihi = st.date_input("Doğum Tarihi", datetime.date(1990, 1, 1))
        with col_sag:
            st.write("Profil Resmi")
            profil_foto = st.file_uploader("Seç", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
            
        telefon = st.text_input("Telefon Numarası", placeholder="05XXXXXXXXX")
        kaydet = st.form_submit_button("Hastayı Kaydet")
        
        if kaydet:
            if ad_soyad and telefon:
                foto_url = None
                if profil_foto:
                    dosya_adi = f"p_{int(datetime.datetime.now().timestamp())}.png"
                    supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, profil_foto.read())
                    foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                hasta_veri = {
                    "ad_soyad": ad_soyad,
                    "cinsiyet": cinsiyet,
                    "dogum_tarihi": dogum_tarihi.isoformat(),
                    "telefon": telefon,
                    "foto_url": foto_url,
                    "kullanici_id": user_id,
                    "kayit_tarihi": datetime.datetime.now().isoformat()
                }
                supabase.table("hastalar").insert(hasta_veri).execute()
                st.toast("✅ Hasta Başarıyla Kaydedildi!")
            else:
                st.error("Lütfen Hasta Adı Soyadı ve Telefon alanlarını doldurun.")

# --- 4. HASTA LİSTESİ VE FİLTRELEME SAYFASI ---
elif st.session_state.sayfa == "hasta_listesi":
    st.subheader("📋 Hasta Listesi")
    
    f_isim = st.text_input("Hasta İsmi ile Arama")
    
    st.write("**Tarih Seçimi / Aralığı:**")
    col_g1, col_a1, col_y1 = st.columns(3)
    f_g1 = col_g1.selectbox("Gün (1)", [0] + list(range(1, 32)))
    f_a1 = col_a1.selectbox("Ay (1)", [0] + list(range(1, 13)))
    f_y1 = col_y1.number_input("Yıl (1)", min_value=0, max_value=2099, value=0)

    col_g2, col_a2, col_y2 = st.columns(3)
    f_g2 = col_g2.selectbox("Gün (2)", [0] + list(range(1, 32)))
    f_a2 = col_a2.selectbox("Ay (2)", [0] + list(range(1, 13)))
    f_y2 = col_y2.number_input("Yıl (2)", min_value=0, max_value=2099, value=0)

    turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
    tur_listesi = ["Tümü"] + [t["tur_adi"] for t in turler_resp] if turler_resp else ["Tümü"]
    f_islem_turu = st.selectbox("İşlem Türü Filtresi", tur_listesi)

    st.write("---")

    c_btn, c_sort = st.columns([2, 2])
    with c_btn:
        if st.button("📋 Hastaları Listele / Kapat"):
            st.session_state.liste_acik = not st.session_state.liste_acik
            
    with c_sort:
        sirulama_secimi = st.selectbox("Sıralama Seçeneği", ["Kayıt Tarihi (Yeni > Eski)", "Alfabetik (A-Z)"])

    if st.session_state.liste_acik:
        # Sadece bu kullanıcının hastalarını çek
        hastalar = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).execute().data
        
        if hastalar:
            df_hastalar = pd.DataFrame(hastalar)
            
            if f_isim:
                df_hastalar = df_hastalar[df_hastalar["ad_soyad"].str.contains(f_isim, case=False, na=False)]

            if f_islem_turu != "Tümü":
                islem_hastalar = supabase.table("islemler").select("hasta_id").eq("islem_turu", f_islem_turu).eq("kullanici_id", user_id).execute().data
                uygun_ids = [i["hasta_id"] for i in islem_hastalar]
                df_hastalar = df_hastalar[df_hastalar["id"].isin(uygun_ids)]

            if sirulama_secimi == "Alfabetik (A-Z)":
                df_hastalar = df_hastalar.sort_values(by="ad_soyad")
            else:
                df_hastalar = df_hastalar.sort_values(by="kayit_tarihi", ascending=False)

            st.write("---")
            for _, h in df_hastalar.iterrows():
                col_h1, col_h2 = st.columns([4, 1])
                with col_h1:
                    st.write(f"**{h['ad_soyad']}** - Tel: {h['telefon']}")
                with col_h2:
                    if st.button("Detay ➡️", key=f"detay_{h['id']}"):
                        st.session_state.secili_hasta_id = h['id']
                        sayfa_degistir("hasta_detay")
                        st.rerun()
        else:
            st.info("Kayıtlı hastanız bulunamadı.")

# --- 4.1 HASTA DETAY SAYFASI ---
elif st.session_state.sayfa == "hasta_detay":
    h_id = st.session_state.secili_hasta_id
    hasta_resp = supabase.table("hastalar").select("*").eq("id", h_id).eq("kullanici_id", user_id).execute().data
    
    if hasta_resp:
        hasta = hasta_resp[0]
        st.subheader(f"🩺 {hasta['ad_soyad']}")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**Cinsiyet:** {hasta.get('cinsiyet', 'Belirtilmemiş')}")
            st.write(f"**Doğum Tarihi:** {hasta.get('dogum_tarihi', '-')}")
            st.write(f"**Telefon:** {hasta['telefon']}")
            st.markdown(f'<a href="tel:{hasta["telefon"]}"><button style="background-color:#1b2a4a; color:#fdfbf7; border:none; padding:8px 12px; border-radius:5px; width:100%;">📞 Hastayı Ara</button></a>', unsafe_allow_html=True)
        with c2:
            if hasta.get("foto_url"):
                st.image(hasta["foto_url"], width=100)
        
        st.write("---")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("➕ Bu Hastaya İşlem Ekle"):
                sayfa_degistir("yeni_islem_ana")
                st.rerun()
        with col_b2:
            if st.button("🗑️ Hastayı Sil", type="secondary"):
                supabase.table("hastalar").delete().eq("id", h_id).execute()
                st.toast("Hasta silindi.")
                sayfa_degistir("hasta_listesi")
                st.rerun()

        st.write("### Yapılan İşlemler Kronolojisi")
        islemler = supabase.table("islemler").select("*").eq("hasta_id", h_id).eq("kullanici_id", user_id).order("islem_tarihi", desc=True).execute().data
        
        if islemler:
            for isl in islemler:
                with st.expander(f"🗓️ {isl['islem_tarihi']} - {isl['islem_turu']}"):
                    st.write(f"**Hekim Notu:** {isl['hekim_notu']}")
                    if isl.get("fotograf_url"):
                        urls = isl["fotograf_url"].split(",")
                        img_cols = st.columns(3)
                        for idx, u in enumerate(urls):
                            with img_cols[idx % 3]:
                                st.image(u, use_container_width=True)
                    if st.button("İşlemi Sil", key=f"isl_sil_{isl['id']}", type="secondary"):
                        supabase.table("islemler").delete().eq("id", isl['id']).execute()
                        st.toast("İşlem silindi.")
                        st.rerun()
        else:
            st.info("İşlem kaydı yok.")

# --- 5. AYARLAR SAYFASI ---
elif st.session_state.sayfa == "ayarlar":
    st.subheader("⚙️ Ayarlar")
    
    st.write("### İşlem Türü Yönetimi")
    yeni_tur = st.text_input("Yeni İşlem Türü Adı")
    if st.button("Ekle"):
        if yeni_tur:
            supabase.table("islem_turleri").insert({"tur_adi": yeni_tur}).execute()
            st.toast("İşlem türü eklendi.")
            st.rerun()
            
    turler = supabase.table("islem_turleri").select("*").execute().data
    if turler:
        for t in turler:
            c_t1, c_t2 = st.columns([3, 1])
            c_t1.write(t["tur_adi"])
            if c_t2.button("Sil", key=f"tur_sil_{t['id']}", type="secondary"):
                supabase.table("islem_turleri").delete().eq("id", t['id']).execute()
                st.toast("İşlem türü silindi.")
                st.rerun()

    st.write("---")
    st.write("### Excel Veri Yedekleme")
    if st.button("📊 Sadece Benim Hastalarımı Excel Olarak İndir"):
        h_data = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).execute().data
        if h_data:
            df = pd.DataFrame(h_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Hastalar')
            excel_data = output.getvalue()
            st.download_button(label="📥 İndirmeyi Başlat", data=excel_data, file_name="Hasta_Kayitlarim.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
