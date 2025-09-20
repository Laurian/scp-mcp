"""
SCP Content Converter Module

Converts SCP Foundation content from raw HTML to AI-friendly markdown format.
This module is part of the SCP MCP Server and handles the transformation of
SCP content for better AI/LLM comprehension.

Main entry point: html_to_markdown(html_content) -> Optional[str]

Conversion Rules:
- Discard boilerplate elements (licensing, rating widgets, navigation)
- Remove interactive elements and JavaScript
- Convert section headers to proper markdown format
- Preserve content structure (blockquotes, lists, tables, images)
- Handle special SCP formatting (redacted text, classification bars)
- Clean up excessive whitespace while maintaining structure
- Robust error handling for malformed HTML content
"""

import re
from typing import Optional

from bs4 import BeautifulSoup, Comment
from markitdown import MarkItDown


def clean_html_content(soup):
    """Remove boilerplate and unwanted elements from the HTML soup."""

    if soup is None:
        return None

    # Define all elements to remove by tag name
    tags_to_remove = ["script", "style", "iframe", "noscript"]

    # Define all classes to remove (with their tag types)
    classes_to_remove = {
        "div": [
            "licensebox",
            "rate-box",
            "creditRate",
            "rateBox",
            "info-container",
            "authorlink-wrapper",
            "authorbox",
            "authorcontent",
            "footnotes-footer",
            "warning-box",
            "page-options-box",
            "page-options-bottom",
            "footer-wikiwalk-nav",
            "page-tags",
            "top-bar",
            "content-panel",
            "print-footer",
            "page-rate-widget-box",
            "wiki-content-table",
            "credit-box",
            "footnotes",
            "page-history",
            "page-files",
            "page-info",
            "page-actions",
            "page-meta",
            "page-toolbar",
            "page-title",
            "page-header",
            "page-body",
            "page-content",
            "page-wrapper",
            "page-container",
            "page-main",
            "page-sidebar",
            "page-footer",
            "page-nav",
            "page-menu",
            # Interactive elements
            "interactive",
            "clickable",
            "button",
            "form",
            "input",
            "textarea",
            "select",
            "option",
            "sandbox",
            "simulation",
            "game",
            "hive",
            "bee",
            "flower",
            "queen",
            "worker",
            "resource",
            "smoke",
            "collection",
        ],
        "ul": ["creditRate", "rateBox"],
        "form": [],  # Remove all forms
        "input": [],  # Remove all inputs
        "button": [],  # Remove all buttons
        "textarea": [],  # Remove all textareas
        "select": [],  # Remove all selects
    }

    # Define IDs to remove
    ids_to_remove = [
        "u-adult-warning",
        "header",
        "footer",
        "side-bar",
        "page-content",  # This might be too aggressive, but let's see
        "main-content",
        "content",
        "sandbox",
        "hive",
        "bee-simulation",
        "interactive-area",
        "game-area",
        "form",
        "input",
        "button",
        "save-button",
        "reset-button",
        "finalOutput",
        "SandboxBase",
        "queenReturnSandbox",
        "finalOuterHousing",
    ]

    # Define content keywords for special handling
    content_keywords = {
        "warning-box": ["clearance", "cognitohazard", "memetic", "level", "authorized"],
        "collapsible-block": [
            "containment",
            "procedure",
            "description",
            "addendum",
            "interview",
            "test",
            "incident",
            "experiment",
        ],
    }

    # Interactive attributes to remove elements with
    interactive_attrs = [
        "onclick",
        "ondblclick",
        "onmousedown",
        "onmouseup",
        "onmouseover",
        "onmouseout",
        "onmouseenter",
        "onmouseleave",
        "onmousemove",
        "onkeydown",
        "onkeyup",
        "onkeypress",
        "onfocus",
        "onblur",
        "onchange",
        "oninput",
        "onsubmit",
        "onreset",
        "onselect",
        "onload",
        "onunload",
        "onresize",
        "onscroll",
        "ondrag",
        "ondragstart",
        "ondragend",
        "ondragenter",
        "ondragleave",
        "ondragover",
        "ondrop",
        "oncopy",
        "oncut",
        "onpaste",
        "ontouchstart",
        "ontouchend",
        "ontouchmove",
        "ontouchcancel",
        "onanimationstart",
        "onanimationend",
        "onanimationiteration",
        "ontransitionstart",
        "ontransitionend",
        "ontransitionrun",
        "ontransitioncancel",
        "onwheel",
        "oncontextmenu",
        "onerror",
        "onabort",
        "oncanplay",
        "oncanplaythrough",
        "oncuechange",
        "ondurationchange",
        "onemptied",
        "onended",
        "onloadeddata",
        "onloadedmetadata",
        "onloadstart",
        "onpause",
        "onplay",
        "onplaying",
        "onprogress",
        "onratechange",
        "onseeked",
        "onseeking",
        "onstalled",
        "onsuspend",
        "ontimeupdate",
        "onvolumechange",
        "onwaiting",
        "onpointerdown",
        "onpointerup",
        "onpointermove",
        "onpointerenter",
        "onpointerleave",
        "onpointerover",
        "onpointerout",
        "onpointercancel",
        "ongotpointercapture",
        "onlostpointercapture",
    ]

    # Remove by tag name
    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove by class
    for tag_name, classes in classes_to_remove.items():
        for class_name in classes:
            for tag in soup.find_all(tag_name, class_=class_name):
                tag.decompose()

    # Remove by ID
    for element_id in ids_to_remove:
        for tag in soup.find_all(id=element_id):
            tag.decompose()

    # Remove elements with interactive attributes
    try:
        for attr in interactive_attrs:
            for tag in soup.find_all(attrs={attr: True}):
                if tag is not None and hasattr(tag, "decompose"):
                    tag.decompose()
    except (AttributeError, TypeError):
        pass

    # Remove elements with JavaScript-style attributes
    try:
        for tag in soup.find_all(attrs={"style": True}):
            if tag is not None and hasattr(tag, "get") and hasattr(tag, "attrs"):
                style_attr = tag.get("style", "")
                if style_attr and (
                    "javascript:" in style_attr.lower()
                    or "display:none" in style_attr.lower()
                ):
                    tag.decompose()
    except (AttributeError, TypeError):
        pass

    # Remove elements containing JavaScript code (not in script tags)
    try:
        for tag in soup.find_all():
            if tag is not None and hasattr(tag, "get_text"):
                text_content = tag.get_text()
                if text_content and any(
                    js_keyword in text_content.lower()
                    for js_keyword in [
                        "function",
                        "var ",
                        "let ",
                        "const ",
                        "document.",
                        "window.",
                        "alert(",
                        "console.",
                    ]
                ):
                    # Only remove if it's not part of the main SCP content
                    if not tag.find_parent(
                        "div", id="page-content"
                    ) and not tag.find_parent("div", class_="scp-content"):
                        tag.decompose()
    except (AttributeError, TypeError):
        pass

    # Special handling for warning boxes and collapsible blocks
    try:
        for div in soup.find_all("div", class_="warning-box"):
            if div is not None and hasattr(div, "get_text"):
                text_content = div.get_text().strip()
                if not any(
                    keyword in text_content.lower()
                    for keyword in content_keywords["warning-box"]
                ):
                    div.decompose()

        for div in soup.find_all("div", class_="collapsible-block"):
            if div is not None and hasattr(div, "get_text"):
                text_content = div.get_text().strip()
                if not any(
                    keyword in text_content.lower()
                    for keyword in content_keywords["collapsible-block"]
                ):
                    div.decompose()
    except (AttributeError, TypeError):
        pass

    # Remove excessive CSS styling that appears after main content
    # Look for style tags that aren't in head
    try:
        for style_tag in soup.find_all("style"):
            if style_tag is not None and hasattr(style_tag, "find_parent"):
                if not style_tag.find_parent("head"):
                    style_tag.decompose()
    except (AttributeError, TypeError):
        pass

    # Remove divs that contain only CSS or are purely stylistic
    try:
        for div in soup.find_all("div"):
            if div is not None and hasattr(div, "get_text"):
                text_content = div.get_text().strip()
                # Remove divs that are mostly CSS or contain @import/@font-face
                if text_content and (
                    "@import" in text_content
                    or "@font-face" in text_content
                    or "position:" in text_content
                    or "display:" in text_content
                ):
                    div.decompose()
    except (AttributeError, TypeError):
        pass

    return soup


