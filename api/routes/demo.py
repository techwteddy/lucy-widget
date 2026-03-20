"""Demo UI route - serves the portfolio-quality demo page."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/demo", include_in_schema=False)
async def demo_ui() -> FileResponse:
    """Serve the portfolio-quality demo page.
    
    This route is hidden from the OpenAPI schema as it serves a static HTML file
    for portfolio/demo purposes, not an API endpoint.
    """
    demo_path = _STATIC_DIR / "demo.html"
    return FileResponse(demo_path, media_type="text/html")
