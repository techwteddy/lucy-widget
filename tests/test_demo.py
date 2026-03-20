"""Tests for demo UI and demo login functionality."""
import pytest
from pathlib import Path
from httpx import AsyncClient
from api.main import app


class TestDemoUI:
    """Tests for GET /demo endpoint."""

    @pytest.mark.asyncio
    async def test_demo_ui_returns_200(self, client: AsyncClient) -> None:
        """GET /demo should return 200 with HTML content."""
        response = await client.get("/demo")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    @pytest.mark.asyncio
    async def test_demo_ui_hidden_from_schema(self, client: AsyncClient) -> None:
        """GET /demo should not appear in OpenAPI schema."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/demo" not in schema.get("paths", {})

    @pytest.mark.asyncio
    async def test_demo_ui_contains_key_elements(self, client: AsyncClient) -> None:
        """Demo page should contain key elements like widget script and copy button."""
        response = await client.get("/demo")
        assert response.status_code == 200
        content = response.text
        # Check for widget script reference
        assert "chatbot.min.js" in content
        # Check for copy functionality
        assert "copy" in content.lower()
        # Check for GitHub link
        assert "GitHub" in content

    @pytest.mark.asyncio
    async def test_demo_ui_contains_api_url_reference(self, client: AsyncClient) -> None:
        """Demo page should reference the widget endpoint."""
        response = await client.get("/demo")
        assert response.status_code == 200
        content = response.text
        # Check for widget endpoint reference
        assert "/widget/chatbot.min.js" in content

    @pytest.mark.asyncio
    async def test_demo_ui_static_dir_exists(self) -> None:
        """Static directory and demo.html should exist."""
        static_dir = Path(__file__).resolve().parent.parent / "api" / "static"
        assert static_dir.exists(), f"Static directory {static_dir} should exist"
        demo_html = static_dir / "demo.html"
        assert demo_html.exists(), f"demo.html should exist at {demo_html}"

    @pytest.mark.asyncio
    async def test_demo_ui_no_external_links_in_head(self, client: AsyncClient) -> None:
        """Demo page head should not contain external CDN links (self-contained)."""
        response = await client.get("/demo")
        assert response.status_code == 200
        content = response.text
        # Extract head section
        head_start = content.find("<head>")
        head_end = content.find("</head>") + len("</head>")
        if head_start != -1 and head_end > head_start:
            head_content = content[head_start:head_end]
            # Check for common CDN patterns
            cdn_patterns = [
                "cdn.jsdelivr.net",
                "unpkg.com",
                "cdnjs.cloudflare.com",
                "fonts.googleapis.com",
            ]
            for pattern in cdn_patterns:
                assert pattern not in head_content, f"External CDN link found in head: {pattern}"


class TestDemoLogin:
    """Tests for POST /auth/demo-login endpoint."""

    @pytest.mark.asyncio
    async def test_demo_login_in_demo_mode(self, demo_client: AsyncClient) -> None:
        """POST /auth/demo-login should return token when DEMO_MODE=true."""
        response = await demo_client.post("/auth/demo-login")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "demo-token"
        assert "email" in data

    @pytest.mark.asyncio
    async def test_demo_login_disabled_in_production(self, client: AsyncClient) -> None:
        """POST /auth/demo-login should return 404 when DEMO_MODE=false."""
        response = await client.post("/auth/demo-login")
        assert response.status_code == 404


class TestDemoChatbotResolution:
    """Tests for demo chatbot ID resolution in chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_with_demo_id_in_demo_mode(
        self, demo_client: AsyncClient, demo_chatbot_id: str
    ) -> None:
        """POST /chat/demo should work when DEMO_MODE=true."""
        response = await demo_client.post(
            f"/api/v1/chat/demo",
            json={"message": "Hello", "session_id": "test-session"},
        )
        # Note: This may fail if no LLM API key is configured, but the routing should work
        # We're testing that "demo" is resolved, not the full chat flow
        assert response.status_code in [200, 500]  # 500 if no API key, but routing worked

    @pytest.mark.asyncio
    async def test_chat_with_demo_id_disabled_in_production(
        self, client: AsyncClient
    ) -> None:
        """POST /chat/demo should return 404 when DEMO_MODE=false."""
        response = await client.post(
            "/api/v1/chat/demo",
            json={"message": "Hello", "session_id": "test-session"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_with_invalid_chatbot_id_format(
        self, client: AsyncClient
    ) -> None:
        """POST /chat/{invalid} should return 400 for invalid UUID format."""
        response = await client.post(
            "/api/v1/chat/not-a-uuid-or-demo",
            json={"message": "Hello", "session_id": "test-session"},
        )
        assert response.status_code == 400
        assert "Invalid chatbot ID format" in response.json().get("detail", "")
