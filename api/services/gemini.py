from google import genai
from google.genai import types

from django.conf import settings

PROMPT = """Edit this street photo into a car-free public space. Keep the same camera angle, lighting, and time of day throughout.

REMOVE (this is mandatory — zero exceptions):
- Every single motor vehicle without exception: cars, trucks, vans, buses, motorcycles — whether parked, moving, partially visible, or in the background
- Parking lanes, kerb markings, and road surface markings
- There must be absolutely no vehicles of any kind visible anywhere in the final image

REPLACE THE FREED SPACE WITH:
- Pedestrian paths with a modest amount of natural stone paving — not wall-to-wall, leave room for green
- Generous patches of grass and ground cover between paths
- Native trees and flowering shrubs in generous planted beds
- Children playing freely in the open space
- Adults sitting at café-style seating, talking and relaxing
- Cyclists passing gently through
- Birds perched in the trees, bees near the flowers

DO NOT CHANGE:
- Buildings, architectural facades, windows, doors, and signage
- The sky and upper atmosphere
- Existing lighting conditions and time of day
- Camera angle and perspective

SEASON: Always depict as spring or summer — regardless of the season visible in the input photo.
- All trees must be in full leaf — no bare or leafless branches
- If the input shows winter or autumn, transform it into a warm, sunny day with lush green foliage

MOOD: Warm, lively, and human-scaled — like a thriving European pedestrian square on a sunny afternoon.

STYLE: Photorealistic architectural visualization, natural daylight, high detail, no HDR over-processing.

Output only the edited photo."""


def remove_cars(image_bytes: bytes, mime_type: str = "image/jpeg") -> bytes:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data
    raise ValueError("Gemini did not return an image in its response")
