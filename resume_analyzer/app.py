"""app.py - ResumeLens: AI-based resume analyzer (Streamlit UI).
Run with:  streamlit run app.py
"""
import base64
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import pandas as pd

from extract import read_resume, load_skills
from report_pdf import build_pdf
from score import analyze, build_report, learning_links, verdict

st.set_page_config(page_title="ResumeLens", page_icon="📄", layout="wide")

TEAL, AMBER, RED, INK = "#2DD4BF", "#F59E0B", "#F87171", "#E8EEF9"

# ---------------------------------------------------------------- styling
def load_bg():
    path = Path(__file__).parent / "assets" / "bg.jpg"
    if path.exists():
        b64 = base64.b64encode(path.read_bytes()).decode()
        return f"url('data:image/jpeg;base64,{b64}')"
    return "linear-gradient(135deg,#0B1220,#12324a)"  # fallback if image missing


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="st-"], .stMarkdown { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, .hero-title, .score-num { font-family: 'Sora', sans-serif !important; letter-spacing: -0.02em; }

.stApp { background: __BG__ center top / cover fixed no-repeat; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem; }

.brand { display:flex; align-items:center; gap:.6rem; font-family:'Sora'; font-weight:700; font-size:1.15rem; }
.brand .dot { width:14px; height:14px; border-radius:50%; background:__TEAL__; box-shadow:0 0 18px __TEAL__; }

.hero { padding: 4.5rem 0 2.5rem; max-width: 640px; }
.hero-title { font-size: clamp(2.2rem, 5vw, 3.6rem); line-height: 1.08; font-weight: 800; margin: 0 0 1.1rem; }
.hero-title span { color: __TEAL__; }
.hero-sub { font-size: 1.12rem; line-height: 1.6; color: #B8C4DA; max-width: 34rem; }
.hero-points { display:flex; gap:.6rem; flex-wrap:wrap; margin-top:1.4rem; }
.pill { padding:.35rem .85rem; border:1px solid rgba(255,255,255,.18); border-radius:999px;
        background: rgba(255,255,255,.06); backdrop-filter: blur(6px); font-size:.88rem; color:#D5DEEE; }

/* glass panels: bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(14,22,40,.72); backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.10) !important; border-radius: 18px; padding: .4rem .5rem;
}
[data-testid="stFileUploader"] section { background: rgba(255,255,255,.04); border: 1.5px dashed rgba(45,212,191,.5); border-radius: 14px; }
.stTextArea textarea { background: rgba(255,255,255,.04); border-radius: 14px; border: 1px solid rgba(255,255,255,.14); }
.stButton > button, .stDownloadButton > button {
  background: linear-gradient(135deg, __TEAL__, #14B8A6); color:#06201C; font-weight:700;
  border:0; border-radius: 12px; padding:.7rem 1.6rem; transition: transform .15s, box-shadow .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 26px rgba(45,212,191,.35); color:#06201C; }
button[data-baseweb="tab"] { font-weight:600; font-size:1rem; }

.panel-title { font-family:'Sora'; font-weight:700; font-size:1.1rem; margin:.2rem 0 .8rem; }
.chip { display:inline-block; margin:.2rem .3rem .2rem 0; padding:.28rem .75rem; border-radius:999px; font-size:.86rem; font-weight:500; }
.chip.ok { background:rgba(45,212,191,.14); color:#7FF0DF; border:1px solid rgba(45,212,191,.4); }
.chip.bad { background:rgba(248,113,113,.12); color:#FCA5A5; border:1px solid rgba(248,113,113,.4); }
.chip.neutral { background:rgba(255,255,255,.07); color:#D5DEEE; border:1px solid rgba(255,255,255,.15); }
.stat { text-align:left; padding:.3rem .2rem; }
.stat .v { font-family:'Sora'; font-size:1.9rem; font-weight:800; }
.stat .l { color:#9FB0CC; font-size:.9rem; }
.check { display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid rgba(255,255,255,.07); }
.check:last-child { border-bottom:0; }
.check .mark { font-weight:800; width:1.2rem; }
.check .tip { color:#9FB0CC; font-size:.87rem; }
.tip-row { padding:.7rem .9rem; margin:.45rem 0; border-left:3px solid __AMBER__; background:rgba(245,158,11,.07); border-radius:0 10px 10px 0; }
a.learn { color:__TEAL__; text-decoration:none; margin-right:.9rem; font-size:.9rem; }
a.learn:hover { text-decoration:underline; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""
st.markdown(
    CSS.replace("__BG__", load_bg()).replace("__TEAL__", TEAL).replace("__AMBER__", AMBER),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- helpers
def chips(items, kind):
    if not items:
        return "<span class='chip neutral'>None</span>"
    return "".join(f"<span class='chip {kind}'>{i}</span>" for i in items)


def stat(value, label):
    return f"<div class='stat'><div class='v'>{value}</div><div class='l'>{label}</div></div>"


def score_color(v):
    return TEAL if v >= 70 else AMBER if v >= 45 else RED


def gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number={"font": {"size": 54, "color": INK}},
        title={"text": title, "font": {"size": 16, "color": "#9FB0CC"}},
        gauge={"axis": {"range": [0, 100], "tickcolor": "#51607D"},
               "bar": {"color": score_color(value), "thickness": 0.28},
               "bgcolor": "rgba(255,255,255,0.05)", "borderwidth": 0,
               "steps": [{"range": [0, 45], "color": "rgba(248,113,113,.12)"},
                         {"range": [45, 70], "color": "rgba(245,158,11,.12)"},
                         {"range": [70, 100], "color": "rgba(45,212,191,.12)"}]},
    ))
    fig.update_layout(height=260, margin=dict(t=50, b=10, l=30, r=30),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": INK})
    return fig


def radar(breakdown):
    names = list(breakdown)
    vals = [round(v[0] / v[1] * 100) for v in breakdown.values()]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=names + names[:1], fill="toself",
                                    line={"color": TEAL}, fillcolor="rgba(45,212,191,.25)"))
    fig.update_layout(height=320, margin=dict(t=30, b=30, l=50, r=50), paper_bgcolor="rgba(0,0,0,0)",
                      polar=dict(bgcolor="rgba(255,255,255,.03)",
                                 radialaxis=dict(range=[0, 100], gridcolor="#2A3752", tickfont={"size": 9}),
                                 angularaxis=dict(gridcolor="#2A3752")),
                      showlegend=False, font={"color": INK})
    return fig


def bars(breakdown):
    names = list(breakdown)
    got = [v[0] for v in breakdown.values()]
    mx = [v[1] for v in breakdown.values()]
    fig = go.Figure()
    fig.add_bar(y=names, x=mx, orientation="h", marker_color="rgba(255,255,255,.08)", name="Max", hoverinfo="skip")
    fig.add_bar(y=names, x=got, orientation="h", marker_color=TEAL, name="You",
                text=[f"{g}/{m}" for g, m in zip(got, mx)], textposition="inside")
    fig.update_layout(barmode="overlay", height=300, margin=dict(t=10, b=10, l=10, r=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      yaxis=dict(autorange="reversed"), xaxis=dict(showgrid=False, visible=False),
                      font={"color": INK})
    return fig


# ---------------------------------------------------------------- home page
st.markdown("<div class='brand'><span class='dot'></span>ResumeLens</div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='hero'>
      <h1 class='hero-title'>See your resume the way a <span>recruiter's software</span> does.</h1>
      <p class='hero-sub'>Upload your resume and, if you have one, a job description. You get a score out of 100,
      the skills you are missing, an ATS check and clear steps to improve it. Recruiters can screen many resumes against one job and get a ranked shortlist.</p>
      <div class='hero-points'>
        <span class='pill'>PDF and DOCX</span><span class='pill'>Job match %</span><span class='pill'>Recruiter ranking</span>
        <span class='pill'>ATS check</span><span class='pill'>Skill gap and learning links</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

def candidate_mode():
    with st.container(border=True):
        st.markdown("<div class='panel-title'>Analyze a resume</div>", unsafe_allow_html=True)
        left, right = st.columns(2, gap="large")
        with left:
            resume_file = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"])
        with right:
            jd_text = st.text_area("Job description (optional)", height=130,
                                   placeholder="Paste the job description here to get a match percentage and missing skills.")
        go_btn = st.button("Analyze my resume")

    if go_btn:
        if not resume_file:
            st.warning("Upload a PDF or DOCX resume first.")
        else:
            try:
                with st.spinner("Reading your resume..."):
                    text, pages = read_resume(resume_file)
                if len(text.split()) < 30:
                    st.error("Almost no text could be read. If your resume is a scanned image, export it as a text-based PDF and try again.")
                else:
                    st.session_state["result"] = analyze(text, pages, jd_text)
            except Exception as e:  # corrupted file, unsupported format, etc.
                st.error(f"Could not read this file: {e}")

    # ---------------------------------------------------------------- results
    r = st.session_state.get("result")
    if r:
        info = r["info"]
        st.markdown("<br>", unsafe_allow_html=True)
        top = st.columns([1.1, 1.4], gap="large")
        with top[0]:
            with st.container(border=True):
                st.plotly_chart(gauge(r["score"], "Overall resume score"), use_container_width=True)
        with top[1]:
            with st.container(border=True):
                st.markdown(f"<div class='panel-title'>{info['name'] or 'Candidate'}</div>", unsafe_allow_html=True)
                c = st.columns(3)
                c[0].markdown(stat(len(info["skills"]), "skills found"), unsafe_allow_html=True)
                c[1].markdown(stat(f"{r['match_pct']}%" if r["has_jd"] else "n/a", "job match"), unsafe_allow_html=True)
                c[2].markdown(stat(f"{sum(ok for _, ok, _ in r['ats'])}/{len(r['ats'])}", "ATS checks passed"), unsafe_allow_html=True)
                st.markdown(
                    f"<span class='chip neutral'>{info['email'] or 'No email'}</span>"
                    f"<span class='chip neutral'>{info['phone'] or 'No phone'}</span>"
                    f"<span class='chip neutral'>{r['word_count']} words</span>"
                    f"<span class='chip neutral'>{r['pages']} page(s)</span>",
                    unsafe_allow_html=True,
                )
                if not r["has_jd"]:
                    st.caption("Add a job description and analyze again to see your match percentage.")

        tabs = st.tabs(["Overview", "Skills", "ATS and sections", "Suggestions", "Roles and learning"])

        with tabs[0]:
            a, b = st.columns(2, gap="large")
            with a:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Score breakdown</div>", unsafe_allow_html=True)
                    st.plotly_chart(bars(r["breakdown"]), use_container_width=True)
            with b:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Strength profile</div>", unsafe_allow_html=True)
                    st.plotly_chart(radar(r["breakdown"]), use_container_width=True)

        with tabs[1]:
            with st.container(border=True):
                st.markdown("<div class='panel-title'>Skills found in your resume</div>", unsafe_allow_html=True)
                st.markdown(chips(sorted(info["skills"]), "ok"), unsafe_allow_html=True)
            if r["has_jd"]:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Compared with the job description</div>", unsafe_allow_html=True)
                    st.markdown("**Matched**")
                    st.markdown(chips(r["matched"], "ok"), unsafe_allow_html=True)
                    st.markdown("**Missing**")
                    st.markdown(chips(r["missing"], "bad"), unsafe_allow_html=True)
            else:
                st.info("Paste a job description to see matched and missing skills.")

        with tabs[2]:
            a, b = st.columns(2, gap="large")
            with a:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>ATS compatibility</div>", unsafe_allow_html=True)
                    for name, ok, tip in r["ats"]:
                        mark, col = ("✓", TEAL) if ok else ("✕", RED)
                        st.markdown(
                            f"<div class='check'><span class='mark' style='color:{col}'>{mark}</span>"
                            f"<div>{name}" + ("" if ok else f"<div class='tip'>{tip}</div>") + "</div></div>",
                            unsafe_allow_html=True,
                        )
            with b:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Sections detected</div>", unsafe_allow_html=True)
                    for sec, present in info["sections"].items():
                        st.markdown(f"<span class='chip {'ok' if present else 'bad'}'>{sec}</span>", unsafe_allow_html=True)
                    st.markdown("<div class='panel-title' style='margin-top:1.2rem'>Writing quality</div>", unsafe_allow_html=True)
                    st.markdown("**Action verbs used**")
                    st.markdown(chips(r["verbs"], "ok"), unsafe_allow_html=True)
                    st.markdown("**Weak phrases to replace**")
                    st.markdown(chips(r["weak"], "bad") if r["weak"] else "<span class='chip ok'>None found</span>", unsafe_allow_html=True)
                    st.caption(f"Quantified achievements found: {r['quantified']}")

        with tabs[3]:
            with st.container(border=True):
                st.markdown("<div class='panel-title'>What to improve</div>", unsafe_allow_html=True)
                for t in r["tips"]:
                    st.markdown(f"<div class='tip-row'>{t}</div>", unsafe_allow_html=True)
            d1, d2, _ = st.columns([1, 1, 2])
            d1.download_button("Download report (PDF)", build_pdf(r), file_name="resume_report.pdf", mime="application/pdf")
            d2.download_button("Download report (.txt)", build_report(r), file_name="resume_analysis.txt")

        with tabs[4]:
            a, b = st.columns(2, gap="large")
            with a:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Roles that fit your skills</div>", unsafe_allow_html=True)
                    for role, pct, gap in r["roles"]:
                        st.markdown(f"**{role}** · {pct}% match")
                        st.progress(pct / 100)
                        if gap:
                            st.caption("Still needed: " + ", ".join(gap[:5]))
            with b:
                with st.container(border=True):
                    st.markdown("<div class='panel-title'>Skill gap: learn these next</div>", unsafe_allow_html=True)
                    if not r["gap_skills"]:
                        st.write("No gaps found.")
                    for skill in r["gap_skills"]:
                        links = " ".join(f"<a class='learn' href='{u}' target='_blank'>{n}</a>" for n, u in learning_links(skill).items())
                        st.markdown(f"**{skill}**<br>{links}", unsafe_allow_html=True)


# ---------------------------------------------------------------- recruiter mode
VERDICT_COLOR = {"Eligible": TEAL, "Maybe": AMBER, "Not eligible": RED}
VERDICT_ORDER = {"Eligible": 0, "Maybe": 1, "Not eligible": 2}
MAX_FILES = 30


def recruiter_mode():
    with st.container(border=True):
        st.markdown("<div class='panel-title'>Screen candidates for a job</div>", unsafe_allow_html=True)
        left, right = st.columns(2, gap="large")
        with left:
            files = st.file_uploader("Resumes (PDF or DOCX, up to 30)", type=["pdf", "docx"],
                                     accept_multiple_files=True, key="rec_files")
        with right:
            jd = st.text_area("Job description (required)", height=130, key="rec_jd",
                              placeholder="Paste the job description. Candidates are ranked by how well they match it.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            cutoff = st.slider("Minimum match % to be eligible", 20, 90, 60, 5)
        with c2:
            must = st.multiselect("Must-have skills (optional)", sorted(s for s, _ in load_skills()),
                                  help="A candidate missing any of these cannot be marked Eligible.")
        min_cgpa = st.number_input("Minimum CGPA, 10-point scale (0 = ignore)", 0.0, 10.0, 0.0, 0.5,
                                   help="Candidates with a lower CGPA, or none found on the resume, cannot be marked Eligible.")
        run = st.button("Rank candidates")

    if run:
        if not files:
            st.warning("Upload at least one resume.")
        elif not jd.strip():
            st.warning("Paste the job description first. Matching needs it.")
        else:
            if len(files) > MAX_FILES:
                st.info(f"Only the first {MAX_FILES} resumes were screened.")
                files = files[:MAX_FILES]
            rows, details, errors = [], {}, []
            bar = st.progress(0.0, text="Screening resumes...")
            for n, f in enumerate(files, 1):
                try:
                    text, pages = read_resume(f)
                    if len(text.split()) < 30:
                        raise ValueError("no readable text (scanned image?)")
                    res = analyze(text, pages, jd)
                    label, miss_must = verdict(res, must, cutoff, min_cgpa)
                    name = res["info"]["name"] or Path(f.name).stem
                    rows.append({
                        "Name": name, "File": f.name, "Match %": res["match_pct"], "Resume score": res["score"],
                        "Verdict": label, "Matched skills": ", ".join(res["matched"]) or "-",
                        "Missing skills": ", ".join(res["missing"]) or "-",
                        "Unmet requirements": ", ".join(miss_must) or "-", "CGPA": res["info"]["cgpa"] or "-",
                        "Email": res["info"]["email"] or "-", "Phone": res["info"]["phone"] or "-",
                    })
                    details[f.name] = res
                except Exception as e:
                    errors.append(f"{f.name}: {e}")
                bar.progress(n / len(files), text=f"Screened {n} of {len(files)}")
            bar.empty()
            rows.sort(key=lambda x: (VERDICT_ORDER[x["Verdict"]], -x["Match %"]))
            for rank, row in enumerate(rows, 1):
                row["Rank"] = rank
            st.session_state["ranking"] = {"rows": rows, "details": details, "errors": errors,
                                           "cutoff": cutoff, "must": must, "min_cgpa": min_cgpa}

    data = st.session_state.get("ranking")
    if not data:
        return
    rows = data["rows"]
    for err in data["errors"]:
        st.error("Could not read " + err)
    if not rows:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    counts = {k: sum(r["Verdict"] == k for r in rows) for k in VERDICT_ORDER}
    with st.container(border=True):
        c = st.columns(4)
        c[0].markdown(stat(len(rows), "resumes screened"), unsafe_allow_html=True)
        c[1].markdown(stat(counts["Eligible"], "eligible"), unsafe_allow_html=True)
        c[2].markdown(stat(counts["Maybe"], "maybe"), unsafe_allow_html=True)
        c[3].markdown(stat(counts["Not eligible"], "not eligible"), unsafe_allow_html=True)
        st.caption(f"Eligible means match of {data['cutoff']}% or more"
                   + (" and all must-have requirements met." if (data["must"] or data["min_cgpa"]) else ".")
                   + f" Maybe means within 15 points of the cutoff, or a must-have requirement is not met.")

    df = pd.DataFrame(rows)[["Rank", "Name", "Verdict", "Match %", "Resume score", "Matched skills",
                             "Missing skills", "Unmet requirements", "CGPA", "Email", "Phone", "File"]]
    t1, t2 = st.tabs(["Ranked shortlist", "Candidate details"])
    with t1:
        with st.container(border=True):
            fig = go.Figure(go.Bar(
                y=[r["Name"] for r in rows], x=[r["Match %"] for r in rows], orientation="h",
                marker_color=[VERDICT_COLOR[r["Verdict"]] for r in rows],
                text=[f"{r['Match %']}%" for r in rows], textposition="outside"))
            fig.add_vline(x=data["cutoff"], line_dash="dash", line_color="#9FB0CC")
            fig.update_layout(height=max(260, 46 * len(rows)), margin=dict(t=10, b=10, l=10, r=40),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              yaxis=dict(autorange="reversed"), xaxis=dict(range=[0, 110], title="Match %"),
                              font={"color": INK})
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, hide_index=True, use_container_width=True,
                         column_config={"Match %": st.column_config.ProgressColumn("Match %", min_value=0, max_value=100, format="%.1f")})
            st.download_button("Download shortlist (.csv)", df.to_csv(index=False), file_name="shortlist.csv", mime="text/csv")
    with t2:
        for row in rows:
            res = data["details"][row["File"]]
            with st.expander(f"#{row['Rank']}  {row['Name']}  ·  {row['Verdict']}  ·  {row['Match %']}% match"):
                st.markdown("**Matched skills**")
                st.markdown(chips(res["matched"], "ok"), unsafe_allow_html=True)
                st.markdown("**Missing skills**")
                st.markdown(chips(res["missing"], "bad"), unsafe_allow_html=True)
                st.markdown("**All skills found**")
                st.markdown(chips(sorted(res["info"]["skills"]), "neutral"), unsafe_allow_html=True)
                st.caption(f"Resume score {res['score']}/100  ·  {res['word_count']} words  ·  {res['info']['email'] or 'no email'}")


# ---------------------------------------------------------------- mode switch
mode = st.radio("Mode", ["Candidate: improve my resume", "Recruiter: screen many resumes"],
                horizontal=True, label_visibility="collapsed")
if mode.startswith("Candidate"):
    candidate_mode()
else:
    recruiter_mode()
