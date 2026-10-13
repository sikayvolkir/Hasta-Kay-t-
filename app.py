import streamlit as st
import datetime
import pandas as pd
import io
import json
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Hasta Takip Sistemi",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "https://zmamzsmfpspenhslskmq.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptYW16c21mcHNwZW5oc2xza21xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU4NDU1MTEsImV4cCI6MjEwMTQyMTUxMX0.YYXkpF9F_jk7lGzIOYtB_dOO0IV-NsuCaFUXrvinndY")
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase bağlantı hatası: {e}")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "user" not in st.session_state:
    st.session_state.user = None
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "hasta_listesi"
if "secili_hasta_id" not in st.session_state:
    st.session_state.secili_hasta_id = None
if "gecici_fotolar" not in st.session_state:
    st.session_state.gecici_fotolar = []
if "duzenlenen_islem_id" not in st.session_state:
    st.session_state.duzenlenen_islem_id = None
if "hasta_duzenleme_modu" not in st.session_state:
    st.session_state.hasta_duzenleme_modu = False

# Modal / Pencere state'leri
if "aktif_modal_dis" not in st.session_state:
    st.session_state.aktif_modal_dis = None
if "dis_islemleri_gecici" not in st.session_state:
    st.session_state.dis_islemleri_gecici = {} # {dis_no: [{islem, tarih, aciklama}]}
if "modal_degerlendirme_acik" not in st.session_state:
    st.session_state.modal_degerlendirme_acik = False
if "yeni_muayene_form_cevaplari" not in st.session_state:
    st.session_state.yeni_muayene_form_cevaplari = {}

# --- AUTHENTICATION FUNCTIONS ---
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.rerun()
    except Exception as e:
        st.error(f"Giriş Başarısız: {e}")

def register(email, password):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            st.success("Kayıt başarılı! Giriş sekmesinden oturum açabilirsiniz.")
        else:
            st.info("Kayıt oluşturuldu, e-posta doğrulamasını kontrol edin.")
    except Exception as e:
        st.error(f"Kayıt Başarısız: {e}")

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.sayfa = "hasta_listesi"
    st.session_state.secili_hasta_id = None
    st.session_state.hasta_duzenleme_modu = False
    st.rerun()

