# Multiple choice builder

## Purpose

As a teacher, I want to create multiple-choice questionnaires for my students. With this repository, I just have to add a json file containing the questions, and it's automatically built and uploaded to GitHub Pages. This way, I can give the link to my students and they can try it.

[The questionnaires are available by clicking here.](https://remdub.github.io/mcb/)


## How does it work

To create a new questionnaire, add a JSON file in the `questionnaires` directory. When pushed to the GitHub repository, it's built and uploaded to GitHub Pages thanks to GitHub Actions.

### Prerequisite

You have to enable Pages from GitHub Actions on your repository. [See documentation](https://docs.github.com/fr/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publication-avec-un-workflow-github-actions-personnalis%C3%A9)

### AI Agent Skill: `multiple-choice-builder`

This repository includes a dedicated AI agent skill located in [`.agents/skills/multiple-choice-builder`](./.agents/skills/multiple-choice-builder).

It allows an AI assistant (such as Antigravity, Gemini CLI, Claude, or any tool supporting `.agents/skills`) to act as a pedagogical expert for teachers in Fédération Wallonie-Bruxelles (FWB), specifically for the **Techniques de Transition Informatique (TTI)** curriculum.

#### What the skill provides
- **Embedded TTI Curriculum**: Includes the official FWB reference documents in [`references/referentiel/`](./.agents/skills/multiple-choice-builder/references/referentiel/) covering all UAAs (*Unités d'Acquis d'Apprentissage*) from 3rd to 6th secondary education.
- **Bloom's Taxonomy Alignment**: Guides evaluation design across cognitive levels (Remember, Understand, Apply, Analyze, Evaluate, Create) according to [`references/bloom_taxonomy.md`](./.agents/skills/multiple-choice-builder/references/bloom_taxonomy.md).
- **Automated JSON Generation**: Generates 10-question multiple-choice quizzes strictly following the JSON schema required by this project, with student-friendly phrasing ("tu", ages 14–18).

#### How to use the skill
1. **Open the project in your AI coding assistant** (e.g. Antigravity). The assistant automatically discovers the `multiple-choice-builder` skill.
2. **Prompt the agent to create a quiz**, for example:
   - *"Crée un QCM de 10 questions sur l'UAA 2 (programmation séquentielle) pour des élèves de 3e au niveau Application."*
   - *"Génère une évaluation formative sur les bases de données (UAA 7). Propose d'abord 3 types d'évaluations selon Bloom, puis génère le QCM."*
   - *"Crée un questionnaire QCM sur le réseau (UAA 15) et enregistre-le dans `questionnaires/uaa15.json`."*
3. **The agent automatically**:
   - Reads the relevant UAA content and Bloom taxonomy guide.
   - Proposes or generates the 10 questions with 4 options each and appropriate feedback tiers.
   - Saves the questionnaire file directly into `questionnaires/<name>.json`.
4. **Publish**:
   - Commit and push the new JSON file (`git add questionnaires/ && git commit -m "Add quiz" && git push`).
   - GitHub Actions will automatically build and publish the quiz to your GitHub Pages site.
   - You can also test locally by running `python3 build.py` and opening `dist/index.html`.

### Curriculum Ingestion Pipeline: `convert_curriculum.py`

This repository includes a standalone curriculum processing pipeline: [`convert_curriculum.py`](./convert_curriculum.py).

It converts **any** official curriculum PDF (such as CPEONS, FWB, SEGEC, WBE) into modular, AI-agent-friendly Markdown documents complete with YAML frontmatter, cross-unit prerequisites graphs, and LLM manifest catalogs. This pipeline powers the reference files in [`.agents/skills/multiple-choice-builder/references/referentiel/`](./.agents/skills/multiple-choice-builder/references/referentiel/).

#### Key Features
- **Zero-Configuration Dynamic Discovery**: Automatically discovers all curriculum units (UAA, units, modules, chapters), learning situations, timetable grids, and pedagogical guidelines without hardcoded unit lists.
- **Metadata & Relationship Extraction**: Parses unit titles, grades/years, hours, competencies, and computes bidirectional prerequisite links (`prerequisites` and `leads_to`).
- **Agent Manifests**: Generates `00_AGENT_MANIFEST.md` and `agent_manifest.json` optimized for LLM agent tool-calling, RAG indexing, and context window efficiency.
- **Two-Tier Caching**: Caches raw Marker extraction in `.cache/raw_marker.md` so re-splitting, styling, or formatting tweaks run in under 2 seconds with `--skip-marker`.
- **Lightweight CPU / CUDA Support**: Automatically selects CUDA or CPU with memory safety. Self-contained dependency management via [`uv`](https://docs.astral.sh/uv/) and PEP 723 metadata (using CPU PyTorch wheels by default to avoid huge downloads).

#### Requirements
- Python `3.11` or `3.12`
- [`uv`](https://docs.astral.sh/uv/)

#### Usage

##### 1. Convert into the Skill Reference Directory
To update or populate the embedded curriculum used by the AI agent skill:
```bash
uv run convert_curriculum.py "path/to/curriculum.pdf" \
  --output-dir .agents/skills/multiple-choice-builder/references/referentiel
```

##### 2. Basic Conversion
Convert any curriculum PDF into a default output folder (`./output_<pdf_name>`):
```bash
uv run convert_curriculum.py "path/to/curriculum.pdf"
```

##### 3. Rapid Iteration (Skip OCR)
Once the PDF has been parsed once by Marker, reuse the cached raw extraction to iterate on splitting and post-processing in seconds:
```bash
uv run convert_curriculum.py "path/to/curriculum.pdf" --skip-marker
```

##### 4. Test a Subset of Pages
Extract and inspect only specific pages (e.g. pages 0 to 20):
```bash
uv run convert_curriculum.py "path/to/curriculum.pdf" --page-range 0-20
```

##### 5. Available Options
| Flag | Description | Default |
|---|---|---|
| `-o, --output-dir` | Target output directory | `./output_<pdf_name>` |
| `--mode {fast, balanced}` | Marker mode: `fast` (lightweight layout) or `balanced` (full VLM) | `fast` |
| `--device {auto, cpu, cuda}` | Compute device selection | `auto` |
| `--unit-prefixes` | Comma-separated list of unit prefixes to discover | `UAA,Unité,Module,Chapitre` |
| `--catalog-file, -c` | Path to JSON/YAML file providing custom metadata overrides | `None` |
| `--skip-marker` | Reuse cached raw extraction to iterate post-processing in seconds | `False` |
| `--disable-images` | Disable image extraction from PDF | `False` |

#### Output Structure
Running the pipeline produces a structured directory:
```
output_dir/
├── 00_AGENT_MANIFEST.md            # Markdown summary table of all units and prerequisites
├── agent_manifest.json             # Structured JSON catalog for AI tool-calling
├── 01_cadre_general_et_profil.md   # General curriculum framework and profiles
├── 02_grilles_horaires.md          # Timetable grids and period distributions
├── 03_considerations_pedagogiques_et_evaluation.md # Pedagogical & evaluation guidance
├── 04_glossaire.md                 # Terminology glossary
├── 05_bibliographie_et_annexes.md  # Bibliography and appendices
├── uaa/                            # Individual learning units with YAML frontmatter
│   ├── uaa_01_*.md
│   └── ...
├── situations_apprentissage/       # Learning situations and practical assignments
├── full/                           # Full cleaned curriculum markdown
└── assets/images/                  # Extracted diagrams and figures
```

### Json file structure

```json
{
  "title": "MCQ title",
  "quiz": {
    "questions": [
        {
            "question": "What is my first question ?",
            "options": [
                "Wrong answer",
                "Another wrong answer",
                "Good answer",
                "Wrong answer"
            ],
            "correct": 2
        },
        {
            "question": "Second question ?",
            "options": [
                "You're right",
                "Another wrong answer",
                "Wrong answer",
                "Wrong answer"
            ],
            "correct": 0
        }
    ],
    "results": {
        "excellent": "Excellent !!!",
        "good": "Very good.",
        "average": "Not bad.",
        "bad": "You can do better."
    },
    "intro": {
        "line1": "This is a test MCQ.",
        "line2": "Good luck."
    }
  }
}
```