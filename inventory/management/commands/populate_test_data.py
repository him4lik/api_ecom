from django.core.management.base import BaseCommand
import random
import datetime
from inventory.models import Category, Product, FilterSpecs, ProductVariant, FeaturedProductLine
from django.contrib.auth.models import User
from user.models import UserProfile, UserAddress 


class Command(BaseCommand):
    help = "This command populates db with test data"

    def handle(self, *args, **kwargs):
        Category.objects.all().delete()
        Product.objects.all().delete()
        FilterSpecs.objects.all().delete()
        ProductVariant.objects.all().delete()
        FeaturedProductLine.objects.all().delete()
        User.objects.all().delete()
        UserProfile.objects.all().delete()

        category_names = ["Men", "Women", "Home Interior", "Accessories", "Gifts"]
        categories = {name: Category.objects.create(name=name) for name in category_names}

        products_data = [
            ("Handmade Leather Shoes", ["Men", "Women"]),
            ("Handwoven Wool Rug", ["Home Interior"]),
            ("Decorative Pillow Covers", ["Home Interior"]),
            ("Handcrafted Wooden Bangles", ["Women", "Gifts"]),
            ("Leather Wallet", ["Men", "Women", "Accessories"]),
            ("Handmade Silk Scarf", ["Women", "Accessories"]),
            ("Organic Cotton Tote Bag", ["Women", "Accessories"]),
        ]

        for product_name, category_list in products_data:
            product = Product.objects.create(
                name=product_name,
                description=f"Beautifully handcrafted {product_name.lower()} made with love."
            )
            product.categories.set([categories[cat] for cat in category_list])

        self.stdout.write(self.style.SUCCESS("Successfully populated the database!"))

        COLORS = ["Red", "Blue", "Black", "Brown", "Green"]
        SIZES = ["S", "M", "L", "XL"]
        MATERIALS = ["Leather", "Cotton", "Wool", "Silk", "Wood"]
        PRICES = [999, 1299, 1499, 1999, 2499, 2999]

        categories = Category.objects.prefetch_related("product_set").all()

        for category in categories:
            products = category.product_set.all()

            for product in products:
                filter_tags = {
                    "Color": random.choice(COLORS),
                    "Size": random.choice(SIZES),
                    "Material": random.choice(MATERIALS),
                }
                FilterSpecs.objects.create(
                    category=category,
                    product=product,
                    filter_tags=list(filter_tags.values())  
                )

                for i in range(5):
                    price = random.choice(PRICES)
                    variant = ProductVariant(
                        name=f"{product.name} {category.name} Variant {i+1}",
                        product_id=product.id,
                        category_id=category.id,
                        price=price,
                        file_path=f"http://localhost:8001/media/variants/variant1.jpg",
                        filters=filter_tags,
                        current_stock=random.randint(10, 100),
                        sold_stock=random.randint(0, 50),
                        is_active=True,
                        created_at=datetime.datetime.utcnow(),
                        updated_at=datetime.datetime.utcnow()
                    )
                    variant.save()

        self.stdout.write(self.style.SUCCESS("Test data populated successfully!"))

        FEATURED_PRODUCTS = [
            {
                "title": "Luxury Handmade Leather Shoes",
                "description": "Premium handcrafted leather shoes for men.",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            },
            {
                "title": "Elegant Handwoven Rugs",
                "description": "Artisan-crafted rugs to enhance your living space.",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            },
            {
                "title": "Exclusive Women's Accessories",
                "description": "A collection of handcrafted bags, scarves, and jewelry.",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            },
            {
                "title": "Luxury Handmade Leather wallet",
                "description": "Premium handcrafted wallets for men.",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            },
            {
                "title": "Elegant Handwoven crochet",
                "description": "Artisan-crafted crochet to enhance your living space.",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            },
            {
                "title": "Exclusive Women's bag",
                "description": "A collection of handcrafted bags",
                "images": ["http://localhost:8001/media/product_line/accessory1.jpg", "http://localhost:8001/media/product_line/accessory1.jpg"],
            }
        ]

        variant_objects = list(ProductVariant.objects(is_active=True).only("id"))
        variant_ids = [str(variant.id) for variant in variant_objects]

        i = 0
        for product in FEATURED_PRODUCTS:
            if len(variant_ids) < 10:
                print("Not enough variants available. Need at least 30.")
                return

            assigned_variants = random.sample(variant_ids, 10)

            featured_product = FeaturedProductLine.objects.create(
                title=product["title"],
                description=product["description"],
                images=product["images"],
                is_active=True,
                variants=assigned_variants  
            )
            if i<3:
                featured_product.is_primary = True
                featured_product.save()
            i += 1
            print(f"Created FeaturedProductLine: {featured_product.title}")


        for _ in range(5):
            phone_number = str(random.randint(6000000000, 9999999999))

            if User.objects.filter(username=phone_number).exists():
                continue

            user = User.objects.create_user(username=phone_number, password="Test@1234")

            address = UserAddress(
                line_1="123 Street Name",
                city="Sample City",
                state="Sample State",
                pin=123456,
                landmark="Near Park"
            )

            profile = UserProfile(
                user_id=user.id,
                name=f"User {phone_number}",
                email=f"user{phone_number}@example.com",
                addresses=[address],
            )
            profile.save()

        print("Users and profiles created successfully!")

