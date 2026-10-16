import streamlit as st
import datetime
import pandas as pd
import io
import json
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas

try:
    from PIL import Image
except ImportError:
    pass

# --- PAGE CONFIGURATION & SIDEBAR AUTO-CLOSE SCRIPT ---
st.set_page_config(
    page_title="Hasta Takip Sistemi",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def close_sidebar_js():
    st.components.v1.html(
        """
        <script>
            var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
            var closeBtn = window.parent.document.querySelector('button[data-testid="stSidebarCollapseButton"]');
            if (closeBtn && sidebar) {
                closeBtn.click();
            }
        </script>
        """,
        height=0,
    )

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "https://zmamzsmfpspenhslskmq.supabase.co")
    # Public Anon Key kullanımı (RLS ile tam uyumlu)
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
if "show_eval_form" not in st.session_state: st.session_state.show_eval_form = False
if "duzenlenen_muayene_id" not in st.session_state: st.session_state.duzenlenen_muayene_id = None
if "aktif_canvas_modal_key" not in st.session_state: st.session_state.aktif_canvas_modal_key = None

# İşlem Bazlı Renkler
if "islem_renkleri" not in st.session_state:
    st.session_state.islem_renkleri = {
        "Dolgu": "#3b82f6", "Kanal": "#f59e0b", "Çekim": "#ef4444", "Kron": "#8b5cf6", "İmplant": "#10b981"
    }

def get_db_islem_turleri():
    try:
        res = supabase.table("islem_turleri").select("tur_adi").execute().data
        if res: return [t["tur_adi"] for t in res]
    except Exception: pass
    return list(st.session_state.islem_renkleri.keys())

# --- AUTHENTICATION FUNCTIONS ---
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.rerun()
    except Exception as e: st.error(f"Giriş Başarısız: {e}")

def register(email, password):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user: st.success("Kayıt başarılı! Giriş sekmesinden oturum açabilirsiniz.")
    except Exception as e: st.error(f"Kayıt Hatası: {e}")

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email)
        st.success("Şifre sıfırlama talimatı e-posta adresinize gönderildi.")
    except Exception as e: st.error(f"Hata: {e}")

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

def yonlendir(sayfa_adi):
    st.session_state.sayfa = sayfa_adi
    st.session_state.close_sidebar_flag = True

if st.session_state.get("close_sidebar_flag", False):
    st.session_state.close_sidebar_flag = False
    close_sidebar_js()

with st.sidebar.expander("📌 Hızlı Menü & İşlemler", expanded=True):
    if st.button("📋 Hasta Listesi & Arama", use_container_width=True, key="nav_hl"): 
        yonlendir("hasta_listesi")
        st.rerun()
    if st.button("👤 Yeni Hasta Kaydı", use_container_width=True, key="nav_yh"): 
        yonlendir("yeni_hasta")
        st.rerun()
    if st.button("🦷 Yeni Muayene", use_container_width=True, key="nav_ym"): 
        st.session_state.duzenlenen_muayene_id = None
        yonlendir("yeni_muayene")
        st.rerun()
    if st.button("💉 Yeni İşlem", use_container_width=True, key="nav_yi"): 
        yonlendir("yeni_islem")
        st.rerun()
    if st.button("⚙️ Ayarlar", use_container_width=True, key="nav_ay"): 
        yonlendir("ayarlar")
        st.rerun()
    if st.button("ℹ️ Hakkında", use_container_width=True, key="nav_hk"): 
        yonlendir("hakkinda")
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True, key="nav_exit"): 
    logout()

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
        path_d = f"M8,{crown_y} C 2,{root_y} 12,5 75,{root_y} C 18,{root_y} 22,5 75,{root_y} C 28,{root_y} 38,5 32,{crown_y} Z" if d_str in ["18","17","16","26","27","28","48","47","46","36","37","38"] else (f"M10,{crown_y} C 5,{root_y} 15,5 70,{root_y} C 25,5 70,{root_y} 30,{crown_y} Z" if d_str in ["15","14","24","25","45","44","35","34"] else f"M12,{crown_y} C 8,{root_y} 20,2 70,{root_y} 20,2 70,{root_y} 28,{crown_y} Z")
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

    lejant = '<div style="display: flex; flex-wrap: wrap; justify- content: center; gap: 20px; margin-top: 25px; font-weight: bold; font-size: 13px; background-color: #f1f5f9; padding: 10px; border-radius: 8px;">'
    for k, v in st.session_state.islem_renkleri.items(): lejant += f'<div><span style="color: {v}; font-size:16px;">■</span> {k}</div>'
    st.markdown(lejant + '</div>', unsafe_allow_html=True)

