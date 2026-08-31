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


def sync_directory_duplicates() -> int:
    """Keep foo/index.html byte-identical to foo.html.

    Ten pages exist twice - as foo.html and as foo/index.html - so that both /foo
    and /foo/ resolve. Only the .html side gets regenerated, so five of the pairs
    had drifted and the trailing-slash URL was serving stale content: an
    out-of-date January 2026 page, an old $5.99 page, a stale Florida page. Both
    sides carry a canonical pointing at /foo, so search engines consolidate them.
    This only stops the copy going stale for the people who land on it.
    """
    synced = 0
    candidates = [
        (index_file, DOCS / f"{index_file.parent.name}.html")
        for index_file in DOCS.glob("*/index.html")
    ] + [
        (
            index_file,
            DOCS / index_file.parent.parent.name / f"{index_file.parent.name}.html",
        )
        for index_file in DOCS.glob("*/*/index.html")
    ]

    for index_file, source in candidates:
        if not source.is_file():
            continue
        content = source.read_text(encoding="utf-8")
        if index_file.read_text(encoding="utf-8", errors="replace") != content:
            index_file.write_text(content, encoding="utf-8")
            synced += 1
    return synced


def repoint_missing_image() -> int:
    """Point og:image and schema images at an asset that exists.

    83 pages referenced /icon-512.png, which was never in the repository, so every
    social preview and every schema image on those pages resolved to a 404. The
    real asset is /logo.png. Kept as a guard because several of those pages have no
    generator and are edited by hand.
    """
    if (DOCS / "icon-512.png").is_file():
        return 0  # someone added the real asset; leave references alone
    fixed = 0
    for path in DOCS.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "icon-512.png" in text:
            path.write_text(text.replace("icon-512.png", "logo.png"), encoding="utf-8")
            fixed += 1
    return fixed


def remove_published_template() -> bool:
    """docs/template.html is a build input, not a page.

    It was being served as a 62-word page whose canonical points at the homepage.
    """
    stray = DOCS / "template.html"
    if stray.is_file():
        stray.unlink()
        return True
    return False


def main() -> None:
    for filename in STATIC_FILES:
        copy_required_file(filename)

    write_file_if_changed(DOCS / ".nojekyll", "\n")
    write_file_if_changed(DOCS / "CNAME", "greatclipsdeal.com\n")

    repointed = repoint_missing_image()
    if repointed:
        print(f"Repointed /icon-512.png -> /logo.png in {repointed} file(s)")

    synced = sync_directory_duplicates()
    if synced:
        print(f"Synced {synced} directory duplicate(s) with their .html source")
    if remove_published_template():
        print("Removed stray docs/template.html (build input, not a page)")


if __name__ == "__main__":
    main()
