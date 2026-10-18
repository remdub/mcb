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