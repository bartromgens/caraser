from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import Transformation
from api.tasks import _to_thumbnail


class Command(BaseCommand):
    help = "Generate (or regenerate) thumbnails for all completed transformations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate even when a thumbnail_image already exists.",
        )

    def handle(self, *args, **options):
        force: bool = options["force"]

        qs = Transformation.objects.filter(status=Transformation.Status.DONE)
        if not force:
            qs = qs.filter(thumbnail_image="")

        total = qs.count()
        if total == 0:
            self.stdout.write("Nothing to do.")
            return

        self.stdout.write(f"Processing {total} transformation(s)…")
        ok = failed = 0

        for t in qs.iterator():
            try:
                result_bytes = t.result_image.read()
                t.result_image.seek(0)

                thumbnail_bytes = _to_thumbnail(result_bytes)
                t.thumbnail_image.save(
                    f"{t.pk}-thumb.jpg",
                    ContentFile(thumbnail_bytes),
                    save=False,
                )
                t.save(update_fields=["thumbnail_image", "updated_at"])
                ok += 1
                self.stdout.write(f"  [OK] {t.pk}")
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  [FAIL] {t.pk}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nDone — {ok} generated, {failed} failed.")
        )
