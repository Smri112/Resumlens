"""score.py - analyse a resume: JD match, score out of 100, ATS checks, suggestions."""
import re
from urllib.parse import quote_plus

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from extract import extract_info, find_skills

ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "created", "led", "managed",
    "improved", "optimized", "reduced", "increased", "launched", "automated",
    "analyzed", "deployed", "integrated", "engineered", "organized", "trained",
    "collaborated", "delivered", "achieved", "established", "migrated", "tested",
    "debugged", "researched", "presented", "coordinated", "architected", "won",
}
WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "duties included", "hard worker",
    "team player", "go-getter", "various tasks", "etc.", "references available",
]

ROLES = {
    "Data Scientist": ["Python", "Machine Learning", "Pandas", "NumPy", "Statistics", "SQL", "Scikit-learn", "Data Visualization"],
    "ML / AI Engineer": ["Python", "Deep Learning", "TensorFlow", "PyTorch", "NLP", "Machine Learning", "Git", "Docker"],
    "Web Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "Git", "REST API", "SQL"],
    "Backend Developer": ["Python", "Java", "SQL", "REST API", "Django", "Docker", "Git", "PostgreSQL"],
    "Software Engineer": ["Data Structures", "Algorithms", "OOP", "Java", "Python", "Git", "SQL", "System Design"],
    "Data Analyst": ["SQL", "Excel", "Python", "Power BI", "Tableau", "Data Analysis", "Statistics", "Data Visualization"],
    "DevOps Engineer": ["Linux", "Docker", "Kubernetes", "AWS", "CI/CD", "Git", "Jenkins", "Bash"],
    "Android Developer": ["Java", "Kotlin", "Android", "Firebase", "Git", "REST API", "SQL", "Flutter"],
}


def match_jd(resume_text, jd_text, resume_skills):
    """Return (match %, matched skills, missing skills, jd skills)."""
    jd_skills = find_skills(jd_text)
    matched = sorted(jd_skills & resume_skills)
    missing = sorted(jd_skills - resume_skills)

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf = vec.fit_transform([resume_text, jd_text])
    sim = float(cosine_similarity(tfidf[0], tfidf[1])[0][0])
    text_pct = min(100.0, sim * 100 * 2)  # raw cosine is low for long texts, so scale it

    if jd_skills:
        skill_pct = len(matched) / len(jd_skills) * 100
        pct = 0.6 * skill_pct + 0.4 * text_pct
    else:
        pct = text_pct
    return round(pct, 1), matched, missing, sorted(jd_skills)


def ats_checks(text, info, pages, word_count):
    """List of (check name, passed, tip)."""
    sections = info["sections"]
    odd_chars = len(re.findall(r"[^\x00-\x7F]", text)) / max(len(text), 1)
    return [
        ("Email address found", bool(info["email"]), "Add a professional email at the top."),
        ("Phone number found", bool(info["phone"]), "Add a phone number recruiters can call."),
        ("Standard section headings", sum(sections.values()) >= 4,
         "Use plain headings like Education, Skills, Projects, Experience."),
        ("Length is 1-2 pages", pages <= 2, "Trim to 1-2 pages; ATS and recruiters skim."),
        ("Word count 250-900", 250 <= word_count <= 900, "Aim for 300-700 words of focused content."),
        ("Readable text (few special symbols)", odd_chars < 0.02,
         "Avoid icons, graphics and fancy symbols; ATS may misread them."),
        ("Bullet points used", bool(re.search(r"^[\s]*[-•*▪●]", text, re.M)),
         "Use bullet points for projects and experience."),
        ("LinkedIn or GitHub link", info["linkedin"] or info["github"],
         "Link your GitHub or LinkedIn profile."),
    ]


def learning_links(skill):
    q = quote_plus(skill)
    return {
        "YouTube": f"https://www.youtube.com/results?search_query={q}+tutorial+for+beginners",
        "Coursera": f"https://www.coursera.org/search?query={q}",
        "GeeksforGeeks": f"https://www.geeksforgeeks.org/search/?q={q}",
    }


def recommend_roles(resume_skills):
    out = []
    for role, needed in ROLES.items():
        have = [s for s in needed if s in resume_skills]
        gap = [s for s in needed if s not in resume_skills]
        out.append((role, round(len(have) / len(needed) * 100), gap))
    return sorted(out, key=lambda r: r[1], reverse=True)[:3]


