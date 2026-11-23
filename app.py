from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="WattMirror — Canlı Enerji Ekosistemi",
    page_icon="🌿",
    layout="wide",
)

# --- HAZIR EV PROFİLLERİ ---
PROFILES = {
    "3+1 Aile Evi": [
        {"id": "ac", "name": "Klima", "watts": 1450, "active": True, "saving_watts": 850, "action_label": "24°C Eko Moda Alındı"},
        {"id": "pc", "name": "Oyun Konsolu / PC", "watts": 420, "active": True, "saving_watts": 320, "action_label": "Uyku Moduna Alındı"},
        {"id": "airfryer", "name": "Airfryer", "watts": 1500, "active": False, "saving_watts": 1500, "action_label": "Kullanım Dışı Kapatıldı"},
        {"id": "dishwasher", "name": "Bulaşık Makinesi", "watts": 1200, "active": True, "saving_watts": 750, "action_label": "Eko Program Seçildi"},
        {"id": "fridge", "name": "Buzdolabı", "watts": 160, "active": True, "saving_watts": 30, "action_label": "Sıcaklık Dengelendi"},
        {"id": "tv", "name": "Akıllı TV", "watts": 130, "active": True, "saving_watts": 90, "action_label": "Ekran Parlaklığı Kısıldı"},
        {"id": "lights", "name": "Oda Aydınlatması", "watts": 75, "active": True, "saving_watts": 55, "action_label": "Gereksiz Işıklar Kapatıldı"},
    ],
    "1+1 Öğrenci Evi": [
        {"id": "ac", "name": "Klima", "watts": 1100, "active": False, "saving_watts": 650, "action_label": "25°C Eko Moda Alındı"},
        {"id": "pc", "name": "Laptop / Oyun PC", "watts": 280, "active": True, "saving_watts": 200, "action_label": "Güç Tasarrufuna Alındı"},
        {"id": "airfryer", "name": "Airfryer", "watts": 1400, "active": True, "saving_watts": 1400, "action_label": "İşlem Bitince Kapatıldı"},
        {"id": "kettle", "name": "Su Isıtıcı / Kettle", "watts": 1800, "active": False, "saving_watts": 1800, "action_label": "Bekleme Modu Kapatıldı"},
        {"id": "fridge", "name": "Mini Buzdolabı", "watts": 95, "active": True, "saving_watts": 20, "action_label": "Eko Mod Aktif"},
        {"id": "lights", "name": "Çalışma Lambası & Oda", "watts": 45, "active": True, "saving_watts": 30, "action_label": "LED Düşük Mod"},
    ],
    "Küçük Ofis": [
        {"id": "ac", "name": "Ofis Kliması", "watts": 1600, "active": True, "saving_watts": 950, "action_label": "23°C Eko Moda Alındı"},
        {"id": "workstations", "name": "Çalışma İstasyonları (x4)", "watts": 640, "active": True, "saving_watts": 420, "action_label": "Ekran Uyku Modu Aktif"},
        {"id": "coffee", "name": "Kahve Makinesi", "watts": 1250, "active": False, "saving_watts": 1250, "action_label": "Otomatik Kapatma Devrede"},
        {"id": "printer", "name": "Lazer Yazıcı & Ağ", "watts": 180, "active": True, "saving_watts": 130, "action_label": "Uyku Moduna Alındı"},
        {"id": "lights", "name": "Ofis Aydınlatması", "watts": 140, "active": True, "saving_watts": 90, "action_label": "Bölgesel Aydınlatma Kısıldı"},
    ],
}

# --- HAZIR SENARYOLAR (cihaz id -> aktif mi?) ---
SCENARIOS = {
    "Normal Ev": {"ac": True, "pc": True, "workstations": True, "airfryer": False, "kettle": False, "coffee": False, "dishwasher": True, "fridge": True, "tv": True, "printer": True, "lights": True},
    "Evde Kimse Yok": {"ac": False, "pc": False, "workstations": False, "airfryer": False, "kettle": False, "coffee": False, "dishwasher": False, "fridge": True, "tv": False, "printer": False, "lights": False},
    "Akşam Zirve (18:00–22:00)": {"ac": True, "pc": True, "workstations": True, "airfryer": True, "kettle": True, "coffee": True, "dishwasher": True, "fridge": True, "tv": True, "printer": True, "lights": True},
    "Çalışma Saati": {"ac": True, "pc": True, "workstations": True, "airfryer": False, "kettle": False, "coffee": True, "dishwasher": False, "fridge": True, "tv": False, "printer": True, "lights": True},
}

