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
    key = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdWBhYmFzZSIsInJlZiI6InptYW16c21mcHNwZW5oc2xza21xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU4NDU1MTEsImV4cCI6MjEwMTQyMTUxMX0.YYXkpF9F_jk7lGzIOYtB_dOO0IV-NsuCaFUXrvinndY")
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase bağlantı hatası: {e}")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "user" not in st.session_state: st.session_state.user = None
if "sayfa" not in st.session_state: st.session_state.sayfa = "hasta_listesi"
if "secili_hasta_id" not in st.session_state: st.session_state.secili_hasta_id = None
if "aktif_modal_dis" not in st.session_state: st.session_state.aktif_modal_dis = None
if "dis_islemleri_gecici" not in st.session_state: st.session_state.dis_islemleri_gecici = {}
if "yeni_muayene_form_cevaplari" not in st.session_state: st.session_state.yeni_muayene_form_cevaplari = {}

# İşlem Bazlı Renkler
if "islem_renkleri" not in st.session_state:
    st.session_state.islem_renkleri = {
        "Dolgu": "#3b82f6", "Kanal": "#f59e0b", "Çekim": "#ef4444", "Kron": "#8b5cf6", "İmplant": "#10b981"
    }

def get_db_islem_turleri():
    try:
        res = supabase.table("islem_turleri").select("tur_adi").execute().data
        if res:
            return [t["tur_adi"] for t in res]
    except Exception:
        pass
    return list(st.session_state.islem_renkleri.keys())

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
        if res.user: st.success("Kayıt başarılı! Giriş sekmesinden oturum açabilirsiniz.")
        else: st.info("Kayıt oluşturuldu, e-posta doğrulamasını kontrol edin.")
    except Exception as e:
        st.error(f"Kayıt Başarısız: {e}")

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email)
        st.success("Şifre sıfırlama talimatı e-posta adresinize gönderildi.")
    except Exception as e:
        st.error(f"Şifre sıfırlama hatası: {e}")

def logout():
    try: supabase.auth.sign_out()
    except Exception: pass
    st.session_state.user = None
    st.session_state.sayfa = "hasta_listesi"
    st.session_state.secili_hasta_id = None
    st.rerun()

# --- LOGIN & REGISTER SCREEN ---
if not st.session_state.user:
    st.markdown("<h2 style='text-align: center;'>🩺 Hasta Takip Sistemi</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_forgot = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol", "🔒 Şifremi Unuttum"])
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("E-posta Adresi")
                password = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    if email and password: login(email, password)
                    else: st.warning("Lütfen e-posta ve şifrenizi girin.")
        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("E-posta Adresi")
                reg_password = st.text_input("Şifre (En az 6 karakter)", type="password")
                if st.form_submit_button("Hesap Oluştur", use_container_width=True):
                    if reg_email and reg_password: register(reg_email, reg_password)
                    else: st.warning("Lütfen e-posta ve şifrenizi doldurun.")
        with tab_forgot:
            with st.form("forgot_form"):
                f_email = st.text_input("Kayıtlı E-posta Adresiniz")
                if st.form_submit_button("Şifre Gönder", use_container_width=True):
                    if f_email: reset_password(f_email)
    st.stop()

user_id = st.session_state.user.id
user_email = st.session_state.user.email

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🩺 Hasta Takip")
st.sidebar.caption(f"👤 {user_email}")

with st.sidebar.expander("📌 Hızlı Menü & İşlemler", expanded=True):
    if st.button("📋 Hasta Listesi & Arama", use_container_width=True):
        st.session_state.sayfa = "hasta_listesi"
        st.rerun()
    if st.button("👤 Yeni Hasta Kaydı", use_container_width=True):
        st.session_state.sayfa = "yeni_hasta"
        st.rerun()
    if st.button("🦷 Yeni Muayene", use_container_width=True):
        st.session_state.sayfa = "yeni_muayene"
        st.rerun()
    if st.button("💉 Yeni İşlem", use_container_width=True):
        st.session_state.sayfa = "yeni_islem"
        st.rerun()
    if st.button("⚙️ Ayarlar", use_container_width=True):
        st.session_state.sayfa = "ayarlar"
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True): logout()