# --- BÜYÜK BOYUTLU POP-UP ÇİZİM MODALİ ---
@st.dialog("✏️ El Yazısı / Çizim Ekle", width="large")
def show_input_canvas_popup(field_key):
    if f"sw_{field_key}" not in st.session_state: st.session_state[f"sw_{field_key}"] = 3
    if f"cp_{field_key}" not in st.session_state: st.session_state[f"cp_{field_key}"] = "#000000"
    if f"silgi_aktif_{field_key}" not in st.session_state: st.session_state[f"silgi_aktif_{field_key}"] = False

    c_sol, c_sag = st.columns([5, 1])

    with c_sol:
        c_color = "#ffffff" if st.session_state[f"silgi_aktif_{field_key}"] else st.session_state[f"cp_{field_key}"]
        c_width = st.session_state[f"sw_{field_key}"]
        initial_drawing = st.session_state.get(f"canvas_data_{field_key}", None)

        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=c_width,
            stroke_color=c_color,
            background_color="#ffffff",
            height=480,
            width=700,
            drawing_mode="freedraw",
            initial_drawing=initial_drawing,
            key=f"canvas_obj_{field_key}"
        )

    with c_sag:
        st.markdown("<div style='font-weight:bold; margin-bottom:5px;'>Araçlar</div>", unsafe_allow_html=True)
        
        kalinlik_val = st.slider("Kalınlık", 1, 20, st.session_state[f"sw_{field_key}"], key=f"sl_{field_key}")
        if kalinlik_val != st.session_state[f"sw_{field_key}"]:
            st.session_state[f"sw_{field_key}"] = kalinlik_val

        secilen_renk = st.color_picker("Renk", st.session_state[f"cp_{field_key}"], key=f"cp_picker_{field_key}")
        if secilen_renk != st.session_state[f"cp_{field_key}"]:
            st.session_state[f"cp_{field_key}"] = secilen_renk
            st.session_state[f"silgi_aktif_{field_key}"] = False

        silgi_durumu = st.checkbox("🧹 Silgi Modu", value=st.session_state[f"silgi_aktif_{field_key}"], key=f"chk_silgi_{field_key}")
        if silgi_durumu != st.session_state[f"silgi_aktif_{field_key}"]:
            st.session_state[f"silgi_aktif_{field_key}"] = silgi_durumu

    st.markdown("---")
    col_b1, col_b2 = st.columns(2)
    
    if col_b1.button("💾 Çizimi Kaydet ve Kapat", key=f"btn_save_{field_key}", use_container_width=True, type="primary"):
        has_content = False
        if canvas_result.json_data is not None:
            st.session_state[f"canvas_data_{field_key}"] = canvas_result.json_data
            if len(canvas_result.json_data.get("objects", [])) > 0:
                has_content = True

        if has_content:
            try:
                img_data_arr = getattr(canvas_result, "image_data", None)
                if img_data_arr is not None:
                    img_pil = Image.fromarray(img_data_arr.astype('uint8'), 'RGBA')
                    buffered = io.BytesIO()
                    img_pil.save(buffered, format="PNG")
                    img_bytes = buffered.getvalue()
                    
                    dosya_adi = f"draw_{int(datetime.datetime.now().timestamp())}_{field_key}.png"
                    supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, img_bytes)
                    img_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)
                    st.session_state[f"saved_img_{field_key}"] = img_url
            except Exception:
                pass

        st.session_state.aktif_canvas_modal_key = None
        st.rerun()

    if col_b2.button("🗑️ Temizle", key=f"btn_clear_{field_key}", use_container_width=True):
        st.session_state[f"saved_img_{field_key}"] = ""
        st.session_state[f"canvas_data_{field_key}"] = None
        st.session_state.aktif_canvas_modal_key = None
        st.rerun()