# --- SESSION STATE BAŞLATMA ---
if "active_profile" not in st.session_state:
    st.session_state.active_profile = "3+1 Aile Evi"

if "devices" not in st.session_state:
    st.session_state.devices = [d.copy() for d in PROFILES["3+1 Aile Evi"]]

if "last_saving_log" not in st.session_state:
    st.session_state.last_saving_log = []

if "previous_snapshot" not in st.session_state:
    st.session_state.previous_snapshot = None

if "saving_used_count" not in st.session_state:
    st.session_state.saving_used_count = 0

if "monthly_budget_tl" not in st.session_state:
    st.session_state.monthly_budget_tl = 1500


def load_profile(profile_name: str):
    st.session_state.active_profile = profile_name
    st.session_state.devices = [d.copy() for d in PROFILES[profile_name]]
    st.session_state.previous_snapshot = None
    st.session_state.last_saving_log = []


def apply_scenario(scenario_name: str):
    mapping = SCENARIOS.get(scenario_name, {})
    for dev in st.session_state.devices:
        if dev["id"] in mapping:
            dev["active"] = mapping[dev["id"]]
        else:
            dev["active"] = scenario_name != "Evde Kimse Yok"


def apply_saving_mode():
    """En yüksek tüketimli aktif cihazlara önerilen tasarruf aksiyonunu uygular."""
    st.session_state.previous_snapshot = [d.copy() for d in st.session_state.devices]
    logs = []

    active_sorted = sorted(
        [d for d in st.session_state.devices if d["active"]],
        key=lambda x: x["watts"],
        reverse=True,
    )

    for dev in active_sorted[:3]:
        target = next(d for d in st.session_state.devices if d["id"] == dev["id"])
        old_w = target["watts"]
        reduction = min(target["saving_watts"], max(0, old_w - 20))
        new_w = old_w - reduction

        if new_w <= 25:
            target["active"] = False
            logs.append(f"**{target['name']}** kapatıldı ({old_w}W → 0W, **-{old_w}W**)")
        else:
            target["watts"] = new_w
            logs.append(f"**{target['name']}** ({target['action_label']}): {old_w}W → {new_w}W (**-{reduction}W**)")

    st.session_state.last_saving_log = logs
    if logs:
        st.session_state.saving_used_count += 1


def undo_saving_mode():
    if st.session_state.previous_snapshot is not None:
        st.session_state.devices = [d.copy() for d in st.session_state.previous_snapshot]
        st.session_state.previous_snapshot = None
        st.session_state.last_saving_log = []


# --- HESAPLAMALAR ---
total_watts = sum(d["watts"] for d in st.session_state.devices if d["active"])
profile_max_watts = max(sum(d["watts"] for d in PROFILES[st.session_state.active_profile]), 1)

ratio = min(total_watts / profile_max_watts, 1.0)
eco_score = int(round((1.0 - ratio ** 0.75) * 100))
eco_score = max(5, min(100, eco_score))

# Tahmini maliyet ve CO2 (4.5 TL / kWh, günlük ortalama 6 saat aktif eşdeğeri, 30 gün)
tariff_tl_per_kwh = 4.5
hourly_cost_tl = (total_watts / 1000.0) * tariff_tl_per_kwh
estimated_monthly_tl = hourly_cost_tl * 6.0 * 30.0
daily_co2_kg = (total_watts * 6.0 / 1000.0) * 0.44


