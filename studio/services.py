from django.db import transaction
from .models import Order, PaymentProof, TShirtColor, Print, StoreSettings


def create_order(cleaned):
    """Prices and catalogue snapshots are fixed atomically on the server."""
    existing = Order.objects.filter(submission_key=cleaned["submission_key"]).first()
    if existing:
        return existing
    saved_files = []
    try:
        with transaction.atomic():
            color = TShirtColor.objects.select_for_update().get(pk=cleaned["color"].pk, is_active=True)
            artwork = Print.objects.select_for_update().get(pk=cleaned["print"].pk, is_active=True)
            store = StoreSettings.objects.select_for_update().get(pk=1)
            unit_price = store.base_price + color.price_adjustment + artwork.surcharge
            fields = ["submission_key", "placement", "print_scale", "full_name", "instagram_username", "phone", "province", "district", "municipality", "ward", "landmark", "size", "quantity", "notes", "payment_method"]
            order = Order(**{name: cleaned[name] for name in fields}, color=color, print=artwork,
                          color_name=color.name, color_hex=color.hex_code, print_name=artwork.name,
                          unit_price=unit_price, delivery_fee=store.delivery_fee,
                          total=unit_price * cleaned["quantity"] + store.delivery_fee,
                          payment_status=Order.PaymentStatus.UNPAID if cleaned["payment_method"] == "cod" else Order.PaymentStatus.REVIEW)
            order.generated_image = cleaned["design_image"]
            # Save file separately so a database rollback can remove it as well.
            from .validators import sanitized_image
            image = sanitized_image(order.generated_image)
            order.generated_image.save(image.name, image, save=False)
            saved_files.append(order.generated_image)
            order.save()
            if cleaned["payment_method"] != "cod":
                proof = PaymentProof(order=order)
                image = sanitized_image(cleaned["payment_screenshot"])
                proof.image.save(image.name, image, save=False)
                saved_files.append(proof.image)
                proof.save()
        return order
    except Exception:
        for file in saved_files:
            file.storage.delete(file.name)
        raise