# --- SARI NOKTA İNDİKATÖRLÜ POP-UP ÇİZİM BUTONU ---
def render_canvas_trigger_button(field_key, button_label="✏️ Elle Çizim / Not Ekle"):
    dolu_mu = bool(st.session_state.get(f"saved_img_{field_key}", ""))
    label = f"🟡 {button_label}" if dolu_mu else button_label
    if st.button(label, key=f"btn_trig_{field_key}", use_container_width=True):
        st.session_state.aktif_canvas_modal_key = field_key
        st.rerun()

# GEÇERLİ AKTİF ÇİZİM MODALİ VARSA GÖSTER
if st.session_state.aktif_canvas_modal_key:
    show_input_canvas_popup(st.session_state.aktif_canvas_modal_key)

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
    except Exception:
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
                foto_url = None
                if profil_foto:
                    dosya_adi = f"p_{int(datetime.datetime.now().timestamp())}.png"
                    supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, profil_foto.getvalue())
                    foto_url = supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi)

                supabase.table("hastalar").insert({
                    "ad_soyad": ad_soyad, "cinsiyet": cinsiyet, "dogum_tarihi": dogum_tarihi.isoformat(),
                    "telefon": telefon, "foto_url": foto_url, "kullanici_id": user_id, "kayit_tarihi": datetime.datetime.now().isoformat()
                }).execute()
                st.session_state.sayfa = "hasta_listesi"
                st.rerun()

