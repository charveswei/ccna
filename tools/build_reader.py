"""Build the direct-launch browser reader from a decoded question-bank page."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "decoded_payload.html"
DESTINATION = ROOT / "web" / "index.html"
AUTO_LAUNCH = """
<!-- Added by the local reader build: skip the welcome screen and open the bank. -->
<script id="direct-reader-launch">
window.addEventListener('load', function () {
  window.setTimeout(function () {
    if (typeof startExam === 'function') startExam();
  }, 0);
});
</script>
"""


def main() -> None:
    page = SOURCE.read_text(encoding="utf-8")
    if "window._builtinQBankData=" not in page:
        raise RuntimeError("Decoded page does not contain an embedded question bank.")
    if "direct-reader-launch" not in page:
        if "</body>" not in page:
            raise RuntimeError("Decoded page has no closing body tag.")
        page = page.replace("</body>", AUTO_LAUNCH + "</body>", 1)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(page, encoding="utf-8")
    print(f"Built {DESTINATION}")


if __name__ == "__main__":
    main()