# --- LOGIN & REGISTER SCREEN ---
if not st.session_state.user:
    st.markdown("<h2 style='text-align: center;'>🩺 Hasta Takip Sistemi</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("E-posta Adresi")
                password = st.text_input("Şifre", type="password")
                submit = st.form_submit_button("Giriş Yap", use_container_width=True)
                if submit:
                    if email and password:
                        login(email, password)
                    else:
                        st.warning("Lütfen e-posta ve şifrenizi girin.")
                        
        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("E-posta Adresi")
                reg_password = st.text_input("Şifre (En az 6 karakter)", type="password")
                reg_submit = st.form_submit_button("Hesap Oluştur", use_container_width=True)
                if reg_submit:
                    if reg_email and reg_password:
                        register(reg_email, reg_password)
                    else:
                        st.warning("Lütfen e-posta ve şifrenizi doldurun.")
    st.stop()

# --- LOGGED IN USER CONTEXT ---
user_id = st.session_state.user.id
user_email = st.session_state.user.email

# --- SIDEBAR NAVIGATION (KAYDIRMA / AÇILIR KAPANIR) ---
st.sidebar.title("🩺 Hasta Takip")
st.sidebar.caption(f"👤 {user_email}")

with st.sidebar.expander("📌 Hızlı Menü & İşlemler", expanded=True):
    if st.button("📋 Hasta Listesi & Arama", use_container_width=True):
        st.session_state.sayfa = "hasta_listesi"
        st.session_state.hasta_duzenleme_modu = False
        st.rerun()

    if st.button("👤 Yeni Hasta Kaydı", use_container_width=True):
        st.session_state.sayfa = "yeni_hasta"
        st.session_state.hasta_duzenleme_modu = False
        st.rerun()

    if st.button("🦷 Yeni Muayene", use_container_width=True):
        st.session_state.sayfa = "yeni_muayene"
        st.session_state.hasta_duzenleme_modu = False
        st.rerun()

    if st.button("💉 Eski Tip İşlem Ekle", use_container_width=True):
        st.session_state.sayfa = "yeni_islem"
        st.session_state.hasta_duzenleme_modu = False
        st.rerun()

    if st.button("⚙️ Ayarlar", use_container_width=True):
        st.session_state.sayfa = "ayarlar"
        st.session_state.hasta_duzenleme_modu = False
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    logout()

# ==============================================================================
# --- SAYFA 1: HASTA LİSTESİ VE ARAMA ---
# ==============================================================================
if st.session_state.sayfa == "hasta_listesi":
    st.title("📋 Hasta Listesi")

    arama_metni = st.text_input("🔍 Hasta Adı Soyadı veya Telefon ile Ara...", "")

    try:
        query = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).order("kayit_tarihi", desc=True)
        if arama_metni.strip():
            query = query.ilike("ad_soyad", f"%{arama_metni.strip()}%")
        
        hastalar = query.execute().data
    except Exception as e:
        st.error(f"Hastalar çekilirken hata oluştu: {e}")
        hastalar = []

    if not hastalar:
        st.info("Kayıtlı hasta bulunamadı.")
    else:
        for hasta in hastalar:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 1])
                with c1:
                    if hasta.get("foto_url"):
                        st.image(hasta["foto_url"], width=60)
                    else:
                        st.markdown("👤")
                with c2:
                    st.subheader(hasta.get("ad_soyad", "İsimsiz"))
                    st.caption(f"Cinsiyet: {hasta.get('cinsiyet', '-')} | D.Tarihi: {hasta.get('dogum_tarihi', '-')}")
                with c3:
                    st.write(f"📞 {hasta.get('telefon', '-')}")
                with c4:
                    if st.button("Detay / İşlemler", key=f"detay_{hasta['id']}", use_container_width=True):
                        st.session_state.secili_hasta_id = hasta["id"]
                        st.session_state.sayfa = "hasta_detay"
                        st.session_state.hasta_duzenleme_modu = False
                        st.rerun()
                with c5:
                    if st.button("🗑️", key=f"sil_h_{hasta['id']}", help="Hastayı Sil"):
                        supabase.table("hastalar").delete().eq("id", hasta["id"]).execute()
                        st.toast("Hasta silindi.")
                        st.rerun()
                st.markdown("---")

# ==============================================================================
# --- SAYFA 2: YENİ HASTA KAYIT SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_hasta":
    st.title("👤 Yeni Hasta Kaydı")

    with st.form("yeni_hasta_formu", clear_on_submit=True):
        col_sol, col_sag = st.columns([3, 1])
        with col_sol:
            ad_soyad = st.text_input("Hasta Adı Soyadı *")
            cinsiyet = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Diğer"])
            dogum_tarihi = st.date_input("Doğum Tarihi", datetime.date(1990, 1, 1))
        with col_sag:
            st.write("Profil Resmi")
            profil_foto = st.file_uploader("Fotoğraf Seç", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

        telefon = st.text_input("Telefon Numarası *", placeholder="05XXXXXXXXX")
        kaydet = st.form_submit_button("Hastayı Kaydet", use_container_width=True)

        if kaydet:
            if ad_soyad and telefon:
                try:
                    foto_url = None
                    if profil_foto:
                        dosya_adi = f"p_{int(datetime.datetime.now().timestamp())}.png"
                        foto_bytes = profil_foto.getvalue()
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto_bytes)
                        foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                    hasta_veri = {
                        "ad_soyad": ad_soyad,
                        "cinsiyet": cinsiyet,
                        "dogum_tarihi": dogum_tarihi.isoformat() if dogum_tarihi else None,
                        "telefon": telefon,
                        "foto_url": foto_url,
                        "kullanici_id": user_id,
                        "kayit_tarihi": datetime.datetime.now().isoformat()
                    }

                    supabase.table("hastalar").insert(hasta_veri).execute()
                    st.toast("✅ Hasta başarıyla kaydedildi!")
                    st.session_state.sayfa = "hasta_listesi"
                    st.rerun()
                except Exception as ex:
                    st.error(f"Kayıt Sırasında Hata Oluştu: {ex}")
            else:
                st.warning("Lütfen Hasta Adı Soyadı ve Telefon alanlarını doldurun.")

