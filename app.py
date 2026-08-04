import streamlit as st
import datetime
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
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
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

# --- AUTHENTICATION FUNCTIONS ---
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.rerun()
    except Exception as e:
        st.error(f"Giriş Başarısız: {e}")

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.sayfa = "hasta_listesi"
    st.session_state.secili_hasta_id = None
    st.rerun()

# --- LOGIN SCREEN ---
if not st.session_state.user:
    st.markdown("<h2 style='text-align: center;'>🩺 Hasta Takip Sistemi</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Giriş Yapın</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("E-posta Adresi")
            password = st.text_input("Şifre", type="password")
            submit = st.form_submit_button("Giriş Yap", use_container_width=True)
            if submit:
                if email and password:
                    login(email, password)
                else:
                    st.warning("Lütfen e-posta ve şifrenizi girin.")
    st.stop()

# --- LOGGED IN USER CONTEXT ---
user_id = st.session_state.user.id
user_email = st.session_state.user.email

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🩺 Hasta Takip")
st.sidebar.caption(f"👤 {user_email}")

if st.sidebar.button("📋 Hasta Listesi & Arama", use_container_width=True):
    st.session_state.sayfa = "hasta_listesi"
    st.rerun()

if st.sidebar.button("➕ Yeni Hasta Kaydı", use_container_width=True):
    st.session_state.sayfa = "yeni_hasta"
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
                c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
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
# --- SAYFA 3: HASTA DETAY & İŞLEM GEÇMİŞİ SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "hasta_detay":
    hasta_id = st.session_state.secili_hasta_id

    if not hasta_id:
        st.warning("Seçili hasta bulunamadı.")
        st.session_state.sayfa = "hasta_listesi"
        st.rerun()

    # Hasta Bilgisini Çek
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
        # Üst Başlık & Profil Kartı
        col_foto, col_info = st.columns([1, 4])
        with col_foto:
            if hasta.get("foto_url"):
                st.image(hasta["foto_url"], width=120)
            else:
                st.markdown("👤 *Fotoğraf Yok*")
        with col_info:
            st.title(hasta.get("ad_soyad"))
            st.write(f"📞 **Telefon:** {hasta.get('telefon', '-')}")
            st.write(f"🧬 **Cinsiyet:** {hasta.get('cinsiyet', '-')} | 📅 **D.Tarihi:** {hasta.get('dogum_tarihi', '-')}")

        st.markdown("---")

        # Tablar: İşlem Geçmişi & Yeni İşlem Ekle
        tab1, tab2 = st.tabs(["📜 İşlem Geçmişi", "➕ Yeni İşlem / Muayene Ekle"])

        # Tab 1: İşlem Geçmişi
        with tab1:
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
                        st.write(f"**Hekim Notu:** {islem.get('hekim_notu', '-')}")
                        if islem.get("fotograf_url"):
                            st.image(islem["fotograf_url"], caption="İşlem Görseli/Röntgen", width=300)

        # Tab 2: Yeni İşlem Ekleme Formu
        with tab2:
            # Dinamik İşlem Türlerini Veritabanından Al
            try:
                tur_data = supabase.table("islem_turleri").select("tur_adi").execute().data
                islem_turleri_listesi = [item["tur_adi"] for item in tur_data] if tur_data else ["Muayene", "Dolgu", "Çekim"]
            except Exception:
                islem_turleri_listesi = ["Muayene", "Dolgu", "Kanal Tedavisi", "Çekim"]

            with st.form("yeni_islem_formu", clear_on_submit=True):
                islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
                islem_turu = st.selectbox("İşlem Türü", islem_turleri_listesi)
                hekim_notu = st.text_area("Hekim Notu / Açıklama")
                islem_foto = st.file_uploader("İşlem Fotoğrafı / Röntgen (İsteğe Bağlı)", type=["jpg", "png", "jpeg"])

                islem_kaydet = st.form_submit_button("İşlemi Kaydet", use_container_width=True)

                if islem_kaydet:
                    try:
                        islem_foto_url = None
                        if islem_foto:
                            dosya_adi = f"i_{hasta_id}_{int(datetime.datetime.now().timestamp())}.png"
                            foto_bytes = islem_foto.getvalue()
                            supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto_bytes)
                            islem_foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                        islem_veri = {
                            "hasta_id": hasta_id,
                            "islem_tarihi": islem_tarihi.isoformat(),
                            "islem_turu": islem_turu,
                            "hekim_notu": hekim_notu,
                            "fotograf_url": islem_foto_url,
                            "kullanici_id": user_id
                        }

                        supabase.table("islemler").insert(islem_veri).execute()
                        st.toast("✅ İşlem başarıyla eklendi!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"İşlem kaydedilirken hata oluştu: {ex}")
