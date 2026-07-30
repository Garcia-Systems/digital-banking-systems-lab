"""Regression tests for copyable commands in reader-facing documentation."""

from pathlib import Path

import pytest

READER_DOCUMENTS = (
    *sorted(Path("book").glob("*.md")),
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    *sorted(Path("docs").glob("*.md")),
)
EXECUTABLE_FENCES = {"bash", "sh"}
COMMAND_PREFIXES = (
    ". ",
    "bank-sim ",
    "cd ",
    "docker ",
    "git ",
    "python ",
    "python3 ",
    "python3.13 ",
)


def markdown_fences(document: Path) -> list[tuple[str, list[str]]]:
    """Return the language and contents of every closed Markdown fence."""
    fences: list[tuple[str, list[str]]] = []
    language: str | None = None
    contents: list[str] = []

    for line in document.read_text().splitlines():
        if language is None and line.startswith("```"):
            language = line.removeprefix("```").strip()
            contents = []
        elif language is not None and line == "```":
            fences.append((language, contents))
            language = None
        elif language is not None:
            contents.append(line)

    assert language is None, f"unclosed Markdown fence in {document}"
    return fences


@pytest.mark.parametrize("document", READER_DOCUMENTS, ids=str)
def test_book_commands_are_separate_from_output(document: Path) -> None:
    """Keep executable fences prompt-free and prohibit book transcripts."""
    for language, lines in markdown_fences(document):
        assert not (document.parts[0] == "book" and language == "console"), (
            f"console fences are prohibited in {document}; put commands in a bash "
            "fence and expected output in a separate text fence"
        )

        if language not in EXECUTABLE_FENCES:
            continue

        prompted_lines = [line for line in lines if line.startswith(("$ ", "> ", "% "))]
        assert not prompted_lines, (
            f"remove shell prompts from the copyable {language} fence in {document}: "
            f"{prompted_lines}"
        )

        previous_was_continued = False
        output_like_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            is_command = stripped.startswith(COMMAND_PREFIXES)
            if stripped and not stripped.startswith("#"):
                if not is_command and not previous_was_continued:
                    output_like_lines.append(line)
                previous_was_continued = stripped.endswith("\\")
        assert not output_like_lines, (
            f"non-command content found in a copyable {language} fence in "
            f"{document}; move expected output to a text fence: {output_like_lines}"
        )