# --- ANATOMİK DİŞ DİYAGRAMI ---
def get_detailed_anatomical_tooth_svg(dis_no, durumsal_renk="#ffffff", is_upper=True):
    border_color = "#334155"
    d_str = str(dis_no)
    
    if is_upper:
        crown_y, root_y = "45", "12"
        path_d = f"M8,{crown_y} C 2,{root_y} 12,5 15,{root_y} C 18,{root_y} 22,5 25,{root_y} C 28,{root_y} 38,5 32,{crown_y} Z" if d_str in ["18","17","16","26","27","28","48","47","46","36","37","38"] else (f"M10,{crown_y} C 5,{root_y} 15,5 20,{root_y} C 25,5 35,{root_y} 30,{crown_y} Z" if d_str in ["15","14","24","25","45","44","35","34"] else f"M12,{crown_y} C 8,{root_y} 20,2 20,{root_y} C 20,2 32,{root_y} 28,{crown_y} Z")
        rect_w, rect_x, crown_h, label_y, box_y = (28, 6, 32, 93, 82) if d_str in ["18","17","16","26","27","28","48","47","46","36","37","38"] else ((24, 8, 32, 93, 82) if d_str in ["15","14","24","25","45","44","35","34"] else (22, 9, 32, 93, 82))
    else:
        crown_y, root_y = "15", "78"
        path_d = f"M8,{crown_y} C 2,{root_y} 12,5 75,{root_y} C 18,{root_y} 22,5 75,{root_y} C 28,{root_y} 38,5 32,{crown_y} Z" if d_str in ["18","17","16","26","27","28","48","47","46","36","37","38"] else (f"M10,{crown_y} C 5,{root_y} 15,5 70,{root_y} C 25,5 70,{root_y} 30,{crown_y} Z" if d_str in ["15","14","24","25","45","44","35","34"] else f"M12,{crown_y} C 8,{root_y} 20,2 70,{root_y} C 20,2 70,{root_y} 28,{crown_y} Z")
        rect_w, rect_x, crown_h, label_y, box_y = (28, 6, 32, 93, 82) if d_str in ["18","17","16","26","27","28","48","47","46","36","37","38"] else ((24, 8, 32, 93, 82) if d_str in ["15","14","24","25","45","44","35","34"] else (22, 9, 32, 93, 82))

    fill_crown = durumsal_renk if durumsal_renk != "#ffffff" else "#ffffff"
    return f'''
    <svg viewBox="0 0 40 100" width="100%" height="100px" style="background-color: #ffffff; border-radius: 6px; padding: 2px;">
        <path d="{path_d}" fill="url(#rg_{dis_no}_{int(is_upper)})" stroke="{border_color}" stroke-width="1.1"/>
        <rect x="{rect_x}" y="{crown_y}" width="{rect_w}" height="{crown_h}" rx="5" fill="{fill_crown}" stroke="{border_color}" stroke-width="1.3"/>
        <rect x="7" y="{box_y}" width="26" height="15" rx="3" fill="#475569" stroke="#1e293b" stroke-width="0.8"/>
        <text x="20" y="{label_y}" font-size="9" font-family="Arial" font-weight="bold" fill="#ffffff" text-anchor="middle">{dis_no}</text>
        <defs><linearGradient id="rg_{dis_no}_{int(is_upper)}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#fecaca"/><stop offset="100%" stop-color="#ffffff"/></linearGradient></defs>
    </svg>'''

