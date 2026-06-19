"""
Seed NexCart with 4 sellers, 5 categories, 20 products with Cloudinary images.
Usage: python manage.py seed_products
"""
import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from apps.vendors.models import Vendor
from apps.products.models import Category, Product

User = get_user_model()

SELLERS = [
    {
        'email': 'seller1@nexcart.cm',
        'first_name': 'Njoh',
        'last_name': 'Emmanuel',
        'phone': '+237670000001',
        'store_name': 'TechHub Cameroon',
        'description': 'Your one-stop shop for phones, laptops and tech gadgets in Cameroon.',
        'city': 'Douala',
        'region': 'Littoral',
        'momo_provider': 'MTN',
        'momo_number': '670000001',
    },
    {
        'email': 'seller2@nexcart.cm',
        'first_name': 'Aisha',
        'last_name': 'Bello',
        'phone': '+237680000002',
        'store_name': 'Aisha Fashion House',
        'description': 'Trendy African fashion, shoes and accessories for men and women.',
        'city': 'Yaoundé',
        'region': 'Centre',
        'momo_provider': 'ORANGE',
        'momo_number': '680000002',
    },
    {
        'email': 'seller3@nexcart.cm',
        'first_name': 'Tabi',
        'last_name': 'Ngwa',
        'phone': '+237650000003',
        'store_name': 'FreshMart Buea',
        'description': 'Fresh groceries, spices, and organic food products delivered to your door.',
        'city': 'Buea',
        'region': 'South West',
        'momo_provider': 'MTN',
        'momo_number': '650000003',
    },
    {
        'email': 'seller4@nexcart.cm',
        'first_name': 'Grace',
        'last_name': 'Fon',
        'phone': '+237690000004',
        'store_name': 'HomeStyle Decor',
        'description': 'Beautiful home décor, kitchen gadgets and furniture for modern living.',
        'city': 'Limbe',
        'region': 'South West',
        'momo_provider': 'ORANGE',
        'momo_number': '690000004',
    },
]