# ==============================================================================
# --- SAYFA 3: YENİ MUAYENE / DÜZENLEME VE DİŞ DİYAGRAMI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_muayene":
    is_edit_mode = st.session_state.duzenlenen_muayene_id is not None
    st.title("✏️ Muayene Düzenleme" if is_edit_mode else "🦷 Diş Tedavi Planlama")

    try:
        hastalar_res = supabase.table("hastalar").select("id, ad_soyad, telefon").eq("kullanici_id", user_id).order("ad_soyad").execute().data
    except Exception:
        hastalar_res = []

    hasta_secenekleri = ["+ Yeni Hasta Ekle"] + [f"{h['ad_soyad']} ({h['telefon']})" for h in hastalar_res]
    
    def_hasta_index = 0
    if st.session_state.secili_hasta_id:
        for idx, h in enumerate(hastalar_res):
            if h['id'] == st.session_state.secili_hasta_id:
                def_hasta_index = idx + 1
                break

    secilen_hasta_secim = st.selectbox("Hasta Seçin veya Yeni Oluşturun *", hasta_secenekleri, index=def_hasta_index)

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
    
    # HASTA DEĞERLENDİRME FORMU BUTONU
    col_f_baslik, col_f_btn = st.columns([3, 1])
    with col_f_baslik:
        st.subheader("📋 Hasta Değerlendirme Formu")
    with col_f_btn:
        if st.button("📑 Formu Aç / Kapat", key="btn_ac_eval_form", use_container_width=True, type="primary"):
            if hedef_hasta_id:
                st.session_state.show_eval_form = not st.session_state.get("show_eval_form", False)
                st.rerun()
            else:
                st.warning("Lütfen önce yukarıdan bir hasta seçin!")

    # HASTA DEĞERLENDİRME FORMU KAPSAYICISI
    if st.session_state.get("show_eval_form", False) and hedef_hasta_id:
        with st.container(border=True):
            st.markdown("### 📋 Hasta Değerlendirme Formu")
            
            try:
                sorular_res = supabase.table("form_sorulari").select("*").eq("kullanici_id", user_id).order("id").execute().data
            except Exception:
                sorular_res = []

            if not sorular_res:
                st.info("Henüz form sorusu tanımlanmamış. Lütfen Ayarlar sayfasından soru ekleyin.")
            else:
                form_cevaplari = st.session_state.get(f"form_data_{hedef_hasta_id}", {})
                
                with st.container(height=420):
                    for s in sorular_res:
                        s_id = s["id"]
                        s_metin = s["soru_metni"]
                        f_key = f"form_f_{hedef_hasta_id}_{s_id}"
                        
                        def_val = form_cevaplari.get(s_metin, "")
                        col_s1, col_s2 = st.columns([4, 1])
                        cevap = col_s1.text_input(s_metin, value=def_val, key=f"inp_{f_key}")
                        form_cevaplari[s_metin] = cevap
                        
                        with col_s2:
                            st.write("")
                            st.write("")
                            render_canvas_trigger_button(f_key, "✏️ Çizim")

                        img_goster = st.session_state.get(f"saved_img_{f_key}", "")
                        if img_goster:
                            st.image(img_goster, width=220, caption="Kaydedilen Çizim")
                        st.markdown("---")

                if st.button("💾 Formu Kaydet ve Kapat", use_container_width=True, type="primary"):
                    st.session_state[f"form_data_{hedef_hasta_id}"] = form_cevaplari
                    st.session_state.show_eval_form = False
                    st.success("Form başarıyla kaydedildi.")
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 Genel Notlar ve Görseller")
    
    genel_not_key = "muayene_genel_not_field"
    col_gn1, col_gn2 = st.columns([4, 1])
    varsayilan_not_val = st.session_state.get("gecici_muayene_notu", "")
    muayene_genel_not = col_gn1.text_area("Muayene Notu / Açıklama", value=varsayilan_not_val, key=genel_not_key)
    
    with col_gn2:
        st.write("")
        st.write("")
        render_canvas_trigger_button(genel_not_key, "✏️ Çizim")

    genel_cizim_url = st.session_state.get(f"saved_img_{genel_not_key}", "")
    if genel_cizim_url:
        st.image(genel_cizim_url, caption="Kaydedilen Çizim Görseli", width=300)

    muayene_fotolar = st.file_uploader("Görsel / Röntgen Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

    if st.button("💾 Planı/Muayeneyi Kaydet", use_container_width=True, type="primary"):
        if not hedef_hasta_id:
            st.warning("Lütfen geçerli bir hasta seçin.")
        else:
            try:
                foto_url_listesi = st.session_state.get("gecici_fotograflar", [])
                if muayene_fotolar:
                    for foto in muayene_fotolar:
                        dosya_adi = f"muayene_{int(datetime.datetime.now().timestamp())}_{user_id[:4]}.png"
                        supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.getvalue())
                        foto_url_listesi.append(supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi))
                
                if genel_cizim_url and genel_cizim_url not in foto_url_listesi:
                    foto_url_listesi.append(genel_cizim_url)

                form_data_to_save = st.session_state.get(f"form_data_{hedef_hasta_id}", {})

                muayene_veri = {
                    "hasta_id": hedef_hasta_id,
                    "kullanici_id": user_id,
                    "islem_tarihi": muayene_tarihi.isoformat(),
                    "islem_turu": "Detaylı Muayene",
                    "hekim_notu": f"[Muayene Notu]: {muayene_genel_not}\n[Diş Planı]: {json.dumps(st.session_state.dis_islemleri_gecici, ensure_ascii=False)}\n[Form Cevapları]: {json.dumps(form_data_to_save, ensure_ascii=False)}",
                    "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None
                }

                if is_edit_mode:
                    supabase.table("islemler").update(muayene_veri).eq("id", st.session_state.duzenlenen_muayene_id).execute()
                    st.toast("✅ Muayene güncellemesi kaydedildi!")
                else:
                    supabase.table("islemler").insert(muayene_veri).execute()
                    st.toast("✅ Muayene başarıyla kaydedildi!")

                st.session_state.dis_islemleri_gecici = {}
                st.session_state.gecici_muayene_notu = ""
                st.session_state.gecici_fotograflar = []
                st.session_state.duzenlenen_muayene_id = None
                st.session_state.secili_hasta_id = hedef_hasta_id
                st.session_state.sayfa = "hasta_detay"
                st.rerun()
            except Exception as ex:
                st.error(f"Hata: {ex}")