def analyze(text, pages, jd_text=""):
    info = extract_info(text)
    skills = info["skills"]
    words = text.split()
    word_count = len(words)
    low = text.lower()
    has_jd = bool(jd_text.strip())

    tokens = set(re.findall(r"[a-z]+", low))
    verbs_found = sorted(ACTION_VERBS & tokens)
    weak_found = [p for p in WEAK_PHRASES if p in low]
    quantified = len(re.findall(r"\b\d+(?:\.\d+)?\s?%|\b\d{2,}\+?\s?(?:users|students|customers|projects|members|records|requests)", low))

    match_pct, matched, missing, jd_skills = (0.0, [], [], [])
    if has_jd:
        match_pct, matched, missing, jd_skills = match_jd(text, jd_text, skills)

    sec = info["sections"]
    contact = (4 if info["email"] else 0) + (3 if info["phone"] else 0) + (3 if (info["linkedin"] or info["github"]) else 0)
    sections_pts = 6 * sec["Education"] + 6 * sec["Skills"] + 6 * (sec["Projects"] or sec["Experience"]) + 2 * sec["Summary"]
    skills_pts = min(len(skills) / 12, 1) * 25
    wc_pts = 6 if 250 <= word_count <= 900 else 3 if 150 <= word_count <= 1200 else 0
    fmt_pts = wc_pts + (4 if pages <= 2 else 2)
    impact_pts = max(0, min(len(verbs_found) / 8, 1) * 9 + min(quantified / 3, 1) * 6 - min(len(weak_found), 3))

    breakdown = {
        "Skills": (round(skills_pts, 1), 25),
        "Sections": (sections_pts, 20),
        "Impact": (round(impact_pts, 1), 15),
        "Contact": (contact, 10),
        "Format": (fmt_pts, 10),
    }
    if has_jd:
        breakdown["JD match"] = (round(match_pct / 100 * 20, 1), 20)

    got = sum(v[0] for v in breakdown.values())
    total = sum(v[1] for v in breakdown.values())
    score = round(got / total * 100)

    ats = ats_checks(text, info, pages, word_count)

    tips = []
    if not info["email"] or not info["phone"]:
        tips.append("Add both an email and a phone number in the header.")
    for s, present in sec.items():
        if not present and s in ("Education", "Skills", "Projects"):
            tips.append(f"Add a clear '{s}' section.")
    if not sec["Summary"]:
        tips.append("Add a 2-3 line summary at the top stating your goal and strongest skills.")
    if len(skills) < 8:
        tips.append("List more relevant technical skills (aim for 10-15 you can really defend).")
    if len(verbs_found) < 5:
        tips.append("Start bullet points with action verbs such as Built, Developed, Optimized, Led.")
    if quantified < 2:
        tips.append("Add numbers to show impact, e.g. 'improved accuracy by 12%' or 'used by 200+ students'.")
    if weak_found:
        tips.append("Replace weak phrases (" + ", ".join(weak_found[:3]) + ") with specific achievements.")
    if word_count > 900 or pages > 2:
        tips.append("Shorten the resume to one page; students rarely need more.")
    if word_count < 250:
        tips.append("Your resume looks thin. Add project details, tools used and outcomes.")
    if missing:
        tips.append("Add these skills if you genuinely have them: " + ", ".join(missing[:8]) + ".")
    if not (info["github"] or info["linkedin"]):
        tips.append("Add GitHub and LinkedIn links so recruiters can verify your work.")
    if not tips:
        tips.append("Great resume. Tailor it to each job description for the best results.")

    roles = recommend_roles(skills)
    gap_skills = missing if missing else [s for s in roles[0][2]]

    return {
        "info": info, "score": score, "breakdown": breakdown, "has_jd": has_jd,
        "match_pct": match_pct, "matched": matched, "missing": missing, "jd_skills": jd_skills,
        "ats": ats, "tips": tips, "roles": roles, "gap_skills": gap_skills[:6],
        "word_count": word_count, "pages": pages, "verbs": verbs_found,
        "weak": weak_found, "quantified": quantified,
    }


def build_report(r):
    info = r["info"]
    lines = [
        "RESUMELENS - ANALYSIS REPORT", "=" * 34,
        f"Candidate : {info['name'] or 'Not detected'}",
        f"Email     : {info['email'] or 'Not found'}",
        f"Phone     : {info['phone'] or 'Not found'}",
        f"CGPA      : {info['cgpa'] or 'Not found'}",
        f"Overall score: {r['score']}/100",
    ]
    if r["has_jd"]:
        lines.append(f"Job description match: {r['match_pct']}%")
    lines += ["", "SCORE BREAKDOWN"]
    lines += [f"  {k:<10}{v[0]}/{v[1]}" for k, v in r["breakdown"].items()]
    lines += ["", "SKILLS FOUND", "  " + (", ".join(sorted(info["skills"])) or "None")]
    if r["has_jd"]:
        lines += ["", "MISSING SKILLS (from job description)", "  " + (", ".join(r["missing"]) or "None")]
    lines += ["", "ATS CHECKS"]
    lines += [f"  [{'PASS' if ok else 'FAIL'}] {name}" for name, ok, _ in r["ats"]]
    lines += ["", "SUGGESTIONS"] + [f"  - {t}" for t in r["tips"]]
    lines += ["", "TOP ROLE MATCHES"] + [f"  {role}: {pct}%" for role, pct, _ in r["roles"]]
    return "\n".join(lines)


def verdict(r, must_have, cutoff, min_cgpa=0):
    """Recruiter verdict. Returns (label, list of unmet hard requirements)."""
    unmet = [m for m in must_have if m not in r["info"]["skills"]]
    cgpa = r["info"].get("cgpa")
    if min_cgpa and (cgpa is None or cgpa < min_cgpa):
        unmet.append(f"CGPA {'not found' if cgpa is None else cgpa} (needs {min_cgpa}+)")
    pct = r["match_pct"]
    if pct >= cutoff and not unmet:
        return "Eligible", unmet
    if pct >= cutoff - 15:
        return "Maybe", unmet
    return "Not eligible", unmet
