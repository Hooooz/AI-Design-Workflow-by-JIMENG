import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.figma_service import FigmaSyncService, load_css_file

OUTPUT_FILE = "scripts/figma_sync.js"


def generate_script():
    try:
        css_content = load_css_file()
    except FileNotFoundError:
        css_content = ":root { --primary: #000000; }"

    token = os.getenv("FIGMA_ACCESS_TOKEN")
    file_key = os.getenv("FIGMA_FILE_KEY")

    if not token or not file_key:
        print(
            "Warning: FIGMA_ACCESS_TOKEN or FIGMA_FILE_KEY not set. Using default values."
        )
        token = "figd_placeholder"
        file_key = "placeholder"

    service = FigmaSyncService(token=token, file_key=file_key)
    variables = service.parse_css_variables(css_content)

    js_code = service.generate_plugin_script(variables)

    with open(OUTPUT_FILE, "w") as f:
        f.write(js_code)

    print(f"Generated {OUTPUT_FILE}")
    print(f"Found {len(variables)} CSS variables")
    for var, val in list(variables.items())[:5]:
        print(f"  - {var}: {val}")


if __name__ == "__main__":
    generate_script()