# ==============================================================================
# --- SAYFA 4: YENİ İŞLEM SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "yeni_islem":
    st.title("💉 Yeni İşlem")
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
        
        islem_not_key = "yeni_islem_cizim_field"
        col_is1, col_is2 = st.columns([4, 1])
        hekim_notu = col_is1.text_area("Hekim Notu / Açıklama")
        
        with col_is2:
            st.write("")
            st.write("")
            render_canvas_trigger_button(islem_not_key, "✏️ Elle Çizim / Not")

        islem_cizim_url = st.session_state.get(f"saved_img_{islem_not_key}", "")
        if islem_cizim_url:
            st.image(islem_cizim_url, caption="Kaydedilen Çizim Görseli", width=280)

        islem_fotolar = st.file_uploader("Görsel / Röntgen Ekle", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        if st.button("💾 İşlemi Kaydet", use_container_width=True, type="primary"):
            foto_url_listesi = []
            if islem_fotolar:
                for foto in islem_fotolar:
                    dosya_adi = f"islem_{int(datetime.datetime.now().timestamp())}.png"
                    supabase.storage.from_("hasta-fotograflari").upload(dosya_adi, foto.getvalue())
                    foto_url_listesi.append(supabase.storage.from_("hasta-fotograflari").get_public_url(dosya_adi))

            if islem_cizim_url and islem_cizim_url not in foto_url_listesi:
                foto_url_listesi.append(islem_cizim_url)

            supabase.table("islemler").insert({
                "hasta_id": secilen_hasta_id, 
                "islem_tarihi": islem_tarihi.isoformat(),
                "islem_turu": islem_turu, 
                "hekim_notu": hekim_notu, 
                "kullanici_id": user_id,
                "fotograf_url": ",".join(foto_url_listesi) if foto_url_listesi else None
            }).execute()
            
            st.session_state[f"saved_img_{islem_not_key}"] = ""
            st.toast("✅ İşlem eklendi.")
            st.session_state.secili_hasta_id = secilen_hasta_id
            st.session_state.sayfa = "hasta_detay"
            st.rerun()

# ==============================================================================
# --- SAYFA 5: HASTA DETAY & İŞLEM GEÇMİŞİ ---
# ==============================================================================
elif st.session_state.sayfa == "hasta_detay":
    if st.button("⬅️ Geri Dön (Hasta Listesi)"):
        st.session_state.sayfa = "hasta_listesi"
        st.rerun()

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
                            if "[Form Cevaplari]:" in kalan:
                                p2 = kalan.split("[Form Cevapları]:")
                                dis_plani_data = json.loads(p2[0].strip())
                                form_cevaplari_data = json.loads(p2[1].strip())
                    except Exception:
                        pass

                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown("### 📝 Not / Açıklama")
                        st.write(genel_not_goster if genel_not_goster else "-")
                    with col_h2:
                        if dis_plani_data:
                            if st.button("🖼️ Plan Görselini Göster", key=f"btn_gorsel_{islem['id']}", use_container_width=True, type="primary"):
                                show_tooth_diagram_popup(dis_plani_data)

                    if form_cevaplari_data:
                        st.markdown("---")
                        st.markdown("### 📋 Değerlendirme Formu Yanıtları")
                        for soru, cevap in form_cevaplari_data.items():
                            st.write(f"- **{soru}:** {cevap if cevap else '-'}")

                    foto_raw = islem.get("fotograf_url")
                    urls = []
                    if foto_raw:
                        urls = [u.strip() for u in foto_raw.split(",") if u.strip()]
                        if urls:
                            st.markdown("---")
                            st.markdown("### 📸 Yüklenen Görseller, Röntgenler ve Çizimler")
                            img_cols = st.columns(min(len(urls), 3))
                            for idx, u in enumerate(urls):
                                with img_cols[idx % 3]: st.image(u, use_container_width=True)

                    st.markdown("---")
                    
                    if st.button("✏️ Bu Muayeneyi Düzenle (Muayene Sayfasında Aç)", key=f"btn_duz_sayfa_{islem['id']}", type="primary"):
                        st.session_state.duzenlenen_muayene_id = islem['id']
                        st.session_state.dis_islemleri_gecici = dis_plani_data
                        st.session_state[f"form_data_{hasta_id}"] = form_cevaplari_data
                        st.session_state.gecici_muayene_notu = genel_not_goster
                        st.session_state.gecici_fotograflar = urls
                        st.session_state.sayfa = "yeni_muayene"
                        st.rerun()

                    st.markdown("---")
                    if st.button("🗑️ Bu Kaydı Sil", key=f"sil_isl_{islem['id']}"):
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
        db_turlar = get_db_islem_turleri()
        for islem_adi in db_turlar:
            mevcut_renk = st.session_state.islem_renkleri.get(islem_adi, "#3b82f6")
            secilen_renk = st.color_picker(f"'{islem_adi}' Rengi", mevcut_renk, key=f"picker_{islem_adi}")
            st.session_state.islem_renkleri[islem_adi] = secilen_renk
        st.success("Renkler güncel.")

    with tab_tur:
        st.subheader("İşlem Türü Yönetimi")
        yeni_tur = st.text_input("Yeni İşlem Türü Adı", placeholder="Örn: Diş Beyazlatma")
        if st.button("İşlem Türü Ekle"):
            if yeni_tur:
                supabase.table("islem_turleri").insert({"tur_adi": yeni_tur}).execute()
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
        st.subheader("Hesap ve Şifre İşlemleri")
        st.write(f"Kayıtlı E-posta: {user_email}")
        
        st.markdown("---")
        st.subheader("🔒 Şifre Değiştir")
        with st.form("sifre_degistir_formu"):
            eski_sifre = st.text_input("Eski Şifre", type="password")
            yeni_sifre_1 = st.text_input("Yeni Şifre", type="password")
            yeni_sifre_2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.form_submit_button("Şifreyi Güncelle", use_container_width=True):
                if not eski_sifre or not yeni_sifre_1 or not yeni_sifre_2:
                    st.warning("Lütfen tüm alanları doldurun.")
                elif yeni_sifre_1 != yeni_sifre_2:
                    st.error("Yeni şifreler birbiriyle uyuşmuyor.")
                else:
                    try:
                        supabase.auth.sign_in_with_password({"email": user_email, "password": eski_sifre})
                        supabase.auth.update_user({"password": yeni_sifre_1})
                        st.success("✅ Şifreniz başarıyla değiştirildi!")
                    except Exception as err:
                        st.error(f"Şifre değiştirilemedi: {err}")

# ==============================================================================
# --- SAYFA 7: HAKKINDA SAYFASI ---
# ==============================================================================
elif st.session_state.sayfa == "hakkinda":
    st.title("ℹ️ Hakkında")
    st.markdown("---")
    st.markdown("### FETİ YILMAZ")
    st.markdown("### 2026")
    st.markdown("### Ulaşım için:")
    st.markdown("📧 fetiylmaz@gmail.com")