@st.dialog("🦷 Ağız ve Diş Tedavi Planı Şeması", width="large")
def show_tooth_diagram_popup(dis_veri_dict=None):
    if dis_veri_dict is None: dis_veri_dict = st.session_state.dis_islemleri_gecici
    st.markdown("<div style='background-color: #475569; padding: 8px 15px; border-radius: 6px; color: white; font-weight: bold; font-size: 13px; margin-bottom: 10px; display:flex; justify-content:space-between;'><span>Sinüs Lift (Sol)</span><span>Sinüs Lift (Sağ)</span></div>", unsafe_allow_html=True)

    ust_disler = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"]
    alt_disler = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"]

    st.markdown("<p style='font-size:11px; font-weight:bold; color:#64748b;'>ÜST ÇENE</p>", unsafe_allow_html=True)
    cols_ust = st.columns(16)
    for idx, d_no in enumerate(ust_disler):
        color = "#ffffff"
        if d_no in dis_veri_dict:
            for isl in dis_veri_dict[d_no].get("islemler", []):
                if isl in st.session_state.islem_renkleri: color = st.session_state.islem_renkleri[isl]
        cols_ust[idx].markdown(get_detailed_anatomical_tooth_svg(d_no, color, is_upper=True), unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px; font-weight:bold; color:#64748b;'>ALT ÇENE</p>", unsafe_allow_html=True)
    cols_alt = st.columns(16)
    for idx, d_no in enumerate(alt_disler):
        color = "#ffffff"
        if d_no in dis_veri_dict:
            for isl in dis_veri_dict[d_no].get("islemler", []):
                if isl in st.session_state.islem_renkleri: color = st.session_state.islem_renkleri[isl]
        cols_alt[idx].markdown(get_detailed_anatomical_tooth_svg(d_no, color, is_upper=False), unsafe_allow_html=True)

    lejant = '<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 25px; font-weight: bold; font-size: 13px; background-color: #f1f5f9; padding: 10px; border-radius: 8px;">'
    for k, v in st.session_state.islem_renkleri.items(): lejant += f'<div><span style="color: {v}; font-size:16px;">■</span> {k}</div>'
    st.markdown(lejant + '</div>', unsafe_allow_html=True)

# --- METİN VE NOT GİRİŞ POPUP EKRANI ---
@st.dialog("✏️ Metin / Not Düzenleme", width="medium")
def show_input_canvas_popup(field_key, current_text=""):
    yazilan_deger = st.text_area("Açıklama / Not", value=current_text, height=180, key=f"txt_popup_{field_key}")

    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("💾 Kaydet", use_container_width=True, type="primary"):
        st.session_state[f"saved_val_{field_key}"] = yazilan_deger
        st.success("Kaydedildi!")
        st.rerun()
    if col_btn2.button("🗑️ Sil / Sıfırla", use_container_width=True):
        st.session_state[f"saved_val_{field_key}"] = ""
        st.rerun()

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
                    if hasta.get("foto_url"): st.image(hasta["foto_url"], width=60)
                    else: st.markdown("👤")
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
            profil_foto = st.file_uploader("Fotoğraf Seç", type=["jpg", "png", "jpeg"])

        telefon = st.text_input("Telefon Numarası *", placeholder="05XXXXXXXXX")
        if st.form_submit_button("Hastayı Kaydet", use_container_width=True):
            if ad_soyad and telefon:
                try:
                    foto_url = None
                    if profil_foto:
                        dosya_adi = f"p_{int(datetime.datetime.now().timestamp())}.png"
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, profil_foto.getvalue())
                        foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                    supabase.table("hastalar").insert({
                        "ad_soyad": ad_soyad, "cinsiyet": cinsiyet, "dogum_tarihi": dogum_tarihi.isoformat(),
                        "telefon": telefon, "foto_url": foto_url, "kullanici_id": user_id, "kayit_tarihi": datetime.datetime.now().isoformat()
                    }).execute()
                    st.toast("✅ Hasta kaydedildi!")
                    st.session_state.sayfa = "hasta_listesi"
                    st.rerun()
                except Exception as ex:
                    st.error(f"Hata: {ex}")