# ==============================================================================
# --- YENİ EKLENEN SAYFA: YENİ MUAYENE EKRANI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_muayene":
    st.title("🦷 Yeni Muayene ve Tedavi Planı")

    # 1. Hasta Seçimi veya Yeni Hasta Ekleme
    try:
        hastalar_res = supabase.table("hastalar").select("id, ad_soyad, telefon").eq("kullanici_id", user_id).order("ad_soyad").execute().data
    except Exception:
        hastalar_res = []

    hasta_secenekleri = ["+ Yeni Hasta Ekle"] + [f"{h['ad_soyad']} ({h['telefon']})" for h in hastalar_res]
    secilen_hasta_secim = st.selectbox("Hasta Seçin veya Yeni Oluşturun *", hasta_secenekleri)

    hedef_hasta_id = None
    if secilen_hasta_secim == "+ Yeni Hasta Ekle":
        with st.expander("📝 Yeni Hasta Bilgileri", expanded=True):
            yeni_h_ad = st.text_input("Yeni Hasta Adı Soyadı *")
            yeni_h_tel = st.text_input("Yeni Hasta Telefon *")
            if st.button("Hızlı Hasta Oluştur"):
                if yeni_h_ad and yeni_h_tel:
                    try:
                        res = supabase.table("hastalar").insert({
                            "ad_soyad": yeni_h_ad,
                            "telefon": yeni_h_tel,
                            "kullanici_id": user_id,
                            "kayit_tarihi": datetime.datetime.now().isoformat()
                        }).execute()
                        st.success("Yeni hasta oluşturuldu! Lütfen sayfayı güncelleyin veya tekrar seçin.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Ad ve telefon zorunludur.")
    else:
        # Seçilen hastanın ID'sini bul
        for h in hastalar_res:
            if f"{h['ad_soyad']} ({h['telefon']})" == secilen_hasta_secim:
                hedef_hasta_id = h['id']
                break

    # 2. Tarih Seçimi (Varsayılan bugün, değiştirmeye izinli)
    muayene_tarihi = st.date_input("Muayene Tarihi", datetime.date.today())

    st.markdown("---")

    # 3. Tedavi Planı Bölümü (Diş Şeması Modalı/Butonları)
    st.subheader("🦷 Tedavi Planı (Diş Şeması)")
    st.info("Dişler üzerine tıklayarak ilgili diş için işlem, ileri tarih ve not tanımlayabilirsiniz.")

    # Diş listesi (Örnek standart diş numaraları / harfleri: Üst ve Alt ark simülasyonu)
    dis_listesi = [
        "18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28",
        "48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"
    ]

    # Grid veya butonlar şeklinde dişlerin gösterimi
    cols_dis = st.columns(8)
    for idx, dis_no in enumerate(dis_listesi[:32]): # Üst/Alt Daimi dişler öncelikli
        is_secili = dis_no in st.session_state.dis_islemleri_gecici and len(st.session_state.dis_islemleri_gecici[dis_no]) > 0
        btn_label = f"🦷 {dis_no}" + (" (İşlemli)" if is_secili else "")
        if cols_dis[idx % 8].button(btn_label, key=f"dis_btn_{dis_no}"):
            st.session_state.aktif_modal_dis = dis_no

    # Eğer bir dişe tıklandıysa o dişin penceresi / ayarları açılır
    if st.session_state.aktif_modal_dis:
        aktif_d = st.session_state.aktif_modal_dis
        st.markdown(f"### ⚙️ Diş No: {aktif_d} - İşlem Tanımlama Penceresi")
        
        try:
            tur_data = supabase.table("islem_turleri").select("tur_adi").execute().data
            tum_islemler = [t["tur_adi"] for t in tur_data] if tur_data else ["Dolgu", "Kanal", "Çekim", "Kron", "İmplant"]
        except Exception:
            tum_islemler = ["Dolgu", "Kanal", "Çekim", "Kron", "İmplant"]

        with st.form(key=f"dis_form_{aktif_d}"):
            st.write("Yapılacak İşlemleri Seçin (Birden fazla seçebilirsiniz):")
            secilen_islemler = []
            for islem_adi in tum_islemler:
                if st.checkbox(islem_adi, key=f"chk_{aktif_d}_{islem_adi}"):
                    secilen_islemler.append(islem_adi)

            islem_metin_kutu = st.text_input("Diş İçin Ek Açıklama / Metin Kutusu", key=f"txt_{aktif_d}")
            ileri_tarih = st.date_input("İleriye Yönelik İşlem Tarihi", datetime.date.today(), key=f"date_{aktif_d}")

            col_m1, col_m2 = st.columns(2)
            kaydet_dis = col_m1.form_submit_button("💾 Diş İşlemini Kaydet")
            kapat_dis = col_m2.form_submit_button("✖️ Çarpı (Kapat)")

            if kaydet_dis:
                st.session_state.dis_islemleri_gecici[aktif_d] = {
                    "islemler": secilen_islemler,
                    "not": islem_metin_kutu,
                    "tarih": ileri_tarih.isoformat()
                }
                st.success(f"{aktif_d} nolu diş kaydedildi.")
                st.session_state.aktif_modal_dis = None
                st.rerun()

            if kapat_dis:
                st.session_state.aktif_modal_dis = None
                st.rerun()

    # Kaydedilmiş diş işlemlerinin özeti
    if st.session_state.dis_islemleri_gecici:
        st.write("📋 **Planlanan Diş İşlemleri Özeti:**")
        for d_no, d_bilgi in st.session_state.dis_islemleri_gecici.items():
            st.write(f"- **Diş {d_no}:** {', '.join(d_bilgi['islemler'])} | Tarih: {d_bilgi['tarih']} | Not: {d_bilgi['not']}")

    st.markdown("---")

    # 4. Hasta Değerlendirme Formu Bölümü
    st.subheader("📋 Hasta Değerlendirme Formu")
    
    # Ayarlardan gelen soruları çek
    try:
        sorular_res = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).execute().data
    except Exception:
        sorular_res = []

    if not sorular_res:
        st.info("Henüz değerlendirme formu sorusu tanımlanmamış. 'Ayarlar' kısmından soru ekleyebilirsiniz.")
    else:
        for s in sorular_res:
            s_id = s["id"]
            s_metin = s["soru_metni"]
            cevap = st.text_input(f"❓ {s_metin}", key=f"form_soru_{s_id}")
            st.session_state.yeni_muayene_form_cevaplari[s_metin] = cevap

    st.markdown("---")

    # 5. Not ve Resim Yükleme Kısımları
    st.subheader("📝 Genel Notlar ve Görseller")
    muayene_genel_not = st.text_area("Muayene Notu / Açıklama")

    st.write("📸 **Röntgen / Resim Yükle:**")
    muayene_fotolar = st.file_uploader("Görsel Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="muayene_foto_yukle")

    # 6. Kaydet Butonu
    if st.button("💾 Muayeneyi Tamamen Kaydet", use_container_width=True):
        if not hedef_hasta_id:
            st.warning("Lütfen geçerli bir hasta seçin.")
        else:
            try:
                foto_url_listesi = []
                if muayene_fotolar:
                    for foto in muayene_fotolar:
                        dosya_adi = f"muayene_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                        foto_bytes = foto.getvalue()
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto_bytes)
                        url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                        foto_url_listesi.append(url)

                # Verileri kaydetme hazırlığı
                muayene_veri = {
                    "hasta_id": hedef_hasta_id,
                    "kullanici_id": user_id,
                    "islem_tarihi": muayene_tarihi.isoformat(),
                    "islem_turu": "Detaylı Muayene",
                    "hekim_notu": f"[Muayene Notu]: {muayene_genel_not}\n[Diş Planı]: {json.dumps(st.session_state.dis_islemleri_gecici, ensure_ascii=False)}\n[Form Cevapları]: {json.dumps(st.session_state.yeni_muayene_form_cevaplari, ensure_ascii=False)}",
                    "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None
                }

                supabase.table("islemler").insert(muayene_veri).execute()
                st.toast("✅ Muayene başarıyla kaydedildi!")
                
                # Session temizliği
                st.session_state.dis_islemleri_gecici = {}
                st.session_state.yeni_muayene_form_cevaplari = {}
                st.session_state.secili_hasta_id = hedef_hasta_id
                st.session_state.sayfa = "hasta_detay"
                st.rerun()
            except Exception as ex:
                st.error(f"Kayıt sırasında hata oluştu: {ex}")

