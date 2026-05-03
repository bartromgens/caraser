from django.contrib import admin

from .models import Transformation


@admin.register(Transformation)
class TransformationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "is_public",
        "allow_cars",
        "fietsstraat",
        "ground_cover",
        "shape_style",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "is_public",
        "allow_cars",
        "fietsstraat",
        "ground_cover",
        "shape_style",
        "created_at",
    )
    search_fields = ("id", "error")
    readonly_fields = (
        "id",
        "original_image",
        "result_image",
        "comparison_image",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "status",
                    "error",
                    "is_public",
                )
            },
        ),
        (
            "Images",
            {
                "fields": (
                    "original_image",
                    "result_image",
                    "comparison_image",
                )
            },
        ),
        (
            "Options",
            {
                "fields": (
                    "allow_cars",
                    "fietsstraat",
                    "ground_cover",
                    "shape_style",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
