import os
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

from atlassian import Confluence
import requests
from requests.auth import HTTPBasicAuth


class ConfluenceClient:
    """Wrapper around atlassian-python-api Confluence client for Server authentication."""

    def __init__(self, url: str, username: str, password: str):
        """
        Initialize the Confluence client.
        
        Args:
            url: The base URL of the Confluence instance (e.g., http://172.16.2.225:8090)
            username: Confluence username
            password: Password for the user
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        
        # Initialize the underlying Atlassian API client
        self.client = Confluence(
            url=self.url,
            username=self.username,
            password=self.password,
            verify_ssl=False  # Allow self-signed certs which are common in internal servers
        )

    def get_page(self, page_id: int) -> Dict[str, Any]:
        """
        Retrieves page metadata and content (both storage and view formats).
        """
        return self.client.get_page_by_id(
            page_id=page_id,
            expand='body.storage,body.view,version,space'
        )

    def get_children(self, page_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves direct child pages for a given page ID.
        """
        # The underlying lib has a limit, default is usually 25, setting to 100
        # If a page has more than 100 children, we would need pagination,
        # but the simple API call `get_page_child_by_id` pagination is limited.
        children = []
        start = 0
        limit = 50
        while True:
            chunk = self.client.get_page_child_by_type(
                page_id=page_id,
                type='page',
                start=start,
                limit=limit
            )
            if not chunk or not isinstance(chunk, list):
                break
            
            children.extend(chunk)
            
            if len(chunk) < limit:
                break
            start += limit
            
        return children

    def get_attachments(self, page_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves a list of attachments for a given page ID.
        """
        attachments = []
        start = 0
        limit = 50
        while True:
            response = self.client.get_attachments_from_content(
                page_id=page_id,
                start=start,
                limit=limit
            )
            
            results = response.get('results', [])
            if not results:
                break
                
            attachments.extend(results)
            
            if len(results) < limit:
                break
            start += limit
            
        return attachments

    def download_attachment(self, download_uri: str, dest_path: str) -> bool:
        """
        Downloads an attachment and saves it to the destination path.
        
        Args:
            download_uri: The URI to download from (e.g., /download/attachments/...)
            dest_path: Local filesystem path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        # Construct full URL
        if download_uri.startswith('http'):
            full_url = download_uri
        else:
            full_url = f"{self.url}{download_uri if download_uri.startswith('/') else '/' + download_uri}"
            
        try:
            # We use direct requests here because the atlassian API's download logic
            # can sometimes be complex regarding streaming vs memory.
            response = requests.get(
                full_url, 
                auth=HTTPBasicAuth(self.username, self.password),
                stream=True,
                verify=False
            )
            response.raise_for_status()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
            
        except requests.exceptions.RequestException as e:
            from rich.console import Console
            Console().print(f"[red]Failed to download attachment {full_url}: {e}[/red]")
            return False
