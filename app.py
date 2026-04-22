#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGERE — Application de commandes repas traiteur
Version Web (Streamlit)
"""

import streamlit as st
import json, os, re, io
from datetime import date, datetime, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ─── Configuration page ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAGERE · Commandes Repas",
    page_icon="🍽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Chemins données ──────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_FILE     = os.path.join(BASE_DIR, "data", "commandes.json")
MENUS_FILE    = os.path.join(BASE_DIR, "data", "menus.json")
SALARIES_FILE = os.path.join(BASE_DIR, "data", "salaries.json")
CARTE_FILE    = os.path.join(BASE_DIR, "data", "carte_permanente.json")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

# ─── Constantes ──────────────────────────────────────────────────────────────
JOURS    = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
CAT_MENU = ["Entrées", "Plats garnis", "Accompagnements", "Produits laitiers", "Desserts"]

CAT_COLORS = {
    "Entrées":           "#8B6BBF",
    "Plats garnis":      "#3E7EC4",
    "Accompagnements":   "#2EA86A",
    "Produits laitiers": "#D4902A",
    "Desserts":          "#C4546A",
    "Carte du jour":     "#3AACAC",
}

DEFAULT_SALARIES = ["GHEYSENS Eric", "CAMPION Pascal", "CHARPENTIER Franck", "PEREIRA Serge"]

DEFAULT_CARTE = {
    "Entrées":           ["Tomate et dosette de vinaigrette", "Salade verte", "Œuf dur mayonnaise"],
    "Plats garnis":      ["Filet de poulet", "Jambon blanc", "Pané de blé, tomate et mozzarella",
                          "Pavé de colin mariné huile d'olive et citron vert", "Steak haché cuit à cœur"],
    "Accompagnements":   ["Pommes vapeur", "Frites au four", "Pâtes", "Haricots verts"],
    "Produits laitiers": [],
    "Desserts":          ["Crème dessert chocolat", "Purée de pommes fraises", "Tarte aux pommes"],
}

# ─── CSS personnalisé ─────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #181B2E !important; }
[data-testid="stSidebar"]          { background: #22263D !important; }
[data-testid="stSidebar"] > div    { padding-top: 1rem; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
div[data-testid="stCheckbox"] label p { color: #E8EAF6 !important; font-size: 0.95rem; }
.sidebar-label {
    font-size: 0.70rem; font-weight: 700;
    color: #555A82; letter-spacing: 0.12em;
    margin: 14px 0 3px 0;
}
.recap-ok  { color: #3DBE6E; font-weight: 700; }
.recap-non { color: #555A82; }
div[data-testid="column"] button { width: 100%; border-radius: 6px; }
/* Supprime le fond blanc parasite sur les containers */
div[data-testid="stVerticalBlock"] > div { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ─── Persistance JSON ─────────────────────────────────────────────────────────
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Semaines ────────────────────────────────────────────────────────────────
def week_key(d=None):
    d = d or date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-S{iso[1]:02d}"

def week_label(key):
    try:
        yr, sw = key.split("-S")
        yr, sw = int(yr), int(sw)
        monday = date.fromisocalendar(yr, sw, 1)
        friday = monday + timedelta(days=4)
        mois = ["","jan.","fév.","mars","avr.","mai","juin",
                "juil.","août","sept.","oct.","nov.","déc."]
        return f"S{sw:02d} · {monday.day} {mois[monday.month]} – {friday.day} {mois[friday.month]} {yr}"
    except Exception:
        return key

def weeks_list(menus):
    keys = sorted(menus.keys(), reverse=True)
    return keys if keys else [week_key()]

# ─── Import menu traiteur ─────────────────────────────────────────────────────
def parse_traiteur_html(content_bytes):
    from bs4 import BeautifulSoup
    raw = content_bytes
    content = None
    for enc in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            content = raw.decode(enc)
            break
        except Exception:
            pass
    if not content:
        raise ValueError("Impossible de décoder le fichier.")

    soup = BeautifulSoup(content, "html.parser")
    periode = ""
    p = soup.find("p", class_="block_date")
    if p:
        periode = p.get_text(strip=True)

    sem_match = re.search(r'(\d{4})-S(\d{2})', periode)
    sem_key = f"{sem_match.group(1)}-S{sem_match.group(2)}" if sem_match else week_key()

    tables = soup.find_all("table", class_="table_recette")
    cat_order = ["Entrées", "Plats garnis", "Accompagnements", "Produits laitiers", "Desserts"]
    jours_data = {j: {c: [] for c in cat_order} for j in JOURS}

    if len(tables) >= 25:
        for cat_idx, cat in enumerate(cat_order):
            for jour_idx, jour in enumerate(JOURS):
                t = tables[cat_idx * 5 + jour_idx]
                items = [tr.get_text(strip=True) for tr in t.find_all("tr") if tr.get_text(strip=True)]
                jours_data[jour][cat] = items
    else:
        per_jour = max(1, len(tables) // len(cat_order))
        for cat_idx, cat in enumerate(cat_order):
            for jour_idx, jour in enumerate(JOURS):
                t_idx = cat_idx * per_jour + jour_idx
                if t_idx < len(tables):
                    t = tables[t_idx]
                    items = [tr.get_text(strip=True) for tr in t.find_all("tr") if tr.get_text(strip=True)]
                    jours_data[jour][cat] = items

    return {"semaine": sem_key, "periode": periode, "jours": jours_data}

# ─── Export Excel traiteur ────────────────────────────────────────────────────
def build_export_traiteur(menu, commandes, salaries, carte):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Commande traiteur"
    periode = menu.get("periode", "")

    def fill(h): return PatternFill("solid", fgColor=h.lstrip("#"))
    thin = Border(**{s: Side(style="thin", color="444870") for s in ("left","right","top","bottom")})

    ws.merge_cells("A1:H1")
    ws["A1"] = f"SAGERE — Bon de commande traiteur  |  {periode}"
    ws["A1"].font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = fill("1E2240")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    ws["A2"].font = Font(name="Calibri", size=9, color="888EC0")
    ws["A2"].fill = fill("1E2240")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 18

    headers = ["Catégorie", "Plat / Article"] + JOURS + ["TOTAL SEMAINE"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=c, value=h)
        cell.font = Font(name="Calibri", bold=True, size=10, color="E8EAF6")
        cell.fill = fill("2B3270")
        cell.alignment = Alignment(horizontal="center" if c > 2 else "left")
        cell.border = thin
    ws.row_dimensions[3].height = 22

    cat_hex = {"Entrées":"3A2060","Plats garnis":"1A3A68","Accompagnements":"0D4A2A",
               "Produits laitiers":"5A3A08","Desserts":"5A1A28","Carte du jour":"0A3A3A"}
    cat_fg  = {"Entrées":"D8C0F8","Plats garnis":"C0D8F8","Accompagnements":"B0F0D0",
               "Produits laitiers":"F8E0A0","Desserts":"F8C0CC","Carte du jour":"A0E8E8"}

    row = [4]
    grand_total = [0]

    def write_block(cat_key, label, items_fn, cmd_cat):
        all_items, seen = [], set()
        for jour in JOURS:
            for it in items_fn(jour):
                if it and it not in seen:
                    all_items.append(it); seen.add(it)
        if not all_items: return

        ws.merge_cells(start_row=row[0], start_column=1, end_row=row[0], end_column=8)
        cell = ws.cell(row=row[0], column=1, value=f"  ▸  {label.upper()}")
        cell.font  = Font(name="Calibri", bold=True, size=10, color=cat_fg.get(cat_key,"E8EAF6"))
        cell.fill  = fill(cat_hex.get(cat_key,"222222"))
        cell.alignment = Alignment(vertical="center")
        ws.row_dimensions[row[0]].height = 18
        row[0] += 1

        for item in all_items:
            totaux, ltotal = [], 0
            for jour in JOURS:
                qty = sum(1 for sal in salaries if item in commandes.get(sal,{}).get(jour,{}).get(cmd_cat,[]))
                totaux.append(qty); ltotal += qty
            grand_total[0] += ltotal

            ws.cell(row=row[0], column=1, value=label).font = Font(name="Calibri", size=8, color="667090")
            ws.cell(row=row[0], column=1).fill = fill("1E2240"); ws.cell(row=row[0], column=1).border = thin
            ws.cell(row=row[0], column=2, value=item).font = Font(name="Calibri", size=10, color="D8DCFF")
            ws.cell(row=row[0], column=2).fill = fill("1E2240"); ws.cell(row=row[0], column=2).border = thin

            for j_idx, qty in enumerate(totaux):
                c = ws.cell(row=row[0], column=3+j_idx, value=qty if qty else "")
                c.fill = fill("0D3020" if qty > 0 else "1E2240")
                c.font = Font(name="Calibri", bold=(qty>0), size=10, color="60E890" if qty>0 else "444870")
                c.alignment = Alignment(horizontal="center"); c.border = thin

            ct = ws.cell(row=row[0], column=8, value=ltotal if ltotal else "")
            ct.fill = fill("101428")
            ct.font = Font(name="Calibri", bold=True, size=10, color="FFD060" if ltotal>0 else "444870")
            ct.alignment = Alignment(horizontal="center"); ct.border = thin
            ws.row_dimensions[row[0]].height = 16
            row[0] += 1

    for cat in CAT_MENU:
        write_block(cat, cat, lambda jour, c=cat: menu.get("jours",{}).get(jour,{}).get(c,[]), cat)

    if any(carte.get(s) for s in CAT_MENU):
        ws.merge_cells(start_row=row[0], start_column=1, end_row=row[0], end_column=8)
        sep = ws.cell(row=row[0], column=1, value="  ━━━  CARTE DU JOUR (permanente)  ━━━")
        sep.font = Font(name="Calibri", bold=True, size=11, color="A0E8E8")
        sep.fill = fill("0A3A3A"); sep.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row[0]].height = 20; row[0] += 1
        for sub in CAT_MENU:
            items = carte.get(sub, [])
            if items:
                write_block("Carte du jour", f"Carte · {sub}", lambda jour, it=items: it, f"Carte · {sub}")

    row[0] += 1
    ws.merge_cells(start_row=row[0], start_column=1, end_row=row[0], end_column=2)
    ws.cell(row=row[0], column=1, value="TOTAL JOURNALIER").font = Font(bold=True, color="FFD060", size=10)
    ws.cell(row=row[0], column=1).fill = fill("101428")

    for j_idx, jour in enumerate(JOURS):
        tj = sum(len(commandes.get(sal,{}).get(jour,{}).get(cat,[]))
                 for sal in salaries for cat in CAT_MENU + [f"Carte · {s}" for s in CAT_MENU])
        c = ws.cell(row=row[0], column=3+j_idx, value=tj)
        c.font = Font(bold=True, size=11, color="FFD060")
        c.fill = fill("101428"); c.alignment = Alignment(horizontal="center"); c.border = thin

    ws.cell(row=row[0], column=8, value=grand_total[0]).font = Font(bold=True, size=12, color="FFD060")
    ws.cell(row=row[0], column=8).fill = fill("101428")
    ws.cell(row=row[0], column=8).alignment = Alignment(horizontal="center")
    ws.row_dimensions[row[0]].height = 24

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 44
    for j in range(5): ws.column_dimensions[openpyxl.utils.get_column_letter(3+j)].width = 12
    ws.column_dimensions["H"].width = 14
    ws.freeze_panes = "C4"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# ─── Export Excel interne ─────────────────────────────────────────────────────
def build_export_interne(menu, commandes, salaries, carte):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Récapitulatif"
    periode = menu.get("periode", "")

    def fill(h): return PatternFill("solid", fgColor=h.lstrip("#"))
    thin = Border(**{s: Side(style="thin", color="444870") for s in ("left","right","top","bottom")})

    nb_cols = 2 + len(JOURS) * len(salaries)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=nb_cols)
    ws["A1"] = f"SAGERE — Récapitulatif interne  |  {periode}"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = fill("1E2240")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    col = 3
    for jour in JOURS:
        ws.merge_cells(start_row=2, start_column=col, end_row=2, end_column=col+len(salaries)-1)
        c = ws.cell(row=2, column=col, value=jour.upper())
        c.font = Font(bold=True, size=10, color="FFFFFF"); c.fill = fill("2B3270")
        c.alignment = Alignment(horizontal="center")
        col += len(salaries)

    ws.cell(row=3, column=1, value="Catégorie").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=3, column=2, value="Article").font   = Font(bold=True, color="FFFFFF")
    ws.cell(row=3,column=1).fill = ws.cell(row=3,column=2).fill = fill("2B3270")
    col = 3
    for jour in JOURS:
        for sal in salaries:
            c = ws.cell(row=3, column=col, value=sal.split()[0])
            c.font = Font(bold=True, size=8, color="FFFFFF"); c.fill = fill("363B5E")
            c.alignment = Alignment(horizontal="center", wrap_text=True); col += 1
    ws.row_dimensions[3].height = 28

    cat_fg = {"Entrées":"E8D5F8","Plats garnis":"CCE0F8","Accompagnements":"C8EDF0",
              "Produits laitiers":"FDE8C0","Desserts":"F8C8CF","Carte du jour":"C0ECEC"}
    row = [4]

    def write_rows(label, items, cmd_cat, fgc):
        for item in items:
            ws.cell(row=row[0],column=1,value=label).fill = fill(fgc)
            ws.cell(row=row[0],column=1).font = Font(size=8, bold=True); ws.cell(row=row[0],column=1).border = thin
            ws.cell(row=row[0],column=2,value=item).fill = fill("F8F9FF")
            ws.cell(row=row[0],column=2).font = Font(size=9); ws.cell(row=row[0],column=2).border = thin
            col = 3
            for jour in JOURS:
                for sal in salaries:
                    has = item in commandes.get(sal,{}).get(jour,{}).get(cmd_cat,[])
                    c = ws.cell(row=row[0], column=col)
                    if has:
                        c.value = "✓"; c.font = Font(bold=True, color="1A7340"); c.fill = fill("D4F5E0")
                    c.alignment = Alignment(horizontal="center"); c.border = thin; col += 1
            ws.row_dimensions[row[0]].height = 14; row[0] += 1

    for cat in CAT_MENU:
        items, seen = [], set()
        for jour in JOURS:
            for it in menu.get("jours",{}).get(jour,{}).get(cat,[]):
                if it and it not in seen: items.append(it); seen.add(it)
        write_rows(cat, items, cat, cat_fg.get(cat,"EEEEEE"))

    for sub in CAT_MENU:
        items = carte.get(sub, [])
        if items:
            write_rows(f"Carte · {sub}", items, f"Carte · {sub}", cat_fg["Carte du jour"])

    ws.column_dimensions["A"].width = 20; ws.column_dimensions["B"].width = 40
    for i in range(3, 3+len(JOURS)*len(salaries)):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 9
    ws.freeze_panes = "C4"

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return buf

# ─── Chargement données (session state) ──────────────────────────────────────
def init_state():
    if "menus"     not in st.session_state: st.session_state.menus     = load_json(MENUS_FILE, {})
    if "commandes" not in st.session_state: st.session_state.commandes = load_json(DATA_FILE, {})
    if "salaries"  not in st.session_state: st.session_state.salaries  = load_json(SALARIES_FILE, DEFAULT_SALARIES)
    if "carte"     not in st.session_state: st.session_state.carte     = load_json(CARTE_FILE, DEFAULT_CARTE)

    wk = week_key()
    if not st.session_state.menus:
        st.session_state.menus[wk] = {"semaine":wk,"periode":"","jours":{j:{c:[] for c in CAT_MENU} for j in JOURS}}
        save_json(MENUS_FILE, st.session_state.menus)

    if "page"       not in st.session_state: st.session_state.page       = "commande"
    if "week_sel"   not in st.session_state: st.session_state.week_sel   = week_key()
    if "salarie"    not in st.session_state: st.session_state.salarie    = st.session_state.salaries[0] if st.session_state.salaries else ""
    if "jour"       not in st.session_state: st.session_state.jour       = JOURS[min(date.today().weekday(),4)]

init_state()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_menu():
    return st.session_state.menus.get(st.session_state.week_sel, {})

def get_commande(sal, jour):
    return st.session_state.commandes.get(
        st.session_state.week_sel,{}).get(sal,{}).get(jour,{})

def save_commande(sal, jour, choix):
    wk = st.session_state.week_sel
    st.session_state.commandes.setdefault(wk,{}).setdefault(sal,{})[jour] = choix
    save_json(DATA_FILE, st.session_state.commandes)

def cat_header(color, text, icon=""):
    """Bandeau coloré auto-contenu — fonctionne indépendamment du CSS externe."""
    return (
        f'<div style="background:{color};padding:7px 16px;border-radius:8px 8px 0 0;'
        f'font-weight:700;font-size:0.83rem;letter-spacing:0.07em;color:#fff;'
        f'margin-top:14px;margin-bottom:0;">'
        f'{icon}{text}</div>'
        f'<div style="background:#22263D;border:1px solid {color}44;border-top:none;'
        f'border-radius:0 0 8px 8px;padding:10px 8px 4px 8px;margin-bottom:4px;">'
    )

CAT_ICONS = {
    "Entrées":           "🥗 ",
    "Plats garnis":      "🍖 ",
    "Accompagnements":   "🥦 ",
    "Produits laitiers": "🧀 ",
    "Desserts":          "🍮 ",
}

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🍽 SAGERE")
    st.markdown("*Commandes repas traiteur*")
    st.divider()

    # ── Navigation ──
    pages = {
        "commande":  "🧾 Passer commande",
        "menu":      "⚙ Saisir le menu",
        "carte":     "🗂 Carte permanente",
        "salaries":  "👥 Salariés",
        "admin":     "📊 Exports & Admin",
    }
    for key, label in pages.items():
        if st.button(label, key=f"nav_{key}",
                     type="primary" if st.session_state.page == key else "secondary",
                     use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()

    # ── Semaine ──
    st.markdown('<p class="sidebar-label">SEMAINE</p>', unsafe_allow_html=True)
    wks    = weeks_list(st.session_state.menus)
    labels = [week_label(k) for k in wks]
    cur_idx = wks.index(st.session_state.week_sel) if st.session_state.week_sel in wks else 0
    sel_label = st.selectbox("", labels, index=cur_idx, key="week_select_box", label_visibility="collapsed")
    st.session_state.week_sel = wks[labels.index(sel_label)]

    # ── Salarié (uniquement page commande) ──
    if st.session_state.page == "commande":
        st.markdown('<p class="sidebar-label">SALARIÉ</p>', unsafe_allow_html=True)
        sal_idx = st.session_state.salaries.index(st.session_state.salarie) \
                  if st.session_state.salarie in st.session_state.salaries else 0
        st.session_state.salarie = st.selectbox(
            "", st.session_state.salaries, index=sal_idx,
            key="sal_select", label_visibility="collapsed")

        # ── Jour ──
        st.markdown('<p class="sidebar-label">JOUR</p>', unsafe_allow_html=True)
        cols = st.columns(5)
        for i, jour in enumerate(JOURS):
            with cols[i]:
                actif = (st.session_state.jour == jour)
                if st.button(jour[:3], key=f"jour_{jour}",
                             type="primary" if actif else "secondary",
                             use_container_width=True):
                    st.session_state.jour = jour
                    st.rerun()

        # ── Récap semaine ──
        st.divider()
        st.markdown('<p class="sidebar-label">MES COMMANDES</p>', unsafe_allow_html=True)
        sal = st.session_state.salarie
        wk  = st.session_state.week_sel
        sem = st.session_state.commandes.get(wk,{}).get(sal,{})
        for jour in JOURS:
            total = sum(len(v) for v in sem.get(jour,{}).values())
            if total:
                st.markdown(f'<span class="recap-ok">✓ {jour[:3]}</span> — {total} article(s)',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="recap-non">○ {jour[:3]}</span>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : COMMANDE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "commande":
    sal  = st.session_state.salarie
    jour = st.session_state.jour
    wk   = st.session_state.week_sel
    menu = get_menu()

    col_title, col_info = st.columns([2, 3])
    with col_title:
        st.markdown(f"# {jour}")
    with col_info:
        st.markdown(f"<br><span style='color:#8890C0'>{week_label(wk)}</span>",
                    unsafe_allow_html=True)

    existing = get_commande(sal, jour)
    choix    = {}

    jour_menu = menu.get("jours", {}).get(jour, {})
    carte     = st.session_state.carte
    has_any_menu = any(jour_menu.get(c) for c in CAT_MENU)
    has_carte    = any(carte.get(c) for c in CAT_MENU)

    if not has_any_menu and not has_carte:
        st.info("📭 Aucun menu saisi pour cette semaine. Importez le menu du traiteur ou saisissez-le manuellement.")
    else:
        # ── Menu du jour ──
        for cat in CAT_MENU:
            items = jour_menu.get(cat, [])
            if not items:
                continue
            color = CAT_COLORS[cat]
            icon  = CAT_ICONS.get(cat, "")
            selected_in_cat = existing.get(cat, [])

            st.markdown(cat_header(color, cat.upper(), icon), unsafe_allow_html=True)
            cols = st.columns(2)
            for i, item in enumerate(items):
                with cols[i % 2]:
                    checked = st.checkbox(item, value=(item in selected_in_cat),
                                          key=f"cb_{wk}_{sal}_{jour}_{cat}_{item}")
                    if checked:
                        choix.setdefault(cat, []).append(item)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Carte permanente ──
        if has_carte:
            st.markdown(
                '<div style="background:#3AACAC18;border:1.5px solid #3AACAC;border-radius:8px;'
                'padding:9px 18px;margin:22px 0 6px 0;color:#3AACAC;font-weight:700;font-size:0.92rem;">'
                '🗂&nbsp; CARTE DU JOUR — Articles permanents</div>',
                unsafe_allow_html=True)
            for sub_cat in CAT_MENU:
                items = carte.get(sub_cat, [])
                if not items:
                    continue
                color   = CAT_COLORS[sub_cat]   # chaque sous-cat garde SA couleur
                cmd_key = f"Carte · {sub_cat}"
                icon    = CAT_ICONS.get(sub_cat, "")
                selected_in_cat = existing.get(cmd_key, [])

                st.markdown(
                    cat_header(color, f"↳ {sub_cat.upper()} (carte)", icon),
                    unsafe_allow_html=True)
                cols = st.columns(2)
                for i, item in enumerate(items):
                    with cols[i % 2]:
                        checked = st.checkbox(item, value=(item in selected_in_cat),
                                              key=f"cb_{wk}_{sal}_{jour}_{cmd_key}_{item}")
                        if checked:
                            choix.setdefault(cmd_key, []).append(item)
                st.markdown('</div>', unsafe_allow_html=True)

        # ── Bouton valider ──
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✓  Valider ma commande", type="primary", use_container_width=True):
            save_commande(sal, jour, choix)
            total = sum(len(v) for v in choix.values())
            if total:
                st.success(f"✓ Commande enregistrée pour **{jour}** — {total} article(s) sélectionné(s).")
            else:
                st.warning(f"Commande effacée pour {jour}.")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SAISIR LE MENU
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "menu":
    st.markdown("## ⚙ Menu de la semaine")
    wk = st.session_state.week_sel
    menu = st.session_state.menus.get(wk, {
        "semaine": wk, "periode": "",
        "jours": {j: {c: [] for c in CAT_MENU} for j in JOURS}
    })

    # Import traiteur
    st.markdown("### 📥 Importer le fichier du traiteur")
    uploaded = st.file_uploader(
        "Sélectionnez le fichier `.xls` reçu du traiteur",
        type=["xls","html","htm"],
        key="uploader_menu"
    )
    if uploaded:
        try:
            parsed = parse_traiteur_html(uploaded.read())
            wk_imp = parsed["semaine"]
            already = wk_imp in st.session_state.menus
            msg = f"Semaine détectée : **{week_label(wk_imp)}**"
            if already:
                msg += " *(déjà existante — sera remplacée)*"
            st.info(msg)
            if st.button("✅ Confirmer l'import", type="primary"):
                st.session_state.menus[wk_imp] = parsed
                save_json(MENUS_FILE, st.session_state.menus)
                st.session_state.week_sel = wk_imp
                total = sum(len(v) for j in parsed["jours"].values() for v in j.values())
                st.success(f"Menu importé — {total} articles chargés.")
                st.rerun()
        except ModuleNotFoundError:
            st.error("❌ Module `beautifulsoup4` manquant.\n\nInstallez-le :\n```\npip install beautifulsoup4\n```")
        except Exception as e:
            st.error(f"❌ Erreur import : {e}")

    st.divider()

    # Saisie manuelle
    st.markdown("### ✏️ Saisie manuelle du menu")
    periode = st.text_input("Période (ex : Du 29 juin au 03 juillet 2026)",
                             value=menu.get("periode",""), key="periode_input")

    tabs = st.tabs(JOURS)
    new_jours = {}
    for t, jour in zip(tabs, JOURS):
        with t:
            new_jours[jour] = {}
            jour_data = menu.get("jours",{}).get(jour,{})
            for cat in CAT_MENU:
                color = CAT_COLORS[cat]
                icon  = CAT_ICONS.get(cat, "")
                st.markdown(
                    f'<div style="background:{color};padding:6px 14px;border-radius:6px;'
                    f'font-weight:700;font-size:0.82rem;color:#fff;margin:10px 0 4px 0;">'
                    f'{icon}{cat}</div>',
                    unsafe_allow_html=True)
                val = "\n".join(jour_data.get(cat,[]))
                txt = st.text_area(
                    f"Un article par ligne",
                    value=val, height=110,
                    key=f"menu_{wk}_{jour}_{cat}",
                    label_visibility="collapsed"
                )
                new_jours[jour][cat] = [l.strip() for l in txt.split("\n") if l.strip()]

    if st.button("💾 Enregistrer le menu", type="primary"):
        st.session_state.menus[wk] = {"semaine":wk, "periode":periode, "jours":new_jours}
        save_json(MENUS_FILE, st.session_state.menus)
        st.success("Menu enregistré !")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CARTE PERMANENTE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "carte":
    st.markdown("## 🗂 Carte permanente")
    st.markdown("*Ces articles sont proposés tous les jours en complément du menu.*")

    carte = st.session_state.carte
    new_carte = {}

    tabs = st.tabs(CAT_MENU)
    for t, cat in zip(tabs, CAT_MENU):
        with t:
            color = CAT_COLORS[cat]
            icon  = CAT_ICONS.get(cat, "")
            st.markdown(
                f'<div style="background:{color};padding:6px 14px;border-radius:6px;'
                f'font-weight:700;font-size:0.82rem;color:#fff;margin:10px 0 4px 0;">'
                f'{icon}{cat}</div>',
                unsafe_allow_html=True)
            val = "\n".join(carte.get(cat, []))
            txt = st.text_area(
                "Un article par ligne",
                value=val, height=200,
                key=f"carte_{cat}",
                label_visibility="collapsed"
            )
            new_carte[cat] = [l.strip() for l in txt.split("\n") if l.strip()]

    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("💾 Enregistrer la carte", type="primary", use_container_width=True):
            st.session_state.carte = new_carte
            save_json(CARTE_FILE, new_carte)
            total = sum(len(v) for v in new_carte.values())
            st.success(f"Carte enregistrée — {total} article(s).")
            st.rerun()
    with col2:
        if st.button("↺ Réinitialiser par défaut", use_container_width=True):
            st.session_state.carte = dict(DEFAULT_CARTE)
            save_json(CARTE_FILE, DEFAULT_CARTE)
            st.info("Carte réinitialisée.")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SALARIÉS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "salaries":
    st.markdown("## 👥 Gestion des salariés")

    salaries = list(st.session_state.salaries)

    st.markdown("**Liste actuelle**")
    for i, sal in enumerate(salaries):
        col1, col2 = st.columns([4,1])
        with col1:
            new_name = st.text_input(f"Salarié {i+1}", value=sal,
                                      key=f"sal_edit_{i}", label_visibility="collapsed")
            salaries[i] = new_name
        with col2:
            if st.button("✕", key=f"sal_del_{i}", help="Supprimer"):
                salaries.pop(i)
                st.session_state.salaries = salaries
                save_json(SALARIES_FILE, salaries)
                st.rerun()

    st.divider()
    new_sal = st.text_input("➕ Ajouter un salarié", placeholder="Prénom NOM",
                             key="new_sal_input")
    if st.button("Ajouter", type="primary") and new_sal.strip():
        salaries.append(new_sal.strip())
        st.session_state.salaries = salaries
        save_json(SALARIES_FILE, salaries)
        st.rerun()

    if st.button("💾 Enregistrer les modifications", use_container_width=True):
        st.session_state.salaries = [s for s in salaries if s.strip()]
        save_json(SALARIES_FILE, st.session_state.salaries)
        st.success("Liste mise à jour.")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : EXPORTS & ADMIN
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "admin":
    st.markdown("## 📊 Exports & Administration")

    wk       = st.session_state.week_sel
    menu     = get_menu()
    commandes= st.session_state.commandes.get(wk, {})
    salaries = st.session_state.salaries
    carte    = st.session_state.carte
    periode  = menu.get("periode", wk)

    st.markdown(f"**Semaine sélectionnée :** {week_label(wk)}")

    # ── Exports ──
    st.markdown("### 📤 Export bon de commande traiteur")
    st.markdown("*Quantités totales par article et par jour — sans détail salarié*")
    buf_traiteur = build_export_traiteur(menu, commandes, salaries, carte)
    st.download_button(
        label="⬇ Télécharger le bon de commande (Excel)",
        data=buf_traiteur,
        file_name=f"BonCommande_Traiteur_{wk}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### 📋 Export récapitulatif interne")
    st.markdown("*Détail par salarié (✓ par plat et par jour)*")
    buf_interne = build_export_interne(menu, commandes, salaries, carte)
    st.download_button(
        label="⬇ Télécharger le récapitulatif interne (Excel)",
        data=buf_interne,
        file_name=f"Recapitulatif_Interne_{wk}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.markdown("---")

    # ── Résumé des commandes ──
    st.markdown("### 📈 Résumé des commandes de la semaine")
    if not commandes:
        st.info("Aucune commande enregistrée pour cette semaine.")
    else:
        # Tableau récap
        recap_data = []
        for sal in salaries:
            row_data = {"Salarié": sal}
            for jour in JOURS:
                total = sum(len(v) for v in commandes.get(sal,{}).get(jour,{}).values())
                row_data[jour] = f"✓ {total}" if total else "—"
            recap_data.append(row_data)
        st.table(recap_data)

    st.markdown("---")

    # ── Gestion semaines ──
    st.markdown("### 🗓 Gestion des semaines")
    col1, col2 = st.columns(2)
    with col1:
        new_wk = st.text_input("Créer une nouvelle semaine", placeholder="ex: 2026-S30")
        if st.button("Créer", type="primary") and new_wk.strip():
            wk_new = new_wk.strip()
            if re.match(r'\d{4}-S\d{2}', wk_new):
                if wk_new not in st.session_state.menus:
                    st.session_state.menus[wk_new] = {
                        "semaine": wk_new, "periode": "",
                        "jours": {j:{c:[] for c in CAT_MENU} for j in JOURS}
                    }
                    save_json(MENUS_FILE, st.session_state.menus)
                st.session_state.week_sel = wk_new
                st.success(f"Semaine {week_label(wk_new)} créée.")
                st.rerun()
            else:
                st.error("Format invalide. Utilisez : 2026-S30")
    with col2:
        st.markdown(f"**Semaines disponibles :**")
        for k in weeks_list(st.session_state.menus):
            n_cmds = sum(
                sum(len(v) for v in st.session_state.commandes.get(k,{}).get(sal,{}).values())
                for sal in salaries
            )
            st.markdown(f"- `{k}` — {week_label(k)} — {n_cmds} article(s) commandé(s)")
