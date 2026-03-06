import os
import re
from typing import Dict, Any

import markdownify
from bs4 import BeautifulSoup


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a valid cross-platform filename.
    """
    # Replace invalid path characters with hyphens
    sanitized = re.sub(r'[\\/*?:"<>|]', "-", name)
    # Remove leading/trailing whitespaces
    return sanitized.strip()

def process_html_content(html_content: str, title: str, attachments_dir: str = None) -> str:
    """
    Process HTML content to fix image links and add basic styling.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Optional: Basic CSS for the HTML export
    style = soup.new_tag('style')
    style.string = """
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 2rem; max-width: 900px; margin: 0 auto; color: #333; }
        h1, h2, h3, h4 { color: #172b4d; margin-top: 1.5em; }
        img { max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        pre { background: #f4f5f7; padding: 1em; border-radius: 4px; overflow-x: auto; }
        code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 0.9em; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; }
        th, td { border: 1px solid #dfe1e6; padding: 0.5rem; text-align: left; }
        th { background-color: #f4f5f7; }
        blockquote { border-left: 4px solid #dfe1e6; margin: 0; padding-left: 1rem; color: #6b778c; }
    """
    
    head = soup.find('head')
    if head:
        head.append(style)
    else:
        # Wrap everything in an html structure if it's just a fragment
        new_soup = BeautifulSoup(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title></head><body></body></html>", 'html.parser')
        new_soup.head.append(style)
        # Move original contents into the new body
        for tag in soup.contents:
             new_soup.body.append(tag.extract())
        soup = new_soup

    # Update image links to point to local attachments if they exist
    if attachments_dir:
        # Finding Confluence specific image tags
        for img in soup.find_all('img'):
            src = img.get('src')
            # For Confluence attachments, usually ri:filename is used in storage format
            # but in view format it's an actual src URL with the filename embedded
            if src:
                # Try to extract just the filename from typical confluence attachment URLs
                # Or use the data-image-src if it exists
                filename = None
                data_linked_resource = img.get('data-linked-resource-default-alias')
                
                if data_linked_resource:
                    filename = data_linked_resource
                else:
                    # Very basic fallback: take the last part of the path, removing query params
                    urll = src.split('?')[0]
                    filename = urll.split('/')[-1]
                
                if filename:
                    # URL encode the filename for local link
                    import urllib.parse
                    encoded_filename = urllib.parse.quote(filename)
                    # Use a relative path to the attachments folder
                    img['src'] = f"./attachments/{encoded_filename}"

    return str(soup)

def save_as_html(title: str, html_content: str, save_path: str, attachments_dir: str = None) -> None:
    """
    Process and save the content as an HTML file.
    """
    processed_html = process_html_content(html_content, title, attachments_dir)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(processed_html)

def save_as_markdown(title: str, html_content: str, save_path: str, attachments_dir: str = None) -> None:
    """
    Convert the HTML content to Markdown and save it.
    """
    # First, let's fix up the HTML so image links point correctly for markdown too
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if attachments_dir:
        for img in soup.find_all('img'):
            data_linked_resource = img.get('data-linked-resource-default-alias')
            if data_linked_resource:
                import urllib.parse
                img['src'] = f"./attachments/{urllib.parse.quote(data_linked_resource)}"
    
    # Custom markdownify configuration for better confluence conversion
    # For example, preserving tables and code blocks correctly
    class ConfluenceMarkdownConverter(markdownify.MarkdownConverter):
        def convert_code(self, el, text, parent_tags):
            # Sometimes confluence code blocks are within pre tags or have specific classes
            return super().convert_code(el, text, parent_tags)
            
        def convert_pre(self, el, text, parent_tags):
            # Try to get language from confluence macros if present
            # Confluence standard code macro often uses classes like "theme: Confluence; brush: python"
            lang = ""
            classes = el.get('class', [])
            for c in classes:
                if c.startswith('brush:'):
                    lang = c.split(':')[1].strip()
                    break
            
            # Remove leading/trailing newlines in the code block content
            code_text = text.strip()
            return f"```{lang}\n{code_text}\n```\n"

    converter = ConfluenceMarkdownConverter(
        heading_style="ATX",
        code_language="",
        escape_asterisks=False,
        escape_underscores=False,
    )
    
    markdown_text = converter.convert(str(soup))
    
    # Prepend the title as an H1 if it's not already the first thing
    if not markdown_text.lstrip().startswith('# '):
        markdown_text = f"# {title}\n\n{markdown_text}"
        
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)
