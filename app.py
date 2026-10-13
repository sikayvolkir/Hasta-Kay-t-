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
if "aktif_modal_dis" not in st.session_state:
    st.session_state.aktif_modal_dis = None
if "dis_islemleri_gecici" not in st.session_state:
    st.session_state.dis_islemleri_gecici = {}
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

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email)
        st.success("Şifre sıfırlama talimatı e-posta adresinize gönderildi.")
    except Exception as e:
        st.error(f"Şifre sıfırlama hatası: {e}")

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

# --- LOGIN & REGISTER & FORGOT PASSWORD SCREEN ---
if not st.session_state.user:
    st.markdown("<h2 style='text-align: center;'>🩺 Hasta Takip Sistemi</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_forgot = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol", "🔒 Şifremi Unuttum"])
        
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

        with tab_forgot:
            with st.form("forgot_form"):
                f_email = st.text_input("Kayıtlı E-posta Adresiniz")
                f_submit = st.form_submit_button("Şifremi E-posta ile Gönder", use_container_width=True)
                if f_submit:
                    if f_email:
                        reset_password(f_email)
                    else:
                        st.warning("Lütfen e-posta adresinizi girin.")
    st.stop()

# --- LOGGED IN USER CONTEXT ---
user_id = st.session_state.user.id
user_email = st.session_state.user.email

