import secrets
import uuid

from django.db import models


class Transformation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        DONE = "done"
        FAILED = "failed"

    class Mode(models.TextChoices):
        CLASSIC = "classic"
        DESIGNER = "designer"

    class GroundCover(models.TextChoices):
        MIXED = "mixed", "Mixed"
        STONES = "stones", "Stones"
        GRASS = "grass", "Grass"
        FLOWERS = "flowers", "Flowers"

    class ShapeStyle(models.TextChoices):
        MIXED = "mixed", "Mixed"
        ORGANIC = "organic", "Organic"
        STRAIGHT = "straight", "Straight"
        WILDERNESS = "wilderness", "Wilderness"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.CLASSIC)
    original_image = models.ImageField(upload_to="originals/%Y/%m/%d/")
    overlay_image = models.ImageField(
        upload_to="overlays/%Y/%m/%d/", blank=True, null=True
    )
    result_image = models.ImageField(
        upload_to="results/%Y/%m/%d/", blank=True, null=True
    )
    thumbnail_image = models.ImageField(
        upload_to="thumbnails/%Y/%m/%d/", blank=True, null=True
    )
    comparison_image = models.ImageField(
        upload_to="comparisons/%Y/%m/%d/", blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error = models.TextField(blank=True)
    prompt = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)

    allow_cars = models.BooleanField(default=False)
    fietsstraat = models.BooleanField(default=False)
    ground_cover = models.CharField(
        max_length=16, choices=GroundCover.choices, default=GroundCover.MIXED
    )
    shape_style = models.CharField(
        max_length=16, choices=ShapeStyle.choices, default=ShapeStyle.MIXED
    )

    is_featured = models.BooleanField(default=False, db_index=True)

    delete_token = models.CharField(
        max_length=64, default=secrets.token_urlsafe, editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
