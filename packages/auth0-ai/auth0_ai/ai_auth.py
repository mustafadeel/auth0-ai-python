from __future__ import annotations

from typing import Any

from auth0_python import AuthenticationBase, GetToken, AsyncAsymmetricSignatureVerifier, PushedAuthorizationRequests

import webbrowser
import urllib.parse

import os

import jwt  # PyJWT for signing cookies
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse

from typing import Any, Dict

import uvicorn
import secrets
import threading

import time
import json


from .session_storage import SessionStorage


class AIAuth(AuthenticationBase):

    def __init__(
            self,
            domain: str | None = None,
            client_id: str | None = None,
            client_secret: str | None = None,
            redirect_uri: str | None = None,
            *args, **kwargs):

        self.domain = domain or os.environ.get("AUTH0_DOMAIN")
        self.client_id = client_id or os.environ.get("AUTH0_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get(
            "AUTH0_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.environ.get(
            "AUTH0_REDIRECT_URI")

        """Initialize AIAuth and set up the middleware app with the callback route."""
        super().__init__(
            domain=self.domain,
            client_id=self.client_id,
            client_secret=self.client_secret,
            *args, **kwargs)  # Initialize parent class

        @property
        def domain(self):
            return self._domain

        @domain.setter
        def domain(self, val):
            if not val:
                raise ValueError(
                    "domain cannot be empty. you can also set AUTH0_DOMAIN value in .env file")
            self._domain = val

        @property
        def client_id(self):
            return self._client_id

        @client_id.setter
        def client_id(self, val):
            if not val:
                raise ValueError(
                    "client_id cannot be empty. you can also AUTH0_CLIENT_ID value in .env file")
            self._client_id = val

        @property
        def client_secret(self):
            return self._client_secret

        @client_secret.setter
        def client_secret(self, val):
            if not val:
                raise ValueError(
                    "client_secret cannot be empty. you can also AUTH0_CLIENT_SECRET value in .env file")
            self._client_secret = val

        @property
        def redirect_uri(self):
            return self._redirect_uri

        @redirect_uri.setter
        def redirect_uri(self, val):
            if not val:
                raise ValueError(
                    "redirect_uri cannot be empty. you can also AUTH0_REDIRECT_URI value in .env file")
            self._redirect_uri = val

        # Initialize token verifier
        jwk_url = f"https://{self.domain}/.well-known/jwks.json"
        self.token_verifier = AsyncAsymmetricSignatureVerifier(
            jwks_url=jwk_url)

        # Initialize FastAPI app
        self.app = FastAPI()
        # Temporary store for state values
        self.state_store: Dict[str, Dict[bool, str]] = {}
        # or secrets.token_urlsafe(32)  # Secure random secret key
        self.secret_key = os.environ.get("AUTH0_SECRET_KEY")

        # Register the callback route
        @self.app.get("/auth/callback")
        async def manage_callback(request: Request, response: Response):
            """Parses and validates callback URL query parameters."""
            query_params = request.query_params
            required_keys = {"code", "state"}

            if query_params.get("error"):
                error_description = query_params.get(
                    "error_description", "Unknown error occurred.")
                if query_params.get("state"):
                    del self.state_store[query_params.get("state")]
                raise HTTPException(status_code=400, detail=error_description)

            if not required_keys.issubset(query_params.keys()):
                raise HTTPException(
                    status_code=400, detail="Missing required query parameters.")

            received_state = query_params["state"]

            # Validate state to prevent CSRF attacks
            if received_state not in self.state_store:
                raise HTTPException(
                    status_code=400, detail="Invalid or missing state parameter.")

            # Extract code value from query string
            received_code = query_params["code"]

            auth0_tokens = self._exchange_code_for_tokens(received_code)

            if auth0_tokens:

                cookie_data = await self._set_encrypted_session(auth0_tokens, state=received_state)

                response.set_cookie(
                    key="session",
                    value=cookie_data,
                    httponly=True,  # Prevent JavaScript access
                    # secure=True,  # Send only over HTTPS
                    samesite="Lax",  # Protect against CSRF
                    # set expiry based on access token expiry
                    max_age=auth0_tokens["expires_in"],
                )

                # Remove state after validation (one-time use)
                # del self.state_store[received_state]

                return {"message": "successul. you can now close this window"}

        @self.app.get("/auth/get_user")
        async def get_user(request: Request):
            """Reads the session cookie and extracts user info."""
            auth_cookie = request.cookies.get("session")

            if not auth_cookie:
                raise HTTPException(
                    status_code=401, detail="Missing session cookie.")

            try:
                # Decode the JWT stored in the session cookie
                decoded_data = jwt.decode(
                    auth_cookie, self.secret_key, algorithms=["HS256"])

                # Extract the user ID (sub) from the decoded JWT
                user_id = decoded_data["user_id"]

                if not user_id:
                    raise HTTPException(
                        status_code=400, detail="Invalid session cookie: Missing 'sub' claim.")

                return (JSONResponse(content=decoded_data))

            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=401, detail="Session cookie has expired.")
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=401, detail="Invalid session cookie.")

        # Start middleware server in a separate thread
        self.host = urllib.parse.urlparse(self.redirect_uri).hostname
        self.port = urllib.parse.urlparse(self.redirect_uri).port
        self._start_server()

    def _start_server(self):
        """Runs FastAPI as the middleware inside a separate thread."""
        server_thread = threading.Thread(
            target=uvicorn.run,
            args=(self.app,),
            kwargs={"host": self.host, "port": self.port, "log_level": "info"},
            daemon=True  # Daemon mode so it exits when the main thread exits
        )
        server_thread.start()

    def _generate_state(self) -> str:
        """Generate a secure random state and store it for validation."""
        state = secrets.token_urlsafe(16)  # Generate a random state
        self.state_store[state] = True  # Store it temporarily
        return state

    def _get_token_set(self, token_data: str, existing_refresh_token: str | None = None) -> dict:

        token_data = {
            "access_token": token_data.get("access_token"), "expires_at": {"epoch": int(time.time())+token_data["expires_in"]},
            "refresh_token": token_data.get("refresh_token", existing_refresh_token),
            "id_token": token_data.get("id_token"),
            "scope": token_data.get("scope"),
        }
        return token_data

    def _get_linked_details(self, token_data: dict, existing_linked_connections: list[str] | None = None) -> list[str]:
        """Extracts unique link_with values from authorization_details if type is 'account_linking'
        and appends them to existing_linked_connections, avoiding duplicates.
        """
        authz_details = token_data.get("authorization_details", [])
        # Use a set to enforce uniqueness
        linked_connections = set(existing_linked_connections or [])

        for item in authz_details:
            if item.get("type") == "account_linking":
                link_with = item.get("linkParams", {}).get("link_with")
                if link_with:  # Ensure link_with is not None
                    # Add to set to avoid duplicates
                    linked_connections.add(link_with)

        # Convert back to a list before returning
        return list(linked_connections)

    async def _set_encrypted_session(self, token_data, state: str | None = None) -> str:
        session_store = SessionStorage()
        try:
            decoded_id_token = await self.token_verifier.verify_signature(token_data["id_token"])
            user_id = decoded_id_token.get("sub")  # Primary Key
            if not user_id:
                raise HTTPException(
                    status_code=400, detail="ID token missing 'sub' claim.")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid ID token: {str(e)}")

        existing_encrypted_session = session_store._get_stored_session(user_id)
        existing_linked_connections = {}
        existing_refresh_token = {}

        if existing_encrypted_session:
            # found existing session, check if there is a refresh token to keep
            existing_session = self._get_encrypted_session(user_id)
            existing_refresh_token = existing_session.get(
                "tokens").get("refresh_token", None)
            existing_linked_connections = existing_session.get(
                "linked_connections")

        session_data = {}
        session_data = {"user_id": user_id,
                        "tokens": self._get_token_set(token_data, existing_refresh_token),
                        "linked_connections": self._get_linked_details(token_data, existing_linked_connections)
                        }

        encrypted_session_data = jwt.encode(
            session_data, self.secret_key, algorithm="HS256")

        # Stored in memory & auto-persisted
        session_store._set_stored_session(
            user_id=user_id, encrypted_session_data=encrypted_session_data)

        self.state_store[state] = {"user_id": user_id}

        # print("Session created/updated for:",user_id)
        return encrypted_session_data

    def _get_encrypted_session(self, user_id):
        session_store = SessionStorage()
        encrypted_session = session_store._get_stored_session(user_id)

        if not encrypted_session:
            return {"not found"}

        try:
            # Decode the JWT stored in the session cookie
            decoded_data = jwt.decode(
                encrypted_session, self.secret_key, algorithms=["HS256"])

            # Extract the user ID (sub) from the decoded JWT
            user_id = decoded_data["user_id"]

            token_expiry = decoded_data.get("tokens", {}).get(
                "expires_at", {}).get("epoch")

            if token_expiry > int(time.time()):
                return decoded_data
            else:
                refresh_token = decoded_data.get(
                    "tokens", {}).get("refresh_token")
                if refresh_token:
                    self._update_encrypted_session(user_id, refresh_token)
                else:
                    session_store._delete_stored_session(user_id)
                    return {"session expired"}

        except jwt.ExpiredSignatureError:
            return {"Session cookie has expired."}
        except jwt.InvalidTokenError:
            return {"Invalid session."}

    def _update_encrypted_session(self, user_id, refresh_token):
        token_manager = GetToken()
        updated_tokens = token_manager.refresh_token(
            refresh_token=refresh_token)

        if updated_tokens:
            self._set_encrypted_session(updated_tokens)

    def get_authorize_url(
        self,
        state: str,
        connection: str | None = None,
        scope: str | None = None,
        additional_scopes: str | None = None,
        **kwargs,
    ) -> str:

        base_url = (
            f"https://{self.domain}/authorize?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"grant_type=authorization_code&"
            f"state={state}&"
        )

        if connection is not None:
            base_url += f"connection={connection}&"

        if scope is not None:
            base_url += f"scope={scope}&"

        if additional_scopes is not None:
            base_url += f"connection_scope={additional_scopes}&"

        # Add any additional custom arguments passed via kwargs
        custom_args = "&".join(
            [f"{key}={value}" for key, value in kwargs.items()])
        if custom_args:
            base_url += custom_args

        return base_url

    def get_authorize_par_url(
        self,
        state: str,
        request_uri: str,
    ) -> str:

        base_url = (
            f"https://{self.domain}/authorize?"
            f"client_id={self.client_id}&"
            f"state={state}&"
            f"request_uri={request_uri}"
        )

        return base_url

    def _exchange_code_for_tokens(
        self,
        code: str,
    ) -> dict[str, Any]:

        get_token = GetToken(self.domain, self.client_id, self.client_secret)

        token_info = get_token.authorization_code(
            code=code,
            redirect_uri=self.redirect_uri,
            grant_type="authorization_code"
        )

        return token_info

    def get_upstream_token(
        self,
        connection,
        refresh_token: str,
        additional_scopes: str | None = None,
    ) -> dict[str, Any]:

        fcat = GetToken(self.domain, self.client_id, self.client_secret)

        x = fcat.federated_connection_access_token(
            subject_token_type="urn:ietf:params:oauth:token-type:refresh_token",
            subject_token=refresh_token,
            requested_token_type="http://auth0.com/oauth/token-type/federated-connection-access-token",
            connection=connection,
            grant_type="urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token"
        )

        return (x)

    def get_session_details(self, user_id: str) -> dict[str, Any]:
        session_store = SessionStorage()
        if user_id in session_store._get_stored_sessions():
            return (self._get_encrypted_session(user_id))
        else:
            return {"user_id not found in session store"}

    async def login(self, connection: str | None = None, scope: str | None = None, **kwargs) -> str:

        if scope is None:
            scope = "openid profile email"

        state = self._generate_state()

        class LoginState:
            def __init__(self, state_store, state):
                self.state_store = state_store
                self.state = state

            def is_completed(self) -> bool:
                if self.state_store.get(self.state, False) == True:
                    return False
                else:
                    return True

            def get_user(self) -> str:
                return self.state_store.get(self.state, "login failed!")

        login_state = LoginState(self.state_store, state)

        auth_url = self.get_authorize_url(
            state=state, connection=connection, scope=scope, **kwargs)

        # this initiates the login flow, and if successful the session is created
        try:
            webbrowser.open(auth_url)
        except webbrowser.Error:
            print("Please navigate here: {auth_url}")

        # check of compleition of login flow
        while not login_state.is_completed():
            # not sure if this needed, but can save some unecessary polling time
            time.sleep(0.05)
        user_id = login_state.get_user()

        if user_id == "login failed!":
            successul_login = False
        else:
            successul_login = True

        login_response = {
            "is_successful": successul_login,
            "user_id": user_id,
        }
        return login_response

    async def link(self, primary_user_id: str, connection: str, scope: str | None = None, **kwargs) -> str:

        state = self._generate_state()

        class LinkState:
            def __init__(self, state_store, state):
                self.state_store = state_store
                self.state = state

            def is_completed(self) -> bool:
                if self.state_store.get(self.state, False) == True:
                    return False
                else:
                    return True

            def get_user(self) -> str:
                return self.state_store.get(self.state, "login failed!").get("user_id")

        par_client = PushedAuthorizationRequests(
            self.domain, self.client_id, self.client_secret)

        link_state = LinkState(self.state_store, state)

        y = par_client.pushed_authorization_request(
            response_type="code",
            redirect_uri=self.redirect_uri,
            audience="https://accounts.auth101.dev/me/",
            connection=connection,
            state=state,
            authorization_details=json.dumps([
                {"type": "account_linking", "linkParams":
                 {"primary_user_id": primary_user_id,
                  "link_with": connection, }
                 }
            ]),
            scope=scope,
            prompt="login",
        )

        request_uri = y.get('request_uri')

        if request_uri:
            auth_url = self.get_authorize_par_url(
                state=state, request_uri=request_uri)

            # this initiates the login flow for the connection to link
            try:
                webbrowser.open(auth_url)
            except webbrowser.Error:
                print("Please navigate here: {auth_url}")

            # check of compleition of login flow
            while not link_state.is_completed():
                # not sure if this needed, but can save some unecessary polling time
                time.sleep(0.05)
            user_id = link_state.get_user()

            if user_id == "login failed!":
                successul_login = False
            else:
                successul_login = True

            link_response = {
                "is_successful": successul_login,
                "user_id": user_id,
            }
            return link_response
        else:
            return ("linking error")
