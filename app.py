import streamlit as st
from supabase import create_client, Client
import datetime

# --- SUPABASE BAĞLANTISI ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SAYFA AYARLARI (Mobil Uyumlu) ---
st.set_page_config(
    page_title="Diş Hekimi Hasta Takip", 
    page_icon="🦷", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS İLE MOBİL ARAYÜZ DÜZENLEMESİ ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3.2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sayfa durumu yönetimi
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "yeni_hasta"

# Esnek Menü Yapısı
MENULER = {
    "➕ Yeni Hasta Kayıt": "yeni_hasta",
    "📋 Hasta Listesi": "hasta_listesi",
    "💉 Yeni İşlem": "yeni_islem",
    "⚙️ Ayarlar": "ayarlar"
}

def sayfa_degistir(kod):
    st.session_state.sayfa = kod

# --- BAŞLIK ---
st.title("🦷 Diş Hekimi Hasta Takip")
st.subheader("Hoş geldiniz.")
st.write("---")

# --- MOBİL UYUMLU BUTON MENÜSÜ ---
for etiket, kod in MENULER.items():
    # Aktif sayfayı vurgulamak için buton türünü değiştiriyoruz
    btn_type = "primary" if st.session_state.sayfa == kod else "secondary"
    if st.button(etiket, key=f"btn_{kod}", type=btn_type):
        sayfa_degistir(kod)
        st.rerun()

st.write("---")

# --- SAYFA İÇERİKLERİ ---

# 1. YENİ HASTA KAYIT
if st.session_state.sayfa == "yeni_hasta":
    st.header("👤 Yeni Hasta Kaydı")
    
    with st.form("yeni_hasta_formu", clear_on_submit=True):
        ad = st.text_input("Hasta Adı")
        soyad = st.text_input("Hasta Soyadı")
        cinsiyet = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Diğer"])
        kayit_tarihi = st.date_input("Kayıt Tarihi", datetime.date.today())
        
        submit = st.form_submit_button("Hastayı Kaydet")
        
        if submit:
            if ad and soyad:
                data = {
                    "ad": ad,
                    "soyad": soyad,
                    "cinsiyet": cinsiyet,
                    "kayit_tarihi": kayit_tarihi.isoformat()
                }
                supabase.table("hastalar").insert(data).execute()
                st.success(f"✅ {ad} {soyad} başarıyla kaydedildi!")
            else:
                st.error("Lütfen ad ve soyad alanlarını doldurun.")

# 2. HASTA LİSTESİ VE DETAYI
elif st.session_state.sayfa == "hasta_listesi":
    st.header("📋 Hasta Listesi ve Geçmişi")
    
    hastalar = supabase.table("hastalar").select("*").order("ad").execute().data
    
    if hastalar:
        hasta_opsiyonlari = {f"{h['ad']} {h['soyad']}": h['id'] for h in hastalar}
        secilen_hasta_adi = st.selectbox("Hastayı Seçin:", list(hasta_opsiyonlari.keys()))
        
        secilen_id = hasta_opsiyonlari[secilen_hasta_adi]
        hasta_detay = next(h for h in hastalar if h['id'] == secilen_id)
        
        st.write("---")
        st.markdown(f"### 🩺 **{hasta_detay['ad']} {hasta_detay['soyad']}**")
        st.write(f"**Cinsiyet:** {hasta_detay['cinsiyet']} | **Kayıt:** {hasta_detay['kayit_tarihi'][:10]}")
        
        islemler = supabase.table("islemler").select("*").eq("hasta_id", secilen_id).order("islem_tarihi", desc=True).execute().data
        
        st.subheader("Yapılan İşlemler")
        if islemler:
            for islem in islemler:
                with st.expander(f"🗓️ {islem['islem_tarihi'][:10]} - {islem['yapilan_islem']}"):
                    st.write(f"**Hekim Notu:** {islem['hekim_notu']}")
                    if islem.get("fotograf_url"):
                        st.image(islem["fotograf_url"], caption="İşlem Fotoğrafı", use_container_width=True)
        else:
            st.info("Bu hastaya ait henüz bir işlem kaydı bulunmamaktadır.")
    else:
        st.info("Kayıtlı hasta bulunamadı.")

# 3. YENİ İŞLEM (KAMERA + DOSYA YÜKLEME)
elif st.session_state.sayfa == "yeni_islem":
    st.header("💉 Hastaya Yeni İşlem Ekle")
    
    hastalar = supabase.table("hastalar").select("*").order("ad").execute().data
    
    if hastalar:
        hasta_opsiyonlari = {f"{h['ad']} {h['soyad']}": h['id'] for h in hastalar}
        secilen_hasta_adi = st.selectbox("Hasta Seçin", list(hasta_opsiyonlari.keys()))
        hasta_id = hasta_opsiyonlari[secilen_hasta_adi]
        
        with st.form("yeni_islem_formu", clear_on_submit=True):
            islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
            yapilan_islem = st.text_input("Yapılan İşlem (Örn: Dolgu, Kanal Tedavisi, Çekim)")
            hekim_notu = st.text_area("Hekim Notları")
            
            st.write("---")
            st.write("📸 **Fotoğraf Ekle (Kamera veya Dosya):**")
            
            # Seçenek 1: Doğrudan Kameradan Çek
            kamera_foto = st.camera_input("Kameradan Fotoğraf Çek")
            
            # Seçenek 2: Galeriden / Dosyalardan Yükle
            dosya_foto = st.file_uploader("veya Galeriden Fotoğraf Seç", type=["jpg", "jpeg", "png"])
            
            submit_islem = st.form_submit_button("İşlemi Kaydet")
            
            if submit_islem:
                if not yapilan_islem:
                    st.error("Lütfen yapılan işlemi belirtin.")
                else:
                    fotograf_url = None
                    # Kameradan mı yoksa galeriden mi dosya geldiğini kontrol ediyoruz
                    yuklenen_dosya = kamera_foto if kamera_foto is not None else dosya_foto
                    
                    if yuklenen_dosya is not None:
                        dosya_adi = f"{hasta_id}_{int(datetime.datetime.now().timestamp())}.png"
                        res_bytes = yuklenen_dosya.read()
                        
                        # Supabase Storage'a yükleme
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, res_bytes)
                        fotograf_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                    
                    islem_veri = {
                        "hasta_id": hasta_id,
                        "islem_tarihi": islem_tarihi.isoformat(),
                        "yapilan_islem": yapilan_islem,
                        "hekim_notu": hekim_notu,
                        "fotograf_url": fotograf_url
                    }
                    
                    supabase.table("islemler").insert(islem_veri).execute()
                    st.success("✅ İşlem kaydı başarıyla eklendi!")
    else:
        st.warning("İşlem ekleyebilmek için önce en az bir hasta kaydetmelisiniz.")

# 4. AYARLAR
elif st.session_state.sayfa == "ayarlar":
    st.header("⚙️ Ayarlar")
    st.write("Uygulama ayarları ve menü yapılandırmaları.")
    st.info("Sistem aktif olarak Supabase bulut veritabanı ile senkronize çalışmaktadır.")
        