def render_animated_ecosystem_svg(score: int, watts: int, profile_name: str) -> str:
    if score >= 75:
        sky_top = "#0284C7"
        sky_mid = "#7DD3FC"
        sky_bot = "#ECFDF5"
        hill_far = "#34D399"
        hill_near = "#10B981"
        leaf_main = "#059669"
        leaf_light = "#6EE7B7"
        canopy_scale = 1.15
        turbine_speed = "3.2s"
        status_badge = "🌿 CANLI & DENGELİ EKOSİSTEM"
        badge_bg = "#D1FAE5"
        badge_fg = "#065F46"
        flow_color = "#10B981"
        show_warning_smoke = False
    elif score >= 45:
        sky_top = "#2563EB"
        sky_mid = "#BAE6FD"
        sky_bot = "#FEF9C3"
        hill_far = "#86EFAC"
        hill_near = "#4ADE80"
        leaf_main = "#65A30D"
        leaf_light = "#BEF264"
        canopy_scale = 0.95
        turbine_speed = "6.5s"
        status_badge = "⚡ ORTA TÜKETİM — DİKKAT"
        badge_bg = "#FEF3C7"
        badge_fg = "#92400E"
        flow_color = "#F59E0B"
        show_warning_smoke = False
    else:
        sky_top = "#475569"
        sky_mid = "#CBD5E1"
        sky_bot = "#FFEDD5"
        hill_far = "#94A3B8"
        hill_near = "#64748B"
        leaf_main = "#D97706"
        leaf_light = "#FDBA74"
        canopy_scale = 0.72
        turbine_speed = "12s"
        status_badge = "🔥 YÜKSEK TÜKETİM UYARISI"
        badge_bg = "#FEE2E2"
        badge_fg = "#991B1B"
        flow_color = "#EF4444"
        show_warning_smoke = True

    smoke_svg = """
      <g class="smoke-puff" opacity="0.75">
        <circle cx="235" cy="182" r="9" fill="#94A3B8"/>
        <circle cx="248" cy="164" r="13" fill="#CBD5E1"/>
        <circle cx="262" cy="144" r="16" fill="#E2E8F0"/>
        <text x="275" y="132" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#DC2626">!</text>
      </g>
    """ if show_warning_smoke else ""

    return f"""
    <div style="border-radius:20px; overflow:hidden; border:1px solid #E2E8F0; box-shadow:0 12px 28px rgba(15,23,42,0.08);">
      <style>
        @keyframes spinRotor {{
          from {{ transform: rotate(0deg); }}
          to {{ transform: rotate(360deg); }}
        }}
        @keyframes sunPulse {{
          0%, 100% {{ transform: scale(1); opacity: 0.25; }}
          50% {{ transform: scale(1.18); opacity: 0.45; }}
        }}
        @keyframes dashFlow {{
          to {{ stroke-dashoffset: -28; }}
        }}
        @keyframes smokeFloat {{
          0% {{ transform: translateY(6px); opacity: 0.2; }}
          50% {{ opacity: 0.8; }}
          100% {{ transform: translateY(-14px); opacity: 0; }}
        }}
        .rotor-blades {{
          transform-origin: 0px 0px;
          animation: spinRotor {turbine_speed} linear infinite;
        }}
        .sun-halo {{
          transform-origin: 695px 82px;
          animation: sunPulse 3.5s ease-in-out infinite;
        }}
        .energy-line {{
          animation: dashFlow 1.4s linear infinite;
        }}
        .smoke-puff {{
          animation: smokeFloat 2.4s ease-in-out infinite;
        }}
      </style>

      <svg viewBox="0 0 820 400" width="100%" height="370" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="wmSky" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="{sky_top}"/>
            <stop offset="55%" stop-color="{sky_mid}"/>
            <stop offset="100%" stop-color="{sky_bot}"/>
          </linearGradient>
          <linearGradient id="wmGround" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{hill_near}"/>
            <stop offset="100%" stop-color="#047857"/>
          </linearGradient>
        </defs>

        <!-- Gökyüzü -->
        <rect width="820" height="400" fill="url(#wmSky)"/>

        <!-- Parlayan Güneş -->
        <circle class="sun-halo" cx="695" cy="82" r="56" fill="#FDE047"/>
        <circle cx="695" cy="82" r="36" fill="#FACC15"/>

        <!-- Bulutlar -->
        <g fill="#FFFFFF" opacity="0.9">
          <rect x="115" y="64" width="104" height="28" rx="14"/>
          <circle cx="147" cy="60" r="22"/>
          <circle cx="177" cy="56" r="26"/>

          <rect x="425" y="48" width="86" height="22" rx="11"/>
          <circle cx="451" cy="44" r="17"/>
          <circle cx="475" cy="42" r="20"/>
        </g>

        <!-- Tepeler & Çayır -->
        <path d="M0 250 Q210 175 430 242 T820 215 L820 400 L0 400 Z" fill="{hill_far}" opacity="0.72"/>
        <path d="M0 282 Q260 225 530 278 T820 255 L820 400 L0 400 Z" fill="url(#wmGround)"/>

        <!-- Canlı Enerji Akış Hatları -->
        <path class="energy-line" d="M225 255 Q315 190 395 250" fill="none" stroke="{flow_color}" stroke-width="3.5" stroke-dasharray="8 6"/>
        <path class="energy-line" d="M425 250 Q525 185 645 235" fill="none" stroke="{flow_color}" stroke-width="3.5" stroke-dasharray="8 6"/>

        <!-- Güneş Panelli Ev -->
        <g transform="translate(105, 192)">
          <rect x="6" y="42" width="124" height="74" rx="10" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
          <polygon points="-6,45 68,-4 142,45" fill="#1E293B"/>
          <polygon points="16,36 62,6 73,16 27,46" fill="#2563EB" stroke="#93C5FD" stroke-width="1.5"/>
          <rect x="54" y="70" width="24" height="46" rx="4" fill="#92400E"/>
          <rect x="20" y="60" width="22" height="22" rx="4" fill="#E0F2FE" stroke="#64748B" stroke-width="1.5"/>
          <rect x="94" y="60" width="22" height="22" rx="4" fill="#E0F2FE" stroke="#64748B" stroke-width="1.5"/>
        </g>

        {smoke_svg}

        <!-- Merkez Eko-Ağaç -->
        <g transform="translate(410, 282)">
          <rect x="-11" y="-58" width="22" height="66" rx="6" fill="#78350F"/>
          <g transform="scale({canopy_scale})">
            <circle cx="0" cy="-86" r="54" fill="{leaf_main}"/>
            <circle cx="-38" cy="-64" r="40" fill="{leaf_main}"/>
            <circle cx="38" cy="-64" r="40" fill="{leaf_main}"/>
            <circle cx="-18" cy="-102" r="34" fill="{leaf_light}" opacity="0.78"/>
            <circle cx="22" cy="-96" r="32" fill="{leaf_light}" opacity="0.78"/>
          </g>
        </g>

        <!-- Dönen Rüzgar Türbini -->
        <g transform="translate(650, 132)">
          <rect x="-4" y="0" width="8" height="145" rx="4" fill="#F8FAFC"/>
          <g class="rotor-blades">
            <path d="M0 0 L-7 -68 L7 -68 Z" fill="#FFFFFF"/>
            <path d="M0 0 L63 33 L51 47 Z" fill="#FFFFFF"/>
            <path d="M0 0 L-63 33 L-51 47 Z" fill="#FFFFFF"/>
          </g>
          <circle cx="0" cy="0" r="8" fill="#0F172A"/>
        </g>

        <!-- Üst Durum Rozeti -->
        <rect x="24" y="20" width="265" height="34" rx="17" fill="{badge_bg}"/>
        <text x="156" y="42" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="{badge_fg}">
          {status_badge}
        </text>

        <!-- Alt Bilgi Çubuğu -->
        <rect x="24" y="336" width="772" height="44" rx="12" fill="#0F172A" opacity="0.86"/>
        <text x="46" y="363" font-family="Arial, sans-serif" font-size="14.5" font-weight="bold" fill="#FFFFFF">
          {profile_name} • Anlık Güç: {watts} W • Eko-Skor: {score}/100
        </text>
        <text x="774" y="363" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="#94A3B8">
          WattMirror Canlı Sahne
        </text>
      </svg>
    </div>
    """


