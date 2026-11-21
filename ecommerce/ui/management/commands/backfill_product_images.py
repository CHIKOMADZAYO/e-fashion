from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from ecommerce.ui.models import Product
import os


class Command(BaseCommand):
    help = "Backfill product images from static to media"

    def handle(self, *args, **options):
        mapping = {
            'Classic Everyday Loafer': 'product-14.jpg',
            'Classic Low-Top Sneaker': 'product-10.jpg',
            'Everyday Leather Belt': 'product-06.jpg',
            'Everyday Straight-Leg Jean': 'product-09.jpg',
            'Linen Blend Summer Dress': 'product-12.jpg',
            'Relaxed Tailored Shirt': 'product-04.jpg',
            'Relaxed Tapered Trouser': 'product-13.jpg',
            'Soft Cotton Weekend Tee': 'product-02.jpg',
            'The City Crossbody': 'product-11.jpg',
            'The Essential Cotton Tee': 'product-01.jpg',
            'The Everyday Tote': 'product-15.jpg',
            'The Soft Knit Cardigan': 'product-05.jpg',
            'The Sunday Shirt': 'product-03.jpg',
            'The Weekend Knit': 'product-07.jpg',
            'The Weekend Overshirt': 'product-16.jpg',
            'The Weekend Shirt Dress': 'product-08.jpg',
        }

        for product_name, filename in mapping.items():
            src = os.path.join('ecommerce', 'ui', 'static', 'ui', 'images', filename)
            if os.path.exists(src):
                product = Product.objects.filter(name=product_name).first()
                if product:
                    with open(src, 'rb') as f:
                        product.image.save(filename, ContentFile(f.read()), save=True)
                    self.stdout.write(f'Assigned {filename} to {product_name}')
                else:
                    self.stdout.write(f'PRODUCT NOT FOUND: {product_name}')
            else:
                self.stdout.write(f'IMAGE NOT FOUND: {src}')

        self.stdout.write('\nDone.')
        for p in Product.objects.all():
            self.stdout.write(f'  {p.name}: {p.image.url if p.image else "None"}')
