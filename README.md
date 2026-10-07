# PathForge V2

> A code analysis tool for figuring out **how a Python solution actually works**.

[![Live App](https://img.shields.io/badge/LIVE_APP-2457D6?style=for-the-badge&logo=vercel&logoColor=white)](https://path-forge-v2.vercel.app/)
[![GitHub](https://img.shields.io/badge/SOURCE-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/vedanshmehrotra/PathForge-v2)

---

## The idea

Most coding platforms stop at *accepted* or *wrong answer*.

PathForge tries to look one step further:

**What strategy is actually present in the code?**

A Python submission is parsed into an AST, analyzed by independent pattern detectors, and then compared with the approaches associated with the problem.

The goal is not to have an LLM guess an answer and call it a day. The system tries to make the reasoning behind a detection visible and testable.

> A detector saying `dynamic programming` means a lot more when there is actual structural evidence behind it.

---

## 📸 The app

<img width="1897" height="1003" alt="{AFE54765-9564-4F14-982D-A71FBD6105F9}" src="https://github.com/user-attachments/assets/47f5d948-0548-438c-bd43-679bb410e9af" />

<img width="1891" height="1003" alt="{D7CDF3DC-F50B-4EE5-B528-B4BAD73AC591}" src="https://github.com/user-attachments/assets/ff6d2e59-4deb-4a5e-8b96-f6858adaba6a" />

<img width="1893" height="1004" alt="{58CABD04-0FAF-4AB1-86F2-B72E1B361CE0}" src="https://github.com/user-attachments/assets/5400477a-f7f1-4b01-8a0e-571aa964b3cd" />

---

## What happens to a submission?

```text
Python solution
      ↓
   Parse AST
      ↓
Extract structural signals
      ↓
Run pattern detectors
      ↓
Collect evidence + confidence
      ↓
Match against accepted approaches
      ↓
Feed results into learning / recommendations
```

The interesting part is in the middle.

PathForge looks at implementation details such as control flow, loops, state changes, index relationships, membership checks, table access, and other code-level signals.

That means it is analysing the **implementation**, not just the problem statement.

---

## 🔍 Pattern detection

The V2 detector system is built around independent detectors.

Each detector:

- gets the same parsed AST
- looks for one specific pattern
- produces structured evidence
- applies its own decision rules
- does not depend on another detector's output
- produces deterministic results for the same input

The current architecture defines **44 algorithmic patterns**.

The decision is deliberately split into separate steps:

```text
Evidence
   ↓
Confidence
   ↓
Gating rules
   ↓
Detected / Not detected
```

So a detector having a 70% confidence score does not automatically mean the pattern is confirmed.

---

## 🧩 Matching

Once the code has been analysed, PathForge compares the detected patterns with accepted solution groups for the problem.

The matcher currently works with three outcomes:

| Result | Meaning |
|---|---|
| `FULL_MATCH` | The accepted approach is represented |
| `PARTIAL_MATCH` | Part of the approach is present |
| `NO_MATCH` | No accepted approach was matched |

Only sufficiently strong detections move into this stage. Uncertain signals are not quietly turned into facts.

---

## One part I care about: evidence

This is probably the less flashy part of PathForge, but it matters.

A pattern suggested by an LLM is not automatically treated as ground truth.

The system keeps track of where evidence came from:

```text
llm_proposed
structurally_observed
externally_listed
unobserved
conflicted
```

That distinction can then affect what happens downstream.

For example, low-authority information can stay in:

```text
analysis_only
```

instead of directly changing a learner's:

- ELO
- topic profile
- gap signals
- recommendations

So the pipeline can separate:

**"the code appears to use this pattern"**

from:

**"we are confident enough to use this information to update the learner model."**

---

## ⚙️ Under the hood

The main analysis path looks roughly like this:

```text
                Submission
                    │
                    ▼
            Problem resolution
                    │
                    ▼
          Accepted solution groups
                    │
                    ▼
              AST analysis
        ┌───────────┼───────────┐
        │           │           │
     Parser      Detectors   Coordinator
        │           │           │
        └───────────┼───────────┘
                    ▼
             Output pipeline
                    │
                    ▼
            Matching engine
                    │
                    ▼
         Evidence / authority checks
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
         ELO      Topics   Recommendations
```

The V2 AST components currently live around:

```text
src/ast_detection/
├── parser.py
├── detector_manager.py
├── coordinator.py
├── output_pipeline.py
├── detectors/
└── tests/
```

The repository also contains the application layer, frontend, database code, evaluation scripts, and the architecture documents that came out of the design process.

---

## 🧪 Testing

Testing is split across the main parts of the system rather than relying only on the UI.

The repository contains tests and evaluation material for:

- AST detectors
- matching
- evidence handling
- ground-truth construction
- adversarial cases
- product-level behaviour

I'm keeping the exact pass counts in the README as a **living section**, since V2 is still changing.

Useful reports:

- `IMPLEMENTATION_AUDIT_REPORT.md`
- `AST_ARCHITECTURE.md`
- `MATCHING_ENGINE.md`
- `DETECTOR_DECISION_RULE.md`
- `PRODUCT_REVIEW.md`

---

## 🛠️ Tech stack

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Flask-111111?style=for-the-badge&logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white">
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white">
</p>

<p>
  <img src="https://img.shields.io/badge/Next.js-111111?style=for-the-badge&logo=next.js&logoColor=white">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white">
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white">
</p>

<p>
  <img src="https://img.shields.io/badge/Python_ast-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/REST_APIs-555555?style=for-the-badge">
  <img src="https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white">
  <img src="https://img.shields.io/badge/Vercel-111111?style=for-the-badge&logo=vercel&logoColor=white">
</p>

---

## 🚀 Running it locally

### Backend

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it and install the dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` from `.env.example` and add the required configuration.

The backend has evolved across Flask and FastAPI components, so the exact entry point depends on the part of the application you are running.

### Frontend

```bash
cd pathforge-frontend
npm install
npm run dev
```

---

## 📁 Repository layout

```text
PathForge-v2/
├── pathforge/              # Application + learning pipeline
├── src/                    # V2 AST analysis
├── pathforge-frontend/     # Next.js frontend
├── docs/                   # Supporting documentation
├── *_report.md             # Audits / evaluation reports
├── *.json                  # Evaluation data
└── requirements.txt
```

---

## 🚧 Current status

PathForge V2 is still being worked on.

Some parts of the system are stable, while others are still being refined. The repository keeps architecture notes, tests, evaluation results, and unresolved issues alongside the implementation rather than hiding them behind a polished demo.

That is intentional.

The project is less about making a flashy "AI code analyser" and more about seeing how far a **structured, evidence-based approach** to code understanding can actually go.