# --- ÜST BAŞLIK & PROFİL / BÜTÇE AYARLARI ---
st.title("🌿 WattMirror — Canlı Enerji Ekosistemi")
st.caption("Hazır ev profilleri ve zaman senaryolarıyla enerji tüketimini yönet, bütçeni koru ve ekosistemi canlandır.")

top_c1, top_c2, top_c3 = st.columns([1.2, 1.3, 1.1])

with top_c1:
    selected_profile = st.selectbox(
        "🏠 Hazır Profil",
        list(PROFILES.keys()),
        index=list(PROFILES.keys()).index(st.session_state.active_profile),
    )
    if selected_profile != st.session_state.active_profile:
        load_profile(selected_profile)
        st.rerun()

with top_c2:
    st.markdown("**⏱️ Zaman / Durum Senaryosu**")
    sc_cols = st.columns(2)
    scenario_names = list(SCENARIOS.keys())
    for idx, sc_name in enumerate(scenario_names):
        with sc_cols[idx % 2]:
            short_label = sc_name.split(" (")[0]
            if st.button(short_label, key=f"sc_{idx}", use_container_width=True):
                apply_scenario(sc_name)
                st.rerun()

with top_c3:
    budget_val = st.number_input(
        "💳 Aylık Elektrik Bütçesi (₺)",
        min_value=200,
        max_value=20000,
        value=int(st.session_state.monthly_budget_tl),
        step=100,
    )
    st.session_state.monthly_budget_tl = budget_val

# Üst metrikler
m1, m2, m3, m4 = st.columns(4)
m1.metric("Anlık Güç", f"{total_watts} W")
m2.metric("Eko-Skor", f"{eco_score} / 100")
m3.metric("Tahmini Aylık Fatura", f"{estimated_monthly_tl:,.0f} ₺")
m4.metric("Tahmini Günlük CO₂", f"{daily_co2_kg:.2f} kg")

