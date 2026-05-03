import secrets

from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Transformation
from .serializers import TransformationCreateSerializer, TransformationSerializer
from .tasks import start_processing

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

_TRUTHY = {"true", "1", "yes", "on"}


def _validate_image(file) -> str | None:
    if file.size > MAX_FILE_SIZE:
        return "File too large. Maximum size is 20 MB."
    content_type = getattr(file, "content_type", "")
    if content_type not in ALLOWED_CONTENT_TYPES:
        return f"Unsupported file type '{content_type}'. Use JPEG, PNG or WebP."
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except (UnidentifiedImageError, Exception):
        return "File does not appear to be a valid image."
    return None


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in _TRUTHY


def _parse_choice(value: str | None, choices: type, default: str) -> str:
    if value is None:
        return default
    allowed = {c.value for c in choices}
    return value if value in allowed else default


def _extract_options(request: Request) -> dict:
    return {
        "allow_cars": _parse_bool(request.data.get("allow_cars"), default=False),
        "fietsstraat": _parse_bool(request.data.get("fietsstraat"), default=False),
        "ground_cover": _parse_choice(
            request.data.get("ground_cover"),
            Transformation.GroundCover,
            Transformation.GroundCover.MIXED,
        ),
        "shape_style": _parse_choice(
            request.data.get("shape_style"),
            Transformation.ShapeStyle,
            Transformation.ShapeStyle.ORGANIC,
        ),
    }


@api_view(["POST"])
@parser_classes([MultiPartParser])
def transformation_create(request: Request) -> Response:
    file = request.FILES.get("image")
    if file is None:
        return Response({"detail": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

    error = _validate_image(file)
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

    transformation = Transformation.objects.create(
        original_image=file,
        **_extract_options(request),
    )
    start_processing(transformation.pk)

    serializer = TransformationCreateSerializer(transformation, context={"request": request})
    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "DELETE"])
def transformation_detail(request: Request, pk: str) -> Response:
    try:
        transformation = Transformation.objects.get(pk=pk)
    except (Transformation.DoesNotExist, Exception):
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        return _handle_delete(request, transformation)

    serializer = TransformationSerializer(transformation, context={"request": request})
    return Response(serializer.data)


def _handle_delete(request: Request, transformation: Transformation) -> Response:
    token = request.headers.get("X-Delete-Token", "")
    if not token:
        return Response({"detail": "Delete token required."}, status=status.HTTP_401_UNAUTHORIZED)
    if not secrets.compare_digest(token, transformation.delete_token):
        return Response({"detail": "Invalid delete token."}, status=status.HTTP_403_FORBIDDEN)

    for field in (transformation.original_image, transformation.result_image, transformation.comparison_image):
        if field:
            field.delete(save=False)
    transformation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class GalleryPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48


@api_view(["GET"])
def transformation_list(request: Request) -> Response:
    qs = Transformation.objects.filter(
        status=Transformation.Status.DONE,
        is_public=True,
    )
    if request.query_params.get("featured", "").lower() in _TRUTHY:
        qs = qs.filter(is_featured=True)
    paginator = GalleryPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = TransformationSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)
