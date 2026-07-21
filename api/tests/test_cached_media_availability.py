"""Every media URL any cached fixture references must resolve to a
committed local file, and the media route must serve it. A presenter
following the demo plan reveals real bytes, not a 404, regardless of
venue connectivity."""

import json

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.config import get_artifacts_dir
from euro_chess_studio.main import app

MEDIA_PREFIX = "/artifacts/media/"


def _collect_urls(value) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            urls.extend(_collect_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_collect_urls(item))
    elif isinstance(value, str) and value.startswith(MEDIA_PREFIX):
        urls.append(value)
    return urls


def fixture_media_urls() -> list[str]:
    cached = get_artifacts_dir() / "cached"
    urls: set[str] = set()
    for path in sorted(cached.glob("*/*.json")):
        urls.update(_collect_urls(json.loads(path.read_text())))
    return sorted(urls)


def test_fixtures_reference_media_and_every_file_exists():
    urls = fixture_media_urls()
    # The reveal and adaptation fixtures must actually point at media;
    # an empty list means the fixtures regressed to metadata-only.
    assert len(urls) >= 10
    for url in urls:
        relative = url.removeprefix(MEDIA_PREFIX)
        path = get_artifacts_dir() / "cached" / "media" / relative
        assert path.is_file(), f"{url} referenced by a fixture but {path} is missing"
        assert path.stat().st_size > 0, f"{path} is empty"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def test_media_route_serves_every_referenced_file(client: TestClient):
    for url in fixture_media_urls():
        response = client.get(url)
        assert response.status_code == 200, url
        assert len(response.content) > 0, url


def test_media_files_cover_the_required_evidence_kinds():
    """The demo plan's promises, as file suffixes: a playable audio
    file with a waveform, a playable clip with poster and frame
    evidence, and an image pair at inspection size."""
    urls = fixture_media_urls()
    assert any(url.endswith(".wav") for url in urls)
    assert any(url.endswith("_waveform.png") for url in urls)
    assert any(url.endswith(".mp4") for url in urls)
    assert any(url.endswith("scene_poster.png") for url in urls)
    assert any(url.endswith("scene_frames.png") for url in urls)
    assert any(url.endswith("style_before.png") for url in urls)
    assert any(url.endswith("style_after.png") for url in urls)
