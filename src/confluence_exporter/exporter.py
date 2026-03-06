import os
from typing import Dict, Any, List, Set
from rich.console import Console
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from .client import ConfluenceClient
from .formatters import save_as_html, save_as_markdown, sanitize_filename

console = Console()

class PageExporter:
    """Orchestrates the recursive downloading and formatting of Confluence pages."""
    
    def __init__(self, client: ConfluenceClient, output_dir: str, format_type: str):
        self.client = client
        self.output_dir = os.path.abspath(output_dir)
        self.format_type = format_type.lower()
        self.visited_pages: Set[int] = set()

    def export(self, page_id: int, recursive: bool = True) -> None:
        """
        Main entry point to export a page and optionally its children.
        """
        console.print(f"[bold blue]Starting export to {self.output_dir}[/bold blue]")
        console.print(f"Format: [bold]{self.format_type.upper()}[/bold], Recursive: [bold]{recursive}[/bold]")
        
        # We'll use rich Tree to show the hierarchy as we discover it
        # and progress bar to show downloading status
        root_tree = Tree(f"[bold]Confluence Root (ID: {page_id})[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task("Fetching page info...", total=None)
            self._process_page(
                page_id=page_id,
                current_dir=self.output_dir,
                tree_node=root_tree,
                recursive=recursive,
                progress=progress,
                task_id=task_id
            )
            progress.update(task_id, description="[bold green]Export completed![/bold green]", completed=1)
            
        console.print()
        console.print(root_tree)
        console.print(f"\n[bold green]Done! Files saved in: {self.output_dir}[/bold green]")

    def _process_page(
        self, 
        page_id: int, 
        current_dir: str, 
        tree_node: Tree, 
        recursive: bool,
        progress: Progress,
        task_id: int
    ) -> None:
        """
        Recursively processes a single page: fetches content, downlaods attachments, formats, and finds children.
        """
        # Prevent infinite loops in case of weird cross-linking disguised as parents
        if page_id in self.visited_pages:
            return
        self.visited_pages.add(page_id)
        
        try:
            progress.update(task_id, description=f"Fetching page {page_id}...")
            # 1. Fetch metadata and content
            page_data = self.client.get_page(page_id)
            title = page_data.get('title', f"Untitled_{page_id}")
            safe_title = sanitize_filename(title)
            
            # The node in the visual tree
            page_node = tree_node.add(f"[green]{title}[/green] (ID:{page_id})")
            
            # 2. Create the directory for this page.
            # We create a folder for each page to hold its content and attachments, 
            # and potentially sub-folders for its children.
            page_dir = os.path.join(current_dir, safe_title)
            os.makedirs(page_dir, exist_ok=True)
            
            # Determine content
            # Priority: body.view (rendered HTML, better for markdownify and displaying) 
            # over body.storage (raw confluence format)
            content_html = ""
            if 'body' in page_data:
                if 'view' in page_data['body']:
                    content_html = page_data['body']['view'].get('value', '')
                elif 'storage' in page_data['body']:
                    content_html = page_data['body']['storage'].get('value', '')
            
            # 3. Handle attachments
            attachments_dir = os.path.join(page_dir, 'attachments')
            progress.update(task_id, description=f"Checking attachments for '{title}'...")
            
            attachments = self.client.get_attachments(page_id)
            if attachments:
                os.makedirs(attachments_dir, exist_ok=True)
                att_node = page_node.add(f"[cyan]Attachments ({len(attachments)})[/cyan]")
                
                for att in attachments:
                    att_title = att.get('title')
                    if not att_title:
                        continue
                        
                    download_uri = None
                    # The Atlassian API returns download links in various structures depending on the schema
                    if '_links' in att and 'download' in att['_links']:
                        download_uri = att['_links']['download']
                        
                    if download_uri:
                        progress.update(task_id, description=f"Downloading attachment: {att_title}")
                        safe_att_name = sanitize_filename(att_title)
                        dest_path = os.path.join(attachments_dir, safe_att_name)
                        
                        success = self.client.download_attachment(download_uri, dest_path)
                        status_color = "green" if success else "red"
                        att_node.add(f"[{status_color}]{safe_att_name}[/{status_color}]")
            
            # 4. Save the content
            progress.update(task_id, description=f"Formatting and saving '{title}'...")
            if self.format_type == 'html':
                # Save as index.html inside the page directory
                save_path = os.path.join(page_dir, f"{safe_title}.html")
                save_as_html(title, content_html, save_path, attachments_dir if attachments else None)
            else:
                # Markdown
                save_path = os.path.join(page_dir, f"{safe_title}.md")
                save_as_markdown(title, content_html, save_path, attachments_dir if attachments else None)
                
            # 5. Process children recursively
            if recursive:
                progress.update(task_id, description=f"Looking for children of '{title}'...")
                children = self.client.get_children(page_id)
                if children:
                    for child in children:
                        child_id = int(child['id'])
                        self._process_page(
                            page_id=child_id,
                            current_dir=page_dir, # Children go inside the parent's directory
                            tree_node=page_node,
                            recursive=True,
                            progress=progress,
                            task_id=task_id
                        )
                        
        except Exception as e:
            tree_node.add(f"[red]Error processing {page_id}: {str(e)}[/red]")
            console.print(f"[bold red]Exception while processing page {page_id}: {e}[/bold red]")