# Header patterns with hierarchy levels
HEADER_PATTERNS = {
    1: [  # H1 - Main document headers
        r"^Item #?:?\s*SCP-\d+",
        r"^Object Class:?",
        r"^Special Containment Procedures[\s\w\d\-\.]*:?",  # More flexible pattern
        r"^Description:?",
    ],
    2: [  # H2 - Primary sections
        r"^Addendum[\s\w\d\-\.]*:?",
        r"^Discovery:?",
        r"^Interview Log[\s\w\d\-\.]*:?",
        r"^Test Log[\s\w\d\-\.]*:?",
        r"^Incident[\s\w\d\-\.]*:?",
        r"^Experiment[\s\w\d\-\.]*:?",
        r"^Update[\s\w\d\-\.]*:?",
        r"^Appendix[\s\w\d\-\.]*:?",
        r"^Status Report[\s\w\d\-\.]*:?",
        r"^Timeline[\s\w\d\-\.]*:?",
        r"^Personnel[\s\w\d\-\.]*:?",
        r"^Technical Specifications?:?",
        r"^Recovery Log[\s\w\d\-\.]*:?",
        r"^Classification[\s\w\d\-\.]*:?",
        r"^Cross-[Rr]eference[\s\w\d\-\.]*:?",
        r"^Foundation[\s\w\d\-\.]*:?",
        r"^Site[\s\w\d\-\.]*:?",
        r"^Clearance[\s\w\d\-\.]*:?",
        r"^Access[\s\w\d\-\.]*:?",
        r"^Warning[\s\w\d\-\.]*:?",
        r"^Notice[\s\w\d\-\.]*:?",
        r"^Memo[\s\w\d\-\.]*:?",
        r"^Report[\s\w\d\-\.]*:?",
        r"^Log[\s\w\d\-\.]*:?",
        r"^Analysis[\s\w\d\-\.]*:?",
        r"^Summary[\s\w\d\-\.]*:?",
    ],
    3: [  # H3 - Subsections and detailed content
        r"^History:?",
        r"^Background:?",
        r"^Recovery:?",
        r"^Origin:?",
        r"^Note:?",
        r"^Researcher Note:?",
        r"^Administrator Note:?",
        r"^HMCL Note:?",
        r"^Overseer Note:?",
        r"^Threat Level:?",
        r"^\d+\.?\s*",  # Numbered sections
        r"^[A-Z][a-z]+ed?:\s*",  # Past tense sections
        r"^[A-Z][a-z]+ing?:\s*",  # Present continuous sections
    ],
}

