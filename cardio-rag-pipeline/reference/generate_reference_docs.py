"""
CardioRAG Reference Documents Generator
=======================================
Generates:
1. reference/Day1_Module_Timer_Cards.pdf (5 poster-style countdown cards)
2. reference/Day1_PreDay_Readiness_Checklist.pdf (Readiness checklist with trainer sign-off)
"""

import os
import sys
import pymupdf as fitz

NAVY = fitz.pdfcolor["navy"] if "navy" in fitz.pdfcolor else (0.05, 0.15, 0.35)
LIGHT_BG = (0.95, 0.97, 1.0)
CARD_BG = (0.98, 0.99, 1.0)
WHITE = (1.0, 1.0, 1.0)
DARK_TEXT = (0.1, 0.1, 0.15)
MUTED_TEXT = (0.35, 0.35, 0.45)
ACCENT_BLUE = (0.1, 0.4, 0.8)
ACCENT_GREEN = (0.05, 0.55, 0.25)
ACCENT_RED = (0.75, 0.15, 0.15)
BORDER_COLOR = (0.75, 0.82, 0.92)


def draw_card(page, rect, card_num, title, time_alloc, target_time, objectives, guardrail, deliverable, total_cards=5):
    """Draws a single poster-style timer card on a page."""
    # Background card
    page.draw_rect(rect, color=BORDER_COLOR, fill=CARD_BG, width=1.5)
    
    # Header box (Dark Navy)
    hdr_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 55)
    page.draw_rect(hdr_rect, color=NAVY, fill=NAVY)
    
    # Header text
    badge_text = f"CARD {card_num} OF {total_cards}"
    page.insert_text((rect.x0 + 15, rect.y0 + 22), badge_text, fontsize=10, fontname="helv", color=(0.6, 0.85, 1.0))
    page.insert_text((rect.x0 + 15, rect.y0 + 42), title.upper(), fontsize=13, fontname="hebo", color=WHITE)
    
    # Timer badge (Top Right)
    timer_box = fitz.Rect(rect.x1 - 180, rect.y0 + 10, rect.x1 - 15, rect.y0 + 45)
    page.draw_rect(timer_box, color=(0.2, 0.5, 0.9), fill=(0.1, 0.25, 0.55), width=1)
    page.insert_text((timer_box.x0 + 8, timer_box.y0 + 15), f"TIME: {time_alloc}", fontsize=9, fontname="hebo", color=WHITE)
    page.insert_text((timer_box.x0 + 8, timer_box.y0 + 28), f"TARGET: {target_time}", fontsize=9, fontname="helv", color=(0.8, 0.95, 0.8))

    # Objectives Section
    cur_y = rect.y0 + 75
    page.insert_text((rect.x0 + 15, cur_y), "OBJECTIVES & LAB TASKS:", fontsize=10, fontname="hebo", color=NAVY)
    cur_y += 18
    
    for obj in objectives:
        # Bullet point
        page.draw_circle(fitz.Point(rect.x0 + 22, cur_y - 3), 2.5, color=ACCENT_BLUE, fill=ACCENT_BLUE)
        page.insert_text((rect.x0 + 32, cur_y), obj, fontsize=9.5, fontname="helv", color=DARK_TEXT)
        cur_y += 16
        
    # Guardrail Box (Red Warning Alert)
    cur_y += 6
    guard_rect = fitz.Rect(rect.x0 + 15, cur_y, rect.x1 - 15, cur_y + 40)
    page.draw_rect(guard_rect, color=(0.9, 0.6, 0.6), fill=(1.0, 0.94, 0.94), width=1)
    page.insert_text((guard_rect.x0 + 10, guard_rect.y0 + 15), "HARD STOP GUARDRAIL:", fontsize=9, fontname="hebo", color=ACCENT_RED)
    page.insert_text((guard_rect.x0 + 10, guard_rect.y0 + 29), guardrail, fontsize=8.5, fontname="helv", color=DARK_TEXT)
    
    # Deliverable Box (Green Success)
    cur_y += 48
    deliv_rect = fitz.Rect(rect.x0 + 15, cur_y, rect.x1 - 15, cur_y + 32)
    page.draw_rect(deliv_rect, color=(0.6, 0.85, 0.6), fill=(0.94, 0.99, 0.94), width=1)
    page.insert_text((deliv_rect.x0 + 10, deliv_rect.y0 + 14), "DELIVERABLE:", fontsize=8.5, fontname="hebo", color=ACCENT_GREEN)
    page.insert_text((deliv_rect.x0 + 10, deliv_rect.y0 + 25), deliverable, fontsize=8.5, fontname="helv", color=DARK_TEXT)


