import logging
from dataclasses import dataclass

from google import genai
from google.genai import types

from django.conf import settings

from ..models import Transformation

logger = logging.getLogger(__name__)


class GeminiNoImageError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptOptions:
    allow_cars: bool = False
    fietsstraat: bool = False
    ground_cover: str = Transformation.GroundCover.MIXED
    shape_style: str = Transformation.ShapeStyle.ORGANIC


_GROUND_COVER_LINE = {
    Transformation.GroundCover.MIXED: (
        "- A balanced mix of natural stone paving, generous grass patches, and flowering "
        "planted beds — no single material dominates"
    ),
    Transformation.GroundCover.STONES: (
        "- Predominantly natural stone paving (cobblestone or setts) as the main ground "
        "surface, with small planted accents and a few low shrubs"
    ),
    Transformation.GroundCover.GRASS: (
        "- Predominantly grass and low ground cover across most of the reclaimed ground, "
        "with only narrow stone paths where needed for walking"
    ),
    Transformation.GroundCover.FLOWERS: (
        "- Predominantly flowering shrubs, wildflower beds, and ornamental planting "
        "dominating the ground, with only minimal paving"
    ),
}


_VEGETATION_LINE = {
    Transformation.GroundCover.MIXED: (
        "- Native trees and flowering shrubs rising above the ground cover"
    ),
    Transformation.GroundCover.STONES: (
        "- Trees and low green accents planted between the paving stones"
    ),
    Transformation.GroundCover.GRASS: (
        "- Scattered shade trees rising from the open grass — no flowering shrubs or planted beds"
    ),
    Transformation.GroundCover.FLOWERS: (
        "- Native trees providing canopy above the flowering beds and wildflower plantings"
    ),
}


_SHAPE_STYLE_LINE = {
    Transformation.ShapeStyle.MIXED: (
        "- Combine curved, flowing organic shapes with clean geometric straight "
        "lines: e.g. softly curving planted beds beside rectangular paving panels "
        "or linear seating edges; balanced, varied, neither fully formal nor fully wild"
    ),
    Transformation.ShapeStyle.ORGANIC: (
        "- Use curved, flowing, organic shapes for paths and planted beds; irregular, "
        "natural-looking layouts"
    ),
    Transformation.ShapeStyle.STRAIGHT: (
        "- Use clean geometric straight lines and rectangular forms for paths and planted "
        "beds; structured and orderly layout, but do follow direction of existing street."
    ),
    Transformation.ShapeStyle.WILDERNESS: (
        "- Use dense, unstructured naturalistic planting with no defined hard edges; "
        "a rewilded meadow aesthetic with tall grasses, wildflowers, and self-seeding "
        "plants — minimal paving, maximum biodiversity"
    ),
}


def _vehicle_rules(allow_cars: bool) -> str:
    if allow_cars:
        return (
            "VEHICLES:\n"
            "- Remove every parked motor vehicle without exception\n"
            "- Narrow the drivable carriageway to one single minimal lane — only wide "
            "enough for one slow car to pass (roughly the width of one car); do NOT "
            "show a full-width or two-lane road\n"
            "- Reclaim all freed-up road surface (former parking lanes and extra "
            "carriageway width) and convert it into planted beds, trees, and pedestrian "
            "space as described in the REPLACE THE SPACE WITH section\n"
            "- Remove all parking lanes, kerb markings, and road surface markings that "
            "emphasise car dominance\n"
            "- The street must read as a calmed, pedestrian-first shared space — not a "
            "traditional road"
        )
    return (
        "REMOVE (mandatory — zero exceptions):\n"
        "- Remove every single motor vehicle\n"
        "- Remove parking lanes, kerb markings, and road surface markings\n"
        "- There must be absolutely no vehicles of any kind visible\n"
        "- Remove traffic signs"
    )


def _surface_rules(fietsstraat: bool) -> str:
    if not fietsstraat:
        return ""
    return (
        "STREET SURFACE:\n"
        "- The main drivable surface is a deep natural red asphalt 'fietsstraat' "
        "(Dutch bicycle street), clearly reading as red/terracotta asphalt\n"
        "- Bicycles are the priority users of this red surface; any cars are guests at "
        "walking pace\n"
        "- Planted beds and ground cover frame the red asphalt rather than covering it\n"
    )


