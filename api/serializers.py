from rest_framework import serializers

from .models import Transformation


class TransformationSerializer(serializers.ModelSerializer):
    original_image = serializers.ImageField(use_url=True)
    result_image = serializers.ImageField(use_url=True, allow_null=True, read_only=True)
    comparison_image = serializers.ImageField(use_url=True, allow_null=True, read_only=True)

    class Meta:
        model = Transformation
        fields = [
            "id",
            "original_image",
            "result_image",
            "comparison_image",
            "status",
            "error",
            "is_public",
            "allow_cars",
            "fietsstraat",
            "ground_cover",
            "shape_style",
            "created_at",
        ]
        read_only_fields = ["id", "result_image", "comparison_image", "status", "error", "created_at"]