# Compile regex patterns for each level
COMPILED_HEADER_PATTERNS = {
    level: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for level, patterns in HEADER_PATTERNS.items()
}

# Section pattern for header detection (compiled from H1 and H2 patterns)
all_header_patterns = HEADER_PATTERNS[1] + HEADER_PATTERNS[2]
SECTION_PATTERN = re.compile(
    r"^(" + "|".join(all_header_patterns) + r")$", re.IGNORECASE
)

# Additional patterns for special content
SPECIAL_CONTENT_PATTERNS = {
    "interview": re.compile(r"interview", re.IGNORECASE),
    "test_log": re.compile(r"test\s+log|experiment", re.IGNORECASE),
    "incident": re.compile(r"incident|breach|containment failure", re.IGNORECASE),
    "addendum": re.compile(r"addendum", re.IGNORECASE),
    "appendix": re.compile(r"appendix", re.IGNORECASE),
}


def convert_section_headers(soup, original_soup=None):
    """Convert <p><strong>Section:</strong> content patterns to proper headers."""

    if soup is None:
        return None

    # Use original_soup for creating new tags if provided
    tag_creator = original_soup if original_soup else soup

    # Find all paragraphs that might contain section headers
    for p_tag in soup.find_all("p"):
        # Skip if inside blockquote (preserve interview/test log formatting)
        if p_tag.find_parent("blockquote"):
            continue

        # Look for strong tag at the beginning
        strong_tag = p_tag.find("strong")
        if strong_tag and p_tag.contents and p_tag.contents[0] == strong_tag:
            strong_text = strong_tag.get_text().strip()

            # Check if it matches our section patterns
            if SECTION_PATTERN.match(strong_text):
                # Determine header level based on pattern matching
                header_level = 2  # Default to H2
                for level, patterns in HEADER_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, strong_text, re.IGNORECASE):
                            header_level = level
                            break
                    if header_level != 2:
                        break

                # Check if this is a short metadata header (like "Object Class: Safe")
                # First check if content is within the same paragraph
                header_text = strong_text.rstrip(":")

                # Get all text content after the strong tag
                remaining_content = []
                for content in p_tag.contents:
                    if content == strong_tag:
                        continue
                    try:
                        text = (
                            content.strip()
                            if hasattr(content, "strip")
                            else str(content).strip()
                        )
                    except (AttributeError, TypeError):
                        text = str(content).strip()
                    if text:
                        remaining_content.append(text)

                # If there's content in the same paragraph, include it
                if remaining_content:
                    combined_text = " ".join(remaining_content)
                    if len(combined_text) < 100 and not combined_text.startswith(
                        ("http", "www")
                    ):
                        # Create header with content included
                        header = tag_creator.new_tag(f"h{header_level}")
                        header.string = f"{header_text}: {combined_text}"

                        # Remove the strong tag from current paragraph
                        strong_tag.decompose()

                        # Insert header before the paragraph
                        p_tag.insert_before(header)

                        # Remove the now-empty paragraph
                        p_tag.decompose()
                        continue

                # Check if next element has short content to include
                next_element = p_tag.find_next_sibling()
                if (
                    next_element
                    and next_element.name in ["p", "div"]
                    and not next_element.find(
                        ["div", "blockquote", "ul", "ol", "table"]
                    )
                    and len(next_element.get_text().strip()) < 100
                ):  # Short content
                    next_text = next_element.get_text().strip()
                    if next_text and not next_text.startswith(
                        ("http", "www")
                    ):  # Not a link
                        # Create header with content included
                        header = tag_creator.new_tag(f"h{header_level}")
                        header.string = f"{header_text}: {next_text}"

                        # Remove the next element since we included its content
                        next_element.decompose()

                        # Remove the strong tag from current paragraph
                        strong_tag.decompose()

                        # Insert header before the paragraph
                        p_tag.insert_before(header)

                        # Remove the now-empty paragraph
                        p_tag.decompose()
                        continue

                # Create a new header element for regular headers
                header = tag_creator.new_tag(f"h{header_level}")
                header.string = header_text

                # Remove the strong tag from the paragraph
                strong_tag.decompose()

                # Insert header before the paragraph
                p_tag.insert_before(header)

                # If paragraph is now empty or just whitespace, remove it
                remaining_text = p_tag.get_text().strip()
                if not remaining_text:
                    p_tag.decompose()

    # Handle special formatting for newer SCP articles
    # Look for divs with class "anom-bar-container" that contain classification info
    for container in soup.find_all("div", class_="anom-bar-container"):
        # Extract and format classification information
        item_info = []

        # Get item number
        item_span = container.find("span", class_="item")
        number_span = container.find("span", class_="number")
        if item_span and number_span:
            item_info.append(
                f"**{item_span.get_text().strip()}** {number_span.get_text().strip()}"
            )

        # Get level
        level_div = container.find("div", class_="level")
        if level_div:
            item_info.append(f"**Level:** {level_div.get_text().strip()}")

        # Get containment class
        contain_class = container.find("div", class_="contain-class")
        if contain_class:
            class_text = contain_class.find("div", class_="class-text")
            if class_text:
                item_info.append(f"**Object Class:** {class_text.get_text().strip()}")

        # Get secondary class
        second_class = container.find("div", class_="second-class")
        if second_class:
            class_text = second_class.find("div", class_="class-text")
            if class_text:
                item_info.append(
                    f"**Secondary Class:** {class_text.get_text().strip()}"
                )

        # Get disruption class
        disrupt_class = container.find("div", class_="disrupt-class")
        if disrupt_class:
            class_text = disrupt_class.find("div", class_="class-text")
            if class_text:
                item_info.append(
                    f"**Disruption Class:** {class_text.get_text().strip()}"
                )

        # Get risk class
        risk_class = container.find("div", class_="risk-class")
        if risk_class:
            class_text = risk_class.find("div", class_="class-text")
            if class_text:
                item_info.append(f"**Risk Class:** {class_text.get_text().strip()}")

        if item_info:
            # Create a formatted header section
            header_section = tag_creator.new_tag("div")
            header_section.string = " | ".join(item_info)
            container.replace_with(header_section)

    return soup