# ==============================================================================
# --- SAYFA 3: YENİ MUAYENE VE DİŞ DİYAGRAMI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_muayene":
    st.title("🦷 Diş Tedavi Planlama")

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
                    supabase.table("hastalar").insert({"ad_soyad": yeni_h_ad, "telefon": yeni_h_tel, "kullanici_id": user_id, "kayit_tarihi": datetime.datetime.now().isoformat()}).execute()
                    st.rerun()
    else:
        for h in hastalar_res:
            if f"{h['ad_soyad']} ({h['telefon']})" == secilen_hasta_secim:
                hedef_hasta_id = h['id']
                break

    muayene_tarihi = st.date_input("Muayene Tarihi", datetime.date.today())
    st.markdown("---")

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("⌨️ Diş Seçim Kutucukları")
    with col_t2:
        if st.button("🖼️ Plan Görselini Göster", use_container_width=True, type="primary"):
            show_tooth_diagram_popup()

    ust_disler = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"]
    alt_disler = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"]

    st.markdown("<p style='font-size:12px; font-weight:bold; color:#555;'>Üst Çene</p>", unsafe_allow_html=True)
    cols_ust = st.columns(16)
    for idx, d_no in enumerate(ust_disler):
        is_secili = d_no in st.session_state.dis_islemleri_gecici
        btn_label = f"✓ {d_no}" if is_secili else f"{d_no}"
        if cols_ust[idx].button(btn_label, key=f"btn_u_{d_no}", use_container_width=True):
            st.session_state.aktif_modal_dis = d_no

    st.markdown("<p style='font-size:12px; font-weight:bold; color:#555; margin-top:10px;'>Alt Çene</p>", unsafe_allow_html=True)
    cols_alt = st.columns(16)
    for idx, d_no in enumerate(alt_disler):
        is_secili = d_no in st.session_state.dis_islemleri_gecici
        btn_label = f"✓ {d_no}" if is_secili else f"{d_no}"
        if cols_alt[idx].button(btn_label, key=f"btn_a_{d_no}", use_container_width=True):
            st.session_state.aktif_modal_dis = d_no

    if st.session_state.aktif_modal_dis:
        aktif_d = st.session_state.aktif_modal_dis
        st.markdown(f"---")
        st.markdown(f"### ⚙️ **{aktif_d} Nolu Diş** İşlem Tanımlama Paneli")
        
        tum_islemler = get_db_islem_turleri()
        mevcut_veri = st.session_state.dis_islemleri_gecici.get(aktif_d, {})

        with st.form(key=f"dis_form_{aktif_d}"):
            st.write("Yapılacak İşlemler:")
            secilen_islemler = []
            for islem_adi in tum_islemler:
                varsayilan = islem_adi in mevcud_islemler if (mevcud_islemler := mevcut_veri.get("islemler", [])) else False
                if st.checkbox(islem_adi, value=varsayilan, key=f"chk_{aktif_d}_{islem_adi}"):
                    secilen_islemler.append(islem_adi)

            islem_metin_kutu = st.text_input("Diş Notu / Açıklama", value=mevcut_veri.get("not", ""), key=f"txt_{aktif_d}")

            col_m1, col_m2 = st.columns(2)
            if col_m1.form_submit_button("💾 Kaydet", use_container_width=True):
                st.session_state.dis_islemleri_gecici[aktif_d] = {"islemler": secilen_islemler, "not": islem_metin_kutu}
                st.session_state.aktif_modal_dis = None
                st.rerun()
            if col_m2.form_submit_button("✖️ Kapat", use_container_width=True):
                st.session_state.aktif_modal_dis = None
                st.rerun()

    if st.session_state.dis_islemleri_gecici:
        st.write("📋 **Planlanan Tedavi Listesi:**")
        for d_no, d_bilgi in st.session_state.dis_islemleri_gecici.items():
            st.write(f"- **Diş {d_no}**: {', '.join(d_bilgi.get('islemler', []))} | Not: {d_bilgi.get('not', '-')}")

    st.markdown("---")
    st.subheader("📋 Hasta Değerlendirme Formu")

    try:
        sorular_res = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).order("id").execute().data
    except Exception:
        sorular_res = []

    if sorular_res:
        for s in sorular_res:
            s_id = s["id"]
            s_metin = s["soru_metni"]
            f_key = f"form_soru_{s_id}"
            
            default_val = st.session_state.get(f"saved_val_{f_key}", st.session_state.yeni_muayene_form_cevaplari.get(s_metin, ""))
            
            c_f1, c_f2 = st.columns([5, 1])
            cevap = c_f1.text_input(f"❓ {s_metin}", value=default_val, key=f_key)
            st.session_state.yeni_muayene_form_cevaplari[s_metin] = cevap
            
            if c_f2.button("✏️", key=f"btn_popup_{f_key}", use_container_width=True):
                show_input_canvas_popup(f_key, cevap)

    st.markdown("---")
    st.subheader("📝 Genel Notlar ve Görseller")
    
    genel_not_key = "muayene_genel_not_field"
    default_genel_not = st.session_state.get(f"saved_val_{genel_not_key}", "")
    
    c_n1, c_n2 = st.columns([5, 1])
    muayene_genel_not = c_n1.text_area("Muayene Notu / Açıklama", value=default_genel_not, key=genel_not_key)
    if c_n2.button("✏️", key=f"btn_popup_{genel_not_key}", use_container_width=True):
        show_input_canvas_popup(genel_not_key, muayene_genel_not)

    muayene_fotolar = st.file_uploader("Görsel Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

    if st.button("💾 Planı ve Muayeneyi Kaydet", use_container_width=True, type="primary"):
        if not hedef_hasta_id:
            st.warning("Lütfen geçerli bir hasta seçin.")
        else:
            try:
                foto_url_listesi = []
                if muayene_fotolar:
                    for foto in muayene_fotolar:
                        dosya_adi = f"muayene_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.getvalue())
                        foto_url_listesi.append(supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi))

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
                st.error(f"Hata: {ex}")

