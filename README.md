# Multiple choice builder

## Purpose

As a teacher, I want to create mutiple-choice questionnaire for my students. With this repository, I just have to add a json file containing the questions, and it's automatically built and uploaded to GitHub Pages. This way, I can give the link to my students and they can try it.

## How does it work

To create a new questionnaire, add a JSON file in the `questionnaires` directory. When pushed to the GitHub repository, it's built and uploaded to GitHub Pages thanks to GitHub Actions.

### Prerequisite

You have to enable Pages from GitHub Actions on your repository. [See documentation](https://docs.github.com/fr/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publication-avec-un-workflow-github-actions-personnalis%C3%A9)

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