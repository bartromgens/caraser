import secrets
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
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
MAX_IMAGE_SIDE = 1536  # px — generous headroom above the 1 K Gemini output

_TRUTHY = {"true", "1", "yes", "on"}
_FALSY = {"false", "0", "no", "off"}


def _to_jpeg_upload(file) -> InMemoryUploadedFile:
    buf = BytesIO()
    img = Image.open(file)
    # Honor EXIF orientation (e.g. portrait photos from phones) before stripping metadata.
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    if max(img.width, img.height) > MAX_IMAGE_SIDE:
        img = ImageOps.contain(img, (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    stem = file.name.rsplit(".", 1)[0] if "." in file.name else file.name
    size = len(buf.getvalue())
    return InMemoryUploadedFile(buf, "image", f"{stem}.jpg", "image/jpeg", size, None)


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


def _to_png_overlay(file, target_width: int, target_height: int):
    """Validate and resize the overlay PNG to match the processed original dimensions."""
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
        img = Image.open(file)
    except Exception:
        return None, "Overlay is not a valid image."

    if img.format not in ("PNG",):
        # Re-open after verify resets the object; allow any PNG-compatible format
        pass

    img = img.convert("RGBA")
    if img.width != target_width or img.height != target_height:
        img = img.resize((target_width, target_height), Image.NEAREST)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    size = len(buf.getvalue())
    from django.core.files.uploadedfile import InMemoryUploadedFile

    name = getattr(file, "name", "overlay")
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return (
        InMemoryUploadedFile(buf, "overlay", f"{stem}.png", "image/png", size, None),
        None,
    )


@csrf_protect
@api_view(["POST"])
@parser_classes([MultiPartParser])
def transformation_create(request: Request) -> Response:
    file = request.FILES.get("image")
    if file is None:
        return Response(
            {"detail": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST
        )

    error = _validate_image(file)
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

    mode = _parse_choice(
        request.data.get("mode"),
        Transformation.Mode,
        Transformation.Mode.CLASSIC,
    )

    jpeg_file = _to_jpeg_upload(file)

    if mode == Transformation.Mode.DESIGNER:
        overlay_file_raw = request.FILES.get("overlay")
        if overlay_file_raw is None:
            return Response(
                {"detail": "Designer mode requires an overlay image."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Determine the dimensions of the processed JPEG so the overlay can be matched.
        jpeg_file.seek(0)
        processed_img = Image.open(jpeg_file)
        target_w, target_h = processed_img.width, processed_img.height
        jpeg_file.seek(0)

        overlay_file, overlay_error = _to_png_overlay(
            overlay_file_raw, target_w, target_h
        )
        if overlay_error:
            return Response(
                {"detail": overlay_error}, status=status.HTTP_400_BAD_REQUEST
            )

        transformation = Transformation.objects.create(
            original_image=jpeg_file,
            overlay_image=overlay_file,
            mode=mode,
        )
    else:
        transformation = Transformation.objects.create(
            original_image=jpeg_file,
            **_extract_options(request),
        )

    start_processing(transformation.pk)

    serializer = TransformationCreateSerializer(
        transformation, context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "DELETE", "PATCH"])
def transformation_detail(request: Request, pk: str) -> Response:
    try:
        transformation = Transformation.objects.get(pk=pk)
    except (Transformation.DoesNotExist, Exception):
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        return _handle_delete(request, transformation)

    if request.method == "PATCH":
        return _handle_patch(request, transformation)

    serializer = TransformationSerializer(transformation, context={"request": request})
    return Response(serializer.data)


def _is_authenticated(request: Request) -> bool:
    return bool(request.user and request.user.is_authenticated)


def _has_valid_delete_token(request: Request, transformation: Transformation) -> bool:
    token = request.headers.get("X-Delete-Token", "")
    return bool(token) and secrets.compare_digest(token, transformation.delete_token)


def _handle_patch(request: Request, transformation: Transformation) -> Response:
    if not _is_authenticated(request):
        return Response(
            {"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if "is_featured" in request.data:
        transformation.is_featured = _parse_bool(
            request.data.get("is_featured"), default=False
        )
        transformation.save(update_fields=["is_featured"])

    serializer = TransformationSerializer(transformation, context={"request": request})
    return Response(serializer.data)


def _handle_delete(request: Request, transformation: Transformation) -> Response:
    if not (
        _is_authenticated(request) or _has_valid_delete_token(request, transformation)
    ):
        return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

    for field in (
        transformation.original_image,
        transformation.result_image,
        transformation.thumbnail_image,
        transformation.comparison_image,
    ):
        if field:
            field.delete(save=False)
    transformation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class GalleryPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48


@ensure_csrf_cookie
@api_view(["GET"])
def auth_me(request: Request) -> Response:
    user = request.user
    if user.is_authenticated:
        return Response({"is_authenticated": True, "username": user.get_username()})
    return Response({"is_authenticated": False})


@ensure_csrf_cookie
@api_view(["GET"])
def transformation_list(request: Request) -> Response:
    ids_param = request.query_params.get("ids", "")
    if ids_param:
        ids = [s.strip() for s in ids_param.split(",") if s.strip()]
        qs = Transformation.objects.filter(
            id__in=ids, status=Transformation.Status.DONE
        )
    else:
        qs = Transformation.objects.filter(
            status=Transformation.Status.DONE,
            is_public=True,
        )
        featured = request.query_params.get("featured", "").lower()
        if featured in _TRUTHY:
            qs = qs.filter(is_featured=True).order_by("?")
        elif featured in _FALSY:
            qs = qs.filter(is_featured=False)
    paginator = GalleryPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = TransformationSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)
