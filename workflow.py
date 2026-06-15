"""
Pipeline orchestrator — runs all stages in sequence.
"""

import json
import logging
from datetime import date
from openai import AsyncOpenAI
from drive import download_resume, upload_resume, delete_old_dated_resume
from naukri import update_naukri_profile
from state import save_state

log = logging.getLogger(__name__)
client = AsyncOpenAI()


async def call_claude(system: str, user: str, max_tokens: int = 2000) -> str:
    resp = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return resp.choices[0].message.content


def parse_json(text: str) -> dict:
    import re
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise ValueError(f"No JSON in response: {text[:200]}")
    return json.loads(match.group())


async def classify(message: str) -> dict:
    log.info("Stage 1: Classifying message...")
    system = """You are a resume relevance classifier. Respond ONLY with valid JSON.
Classify as RESUME_WORTHY if: completed project/deliverable, measurable outcome (numbers/scale/time saved), new skill used professionally, leadership moment, client win, process improvement built.
Classify as NOT_WORTHY if: routine task, vague update, meeting with no clear output, personal news.
JSON format:
{"verdict":"RESUME_WORTHY","reason":"one sentence","extracted_achievement":"rewritten in strong action-verb resume language","suggested_section":"Experience or Projects or Skills or Certifications"}"""

    raw = await call_claude(system, f"Work update: {message}")
    return parse_json(raw)


async def update_resume(current_resume: str, achievement: str, section: str) -> dict:
    log.info(f"Stage 2: Updating resume (section: {section})...")
    system = """You are an expert resume writer and ATS specialist.
STRICT RULES: Max 2 pages. No colors/graphics/tables/icons. ATS score >85. Strong action verbs. Quantify impact. Consistent formatting.
Sections order: Summary → Experience → Skills → Projects → Education → Certifications.
If adding causes overflow, trim 1-2 weakest/oldest bullets.
Return the COMPLETE updated resume as plain text, then this JSON audit on a new line:
{"change_summary":"what changed","estimated_pages":1,"ats_confidence":"High","ats_score_estimate":90,"warnings":[]}"""

    user = f"CURRENT RESUME:\n{current_resume}\n\nNEW ACHIEVEMENT (add to {section}):\n{achievement}"
    raw = await call_claude(system, user, max_tokens=3000)

    import re
    json_match = re.search(r'\{[\s\S]*\}', raw)
    audit = {}
    resume_text = raw
    if json_match:
        try:
            audit = json.loads(json_match.group())
            resume_text = raw[:raw.rfind('{')].strip()
        except Exception:
            pass

    return {"resume_text": resume_text, "audit": audit}


async def quality_gate(resume_text: str) -> dict:
    log.info("Stage 3: Quality gate check...")
    system = """You are a resume quality auditor. Respond ONLY with this JSON:
{"pass":true,"ats_score_estimate":88,"estimated_pages":1,"checklist":{"within_2_pages":true,"action_verbs":true,"quantified_bullets":true,"no_design_elements":true,"no_pronouns":true,"consistent_dates":true,"no_errors":true},"issues":[],"approved_for_save":true}
Set approved_for_save to true ONLY if pass is true AND ats_score_estimate >= 85."""

    raw = await call_claude(system, f"Audit this resume:\n{resume_text}")
    return parse_json(raw)


async def generate_naukri_content(resume_text: str) -> dict:
    log.info("Stage 5: Generating Naukri content...")
    system = """You are a Naukri.com profile optimizer. Generate updated profile content.
LIMITS: Headline max 250 chars. Summary: 3 short plain-text paragraphs (no bullets). Key Skills: top 15-20 comma-separated. IT Skills: tools/platforms/languages only.
Respond ONLY with this JSON:
{"headline":"...","summary":"para1\\n\\npara2\\n\\npara3","key_skills":["skill1"],"it_skills":["tool1"],"flags":[]}"""

    raw = await call_claude(system, f"Resume:\n{resume_text}\nToday: {date.today()}")
    return parse_json(raw)


async def run_pipeline(message: str) -> dict:
    today = date.today().isoformat()

    # Stage 1: Classify
    classification = await classify(message)
    log.info(f"Verdict: {classification['verdict']}")

    if classification["verdict"] != "RESUME_WORTHY":
        return {
            "verdict": "NOT_WORTHY",
            "reason": classification.get("reason", "Not resume-worthy.")
        }

    achievement = classification["extracted_achievement"]
    section = classification.get("suggested_section", "Experience")

    # Stage 2: Fetch current resume from Drive
    log.info("Fetching resume from Drive...")
    current_resume = download_resume("resume_base")

    # Stage 3: Update resume
    update_result = await update_resume(current_resume, achievement, section)
    updated_resume = update_result["resume_text"]
    audit = update_result["audit"]

    # Stage 4: Quality gate — retry once if it fails
    gate = await quality_gate(updated_resume)
    if not gate.get("approved_for_save"):
        log.warning(f"Quality gate failed: {gate.get('issues')}. Retrying with fix instructions...")
        issues_str = "; ".join(gate.get("issues", ["improve quality"]))
        fix_prompt = f"Fix these issues and return the corrected resume:\n{issues_str}\n\nRESUME:\n{updated_resume}"
        retry = await call_claude(
            "You are a resume editor. Fix the issues listed and return only the corrected resume text.",
            fix_prompt,
            max_tokens=3000
        )
        updated_resume = retry
        gate = await quality_gate(updated_resume)

    if not gate.get("approved_for_save"):
        raise Exception(f"Resume failed quality gate after retry. Issues: {gate.get('issues')}")

    # Stage 5: Save to Drive (keep only 2 files: base + latest dated)
    log.info("Saving updated resume to Drive...")
    delete_old_dated_resume()
    upload_resume(updated_resume, f"resume_{today}")

    # Stage 6: Update Naukri
    log.info("Updating Naukri profile...")
    naukri_content = await generate_naukri_content(updated_resume)
    naukri_status = update_naukri_profile(naukri_content)

    # Save state for /status command
    save_state({
        "last_update": today,
        "last_section": section,
        "last_achievement": achievement,
        "last_ats_score": gate.get("ats_score_estimate", 0),
        "last_pages": gate.get("estimated_pages", 1)
    })

    return {
        "verdict": "RESUME_WORTHY",
        "achievement": achievement,
        "section": section,
        "ats_score": gate.get("ats_score_estimate", 0),
        "pages": gate.get("estimated_pages", 1),
        "date": today,
        "naukri_status": naukri_status,
        "reason": classification.get("reason", "")
    }