# --- SIDEBAR NAVIGATION ---
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
# --- YENİ MUAYENE EKRANI VE ANATOMİK DİŞ ŞEMASI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_muayene":
    st.title("🦷 Yeni Muayene ve Tedavi Planı")

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
                        supabase.table("hastalar").insert({
                            "ad_soyad": yeni_h_ad,
                            "telefon": yeni_h_tel,
                            "kullanici_id": user_id,
                            "kayit_tarihi": datetime.datetime.now().isoformat()
                        }).execute()
                        st.success("Yeni hasta oluşturuldu! Sayfa yenileniyor.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Ad ve telefon zorunludur.")
    else:
        for h in hastalar_res:
            if f"{h['ad_soyad']} ({h['telefon']})" == secilen_hasta_secim:
                hedef_hasta_id = h['id']
                break

    muayene_tarihi = st.date_input("Muayene Tarihi", datetime.date.today())
    st.markdown("---")

    # --- ANATOMİK DİŞ ŞEMASI (GERÇEKÇİ DİŞ GÖRSELLERİ İLE) ---
    st.markdown("### 🦷 Diş Şeması (Kalıcı Dişler)")
    st.info("Üst ve alt çene kalıcı diş şeması[cite: 3, 5]. İşlem yapmak istediğiniz dişe tıklayın.")

    ust_disler = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"]
    alt_disler = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"]

    st.markdown("#### **HASTANIN SAĞI ------------------------ ÜST ÇENE ------------------------ HASTANIN SOLU**[cite: 3, 5]")
    cols_ust = st.columns(16)
    for idx, d_no in enumerate(ust_disler):
        is_secili = d_no in st.session_state.dis_islemleri_gecici and len(st.session_state.dis_islemleri_gecici[d_no]["islemler"]) > 0
        kutu_durum = "🟦" if is_secili else "⬜"
        # Gerçekçi diş görsel simgesi ve altında kutucuk
        btn_label = f"🦷\n{d_no}\n{kutu_durum}"
        if cols_ust[idx].button(btn_label, key=f"ust_d_{d_no}", use_container_width=True):
            st.session_state.aktif_modal_dis = d_no

    st.markdown("#### **HASTANIN SAĞI ------------------------ ALT ÇENE ------------------------ HASTANIN SOLU**[cite: 3, 5]")
    cols_alt = st.columns(16)
    for idx, d_no in enumerate(alt_disler):
        is_secili = d_no in st.session_state.dis_islemleri_gecici and len(st.session_state.dis_islemleri_gecici[d_no]["islemler"]) > 0
        kutu_durum = "🟦" if is_secili else "⬜"
        btn_label = f"🦷\n{d_no}\n{kutu_durum}"
        if cols_alt[idx].button(btn_label, key=f"alt_d_{d_no}", use_container_width=True):
            st.session_state.aktif_modal_dis = d_no

    if st.session_state.aktif_modal_dis:
        aktif_d = st.session_state.aktif_modal_dis
        st.markdown(f"---")
        st.markdown(f"### ⚙️ Seçilen Diş: **{aktif_d} Nolu Diş** İşlem Tanımlama")
        
        try:
            tur_data = supabase.table("islem_turleri").select("tur_adi").execute().data
            tum_islemler = [t["tur_adi"] for t in tur_data] if tur_data else ["Dolgu", "Kanal", "Çekim", "Kron", "İmplant"]
        except Exception:
            tum_islemler = ["Dolgu", "Kanal", "Çekim", "Kron", "İmplant"]

        with st.form(key=f"dis_form_{aktif_d}"):
            st.write("Bu diş için yapılacak işlemleri seçin (Birden fazla seçilebilir):")
            secilen_islemler = []
            for islem_adi in tum_islemler:
                if st.checkbox(islem_adi, key=f"chk_{aktif_d}_{islem_adi}"):
                    secilen_islemler.append(islem_adi)

            islem_metin_kutu = st.text_input("Diş Notu / Açıklama", key=f"txt_{aktif_d}")
            ileri_tarih = st.date_input("İleriye Yönelik İşlem Tarihi", datetime.date.today(), key=f"date_{aktif_d}")

            col_m1, col_m2 = st.columns(2)
            kaydet_dis = col_m1.form_submit_button("💾 Diş İşlemini Kaydet", use_container_width=True)
            kapat_dis = col_m2.form_submit_button("✖️ Kapat / Vazgeç", use_container_width=True)

            if kaydet_dis:
                st.session_state.dis_islemleri_gecici[aktif_d] = {
                    "islemler": secilen_islemler,
                    "not": islem_metin_kutu,
                    "tarih": ileri_tarih.isoformat()
                }
                st.success(f"{aktif_d} nolu diş planı güncellendi.")
                st.session_state.aktif_modal_dis = None
                st.rerun()

            if kapat_dis:
                st.session_state.aktif_modal_dis = None
                st.rerun()

    if st.session_state.dis_islemleri_gecici:
        st.write("📋 **Planlanan Diş İşlemleri Özeti:**")
        for d_no, d_bilgi in st.session_state.dis_islemleri_gecici.items():
            st.write(f"- **Diş {d_no}:** {', '.join(d_bilgi['islemler'])} | Tarih: {d_bilgi['tarih']} | Not: {d_bilgi['not']}")

    st.markdown("---")

    st.subheader("📋 Hasta Değerlendirme Formu")
    try:
        sorular_res = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).order("id").execute().data
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
    st.subheader("📝 Genel Notlar ve Görseller")
    muayene_genel_not = st.text_area("Muayene Notu / Açıklama")
    muayene_fotolar = st.file_uploader("Görsel Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="muayene_foto_yukle")

    if st.button("💾 Muayeneyi Tamamen Kaydet", use_container_width=True):
        if not hedef_hasta_id:
            st.warning("Lütfen geçerli bir hasta seçin.")
        else:
            try:
                foto_url_listesi = []
                if muayene_fotolar:
                    for foto in muayene_fotolar:
                        dosya_adi = f"muayene_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.getvalue())
                        url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                        foto_url_listesi.append(url)

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
        st.warning("Henüz kayıtlı hastanız bulunmuyor.")
    else:
        hasta_dict = {f"{h['ad_soyad']} ({h['telefon']})": h['id'] for h in hastalar_res}
        secilen_label = st.selectbox("İşlem Yapılacak Hastayı Seçin *", list(hasta_dict.keys()))
        secilen_hasta_id = hasta_dict[secilen_label]

        try:
            tur_data = supabase.table("islem_turleri").select("tur_adi").execute().data
            islem_turleri_listesi = [item["tur_adi"] for item in tur_data] if tur_data else ["Muayene", "Dolgu", "Çekim"]
        except Exception:
            islem_turleri_listesi = ["Muayene", "Dolgu", "Çekim"]

        islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
        islem_turu = st.selectbox("İşlem Türü", islem_turleri_listesi)
        hekim_notu = st.text_area("Hekim Notu / Açıklama")

        if st.button("💾 İşlemi Kaydet", use_container_width=True):
            try:
                supabase.table("islemler").insert({
                    "hasta_id": secilen_hasta_id,
                    "islem_tarihi": islem_tarihi.isoformat(),
                    "islem_turu": islem_turu,
                    "hekim_notu": hekim_notu,
                    "kullanici_id": user_id
                }).execute()
                st.toast("✅ İşlem kaydedildi!")
                st.session_state.secili_hasta_id = secilen_hasta_id
                st.session_state.sayfa = "hasta_detay"
                st.rerun()
            except Exception as ex:
                st.error(f"Hata: {ex}")

# ==============================================================================
# --- SAYFA 4: HASTA DETAY & İŞLEM GEÇMİŞİ (DETAYLI GÖRÜNÜM) ---
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
    except Exception:
        hasta = None

    if hasta:
        col_foto, col_info, col_del = st.columns([1, 3, 1])
        with col_foto:
            if hasta.get("foto_url"):
                st.image(hasta["foto_url"], width=120)
            else:
                st.markdown("👤")
        with col_info:
            st.title(hasta.get("ad_soyad"))
            st.write(f"📞 **Telefon:** {hasta.get('telefon', '-')}")
        with col_del:
            if st.button("🗑️ Hastayı Sil", type="primary", use_container_width=True):
                supabase.table("hastalar").delete().eq("id", hasta_id).execute()
                st.session_state.sayfa = "hasta_listesi"
                st.rerun()

        st.markdown("---")
        st.subheader("📜 İşlem ve Muayene Geçmişi")
        try:
            islemler = supabase.table("islemler").select("*").eq("hasta_id", hasta_id).order("islem_tarihi", desc=True).execute().data
        except Exception:
            islemler = []

        if not islemler:
            st.info("Bu hastaya ait işlem geçmişi bulunmuyor.")
        else:
            for islem in islemler:
                with st.expander(f"🗓️ {islem.get('islem_tarihi')} - {islem.get('islem_turu')}"):
                    notlar_ham = islem.get('hekim_notu', '')
                    
                    genel_not_goster = notlar_ham
                    dis_plani_data = {}
                    form_cevaplari_data = {}
                    
                    try:
                        if "[Diş Planı]:" in notlar_ham:
                            parcalar = notlar_ham.split("[Diş Planı]:")
                            genel_not_goster = parcalar[0].replace("[Muayene Notu]:", "").strip()
                            kalan = parcalar[1]
                            if "[Form Cevapları]:" in kalan:
                                p2 = kalan.split("[Form Cevapları]:")
                                dis_plani_str = p2[0].strip()
                                form_str = p2[1].strip()
                                dis_plani_data = json.loads(dis_plani_str)
                                form_cevaplari_data = json.loads(form_str)
                    except Exception:
                        pass

                    st.markdown("### 📝 Muayene Notu / Açıklama")
                    st.write(genel_not_goster if genel_not_goster else "-")

                    st.markdown("### 🦷 Kayıtlı Diş Şeması Durumu")
                    ust_disler = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"]
                    alt_disler = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"]

                    st.markdown("**ÜST ÇENE**[cite: 3, 5]")
                    cols_ust = st.columns(16)
                    for idx, d_no in enumerate(ust_disler):
                        is_secili = d_no in dis_plani_data and len(dis_plani_data[d_no].get("islemler", [])) > 0
                        kutu = "🟦" if is_secili else "⬜"
                        cols_ust[idx].markdown(f"<div style='text-align:center;'>🦷<br>{d_no}<br>{kutu}</div>", unsafe_allow_html=True)

                    st.markdown("**ALT ÇENE**[cite: 3, 5]")
                    cols_alt = st.columns(16)
                    for idx, d_no in enumerate(alt_disler):
                        is_secili = d_no in dis_plani_data and len(dis_plani_data[d_no].get("islemler", [])) > 0
                        kutu = "🟦" if is_secili else "⬜"
                        cols_alt[idx].markdown(f"<div style='text-align:center;'>🦷<br>{d_no}<br>{kutu}</div>", unsafe_allow_html=True)

                    if dis_plani_data:
                        st.write("---")
                        st.write("**Planlanan Diş İşlemleri Detayları:**")
                        for d_no, d_bilgi in dis_plani_data.items():
                            st.write(f"- **Diş {d_no}:** {', '.join(d_bilgi.get('islemler', []))} | Tarih: {d_bilgi.get('tarih', '-')} | Not: {d_bilgi.get('not', '-')}")

                    if form_cevaplari_data:
                        st.markdown("---")
                        st.markdown("### 📋 Hasta Değerlendirme Formu Yanıtları")
                        for soru, cevap in form_cevaplari_data.items():
                            st.write(f"- **{soru}:** {cevap if cevap else '-'}")

                    foto_raw = islem.get("fotograf_url")
                    if foto_raw:
                        urls = [u.strip() for u in foto_raw.split(",") if u.strip()]
                        if urls:
                            st.markdown("---")
                            st.markdown("### 📸 Yüklenen Görseller / Röntgenler")
                            img_cols = st.columns(min(len(urls), 3))
                            for idx, u in enumerate(urls):
                                with img_cols[idx % 3]:
                                    st.image(u, use_container_width=True)

                    st.markdown("---")
                    if st.button("🗑️ Bu Muayene Kaydını Sil", key=f"sil_isl_{islem['id']}"):
                        supabase.table("islemler").delete().eq("id", islem['id']).execute()
                        st.toast("Muayene kaydı silindi.")
                        st.rerun()

# ==============================================================================
# --- SAYFA 5: AYARLAR SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "ayarlar":
    st.title("⚙️ Ayarlar")

    tab_tur, tab_form_soru, tab_export, tab_account = st.tabs(["🏷️ İşlem Türleri", "📋 Form Soruları", "📊 Excel", "👤 Hesap"])

    with tab_tur:
        st.subheader("İşlem Türü Yönetimi")
        yeni_tur = st.text_input("Tür Adı", placeholder="Örn: Diş Beyazlatma")
        if st.button("Tür Ekle"):
            if yeni_tur:
                supabase.table("islem_turleri").insert({"tur_adi": yeni_tur}).execute()
                st.success("Eklendi.")
                st.rerun()

        try:
            turler = supabase.table("islem_turleri").select("*").execute().data
        except Exception:
            turler = []
        for t in turler:
            col1, col2 = st.columns([4, 1])
            col1.write(t['tur_adi'])
            if col2.button("Sil", key=f"t_sil_{t['id']}"):
                supabase.table("islem_turleri").delete().eq("id", t['id']).execute()
                st.rerun()

    with tab_form_soru:
        st.subheader("Değerlendirme Formu Soruları (Sıralama ve Silme)")
        
        with st.form("yeni_soru_formu"):
            yeni_soru_metni = st.text_input("Yeni Soru Metni")
            if st.form_submit_button("Soru Ekle"):
                if yeni_soru_metni.strip():
                    supabase.table("form_sorulari").insert({
                        "kullanici_id": user_id,
                        "soru_metni": yeni_soru_metni.strip()
                    }).execute()
                    st.success("Soru eklendi.")
                    st.rerun()

        try:
            mevcut_sorular = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).order("id").execute().data
        except Exception:
            mevcut_sorular = []

        if mevcut_sorular:
            for idx, m_soru in enumerate(mevcut_sorular):
                c_s1, c_s2, c_s3, c_s4 = st.columns([1, 4, 1, 1])
                c_s1.write(f"#{idx+1}")
                c_s2.write(m_soru['soru_metni'])
                
                if idx > 0 and c_s3.button("⬆️", key=f"yukari_{m_soru['id']}"):
                    ustteki_soru = mevcut_sorular[idx - 1]
                    try:
                        supabase.table("form_sorulari").update({"soru_metni": "___TEMP___"}).eq("id", ustteki_soru['id']).execute()
                        supabase.table("form_sorulari").update({"soru_metni": ustteki_soru['soru_metni']}).eq("id", m_soru['id']).execute()
                        supabase.table("form_sorulari").update({"soru_metni": m_soru['soru_metni']}).eq("id", ustteki_soru['id']).execute()
                        st.toast("Soru sırası değiştirildi.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Sıralama değiştirilirken hata oluştu: {ex}")

                if c_s4.button("🗑️ Sil", key=f"soru_sil_{m_soru['id']}"):
                    supabase.table("form_sorulari").delete().eq("id", m_soru['id']).execute()
                    st.toast("Soru silindi.")
                    st.rerun()

    with tab_export:
        st.subheader("Verileri İndir")
        if st.button("📥 Excel İndir"):
            h_data = supabase.table("hastalar").select("*").eq("kullanici_id", user_id).execute().data
            if h_data:
                df = pd.DataFrame(h_data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("Dosyayı İndir", data=output.getvalue(), file_name="hastalar.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab_account:
        st.subheader("Oturum")
        st.write(f"E-posta: {user_email}")
        if st.button("Çıkış Yap"):
            logout()
