import os
import re
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_DIRS = ["services", "models", "scripts", "docs"]
IGNORE_DIRS = {
    "__pycache__", ".git", ".github", ".idea", ".vscode", "venv", "node_modules", "site-packages"
}
IGNORE_FILES = {
    ".DS_Store", "__init__.py"
}

def should_ignore(name):
    return name in IGNORE_DIRS or name in IGNORE_FILES

def generate_structure_markdown(root_dir, target_dirs):
    lines = []
    
    for target in target_dirs:
        dir_path = os.path.join(root_dir, target)
        if not os.path.exists(dir_path):
            continue
            
        lines.append(f"- `{target}/`")
        
        try:
            items = sorted(os.listdir(dir_path))
        except OSError as e:
            logger.warning(f"Cannot access directory {dir_path}: {e}")
            continue
            
        for item in items:
            if should_ignore(item):
                continue
                
            item_path = os.path.join(dir_path, item)
            is_dir = os.path.isdir(item_path)
            
            suffix = "/" if is_dir else ""
            lines.append(f"    - `{item}{suffix}`")
            
    return lines

def update_map(file_path, new_lines):
    with open(file_path, "r") as f:
        content = f.read()
        
    start_marker = "<!-- AUTOMATED-STRUCTURE-START -->"
    end_marker = "<!-- AUTOMATED-STRUCTURE-END -->"
    
    pattern = re.compile(f"({re.escape(start_marker)}).*?({re.escape(end_marker)})", re.DOTALL)
    
    new_content_block = f"{start_marker}\n" + "\n".join(new_lines) + f"\n{end_marker}"
    
    if start_marker not in content or end_marker not in content:
        logger.error("Markers not found in codebase_map.md")
        return False
        
    updated_content = pattern.sub(new_content_block, content)
    
    with open(file_path, "w") as f:
        f.write(updated_content)

    logger.info(f"Successfully updated {file_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate codebase structure markdown map")
    parser.add_argument("--root-dir", required=True, help="Root directory of the codebase")
    parser.add_argument("--output", help="Output markdown file path (optional)")
    args = parser.parse_args()

    markdown_lines = generate_structure_markdown(args.root_dir, TARGET_DIRS)

    if args.output:
        success = update_map(args.output, markdown_lines)
        if not success:
            exit(1)
    else:
        # Log summary for observability, keep print for stdout output
        logger.info(f"Generated {len(markdown_lines)} lines of markdown output")
        print("\n".join(markdown_lines))