CATALOG = {
    'Electronics': {
        'desc': 'Phones, laptops, gadgets and accessories',
        'image': 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400',
        'seller_idx': 0,
        'products': [
            {'name': 'Samsung Galaxy A54 5G', 'price': 185000, 'compare': 210000, 'stock': 15,
             'desc': 'Samsung Galaxy A54 with 128GB storage, 6GB RAM, Super AMOLED display. Perfect for everyday use with 5000mAh battery.',
             'image': 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400',
             'tags': 'samsung,phone,5g,mobile'},
            {'name': 'HP Pavilion Laptop 15 inch', 'price': 350000, 'compare': 420000, 'stock': 8,
             'desc': '15.6 inch FHD display, Intel Core i5, 8GB RAM, 512GB SSD. Great for students and professionals.',
             'image': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400',
             'tags': 'laptop,hp,computer,school'},
            {'name': 'JBL Flip 6 Bluetooth Speaker', 'price': 45000, 'compare': 55000, 'stock': 25,
             'desc': 'Portable waterproof Bluetooth speaker with powerful bass. 12 hours playtime. Perfect for outdoor parties.',
             'image': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400',
             'tags': 'speaker,bluetooth,jbl,music'},
            {'name': 'Apple AirPods Pro 2nd Gen', 'price': 125000, 'compare': 150000, 'stock': 12,
             'desc': 'Active noise cancellation, spatial audio, MagSafe charging case. Premium wireless earbuds.',
             'image': 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=400',
             'tags': 'airpods,apple,earbuds,wireless'},
        ]
    },
    'Fashion & Clothing': {
        'desc': 'Men and women fashion, African wear, shoes and accessories',
        'image': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400',
        'seller_idx': 1,
        'products': [
            {'name': 'African Print Ankara Dress', 'price': 15000, 'compare': 22000, 'stock': 30,
             'desc': 'Beautiful handmade Ankara dress with modern cuts. Available in multiple colorful African print patterns.',
             'image': 'https://images.unsplash.com/photo-1590735213920-68192a487bc2?w=400',
             'tags': 'ankara,dress,african,women'},
            {'name': 'Mens Leather Oxford Shoes', 'price': 28000, 'compare': 35000, 'stock': 20,
             'desc': 'Genuine leather Oxford shoes. Classic design suitable for office, church, and formal occasions.',
             'image': 'https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=400',
             'tags': 'shoes,leather,men,formal'},
            {'name': 'Dashiki Mens Traditional Shirt', 'price': 8500, 'compare': 12000, 'stock': 40,
             'desc': 'Embroidered West African Dashiki shirt. Comfortable cotton fabric, perfect for casual and cultural events.',
             'image': 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400',
             'tags': 'dashiki,shirt,african,men'},
            {'name': 'Ladies Handwoven Straw Bag', 'price': 12000, 'compare': 18000, 'stock': 15,
             'desc': 'Artisan handwoven straw tote bag. Eco-friendly, locally made in Cameroon. Great for beach and market.',
             'image': 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=400',
             'tags': 'bag,handmade,women,accessories'},
        ]
    },
    'Food & Groceries': {
        'desc': 'Fresh produce, spices, snacks and packaged foods',
        'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400',
        'seller_idx': 2,
        'products': [
            {'name': 'Cameroon Ground Coffee 500g', 'price': 5500, 'compare': 7000, 'stock': 50,
             'desc': 'Premium Arabica coffee beans from Mount Cameroon region. Freshly roasted and ground. Rich bold flavor.',
             'image': 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400',
             'tags': 'coffee,cameroon,organic,drink'},
            {'name': 'White Pepper Penja 250g', 'price': 8000, 'compare': 10000, 'stock': 35,
             'desc': 'World-famous Penja white pepper with GI certification. Aromatic, spicy, and perfect for Cameroonian cuisine.',
             'image': 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=400',
             'tags': 'pepper,penja,spice,cooking'},
            {'name': 'Ndole Spice Mix Pack', 'price': 3500, 'compare': 4500, 'stock': 60,
             'desc': 'Ready-to-use Ndole spice mix with crayfish, maggi, and seasonings. Makes cooking Ndole easy and quick.',
             'image': 'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=400',
             'tags': 'ndole,spice,cameroon,cooking'},
            {'name': 'Organic Palm Oil 2 Litres', 'price': 4000, 'compare': 5000, 'stock': 45,
             'desc': 'Pure organic red palm oil from the South West Region. Unrefined, chemical-free. Essential for Cameroon dishes.',
             'image': 'https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=400',
             'tags': 'palm oil,organic,cooking,cameroon'},
        ]
    },
    'Home & Living': {
        'desc': 'Furniture, kitchen items, home decor and appliances',
        'image': 'https://images.unsplash.com/photo-1484101403633-562f891dc89a?w=400',
        'seller_idx': 3,
        'products': [
            {'name': 'Handcrafted Wooden Side Table', 'price': 35000, 'compare': 45000, 'stock': 10,
             'desc': 'Beautiful hand-carved mahogany side table by local Cameroon artisans. Unique African design.',
             'image': 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400',
             'tags': 'furniture,table,wood,handmade'},
            {'name': 'Non-Stick Cookware Set 5 Pcs', 'price': 22000, 'compare': 30000, 'stock': 18,
             'desc': 'Complete cooking set with frying pan, saucepans, and stockpot. Durable non-stick coating.',
             'image': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400',
             'tags': 'kitchen,cookware,cooking,pots'},
            {'name': 'African Wax Print Throw Pillows', 'price': 8000, 'compare': 12000, 'stock': 25,
             'desc': 'Decorative throw pillows with vibrant African wax print covers. 18x18 inches. Adds color to any room.',
             'image': 'https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=400',
             'tags': 'pillow,decor,african,home'},
            {'name': 'LED Desk Lamp Rechargeable', 'price': 12000, 'compare': 15000, 'stock': 30,
             'desc': 'Rechargeable LED desk lamp with 3 brightness levels. Lasts 8+ hours. Perfect for students during power cuts.',
             'image': 'https://images.unsplash.com/photo-1534073737927-85f1ebff1f5d?w=400',
             'tags': 'lamp,led,study,rechargeable'},
        ]
    },
    'Health & Beauty': {
        'desc': 'Skincare, cosmetics, personal care and wellness',
        'image': 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400',
        'seller_idx': 1,
        'products': [
            {'name': 'Shea Butter Natural 500g', 'price': 3000, 'compare': 4500, 'stock': 50,
             'desc': 'Pure unrefined shea butter from North Cameroon. Natural moisturizer for skin and hair. No additives.',
             'image': 'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=400',
             'tags': 'shea butter,skincare,natural,cameroon'},
            {'name': 'African Black Soap Bar 3 Pack', 'price': 5000, 'compare': 7000, 'stock': 40,
             'desc': 'Traditional African black soap with plantain ash and cocoa pod. Deep cleanses without drying skin.',
             'image': 'https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?w=400',
             'tags': 'soap,black soap,skincare,natural'},
            {'name': 'Coconut Oil Hair Treatment 250ml', 'price': 4500, 'compare': 6000, 'stock': 35,
             'desc': 'Cold-pressed virgin coconut oil blend with castor oil. Promotes hair growth, reduces breakage.',
             'image': 'https://images.unsplash.com/photo-1526947425960-945c6e72858f?w=400',
             'tags': 'hair,coconut oil,treatment,beauty'},
            {'name': 'Aloe Vera Face Cream 100ml', 'price': 6500, 'compare': 8000, 'stock': 28,
             'desc': 'Organic aloe vera moisturizing cream. Soothes, hydrates and protects skin. SPF 15 protection.',
             'image': 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=400',
             'tags': 'face cream,aloe vera,skincare,moisturizer'},
        ]
    },
}


