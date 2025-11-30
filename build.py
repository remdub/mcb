# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///

import shutil
from pathlib import Path

# Configuration
DIST_DIR = Path("dist")
TEMPLATE_HTML = "quiz.html"

def main():
    """
    Generates the quiz website in the dist directory.
    """
    # Create dist directory, cleaning it first if it exists
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()

    print(f"Created directory: {DIST_DIR}")

    # Copy script.js and style.css
    shutil.copy("script.js", DIST_DIR)
    shutil.copy("style.css", DIST_DIR)
    print("Copied script.js and style.css")

    # Read the HTML template
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        html_template = f.read()

    # Find all JSON files in the current directory
    json_files = list(Path("questionnaires").glob("*.json"))

    if not json_files:
        print("No JSON files found. Nothing to build.")
        return

    for json_file in json_files:
        # Copy the JSON file to dist
        shutil.copy(json_file, DIST_DIR)
        print(f"Copied {json_file} to {DIST_DIR}")

        # Generate the new HTML file name
        html_file_name = json_file.with_suffix(".html").name
        output_html_path = DIST_DIR / html_file_name

        # Modify the template
        # The quiz.html template has a script tag with id="quiz-script" and data-json="..."
        # We need to replace the value of data-json with the current json file name.
        # I will replace the whole script tag to be safe.
        
        old_script_tag = 'data-json="quizData.json"'
        new_script_tag = f'data-json="{json_file.name}"'
        
        new_html_content = html_template.replace(old_script_tag, new_script_tag)

        # Write the new HTML file
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(new_html_content)
        print(f"Generated {output_html_path}")

    generate_index_html()

    print("\nBuild complete!")
    print(f"You can now open the HTML files in the '{DIST_DIR}' directory.")


def generate_index_html():
    """
    Generates an index.html file with a list of all generated quizzes.
    """
    print("Generating index.html...")
    html_files = sorted(list(DIST_DIR.glob("*.html")))
    
    # Start of the HTML content
    index_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste des Quiz</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Liste des Quiz</h1>
        <ul>
"""

    # Add a list item for each HTML file
    for html_file in html_files:
        if html_file.name != "index.html":
            index_content += f'            <li><a href="{html_file.name}">{html_file.stem}</a></li>\n'

    # End of the HTML content
    index_content += """        </ul>
    </div>
</body>
</html>
"""

    # Write the index.html file
    with open(DIST_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_content)
    print("Generated index.html")


if __name__ == "__main__":
    main()
