from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import Transformation
from api.services.comparison import build_comparison_image


class Command(BaseCommand):
    help = "Generate (or regenerate) comparison images for all completed transformations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate even when a comparison_image already exists.",
        )

    def handle(self, *args, **options):
        force: bool = options["force"]

        qs = Transformation.objects.filter(status=Transformation.Status.DONE)
        if not force:
            qs = qs.filter(comparison_image="")

        total = qs.count()
        if total == 0:
            self.stdout.write("Nothing to do.")
            return

        self.stdout.write(f"Processing {total} transformation(s)…")
        ok = skipped = failed = 0

        for t in qs.iterator():
            try:
                before_bytes = t.original_image.read()
                t.original_image.seek(0)
                after_bytes = t.result_image.read()
                t.result_image.seek(0)

                comparison_bytes = build_comparison_image(before_bytes, after_bytes)
                t.comparison_image.save(
                    f"{t.pk}-comparison.jpg",
                    ContentFile(comparison_bytes),
                    save=False,
                )
                t.save(update_fields=["comparison_image", "updated_at"])
                ok += 1
                self.stdout.write(f"  [OK] {t.pk}")
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  [FAIL] {t.pk}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {ok} generated, {skipped} skipped, {failed} failed."
            )
        )
