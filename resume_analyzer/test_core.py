"""test_core.py - quick automated checks. Run:  python test_core.py   (or: pytest)"""
from pathlib import Path

from extract import extract_cgpa, extract_email, extract_phone, read_resume
from report_pdf import build_pdf
from score import analyze, build_report, verdict

SAMPLES = Path(__file__).parent / "sample_data"
JD = (SAMPLES / "job_description_ml_intern.txt").read_text(encoding="utf-8")


class FakeUpload:
    """Mimics Streamlit's uploaded file object."""
    def __init__(self, path):
        self.name = path.name
        self._data = path.read_bytes()

    def getvalue(self):
        return self._data


def run(name):
    text, pages = read_resume(FakeUpload(SAMPLES / name))
    return analyze(text, pages, JD)


def test_regex_helpers():
    assert extract_email("mail me at a.b@x.co.in now") == "a.b@x.co.in"
    assert extract_phone("call +91 98765 43210") is not None
    assert extract_cgpa("CGPA: 8.4") == 8.4
    assert extract_cgpa("92/100") is None


def test_reads_pdf_and_docx():
    for name in ["aarav_mehta_strong_ml.pdf", "meera_iyer_data_analyst.docx"]:
        text, pages = read_resume(FakeUpload(SAMPLES / name))
        assert len(text.split()) > 30 and pages >= 1


def test_ranking_order_is_sensible():
    names = ["aarav_mehta_strong_ml.pdf", "meera_iyer_data_analyst.docx", "diya_nair_web_developer.pdf",
             "rohan_gupta_average.pdf", "kabir_singh_weak.pdf"]
    res = {n: run(n) for n in names}
    match = {n: r["match_pct"] for n, r in res.items()}
    print("match %:", match)
    print("score  :", {n: r["score"] for n, r in res.items()})
    assert match[names[0]] == max(match.values())          # strongest ML resume ranks first
    assert match[names[-1]] == min(match.values())         # weakest ranks last
    assert res[names[0]]["score"] > res[names[-1]]["score"]


def test_verdicts():
    strong, weak = run("aarav_mehta_strong_ml.pdf"), run("kabir_singh_weak.pdf")
    assert verdict(strong, ["Python"], 40)[0] == "Eligible"
    assert verdict(weak, ["Python"], 40)[0] == "Not eligible"
    label, unmet = verdict(strong, [], 40, min_cgpa=9.5)   # CGPA 8.7 < 9.5
    assert label != "Eligible" and unmet


def test_reports_build():
    r = run("aarav_mehta_strong_ml.pdf")
    assert build_pdf(r)[:4] == b"%PDF"
    assert "Overall score" in build_report(r)


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
        print("PASS", fn.__name__)