class Command(BaseCommand):
    help = 'Seed database with 4 sellers, 5 categories, and 20 products with Cloudinary images'

    def upload_image(self, url, folder, public_id):
        """Upload image URL to Cloudinary"""
        try:
            self.stdout.write(f'  Uploading {public_id}...', ending=' ')
            result = cloudinary.uploader.upload(
                url,
                folder=f'nexcart/{folder}',
                public_id=public_id,
                overwrite=True,
                resource_type='image',
                transformation=[
                    {'width': 600, 'height': 600, 'crop': 'fill', 'quality': 'auto'}
                ]
            )
            self.stdout.write(self.style.SUCCESS('OK'))
            return result['secure_url']
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'FAILED ({e})'))
            return ''

    def add_arguments(self, parser):
        parser.add_argument('--update-images', action='store_true', help='Force re-upload images even for existing products')

    def handle(self, *args, **options):
        update_images = options.get('update_images', False)
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.HTTP_INFO('SEEDING NEXCART DATABASE'))
        self.stdout.write('=' * 60)

        # ── Create Sellers ───────────────────────────────────
        vendors = []
        for s in SELLERS:
            self.stdout.write(f'\nCreating seller: {s["store_name"]}')

            user, created = User.objects.get_or_create(
                email=s['email'],
                defaults={
                    'first_name': s['first_name'],
                    'last_name': s['last_name'],
                    'phone': s['phone'],
                    'is_active': True,
                    'is_verified': True,
                }
            )
            if created:
                user.set_password('seller123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  User created: {s["email"]}'))
            else:
                self.stdout.write(f'  User exists: {s["email"]}')

            vendor, v_created = Vendor.objects.get_or_create(
                user=user,
                defaults={
                    'store_name': s['store_name'],
                    'slug': slugify(s['store_name']),
                    'description': s['description'],
                    'phone': s['phone'],
                    'city': s['city'],
                    'region': s['region'],
                    'momo_provider': s['momo_provider'],
                    'momo_number': s['momo_number'],
                    'status': 'approved',
                    'is_active': True,
                    'is_verified': True,
                    'approved_at': timezone.now(),
                }
            )
            if v_created:
                self.stdout.write(self.style.SUCCESS(f'  Vendor approved: {s["store_name"]}'))
            else:
                self.stdout.write(f'  Vendor exists: {s["store_name"]}')

            vendors.append(vendor)

        # ── Create Categories & Products ─────────────────────
        sku_counter = 1000

        for cat_name, cat_data in CATALOG.items():
            self.stdout.write(f'\nCategory: {cat_name}')
            cat_slug = slugify(cat_name)

            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={
                    'slug': cat_slug,
                    'description': cat_data['desc'],
                    'is_active': True,
                }
            )

            # Upload category image if missing or forced
            if not category.image or update_images:
                cat_image_url = self.upload_image(cat_data['image'], 'categories', cat_slug)
                if cat_image_url:
                    category.image = cat_image_url
                    category.save(update_fields=['image'])

            vendor = vendors[cat_data['seller_idx']]

            for p in cat_data['products']:
                sku_counter += 1
                prod_slug = slugify(p['name'])

                product, p_created = Product.objects.get_or_create(
                    slug=prod_slug,
                    defaults={
                        'name': p['name'],
                        'description': p['desc'],
                        'short_description': p['desc'][:200],
                        'category': category,
                        'vendor': vendor,
                        'price': p['price'],
                        'compare_price': p.get('compare'),
                        'sku': f'NXC-{sku_counter}',
                        'stock_quantity': p['stock'],
                        'tags': p.get('tags', ''),
                        'is_active': True,
                        'is_featured': sku_counter % 3 == 0,
                    }
                )

                # Upload image if missing or forced
                if not product.featured_image or update_images:
                    prod_image_url = self.upload_image(p['image'], 'products', prod_slug)
                    if prod_image_url:
                        product.featured_image = prod_image_url
                        product.save(update_fields=['featured_image'])
                        self.stdout.write(self.style.SUCCESS(f'    Image updated: {p["name"]}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'    No image: {p["name"]}'))
                elif p_created:
                    self.stdout.write(self.style.SUCCESS(f'    Created: {p["name"]} - {p["price"]:,} FCFA'))
                else:
                    self.stdout.write(f'    OK: {p["name"]}')

            vendor.total_products = Product.objects.filter(vendor=vendor, is_active=True).count()
            vendor.save(update_fields=['total_products'])


        # ── Summary ──────────────────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('SEEDING COMPLETE!'))
        self.stdout.write(f'   Sellers: {Vendor.objects.count()}')
        self.stdout.write(f'   Categories: {Category.objects.count()}')
        self.stdout.write(f'   Products: {Product.objects.count()}')
        self.stdout.write(f'   Admin: admin@nexcart.com')
        self.stdout.write(f'   Seller logins: seller1@nexcart.cm - seller4@nexcart.cm')
        self.stdout.write(f'   Seller password: seller123')
        self.stdout.write('=' * 60)
