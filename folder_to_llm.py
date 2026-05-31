from pathlib import Path

IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"}
IGNORE_FILES = {".DS_Store"}

def generate_tree(path: Path, prefix: str = "") -> list[str]:
    lines = []
    entries = sorted(
        [p for p in path.iterdir() if p.name not in IGNORE_DIRS and p.name not in IGNORE_FILES],
        key=lambda p: (p.is_file(), p.name.lower())
    )

    for index, entry in enumerate(entries):
        connector = "└── " if index == len(entries) - 1 else "├── "
        lines.append(prefix + connector + entry.name)

        if entry.is_dir():
            extension = "    " if index == len(entries) - 1 else "│   "
            lines.extend(generate_tree(entry, prefix + extension))

    return lines

if __name__ == "__main__":
    root = Path("A:/Mo_portfolio/my_portfolio/src").resolve()

    output = [root.name]
    output.extend(generate_tree(root))

    tree_text = "\n".join(output)
    print(tree_text)

    with open("folder_structure_frontend.txt", "w", encoding="utf-8") as f:
        f.write(tree_text)