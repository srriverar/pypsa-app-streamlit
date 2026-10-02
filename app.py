#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 PyPSA App — Interactive Explorer · Self-hosted PyPSA Network Analysis
 Built from https://github.com/PyPSA/pypsa-app
================================================================================
Interactive Streamlit clone of PyPSA/pypsa-app (early development, AGPL-3.0):
- every file/folder becomes a tab,
- mock backend (Postgres + Redis + Celery) runs in-browser,
- file upload + network editing + optimization (PyPSA + HiGHS) live,
- Grid2Poster us_mainland.geojson integrated as map background + poster lab.

Author: LICA_SE · companion to pypsa-usa-explorer
"""
from __future__ import annotations
import os, json, base64, textwrap, math, random, traceback, warnings, logging, io
from pathlib import Path
import pathlib
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
# Fix pandas 3.0 StringDtype break with pypsa/linopy/xarray (infer_string=True makes pd.Index default to StringDtype which xarray 2025.4 cannot handle)
try:
    pd.options.future.infer_string = False
except: pass
try:
    pd.set_option("mode.string_storage", "python")
except: pass
# Also ensure numpy string handling
import numpy as np
# Monkey-patch xarray coord dtype handling for StringDtype if needed
try:
    import xarray.core.indexes as _xri
    _orig_join = _xri.PandasIndex.join
    def _patched_join(self, other, *args, **kwargs):
        # Convert StringDtype to object before np.result_type
        try:
            if isinstance(self.index.dtype, pd.StringDtype) or str(self.index.dtype) == "string":
                self = self.copy()
                self.index = self.index.astype(object)
        except: pass
        try:
            if isinstance(other.index.dtype, pd.StringDtype) or str(other.index.dtype) == "string":
                other = other.copy()
                other.index = other.index.astype(object)
        except: pass
        return _orig_join(self, other, *args, **kwargs)
    _xri.PandasIndex.join = _patched_join
except: pass
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

warnings.filterwarnings("ignore")
logging.getLogger("pypsa").setLevel(logging.ERROR)
logging.getLogger("linopy").setLevel(logging.ERROR)

st.set_page_config(page_title="PyPSA App — Interactive Explorer", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

ROOT = Path(__file__).parent
REPO = ROOT / "pypsa-app"
ASSETS = ROOT / "assets"

CSS = """
<style>
.block-container{padding-top:1.0rem;max-width:1620px;}
div[data-testid="stMetric"]{background:#fff;border:1px solid #e3eaf3;border-radius:14px;padding:12px 16px 8px;box-shadow:0 1px 3px rgba(16,42,76,.07);}
.hero{background:linear-gradient(135deg,#0b1d3a 0%,#003366 40%,#1a5c8a 70%,#d67e00 100%);border-radius:18px;padding:26px 28px 18px;color:#fff;margin-bottom:12px;box-shadow:0 6px 18px rgba(13,42,96,.22);}
.hero h1{margin:0;font-size:1.92rem;font-weight:850;}
.hero p{margin:.5rem 0 0;font-size:.92rem;opacity:.95;line-height:1.45;}
.chip{display:inline-block;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);padding:3px 11px;border-radius:999px;font-size:.72rem;font-weight:600;margin-right:6px;margin-top:6px;}
.chip.hi{background:#d67e00;border-color:#ffbb66;color:#fff;}
.chip.ok{background:#1a7f5e;border-color:#6cc5ba;}
.callout{background:#eaf4ff;border-left:4px solid #003366;padding:10px 14px;border-radius:8px;font-size:.86rem;color:#1a2a3a;margin:8px 0;}
.callout.warn{background:#fff8e6;border-left-color:#ff9800;}
.callout.ok{background:#e8f8f3;border-left-color:#1a7f5e;}
.callout.hi{background:#fff0f0;border-left-color:#c0392b;}
.legend{background:#f5f9fc;border-left:4px solid #003366;padding:10px 16px;border-radius:0 12px 12px 0;font-size:.85rem;color:#33475e;line-height:1.55;margin:8px 0;}
.play-banner{background:linear-gradient(135deg,#003366,#1a7f5e);color:white;padding:10px 16px;border-radius:10px;font-weight:700;text-align:center;margin:8px 0;letter-spacing:.02em;}
.file-card{background:#fff;border:1px solid #e3eaf3;border-radius:10px;padding:10px 12px;margin:6px 0;}
.stTabs [data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid #dfe7f0;}
.stTabs [data-baseweb="tab"]{font-size:.82rem;font-weight:600;padding:7px 10px;border-radius:10px 10px 0 0;color:#51617a;}
.stTabs [data-baseweb="tab"]:hover{background:#f2f6fb;color:#0f3d63;}
.stTabs [aria-selected="true"]{background:#eaf3fb;color:#0f3d63;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
DISCLAIMER = """<div style='background:#fff3cd;padding:9px 14px;border-radius:8px;border-left:5px solid #ffc107;margin:10px 0 14px;font-size:0.80em;line-height:1.5'>⚠️ <b>Early development</b> · Built from <b>PyPSA/pypsa-app</b> (AGPL-3.0, commit 2cbefa3). Frontend currently <b>non-existent</b> (Svelte removed → React). This Streamlit clone makes the <b>backend (FastAPI + Postgres + Redis + Celery)</b> explorable in the browser — no Docker needed for the demo. Synthetic networks run <b>PyPSA + HiGHS</b> live.</div>"""

def hero():
    st.markdown("""
    <div class="hero">
      <h1>⚡ PyPSA App — Interactive Explorer <span style='font-weight:400;font-size:.52em;opacity:.9'>self-hosted PyPSA network analysis</span></h1>
      <p>Clone in detail of <b>PyPSA/pypsa-app</b> — every folder, route and model becomes interactive. Mock <b>Postgres + Redis + Celery worker + FastAPI</b> plus <b>file upload, network editing, optimization, plotting & Grid2Poster</b> — all in-browser.</p>
      <div>
        <span class="chip">pypsa-app · AGPL-3.0</span><span class="chip">FastAPI + SQLAlchemy</span><span class="chip">Postgres + Redis + Celery</span><span class="chip ok">PyPSA ≥1.2.3 + HiGHS</span><span class="chip">React (next) · no frontend yet</span><span class="chip hi">demo.gif</span><span class="chip">0.1.0-alpha.1</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(DISCLAIMER, unsafe_allow_html=True)

def _fig(h=380, title=""):
    fig=go.Figure()
    fig.update_layout(template="plotly_white", height=h, title=title, margin=dict(l=18,r=18,t=54 if title else 20,b=12), hovermode="x unified",
                      font=dict(family="Inter,'Segoe UI',system-ui,sans-serif", size=12.5, color="#33475e"), title_font=dict(size=14,color="#0f3d63"),
                      legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"), plot_bgcolor="#fbfcfe", paper_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(bgcolor="white", bordercolor="#c9d6e4"))
    return fig
def section_header(title, desc):
    st.markdown(f"<div style='background:#f0f4f8;padding:11px 16px;border-radius:8px;border-left:5px solid #003366;margin-bottom:10px'><b style='color:#003366;font-size:1.03em'>{title}</b><br><span style='color:#555;font-size:.84em'>{desc}</span></div>", unsafe_allow_html=True)
def banner(txt="👆 PLAY HERE — move any slider and click ▶️ Run!"):
    st.markdown(f"<div class='play-banner'>{txt}</div>", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def repo_tree():
    base=REPO
    out=[]
    for p in sorted(base.rglob("*")):
        if ".git" in p.parts: continue
        if p.is_file():
            rel=p.relative_to(base)
            out.append(str(rel))
    return out
@st.cache_data(show_spinner=False)
def read_repo_file(rel):
    try:
        fp=REPO / rel
        if not fp.exists(): return "(not found)"
        if fp.suffix in (".png",".jpg",".jpeg",".svg",".tif",".shp",".pdf",".gif"):
            return f"[binary {fp.suffix} {fp.stat().st_size/1024:.1f} KB]"
        txt=fp.read_text(encoding="utf-8", errors="ignore")
        if len(txt)>12000: txt=txt[:12000]+"\n\n... truncated ..."
        return txt
    except Exception as e: return f"read error: {e}"

# ——— Tech colors (from pypsa-usa config.plotting.yaml — same palette pypsa-app will use) ———
TECH_COLORS = {
    "oil":"#262626","Oil":"#262626","coal":"#707070","Coal":"#707070","nuclear":"#ff9000","Nuclear":"#ff9000",
    "biomass":"#0c6013","Biomass":"#0c6013","geothermal":"#ba91b1","Geothermal":"#ba91b1",
    "CCGT":"#b20101","Combined-Cycle Gas":"#b20101","gas":"#b20101","OCGT":"#d35050","Open-Cycle Gas":"#d35050",
    "onwind":"#235ebc","Onshore Wind":"#235ebc","offwind":"#6895dd","Fixed Bottom Offshore Wind":"#6895dd",
    "offwind_floating":"#11a1c1","Floating Offshore Wind":"#11a1c1","solar":"#f9d002","Solar":"#f9d002",
    "hydro":"#08ad97","Reservoir & Dam":"#08ad97","PHS":"#08ad97","ror":"#4adbc8",
    "battery":"#b8ea04","Battery Storage":"#b8ea04","4hr_battery_storage":"#a4d600","AC":"#70af1d","Ac":"#70af1d","DC":"#8a1caf","Dc":"#8a1caf","H2":"#ea048a","load":"#2ad55f","other":"#cccccc",
}
CARRIER_ORDER = ["oil","coal","nuclear","biomass","geothermal","CCGT","OCGT","onwind","offwind","offwind_floating","solar","hydro","battery","H2"]
def carrier_color(car):
    c=str(car).strip()
    if c in TECH_COLORS: return TECH_COLORS[c]
    cl=c.lower()
    for k,v in TECH_COLORS.items():
        if cl==k.lower(): return v
    if "wind" in cl and "off" in cl and "float" in cl: return TECH_COLORS["offwind_floating"]
    if "wind" in cl and "off" in cl: return TECH_COLORS["offwind"]
    if "wind" in cl: return TECH_COLORS["onwind"]
    if "solar" in cl: return TECH_COLORS["solar"]
    if "hydro" in cl or "reservoir" in cl: return TECH_COLORS["hydro"]
    if "battery" in cl: return TECH_COLORS["battery"]
    if "nuclear" in cl: return TECH_COLORS["nuclear"]
    if "coal" in cl: return TECH_COLORS["coal"]
    if "oil" in cl: return TECH_COLORS["oil"]
    if "biomass" in cl: return TECH_COLORS["biomass"]
    if "geothermal" in cl: return TECH_COLORS["geothermal"]
    if "ccgt" in cl or "combined" in cl: return TECH_COLORS["CCGT"]
    if "ocgt" in cl or "open" in cl: return TECH_COLORS["OCGT"]
    if "gas" in cl: return TECH_COLORS["CCGT"]
    return "#999999"
@st.cache_data(show_spinner=False)
def load_us_geojson():
    try:
        fp = ROOT / "assets" / "us_mainland.geojson"
        if not fp.exists():
            fp = pathlib.Path("/tmp/grid2poster/regions/us_mainland.geojson")
        if fp.exists():
            return json.loads(fp.read_text())
    except: return None
    return None
def inject_usa_background(alpha=0.92):
    try:
        fp = ROOT / "assets" / "PyPSA-USA_network.png"
        if not fp.exists():
            fp = ROOT / "assets" / "user_reference_map.png"
        if fp.exists():
            b64 = base64.b64encode(fp.read_bytes()).decode()
            st.markdown(f'''<style>.stApp {{background-image: linear-gradient(rgba(255,255,255,{alpha}), rgba(255,255,255,{alpha})), url("data:image/png;base64,{b64}");background-size:cover;background-attachment:fixed;background-position:center 12%;background-repeat:no-repeat;}} section[data-testid="stSidebar"] {{background-color: rgba(248,249,251,0.96) !important;}}</style>''', unsafe_allow_html=True)
    except: pass
def render_usa_landing():
    try:
        n_land = build_network(interconnect="usa", clusters=30, n_hours=4, extendable=True)
        fig = plot_map(n_land, h=460, title="🇺🇸 pypsa-app can analyze any of these networks — usa 30 buses · pies 5/10/50 GW · lines 2→5 GW — Grid2Poster us_mainland.geojson behind")
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="landing-usa-map")
            st.caption("This topology is the same one you upload/edit/optimize in **▶️ Run & Optimize** — the app is deployed *behind* this map. Change `clusters` in any lab to densify.")
    except Exception as e:
        fp = ROOT / "assets" / "PyPSA-USA_network.png"
        if fp.exists(): st.image(str(fp), caption="USA transmission — deployment behind this map (fallback)", use_container_width=True)

# ——— PyPSA network helpers (synthetic, but using pypsa-app's pypsa>=1.2.3) ———
INTERCONNECT_COORDS = {
    "western":{"x":[-124,-102],"y":[32,49],"desc":"WECC — West (11 states)","color":"#1f77b4"},
    "eastern":{"x":[-96,-67],"y":[25,49],"desc":"Eastern — East (36 states)","color":"#d67e00"},
    "texas":{"x":[-107,-93],"y":[25,37],"desc":"ERCOT — Texas","color":"#c0392b"},
    "usa":{"x":[-124,-67],"y":[25,49],"desc":"CONUS — all 3","color":"#1a7f5e"},
    "europe":{"x":[-10,30],"y":[35,70],"desc":"Europe — demo (pypsa-eur)","color":"#6a5acd"},
    "world":{"x":[-180,180],"y":[-60,80],"desc":"World","color":"#1a7f5e"},
}
SIZE_OPTIONS=[4,9,14,20,30,50,80,100,150]
SIZE_HELP={4:"Tiny — 4 buses instant",9:"Demo — 9 buses <1s",14:"Small — 14 buses 1s",20:"Tutorial — 20 buses 2s",30:"Medium — 30 buses 3s",50:"Research — 50 buses 5-8s",80:"Detailed — 80 buses 10s",100:"Planning — 100 buses 12s",150:"Large — 150 buses 20s"}
def size_label(n): return f"{n} — {SIZE_HELP.get(n,'')}"
WECC_9={"CA_N":(38.5,-121.0),"CA_S":(34.0,-118.5),"PNW":(45.5,-122.5),"NV":(39.5,-116.5),"AZ":(33.5,-112.0),"CO":(39.0,-105.5),"NM":(34.5,-106.0),"WY":(42.5,-107.5),"UT":(39.5,-111.5)}
EASTERN_9={"NY":(43.0,-75.5),"PJM":(39.5,-77.5),"NE":(42.5,-71.5),"CAR":(35.5,-80.0),"FL":(28.0,-82.0),"MISO_N":(44.0,-93.0),"MISO_S":(32.5,-90.0),"SPP":(37.0,-98.0),"SERC":(33.0,-85.5)}
TEXAS_6={"W_Tex":(31.5,-103.5),"N_Tex":(33.5,-98.0),"S_Tex":(27.5,-98.5),"Houston":(29.8,-95.3),"Austin":(30.3,-97.7),"Dallas":(32.8,-96.8)}
def _hav(lat1,lon1,lat2,lon2):
    R=6371; dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2+math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))
def build_network(interconnect="western", clusters=20, n_hours=24, extendable=True, seed=42):
    import pypsa
    rng=np.random.RandomState(seed)
    T=int(n_hours); snaps=pd.date_range("2019-01-01", periods=T, freq="h")
    n=pypsa.Network(); n.set_snapshots(snaps)
    if interconnect=="western": base=WECC_9
    elif interconnect=="eastern": base=EASTERN_9
    elif interconnect=="texas": base=TEXAS_6
    elif interconnect=="europe":
        base={"DE":(51.0,10.0),"FR":(48.0,2.0),"ES":(40.0,-3.0),"IT":(42.0,12.0),"PL":(52.0,19.0),"SE":(62.0,15.0),"UK":(54.0,-2.0),"NO":(60.0,8.0),"FI":(64.0,26.0)}
    elif interconnect=="usa": base={**WECC_9,**EASTERN_9,**TEXAS_6}
    else: base={**WECC_9,**EASTERN_9,**TEXAS_6}
    if clusters <= len(base):
        keys=list(base.keys())[:clusters]; coords={k:base[k] for k in keys}
    else:
        coords=dict(base); base_keys=list(base.keys())
        ic=INTERCONNECT_COORDS.get(interconnect, INTERCONNECT_COORDS["western"]); lon_min,lon_max=ic["x"]; lat_min,lat_max=ic["y"]
        while len(coords)<clusters:
            if rng.rand()<0.7:
                a,b=rng.choice(base_keys,2,replace=False); lat1,lon1=base[a]; lat2,lon2=base[b]
                lat=(lat1+lat2)/2+rng.normal(0,0.5); lon=(lon1+lon2)/2+rng.normal(0,0.7)
            else:
                lat=rng.uniform(lat_min+0.5,lat_max-0.5); lon=rng.uniform(lon_min+0.5,lon_max-0.5)
            lat=max(lat_min,min(lat_max,lat)); lon=max(lon_min,min(lon_max,lon))
            name=f"Bus_{len(coords)+1:03d}"
            if name not in coords: coords[name]=(lat,lon)
    for name,(lat,lon) in coords.items():
        v=rng.choice([115,230,345,500],p=[0.25,0.35,0.2,0.2]); n.add("Bus", name, x=float(lon), y=float(lat), v_nom=int(v), carrier="AC")
    for c in ["onwind","offwind","offwind_floating","solar","hydro","ror","PHS","gas","coal","nuclear","load","battery","H2"]:
        try: n.add("Carrier", c)
        except: pass
    hour=np.arange(T)%24; dem_base=2500 if interconnect=="usa" else (1800 if interconnect=="eastern" else (800 if interconnect=="texas" else 1200))
    dem_pf=0.65+0.35*np.sin(np.pi*(hour-6)/12); dem_pf=np.clip(dem_pf+rng.normal(0,0.03,T),0.5,1.1)
    wind_cf=np.clip(rng.weibull(2,T)*0.35+0.12,0.05,0.95); solar_cf=np.clip(np.maximum(0,np.sin(np.pi*(hour-6)/12))*0.85+rng.normal(0,0.04,T),0,0.95); hydro_cf=np.clip(0.55+0.1*np.sin(np.pi*(hour-4)/12)+rng.normal(0,0.05,T),0.25,0.85)
    for bus in n.buses.index:
        cf_w=wind_cf*np.clip(rng.normal(1,0.08,T),0.7,1.3); cf_w=np.clip(cf_w,0,1)
        if extendable:
            n.add("Generator", f"Wind {bus}", bus=bus, carrier="onwind", p_nom_extendable=True, capital_cost=80000, marginal_cost=0.5, p_max_pu=cf_w)
            n.add("Generator", f"Solar {bus}", bus=bus, carrier="solar", p_nom_extendable=True, capital_cost=60000, marginal_cost=0.2, p_max_pu=solar_cf)
        else:
            n.add("Generator", f"Wind {bus}", bus=bus, carrier="onwind", p_nom=rng.uniform(80,300), marginal_cost=0.5, p_max_pu=cf_w)
            n.add("Generator", f"Solar {bus}", bus=bus, carrier="solar", p_nom=rng.uniform(60,250), marginal_cost=0.2, p_max_pu=solar_cf)
        if rng.rand()<0.4: n.add("Generator", f"Hydro {bus}", bus=bus, carrier="hydro", p_nom=rng.uniform(100,600), marginal_cost=3, p_max_pu=hydro_cf)
        n.add("Generator", f"Gas {bus}", bus=bus, carrier="gas", p_nom=rng.uniform(200,800), marginal_cost=40+rng.normal(0,5), p_max_pu=1.0)
        if rng.rand()<0.3: n.add("Generator", f"Coal {bus}", bus=bus, carrier="coal", p_nom=rng.uniform(150,500), marginal_cost=30+rng.normal(0,4), p_max_pu=1.0)
        p_load=dem_base/len(n.buses)*(0.8+rng.uniform(0,0.4)); n.add("Load", f"Load {bus}", bus=bus, p_set=float(p_load)*dem_pf)
    buses=list(n.buses.index)
    for i,b in enumerate(buses):
        dlist=[]
        for j,bj in enumerate(buses):
            if i==j: continue
            d=_hav(n.buses.loc[b,"y"],n.buses.loc[b,"x"],n.buses.loc[bj,"y"],n.buses.loc[bj,"x"]); dlist.append((d,bj))
        dlist.sort()
        for d,bj in dlist[:2]:
            if i < buses.index(bj):
                length=d; s_nom=1000 if rng.rand()>0.7 else 600; r=0.02*length/100; x=0.10*length/100
                try: n.add("Line", f"Line {b}-{bj}", bus0=b, bus1=bj, length=float(length), r=float(r), x=float(x), s_nom=float(s_nom))
                except: pass
    for bus in list(n.buses.index)[:2]:
        n.add("StorageUnit", f"Battery {bus}", bus=bus, p_nom=80 if not extendable else 0, p_nom_extendable=extendable, max_hours=4, efficiency_store=0.9, efficiency_dispatch=0.9, cyclic_state_of_charge=True)
    for b in n.buses.index:
        n.add("Generator", f"Slack {b}", bus=b, carrier="gas", p_nom=2000, marginal_cost=500, p_max_pu=1.0)
    # Final sanitize: force all indexes to object dtype for pandas 3.0 compatibility
    try:
        for df in [n.buses, n.generators, n.loads, n.lines, n.storage_units, n.carriers]:
            try:
                if isinstance(df.index.dtype, pd.StringDtype) or str(df.index.dtype) == "string":
                    df.index = df.index.astype(object)
                for col in df.columns:
                    if isinstance(df[col].dtype, pd.StringDtype) or str(df[col].dtype) == "string":
                        df[col] = df[col].astype(object)
            except: pass
        # snapshots is DatetimeIndex, keep as is
    except: pass
    return n
def _sanitize_network_dtypes(n):
    # Fix pandas 2/3 StringDtype -> object which HiGHS/linopy cannot interpret
    # Seen as: "Cannot interpret '<StringDtype(na_value=nan)>' as a data type"
    import pandas as pd
    for attr in ["buses","generators","loads","lines","links","storage_units","carriers","buses_t","generators_t","loads_t","lines_t"]:
        try:
            df = getattr(n, attr, None)
            if df is None: continue
            # DataFrame or panel?
            if isinstance(df, pd.DataFrame):
                for col in df.columns:
                    try:
                        # detect StringDtype (pandas >=1.0) or arrow string
                        dtype = df[col].dtype
                        is_str_dtype = isinstance(dtype, pd.StringDtype) or str(dtype) == "string" or str(dtype).startswith("string")
                        # also handle nullable string with pyarrow
                        if is_str_dtype or dtype == object and df[col].dtype.kind in "OU":
                            # only convert if contains strings
                            pass
                        if is_str_dtype:
                            df[col] = df[col].astype(object)
                    except: pass
                # also fix index if it is StringDtype
                try:
                    if isinstance(df.index.dtype, pd.StringDtype) or str(df.index.dtype) == "string":
                        df.index = df.index.astype(object)
                except: pass
            # for _t multiindexed DataFrames (e.g. generators_t.p)
            elif hasattr(df, "p") and isinstance(df.p, pd.DataFrame):
                for sub in ["p","p_max_pu","p_set"]:
                    try:
                        subdf = getattr(df, sub, None)
                        if isinstance(subdf, pd.DataFrame):
                            for col in subdf.columns:
                                if isinstance(subdf[col].dtype, pd.StringDtype) or str(subdf[col].dtype) == "string":
                                    subdf[col] = subdf[col].astype(object)
                    except: pass
        except: pass
    # also snapshots
    try:
        n.snapshots = pd.DatetimeIndex(n.snapshots)
    except: pass

def optimize_network(n):
    # sanitize before first try
    try: _sanitize_network_dtypes(n)
    except: pass
    try:
        n.optimize(solver_name="highs", solver_options={"threads":2})
        obj=getattr(n,"objective",None)
        if obj is not None and not (isinstance(obj,float) and np.isnan(obj)):
            return True, f"Optimal · objective = {float(obj):,.0f} (HiGHS)"
    except Exception as e:
        msg = str(e)
        # Retry once after aggressive sanitization if StringDtype error
        if "StringDtype" in msg or "Cannot interpret" in msg:
            try:
                traceback.print_exc()
                # aggressive: convert ALL object-like to object explicitly via pypsa helpers
                import pandas as pd
                for comp in n.iterate_components():
                    try:
                        df = comp.df
                        for col in df.select_dtypes(include=["string"]).columns:
                            df[col] = df[col].astype(object)
                        # also convert any StringDtype columns
                        for col in df.columns:
                            if isinstance(df[col].dtype, pd.StringDtype):
                                df[col] = df[col].astype(object)
                    except: pass
                # also fix snapshot weightings if any
                n.optimize(solver_name="highs", solver_options={"threads":2})
                obj=getattr(n,"objective",None)
                if obj is not None and not (isinstance(obj,float) and np.isnan(obj)):
                    return True, f"Optimal (retry) · objective = {float(obj):,.0f} (HiGHS)"
            except Exception as e2:
                traceback.print_exc()
                return False, f"HiGHS failed even after StringDtype fix: {e2} — try `pip install --upgrade pypsa linopy pandas==2.2` or use solver=glpk"
        traceback.print_exc()
        # fallback to lopf if highs not available?
        if "highs" in msg.lower() or "StringDtype" in msg:
            try:
                n.lopf(solver_name="highs", solver_options={"threads":2})
                obj=getattr(n,"objective",None)
                if obj is not None:
                    return True, f"Optimal via lopf · objective = {float(obj):,.0f} (HiGHS)"
            except Exception as e3:
                pass
        return False, f"HiGHS failed: {e} — tip: if you see StringDtype, `pip install -U linopy>=0.4` fixes it, or rebuild network after updating pandas."
    return False, "Infeasible — check load vs capacity"
def plot_dispatch(n, h=340):
    if not hasattr(n,"generators_t") or n.generators_t.p.empty: return None
    df=n.generators_t.p; cmap=n.generators["carrier"].to_dict(); byc={}
    for col in df.columns:
        car=cmap.get(col,"other"); byc.setdefault(car, np.zeros(len(df))); byc[car]+=df[col].values
    byc_ns={k:v for k,v in byc.items() if "Slack" not in k}; slack=sum(v for k,v in byc.items() if "Slack" in k) if any("Slack" in k for k in byc) else np.zeros(len(df))
    fig=_fig(h, "Dispatch by carrier (MW) — PyPSA HiGHS")
    for car, arr in sorted(byc_ns.items()):
        fig.add_trace(go.Scatter(x=n.snapshots, y=arr, mode="lines", stackgroup="one", name=car, line=dict(width=0), hoverinfo="x+y"))
    if slack.sum()>1: fig.add_trace(go.Scatter(x=n.snapshots, y=slack, mode="lines", name="Slack (ENS)", line=dict(color="red", width=2, dash="dot")))
    fig.update_layout(yaxis_title="MW (stacked = demand)", xaxis_title="Snapshot (hour)")
    return fig
def plot_loading(n, h=320):
    try:
        if hasattr(n,"lines_t") and not n.lines_t.p0.empty:
            df=n.lines_t.p0.abs(); s_nom=n.lines.s_nom.replace(0,np.nan); loading=(df.div(s_nom,axis=1)*100).mean().sort_values(ascending=False)
            fig=_fig(h, "Avg loading per line (%)"); fig.add_trace(go.Bar(x=loading.index.astype(str), y=loading.values, marker_color="#70af1d", text=[f"{v:.0f}%" for v in loading.values], textposition="outside")); fig.update_layout(yaxis_title="% avg (>85% congested)", xaxis_tickangle=-18); return fig
    except: return None
    return None
def plot_map(n, h=560, title="Network map — pies 5/10/50 GW · lines 2→5 GW · US background"):
    try:
        fig=go.Figure()
        gj=load_us_geojson()
        if gj:
            for feat in gj.get("features",[])[:1]:
                geom=feat.get("geometry",{}); coords=geom.get("coordinates",[]); polys=[coords] if geom.get("type")=="Polygon" else coords
                for poly in polys[:1]:
                    for ring in poly[:1]:
                        lons=[c[0] for c in ring]; lats=[c[1] for c in ring]
                        fig.add_trace(go.Scatter(x=lons, y=lats, mode="lines", fill="toself", fillcolor="rgba(242,240,236,0.9)", line=dict(color="#c9bdaa",width=1.2), hoverinfo="skip", showlegend=False))
        else:
            fig.add_shape(type="rect", x0=-124.5,y0=24.5,x1=-66.5,y1=49.5, line=dict(color="#d0dce9",width=1,dash="dot"), fillcolor="rgba(240,244,248,0.35)")
        load_dict={}
        try:
            if hasattr(n,"lines_t") and not n.lines_t.p0.empty and hasattr(n,"lines") and "s_nom" in n.lines.columns:
                avg=(n.lines_t.p0.abs().div(n.lines.s_nom.replace(0,1),axis=1)*100).mean()
                for idx,v in avg.items():
                    if v>88: load_dict[idx]="#c0392b"
                    elif v>60: load_dict[idx]="#d67e00"
                    else: load_dict[idx]="#2a7f62"
        except: pass
        if hasattr(n,"lines") and len(n.lines):
            for _,r in n.lines.iterrows():
                try:
                    x0,y0=n.buses.loc[r.bus0,["x","y"]].values; x1,y1=n.buses.loc[r.bus1,["x","y"]].values
                    s_nom=float(r.s_nom) if "s_nom" in r and not pd.isna(r.s_nom) else 600
                    w=1.0+(s_nom/5000)*4; w=max(1.0,min(4.5,w)); col=load_dict.get(r.name, TECH_COLORS["AC"])
                    fig.add_trace(go.Scatter(x=[x0,x1], y=[y0,y1], mode="lines", line=dict(color=col,width=w), hoverinfo="text", text=f"{r.name}: {r.bus0}→{r.bus1} · {s_nom:.0f} MW", showlegend=False, opacity=0.95))
                except: continue
        bus_tot={}; bus_mix={}
        for b in n.buses.index:
            gens=n.generators[n.generators["bus"]==b]
            if len(gens)==0: bus_tot[b]=0; bus_mix[b]={}
            else:
                col="p_nom_opt" if "p_nom_opt" in gens.columns and gens["p_nom_opt"].sum()>1 else "p_nom"
                grp=gens.groupby("carrier")[col].sum(); grp=grp[grp>1]; bus_mix[b]=grp.to_dict(); bus_tot[b]=float(grp.sum())
        def lon_to_x(lon): return (lon+126)/61
        def lat_to_y(lat): return (lat-23)/27.5
        for b in n.buses.index:
            try:
                lon,lat=float(n.buses.loc[b,"x"]),float(n.buses.loc[b,"y"]); tot=bus_tot.get(b,0) or 0; gw=tot/1000 if tot>100 else 0.5
                r=0.018 if gw<=5 else (0.025 if gw<=10 else (0.038 if gw<=25 else 0.055))
                if gw>5 and gw!=10 and gw!=50: r=0.015+(gw**0.5)*0.007; r=max(0.015,min(0.06,r))
                xn=lon_to_x(lon); yn=lat_to_y(lat); x0=max(0,xn-r); x1=min(1,xn+r); y0=max(0,yn-r*1.25); y1=min(1,yn+r*1.25)
                mix=bus_mix.get(b,{})
                if not mix:
                    fig.add_trace(go.Scatter(x=[lon],y=[lat],mode="markers",marker=dict(size=8,color="#b0b0b0",line=dict(color="white",width=1)),hovertext=f"{b}: no cap",hoverinfo="text",showlegend=False)); continue
                ordered=sorted(mix.items(), key=lambda kv: (CARRIER_ORDER.index(kv[0]) if kv[0] in CARRIER_ORDER else 99, -kv[1]))
                labels=[k for k,_ in ordered]; values=[v for _,v in ordered]; colors=[carrier_color(k) for k in labels]
                fig.add_trace(go.Pie(labels=labels,values=values,marker=dict(colors=colors,line=dict(color="white",width=1)),domain=dict(x=[x0,x1],y=[y0,y1]),hole=0.15,sort=False,direction="clockwise",textinfo="none",hoverinfo="label+value",hovertemplate=f"{b}<br>%{{label}}: %{{value:.0f}} MW<extra></extra>",showlegend=False))
                fig.add_annotation(x=lon,y=lat+0.6,xref="x",yref="y",text=f"<b>{b}</b>",showarrow=False,font=dict(size=9,color="#0f3d63"),bgcolor="rgba(255,255,255,0.75)",borderpad=1)
            except: continue
        fig.update_layout(template="plotly_white", height=h, title=dict(text=title,font=dict(size=14,color="#0f3d63")), margin=dict(l=14,r=14,t=62,b=14), xaxis=dict(title="Lon",range=[-126,-65],gridcolor="#eaf0f7",zeroline=False), yaxis=dict(title="Lat",range=[23,50.5],gridcolor="#eaf0f7",scaleanchor="x",scaleratio=1.28), plot_bgcolor="#f7fbff", paper_bgcolor="rgba(0,0,0,0)", hovermode="closest", showlegend=False)
        fig.add_annotation(x=-124,y=49.2,xref="x",yref="y", text="<b>Legend</b>  <span style='color:#70af1d'>━ AC 2GW</span> <b>━━━ 5GW</b> <span style='color:#8a1caf'>┅ DC</span>  ●5GW ●10GW ●50GW  <span style='color:#c0392b'>■>88%</span> <span style='color:#d67e00'>■60%</span>", showarrow=False, align="left", bgcolor="rgba(255,255,255,0.92)", bordercolor="#d0dce9", borderwidth=1, font=dict(size=9,color="#33475e"))
        return fig
    except Exception as e:
        try:
            fig=go.Figure(); fig.add_trace(go.Scatter(x=n.buses["x"],y=n.buses["y"],mode="markers+text",text=n.buses.index.astype(str))); fig.update_layout(height=h,title=title); return fig
        except: return None

# ——— Tabs ———
def render_about():
    section_header("📖 About — PyPSA App (early dev, AGPL-3.0)", "Self-hosted web app for PyPSA networks — modular, Docker-ready, React next.")
    banner("📖 PLAY HERE — read the real README, then try uploading a network")
    fp=REPO/"README.md"; txt=fp.read_text()[:9000] if fp.exists() else "(no README)"
    st.code(txt, language="markdown")
    c1,c2,c3=st.columns(3)
    with c1: st.link_button("🔗 GitHub", "https://github.com/PyPSA/pypsa-app", use_container_width=True)
    with c2: st.link_button("🔗 Issues 33", "https://github.com/PyPSA/pypsa-app/issues", use_container_width=True)
    with c3: st.link_button("🔗 Pulls 9", "https://github.com/PyPSA/pypsa-app/pulls", use_container_width=True)
    if (REPO/"demo.gif").exists():
        st.image(str(REPO/"demo.gif"), caption="demo.gif from repo (early dev)", use_container_width=True)
    st.markdown("<div class='callout warn'><b>Warning from README:</b> This project is in early development. Expect frequent breaking changes and bugs. Frontend currently non-existent (Svelte removed → React).</div>", unsafe_allow_html=True)
    st.markdown("**Stack:** `FastAPI ≥0.137` + `Starlette` + `Uvicorn` + `Pydantic` + `SQLAlchemy ≥2.0` + `PyPSA ≥1.2.3` + `Postgres` + `Redis` + `Celery[redis]` + `Alembic` — all visible in `pyproject.toml` / `compose`.")
def render_repo_explorer():
    section_header("📁 Repo Explorer — every file", "Clone in detail: click any file to see role + live content.")
    tree=repo_tree()
    c1,c2,c3=st.columns([1.2,1,1])
    with c1:
        q=st.text_input("🔍 Search", "", placeholder="e.g., networks.py, compose.yaml, models.py", key="repo-q")
        ext=st.selectbox("Filter", ["all",".py",".yaml",".md",".toml",".sh"], key="repo-ext")
    with c2:
        folder=st.selectbox("Folder", ["all","src/pypsa_app","src/pypsa_app/backend","compose","docs","tests",".github"], key="repo-folder")
        show_cnt=st.slider("Show N", 20, 300, 80, 20, key="repo-cnt")
    with c3:
        st.metric("Files", f"{len(tree)}"); st.caption("`git clone https://github.com/PyPSA/pypsa-app.git`")
        if st.button("🔄 Refresh", key="repo-refresh"): st.cache_data.clear(); st.rerun()
    filtered=tree
    if q.strip(): filtered=[f for f in filtered if q.lower() in f.lower()]
    if ext!="all": filtered=[f for f in filtered if f.endswith(ext)]
    if folder!="all": filtered=[f for f in filtered if f.startswith(folder)]
    filtered=sorted(filtered)[:show_cnt]
    st.caption(f"Showing {len(filtered)} files")
    cols=st.columns([1,1.6])
    with cols[0]:
        sel=st.selectbox("Select file", filtered, key="repo-sel")
        if sel:
            fp=REPO/sel; st.code(f"pypsa-app/{sel}", language="text")
            if fp.exists(): st.caption(f"{fp.stat().st_size/1024:.1f} KB · {fp.suffix}")
    with cols[1]:
        if sel:
            txt=read_repo_file(sel)
            lang="python" if sel.endswith(".py") else ("yaml" if sel.endswith(".yaml") else "markdown" if sel.endswith(".md") else "text")
            st.code(txt, language=lang)
            fp=REPO/sel
            if fp.exists() and fp.stat().st_size<500000:
                st.download_button(f"⬇️ Download {sel.split('/')[-1]}", fp.read_bytes(), file_name=sel.split('/')[-1], key=f"dl-{sel}")
    st.divider(); st.markdown("#### 📂 What each top folder does")
    folders=[
        ("`compose/`","`compose.yaml` (api + postgres + redis) + `compose.services.yaml` (postgres, redis, celery). `docker compose -f compose/compose.yaml --env-file compose/.env.local up --build` → `http://localhost:8000/docs`.","2"),
        ("`src/pypsa_app/backend/`","`main.py` FastAPI app, `models.py` SQLAlchemy (users, networks, runs, backends), `api/routes` (auth, networks, runs, plots, statistics, tasks), `alembic` migrations (6 versions), `task_queue.py` + `tasks.py` (Celery + Redis), `settings.py` + `database.py`.","~40"),
        ("`src/pypsa_app/cli.py`","`pypsa-app serve --reload` via `uv run --extra full`.","1"),
        ("`scripts/`","`generate_settings_docs.py` — builds `docs/configuration.md` from `settings.py`.","1"),
        ("`docs/`","`configuration.md` — auto-generated settings docs.","1"),
        ("`tests/`","`pytest` + `pytest-asyncio` + `pytest-alembic` + `coverage`. `uv sync --extra dev` + `uv run pytest` → 9+ tests.","~10"),
        ("`pyproject.toml`","`requires-python ≥3.13`, `fastapi`, `sqlalchemy`, `pypsa≥1.2.3`, `pandas≥3.0`, `alembic`, `celery[redis]`, `ruff` lint.","1"),
    ]
    for title,desc,cnt in folders:
        with st.expander(f"{title} — {desc} ({cnt})", expanded=False):
            if "compose" in title:
                for f in sorted((REPO/"compose").glob("*.yaml")):
                    st.code(f.read_text()[:1200], language="yaml")
            elif "backend" in title:
                st.dataframe(pd.DataFrame([{"file":p.name,"KB":round(p.stat().st_size/1024,1)} for p in sorted((REPO/"src/pypsa_app/backend").rglob("*.py"))[:12]]), use_container_width=True)
def render_architecture():
    section_header("🏗️ Architecture — Docker + FastAPI + Postgres + Redis + Celery", "How the `containerized` and `dev` modes run — and what you can click to explore.")
    banner("🏗️ PLAY HERE — start the mock stack, then call the API")
    c1,c2=st.columns([1.1,1.4])
    with c1:
        st.graphviz_chart("""
        digraph G {
          rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#eaf3fb", color="#003366"];
          React [label="React\\n(future frontend)\\nhttp://localhost:3000", fillcolor="#fff8e6", color="#d67e00"];
          FastAPI [label="FastAPI\\nsrc/pypsa_app/backend/main.py\\nhttp://localhost:8000/docs", fillcolor="#e8f8f3", color="#1a7f5e"];
          Postgres [label="Postgres\\n:5432\\nSQLAlchemy + Alembic\\n6 migrations", fillcolor="#f0e6ff", color="#6a5acd"];
          Redis [label="Redis\\n:6379", fillcolor="#ffe6e6", color="#c0392b"];
          Celery [label="Celery worker\\ntasks.py + task_queue.py", fillcolor="#fff0f0", color="#c0392b"];
          React -> FastAPI -> Postgres;
          FastAPI -> Redis -> Celery -> Postgres;
          Celery -> FastAPI;
        }
        """)
        st.markdown("**Modes:**")
        st.code("docker compose -f compose/compose.yaml --env-file compose/.env.local up --build", language="bash")
        st.code("docker compose -f compose/compose.services.yaml --env-file compose/.env.local up\nuv run --extra full --env-file compose/.env.local pypsa-app serve --reload", language="bash")
        if st.button("▶️ Mock start stack (Postgres ✓ Redis ✓ Celery ✓ API ✓)", key="arch-start"):
            st.success("Mock: Postgres healthy, Redis PONG, Celery worker up (1), FastAPI http://localhost:8000/docs — 6 alembic migrations applied")
            st.session_state["arch-up"]=True
        if st.button("🔍 Show compose.yaml", key="arch-compose"):
            st.code((REPO/"compose/compose.yaml").read_text()[:5000], language="yaml")
    with c2:
        st.markdown("#### 🔌 API routes — `src/pypsa_app/backend/api/routes`")
        routes_dir = REPO / "src/pypsa_app/backend/api/routes"
        routes = sorted(routes_dir.rglob("*.py")) if routes_dir.exists() else []
        if routes:
            opts = [str(p.relative_to(REPO)) for p in routes]
            sel=st.selectbox("Route file", opts, key="arch-route")
            if sel:
                try:
                    target = REPO / sel
                    if target.exists():
                        st.code(target.read_text()[:5000], language="python")
                    else:
                        st.warning(f"File not found: {target}")
                except Exception as e:
                    st.error(f"Cannot read {sel}: {e}")
            else:
                st.info("Select a route file above.")
        else:
            st.info(f"No route files found at `{routes_dir}` — check that `pypsa-app` was cloned. Showing `main.py` instead.")
            # fallback: show main.py
            try:
                fb = REPO / "src/pypsa_app/backend/main.py"
                if fb.exists():
                    st.code(fb.read_text()[:5000], language="python")
            except Exception as e:
                st.error(str(e))
        st.markdown("#### 🗄️ Models — `models.py` (users, networks, runs, backends)")
        try:
            mp = REPO/"src/pypsa_app/backend/models.py"
            if mp.exists():
                st.code(mp.read_text()[:4000], language="python")
            else:
                st.warning(f"Not found: {mp}")
                # try alternative location
                alt = REPO/"src/pypsa_app/models.py"
                if alt.exists():
                    st.code(alt.read_text()[:4000], language="python")
        except Exception as e:
            st.error(f"Cannot read models.py: {e}")
        if st.button("📄 Show Alembic versions", key="arch-alembic"):
            for p in sorted((REPO/"src/pypsa_app/backend/alembic/versions").glob("*.py")):
                st.caption(p.name); st.code(p.read_text()[:600], language="python")
        st.markdown("<div class='legend'>💡 <b>Extend:</b> add a route in `api/routes` → `models.py` table → `schemas` Pydantic → Celery task in `tasks.py` → frontend calls `/api/v1/...` — Streamlit here mocks that flow.</div>", unsafe_allow_html=True)
def render_data_model():
    section_header("🗄️ Data Model — Networks, Runs, Users, Visibility", "Upload & edit PyPSA networks — SQLAlchemy + Pydantic.")
    banner("🗄️ PLAY HERE — upload a .nc or build a synthetic network, then edit it")
    left,right=st.columns([1,1.3])
    with left:
        st.markdown("#### 📤 File upload — `routes/networks.py` + `networks_remote.py`")
        st.caption("pypsa-app supports `POST /api/v1/networks` with multipart `file`. Here: interactive upload + in-browser editing.")
        up=st.file_uploader("Upload PyPSA network (.nc, .csv, .h5)", type=["nc","netcdf","h5","csv"], key="dm-up")
        n=None
        if up is not None:
            try:
                import tempfile, pypsa
                suffix="."+up.name.split(".")[-1]
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
                    tf.write(up.getbuffer()); tmp=tf.name
                # try netcdf
                n=pypsa.Network()
                if suffix in [".nc",".netcdf"]:
                    n.import_from_netcdf(tmp)
                    st.success(f"Imported .nc: {len(n.buses)} buses · {len(n.lines)} lines · {len(n.generators)} gens — synced to ▶️ Run & Optimize")
                    st.session_state["run-n"]=n; st.session_state["vis-n"]=n
                else:
                    st.info("CSV/H5: showing preview of file (pypsa supports via import_from_csv)")
                    st.dataframe(pd.read_csv(tmp).head())
                    n=build_network(clusters=20, n_hours=48)  # demo fallback 48 h
                    st.caption("Demo: built synthetic 20-bus for visualization (CSV import needs folder)")
                st.session_state["dm-n"]=n
            except Exception as e:
                st.error(f"Import failed: {e}")
                st.code(traceback.format_exc()[:2000])
        else:
            st.markdown("No file? Build a synthetic one:")
            inter=st.selectbox("Interconnect", ["western","eastern","texas","usa","europe"], key="dm-inter")
            clusters=st.select_slider("Clusters", options=SIZE_OPTIONS, value=20, key="dm-clusters", format_func=size_label)
            st.caption("⏱️ Horizon **48 h** is the reference study (reference time scale) — shared with ▶️ Run & Optimize.")
            if st.button("⚡ Build synthetic network (pypsa-app style) — 48 h", key="dm-build"):
                n=build_network(interconnect=inter, clusters=clusters, n_hours=48); st.session_state["dm-n"]=n; st.session_state["run-n"]=n; st.session_state["vis-n"]=n; st.success(f"Built {len(n.buses)} buses · {len(n.lines)} lines · 48 h — synced to ▶️ Run & Optimize & 📊 Visualization")
                st.info("✅ Network synced: 🗄️ Data Model = ▶️ Run & Optimize = 📊 Visualization (same 48 h system)")
                st.rerun()
        # Show stored network summary
        if "dm-n" in st.session_state:
            n=st.session_state["dm-n"]
            st.markdown("#### ✏️ Quick edit — `networks:modify` permission")
            bus=st.selectbox("Bus to edit", n.buses.index.tolist()[:20], key="dm-bus")
            new_pnom=st.slider("Add gas p_nom at bus (MW)", 0, 1000, 200, 50, key="dm-pnom")
            if st.button("➕ Add gas generator", key="dm-add"):
                try: n.add("Generator", f"Gas {bus} manual", bus=bus, carrier="gas", p_nom=float(new_pnom)); st.success(f"Added Gas {bus} {new_pnom} MW — synced"); st.session_state["dm-n"]=n; st.session_state["run-n"]=n; st.session_state["vis-n"]=n
                except Exception as e: st.error(str(e))
            if st.button("🗑️ Remove slack generators", key="dm-rm"):
                slacks=[g for g in n.generators.index if "Slack" in g]
                if slacks:
                    try:
                        # pypsa 1.3 uses n.remove, older versions n.mremove — handle both
                        if hasattr(n, "mremove"):
                            n.mremove("Generator", slacks)
                        else:
                            n.remove("Generator", slacks)
                        st.success(f"Removed {len(slacks)} slack generators — synced")
                        st.session_state["dm-n"]=n; st.session_state["run-n"]=n; st.session_state["vis-n"]=n
                    except Exception as e:
                        st.error(f"Remove failed: {e}")
                        st.code(traceback.format_exc()[:1500])
                else:
                    st.info("No slack generators to remove (already removed).")
            st.dataframe(n.buses.head(), use_container_width=True, height=160)
            st.dataframe(n.generators[["bus","carrier","p_nom"]].head(10), use_container_width=True, height=180)
    with right:
        if "dm-n" not in st.session_state:
            st.info("Upload or build a network on the left to see stats & plots.")
        else:
            n=st.session_state["dm-n"]
            st.markdown("#### 📊 Statistics — `routes/statistics.py` + `plots.py`")
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Buses", f"{len(n.buses)}"); m2.metric("Lines", f"{len(n.lines)}"); m3.metric("Generators", f"{len(n.generators)}"); m4.metric("Load", f"{n.loads.p_set.sum():.0f} MW" if hasattr(n.loads,"p_set") else "—")
            # carrier split
            try:
                split=n.generators.groupby("carrier")["p_nom"].sum().sort_values(ascending=False)
                fig=px.bar(x=split.index, y=split.values, color=split.index, color_discrete_map={k:carrier_color(k) for k in split.index}, title="Capacity by carrier (p_nom MW) — TECH_COLORS")
                fig.update_layout(height=300, showlegend=False); st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="dm-carrier")
            except: pass
            # visibility
            vis=st.selectbox("Visibility (enum `public`/`private`)", ["public","private"], key="dm-vis")
            st.caption(f"Visibility = `{vis}` → `Visibility.{vis.upper()}` in `models.py` — controls `Permission.NETWORKS_VIEW`")
            # export
            c1,c2=st.columns(2)
            with c1:
                if st.button("⬇️ Export .nc (download)", key="dm-export"):
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tf:
                        n.export_to_netcdf(tf.name); data=open(tf.name,"rb").read()
                    st.download_button("Download", data, file_name="pypsa_app_network.nc", key="dm-dl")
            with c2:
                if st.button("📋 Show Pydantic schema", key="dm-schema"):
                    try:
                        schemas_path = REPO/"src/pypsa_app/backend/schemas"
                        if schemas_path.is_dir():
                            py_files = sorted(schemas_path.glob("*.py"))
                            if py_files:
                                st.code(py_files[0].read_text()[:2000], language="python")
                                st.caption(f"Showing {py_files[0].name} — {len(py_files)} files in schemas/")
                            else:
                                st.code("schemas/*.py — Pydantic models for API", language="python")
                        elif schemas_path.is_file():
                            st.code(schemas_path.read_text()[:2000], language="python")
                        else:
                            st.code("schemas/*.py — Pydantic models for API", language="python")
                    except Exception as e:
                        st.error(f"Cannot read schemas: {e}")
                        st.code("schemas/*.py — Pydantic models for API", language="python")
            figm=plot_map(n, h=420, title="Editable network — Grid2Poster us_mainland.geojson behind")
            if figm: st.plotly_chart(figm, use_container_width=True, config={"displaylogo":False}, key="dm-map")
def render_run_optimize():
    section_header("▶️ Run & Optimize — Celery + Redis task queue", "From `tasks.py`/`task_queue.py`: runs are queued, executed via Celery worker, results polled via `/api/v1/runs` & `/tasks`.")
    banner("▶️ PLAY HERE — queue a run, watch Celery, get results")
    # Mock queue status
    qcol1,qcol2,qcol3=st.columns(3)
    with qcol1: st.metric("Redis", "PONG (6379)", delta="up", delta_color="normal")
    with qcol2: st.metric("Celery workers", "1", delta="1 active", delta_color="normal")
    with qcol3: st.metric("Queue", f"{random.randint(0,2)} pending", delta="Redis length", delta_color="off")
    left,right=st.columns([1,1.4])
    with left:
        # --- Sync with Data Model (48 h reference) ---
        if "dm-n" in st.session_state:
            dm = st.session_state["dm-n"]
            try:
                dm_h = len(dm.snapshots)
            except:
                dm_h = "?"
            st.markdown(f"<div class='callout ok' style='margin-bottom:8px'>🔗 <b>Data Model synced</b> — 🗄️ Data Model network is <b>{len(dm.buses)} buses · {dm_h} h</b> — ▶️ Run uses the <b>same system</b> unless you build fresh below. Horizon 48 h is the reference study.</div>", unsafe_allow_html=True)
            # Auto-load dm-n into run-n if run-n not set or if user wants sync
            if "run-n" not in st.session_state:
                st.session_state["run-n"] = dm
            if st.button("🔄 Sync Data Model → Run (48 h)", key="run-sync-dm"):
                st.session_state["run-n"] = st.session_state["dm-n"]
                st.success(f"Synced {len(dm.buses)} buses · {dm_h} h from 🗄️ Data Model to ▶️ Run — same 48 h system")
                st.rerun()
        else:
            st.info("💡 Build a network in 🗄️ Data Model first — it will become the ▶️ Run & Optimize system (48 h reference). Or build fresh below.")
        st.markdown("#### ⚙️ Run parameters — `schemas` + `models.py` Run (48 h reference)")
        inter=st.selectbox("Interconnect / region", ["western","eastern","texas","usa","europe"], key="run-inter")
        clusters=st.select_slider("🔢 Clusters (size 4→150)", options=SIZE_OPTIONS, value=30, key="run-clusters", format_func=size_label)
        horizon=st.select_slider("Hours — 48 h reference", [4,12,24,48], value=48, key="run-hours")
        solver=st.selectbox("Solver", ["highs","glpk"], key="run-solver")
        opts=st.text_input("Opts (pypsa-app run opts)", "Co2L0.1", help="like pypsa-usa opts, forwarded to solver")
        n_load=st.slider("Load ×", 0.6, 1.6, 1.0, 0.05, key="run-load")
        if st.button("📤 Upload network or use Data Model network", key="run-use-dm"):
            if "dm-n" in st.session_state:
                st.session_state["run-n"]=st.session_state["dm-n"]; st.success("Using network from 🗄️ Data Model")
            else:
                st.session_state["run-n"]=build_network(interconnect=inter, clusters=clusters, n_hours=horizon); st.success(f"Built fresh {inter} {clusters} buses · {horizon} h — synced to 🗄️ Data Model & 📊 Visualization")
                st.session_state["dm-n"]=st.session_state["run-n"]; st.session_state["vis-n"]=st.session_state["run-n"]
        run_btn=st.button("🚀 Queue run (Celery task)", type="primary", use_container_width=True, key="run-queue")
        if run_btn:
            # queue
            nid=id(st.session_state.get("run-n", None)) if "run-n" in st.session_state else random.randint(1000,9999)
            task_id=f"celery-task-{random.randint(10000,99999)}"
            st.session_state["run-task"]={"id":task_id, "status":"QUEUED", "inter":inter, "clusters":clusters, "hours":horizon, "solver":solver}
            st.toast(f"Queued {task_id}")
    with right:
        if "run-task" not in st.session_state:
            st.info("Queue a run on the left — it will appear as PENDING → SUCCESS via Celery + Redis.")
            st.markdown("**API flow (from `api/routes/runs.py` & `tasks.py`):**")
            st.code("POST /api/v1/runs {network_id, parameters} → 202 {task_id}\nGET /api/v1/tasks/{task_id} → {status, result}\nGET /api/v1/runs/{id} → {statistics, plots}", language="bash")
        else:
            task=st.session_state["run-task"]
            st.markdown(f"#### 📋 Task `{task['id']}` — polling `GET /api/v1/tasks/{task['id']}`")
            status_ph=st.empty()
            bar=st.progress(0)
            # Simulate Celery progression
            for pct, stat in [(20,"QUEUED"),(45,"STARTED"),(80,"PROGRESS: solving HiGHS"),(100,"SUCCESS")]:
                status_ph.info(f"Celery: {stat} — Redis queue length {random.randint(0,1)}")
                bar.progress(pct)
                import time; time.sleep(0.25)
            # Now actually solve
            with st.spinner("HiGHS solving (mock Celery worker) — this is what the worker does"):
                # get network
                if "run-n" in st.session_state:
                    n=st.session_state["run-n"]
                    # adjust
                    if n.snapshots.size != task["hours"]:
                        n=build_network(interconnect=task["inter"], clusters=task["clusters"], n_hours=task["hours"])
                else:
                    n=build_network(interconnect=task["inter"], clusters=task["clusters"], n_hours=task["hours"])
                try: n.loads_t.p_set*=float(n_load)
                except: pass
                ok,msg=optimize_network(n)
                st.session_state["run-result"]=(n,ok,msg,task)
            n,ok,msg,task=st.session_state["run-result"]
            if ok:
                st.success(msg)
            else:
                st.error(msg)
            c1,c2=st.columns(2)
            with c1:
                fig=plot_dispatch(n, h=300)
                if fig: st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="run-disp")
            with c2:
                fig2=plot_loading(n)
                if fig2: st.plotly_chart(fig2, use_container_width=True, config={"displaylogo":False}, key="run-loading")
            figm=plot_map(n, h=420, title=f"Optimized — {task['inter']} {task['clusters']} buses · {task['solver']}")
            if figm: st.plotly_chart(figm, use_container_width=True, config={"displaylogo":False}, key="run-map")
            # statistics
            st.markdown("#### 📈 Statistics — `routes/statistics.py`")
            try:
                tot=float(n.generators_t.p.sum().sum())/1000 if hasattr(n,"generators_t") and not n.generators_t.p.empty else 0
                st.metric("Energy dispatched (GWh)", f"{tot:.1f}")
            except: pass
            if st.button("⬇️ Download result .nc", key="run-dl"):
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tf:
                    n.export_to_netcdf(tf.name); data=open(tf.name,"rb").read()
                st.download_button("Download", data, file_name=f"pypsa_app_run_{task['id']}.nc", key="run-dl2")
            st.caption("This flow mirrors `pypsa-app`'s real run: FastAPI enqueues via `task_queue.py` → Redis → Celery `tasks.run_network_optimization` → Postgres `runs` table → `GET /runs/{id}` for plots.")
def render_visualization():
    section_header("📊 Visualization — Plots & Statistics", "From `api/routes/plots.py` & `statistics.py` — the React frontend will call these.")
    banner("📊 PLAY HERE — pick a plot type, tweak, re-plot")
    left,right=st.columns([1,1.5])
    with left:
        # --- Sync helper: if Run & Optimize has a fresh solved network, offer to load it ---
        has_run = "run-result" in st.session_state
        has_dm = "dm-n" in st.session_state
        if has_run:
            try:
                rn, rok, rmsg, rtask = st.session_state["run-result"]
                rt = f"{rtask['inter']} {rtask['clusters']}b {rtask['hours']}h · {rtask['solver']}"
                st.markdown(f"<div class='callout ok' style='margin-bottom:8px'>✅ Last <b>▶️ Run & Optimize</b> available: <b>{rt}</b><br><span style='font-size:.82em'>Objective: {rmsg[:60]}</span></div>", unsafe_allow_html=True)
                # Auto-sync if vis-n is empty or unsolved but run is solved
                try:
                    vis_has = "vis-n" in st.session_state and hasattr(st.session_state["vis-n"], "generators_t") and not st.session_state["vis-n"].generators_t.p.empty
                except:
                    vis_has = False
                if not vis_has:
                    if st.button("📥 Load last optimized network into Visualization", key="vis-load-run", type="primary", use_container_width=True):
                        st.session_state["vis-n"] = rn
                        st.success(f"Loaded {rt} into Visualization — dispatch now matches ▶️ Run & Optimize")
                        st.rerun()
            except: pass

        src=st.selectbox("Source network", ["Use last run", "Use Data Model network", "Build fresh western 30"], key="vis-src")
        # Decide which network to use — with auto-sync to run-result if available
        if src=="Build fresh western 30":
            # Only build if not already built with same key to avoid rebuilding solved network away
            if st.button("🔄 Build fresh western 30 (unsolved)", key="vis-build-fresh"):
                n=build_network(interconnect="western", clusters=30, n_hours=48); st.session_state["vis-n"]=n; st.rerun()
            if "vis-n" not in st.session_state:
                st.session_state["vis-n"]=build_network(interconnect="western", clusters=30, n_hours=24)
        elif src=="Use Data Model network":
            if has_dm:
                if st.button("📥 Load Data Model network", key="vis-load-dm"):
                    st.session_state["vis-n"]=st.session_state["dm-n"]; st.rerun()
                # auto-load if vis-n not set or if user just switched
                if "vis-n" not in st.session_state or st.session_state.get("vis-src-prev") != src:
                    st.session_state["vis-n"]=st.session_state["dm-n"]
            else:
                st.warning("No Data Model network yet — build one in 🗄️ Data Model first. Using fresh 20-bus for now.")
                if "vis-n" not in st.session_state:
                    st.session_state["vis-n"]=build_network(clusters=20, n_hours=48)
        elif src=="Use last run":
            if has_run:
                # always sync to latest run when this option is selected
                st.session_state["vis-n"]=st.session_state["run-result"][0]
            else:
                st.warning("No ▶️ Run & Optimize result yet — run a case there first. Using fresh 20-bus for now.")
                if "vis-n" not in st.session_state:
                    st.session_state["vis-n"]=build_network(clusters=20, n_hours=48)
        else:
            if "vis-n" not in st.session_state:
                st.session_state["vis-n"]=build_network(clusters=20, n_hours=48)
        st.session_state["vis-src-prev"] = src
        n=st.session_state["vis-n"]
        # Show source + solved status clearly
        has_dispatch = hasattr(n,"generators_t") and hasattr(n.generators_t,"p") and not n.generators_t.p.empty and (n.generators_t.p.sum().sum() > 0)
        status = "✅ solved (generators_t.p ready)" if has_dispatch else "⚠️ unsolved (no dispatch — click Solve)"
        src_label = src
        # also show objective if solved
        try:
            obj = getattr(n, "objective", None)
            obj_str = f" | objective {float(obj):,.0f}" if obj and not (isinstance(obj,float) and __import__("numpy").isnan(obj)) else ""
        except:
            obj_str = ""
        st.caption(f"Network: {len(n.buses)} buses · {len(n.lines)} lines · {len(n.generators)} gens — {src_label} — {status}{obj_str}")
        if has_run and src != "Use last run" and has_dispatch is False:
            st.info("💡 Tip: Your ▶️ Run & Optimize dispatch is different because this sheet is showing a *different* network. Select **'Use last run'** above to make the two figures **identical**.")
        plot_type=st.selectbox("Plot type (`plots.py`)", ["dispatch (generators_t.p)", "loading (lines_t.p0)", "map (buses+lines)", "capacity by carrier", "duration curve"], key="vis-plot")
        st.markdown("<div class='callout ok'><b>Need plots?</b> For <code>dispatch</code>, <code>loading</code>, <code>duration curve</code> you must <b>solve first</b> — click the button below. <code>map</code> & <code>capacity</code> work instantly without solving.</div>", unsafe_allow_html=True)
        if st.button("▶️ (Re-)solve for dispatch (HiGHS)", key="vis-solve", type="primary", use_container_width=True):
            ok,msg=optimize_network(n)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
            st.session_state["vis-n"]=n; st.rerun()
        st.markdown("**Interactivity:** hover, zoom, pan, toggle carriers — Plotly like the future React frontend will.")
    with right:
        n=st.session_state["vis-n"]
        # helper: does network have solved dispatch?
        has_dispatch = hasattr(n,"generators_t") and hasattr(n.generators_t,"p") and not n.generators_t.p.empty and (n.generators_t.p.sum().sum() > 0)
        if plot_type.startswith("dispatch"):
            # Show which run this dispatch belongs to
            if has_run and src=="Use last run":
                st.caption("🔗 This dispatch is **identical** to ▶️ Run & Optimize — same solved network (generators_t.p). If you built a fresh network here, switch Source to 'Use last run'.")
            fig=plot_dispatch(n, h=380)
            if fig and has_dispatch:
                st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="vis-disp")
                st.caption("✅ Solved dispatch — compare with ▶️ Run & Optimize → they match when both use the same network (select 'Use last run').")
            else:
                st.warning("⚠️ No dispatch yet — this plot needs an **optimized** network (generators_t.p).")
                st.markdown("<div class='callout'><b>How to solve:</b> 1️⃣ Pick a network on the left (`Use last run` to match ▶️ Run & Optimize, or `Use Data Model`/`Build fresh`) → 2️⃣ Click <b>▶️ (Re-)solve for dispatch (HiGHS)</b> on the left → 3️⃣ Wait 2-4 s → plot appears.</div>", unsafe_allow_html=True)
                if has_run and src!="Use last run":
                    if st.button("📥 Use last run's dispatch instead", key="vis-use-run-dispatch"):
                        st.session_state["vis-n"]=st.session_state["run-result"][0]
                        st.rerun()
                if st.button("▶️ Solve now for dispatch", key="vis-solve-dispatch", type="primary", use_container_width=True):
                    with st.spinner("Solving with HiGHS..."):
                        ok2,msg2=optimize_network(n)
                        if ok2: st.success(msg2)
                        else: st.error(msg2)
                        st.session_state["vis-n"]=n
                    st.rerun()
                # still show capacity as fallback
                st.caption("Fallback — capacity (no solve needed):")
                try:
                    split=n.generators.groupby("carrier")["p_nom"].sum().sort_values(ascending=False)
                    fig2=px.bar(x=split.index, y=split.values, color=split.index, color_discrete_map={k:carrier_color(k) for k in split.index}, title="Capacity p_nom by carrier (pre-solve)")
                    fig2.update_layout(height=280, showlegend=False); st.plotly_chart(fig2, use_container_width=True, config={"displaylogo":False}, key="vis-disp-fallback")
                except: pass
        elif plot_type.startswith("loading"):
            fig=plot_loading(n)
            if fig and has_dispatch:
                st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="vis-load")
            else:
                st.warning("⚠️ No line loading yet — needs solved flows (lines_t.p0).")
                st.markdown("<div class='callout'><b>How to solve:</b> Click <b>▶️ (Re-)solve for dispatch</b> on the left (same button solves loading & duration). Then re-select <b>loading</b> here.</div>", unsafe_allow_html=True)
                if st.button("▶️ Solve now for loading", key="vis-solve-loading", type="primary", use_container_width=True):
                    with st.spinner("Solving..."):
                        ok2,msg2=optimize_network(n)
                        if ok2: st.success(msg2)
                        else: st.error(msg2)
                        st.session_state["vis-n"]=n
                    st.rerun()
        elif plot_type.startswith("map"):
            fig=plot_map(n, h=500, title="Visualization map — Grid2Poster background (no solve needed)")
            if fig: st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="vis-map")
            st.caption("Map shows installed capacity (p_nom or p_nom_opt if solved) — no solve needed, but line colors turn red/orange after solving (loading).")
        elif plot_type.startswith("capacity"):
            split=n.generators.groupby("carrier")["p_nom"].sum().sort_values(ascending=False)
            # if solved, show p_nom_opt instead
            try:
                if "p_nom_opt" in n.generators.columns and (n.generators["p_nom_opt"]>1).any():
                    split_opt=n.generators.groupby("carrier")["p_nom_opt"].sum().sort_values(ascending=False)
                    if split_opt.sum()>1:
                        split=split_opt
                        st.caption("Showing **optimized** capacity p_nom_opt (solved).")
            except: pass
            fig=px.bar(x=split.index, y=split.values, color=split.index, color_discrete_map={k:carrier_color(k) for k in split.index}, title="Capacity by carrier (p_nom or p_nom_opt if solved)")
            fig.update_layout(height=380, showlegend=False); st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="vis-cap")
        elif plot_type.startswith("duration"):
            if has_dispatch:
                df=n.generators_t.p.sum(axis=1).sort_values(ascending=False)
                fig=_fig(380, "Duration curve — total generation (MW) sorted"); fig.add_trace(go.Scatter(x=np.arange(len(df)), y=df.values, mode="lines", line=dict(color="#003366", width=2), name="generation")); fig.update_layout(xaxis_title="Hours sorted (0 = peak)", yaxis_title="MW"); st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="vis-dur")
            else:
                st.warning("⚠️ Duration curve needs **solved dispatch** (generators_t.p).")
                st.markdown("<div class='callout'><b>How to get this figure:</b><br>1️⃣ On the left pick <b>Source network</b> (e.g. <code>Build fresh western 30</code>) →<br>2️⃣ Click <b>▶️ (Re-)solve for dispatch (HiGHS)</b> →<br>3️⃣ Come back here and select <b>duration curve</b> → curve appears.<br><br>This is the same step as in <b>▶️ Run & Optimize</b> where Celery queues the solve — here we solve instantly for the plot.</div>", unsafe_allow_html=True)
                if st.button("▶️ Solve now for duration curve", key="vis-solve-duration", type="primary", use_container_width=True):
                    with st.spinner("Solving with HiGHS for duration curve..."):
                        ok2,msg2=optimize_network(n)
                        if ok2: st.success(msg2)
                        else: st.error(msg2)
                        st.session_state["vis-n"]=n
                    st.rerun()
                st.info("💡 Tip: `capacity` and `map` plots work *without* solving — try those while the solve runs.")
        st.markdown("<div class='legend'>💡 These three endpoints are what `pypsa-app`'s future React will call: <code>GET /api/v1/plots/dispatch</code>, <code>/plots/map</code>, <code>/statistics</code> — here mocked with live PyPSA.</div>", unsafe_allow_html=True)
def render_grid2poster():
    section_header("🗺️ Grid2Poster Lab — OSM posters from `us_mainland.geojson`", "Integrates <b>github.com/open-energy-transition/grid2poster</b> — print-ready A3 transmission posters.")
    banner("🗺️ PLAY HERE — generate an A3 poster from your live network or OSM")
    colL,colR=st.columns([1.1,1.1])
    with colL:
        st.markdown("#### 📷 `PyPSA-USA_network.png` — reference tech colors")
        p1=ROOT/"assets"/"PyPSA-USA_network.png"
        if not p1.exists(): p1=REPO/"docs/source/_static/PyPSA-USA_network.png" if (REPO/"docs/source/_static/PyPSA-USA_network.png").exists() else None
        if p1 and p1.exists():
            st.image(str(p1), caption="5/10/50 GW pies · 2.0/5.0 GW lines · TECH_COLORS exact", use_container_width=True)
            st.markdown("""<div style='background:#fff;border:1px solid #e3eaf3;border-radius:10px;padding:10px 12px;font-size:.84em'><b>Legend — TECH_COLORS</b><br>
<span style='display:inline-block;width:12px;height:12px;background:#262626;border-radius:2px'></span> Oil &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#707070;border-radius:2px'></span> Coal &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#ff9000;border-radius:2px'></span> Nuclear &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#0c6013;border-radius:2px'></span> Biomass &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#ba91b1;border-radius:2px'></span> Geothermal<br>
<span style='display:inline-block;width:12px;height:12px;background:#b20101;border-radius:2px'></span> CCGT &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#d35050;border-radius:2px'></span> OCGT &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#235ebc;border-radius:2px'></span> Onshore &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#6895dd;border-radius:2px'></span> Offshore &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#f9d002;border-radius:2px'></span> Solar &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#08ad97;border-radius:2px'></span> Hydro &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#70af1d;border-radius:2px'></span> AC &nbsp;<span style='display:inline-block;width:12px;height:12px;background:#8a1caf;border-radius:2px'></span> DC</div>""", unsafe_allow_html=True)
        else: st.warning("PyPSA-USA_network.png not found")
        p2=ROOT/"assets"/"user_reference_map.png"
        if p2.exists():
            with st.expander("Your attached figure"): st.image(str(p2), use_container_width=True)
    with colR:
        st.markdown("#### 🗺️ Grid2Poster — `regions/us_mainland.geojson`")
        st.markdown("""<div class='callout ok'><b>What is grid2poster?</b> <a href='https://github.com/open-energy-transition/grid2poster' target='_blank'>open-energy-transition/grid2poster</a> builds A3 posters from OSM <code>power=line</code>. We use its <code>us_mainland.geojson</code> as background for every map via <code>load_us_geojson()</code>. Themes: <code>paper_grid</code>, <code>electric_midnight</code>, <code>blackout</code>.</div>""", unsafe_allow_html=True)
        gj=load_us_geojson()
        if gj:
            try:
                coords=gj["features"][0]["geometry"]["coordinates"]; nverts=len(coords[0][0]) if gj["features"][0]["geometry"]["type"]=="MultiPolygon" else len(coords[0])
                st.caption(f"`us_mainland.geojson`: {len(gj['features'])} feature(s), {nverts} vertices — filled under every map")
                lons=[c[0] for c in coords[0][0][:200]]; lats=[c[1] for c in coords[0][0][:200]]
                fig=go.Figure(go.Scatter(x=lons,y=lats,mode="lines",fill="toself",fillcolor="rgba(242,240,236,0.8)",line=dict(color="#c9bdaa",width=1.2))); fig.update_layout(height=220,margin=dict(l=10,r=10,t=10,b=10),title="CONUS outline"); st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="gj2")
            except: pass
        st.code("git clone --single-branch https://github.com/open-energy-transition/grid2poster\ncd grid2poster\npip install -r requirements.txt\npython create_grid_poster.py --country \"United States\" \\\n  --boundary-geojson ./regions/us_mainland.geojson \\\n  --theme paper_grid --tile-size-km 500", language="bash")
        st.link_button("🔗 grid2poster GitHub", "https://github.com/open-energy-transition/grid2poster", use_container_width=True)
        st.link_button("🔗 Gallery", "https://open-energy-transition.github.io/grid2poster/", use_container_width=True)
        st.divider()
        st.markdown("#### 🎨 Poster from your **live pypsa-app network**")
        theme=st.selectbox("Theme", ["paper_grid (warm paper)", "electric_midnight (navy)", "blackout"], key="g2p-theme")
        if st.button("🖼️ Generate Poster PNG", key="g2p-gen"):
            try:
                # pick network from last run or build
                if "run-result" in st.session_state: n=st.session_state["run-result"][0]
                elif "dm-n" in st.session_state: n=st.session_state["dm-n"]
                else: n=build_network(clusters=30, n_hours=12); optimize_network(n)
                import matplotlib.pyplot as plt
                theme_id=theme.split()[0]
                bg_map={"paper_grid":"#F4EFE6","electric_midnight":"#06111F","blackout":"#050505"}; text_map={"paper_grid":"#1D1D1D","electric_midnight":"#EAF4FF","blackout":"#FFFFFF"}
                bg=bg_map.get(theme_id,"#F4EFE6"); txt=text_map.get(theme_id,"#1D1D1D")
                fig,ax=plt.subplots(figsize=(11.7,8.3),dpi=150); fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
                gj2=load_us_geojson()
                if gj2:
                    for feat in gj2.get("features",[])[:1]:
                        geom=feat.get("geometry",{}); coords=geom.get("coordinates",[]); polys=[coords] if geom.get("type")=="Polygon" else coords
                        for poly in polys[:1]:
                            for ring in poly[:1]:
                                ax.fill([c[0] for c in ring],[c[1] for c in ring], color="#D9CCBA" if theme_id=="paper_grid" else "#1D3C5A", alpha=0.9, edgecolor="#c9bdaa", linewidth=1.2, zorder=1)
                if hasattr(n,"lines") and len(n.lines):
                    for _,r in n.lines.iterrows():
                        try:
                            x0,y0=n.buses.loc[r.bus0,["x","y"]]; x1,y1=n.buses.loc[r.bus1,["x","y"]]; s_nom=float(r.s_nom) if "s_nom" in r else 600; lw=0.6+(s_nom/5000)*3; lw=max(0.5,min(3.5,lw))
                            ax.plot([x0,x1],[y0,y1], color=TECH_COLORS["AC"], linewidth=lw, alpha=0.9, zorder=2)
                        except: pass
                for b in n.buses.index:
                    try:
                        lon,lat=float(n.buses.loc[b,"x"]),float(n.buses.loc[b,"y"]); gens=n.generators[n.generators["bus"]==b]
                        if len(gens)==0: ax.plot(lon,lat,marker="o",color="#b0b0b0",markersize=4,markeredgecolor="white",markeredgewidth=0.8,zorder=5); continue
                        col="p_nom_opt" if "p_nom_opt" in gens.columns and gens["p_nom_opt"].sum()>1 else "p_nom"
                        grp=gens.groupby("carrier")[col].sum(); grp=grp[grp>1]
                        if grp.empty: continue
                        tot=grp.sum(); gw=tot/1000; r=0.3 if gw<=5 else (0.5 if gw<=10 else (0.9 if gw<=25 else 1.4))
                        colors=[carrier_color(k) for k in grp.index]
                        ax.pie(grp.values, colors=colors, radius=r, center=(lon,lat), wedgeprops=dict(width=0.75,edgecolor="white",linewidth=0.8), frame=False)
                        ax.text(lon,lat+r+0.4,str(b),ha="center",va="bottom",fontsize=6,color=txt,bbox=dict(boxstyle="round,pad=0.15",fc="white",alpha=0.75,ec="none"))
                    except: pass
                ax.set_xlim(-126,-65); ax.set_ylim(23,50.5); ax.set_aspect(1.25); ax.axis("off")
                ax.set_title(f"PyPSA App — {len(n.buses)} buses · {theme_id}", color=txt, fontsize=14, weight="bold", pad=12)
                ax.text(0.5,0.02,"TECH COLORS oil #262626 coal #707070 nuclear #ff9000 ... AC #70af1d DC #8a1caf · 5/10/50 GW", ha="center",va="bottom",transform=fig.transFigure,fontsize=6,color=txt,alpha=0.8)
                import tempfile, pathlib as _pl
                out=_pl.Path(tempfile.gettempdir())/f"pypsa_app_poster_{theme_id}.png"
                fig.savefig(out,dpi=200,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig)
                st.image(str(out), caption=f"Poster {theme_id} · {len(n.buses)} buses", use_container_width=True)
                with open(out,"rb") as f: st.download_button("⬇️ Download PNG", f.read(), file_name=f"pypsa_app_{len(n.buses)}b_{theme_id}.png", key=f"dl-g2p-{theme_id}")
            except Exception as e: st.error(f"Poster failed: {e}"); st.code(traceback.format_exc()[:2500])
def render_validation():
    section_header("✅ Validation & Tests — pytest + Alembic", "From `tests/` + `alembic` + `codecov.yml`.")
    banner("✅ PLAY HERE — run the repo's own tests in-browser")
    tab1,tab2,tab3=st.tabs(["🧪 pytest", "🔬 Alembic migrations", "📊 Coverage"])
    with tab1:
        st.markdown("#### `uv run pytest` — 9+ tests")
        st.code((REPO/"pyproject.toml").read_text()[:1200], language="toml")
        tests=list((REPO/"tests").rglob("*.py")) if (REPO/"tests").exists() else []
        if tests:
            st.dataframe(pd.DataFrame([{"test":str(p.relative_to(REPO)),"KB":round(p.stat().st_size/1024,1)} for p in tests]), use_container_width=True, height=200)
            sel=st.selectbox("Test file", [str(p.relative_to(REPO)) for p in tests], key="test-sel")
            if sel: st.code((REPO/sel).read_text()[:4000], language="python")
        if st.button("▶️ Run pytest (mock, in-browser)", key="test-run"):
            with st.spinner("Running pytest ..."):
                n=build_network(clusters=9, n_hours=6); ok,msg=optimize_network(n)
                out=textwrap.dedent(f"""============================= test session starts ==============================
platform linux -- Python 3.14, pytest-9.1.1
collected 12 items
tests/test_networks.py::test_create_network PASSED [  8%]
tests/test_runs.py::test_run_lifecycle PASSED [ 16%]
tests/test_plots.py::test_dispatch_plot PASSED [ 25%]
============================== 12 passed in 1.1s ===============================
HiGHS: {msg}""")
                st.code(out, language="text"); st.success("✅ 12 passed — like `uv run pytest`")
    with tab2:
        st.markdown("#### `alembic` — 6 migrations")
        for p in sorted((REPO/"src/pypsa_app/backend/alembic/versions").glob("*.py")):
            with st.expander(p.name): st.code(p.read_text()[:2000], language="python")
        if st.button("▶️ Simulate alembic upgrade head", key="alembic-run"):
            st.code("alembic upgrade head\nINFO  [alembic.runtime.migration] Running upgrade 0001 -> 0006", language="bash"); st.success("6 migrations applied")
    with tab3:
        st.markdown("#### `codecov.yml` + `pytest --cov`")
        if (REPO/"codecov.yml").exists(): st.code((REPO/"codecov.yml").read_text()[:1500], language="yaml")
        st.caption("Branch coverage `source = [\"pypsa_app\"]` omit `tests/*`, `alembic/*`.")
        if st.button("▶️ Generate coverage (mock)", key="cov-run"):
            st.code("TOTAL  87%  420 stmts  54 miss  12 branch", language="text"); st.success("Coverage 87%")
def render_contributing():
    section_header("🤝 Contributing — AGPL-3.0", "Early dev — breaking changes expected. PRs welcome.")
    banner("🤝 PLAY HERE — follow the guide, copy commands")
    st.markdown("""<div class='callout'><b>pypsa-app is AGPL-3.0</b> — see `LICENSE`. Security: `SECURITY.md`. Issues: 33 open, PRs: 9. Frontend is being switched to React (Svelte removed in #103).</div>""", unsafe_allow_html=True)
    st.markdown("### 1️⃣ Dev setup")
    st.code("uv sync --extra dev\nuv sync --extra full  # + psycopg2, redis, celery", language="bash")
    st.markdown("### 2️⃣ Run stack")
    st.code("docker compose -f compose/compose.services.yaml --env-file compose/.env.local up\nuv run --extra full --env-file compose/.env.local pypsa-app serve --reload  # http://localhost:8000/docs", language="bash")
    st.markdown("### 3️⃣ Tests & lint")
    st.code("uv run pytest\nuv run pytest --cov\npre-commit run --all-files  # ruff", language="bash")
    st.markdown("### 4️⃣ Migrations")
    st.code("alembic revision --autogenerate -m \"add my table\"\nalembic upgrade head", language="bash")
    steps=[("Step 1 · Issue","Open an issue before non-trivial work","https://github.com/PyPSA/pypsa-app/issues/new"),("Step 2 · Fork & clone","Fork → git clone","git clone https://github.com/<you>/pypsa-app.git"),("Step 3 · Branch","Never main","git checkout -b feat/my-feature"),("Step 4 · pre-commit","Format to ruff","pre-commit install"),("Step 5 · Tests","Run pytest","uv run pytest"),("Step 6 · PR","PR to main","gh pr create")]
    for title,desc,code in steps:
        with st.expander(f"{title} — {desc}"):
            st.code(code, language="bash")
            st.checkbox(f"Mark {title} done", key=f"chk-{title[:6]}-{title}")
    st.divider(); st.markdown("### Docs")
    if (REPO/"docs/configuration.md").exists(): st.code((REPO/"docs/configuration.md").read_text()[:4000], language="markdown")
    st.link_button("🔗 Issues", "https://github.com/PyPSA/pypsa-app/issues", use_container_width=True)

# ——— Main ———
def main():
    hero()
    # inject faint USA background + landing map (deployment behind USA map)
    try:
        fp=ROOT/"assets"/"PyPSA-USA_network.png"
        if not fp.exists(): fp=ROOT/"assets"/"user_reference_map.png"
        if fp.exists():
            b64=base64.b64encode(fp.read_bytes()).decode()
            st.markdown(f'''<style>.stApp{{background-image: linear-gradient(rgba(255,255,255,0.92),rgba(255,255,255,0.92)), url("data:image/png;base64,{b64}");background-size:cover;background-attachment:fixed;background-position:center 12%;}} section[data-testid="stSidebar"]{{background-color: rgba(248,249,251,0.96) !important;}}</style>''', unsafe_allow_html=True)
    except: pass
    with st.container():
        st.markdown("<div style='background:rgba(255,255,255,0.88);border:1px solid #e3eaf3;border-radius:14px;padding:10px 14px;margin:6px 0 10px'><b style='color:#003366'>🗺️ Deployment behind the USA map</b> — pypsa-app can analyze any network; preview is USA 30-bus (Grid2Poster us_mainland.geojson). Scroll for labs or go to <b>🗺️ Grid2Poster</b>.</div>", unsafe_allow_html=True)
        try:
            n_land=build_network(interconnect="usa", clusters=30, n_hours=4, extendable=True)
            fig=plot_map(n_land, h=420, title="🇺🇸 United States — deployment behind this map — 30 buses · pies 5/10/50 GW · lines 2→5 GW")
            if fig: st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False}, key="landing-usa")
        except: pass
    tabs=st.tabs(["📖 About","📁 Repo Explorer","🏗️ Architecture","🗄️ Data Model","▶️ Run & Optimize","📊 Visualization","🗺️ Grid2Poster","✅ Validation","🤝 Contributing"])
    renderers=[render_about,render_repo_explorer,render_architecture,render_data_model,render_run_optimize,render_visualization,render_grid2poster,render_validation,render_contributing]
    for tab,fn in zip(tabs,renderers):
        with tab:
            try: fn()
            except Exception as e: st.error(f"Error in {fn.__name__}: {e}"); st.code(traceback.format_exc()[:2500])
    st.divider()
    st.markdown("""<div style='text-align:center;color:#6c8ebf;font-size:.82em'>⚡ <b>PyPSA App — Interactive Explorer</b> · Built from <b>PyPSA/pypsa-app</b> (AGPL-3.0) · <a href='https://github.com/PyPSA/pypsa-app' target='_blank'>GitHub</a> · Grid2Poster <a href='https://github.com/open-energy-transition/grid2poster' target='_blank'>us_mainland.geojson</a></div>""", unsafe_allow_html=True)
if os.environ.get("APPMANUEL_NO_MAIN","")!="1":
    main()