def handle_special_formatting(soup, original_soup=None):
    """Handle special SCP formatting patterns found in newer articles."""

    # Use original_soup for creating new tags if provided
    tag_creator = original_soup if original_soup else soup

    # Convert div.collapsible-block-folded to h3 headers (common in newer SCPs)
    for tag in soup.find_all("div", class_="collapsible-block-folded"):
        # Check if it contains a link with header-like text
        link = tag.find("a", class_="collapsible-block-link")
        if link:
            header_text = link.get_text().strip()
            # Create a new header element
            header = tag_creator.new_tag("h3")
            header.string = header_text
            tag.replace_with(header)

    # Handle tabview containers (convert tabs to sequential sections)
    for tabview in soup.find_all("div", class_="yui-navset"):
        # Extract tab content and convert to sequential sections
        tab_content = tabview.find("div", class_="yui-content")
        if tab_content:
            tab_panels = tab_content.find_all("div", class_="yui-tab-content")
            for i, tab_panel in enumerate(tab_panels):
                # Create header for each tab
                header = tag_creator.new_tag("h3")
                header.string = f"Section {i + 1}"
                tab_panel.insert(0, header)
            # Replace tabview with just the content
            tabview.replace_with(tab_content)

    # Handle classification bars (convert to headers or preserve as warnings)
    for tag in soup.find_all("div", class_="classification-bar"):
        text_content = tag.get_text().strip()
        classification_keywords = [
            "classified",
            "restricted",
            "confidential",
            "top secret",
        ]
        if any(keyword in text_content.lower() for keyword in classification_keywords):
            # Convert to header
            header = tag_creator.new_tag("h2")
            header.string = text_content
            tag.replace_with(header)

    # Handle anomalous item bars (convert to proper headers)
    for tag in soup.find_all("div", class_="anom-bar"):
        # Extract item number and class information
        item_span = tag.find("span", class_="item")
        number_span = tag.find("span", class_="number")
        level_div = tag.find("div", class_="level")

        if item_span and number_span:
            item_text = item_span.get_text().strip()
            number_text = number_span.get_text().strip()
            level_text = level_div.get_text().strip() if level_div else ""

            # Create proper header
            header = tag_creator.new_tag("h1")
            header_text = f"{item_text} {number_text}"
            if level_text:
                header_text += f" - {level_text}"
            header.string = header_text
            tag.replace_with(header)

    # Handle containment class information
    for tag in soup.find_all("div", class_="contain-class"):
        class_text = tag.find("div", class_="class-text")
        if class_text:
            class_name = class_text.get_text().strip()
            # Create header for object class
            header = tag_creator.new_tag("h2")
            header.string = f"Object Class: {class_name}"
            tag.replace_with(header)

    # Handle redacted text formatting
    for tag in soup.find_all(["span", "div"], class_="redacted"):
        # Ensure redacted text is properly marked
        if not tag.get_text().strip().startswith("["):
            tag.string = f"[REDACTED: {tag.get_text().strip()}]"

    # Handle anomalous text formatting
    for tag in soup.find_all(["span", "div"], class_="anomalous"):
        # Mark anomalous text with special formatting
        tag.name = "em"
        tag["class"] = None

    return soup