# ==============================================================================
# --- SAYFA 4: YENİ İŞLEM SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_islem":
    st.title("💉 Yeni İşlem Ekle")
    try:
        hastalar_res = supabase.table("hastalar").select("id, ad_soyad, telefon").eq("kullanici_id", user_id).order("ad_soyad").execute().data
    except Exception:
        hastalar_res = []

    if not hastalar_res:
        st.warning("Kayıtlı hastanız bulunmuyor.")
    else:
        hasta_dict = {f"{h['ad_soyad']} ({h['telefon']})": h['id'] for h in hastalar_res}
        secilen_label = st.selectbox("İşlem Yapılacak Hastayı Seçin *", list(hasta_dict.keys()))
        secilen_hasta_id = hasta_dict[secilen_label]

        islem_turleri_listesi = get_db_islem_turleri()
        islem_tarihi = st.date_input("İşlem Tarihi", datetime.date.today())
        islem_turu = st.selectbox("İşlem Türü", islem_turleri_listesi)
        hekim_notu = st.text_area("Hekim Notu / Açıklama")

        if st.button("💾 İşlemi Kaydet", use_container_width=True):
            supabase.table("islemler").insert({
                "hasta_id": secilen_hasta_id, "islem_tarihi": islem_tarihi.isoformat(),
                "islem_turu": islem_turu, "hekim_notu": hekim_notu, "kullanici_id": user_id
            }).execute()
            st.toast("✅ İşlem eklendi.")
            st.session_state.secili_hasta_id = secilen_hasta_id
            st.session_state.sayfa = "hasta_detay"
            st.rerun()

