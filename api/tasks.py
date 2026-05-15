import logging
import threading
import uuid
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Transformation
from .services.comparison import build_comparison_image
from .services.designer import build_designer_prompt
from .services.gemini import PromptOptions, build_prompt, generate_image, remove_cars

logger = logging.getLogger(__name__)

# NOTE: This uses a simple daemon thread for MVP. For production, replace with
# Celery + Redis or another task queue to survive server restarts and scale.


THUMBNAIL_WIDTH = 600


def _to_jpeg(image_bytes: bytes, quality: int = 85) -> bytes:
    buf = BytesIO()
    Image.open(BytesIO(image_bytes)).convert("RGB").save(
        buf, format="JPEG", quality=quality
    )
    return buf.getvalue()


def _composite_annotation(original_bytes: bytes, overlay_bytes: bytes) -> bytes:
    base = Image.open(BytesIO(original_bytes)).convert("RGBA")
    overlay = Image.open(BytesIO(overlay_bytes)).convert("RGBA")

    if overlay.size != base.size:
        overlay = overlay.resize(base.size, Image.NEAREST)

    composite = Image.alpha_composite(base, overlay)
    buf = BytesIO()
    composite.convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.getvalue()


def _to_thumbnail(
    image_bytes: bytes, width: int = THUMBNAIL_WIDTH, quality: int = 80
) -> bytes:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    if img.width > width:
        height = int(img.height * width / img.width)
        img = img.resize((width, height), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _options_from(transformation: Transformation) -> PromptOptions:
    return PromptOptions(
        allow_cars=transformation.allow_cars,
        fietsstraat=transformation.fietsstraat,
        ground_cover=transformation.ground_cover,
        shape_style=transformation.shape_style,
    )


def process_transformation(transformation_id: uuid.UUID) -> None:
    try:
        transformation = Transformation.objects.get(pk=transformation_id)
    except Transformation.DoesNotExist:
        logger.error("Transformation %s not found", transformation_id)
        return

    transformation.status = Transformation.Status.PROCESSING
    transformation.save(update_fields=["status", "updated_at"])

    try:
        image_bytes = transformation.original_image.read()

        if transformation.mode == Transformation.Mode.DESIGNER:
            overlay_bytes = transformation.overlay_image.read()
            annotated_bytes = _composite_annotation(image_bytes, overlay_bytes)
            transformation.annotated_image.save(
                f"{transformation.pk}-annotated.jpg",
                ContentFile(_to_jpeg(annotated_bytes)),
                save=False,
            )
            prompt = build_designer_prompt()
            transformation.prompt = prompt
            transformation.save(
                update_fields=["annotated_image", "prompt", "updated_at"]
            )
            result_bytes = _to_jpeg(
                generate_image(
                    [
                        (image_bytes, "image/jpeg"),
                        (annotated_bytes, "image/jpeg"),
                    ],
                    prompt,
                    model=settings.GEMINI_DESIGNER_MODEL,
                    image_labels=[
                        "IMAGE 1 — original unmodified street photo (pixel-perfect source):",
                        "IMAGE 2 — same photo with semi-transparent color zone annotations painted on top (zone map only, not a photo to edit):",
                    ],
                )
            )
        else:
            prompt = build_prompt(_options_from(transformation))
            transformation.prompt = prompt
            transformation.save(update_fields=["prompt", "updated_at"])
            result_bytes = _to_jpeg(remove_cars(image_bytes, prompt=prompt))
        thumbnail_bytes = _to_thumbnail(result_bytes)
        comparison_bytes = build_comparison_image(image_bytes, result_bytes)

        transformation.result_image.save(
            f"{transformation.pk}.jpg", ContentFile(result_bytes), save=False
        )
        transformation.thumbnail_image.save(
            f"{transformation.pk}-thumb.jpg", ContentFile(thumbnail_bytes), save=False
        )
        transformation.comparison_image.save(
            f"{transformation.pk}-comparison.jpg",
            ContentFile(comparison_bytes),
            save=False,
        )
        transformation.status = Transformation.Status.DONE
        transformation.save(
            update_fields=[
                "result_image",
                "thumbnail_image",
                "comparison_image",
                "status",
                "updated_at",
            ]
        )
    except Exception as exc:
        logger.exception("Transformation %s failed", transformation_id)
        transformation.status = Transformation.Status.FAILED
        transformation.error = str(exc)
        transformation.save(update_fields=["status", "error", "updated_at"])


def start_processing(transformation_id: uuid.UUID) -> None:
    t = threading.Thread(
        target=process_transformation, args=(transformation_id,), daemon=True
    )
    t.start()