def extract_main_content(soup):
    """Extract the main SCP content, avoiding navigation and boilerplate."""

    # Look for the main content container
    content_div = soup.find("div", id="page-content")
    if content_div:
        return content_div

    # Fallback to body if no page-content div found
    return soup.find("body") or soup


def convert_table_to_markdown(table_html):
    """Convert a single table to markdown using MarkItDown."""
    if not table_html.strip():
        return ""

    md = MarkItDown()

    # Use temporary file approach for reliable conversion
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        # Wrap table in minimal HTML structure
        html_content = f"""<!DOCTYPE html>
<html>
<head><title>Table</title></head>
<body>
{table_html}
</body>
</html>"""
        f.write(html_content)
        temp_path = f.name

    try:
        result = md.convert(temp_path)
        return result.text_content.strip()
    except Exception:
        # Fallback: return empty string if table conversion fails
        return ""
    finally:
        # Clean up temporary file
        os.unlink(temp_path)


def html_element_to_markdown(element):
    """Convert a BeautifulSoup element to markdown."""
    if element.name == "p":
        text = element.get_text().strip()
        return text if text else ""
    elif element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(element.name[1])
        prefix = "#" * level
        text = element.get_text().strip()
        return f"{prefix} {text}" if text else ""
    elif element.name == "blockquote":
        text = element.get_text().strip()
        if not text:
            return ""
        lines = text.split("\n")
        return "\n".join(f"> {line}" if line.strip() else "" for line in lines)
    elif element.name == "ul":
        items = []
        for li in element.find_all("li"):
            text = li.get_text().strip()
            if text:
                items.append(f"- {text}")
        return "\n".join(items) if items else ""
    elif element.name == "ol":
        items = []
        for i, li in enumerate(element.find_all("li"), 1):
            text = li.get_text().strip()
            if text:
                items.append(f"{i}. {text}")
        return "\n".join(items) if items else ""
    elif element.name == "strong" or element.name == "b":
        text = element.get_text().strip()
        return f"**{text}**" if text else ""
    elif element.name == "em" or element.name == "i":
        text = element.get_text().strip()
        return f"*{text}*" if text else ""
    elif element.name == "a":
        href = element.get("href", "")
        text = element.get_text().strip()
        if href and text:
            return f"[{text}]({href})"
        else:
            return text
    elif element.name == "br":
        return "\n"
    elif element.name == "div" and "class" in element.attrs:
        # Handle special div classes
        class_names = element.get("class", [])
        text = element.get_text().strip()

        if "collapsible-block" in class_names:
            # Handle collapsible blocks - extract content from unfolded version
            unfolded = element.find("div", class_="collapsible-block-unfolded")
            if unfolded:
                content = unfolded.find("div", class_="collapsible-block-content")
                if content:
                    return content.get_text().strip()
            return ""
        elif "anomalous" in class_names:
            return f"*{text}*" if text else ""
        elif "redacted" in class_names:
            return f"[REDACTED: {text}]" if text else ""
        elif "scp-image-block" in class_names:
            # Handle image blocks
            img = element.find("img")
            if img:
                alt = img.get("alt", "")
                src = img.get("src", "")
                if alt and src:
                    return f"![{alt}]({src})"
                elif src:
                    return f"![Image]({src})"
            return ""
        else:
            # For other divs, return text content if any
            return text if text else ""
    elif element.name == "table":
        # Handle tables separately
        return convert_table_to_markdown(str(element))
    elif element.name == "img":
        alt = element.get("alt", "")
        src = element.get("src", "")
        if alt and src:
            return f"![{alt}]({src})"
        elif src:
            return f"![Image]({src})"
        else:
            return ""
    else:
        # Default: return text content
        text = element.get_text().strip()
        return text if text else ""


