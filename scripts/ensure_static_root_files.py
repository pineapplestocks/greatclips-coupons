from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

STATIC_FILES = [
    "ads.txt",
    "googleac01e447c5ec05f2.html",
    "6b4474afbc6183c57a91.txt",
]


def copy_required_file(filename: str) -> None:
    source = ROOT / filename
    destination = DOCS / filename
    if not source.is_file():
        raise FileNotFoundError(f"Required static file is missing: {source}")

    DOCS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_file_if_changed(path: Path, content: str) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def main() -> None:
    for filename in STATIC_FILES:
        copy_required_file(filename)

    write_file_if_changed(DOCS / ".nojekyll", "\n")
    write_file_if_changed(DOCS / "CNAME", "greatclipsdeal.com\n")


if __name__ == "__main__":
    main()
