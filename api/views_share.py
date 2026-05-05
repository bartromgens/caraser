import json
import re
import time
import urllib.error
import urllib.request
import uuid
from typing import Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .models import Transformation

_SHELL_CACHE: tuple[float, str] | None = None
_SHELL_CACHE_TTL = 60  # seconds

_META_RE = re.compile(
    r"<!-- ssr:meta:start -->.*?<!-- ssr:meta:end -->",
    re.DOTALL,
)


def _fetch_shell() -> str:
    global _SHELL_CACHE
    now = time.monotonic()
    if _SHELL_CACHE and now - _SHELL_CACHE[0] < _SHELL_CACHE_TTL:
        return _SHELL_CACHE[1]

    url = getattr(settings, "CLIENT_SHELL_URL", "http://client/index.html")
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            html = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        html = _read_shell_from_dist()

    _SHELL_CACHE = (now, html)
    return html


def _read_shell_from_dist() -> str:
    from pathlib import Path

    candidates = [
        Path(settings.BASE_DIR)
        / "client"
        / "dist"
        / "client"
        / "browser"
        / "index.html",
        Path(settings.BASE_DIR) / "client" / "dist" / "index.html",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "<html><head></head><body><app-root></app-root></body></html>"


def _build_meta_block(
    title: str,
    description: str,
    canonical: str,
    image_url: str,
    image_alt: str,
    json_ld: dict,
) -> str:
    json_ld_str = json.dumps(json_ld, ensure_ascii=False, indent=2)
    return f"""<!-- ssr:meta:start -->
    <title>{title}</title>
    <meta name="theme-color" content="#2e7d32" />
    <meta name="description" content="{description}" />
    <link rel="canonical" href="{canonical}" />

    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Caraser" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:image" content="{image_url}" />
    <meta property="og:image:secure_url" content="{image_url}" />
    <meta property="og:image:type" content="image/jpeg" />
    <meta property="og:image:alt" content="{image_alt}" />

    <!-- Twitter / X -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{description}" />
    <meta name="twitter:image" content="{image_url}" />

    <!-- Structured data -->
    <script type="application/ld+json">
      {json_ld_str}
    </script>
    <!-- ssr:meta:end -->"""


def _default_meta() -> tuple[str, str, str, str, str, dict]:
    title = "Caraser \u2013 See your street without cars"
    description = (
        "Upload a street photo and see what it looks like without cars. "
        "Caraser uses AI to replace cars with trees, benches, greenery and people."
    )
    canonical = "https://caraser.org/"
    image_url = "https://caraser.org/og-image.jpg"
    image_alt = "A street before and after removing cars \u2013 replaced with trees, benches and greenery"
    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Caraser",
        "url": "https://caraser.org/",
        "description": description,
    }
    return title, description, canonical, image_url, image_alt, json_ld


def _transformation_meta(
    t: Transformation, request: HttpRequest
) -> tuple[str, str, str, str, str, dict]:
    title = "Street without cars | Caraser"
    description = (
        "See what this street looks like without cars, reimagined by Caraser AI."
    )
    canonical = f"https://caraser.org/t/{t.id}"

    image_field: Optional[object] = None
    for field in (t.comparison_image, t.result_image):
        if field:
            image_field = field
            break

    if image_field:
        image_url = request.build_absolute_uri(image_field.url)
    else:
        image_url = "https://caraser.org/og-image.jpg"

    image_alt = "A street reimagined without cars by Caraser AI"

    json_ld = {
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "url": image_url,
        "name": title,
        "description": description,
        "isPartOf": {
            "@type": "WebSite",
            "name": "Caraser",
            "url": "https://caraser.org/",
        },
    }
    return title, description, canonical, image_url, image_alt, json_ld


def transformation_share(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    try:
        t = Transformation.objects.get(pk=pk)
        meta_args = _transformation_meta(t, request)
    except Transformation.DoesNotExist:
        meta_args = _default_meta()

    shell = _fetch_shell()
    meta_block = _build_meta_block(*meta_args)
    html = _META_RE.sub(meta_block, shell)

    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    return response