# ==============================================================================
# --- SAYFA 5: HASTA DETAY & İŞLEM GEÇMİŞİ ---
# ==============================================================================
elif st.session_state.sayfa == "hasta_detay":
    hasta_id = st.session_state.secili_hasta_id
    if not hasta_id:
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
            if hasta.get("foto_url"): st.image(hasta["foto_url"], width=120)
            else: st.markdown("👤")
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
                                dis_plani_data = json.loads(p2[0].strip())
                                form_cevaplari_data = json.loads(p2[1].strip())
                    except Exception:
                        pass

                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown("### 📝 Muayene Notu / Açıklama")
                        st.write(genel_not_goster if genel_not_goster else "-")
                    with col_h2:
                        if dis_plani_data:
                            if st.button("🖼️ Plan Görselini Göster", key=f"btn_gorsel_{islem['id']}", use_container_width=True, type="primary"):
                                show_tooth_diagram_popup(dis_plani_data)

                    if dis_plani_data:
                        st.write("---")
                        st.write("**Planlanan Diş İşlemleri Detayları:**")
                        for d_no, d_bilgi in dis_plani_data.items():
                            st.write(f"- **Diş {d_no}**: {', '.join(d_bilgi.get('islemler', []))} | Not: {d_bilgi.get('not', '-')}")

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
                                with img_cols[idx % 3]: st.image(u, use_container_width=True)

                    st.markdown("---")
                    if st.button("🗑️ Bu Muayene Kaydını Sil", key=f"sil_isl_{islem['id']}"):
                        supabase.table("islemler").delete().eq("id", islem['id']).execute()
                        st.rerun()

# ==============================================================================
# --- SAYFA 6: AYARLAR SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "ayarlar":
    st.title("⚙️ Ayarlar")

    tab_renk, tab_tur, tab_form_soru, tab_export, tab_account = st.tabs(["🎨 İşlem Renkleri", "🏷️ İşlem Türleri", "📋 Form Soruları", "📊 Excel", "👤 Hesap"])

    with tab_renk:
        st.subheader("İşlem Türlerine Göre Diş Şeması Renkleri")
        st.markdown("Veritabanınızdaki işlem türlerine karşılık gelen renkleri belirleyebilirsiniz.")
        
        db_turlar = get_db_islem_turleri()
        for islem_adi in db_turlar:
            mevcut_renk = st.session_state.islem_renkleri.get(islem_adi, "#3b82f6")
            secilen_renk = st.color_picker(f"'{islem_adi}' Rengi", mevcut_renk, key=f"picker_{islem_adi}")
            st.session_state.islem_renkleri[islem_adi] = secilen_renk
        st.success("Renk eşleşmeleri güncel.")

    with tab_tur:
        st.subheader("İşlem Türü Yönetimi")
        yeni_tur = st.text_input("Yeni İşlem Türü Adı", placeholder="Örn: Diş Beyazlatma")
        if st.button("İşlem Türü Ekle"):
            if yeni_tur:
                try:
                    supabase.table("islem_turleri").insert({"tur_adi": yeni_tur}).execute()
                    st.success("İşlem türü eklendi.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Hata: {ex}")

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
        st.subheader("Değerlendirme Formu Soruları")
        with st.form("yeni_soru_formu"):
            yeni_soru_metni = st.text_input("Yeni Soru Metni")
            if st.form_submit_button("Soru Ekle"):
                if yeni_soru_metni.strip():
                    supabase.table("form_sorulari").insert({"kullanici_id": user_id, "soru_metni": yeni_soru_metni.strip()}).execute()
                    st.rerun()

        try:
            mevcut_sorular = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).order("id").execute().data
        except Exception:
            mevcut_sorular = []

        if mevcut_sorular:
            for idx, m_soru in enumerate(mevcut_sorular):
                c_s1, c_s2, c_s3 = st.columns([1, 5, 1])
                c_s1.write(f"#{idx+1}")
                c_s2.write(m_soru['soru_metni'])
                if c_s3.button("🗑️ Sil", key=f"soru_sil_{m_soru['id']}"):
                    supabase.table("form_sorulari").delete().eq("id", m_soru['id']).execute()
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
