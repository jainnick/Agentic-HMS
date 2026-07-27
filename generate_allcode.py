# generate_allcode.py
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT_DIR / "allcodehms.py"
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "output",
    "archive",
    ".ruff_cache",
    "htmlcov",
    "hotel_agent_backend.egg-info",
}
EXCLUDE_FILES = {"generate_allcode.py", "allcodehms.py", ".env", ".coverage"}
INCLUDE_EXTENSIONS = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".sql",
    ".toml",
    ".ini",
    ".cfg",
    ".gitignore",
}
EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pptx",
    ".xlsx",
    ".xls",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".log",
}
MAX_FILE_SIZE_MB = 5


# ============================================================
# FILE FILTERING
# ============================================================
def is_inside_excluded_dir(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def should_include_file(path: Path) -> bool:
    if path.name in EXCLUDE_FILES:
        return False
    if is_inside_excluded_dir(path.relative_to(ROOT_DIR)):
        return False
    if path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False
    # Allows extensionless files like .gitignore, Dockerfile, Makefile, etc.
    if (
        path.suffix.lower() not in INCLUDE_EXTENSIONS
        and path.name not in INCLUDE_EXTENSIONS
    ):
        return False
    try:
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return False
    except OSError:
        return False
    return True


def collect_files() -> list[Path]:
    files = []
    for path in ROOT_DIR.rglob("*"):
        if path.is_file() and should_include_file(path):
            files.append(path)
    return sorted(files, key=lambda p: str(p.relative_to(ROOT_DIR)).lower())


# ============================================================
# DIRECTORY TREE BUILDER
# ============================================================
def build_tree_from_files(files: list[Path]) -> str:
    """
    Builds tree only for included files.
    """
    tree = {}
    for file_path in files:
        relative_parts = file_path.relative_to(ROOT_DIR).parts
        current = tree
        for part in relative_parts:
            current = current.setdefault(part, {})
    lines = [f"└── {ROOT_DIR.name}/"]

    def add_lines(node: dict, prefix: str = "") -> None:
        items = sorted(node.items(), key=lambda item: (bool(item[1]), item[0].lower()))
        for index, (name, child) in enumerate(items):
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if child:
                extension = "    " if is_last else "│   "
                add_lines(child, prefix + extension)

    add_lines(tree, "    ")
    return "\n".join(lines)


# ============================================================
# FILE READING
# ============================================================
def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as error:
        return f"<<ERROR READING FILE: {error}>>"


# ============================================================
# OUTPUT GENERATOR
# ============================================================
def generate_allcode() -> None:
    files = collect_files()
    directory_structure = build_tree_from_files(files)
    output_parts = []
    output_parts.append("Directory structure:")
    output_parts.append(directory_structure)
    output_parts.append("")
    output_parts.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_parts.append(f"Total files included: {len(files)}")
    output_parts.append("")
    for file_path in files:
        relative_path = file_path.relative_to(ROOT_DIR).as_posix()
        file_content = read_text_file(file_path)
        output_parts.append("================================================")
        output_parts.append(f"FILE: {relative_path}")
        output_parts.append("================================================")
        output_parts.append(file_content.rstrip())
        output_parts.append("")
    final_output = "\n".join(output_parts)
    OUTPUT_FILE.write_text(final_output, encoding="utf-8")
    print(f"[OK] Generated: {OUTPUT_FILE}")
    print(f"[OK] Files included: {len(files)}")


if __name__ == "__main__":
    generate_allcode()