def generate_module_timer_cards(output_pdf_path: str):
    """Generates the 5 poster-style timer countdown cards."""
    doc = fitz.open()
    
    cards_data = [
        {
            "card_num": 1,
            "title": "Task 1: Source Ingestion & License Verification",
            "time_alloc": "30 MINS",
            "target_time": "10:00 AM",
            "objectives": [
                "Acquire official guideline PDFs: WHO 2021 Hypertension & NICE NG238 Lipid Modification.",
                "Confirm source licensing (Open Access CC BY-NC-SA 3.0 IGO & Crown Copyright OGL).",
                "Verify file integrity, page counts, and absence of corrupted PDF text streams.",
            ],
            "guardrail": "Stop source vetting by 10:00! Do NOT spend time reading guidelines. Move to parsing immediately.",
            "deliverable": "data/raw/ directory populated with validated PDFs and confirmed licensing.",
        },
        {
            "card_num": 2,
            "title": "Task 2: Extraction & Medical Cleaning",
            "time_alloc": "45 MINS",
            "target_time": "10:45 AM",
            "objectives": [
                "Extract document text streams with page tracking using PyMuPDF.",
                "Extract structured clinical tables using pdfplumber.",
                "Strip repetitive running headers/footers while preserving medical terms.",
                "Preserve comparison operators (>=, <=, <, >) and dosage units (mmHg, mmol/L, mg).",
            ],
            "guardrail": "Cleaning must be purely structural. Never modify clinical sentences or thresholds.",
            "deliverable": "Cleaned page text stream with exact source PDF page boundaries intact.",
        },
        {
            "card_num": 3,
            "title": "Task 3: Guideline Structure & Recommendation Parsing",
            "time_alloc": "60 MINS",
            "target_time": "11:45 AM",
            "objectives": [
                "Detect major section headings, subheadings, and rationale blocks.",
                "Parse discrete recommendation IDs (e.g. 1.1.4, 1.6.7, WHO Rec 1-8).",
                "Extract recommendation publication and amendment dates (e.g. [2014, amended May 2023]).",
                "Map cross-references, technology appraisals (TAs), and clinical algorithms.",
            ],
            "guardrail": "Ensure 100% ID uniqueness across all chunks. Map orphan recommendations to parent sections.",
            "deliverable": "Parsed document hierarchy tree with classified recommendation blocks.",
        },
        {
            "card_num": 4,
            "title": "Task 4: Semantic Chunking & Clinical Enrichment",
            "time_alloc": "45 MINS",
            "target_time": "12:30 PM",
            "objectives": [
                "Produce standalone recommendation, rationale, table, and algorithm chunks.",
                "Enforce token length bounds (50 <= tokens <= 800) with tiktoken cl100k_base.",
                "Extract clinical metadata: populations, risk tools (QRISK3), lipid targets, drug doses.",
                "Assign clinical priority weights (Priority 1: Active Recommendations).",
            ],
            "guardrail": "No orphan sentences or micro-chunks (< 20 tokens). Keep each chunk fully self-contained.",
            "deliverable": "Enriched semantic chunk objects ready for Validation Gates V1-V6.",
        },
        {
            "card_num": 5,
            "title": "Task 5: Validation Gates V1-V6 & Trainer Sign-off",
            "time_alloc": "30 MINS",
            "target_time": "13:00 (CUTOFF: 13:30)",
            "objectives": [
                "Run Quality Gates V1-V6 (Unique IDs, Completeness, Bounds, Provenance, Priority, Idempotency).",
                "Emit final data/processed/*_chunks.json, *.jsonl, and QA preview markdown.",
                "Execute full pytest test suite (119/119 unit tests green).",
                "Present Readiness Checklist to Trainer for sign-off before 13:30 lunch cutoff!",
            ],
            "guardrail": "13:30 LUNCH HARD CUTOFF. Trainer sign-off is required before afternoon index-building session.",
            "deliverable": "Green test suite + validated chunks + signed Trainer Readiness Checklist.",
        },
    ]

    # Page 1: Cards 1 & 2
    p1 = doc.new_page(width=595, height=842)  # A4 Portrait
    p1.draw_rect(fitz.Rect(0, 0, 595, 50), color=NAVY, fill=NAVY)
    p1.insert_text((30, 32), "CARDIORAG  |  DAY 1 MODULE TIMER CARDS", fontsize=15, fontname="hebo", color=WHITE)
    p1.insert_text((420, 32), "POSTER COUNTDOWN", fontsize=10, fontname="helv", color=(0.7, 0.9, 1.0))
    
    draw_card(p1, fitz.Rect(30, 70, 565, 430), **cards_data[0])
    draw_card(p1, fitz.Rect(30, 455, 565, 815), **cards_data[1])

    # Page 2: Cards 3 & 4
    p2 = doc.new_page(width=595, height=842)
    p2.draw_rect(fitz.Rect(0, 0, 595, 50), color=NAVY, fill=NAVY)
    p2.insert_text((30, 32), "CARDIORAG  |  DAY 1 MODULE TIMER CARDS", fontsize=15, fontname="hebo", color=WHITE)
    p2.insert_text((420, 32), "POSTER COUNTDOWN", fontsize=10, fontname="helv", color=(0.7, 0.9, 1.0))
    
    draw_card(p2, fitz.Rect(30, 70, 565, 430), **cards_data[2])
    draw_card(p2, fitz.Rect(30, 455, 565, 815), **cards_data[3])

    # Page 3: Card 5 (Full Page Poster)
    p3 = doc.new_page(width=595, height=842)
    p3.draw_rect(fitz.Rect(0, 0, 595, 50), color=NAVY, fill=NAVY)
    p3.insert_text((30, 32), "CARDIORAG  |  DAY 1 MODULE TIMER CARDS", fontsize=15, fontname="hebo", color=WHITE)
    p3.insert_text((370, 32), "FINAL PRE-LUNCH GATE", fontsize=10, fontname="helv", color=(1.0, 0.8, 0.8))
    
    draw_card(p3, fitz.Rect(30, 70, 565, 450), **cards_data[4])
    
    # Bottom reminder box
    rem_rect = fitz.Rect(30, 480, 565, 780)
    p3.draw_rect(rem_rect, color=ACCENT_BLUE, fill=(0.95, 0.98, 1.0), width=1.5)
    p3.insert_text((rem_rect.x0 + 20, rem_rect.y0 + 35), "IMPORTANT PACING REMINDER FOR DAY 1", fontsize=12, fontname="hebo", color=NAVY)
    
    reminders = [
        "1. Keep Table Focus: Display the current module timer card prominently at your workspace table.",
        "2. Avoid Scope Creep: Do not spend time researching clinical guidelines beyond the scope of ingestion.",
        "3. Deterministic Ingestion: Use rule-based parsing for 100% reproducibility and clinical safety.",
        "4. Validation Gates V1-V6: All 6 quality gates must pass before requesting trainer sign-off.",
        "5. 13:30 Lunch Cutoff: Ensure your pipeline produces validated JSON/JSONL outputs before lunch.",
    ]
    ry = rem_rect.y0 + 65
    for r in reminders:
        p3.insert_text((rem_rect.x0 + 20, ry), r, fontsize=10, fontname="helv", color=DARK_TEXT)
        ry += 30

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc.save(output_pdf_path)
    doc.close()
    print(f"[OK] Generated: {output_pdf_path}")


