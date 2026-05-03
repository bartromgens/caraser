import logging
import threading
import uuid
from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile

from .models import Transformation
from .services.comparison import build_comparison_image
from .services.gemini import PromptOptions, build_prompt, remove_cars

logger = logging.getLogger(__name__)

# NOTE: This uses a simple daemon thread for MVP. For production, replace with
# Celery + Redis or another task queue to survive server restarts and scale.


def _to_jpeg(image_bytes: bytes, quality: int = 85) -> bytes:
    buf = BytesIO()
    Image.open(BytesIO(image_bytes)).convert("RGB").save(buf, format="JPEG", quality=quality)
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

        prompt = build_prompt(_options_from(transformation))
        transformation.prompt = prompt
        transformation.save(update_fields=["prompt", "updated_at"])

        result_bytes = _to_jpeg(remove_cars(image_bytes, prompt=prompt))
        comparison_bytes = build_comparison_image(image_bytes, result_bytes)

        transformation.result_image.save(
            f"{transformation.pk}.jpg", ContentFile(result_bytes), save=False
        )
        transformation.comparison_image.save(
            f"{transformation.pk}-comparison.jpg", ContentFile(comparison_bytes), save=False
        )
        transformation.status = Transformation.Status.DONE
        transformation.save(update_fields=["result_image", "comparison_image", "status", "updated_at"])
    except Exception as exc:
        logger.exception("Transformation %s failed", transformation_id)
        transformation.status = Transformation.Status.FAILED
        transformation.error = str(exc)
        transformation.save(update_fields=["status", "error", "updated_at"])


def start_processing(transformation_id: uuid.UUID) -> None:
    t = threading.Thread(target=process_transformation, args=(transformation_id,), daemon=True)
    t.start()
