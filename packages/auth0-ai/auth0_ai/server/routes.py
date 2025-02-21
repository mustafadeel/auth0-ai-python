from __future__ import annotations
from typing import Any

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import jwt
from auth0.authentication import RevokeToken


def setup_routes(app: FastAPI, auth_client: Any) -> None:
    """Set up all routes for the authentication server."""

    @app.get("/auth/callback")
    async def manage_callback(request: Request, response: Response):
        """Parses and validates callback URL query parameters."""
        query_params = request.query_params
        required_keys = {"code", "state"}

        if query_params.get("error"):
            error_description = query_params.get(
                "error_description", "Unknown error occurred.")
            if query_params.get("state"):
                del auth_client.state_store[query_params.get("state")]
            raise HTTPException(status_code=400, detail=error_description)

        if not required_keys.issubset(query_params.keys()):
            raise HTTPException(
                status_code=400, detail="Missing required query parameters.")

        received_state = query_params["state"]

        # Validate state to prevent CSRF attacks
        if received_state not in auth_client.state_store:
            raise HTTPException(
                status_code=400, detail="Invalid or missing state parameter.")

        # Extract code value from query string
        received_code = query_params["code"]

        auth0_tokens = auth_client.token_manager.exchange_code_for_tokens(
            received_code)

        if auth0_tokens:
            cookie_session_data = await auth_client.session_manager.set_encrypted_session(auth0_tokens, state=received_state)

            user_id = auth_client.state_store[received_state].get(
                "user_id", "failed")
            return_to = auth_client.state_store[received_state].get(
                "return_to", None)
            auth_client.state_store[received_state] = {
                "user_id": user_id, "is_completed": True}

            if return_to:
                response = RedirectResponse(url=return_to, status_code=302)

            else:
                response.body = b'{"message": "login successful"}'
                response.status_code = 200

            response.set_cookie(
                key="sessionData",
                value=cookie_session_data,
                path="/auth",
                httponly=True,  # Prevent JavaScript access
                # secure=True,  # Send only over HTTPS
                samesite="Lax",  # Protect against CSRF
                # set expiry based on access token expiry
                max_age=auth0_tokens["expires_in"],
            )
            return response

        else:
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for tokens.")

    @app.get("/auth/login")
    async def manage_login(request: Request, response: Response,
                           return_to: str | None = None, scope: str | None = None, connection: str | None = None):
        """Handle login initiation."""
        # check cookie for existing session
        auth_cookie = request.cookies.get("sessionData")
        if auth_cookie:
            decoded_data = jwt.decode(
                auth_cookie, auth_client.secret_key, algorithms=["HS256"])
            # Session cookie exists, do something with it
            # ...
            return {"session": decoded_data}
        else:
            # No session cookie, redirect to Auth0
            _scope = scope or "openid profile email"
            _connection = connection or "Username-Password-Authentication"

            state = auth_client._generate_state(return_to=return_to)

            auth_url = auth_client.url_builder.get_authorize_url(
                state=state, connection=_connection, scope=_scope)

        return RedirectResponse(url=auth_url, status_code=302)

    @app.get("/auth/get_user")
    async def get_user(request: Request):
        """Reads the session cookie and extracts user info."""
        auth_cookie = request.cookies.get("sessionData")

        if not auth_cookie:
            raise HTTPException(
                status_code=401, detail="Missing session cookie.")

        try:
            # Decode the JWT stored in the session cookie
            decoded_data = jwt.decode(
                auth_cookie, auth_client.secret_key, algorithms=["HS256"])

            # Extract the user ID (sub) from the decoded JWT
            user_id = decoded_data.get("user").get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=400, detail="Invalid session cookie: Missing 'sub' claim.")

            return JSONResponse(content=decoded_data)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail="Session cookie has expired.")
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid session cookie.")

    @app.get("/auth/logout")
    async def manage_logout(request: Request, response: Response):
        """Reads the session cookie and extracts user info."""
        auth_cookie = request.cookies.get("sessionData")

        if not auth_cookie:
            raise HTTPException(
                status_code=401, detail="Missing session cookie.")

        try:
            # Decode the JWT stored in the session cookie
            decoded_data = jwt.decode(
                auth_cookie, auth_client.secret_key, algorithms=["HS256"])

            # Extract the user ID (sub) from the decoded JWT
            user_id = decoded_data.get('user').get('sub')

            if not user_id:
                raise HTTPException(
                    status_code=400, detail="Invalid session cookie: Missing 'sub' claim.")

            auth_client.get(url=f"https://{auth_client.domain}/v2/logout")
            rt = decoded_data.get("refresh_token", None)
            if rt:
                rt_manager = RevokeToken(
                    auth_client.domain, auth_client.client_id, auth_client.client_secret)
                rt_manager.revoke_refresh_token(token=rt)

            response.delete_cookie(key="sessionData", path="/auth")
            auth_client.session_manager._delete_stored_session(user_id)

            # MODIFY RESPONSE to ensure it returns properly
            response.body = b'{"message": "logout successful"}'
            response.status_code = 200
            response.media_type = "application/json"

            return response

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail="Session cookie has expired.")
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid session cookie.")