# ==============================================================================
# --- SAYFA 3 (ESKİ): YENİ İŞLEM EKLE SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_islem":
    st.title("💉 Yeni İşlem Ekle (Hızlı)")

    try:
        hastalar_res = supabase.table("hastalar").select("id, ad_soyad, telefon").eq("kullanici_id", user_id).order("ad_soyad").execute().data
    except Exception:
        hastalar_res = []

    if not hastalar_res:
        st.warning("Henüz kayıtlı hastanız bulunmuyor. Önce 'Yeni Hasta Kaydı' yapmalısınız.")
    else:
        hasta_dict = {f"{h['ad_soyad']} ({h['telefon']})": h['id'] for h in hastalar_res}
        secilen_label = st.selectbox("İşlem Yapılacak Hastayı Seçin *", list(hasta_dict.keys()))
        secilen_hasta_id = hasta_dict[secilen_label]

        try:
            tur_data = supabase.table("islem_turleri").select("tur_adi").execute().data
            islem_turleri_listesi = [item["tur_adi"] for item in tur_data] if tur_data else ["Muayene", "Dolgu", "Çekim"]
        except Exception:
            islem_turleri_listesi = ["Muayene", "Dolgu", "Kanal Tedavisi", "Çekim"]

        islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
        islem_turu = st.selectbox("İşlem Türü", islem_turleri_listesi)
        hekim_notu = st.text_area("Hekim Notu / Açıklama")

        st.write("📸 **Fotoğraf / Röntgen Yükle:**")
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
            st.write("**Eklenecek Görseller:**")
            cols = st.columns(4)
            for idx, foto in enumerate(st.session_state.gecici_fotolar):
                with cols[idx % 4]:
                    st.image(foto, width=120)
                    if st.button("Sil", key=f"f_sil_{idx}"):
                        st.session_state.gecici_fotolar.pop(idx)
                        st.rerun()

        if st.button("💾 İşlemi Kaydet", use_container_width=True):
            try:
                foto_url_listesi = []
                for foto in st.session_state.gecici_fotolar:
                    dosya_adi = f"proc_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                    foto_bytes = foto.getvalue() if hasattr(foto, 'getvalue') else foto.read()
                    supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto_bytes)
                    url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                    foto_url_listesi.append(url)

                formatted_not = f"[{datetime.date.today().strftime('%d.%m.%Y')}] {hekim_notu}" if hekim_notu else ""

                islem_veri = {
                    "hasta_id": secilen_hasta_id,
                    "islem_tarihi": islem_tarihi.isoformat(),
                    "islem_turu": islem_turu,
                    "hekim_notu": formatted_not,
                    "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None,
                    "kullanici_id": user_id
                }

                supabase.table("islemler").insert(islem_veri).execute()
                st.toast("✅ İşlem başarıyla kaydedildi!")
                st.session_state.gecici_fotolar = []
                st.session_state.secili_hasta_id = secilen_hasta_id
                st.session_state.sayfa = "hasta_detay"
                st.rerun()
            except Exception as ex:
                st.error(f"İşlem kaydedilirken hata oluştu: {ex}")

