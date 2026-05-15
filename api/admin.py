from django.contrib import admin

from .models import Transformation


@admin.register(Transformation)
class TransformationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "is_public",
        "is_featured",
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
        "is_featured",
        "allow_cars",
        "fietsstraat",
        "ground_cover",
        "shape_style",
        "created_at",
    )
    actions = ["mark_featured", "unmark_featured"]

    @admin.action(description="Mark selected as featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Unmark selected as featured")
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)

    search_fields = ("id", "error")
    readonly_fields = (
        "id",
        "original_image",
        "result_image",
        "comparison_image",
        "prompt",
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
                    "is_featured",
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
            "Prompt",
            {
                "fields": ("prompt",),
                "classes": ("collapse",),
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
