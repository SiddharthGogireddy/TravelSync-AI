from pathlib import Path
import re

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"


def test_api_ts_exports_central_configuration():
    """Verify api.ts exports API and API_BASE with VITE_API_URL fallback."""
    api_file = FRONTEND_SRC / "services" / "api.ts"
    content = api_file.read_text(encoding="utf-8")
    assert "export const API =" in content
    assert "import.meta.env.VITE_API_URL" in content
    assert "export const API_BASE = API;" in content


def test_tripview_has_no_hardcoded_backend_urls():
    """Verify TripView.tsx contains no hardcoded backend IP or port URLs."""
    tripview_file = FRONTEND_SRC / "pages" / "TripView.tsx"
    content = tripview_file.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000" not in content
    assert "http://localhost:8000" not in content
    assert "getTrip" in content
    assert "updateTrip" in content


def test_expense_service_uses_central_api():
    """Verify expense.ts imports and reuses API from api.ts instead of hardcoded strings."""
    expense_file = FRONTEND_SRC / "services" / "expense.ts"
    content = expense_file.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000" not in content
    assert 'import { API } from "./api"' in content


def test_no_hardcoded_backend_urls_in_frontend_source():
    """Verify no .ts or .tsx files in frontend/src hardcode local backend addresses except api.ts default fallback."""
    hardcoded_pattern = re.compile(r"http://(?:127\.0\.0\.1|localhost):8000")
    files_with_hardcoded = []

    for file_path in FRONTEND_SRC.rglob("*.ts*"):
        if file_path.name == "api.ts":
            continue
        text = file_path.read_text(encoding="utf-8")
        if hardcoded_pattern.search(text):
            files_with_hardcoded.append(str(file_path.relative_to(FRONTEND_SRC)))

    assert files_with_hardcoded == [], f"Found hardcoded backend URLs in: {files_with_hardcoded}"