# ==============================================================================
# --- SAYFA 4: HASTA DETAY & İŞLEM GEÇMİŞİ SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "hasta_detay":
    hasta_id = st.session_state.secili_hasta_id

    if not hasta_id:
        st.warning("Seçili hasta bulunamadı.")
        st.session_state.sayfa = "hasta_listesi"
        st.rerun()

    try:
        hasta_res = supabase.table("hastalar").select("*").eq("id", hasta_id).execute()
        hasta = hasta_res.data[0] if hasta_res.data else None
    except Exception as e:
        st.error(f"Hasta bilgisi çekilemedi: {e}")
        hasta = None

    if not hasta:
        st.error("Hasta bulunamadı!")
        if st.button("Listeye Dön"):
            st.session_state.sayfa = "hasta_listesi"
            st.rerun()
    else:
        if st.session_state.hasta_duzenleme_modu:
            st.subheader("✏️ Hasta Bilgilerini Düzenle")
            with st.form("hasta_duzenle_formu"):
                col1, col2 = st.columns(2)
                with col1:
                    yeni_ad = st.text_input("Hasta Adı Soyadı", value=hasta.get("ad_soyad", ""))
                    yeni_tel = st.text_input("Telefon Numarası", value=hasta.get("telefon", ""))
                    cinsiyet_opts = ["Kadın", "Erkek", "Diğer"]
                    c_idx = cinsiyet_opts.index(hasta.get("cinsiyet")) if hasta.get("cinsiyet") in cinsiyet_opts else 0
                    yeni_cinsiyet = st.selectbox("Cinsiyet", cinsiyet_opts, index=c_idx)
                with col2:
                    dt_val = datetime.datetime.strptime(hasta["dogum_tarihi"], "%Y-%m-%d").date() if hasta.get("dogum_tarihi") else datetime.date(1990, 1, 1)
                    yeni_dt = st.date_input("Doğum Tarihi", dt_val)
                    yeni_foto = st.file_uploader("Yeni Profil Fotoğrafı Yükle", type=["jpg", "png", "jpeg"])

                c_h_save, c_h_cancel = st.columns(2)
                with c_h_save:
                    btn_hasta_kaydet = st.form_submit_button("💾 Bilgileri Güncelle", use_container_width=True)
                with c_h_cancel:
                    btn_hasta_iptal = st.form_submit_button("❌ İptal", use_container_width=True)

                if btn_hasta_kaydet:
                    updated_foto_url = hasta.get("foto_url")
                    if yeni_foto:
                        dosya_adi = f"p_{int(datetime.datetime.now().timestamp())}.png"
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, yeni_foto.getvalue())
                        updated_foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                    supabase.table("hastalar").update({
                        "ad_soyad": yeni_ad,
                        "telefon": yeni_tel,
                        "cinsiyet": yeni_cinsiyet,
                        "dogum_tarihi": yeni_dt.isoformat() if yeni_dt else None,
                        "foto_url": updated_foto_url
                    }).eq("id", hasta_id).execute()

                    st.toast("✅ Hasta bilgileri güncellendi.")
                    st.session_state.hasta_duzenleme_modu = False
                    st.rerun()

                if btn_hasta_iptal:
                    st.session_state.hasta_duzenleme_modu = False
                    st.rerun()
        else:
            col_foto, col_info, col_del = st.columns([1, 3, 1])
            with col_foto:
                if hasta.get("foto_url"):
                    st.image(hasta["foto_url"], width=120)
                else:
                    st.markdown("👤 *Fotoğraf Yok*")
            with col_info:
                st.title(hasta.get("ad_soyad"))
                st.write(f"📞 **Telefon:** {hasta.get('telefon', '-')}")
                st.write(f"🧬 **Cinsiyet:** {hasta.get('cinsiyet', '-')} | 📅 **D.Tarihi:** {hasta.get('dogum_tarihi', '-')}")
            with col_del:
                if st.button("✏️ Hastayı Düzenle", use_container_width=True):
                    st.session_state.hasta_duzenleme_modu = True
                    st.rerun()
                if st.button("🗑️ Hastayı Sil", type="primary", use_container_width=True):
                    supabase.table("hastalar").delete().eq("id", hasta_id).execute()
                    st.toast("Hasta ve tüm geçmişi silindi.")
                    st.session_state.sayfa = "hasta_listesi"
                    st.rerun()

        st.markdown("---")
        st.subheader("📜 Yapılan İşlemler ve Muayene Geçmişi")

        try:
            islemler = supabase.table("islemler").select("*").eq("hasta_id", hasta_id).order("islem_tarihi", desc=True).execute().data
        except Exception as e:
            st.error(f"İşlemler çekilirken hata oluştu: {e}")
            islemler = []

        if not islemler:
            st.info("Bu hastaya ait henüz bir işlem kaydı bulunmuyor.")
        else:
            for islem in islemler:
                with st.expander(f"🗓️ {islem.get('islem_tarihi')} - {islem.get('islem_turu')}"):
                    
                    if st.session_state.duzenlenen_islem_id == islem['id']:
                        st.markdown("### ✏️ İşlemi Düzenle")
                        
                        yeni_ek_not = st.text_area("Yeni Not / Güncelleme Ekle", placeholder="Eklemek istediğiniz notu yazın...")
                        
                        st.write("📸 **Yeni Fotoğraf / Röntgen Ekle:**")
                        yeni_fotolar = st.file_uploader("Görsel Yükle", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"up_{islem['id']}")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾 Değişiklikleri Kaydet", key=f"save_{islem['id']}", use_container_width=True):
                                existing_not = islem.get("hekim_notu") or ""
                                bugun_str = datetime.date.today().strftime('%d.%m.%Y')
                                
                                if yeni_ek_not.strip():
                                    ek_metin = f"\n[{bugun_str} Ek Not]: {yeni_ek_not.strip()}"
                                    yeni_toplam_not = existing_not + ek_metin if existing_not else f"[{bugun_str} Not]: {yeni_ek_not.strip()}"
                                else:
                                    yeni_toplam_not = existing_not

                                mev_url_str = islem.get("fotograf_url") or ""
                                mevcut_urls = [u.strip() for u in mev_url_str.split(",") if u.strip()]
                                
                                if yeni_fotolar:
                                    for yf in yeni_fotolar:
                                        dosya_adi = f"proc_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, yf.getvalue())
                                        url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                                        mevcut_urls.append(url)

                                supabase.table("islemler").update({
                                    "hekim_notu": yeni_toplam_not,
                                    "fotograf_url": ",".join(mevcut_urls) if mevcut_urls else None
                                }).eq("id", islem['id']).execute()

                                st.toast("✅ İşlem başarıyla güncellendi.")
                                st.session_state.duzenlenen_islem_id = None
                                st.rerun()

                        with col_cancel:
                            if st.button("❌ İptal", key=f"cancel_{islem['id']}", use_container_width=True):
                                st.session_state.duzenlenen_islem_id = None
                                st.rerun()

                    else:
                        st.text_area("Hekim Notları Geçmişi", value=islem.get('hekim_notu', '-'), disabled=True, height=120)
                        
                        foto_raw = islem.get("fotograf_url")
                        if foto_raw:
                            urls = [u.strip() for u in foto_raw.split(",") if u.strip()]
                            if urls:
                                st.write("**Görseller / Röntgenler:**")
                                img_cols = st.columns(min(len(urls), 3))
                                for idx, u in enumerate(urls):
                                    with img_cols[idx % 3]:
                                        st.image(u, use_container_width=True)

                        c_btn1, c_btn2 = st.columns([1, 1])
                        with c_btn1:
                            if st.button("✏️ Düzenle / Yeni Not-Foto Ekle", key=f"edit_{islem['id']}"):
                                st.session_state.duzenlenen_islem_id = islem['id']
                                st.rerun()
                        with c_btn2:
                            if st.button("🗑️ İşlemi Sil", key=f"isl_sil_{islem['id']}"):
                                supabase.table("islemler").delete().eq("id", islem['id']).execute()
                                st.toast("İşlem silindi.")
                                st.rerun()

