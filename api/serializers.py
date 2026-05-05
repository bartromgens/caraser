from rest_framework import serializers

from .models import Transformation

_COMMON_FIELDS = [
    "id",
    "original_image",
    "result_image",
    "thumbnail_image",
    "comparison_image",
    "status",
    "error",
    "is_public",
    "is_featured",
    "allow_cars",
    "fietsstraat",
    "ground_cover",
    "shape_style",
    "created_at",
]

_COMMON_READ_ONLY = [
    "id",
    "result_image",
    "thumbnail_image",
    "comparison_image",
    "status",
    "error",
    "is_featured",
    "created_at",
]


class TransformationSerializer(serializers.ModelSerializer):
    original_image = serializers.ImageField(use_url=True)
    result_image = serializers.ImageField(use_url=True, allow_null=True, read_only=True)
    thumbnail_image = serializers.ImageField(
        use_url=True, allow_null=True, read_only=True
    )
    comparison_image = serializers.ImageField(
        use_url=True, allow_null=True, read_only=True
    )
    prompt = serializers.SerializerMethodField()

    class Meta:
        model = Transformation
        fields = _COMMON_FIELDS + ["prompt"]
        read_only_fields = _COMMON_READ_ONLY + ["prompt"]

    def get_prompt(self, obj: Transformation) -> str | None:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.prompt or ""
        return None


class TransformationCreateSerializer(TransformationSerializer):
    delete_token = serializers.CharField(read_only=True)

    class Meta(TransformationSerializer.Meta):
        fields = _COMMON_FIELDS + ["delete_token"]
