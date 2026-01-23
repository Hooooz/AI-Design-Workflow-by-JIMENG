import os

file_path = "/Users/huangchuhao/.claude/plugins/marketplaces/claude-code-plugins/plugins/ralph-wiggum/commands/ralph-loop.md"
target_str = "${CLAUDE_PLUGIN_ROOT}"
replacement = "/Users/huangchuhao/.claude/plugins/marketplaces/claude-code-plugins/plugins/ralph-wiggum"

try:
    with open(file_path, "r") as f:
        content = f.read()

    new_content = content.replace(target_str, replacement)

    with open(file_path, "w") as f:
        f.write(new_content)

    print("File updated successfully")
except Exception as e:
    print(f"Error: {e}")