def build_prompt(options: PromptOptions) -> str:
    headline = (
        "calmed, shared public space where cars are guests"
        if options.allow_cars
        else "car-free public space"
    )

    return f"""Edit this street photo into a {headline}. Keep the same camera angle.

{_vehicle_rules(options.allow_cars)}

{_surface_rules(options.fietsstraat)}REPLACE THE SPACE WITH:
{_GROUND_COVER_LINE[options.ground_cover]}
{_VEGETATION_LINE[options.ground_cover]}
- Pedestrian paths sized to the remaining space
- Children playing freely in the open space
- Adults sitting at café-style seating, talking and relaxing
- Benches integrated along the street, with people sitting on them
- Cyclists passing gently through
- Birds in the sky{", butterflies near the flowers" if options.ground_cover in (Transformation.GroundCover.MIXED, Transformation.GroundCover.FLOWERS) else ""}

DESIGN LANGUAGE:
{_SHAPE_STYLE_LINE[options.shape_style]}

KEEP THE FOLLOWING AS IS:
- Buildings, architectural facades, windows, doors, and signage
- Camera angle and perspective
- The total street corridor width from building facade to building facade — do not widen or narrow the space between buildings (only the drivable carriageway within it may be narrowed when cars are allowed)
- The spatial proportions of the scene;

SEASON: Always depict as spring or summer.
- All trees must be in full leaf
- Transform it into a warm, sunny day with lush green foliage
- Change the time of day to a sunny afternoon with blue sky

MOOD: Warm, lively, and human-scaled — like a thriving European pedestrian square on a sunny afternoon.

STYLE: Photorealistic, natural daylight, high detail, no HDR over-processing.
"""


_HTTP_OPTIONS = types.HttpOptions(
    retry_options=types.HttpRetryOptions(
        attempts=5,
        initial_delay=1.0,
        max_delay=60.0,
        exp_base=2,
        jitter=1,
        http_status_codes=(408, 429, 500, 502, 503, 504),
    ),
)

_NO_IMAGE_MAX_ATTEMPTS = 3


def _diagnose_no_image(response) -> str:
    candidate = response.candidates[0] if response.candidates else None
    finish_reason = getattr(candidate, "finish_reason", None)

    blocked_ratings = []
    for r in getattr(candidate, "safety_ratings", None) or []:
        if getattr(r, "blocked", False):
            blocked_ratings.append(str(getattr(r, "category", r)))

    pf = getattr(response, "prompt_feedback", None)
    block_reason = getattr(pf, "block_reason", None)
    block_reason_message = getattr(pf, "block_reason_message", None)

    text_parts = [
        p.text
        for p in (getattr(candidate, "content", None) and candidate.content.parts or [])
        if getattr(p, "text", None)
    ]
    text_snippet = " ".join(text_parts)[:500] if text_parts else None

    parts = [f"finish_reason={finish_reason}"]
    if blocked_ratings:
        parts.append(f"blocked_categories={blocked_ratings}")
    parts.append(f"block_reason={block_reason}")
    if block_reason_message:
        parts.append(f"block_reason_message={block_reason_message!r}")
    if text_snippet:
        parts.append(f"text={text_snippet!r}")
    return ", ".join(parts)


def remove_cars(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    options: PromptOptions | None = None,
    prompt: str | None = None,
) -> bytes:
    if prompt is None:
        prompt = build_prompt(options or PromptOptions())
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=_HTTP_OPTIONS,
    )
    diagnostic = ""
    for attempt in range(1, _NO_IMAGE_MAX_ATTEMPTS + 1):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(image_size=settings.GEMINI_IMAGE_SIZE),
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        diagnostic = _diagnose_no_image(response)
        logger.warning(
            "Gemini returned no image (attempt %d/%d): %s",
            attempt,
            _NO_IMAGE_MAX_ATTEMPTS,
            diagnostic,
        )
    raise GeminiNoImageError(
        f"Gemini returned no image after {_NO_IMAGE_MAX_ATTEMPTS} attempts ({diagnostic})"
    )