def scp_html_to_markdown(html_content):
    """Convert SCP HTML content to clean markdown."""

    # Parse HTML with lxml parser for better performance if available
    try:
        soup = BeautifulSoup(html_content, "lxml")
    except ImportError:
        soup = BeautifulSoup(html_content, "html.parser")

    # Extract main content
    main_content = extract_main_content(soup)

    # Clean unwanted elements
    main_content = clean_html_content(main_content)

    # Convert section headers
    main_content = convert_section_headers(main_content, soup)

    # Handle special SCP formatting patterns
    main_content = handle_special_formatting(main_content, soup)

    # Convert to markdown using optimized processing
    markdown_parts = []

    # First, handle the main classification table
    classification_table = main_content.find("table")
    if classification_table:
        # Extract classification info from table
        rows = classification_table.find_all("tr")
        if len(rows) >= 2:
            # First row: Item # and Level
            first_row = rows[0]
            cols = first_row.find_all(["td", "th"])
            if len(cols) >= 2:
                item_text = cols[0].get_text().strip()
                level_text = cols[1].get_text().strip()
                # Clean up the item text
                if item_text.startswith("Item #:"):
                    item_text = item_text.replace("Item #:", "").strip()
                markdown_parts.append(f"## {item_text}")
                markdown_parts.append(f"**Level:** {level_text}")

            # Second row: Object Class and additional info
            second_row = rows[1]
            cols = second_row.find_all(["td", "th"])
            if len(cols) >= 2:
                object_class = cols[0].get_text().strip()
                classified_text = cols[1].get_text().strip()
                # Clean up the object class text
                if object_class.startswith("Object Class:"):
                    object_class = object_class.replace("Object Class:", "").strip()
                markdown_parts.append(f"**Object Class:** {object_class}")
                if classified_text and not classified_text.startswith("Classified"):
                    markdown_parts.append(f"**Classified:** {classified_text}")

    # Remove the classification table from further processing
    if classification_table:
        classification_table.decompose()

    # Process remaining elements in order with optimized batching
    elements_to_process = main_content.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "blockquote",
            "ul",
            "ol",
            "div",
            "table",
            "img",
            "br",
        ]
    )

    # Process elements in batches for better memory efficiency
    batch_size = 50
    for i in range(0, len(elements_to_process), batch_size):
        batch = elements_to_process[i : i + batch_size]

        for element in batch:
            # Skip script and style elements
            if element.name in ["script", "style"]:
                continue

            # Skip empty elements
            if not element.get_text().strip() and element.name != "br":
                continue

            markdown = html_element_to_markdown(element)
            if markdown:
                markdown_parts.append(markdown)

    # Join all parts
    markdown_content = "\n\n".join(markdown_parts)

    # Clean up excessive whitespace and normalize line endings
    markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
    markdown_content = re.sub(
        r"[ \t]+\n", "\n", markdown_content
    )  # Remove trailing spaces
    markdown_content = re.sub(
        r"\n\n\n+", "\n\n", markdown_content
    )  # Normalize multiple line breaks

    return markdown_content.strip()




