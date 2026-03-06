import os
import sys
import click
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

from .client import ConfluenceClient
from .exporter import PageExporter

# Load environment variables from .env file
# This must happen before click processes the decorators so that default envvars are loaded.
load_dotenv()


def parse_confluence_url(url_str: str):
    """
    Parses a Confluence URL to extract the base URL and page ID.
    Supports formats like:
    http://172.16.2.225:8090/pages/viewpage.action?pageId=162180277
    """
    try:
        parsed = urlparse(url_str)
        # Reconstruct base URL
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try to find pageId in query parameters
        query_params = parse_qs(parsed.query)
        page_id = None
        if 'pageId' in query_params:
            page_id = query_params['pageId'][0]
            
        # If not, try to parse from something like /display/SPACE/Page+Title (harder, requires different API)
        # Note: We enforce pageId in the query for this simple implementation
        if not page_id:
            raise ValueError("Could not find 'pageId' in URL query parameters.")
            
        return base_url, int(page_id)
    except Exception as e:
        raise click.ClickException(f"Failed to parse URL '{url_str}': {e}")


@click.command()
@click.option('--url', envvar='CONFLUENCE_URL', help='Confluence Base URL (e.g. http://172.16.2.225:8090)')
@click.option('--username', envvar='CONFLUENCE_USERNAME', required=True, help='Confluence Username')
@click.option('--password', envvar='CONFLUENCE_PASSWORD', required=True, help='Confluence Password')
@click.option('--page-id', type=int, help='The ID of the Confluence page to export.')
@click.option('--page-url', type=str, help='The full URL of the Confluence page (alternative to --url + --page-id).')
@click.option('--format', type=click.Choice(['html', 'markdown'], case_sensitive=False), default='markdown', help='Export format')
@click.option('--output', type=click.Path(file_okay=False, dir_okay=True), default='./export', help='Output directory')
@click.option('--recursive/--no-recursive', default=True, help='Recursively export child pages')
def main(url, username, password, page_id, page_url, format, output, recursive):
    """
    Recursively exports a Confluence page and its children.
    
    Credentials can be provided via flags or a .env file containing:
    CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD
    """
    # Resolve Page ID and Base URL
    final_url = url
    final_page_id = page_id
    
    if page_url:
        parsed_url, parsed_page_id = parse_confluence_url(page_url)
        # If user provided --page-url, it overrides --url and --page-id
        final_url = final_url or parsed_url
        final_page_id = final_page_id or parsed_page_id
        
    if not final_url:
        click.echo("Error: Missing Confluence URL. Provide --url or --page-url.", err=True)
        sys.exit(1)
        
    if not final_page_id:
        click.echo("Error: Missing Page ID. Provide --page-id or --page-url.", err=True)
        sys.exit(1)

    try:
        # Initialize Client
        client = ConfluenceClient(
            url=final_url,
            username=username,
            password=password
        )
        
        # Initialize Exporter
        exporter = PageExporter(
            client=client,
            output_dir=output,
            format_type=format
        )
        
        # Start Export
        exporter.export(
            page_id=final_page_id,
            recursive=recursive
        )
        
    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
