"""MkDocs hook: drop the GitHub-only navigation line from each page.

On GitHub every page starts with a line linking to the other language and
back to the home page. The site has a language switcher and its own
navigation, and builds each language separately, so that line is removed
before rendering.
"""
import re

_GITHUB_NAV = re.compile(
    r"^\[(?:🇷🇺 Русская версия|🇬🇧 English version)\]\([^)]*\).*\n", re.MULTILINE)


def on_page_markdown(markdown, page, config, files):
    return _GITHUB_NAV.sub("", markdown, count=1)
