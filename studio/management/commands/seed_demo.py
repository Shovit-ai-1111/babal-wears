from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from studio.models import StoreSettings, TShirtColor, Print, Product


def font(size):
    candidates = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"), Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf")]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def png(image, name):
    buffer = BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return ContentFile(buffer.getvalue(), name=name)


def print_art(index):
    image = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    if index == 0:
        d.rounded_rectangle((60, 40, 540, 560), 55, fill="#D5FF45")
        d.text((300, 92), "OFFLINE", font=font(67), anchor="mt", fill="#17191B")
        d.text((300, 455), "CLUB", font=font(70), anchor="mt", fill="#17191B")
        d.ellipse((175, 205, 425, 425), fill="#17191B")
        for x in [245, 350]:
            d.ellipse((x-12, 265, x+12, 310), fill="#D5FF45")
        d.arc((235, 290, 365, 370), 5, 175, fill="#D5FF45", width=9)
    elif index == 1:
        d.rounded_rectangle((55, 75, 545, 525), 45, fill="#C8BCF2")
        d.text((300, 120), "LOW", font=font(96), anchor="mt", fill="#17191B")
        d.text((300, 225), "BATTERY", font=font(58), anchor="mt", fill="#17191B")
        d.rounded_rectangle((140, 340, 440, 445), 15, outline="#17191B", width=12)
        d.rectangle((450, 370, 470, 415), fill="#17191B")
        d.rectangle((162, 362, 210, 425), fill="#FF785D")
    elif index == 2:
        d.ellipse((45, 45, 555, 555), fill="#375CFF")
        d.text((300, 175), "OWN", font=font(105), anchor="mt", fill="#F4F1E8")
        d.text((300, 300), "LANE", font=font(100), anchor="mt", fill="#F4F1E8")
        d.line((190, 435, 400, 435), fill="#D5FF45", width=15)
        d.polygon([(390, 405), (430, 435), (390, 465)], fill="#D5FF45")
    else:
        d.rounded_rectangle((45, 45, 555, 555), 40, fill="#FF785D")
        for x in range(100, 510, 60):
            d.line([(x, 175), (x-30, 260), (x+30, 345), (x, 425)], fill="#17191B", width=18)
        d.text((300, 465), "WAVEFORM", font=font(40), anchor="mt", fill="#17191B")
    return image


def product_art(index):
    colors = ["#DCE4D1", "#DED6F3", "#F1D4BD", "#D6DEED"]
    image = Image.new("RGB", (850, 1000), colors[index])
    d = ImageDraw.Draw(image)
    d.ellipse((160, 780, 700, 860), fill="#B5B6AD")
    if index in (0, 3):
        c = "#263F39" if index == 0 else "#4057A1"
        points = [(315, 230), (210, 265), (80, 620), (175, 680), (275, 470), (270, 805), (580, 805), (575, 470), (675, 680), (770, 620), (640, 265), (535, 230)]
        d.polygon(points, fill=c)
        d.ellipse((350, 210, 500, 280), fill=colors[index])
        d.rounded_rectangle((350, 580, 500, 700), 20, outline="#8B9F99", width=3)
        d.text((425, 420), "babal.", anchor="mm", font=font(44), fill="#EDEEDB")
    elif index == 1:
        d.pieslice((220, 300, 670, 770), 180, 360, fill="#25262C")
        d.polygon([(220, 535), (670, 535), (760, 655), (130, 655)], fill="#35363D")
        d.line((445, 320, 445, 530), fill="#75757F", width=4)
        d.text((445, 460), "b.", anchor="mm", font=font(70), fill="#D5FF45")
    else:
        d.rounded_rectangle((260, 210, 590, 500), 150, outline="#A49A7C", width=30)
        d.rectangle((190, 400, 660, 820), fill="#E7DFC9")
        d.text((425, 540), "TAKE", anchor="mm", font=font(60), fill="#F45C3F")
        d.text((425, 625), "IT EASY.", anchor="mm", font=font(55), fill="#F45C3F")
    return image


class Command(BaseCommand):
    help = "Seed clearly marked original demo assets. Safe to repeat; never overwrites catalogue edits or seeds fake reviews."

    def handle(self, *args, **options):
        StoreSettings.load()
        for i, (name, color) in enumerate([("Washed black", "#28292D"), ("Chalk", "#F4F0E5"), ("Moss", "#70826B"), ("Lilac", "#B5A4CC"), ("Burnt orange", "#CA6546")]):
            TShirtColor.objects.get_or_create(name=name, defaults={"hex_code": color, "sort_order": i})
        for i, name in enumerate(["Offline club", "Low battery", "Own lane", "Waveform"]):
            if not Print.objects.filter(name=f"{name} / demo").exists():
                Print.objects.create(name=f"{name} / demo", image=png(print_art(i), f"print-{i}.png"), description="Original demo artwork. Replace with an approved BABAL WEARS print.", is_demo=True, sort_order=i)
        for i, (name, category, price) in enumerate([("Off-duty crew", "Layers", 2200), ("Everyday cap", "Headwear", 650), ("Carry a little", "Bags", 850), ("After-hours hoodie", "Layers", 2600)]):
            if not Product.objects.filter(name=f"{name} / demo").exists():
                Product.objects.create(name=f"{name} / demo", category=category, price=price, image=png(product_art(i), f"product-{i}.png"), is_demo=True, sort_order=i, description="Illustrative product and price. Availability has not been confirmed by the brand.")
        self.stdout.write(self.style.SUCCESS("Demo catalogue ready. No customer reviews or payment accounts were invented."))
