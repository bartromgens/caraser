import io
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import Transformation

IMAGE_FIELDS = ["original_image", "result_image", "thumbnail_image", "comparison_image"]


def _png_to_jpg(data: bytes) -> bytes:
    from PIL import Image

    img = Image.open(io.BytesIO(data)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Convert PNG images to JPG for all image fields on Transformation."

    def handle(self, *args, **options):
        qs = Transformation.objects.all()
        total = qs.count()

        if total == 0:
            self.stdout.write("No transformations found.")
            return

        self.stdout.write(f"Scanning {total} transformation(s)…")
        ok = failed = skipped = 0

        for t in qs.iterator():
            changed_fields: list[str] = []

            for field_name in IMAGE_FIELDS:
                field = getattr(t, field_name)
                if not field or not field.name:
                    continue

                if not field.name.lower().endswith(".png"):
                    continue

                try:
                    png_bytes = field.read()
                    jpg_bytes = _png_to_jpg(png_bytes)

                    old_path = field.path
                    new_name = os.path.splitext(field.name)[0] + ".jpg"
                    field.save(
                        os.path.basename(new_name),
                        ContentFile(jpg_bytes),
                        save=False,
                    )
                    os.remove(old_path)
                    changed_fields.append(field_name)
                except Exception as exc:
                    failed += 1
                    self.stderr.write(
                        self.style.ERROR(f"  [FAIL] {t.pk} / {field_name}: {exc}")
                    )

            if changed_fields:
                t.save(update_fields=[*changed_fields, "updated_at"])
                ok += 1
                self.stdout.write(f"  [OK] {t.pk}: {', '.join(changed_fields)}")
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {ok} converted, {skipped} skipped, {failed} failed."
            )
        )
