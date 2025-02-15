from __future__ import annotations
import threading
import urllib.parse
from typing import Any

import uvicorn
from fastapi import FastAPI

from .routes import setup_routes

class AuthServer:
    """
    FastAPI server handling Auth0 callbacks and authentication routes.
    """
    
    def __init__(self, auth_client: Any):
        """
        Initialize the authentication server.
        
        Args:
            auth_client: The parent AIAuth instance
        """
        self.auth_client = auth_client
        self.app = FastAPI()
        
        # Parse redirect URI for server config
        parsed_uri = urllib.parse.urlparse(auth_client.redirect_uri)
        self.host = parsed_uri.hostname
        self.port = parsed_uri.port
        
        # Setup routes with dependencies
        setup_routes(self.app, auth_client)
        self.start()

    def start(self) -> None:
        """Start the FastAPI server in a daemon thread."""
        server_thread = threading.Thread(
            target=uvicorn.run,
            args=(self.app,),
            kwargs={
                "host": self.host or "localhost",
                "port": self.port or "3000",
                "log_level": "info"
            },
            daemon=False
        )
        server_thread.start()
