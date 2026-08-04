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

# --- TASARIM VE RENK DÜZENLEMELERİ (CSS) ---
st.markdown("""
    <style>
    /* Arka Plan Krem Rengi */
    .stApp {
        background-color: #fdfbf7;
    }
    /* Üst Başlık Yeşil */
    .main-title {
        color: #2e7d32 !important;
        text-align: center;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    /* Butonlar: Lacivert Arka Plan, Krem Yazı, Ekranı Ortala */
    .stButton>button {
        background-color: #1b2a4a !important;
        color: #fdfbf7 !important;
        border: none !important;
        border-radius: 10px !important;
        height: 3.2rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        margin-bottom: 0.5rem !important;
    }
    .stButton>button:hover {
        background-color: #142038 !important;
        color: #ffffff !important;
    }
    /* Kırmızı Silme Butonu Stili */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #c62828 !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE YÖNETİMİ ---
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "ana_sayfa"
if "secili_hasta_id" not in st.session_state:
    st.session_state.secili_hasta_id = None

def sayfa_degistir(sayfa_kodu):
    st.session_state.sayfa = sayfa_kodu

# --- 1. ANA SAYFA (YALNIZCA BUTONLAR & YEŞİL BAŞLIK) ---
if st.session_state.sayfa == "ana_sayfa":
    st.markdown("<h1 class='main-title'>Hoş geldiniz.</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Yeni Hasta Kayıt"):
            sayfa_degistir("yeni_hasta")
            st.rerun()
        if st.button("Hasta Listesi"):
            sayfa_degistir("hasta_listesi")
            st.rerun()
        if st.button("Ayarlar"):
            sayfa_degistir("ayarlar")
            st.rerun()

# --- 2. YENİ HASTA KAYIT SAYFASI ---
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
        
        col_tel, col_ara = st.columns([4, 1])
        with col_tel:
            telefon = st.text_input("Telefon Numarası", placeholder="05XXXXXXXXX")
        with col_ara:
            st.write(" ")
            st.write(" ")
            if telefon:
                st.markdown(f'<a href="tel:{telefon}" target="_blank" style="text-decoration:none;"><button type="button" style="background-color:#2e7d32; color:white; border:none; padding:8px 12px; border-radius:5px; cursor:pointer; width:100%;">📞 Ara</button></a>', unsafe_allow_html=True)

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
                    "kayit_tarihi": datetime.datetime.now().isoformat()
                }
                supabase.table("hastalar").insert(hasta_veri).execute()
                st.toast("✅ Hasta Başarıyla Kaydedildi!", icon="🎉")
            else:
                st.error("Lütfen Hasta Adı Soyadı ve Telefon alanlarını doldurun.")

    if st.button("⬅️ Ana Sayfaya Dön"):
        sayfa_degistir("ana_sayfa")
        st.rerun()

# --- 3. HASTA LİSTESİ VE FİLTRELEME ---
elif st.session_state.sayfa == "hasta_listesi":
    st.subheader("📋 Hasta Listesi")
    
    # Arama ve Filtre Paneli
    with st.expander("🔍 Arama ve Filtreleme Seçenekleri"):
        f_isim = st.text_input("Hasta İsmi ile Ara")
        
        st.write("**Tarih Aralığı Seçimi (İsteğe Bağlı):**")
        c1, c2, c3 = st.columns(3)
        f_g1 = c1.number_input("Gün 1", min_value=0, max_value=31, value=0)
        f_a1 = c2.number_input("Ay 1", min_value=0, max_value=12, value=0)
        f_y1 = c3.number_input("Yıl 1", min_value=0, max_value=2099, value=0)
        
        c4, c5, c6 = st.columns(3)
        f_g2 = c4.number_input("Gün 2", min_value=0, max_value=31, value=0)
        f_a2 = c5.number_input("Ay 2", min_value=0, max_value=12, value=0)
        f_y2 = c6.number_input("Yıl 2", min_value=0, max_value=2099, value=0)

        # Ayarlardan gelen İşlem Türleri
        turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
        tur_listesi = ["Tümü"] + [t["tur_adi"] for t in turler_resp] if turler_resp else ["Tümü"]
        f_islem_turu = st.selectbox("Yapılan İşlem Türü Filtresi", tur_listesi)

    # Sıralama Seçenekleri (Sağ Üst)
    col_bos, col_sirala = st.columns([2, 2])
    with col_sirala:
        sirulama_secimi = st.selectbox("Sırala:", ["Kayıt Tarihi (Yeniden Eskiye)", "Alfabetik (A-Z)"])

    # Verileri Çekme ve Filtreleme
    hastalar = supabase.table("hastalar").select("*").execute().data
    
    if hastalar:
        df_hastalar = pd.DataFrame(hastalar)
        
        # İsim Filtresi
        if f_isim:
            df_hastalar = df_hastalar[df_hastalar["ad_soyad"].str.contains(f_isim, case=False, na=False)]

        # Sıralama
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
        st.info("Sistemde henüz kayıtlı hasta bulunmuyor.")

    if st.button("⬅️ Ana Sayfaya Dön"):
        sayfa_degistir("ana_sayfa")
        st.rerun()

# --- 3.1 HASTA DETAY SAYFASI ---
elif st.session_state.sayfa == "hasta_detay":
    h_id = st.session_state.secili_hasta_id
    hasta_resp = supabase.table("hastalar").select("*").eq("id", h_id).execute().data
    
    if hasta_resp:
        hasta = hasta_resp[0]
        st.subheader(f"🩺 {hasta['ad_soyad']}")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**Cinsiyet:** {hasta['cinsiyet']}")
            st.write(f"**Doğum Tarihi:** {hasta['dogum_tarihi']}")
            st.write(f"**Telefon:** {hasta['telefon']}")
            st.markdown(f'<a href="tel:{hasta["telefon"]}"><button style="background-color:#2e7d32; color:white; border:none; padding:5px 10px; border-radius:5px;">📞 Hastayı Ara</button></a>', unsafe_allow_html=True)
        with c2:
            if hasta.get("foto_url"):
                st.image(hasta["foto_url"], width=100)
        
        st.write("---")
        
        # Butonlar
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("➕ Yeni İşlem Ekle"):
                sayfa_degistir("yeni_islem")
                st.rerun()
        with col_b2:
            if st.button("🗑️ Hastayı Sil", type="secondary"):
                supabase.table("hastalar").delete().eq("id", h_id).execute()
                st.toast("Hasta başarıyla silindi.")
                sayfa_degistir("hasta_listesi")
                st.rerun()

        st.write("### Yapılan İşlemler Kronolojisi")
        islemler = supabase.table("islemler").select("*").eq("hasta_id", h_id).order("islem_tarihi", desc=True).execute().data
        
        if islemler:
            for isl in islemler:
                with st.expander(f"🗓️ {isl['islem_tarihi'][:10]} - {isl['islem_turu']}"):
                    st.write(f"**Hekim Notu:** {isl['hekim_notu']}")
                    if isl.get("fotograf_url"):
                        st.image(isl["fotograf_url"], use_container_width=True)
                    if st.button("İşlemi Sil", key=f"isl_sil_{isl['id']}", type="secondary"):
                        supabase.table("islemler").delete().eq("id", isl['id']).execute()
                        st.toast("İşlem silindi.")
                        st.rerun()
        else:
            st.info("Bu hastaya ait işlem kaydı yok.")

    if st.button("⬅️ Lista Dön"):
        sayfa_degistir("hasta_listesi")
        st.rerun()

# --- 4. YENİ İŞLEM EKLEME SAYFASI ---
elif st.session_state.sayfa == "yeni_islem":
    st.subheader("💉 Yeni İşlem Ekle")
    h_id = st.session_state.secili_hasta_id
    hasta_resp = supabase.table("hastalar").select("*").eq("id", h_id).execute().data
    
    if hasta_resp:
        hasta = hasta_resp[0]
        st.text_input("Hasta İsmi", value=hasta['ad_soyad'], disabled=True)
        
        islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
        
        turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
        turler = [t["tur_adi"] for t in turler_resp] if turler_resp else ["Dolgu", "Kanal Tedavisi", "Muayene"]
        secilen_tur = st.selectbox("İşlem Türü", turler)
        
        hekim_notu = st.text_area("Hekim Notları")
        
        st.write("📸 **Fotoğraf Ekle (Kamera veya Galeri):**")
        cam_foto = st.camera_input("Kameradan Çek")
        file_foto = st.file_uploader("Galeriden Yükle", type=["jpg", "png", "jpeg"])
        
        if st.button("İşlemi Kaydet"):
            yuklenen = cam_foto if cam_foto else file_foto
            foto_url = None
            if yuklenen:
                dosya_adi = f"i_{int(datetime.datetime.now().timestamp())}.png"
                supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, yuklenen.read())
                foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
            
            islem_data = {
                "hasta_id": h_id,
                "islem_tarihi": islem_tarihi.isoformat(),
                "islem_turu": secilen_tur,
                "hekim_notu": hekim_notu,
                "fotograf_url": foto_url
            }
            supabase.table("islemler").insert(islem_data).execute()
            st.toast("✅ İşlem başarıyla kaydedildi!")

    if st.button("⬅️ Hasta Detayına Dön"):
        sayfa_degistir("hasta_detay")
        st.rerun()

# --- 5. AYARLAR SAYFASI (İŞLEM TÜRLERİ VE EXCEL) ---
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
    st.write("### Excel Veri Yedekleme / Aktarma")
    
    # Excel Dışa Aktar
    if st.button("📊 Tüm Hasta Verilerini Excel Olarak İndir"):
        h_data = supabase.table("hastalar").select("*").execute().data
        if h_data:
            df = pd.DataFrame(h_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Hastalar')
            excel_data = output.getvalue()
            st.download_button(label="📥 İndirmeyi Başlat", data=excel_data, file_name="Hasta_Kayitlari.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    if st.button("⬅️ Ana Sayfaya Dön"):
        sayfa_degistir("ana_sayfa")
        st.rerun()
    
