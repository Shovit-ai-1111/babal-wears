import re
import warnings
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


def normalize_phone(value):
    value = str(value).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    value = re.sub(r"[\s()-]", "", value)
    if value.startswith("+977"):
        value = value[4:]
    elif value.startswith("977") and len(value) == 13:
        value = value[3:]
    # Validate Nepal mobile syntax, not carrier ownership or reachability.
    if not re.fullmatch(r"9[678]\d{8}", value):
        raise ValidationError("Enter a 10-digit Nepali mobile number starting with 96, 97 or 98.")
    return value


def normalize_instagram(value):
    value = value.strip().lstrip("@")
    if value and not re.fullmatch(r"[A-Za-z0-9._]{1,30}", value):
        raise ValidationError("Use an Instagram username, without a link or spaces.")
    return value


def validate_image(upload):
    if upload.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("Use a PNG, JPEG or WebP image smaller than 5 MB.")
    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(upload)
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValidationError("Only PNG, JPEG and WebP images are accepted. SVG and GIF are not supported.")
            if image.width * image.height > settings.MAX_IMAGE_PIXELS or max(image.size) > 6000:
                raise ValidationError("Image dimensions are too large. Maximum: 16 megapixels and 6000px per side.")
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("This image is damaged or is not a supported image.")
    finally:
        upload.seek(0)


def sanitized_image(upload, max_side=1800):
    """Decode and re-encode: never retain metadata or an untrusted original filename."""
    validate_image(upload)
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
    upload.seek(0)
    return ContentFile(output.getvalue(), name=f"{uuid4().hex}.png")
