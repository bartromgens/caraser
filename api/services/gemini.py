from dataclasses import dataclass

from google import genai
from google.genai import types

from django.conf import settings

from ..models import Transformation


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


_SHAPE_STYLE_LINE = {
    Transformation.ShapeStyle.ORGANIC: (
        "- Use curved, flowing, organic shapes for paths and planted beds; irregular, "
        "natural-looking layouts"
    ),
    Transformation.ShapeStyle.STRAIGHT: (
        "- Use clean geometric straight lines and rectangular forms for paths and planted "
        "beds; structured and orderly layout"
    ),
    Transformation.ShapeStyle.FORMAL: (
        "- Use a strictly symmetrical, axial layout with mirrored planting beds and a "
        "central path; classical formal garden arrangement with clipped hedges and "
        "matching tree rows on each side"
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
            "- Leave a single narrow shared lane so the occasional car can still pass "
            "through slowly (woonerf-style shared space)\n"
            "- Remove parking lanes, kerb markings, and road surface markings that "
            "emphasise car dominance\n"
            "- The street must read as a calmed, pedestrian-first shared space — not a "
            "traditional road"
        )
    return (
        "REMOVE (mandatory — zero exceptions):\n"
        "- Every single motor vehicle without exception: cars, trucks, vans, buses, "
        "motorcycles — whether parked, moving, partially visible, or in the background\n"
        "- Parking lanes, kerb markings, and road surface markings\n"
        "- There must be absolutely no vehicles of any kind visible anywhere in the final image"
    )


def _surface_rules(fietsstraat: bool) -> str:
    if not fietsstraat:
        return ""
    return (
        "STREET SURFACE:\n"
        "- The main drivable surface is a deep red asphalt 'fietsstraat' "
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

    return f"""Edit this street photo into a {headline}. Keep the same camera angle, lighting, and time of day throughout.

{_vehicle_rules(options.allow_cars)}

{_surface_rules(options.fietsstraat)}REPLACE ONLY THE SPACE CURRENTLY OCCUPIED BY CARS AND ROAD MARKINGS WITH:
{_GROUND_COVER_LINE[options.ground_cover]}
- Native trees and flowering shrubs in generous planted beds
- Pedestrian paths sized to the remaining space
- Children playing freely in the open space
- Adults sitting at café-style seating, talking and relaxing
- Cyclists passing gently through
- Birds perched in the trees, bees near the flowers

DESIGN LANGUAGE:
{_SHAPE_STYLE_LINE[options.shape_style]}

DO NOT CHANGE:
- Buildings, architectural facades, windows, doors, and signage
- The sky and upper atmosphere
- Existing lighting conditions and time of day
- Camera angle and perspective
- The total street width: the distance between the building faces (or kerbs) must stay exactly the same as in the input — do not widen or narrow the street corridor under any circumstances
- Existing footpaths, pavements, and sidewalks — their width and position must remain unchanged
- The spatial proportions of the scene; only the surface treatment and contents within the existing street boundary change

SEASON: Always depict as spring or summer — regardless of the season visible in the input photo.
- All trees must be in full leaf — no bare or leafless branches
- If the input shows winter or autumn, transform it into a warm, sunny day with lush green foliage

MOOD: Warm, lively, and human-scaled — like a thriving European pedestrian square on a sunny afternoon.

STYLE: Photorealistic architectural visualization, natural daylight, high detail, no HDR over-processing.

Output only the edited photo."""


def remove_cars(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    options: PromptOptions | None = None,
    prompt: str | None = None,
) -> bytes:
    if prompt is None:
        prompt = build_prompt(options or PromptOptions())
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
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
    raise ValueError("Gemini did not return an image in its response")
