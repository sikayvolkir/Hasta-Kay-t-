import streamlit as st
from supabase import create_client, Client
import datetime

# --- SUPABASE BAĞLANTISI ---
# .streamlit/secrets.toml dosyasındaki bilgileri okur
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Diş Hekimi Hasta Takip", layout="centered")

# Sayfa durumu yönetimi (Session State)
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "Ana Sayfa"
if "secili_hasta_id" not in st.session_state:
    st.session_state.secili_hasta_id = None

# --- GELİŞMİŞ/ESNEK BUTON MENÜSÜ ---
# İleride yeni sayfa eklemek/çıkarmak için sadece bu sözlüğü güncellemen yeterlidir.
MENULER = {
    "Yeni Hasta Kayıt": "yeni_hasta",
    "Hasta Listesi": "hasta_listesi",
    "Yeni İşlem": "yeni_islem",
    "Ayarlar": "ayarlar"
}

def sayfa_degistir(sayfa_adi):
    st.session_state.sayfa = sayfa_adi

# --- ANA EKRAN (HOŞ GELDİNİZ & BUTONLAR) ---
st.title("🦷 Diş Hekimi Hasta Kayıt Sistemi")
st.subheader("Hoş geldiniz.")
st.write("---")

# Yan menüde veya ana sayfada gezinti butonları
st.write("### Hızlı Menü")
cols = st.columns(len(MENULER))
for i, (etiket, kod) in enumerate(MENULER.items()):
    if cols[i].button(etiket, use_container_width=True):
        sayfa_degistir(kod)

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
                res = supabase.table("hastalar").insert(data).execute()
                st.success(f"{ad} {soyad} başarıyla kaydedildi!")
            else:
                st.error("Lütfen ad ve soyad alanlarını doldurun.")

# 2. HASTA LİSTESİ VE HASTA DETAYI
elif st.session_state.sayfa == "hasta_listesi":
    st.header("📋 Hasta Listesi ve Geçmişi")
    
    hastalar = supabase.table("hastalar").select("*").execute().data
    
    if hastalar:
        # Hasta seçimi için liste hazırlığı
        hasta_opsiyonlari = {f"{h['ad']} {h['soyad']} (ID: {h['id']})": h['id'] for h in hastalar}
        secilen_hasta_etiket = st.selectbox("İşlem geçmişini görmek istediğiniz hastayı seçin:", list(hasta_opsiyonlari.keys()))
        
        secilen_id = hasta_opsiyonlari[secilen_hasta_etiket]
        
        # Seçilen Hastanın Detayları ve İşlem Geçmişi
        st.write("---")
        hasta_detay = next(h for h in hastalar if h['id'] == secilen_id)
        st.markdown(f"### 🩺 **{hasta_detay['ad']} {hasta_detay['soyad']}**")
        st.write(f"**Cinsiyet:** {hasta_detay['cinsiyet']} | **Kayıt Tarihi:** {hasta_detay['kayit_tarihi'][:10]}")
        
        # Hastaya ait işlemleri çek
        islemler = supabase.table("islemler").select("*").eq("hasta_id", secilen_id).order("islem_tarihi", desc=True).execute().data
        
        st.subheader("Yapılan İşlemler")
        if islemler:
            for islem in islemler:
                with st.expander(f"🗓️ {islem['islem_tarihi'][:10]} - {islem['yapilan_islem']}"):
                    st.write(f"**Hekim Notu:** {islem['hekim_notu']}")
                    if islem.get("fotograf_url"):
                        st.image(islem["fotograf_url"], caption="İşlem Fotoğrafı", width=300)
        else:
            st.info("Bu hastaya ait henüz bir işlem kaydı bulunmamaktadır.")
    else:
        st.info("Kayıtlı hasta bulunamadı.")

# 3. YENİ İŞLEM EKLEME
elif st.session_state.sayfa == "yeni_islem":
    st.header("💉 Hastaya Yeni İşlem Ekle")
    
    hastalar = supabase.table("hastalar").select("*").execute().data
    
    if hastalar:
        hasta_opsiyonlari = {f"{h['ad']} {h['soyad']}": h['id'] for h in hastalar}
        secilen_hasta_adi = st.selectbox("Hasta Seçin", list(hasta_opsiyonlari.keys()))
        hasta_id = hasta_opsiyonlari[secilen_hasta_adi]
        
        with st.form("yeni_islem_formu", clear_on_submit=True):
            islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
            yapilan_islem = st.text_input("Yapılan İşlem (Örn: Dolgu, Kanal Tedavisi, Çekim)")
            hekim_notu = st.text_area("Hekim Notları")
            yuklenen_dosya = st.file_uploader("İşlem Fotoğrafı Yükle", type=["jpg", "jpeg", "png"])
            
            submit_islem = st.form_submit_button("İşlemi Kaydet")
            
            if submit_islem:
                fotograf_url = None
                
                # Fotoğraf yükleme mantığı
                if yuklenen_dosya is not None:
                    dosya_adi = f"{hasta_id}_{datetime.datetime.now().timestamp()}.png"
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
                st.success("İşlem kaydı başarıyla eklendi!")
    else:
        st.warning("İşlem ekleyebilmek için önce en az bir hasta kaydetmelisiniz.")

# 4. AYARLAR
elif st.session_state.sayfa == "ayarlar":
    st.header("⚙️ Ayarlar")
    st.write("Uygulama ayarlarını ve menü yapılandırmalarını buradan yönetebilirsiniz.")
