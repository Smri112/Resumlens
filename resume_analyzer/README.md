# ResumeLens - AI Resume Analyzer

Two modes, chosen with the switch on the home page:

- **Candidate mode:** upload one resume (PDF/DOCX) and optionally a job description. Get a score out of 100,
  job match %, missing skills, ATS check, suggestions, role recommendations and learning links.
- **Recruiter mode:** paste one job description, upload up to 30 resumes, set a cutoff % and optional must-have
  skills. Get a ranked shortlist with an Eligible / Maybe / Not eligible verdict and a CSV download.

**Verdict rule:** Eligible = match >= cutoff and all must-have skills and the minimum CGPA are met. Maybe = within 15 points of the cutoff,
or a must-have requirement is not met. Otherwise Not eligible. This is a screening aid; the final decision stays with the recruiter.

## Run it
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
The app opens at http://localhost:8501. An internet connection is needed once for the Google Fonts.

## Try it with the sample data
`sample_data/` has 4 PDF resumes, 1 DOCX resume and `job_description_ml_intern.txt`.
- Candidate mode: upload any sample resume and paste the job description.
- Recruiter mode: upload all 5 resumes, paste the job description, set the cutoff to about 40%.
  Expected order: Aarav (strong ML) first, Kabir (almost empty resume) last.

## Test the code
```bash
python test_core.py
```
Checks PDF/DOCX reading, email/phone/CGPA extraction, ranking order, verdict rules and report generation.

## Deploy free (for a live demo link)
1. Push this folder to a GitHub repository.
2. Go to share.streamlit.io, sign in with GitHub, choose the repo and set the main file to `app.py`.
3. Click Deploy. `requirements.txt` is installed automatically.

## Files
| File | Job |
|---|---|
| `app.py` | Streamlit UI (home page, background image, charts, tabs) |
| `extract.py` | Reads PDF/DOCX, extracts name, email, phone, skills, sections |
| `score.py` | JD matching (TF-IDF + cosine similarity), scoring, ATS checks, suggestions, roles |
| `report_pdf.py` | Builds the downloadable PDF report |
| `make_samples.py` | Creates the sample resumes and job description |
| `test_core.py` | Automated tests |
| `data/skills.csv` | Skills database (250+ skills). Add more rows to improve detection |
| `sample_data/` | Sample resumes and job description for testing and demos |
| `assets/bg.jpg` | Home page background. Replace with any image, or rerun `make_bg.py` |
| `.streamlit/config.toml` | Dark theme colours |

## How the score is calculated (out of 100)
| Part | Marks |
|---|---|
| Skills found (12+ skills = full marks) | 25 |
| Sections present (Education, Skills, Projects/Experience, Summary) | 20 |
| Impact (action verbs, numbers, no weak phrases) | 15 |
| Contact details (email, phone, GitHub/LinkedIn) | 10 |
| Format (word count, pages) | 10 |
| Job description match (only if JD given) | 20 |

Without a JD, the score is scaled to 100 from the other parts.

## Job match formula
`match % = 0.6 x (matched JD skills / total JD skills) + 0.4 x (TF-IDF cosine similarity, scaled)`

## Viva questions to prepare
- **TF-IDF:** gives each word a weight; words frequent in a document but rare overall get higher weight.
- **Cosine similarity:** measures the angle between two text vectors; 1 = identical, 0 = nothing in common.
- **ATS:** Applicant Tracking System, software that filters resumes before humans see them.
- **Why not a trained ML model?** No labelled dataset; rule-based + similarity is explainable and reliable.

## Limitations (write in your report)
- Scanned/image PDFs cannot be read (no OCR).
- Only skills in `skills.csv` are detected.
- Name detection is a heuristic and can fail on unusual layouts.

## Future scope
LLM-based rewriting of bullet points, OCR for scanned resumes, user login and history with a database, support for more languages and resume layouts.