# Aylık bütçe uyarısı
diff_tl = estimated_monthly_tl - st.session_state.monthly_budget_tl
if diff_tl > 0:
    st.warning(
        f"⚠️ **Bütçe Uyarısı:** Bu hızla gidersen ay sonu tahmini faturan **{estimated_monthly_tl:,.0f} TL** "
        f"(**{diff_tl:,.0f} TL aşım**). Hedefin: {st.session_state.monthly_budget_tl:,.0f} TL."
    )
else:
    saved_margin = abs(diff_tl)
    st.success(
        f"✅ **Bütçe Hedefte:** Ay sonu tahmini faturan **{estimated_monthly_tl:,.0f} TL** — "
        f"bütçenin **{saved_margin:,.0f} TL** altında kalıyorsun!"
    )

st.divider()

# --- SOL: EKOSİSTEM, ROZETLER & GRAFİK | SAĞ: CİHAZ KONTROLLERİ ---
left_col, right_col = st.columns([1.35, 1], gap="large")

with left_col:
    components.html(
        render_animated_ecosystem_svg(eco_score, total_watts, st.session_state.active_profile),
        height=385,
    )

    btn_c1, btn_c2, btn_c3 = st.columns([1.4, 1, 1])
    with btn_c1:
        st.button("⚡ Tasarruf Modunu Uygula", type="primary", use_container_width=True, on_click=apply_saving_mode)
    with btn_c2:
        st.button(
            "↩ Geri Al",
            use_container_width=True,
            disabled=(st.session_state.previous_snapshot is None),
            on_click=undo_saving_mode,
        )
    with btn_c3:
        if st.button("🔄 Profili Sıfırla", use_container_width=True):
            load_profile(st.session_state.active_profile)
            st.rerun()

    if st.session_state.last_saving_log:
        st.info("Tasarruf Modu önerilen aksiyonları uyguladı:")
        for item in st.session_state.last_saving_log:
            st.markdown(f"* {item}")

    # Rozetler
    st.markdown("### 🏆 Rozetler & Hedefler")
    b1, b2, b3 = st.columns(3)
    with b1:
        if eco_score >= 80:
            st.success("🌟 **Eko-Skor 80+**\nKazanıldı!")
        else:
            st.caption("🔒 **Eko-Skor 80+** (Skoru 80 ve üstüne çıkar)")
    with b2:
        if total_watts < 1000:
            st.success("🍃 **1000 W Altı**\nKazanıldı!")
        else:
            st.caption("🔒 **1000 W Altı** (Anlık gücü 1000 W altına indir)")
    with b3:
        if st.session_state.saving_used_count >= 1:
            st.success("⚡ **İlk Tasarruf**\nKazanıldı!")
        else:
            st.caption("🔒 **İlk Tasarruf** (Tasarruf Modunu uygula)")

    # Cihaz bazlı anlık tüketim grafiği
    st.markdown("### 📊 Cihaz Bazlı Güç Tüketimi (Watt)")
    chart_data = {
        d["name"]: (d["watts"] if d["active"] else 0)
        for d in st.session_state.devices
    }
    st.bar_chart(chart_data, height=220)

with right_col:
    st.subheader("🔌 Cihaz Listesi")

    for dev in st.session_state.devices:
        c_toggle, c_info = st.columns([0.2, 0.8])
        with c_toggle:
            new_state = st.toggle(
                dev["name"],
                value=dev["active"],
                key=f"toggle_{st.session_state.active_profile}_{dev['id']}",
                label_visibility="collapsed",
            )
            dev["active"] = new_state

        with c_info:
            if dev["active"]:
                st.markdown(f"**{dev['name']}** — **{dev['watts']} W** *(Öneri: {dev['action_label']})*")
            else:
                st.markdown(f"**{dev['name']}** — ~~{dev['watts']} W~~ *(Kapalı)*")

    st.divider()
    st.markdown("**➕ Yeni Cihaz Ekle**")
    with st.form("add_device_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns([1.4, 1])
        new_name = f_col1.text_input("Cihaz Adı", placeholder="Örn: Çamaşır Makinesi")
        new_watts = f_col2.number_input("Güç (Watt)", min_value=5, max_value=5000, value=600, step=10)
        submitted = st.form_submit_button("Listeye Ekle", use_container_width=True)

        if submitted:
            if new_name.strip():
                new_id = f"custom_{len(st.session_state.devices) + 1}_{new_name.strip().lower().replace(' ', '_')}"
                st.session_state.devices.append(
                    {
                        "id": new_id,
                        "name": new_name.strip(),
                        "watts": int(new_watts),
                        "active": True,
                        "saving_watts": int(new_watts * 0.4),
                        "action_label": "Eko Moda Alındı",
                    }
                )
                st.rerun()
            else:
                st.warning("Lütfen bir cihaz adı gir.")