# ==============================================================================
# --- SAYFA 5: AYARLAR SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "ayarlar":
    st.title("⚙️ Ayarlar")

    tab_tur, tab_form_soru, tab_export, tab_account = st.tabs(["🏷️ İşlem Türleri", "📋 Değerlendirme Formu Soruları", "📊 Excel Dışa Aktar", "👤 Hesap"])

    with tab_tur:
        st.subheader("Yeni İşlem Türü Ekle")
        c_add1, c_add2 = st.columns([3, 1])
        with c_add1:
            yeni_tur = st.text_input("Tür Adı", placeholder="Örn: Diş Beyazlatma", label_visibility="collapsed")
        with c_add2:
            if st.button("Ekle", use_container_width=True):
                if yeni_tur:
                    try:
                        supabase.table("islem_turleri").insert({"tur_adi": yeni_tur}).execute()
                        st.toast("✅ İşlem türü eklendi.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ekleme başarısız: {e}")

        st.write("---")
        st.subheader("Mevcut İşlem Türleri")
        try:
            turler = supabase.table("islem_turleri").select("*").execute().data
        except Exception:
            turler = []

        if turler:
            for t in turler:
                col_t1, col_t2 = st.columns([4, 1])
                col_t1.write(f"• **{t['tur_adi']}**")
                if col_t2.button("Sil", key=f"tur_sil_{t['id']}"):
                    supabase.table("islem_turleri").delete().eq("id", t['id']).execute()
                    st.toast("İşlem türü silindi.")
                    st.rerun()

    with tab_form_soru:
        st.subheader("📋 Hasta Değerlendirme Formu Soru Ayarları (Sınırsız)")
        st.write("Yeni muayene ekranında görünmesini istediğiniz soruları buradan ekleyebilirsiniz.")

        with st.form("yeni_soru_formu"):
            yeni_soru_metni = st.text_input("Yeni Soru Metni", placeholder="Örn: Alerjik olduğunuz bir ilaç var mı?")
            soru_kaydet_btn = st.form_submit_button("Soru Ekle")
            if soru_kaydet_btn:
                if yeni_soru_metni.strip():
                    try:
                        supabase.table("form_sorulari").insert({
                            "kullanici_id": user_id,
                            "soru_metni": yeni_soru_metni.strip()
                        }).execute()
                        st.success("Soru başarıyla eklendi.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Soru metni boş olamaz.")

        st.write("---")
        st.subheader("Mevcut Sorularınız")
        try:
            mevcut_sorular = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).execute().data
        except Exception:
            mevcut_sorular = []

        if mevcut_sorular:
            for m_soru in mevcut_sorular:
                c_s1, c_s2 = st.columns([4, 1])
                c_s1.write(f"• {m_soru['soru_metni']}")
                if c_s2.button("Sil", key=f"soru_sil_{m_soru['id']}"):
                    supabase.table("form_sorulari").delete().eq("id", m_soru['id']).execute()
                    st.toast("Soru silindi.")
                    st.rerun()
        else:
            st.info("Kayıtlı soru bulunmuyor.")

    with tab_export:
        st.subheader("📊 Klinik Verilerini İndir")
        st.write("Kayıtlı hastalarınızı ve işlem geçmişinizi Excel dosyası olarak bilgisayarınıza aktarabilirsiniz.")
        
        if st.button("📥 Hastaları Excel Olarak İndir", use_container_width=True):
            h_data = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).execute().data
            if h_data:
                df_hastalar = pd.DataFrame(h_data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_hastalar.to_excel(writer, index=False, sheet_name='Hastalar')
                excel_bytes = output.getvalue()
                st.download_button(
                    label="💾 İndirmeyi Başlat (xlsx)", 
                    data=excel_bytes, 
                    file_name=f"Hastalar_{datetime.date.today()}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.warning("İndirilecek hasta kaydı bulunamadı.")

    with tab_account:
        st.subheader("👤 Oturum Bilgileri")
        st.write(f"**Mevcut Giriş Yapılan E-Posta:** `{user_email}`")
        st.write("Farklı bir hekim hesabına geçmek için çıkış yapabilirsiniz.")
        if st.button("🔄 Hesap Değiştir / Çıkış Yap", use_container_width=True):
            logout()
