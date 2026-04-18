import io
import logging
import threading
import uuid

from django.core.files.base import ContentFile

from .models import Transformation
from .services.gemini import remove_cars

logger = logging.getLogger(__name__)

# NOTE: This uses a simple daemon thread for MVP. For production, replace with
# Celery + Redis or another task queue to survive server restarts and scale.


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
        name = transformation.original_image.name
        mime_type = "image/png" if name.lower().endswith(".png") else "image/jpeg"

        result_bytes = remove_cars(image_bytes, mime_type)

        filename = f"{transformation.pk}.png"
        transformation.result_image.save(filename, ContentFile(result_bytes), save=False)
        transformation.status = Transformation.Status.DONE
        transformation.save(update_fields=["result_image", "status", "updated_at"])
    except Exception as exc:
        logger.exception("Transformation %s failed", transformation_id)
        transformation.status = Transformation.Status.FAILED
        transformation.error = str(exc)
        transformation.save(update_fields=["status", "error", "updated_at"])


def start_processing(transformation_id: uuid.UUID) -> None:
    t = threading.Thread(target=process_transformation, args=(transformation_id,), daemon=True)
    t.start()
