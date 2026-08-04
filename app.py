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
# Butonlar: Lacivert (#1b2a4a), Buton Yazısı: Krem (#fdfbf7)
# Arka Plan: Krem (#fdfbf7), Diğer Yazılar: Siyah (#000000) ve Lacivert
st.markdown("""
    <style>
    .stApp {
        background-color: #fdfbf7;
        color: #000000;
    }
    h1, h2, h3, h4, label, .stMarkdown {
        color: #1b2a4a !important;
    }
    .stButton>button {
        background-color: #1b2a4a !important;
        color: #fdfbf7 !important;
        border: none !important;
        border-radius: 8px !important;
        height: 3rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        margin-bottom: 0.5rem !important;
    }
    .stButton>button:hover {
        background-color: #142038 !important;
        color: #ffffff !important;
    }
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
if "gecici_fotolar" not in st.session_state:
    st.session_state.gecici_fotolar = []
if "liste_acik" not in st.session_state:
    st.session_state.liste_acik = False

def sayfa_degistir(sayfa_kodu):
    st.session_state.sayfa = sayfa_kodu

# --- HER EKRANDA ANA SAYFAYA DÖN BUTONU ---
if st.session_state.sayfa != "ana_sayfa":
    if st.button("🏠 Ana Sayfaya Dön", key="btn_ana_sayfa_ust"):
        sayfa_degistir("ana_sayfa")
        st.rerun()

# --- 1. ANA SAYFA ---
if st.session_state.sayfa == "ana_sayfa":
    st.markdown("<h1 style='text-align: center;'>🦷 Diş Hekimi Takip Sistemi</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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

# --- 2. ANA SAYFADAN DOĞRUDAN YENİ İŞLEM EKLEME SAYFASI ---
elif st.session_state.sayfa == "yeni_islem_ana":
    st.subheader("💉 Yeni İşlem / Hasta Kaydı")
    
    hastalar = supabase.table("hastalar").select("*").order("ad_soyad").execute().data
    hasta_opsiyonlari = {"Yeni Hasta Oluştur": "YENI"}
    if hastalar:
        for h in hastalar:
            hasta_opsiyonlari[f"{h['ad_soyad']} ({h['telefon']})"] = h['id']
            
    secilen_hasta_label = st.selectbox("Hasta Seçin", list(hasta_opsiyonlari.keys()))
    secilen_hasta_id = hasta_opsiyonlari[secilen_hasta_label]
    
    # Eğer yeni hasta oluşturulacaksa isim ve tel bilgisi al
    yeni_ad = ""
    yeni_tel = ""
    if secilen_hasta_id == "YENI":
        c_a1, c_a2 = st.columns(2)
        yeni_ad = c_a1.text_input("Hasta Adı Soyadı")
        yeni_tel = c_a2.text_input("Telefon Numarası")

    # İşlem Tarihi (Otomatik bugünün tarihi, elle değiştirilebilir)
    islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
    
    # İşlem Türü Seçimi
    turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
    turler = [t["tur_adi"] for t in turler_resp] if turler_resp else ["Dolgu", "Kanal Tedavisi", "Muayene", "Çekim"]
    secilen_tur = st.selectbox("Yapılan İşlem", turler)
    
    # Hekim Notu
    hekim_notu = st.text_area("Hekim Notları")
    
    st.write("---")
    st.write("📸 **Fotoğraf Ekle (Çoklu Yükleme ve Çekim):**")
    
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

    # Yüklenen Geçici Fotoğrafları Listele ve Silme Seçeneği Sun
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
        
        # Yeni Hasta ise önce hastayı kaydet
        if secilen_hasta_id == "YENI":
            if yeni_ad and yeni_tel:
                h_res = supabase.table("hastalar").insert({
                    "ad_soyad": yeni_ad,
                    "telefon": yeni_tel,
                    "kayit_tarihi": datetime.datetime.now().isoformat()
                }).execute()
                final_hasta_id = h_res.data[0]["id"]
            else:
                st.error("Lütfen Yeni Hasta için Ad Soyad ve Telefon alanlarını doldurun.")
                st.stop()
                
        # Fotoğrafları Supabase Storage'a Yükle
        foto_url_listesi = []
        for foto in st.session_state.gecici_fotolar:
            dosya_adi = f"proc_{int(datetime.datetime.now().timestamp())}_{foto.name if hasattr(foto, 'name') else 'cam.png'}"
            supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.read())
            url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
            foto_url_listesi.append(url)

        # İşlemi Kaydet
        islem_data = {
            "hasta_id": final_hasta_id,
            "islem_tarihi": islem_tarihi.isoformat(),
            "islem_turu": secilen_tur,
            "hekim_notu": hekim_notu,
            "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None
        }
        supabase.table("islemler").insert(islem_data).execute()
        
        st.toast("✅ İşlem başarıyla kaydedildi!")
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
                    "kayit_tarihi": datetime.datetime.now().isoformat()
                }
                supabase.table("hastalar").insert(hasta_veri).execute()
                st.toast("✅ Hasta Başarıyla Kaydedildi!")
            else:
                st.error("Lütfen Hasta Adı Soyadı ve Telefon alanlarını doldurun.")

# --- 4. HASTA LİSTESİ VE FİLTRELEME SAYFASI ---
elif st.session_state.sayfa == "hasta_listesi":
    st.subheader("📋 Hasta Listesi")
    
    # 1. ARAMA VE BİREBİR İSTEDİĞİN TARİH DÜZENİ
    st.write("### 🔍 Arama ve Filtreleme")
    f_isim = st.text_input("Hasta İsmi ile Arama")
    
    st.write("**Tarih Seçimi / Aralığı:**")
    # 1. Tarih Grubu (Yan Yana: Gün, Ay, Yıl)
    col_g1, col_a1, col_y1 = st.columns(3)
    f_g1 = col_g1.selectbox("Gün (1)", [0] + list(range(1, 32)))
    f_a1 = col_a1.selectbox("Ay (1)", [0] + list(range(1, 13)))
    f_y1 = col_y1.number_input("Yıl (1)", min_value=0, max_value=2099, value=0)

    # 2. Tarih Grubu (Aynı Sırayla Altına: Gün, Ay, Yıl)
    col_g2, col_a2, col_y2 = st.columns(3)
    f_g2 = col_g2.selectbox("Gün (2)", [0] + list(range(1, 32)))
    f_a2 = col_a2.selectbox("Ay (2)", [0] + list(range(1, 13)))
    f_y2 = col_y2.number_input("Yıl (2)", min_value=0, max_value=2099, value=0)

    # İşlem Filtresi
    turler_resp = supabase.table("islem_turleri").select("tur_adi").execute().data
    tur_listesi = ["Tümü"] + [t["tur_adi"] for t in turler_resp] if turler_resp else ["Tümü"]
    f_islem_turu = st.selectbox("İşlem Türü Filtresi", tur_listesi)

    st.write("---")

    # LISTENI SAĞ ÜSTÜNDE SIRALAMA SEÇENEĞİ VE LİSTE BUTONU
    c_btn, c_sort = st.columns([2, 2])
    with c_btn:
        if st.button("📋 Hastaları Listele / Kapat"):
            st.session_state.liste_acik = not st.session_state.liste_acik
            
    with c_sort:
        sirulama_secimi = st.selectbox("Sıralama Seçeneği", ["Kayıt Tarihi (Yeni > Eski)", "Alfabetik (A-Z)"])

    # LİSTELEME
    if st.session_state.liste_acik:
        hastalar = supabase.table("hastalar").select("*").execute().data
        
        if hastalar:
            df_hastalar = pd.DataFrame(hastalar)
            
            # İsim Filtresi
            if f_isim:
                df_hastalar = df_hastalar[df_hastalar["ad_soyad"].str.contains(f_isim, case=False, na=False)]

            # İşlem Türüne Göre Filtrele
            if f_islem_turu != "Tümü":
                islem_hastalar = supabase.table("islemler").select("hasta_id").eq("islem_turu", f_islem_turu).execute().data
                uygun_ids = [i["hasta_id"] for i in islem_hastalar]
                df_hastalar = df_hastalar[df_hastalar["id"].isin(uygun_ids)]

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
            st.info("Kayıtlı hasta bulunamadı.")

# --- 4.1 HASTA DETAY SAYFASI ---
elif st.session_state.sayfa == "hasta_detay":
    h_id = st.session_state.secili_hasta_id
    hasta_resp = supabase.table("hastalar").select("*").eq("id", h_id).execute().data
    
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
        islemler = supabase.table("islemler").select("*").eq("hasta_id", h_id).order("islem_tarihi", desc=True).execute().data
        
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
    if st.button("📊 Tüm Hasta Verilerini Excel Olarak İndir"):
        h_data = supabase.table("hastalar").select("*").execute().data
        if h_data:
            df = pd.DataFrame(h_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Hastalar')
            excel_data = output.getvalue()
            st.download_button(label="📥 İndirmeyi Başlat", data=excel_data, file_name="Hasta_Kayitlari.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