def scp_html_to_markdown_fallback(html_content):
    """Fallback conversion using markitdown for edge cases."""
    md = MarkItDown()

    # Use temporary file approach for reliable conversion
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        # Wrap HTML in minimal structure if needed
        if not html_content.strip().startswith(
            "<!DOCTYPE"
        ) and not html_content.strip().startswith("<html"):
            html_content = f"""<!DOCTYPE html>
<html>
<head><title>SCP Content</title></head>
<body>
{html_content}
</body>
</html>"""
        f.write(html_content)
        temp_path = f.name

    try:
        result = md.convert(temp_path)
        return result.text_content.strip()
    except Exception as e:
        print(f"DEBUG: Markitdown fallback failed: {e}")
        return ""
    finally:
        # Clean up temporary file
        os.unlink(temp_path)


def html_to_markdown(html_content: str) -> Optional[str]:
    """Convert HTML content to AI-friendly markdown format.

    Args:
        html_content: Raw HTML content to convert to markdown

    Returns:
        Markdown content string, or None if conversion failed
    """
    # Check if HTML content is empty or nearly empty
    if not html_content or not html_content.strip() or len(html_content.strip()) < 50:
        return None

    try:
        # Convert to markdown
        markdown_content = scp_html_to_markdown(html_content)

        if not markdown_content:
            # Try fallback with markitdown
            markdown_content = scp_html_to_markdown_fallback(html_content)
            if not markdown_content:
                return None

        return markdown_content

    except Exception:
        # If conversion fails, return None
        return None