def generate_readiness_checklist(output_pdf_path: str):
    """Generates the Pre-Day Readiness Checklist with Trainer Sign-off Box."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Header
    page.draw_rect(fitz.Rect(0, 0, 595, 60), color=NAVY, fill=NAVY)
    page.insert_text((30, 30), "CARDIORAG  |  DAY 1 PRE-DAY READINESS CHECKLIST", fontsize=14, fontname="hebo", color=WHITE)
    page.insert_text((30, 48), "Mandatory Gate Completed Before the 13:30 Lunch Cutoff", fontsize=9.5, fontname="helv", color=(0.8, 0.92, 1.0))

    cur_y = 80

    # Helper for checklist items
    def draw_section(title, items):
        nonlocal cur_y
        sec_hdr = fitz.Rect(30, cur_y, 565, cur_y + 20)
        page.draw_rect(sec_hdr, color=(0.8, 0.88, 0.96), fill=(0.92, 0.96, 1.0))
        page.insert_text((sec_hdr.x0 + 10, sec_hdr.y0 + 14), title, fontsize=10, fontname="hebo", color=NAVY)
        cur_y += 26
        
        for item in items:
            box_rect = fitz.Rect(35, cur_y - 9, 45, cur_y + 1)
            page.draw_rect(box_rect, color=ACCENT_GREEN, fill=(0.92, 0.99, 0.92), width=1)
            page.insert_text((box_rect.x0 + 2, box_rect.y0 + 8), "V", fontsize=8, fontname="hebo", color=ACCENT_GREEN)
            page.insert_text((55, cur_y), item, fontsize=8.5, fontname="helv", color=DARK_TEXT)
            cur_y += 15
        cur_y += 6

    # Gate 1
    draw_section("GATE 1: SOURCE DOCUMENTS & LICENSING VERIFICATION", [
        "WHO 2021 Hypertension Guideline (data/raw/WHO_2021.pdf) — Verified CC BY-NC-SA 3.0 IGO Open Access.",
        "NICE NG238 (2023) Lipid Modification Guideline (data/raw/NICE_2023.pdf) — Verified OGL Crown Copyright.",
        "File stream integrity verified: SHA-256 checksums match and no corrupt PDF objects detected.",
    ])

    # Gate 2
    draw_section("GATE 2: EXTRACTION & MEDICAL CLEANING VERIFICATION", [
        "Extraction Engines operational: PyMuPDF for text streams and pdfplumber for clinical tables.",
        "Boilerplate stripping verified: Headers, footers, and page numbers removed without loss of recommendations.",
        "Medical safety preserved: Comparison operators (>=, <=, <, >) and dosage units intact 100%.",
    ])

    # Gate 3
    draw_section("GATE 3: INGESTION PIPELINE & QUALITY GATES (V1–V6)", [
        "Gate V1 (Unique IDs): 100% globally unique, deterministic chunk IDs generated across all documents.",
        "Gate V2 (Completeness): All canonical recommendations present (WHO Rec 1-8, NICE 1.1-1.12).",
        "Gate V3 (Token Bounds): All chunks satisfy length criteria (50 <= tokens <= 800) with zero micro-chunks.",
        "Gate V4 (Provenance): Source file, starting PDF page number, and section hierarchy preserved per chunk.",
        "Gate V5 (Clinical Priority): Active clinical recommendations assigned Priority 1.",
        "Gate V6 (Idempotency): Pipeline execution is 100% reproducible and deterministic.",
    ])

    # Gate 4: Deliverables Summary Table
    sec_hdr = fitz.Rect(30, cur_y, 565, cur_y + 20)
    page.draw_rect(sec_hdr, color=(0.8, 0.88, 0.96), fill=(0.92, 0.96, 1.0))
    page.insert_text((sec_hdr.x0 + 10, sec_hdr.y0 + 14), "GATE 4: PIPELINE OUTPUT ARTIFACTS & TEST SUITE", fontsize=10, fontname="hebo", color=NAVY)
    cur_y += 26

    deliverables = [
        ("WHO Processed JSON", "data/processed/WHO_2021_chunks.json (104 chunks)", "READY"),
        ("WHO Vector JSONL & Preview", "data/processed/WHO_2021_chunks.jsonl / preview.md", "READY"),
        ("NICE Processed JSON", "data/processed/NICE_2023_chunks.json (143 chunks)", "READY"),
        ("NICE Vector JSONL & Preview", "data/processed/NICE_2023_chunks.jsonl / preview.md", "READY"),
        ("Automated Test Suite", "tests/ (119/119 unit & integration tests passing)", "100% PASSED"),
    ]
    for name, path, status in deliverables:
        page.draw_rect(fitz.Rect(35, cur_y - 9, 45, cur_y + 1), color=ACCENT_GREEN, fill=(0.92, 0.99, 0.92), width=1)
        page.insert_text((37, cur_y - 1), "V", fontsize=8, fontname="hebo", color=ACCENT_GREEN)
        page.insert_text((55, cur_y), f"{name}: {path}", fontsize=8.5, fontname="helv", color=DARK_TEXT)
        page.insert_text((490, cur_y), status, fontsize=8.5, fontname="hebo", color=ACCENT_GREEN)
        cur_y += 14

    cur_y += 10

    # Gate 5: Trainer Sign-off Box
    sign_box = fitz.Rect(30, cur_y, 565, 805)
    page.draw_rect(sign_box, color=NAVY, fill=(0.96, 0.98, 1.0), width=2)
    
    # Sign-off Header
    page.draw_rect(fitz.Rect(sign_box.x0, sign_box.y0, sign_box.x1, sign_box.y0 + 26), color=NAVY, fill=NAVY)
    page.insert_text((sign_box.x0 + 15, sign_box.y0 + 18), "TRAINER READINESS SIGN-OFF (MANDATORY BEFORE 13:30 CUTOFF)", fontsize=10, fontname="hebo", color=WHITE)
    
    sy = sign_box.y0 + 44
    page.insert_text((sign_box.x0 + 15, sy), "Participant / Team Name :  __________________________________________________________", fontsize=9, fontname="helv", color=DARK_TEXT)
    sy += 22
    page.insert_text((sign_box.x0 + 15, sy), "Table Number            :  _________________________    Total Chunks: WHO (104) | NICE (143)", fontsize=9, fontname="helv", color=DARK_TEXT)
    sy += 22
    page.insert_text((sign_box.x0 + 15, sy), "Pipeline Status         :  [X] Confirmed Source License   [X] Functioning Parser   [X] Tests Passed", fontsize=9, fontname="hebo", color=ACCENT_GREEN)
    sy += 22
    page.insert_text((sign_box.x0 + 15, sy), "Trainer Name            :  __________________________________________________________", fontsize=9, fontname="helv", color=DARK_TEXT)
    sy += 22
    page.insert_text((sign_box.x0 + 15, sy), "Trainer Signature       :  ___________________________   Sign-off Time: ____:____ (<=13:30)", fontsize=9, fontname="helv", color=DARK_TEXT)
    sy += 20
    
    status_badge = fitz.Rect(sign_box.x0 + 15, sy - 5, sign_box.x1 - 15, sy + 18)
    page.draw_rect(status_badge, color=ACCENT_GREEN, fill=(0.88, 0.97, 0.88), width=1)
    page.insert_text((status_badge.x0 + 10, status_badge.y0 + 15), "STATUS: APPROVED FOR AFTERNOON EMBEDDING & INDEX-BUILDING", fontsize=9.5, fontname="hebo", color=ACCENT_GREEN)

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc.save(output_pdf_path)
    doc.close()
    print(f"[OK] Generated: {output_pdf_path}")


def generate_spotcheck_protocol(output_pdf_path: str):
    """Generates the Day 2 Facilitator Spot-Check Protocol document."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Header
    page.draw_rect(fitz.Rect(0, 0, 595, 60), color=NAVY, fill=NAVY)
    page.insert_text((30, 30), "CARDIORAG  |  DAY 2 FACILITATOR SPOT-CHECK PROTOCOL", fontsize=14, fontname="hebo", color=WHITE)
    page.insert_text((30, 48), "Mandatory In-Person Audit to Combat Metric Drift & Guarantee Verification", fontsize=9.5, fontname="helv", color=(0.8, 0.92, 1.0))

    cur_y = 75

    # Section 1: Why Spot-Checks Exist
    sec1_hdr = fitz.Rect(30, cur_y, 565, cur_y + 20)
    page.draw_rect(sec1_hdr, color=(0.8, 0.88, 0.96), fill=(0.92, 0.96, 1.0))
    page.insert_text((sec1_hdr.x0 + 10, sec1_hdr.y0 + 14), "1. PURPOSE & ANTI-DRIFT PHILOSOPHY", fontsize=10, fontname="hebo", color=NAVY)
    cur_y += 26

    reasons = [
        "Self-Reported Metric Drift: Teams often grade borderline chunks as relevant (1) without verifying exact recommendation IDs.",
        "Reproducibility Requirement: Guarantees that reported Precision@5, Hit Rate, and MRR reflect actual live retriever outputs.",
        "Refusal & Hallucination Guard: Validates that out-of-scope queries (e.g. breast cancer screening) are strictly refused.",
    ]
    for r in reasons:
        page.draw_circle(fitz.Point(38, cur_y - 3), 2.5, color=ACCENT_BLUE, fill=ACCENT_BLUE)
        page.insert_text((48, cur_y), r, fontsize=8.5, fontname="helv", color=DARK_TEXT)
        cur_y += 14
    cur_y += 6

    # Section 2: 5-Step In-Person Audit Workflow
    sec2_hdr = fitz.Rect(30, cur_y, 565, cur_y + 20)
    page.draw_rect(sec2_hdr, color=(0.8, 0.88, 0.96), fill=(0.92, 0.96, 1.0))
    page.insert_text((sec2_hdr.x0 + 10, sec2_hdr.y0 + 14), "2. THE 5-STEP LIVE IN-PERSON AUDIT WORKFLOW", fontsize=10, fontname="hebo", color=NAVY)
    cur_y += 26

    steps = [
        ("Step 1: Random Draw", "Facilitator unannouncedly draws 1 in-scope query + 1 out-of-scope query from team scorecard."),
        ("Step 2: Live Execution", "Participant runs retrieval query live in terminal/notebook directly in front of the facilitator."),
        ("Step 3: Chunk Audit", "Facilitator inspects top-5 chunks, chunk_ids, and PDF page provenance against data/raw/ guidelines."),
        ("Step 4: Cross-Grading", "Facilitator independently grades 0/1 relevance against clinical ground truth recommendations."),
        ("Step 5: Delta & Sign-off", "Compares Reported vs Verified Live P@5. Discrepancy delta must be <= 10% for certification."),
    ]
    for s_title, s_desc in steps:
        page.draw_rect(fitz.Rect(35, cur_y - 9, 130, cur_y + 4), color=ACCENT_BLUE, fill=(0.94, 0.97, 1.0), width=1)
        page.insert_text((38, cur_y - 1), s_title, fontsize=8, fontname="hebo", color=NAVY)
        page.insert_text((138, cur_y), s_desc, fontsize=8.5, fontname="helv", color=DARK_TEXT)
        cur_y += 16
    cur_y += 6

    # Section 3: Audit Tolerance Rubric
    sec3_hdr = fitz.Rect(30, cur_y, 565, cur_y + 20)
    page.draw_rect(sec3_hdr, color=(0.8, 0.88, 0.96), fill=(0.92, 0.96, 1.0))
    page.insert_text((sec3_hdr.x0 + 10, sec3_hdr.y0 + 14), "3. AUDIT SCORING RUBRIC & DISCREPANCY TOLERANCE", fontsize=10, fontname="hebo", color=NAVY)
    cur_y += 26

    rubrics = [
        ("Precision@5 Delta", "|Reported P@5 - Live P@5| <= 10%", "PASS if <= 10%; Re-evaluate scorecard if > 10%"),
        ("Hit@5 Alignment", "Exact agreement on Top-1 / Top-3 chunk", "Invalidate question score on mismatch"),
        ("Refusal Validation", "100% clean refusal on out-of-scope query", "Critical failure if retriever hallucinates answer"),
        ("Provenance Check", "100% valid PDF page & chunk_id link", "Disqualify index if fake chunk IDs detected"),
    ]
    for r_item, r_tol, r_act in rubrics:
        page.insert_text((35, cur_y), f"• {r_item}:", fontsize=8.5, fontname="hebo", color=NAVY)
        page.insert_text((140, cur_y), f"Tolerance: {r_tol}", fontsize=8.5, fontname="helv", color=DARK_TEXT)
        page.insert_text((360, cur_y), f"Action: {r_act}", fontsize=8, fontname="helv", color=ACCENT_RED)
        cur_y += 14
    cur_y += 10

    # Section 4: Facilitator Certification Box
    sign_box = fitz.Rect(30, cur_y, 565, 810)
    page.draw_rect(sign_box, color=NAVY, fill=(0.96, 0.98, 1.0), width=2)
    
    # Sign Box Header
    page.draw_rect(fitz.Rect(sign_box.x0, sign_box.y0, sign_box.x1, sign_box.y0 + 24), color=NAVY, fill=NAVY)
    page.insert_text((sign_box.x0 + 15, sign_box.y0 + 16), "OFFICIAL FACILITATOR SPOT-CHECK AUDIT SHEET", fontsize=10, fontname="hebo", color=WHITE)

    sy = sign_box.y0 + 40
    page.insert_text((sign_box.x0 + 15, sy), "Team / Table Number    :  _______________________________________________________________", fontsize=8.5, fontname="helv", color=DARK_TEXT)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Participant Name(s)    :  _______________________________________________________________", fontsize=8.5, fontname="helv", color=DARK_TEXT)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Selected In-Scope QID  :  [  ] WHO_01..07   [  ] NICE_01..07   ──   Query: ________________________", fontsize=8.5, fontname="helv", color=DARK_TEXT)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Reported Precision@5   :  _______ %     Verified Live P@5: _______ %     Delta (Δ): _______ %", fontsize=8.5, fontname="hebo", color=NAVY)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Selected Refusal QID   :  [  ] WHO_08 (Breast Cancer)  [  ] NICE_08 (Appendicitis)  ──  Refused? [  ] YES  [  ] NO", fontsize=8.5, fontname="helv", color=DARK_TEXT)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Audit Outcome          :  [  ] PASSED & CERTIFIED (Delta <= 10%)     [  ] RE-EVALUATION REQUIRED", fontsize=8.5, fontname="hebo", color=ACCENT_GREEN)
    sy += 20
    page.insert_text((sign_box.x0 + 15, sy), "Facilitator Name       :  ___________________________   Signature: __________________________", fontsize=8.5, fontname="helv", color=DARK_TEXT)
    sy += 18
    page.insert_text((sign_box.x0 + 15, sy), "Audit Timestamp        :  ____ / ____ / 2026  ──  ____ : ____   Status: [X] OFFICIAL VERIFICATION", fontsize=8.5, fontname="helv", color=DARK_TEXT)

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc.save(output_pdf_path)
    doc.close()
    print(f"[OK] Generated: {output_pdf_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, "reference")
    
    timer_pdf = os.path.join(ref_dir, "Day1_Module_Timer_Cards.pdf")
    checklist_pdf = os.path.join(ref_dir, "Day1_PreDay_Readiness_Checklist.pdf")
    spotcheck_pdf = os.path.join(ref_dir, "Day2_Facilitator_SpotCheck_Protocol.pdf")
    
    generate_module_timer_cards(timer_pdf)
    generate_readiness_checklist(checklist_pdf)
    generate_spotcheck_protocol(spotcheck_pdf)
    print("\n[SUCCESS] All reference PDF documents generated successfully in 'reference/' directory.")
