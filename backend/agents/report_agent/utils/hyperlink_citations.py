import json
import os
import re


def add_hyperlinks_to_citations(markdown_content: str, reference_data: dict) -> str:
    """
    Adds hyperlinks to citations in a markdown string.

    Args:
        markdown_content: The string content of the markdown file.
        reference_data: A dictionary containing 'url_to_info' which maps
                        URLs to objects/dicts that have a 'citation_uuid' and 'url'.
                        It also expects 'url_to_unified_index' which maps a URL
                        to its citation index (the number used in text like [1]).
    Returns:
        The markdown content with citations hyperlinked.
    """
    if (
        not reference_data
        or "url_to_info" not in reference_data
        or "url_to_unified_index" not in reference_data
    ):
        print(
            "Warning: Reference data is missing or incomplete. Skipping hyperlink addition."
        )
        return markdown_content

    print(
        f"Adding hyperlinks to citations. Found {len(reference_data.get('url_to_unified_index', {}))} citation indexes."
    )

    index_to_url = {}
    for url, display_index in reference_data.get("url_to_unified_index", {}).items():
        if url in reference_data["url_to_info"]:
            # The Information class stores the url in a 'url' attribute.
            # If it's a dict (from JSON), it's a 'url' key.
            info_entry = reference_data["url_to_info"][url]
            actual_url = (
                info_entry.get("url")
                if isinstance(info_entry, dict)
                else getattr(info_entry, "url", None)
            )
            if actual_url:
                index_to_url[str(display_index)] = actual_url
            else:
                # Fallback if direct URL is not found (should not happen with valid reference_data)
                index_to_url[str(display_index)] = url
                print(f"Using fallback URL for citation [{display_index}]: {url}")
        else:
            # Fallback if URL is in url_to_unified_index but not in url_to_info (should not happen)
            index_to_url[str(display_index)] = url
            print(
                f"Warning: URL {url} found in url_to_unified_index but not in url_to_info. Using as fallback for citation [{display_index}]."
            )

    def replace_citation(match):
        # Extract just the digit from the citation [digit]
        citation_text = match.group(1)  # This now contains the entire [digit] format
        citation_index_str = re.search(r"\d+", citation_text).group(
            0
        )  # Extract just the number

        url = index_to_url.get(citation_index_str)
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            return f"[[{citation_index_str}]]({url})"
        return match.group(0)

    # Count the number of replacements made
    citation_count = len(re.findall(r"(?<!\[)(?<!\]\()(\[\d+\])", markdown_content))
    print(f"Found {citation_count} citation patterns to process.")

    markdown_content_new = re.sub(
        r"(?<!\[)(?<!\]\()(\[\d+\])", replace_citation, markdown_content
    )

    # Count final hyperlinks
    hyperlink_count = len(re.findall(r"\[\[\d+\]\]\(http", markdown_content_new))
    print(f"Added {hyperlink_count} hyperlinks to citations.")

    return markdown_content_new


if __name__ == "__main__":
    if len(os.sys.argv) < 4:
        print(
            "Usage: python hyperlink_citations.py <input_md_file> <reference_json_file> <output_md_file>"
        )
        os.sys.exit(1)

    input_md_path = os.sys.argv[1]
    reference_json_path = os.sys.argv[2]
    output_md_path = os.sys.argv[3]

    print(f"Input MD: {input_md_path}")
    print(f"Reference JSON: {reference_json_path}")
    print(f"Output MD: {output_md_path}")

    if not os.path.exists(input_md_path):
        print(f"Error: Input markdown file not found: {input_md_path}")
        os.sys.exit(1)
    if not os.path.exists(reference_json_path):
        print(f"Error: Reference JSON file not found: {reference_json_path}")
        os.sys.exit(1)

    with open(input_md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(reference_json_path, "r", encoding="utf-8") as f:
        refs_from_json = json.load(f)

    # The structure from StormArticle.reference is what add_hyperlinks_to_citations expects.
    # This usually has 'url_to_info' and 'url_to_unified_index' as top-level keys.
    # Information objects within url_to_info would have been serialized to dicts if dumped to JSON.
    reference_data_for_script = refs_from_json

    updated_md_content = add_hyperlinks_to_citations(
        md_content, reference_data_for_script
    )

    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(updated_md_content)

    print(f"Successfully added hyperlinks. Output written to: {output_md_path}")
