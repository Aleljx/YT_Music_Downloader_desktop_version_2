"""
Обработка обложек треков.

Проблема: YouTube для музыкальных треков часто отдаёт превью, где
квадратная обложка альбома вписана в кадр 16:9 (или другую пропорцию)
на чёрном фоне — это не padding на уровне отображения, а буквально
впечатанные в пиксели чёрные поля. YouTube Music у себя их обрезает
на лету при отображении, а мы получаем уже "плоскую" картинку с этими
полосами. Поэтому обрезать их нужно самим, а не просто вписывать
изображение в квадратный виджет.
"""

from io import BytesIO

from PIL import Image, ImageChops


def process_cover_image(raw_bytes: bytes, threshold: int = 24, target_size: int = 500) -> bytes | None:
    """
    1. Обрезает чёрные поля по краям (если они есть).
    2. Обрезает результат по центру до квадрата.
    3. Возвращает готовые JPEG-байты — для показа в UI и для встраивания в mp3.

    Возвращает None, если байты не удалось декодировать как изображение.
    """
    try:
        img = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except Exception:
        return None

    img = _trim_black_borders(img, threshold)
    img = _crop_to_square(img)

    if target_size and (img.width > target_size or img.height > target_size):
        img = img.resize((target_size, target_size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _trim_black_borders(img: Image.Image, threshold: int) -> Image.Image:
    """
    Сравнивает картинку с чёрным полотном того же размера и находит
    bounding box непочти-чёрной области. threshold — насколько тёмный
    пиксель ещё считается "чёрной полосой" (0-255, чем выше — тем
    агрессивнее обрезка тёмных краёв).
    """
    black_bg = Image.new(img.mode, img.size, (0, 0, 0))
    diff = ImageChops.difference(img, black_bg)
    # Вычитаем порог из разницы — почти-чёрные пиксели уходят в 0,
    # у настоящего контента разница остаётся положительной.
    diff = ImageChops.add(diff, diff, 2.0, -threshold)
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img


def _crop_to_square(img: Image.Image) -> Image.Image:
    """Обрезает по центру до квадрата (используется меньшая сторона)."""
    side = min(img.width, img.height)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    return img.crop((left, top, left + side, top + side))
