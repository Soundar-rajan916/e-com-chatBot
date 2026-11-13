import argparse
import json
import random
from pathlib import Path

# Seed for reproducible deterministic generation
SEED = 42

CATEGORIES = [
    {
        "id": "sarees_ethnic",
        "name_en": "Sarees & Ethnic Wear",
        "name_ta": "புடவைகள் மற்றும் பாரம்பரிய ஆடைகள்",
        "subcategories": ["Kanchipuram Silk", "Cotton Sarees", "Kurtis", "Dhotis", "Salwar Suits"],
        "price_min": 499,
        "price_max": 24999,
    },
    {
        "id": "mens_wear",
        "name_en": "Men's Clothing",
        "name_ta": "ஆண்கள் ஆடைகள்",
        "subcategories": ["Formal Shirts", "Casual T-Shirts", "Trousers", "Blazers", "Lungi & Vesti"],
        "price_min": 299,
        "price_max": 7999,
    },
    {
        "id": "womens_wear",
        "name_en": "Women's Clothing",
        "name_ta": "பெண்கள் ஆடைகள்",
        "subcategories": ["Tops", "Leggings", "Nightwear", "Maxi Dresses", "Ethnic Skirts"],
        "price_min": 299,
        "price_max": 5999,
    },
    {
        "id": "footwear",
        "name_en": "Footwear",
        "name_ta": "காலணிகள்",
        "subcategories": [
            "Running Shoes",
            "Leather Sandals",
            "Formal Shoes",
            "Kolhapuri Chappals",
            "Casual Loafers",
        ],
        "price_min": 399,
        "price_max": 6999,
    },
    {
        "id": "kitchenware",
        "name_en": "Kitchenware & Cookware",
        "name_ta": "சமையலறை பாத்திரங்கள்",
        "subcategories": [
            "Cast Iron Kadai",
            "Pressure Cookers",
            "Stainless Steel Vessels",
            "Air Fryers",
            "Spice Jars",
        ],
        "price_min": 249,
        "price_max": 8999,
    },
    {
        "id": "home_decor",
        "name_en": "Home Decor & Furnishing",
        "name_ta": "வீட்டு அலங்காரப் பொருட்கள்",
        "subcategories": ["Bedsheets", "Wall Hangings", "Brass Lamps", "Cushion Covers", "Curtains"],
        "price_min": 199,
        "price_max": 4999,
    },
    {
        "id": "electronics_accessories",
        "name_en": "Electronics & Audio",
        "name_ta": "மின்னணு மற்றும் ஆடியோ சாதனங்கள்",
        "subcategories": [
            "Headphones",
            "Bluetooth Speakers",
            "Mechanical Keyboards",
            "Smart Watches",
            "Power Banks",
        ],
        "price_min": 499,
        "price_max": 14999,
    },
    {
        "id": "mobile_accessories",
        "name_en": "Mobile Accessories",
        "name_ta": "மொபைல் பாகங்கள்",
        "subcategories": ["Fast Chargers", "Screen Protectors", "Phone Cases", "OTG Cables", "Car Mounts"],
        "price_min": 99,
        "price_max": 1999,
    },
    {
        "id": "kids_toys",
        "name_en": "Toys & Games",
        "name_ta": "குழந்தைகள் பொம்மைகள்",
        "subcategories": [
            "Wooden Educational Toys",
            "Board Games",
            "Soft Dolls",
            "Puzzle Sets",
            "Action Figures",
        ],
        "price_min": 149,
        "price_max": 3499,
    },
    {
        "id": "stationery",
        "name_en": "Stationery & Books",
        "name_ta": "எழுதுபொருட்கள் மற்றும் நோட்டுகள்",
        "subcategories": ["Notebooks", "Fountain Pens", "Art Supplies", "Office Organizers", "Desk Planners"],
        "price_min": 49,
        "price_max": 1499,
    },
    {
        "id": "personal_care",
        "name_en": "Personal Care & Herbal",
        "name_ta": "சுய பராமரிப்பு மற்றும் மூலிகைப் பொருட்கள்",
        "subcategories": [
            "Herbal Hair Oil",
            "Natural Soaps",
            "Ayurvedic Face Creams",
            "Body Scrubs",
            "Comb Sets",
        ],
        "price_min": 99,
        "price_max": 2499,
    },
    {
        "id": "pooja_items",
        "name_en": "Pooja & Spiritual Items",
        "name_ta": "பூஜை மற்றும் ஆன்மீகப் பொருட்கள்",
        "subcategories": [
            "Brass Diyas",
            "Incense Sticks",
            "Kumkum & Sandalwood",
            "Bell & Panchapatra",
            "Camphor & Oils",
        ],
        "price_min": 79,
        "price_max": 3999,
    },
    {
        "id": "packaged_groceries",
        "name_en": "Packaged Groceries & Snacks",
        "name_ta": "பாரம்பரிய பலகாரங்கள் மற்றும் மளிகை",
        "subcategories": [
            "Cold Pressed Oils",
            "Millet Snacks",
            "Filter Coffee Powder",
            "Palm Jaggery",
            "Spice Powders",
        ],
        "price_min": 89,
        "price_max": 1999,
    },
]

FICTIONAL_BRANDS = [
    "KaveriCraft",
    "ThanjavurSilks",
    "MaduraiWeaves",
    "CholaStyle",
    "KonguGold",
    "AnnamFoods",
    "MeenakshiPooja",
    "CoromandelAudio",
    "PondyLiving",
    "KurinjiBoutique",
    "NilgiriHerbs",
    "ChettinadKitchen",
    "SundaramStationery",
    "VaigaiWear",
    "PallavaTech",
]

# Exact seeded items from Phase 1 orders to ensure 100% catalog consistency
PHASE1_CANONICAL_ITEMS = [
    {
        "sku": "SKU-CAN-0001",
        "name_en": "Cotton Kurti Set",
        "name_ta": "பருத்தி குர்தி செட்",
        "category": "sarees_ethnic",
        "subcategory": "Kurtis",
        "price": 1499.00,
        "stock_qty": 35,
        "rating": 4.5,
        "description_en": "Pure South Indian breathable cotton kurti set with printed dupatta and matching ankle-length pants. Ideal for daily office wear and festive occasions with fast colour guarantee.",
        "description_ta": "தூய பருத்தி துணியால் நெய்யப்பட்ட அழகான குர்தி செட் மற்றும் துப்பட்டா. அலுவலகம் மற்றும் அன்றாட பயன்பாட்டிற்கு ஏற்றது, வண்ணம் மங்காது.",
    },
    {
        "sku": "SKU-CAN-0002",
        "name_en": "Wireless Noise-Cancelling Headphones",
        "name_ta": "வயர்லெஸ் நாய்ஸ் கேன்சலிங் ஹெட்ஃபோன்",
        "category": "electronics_accessories",
        "subcategory": "Headphones",
        "price": 3499.00,
        "stock_qty": 18,
        "rating": 4.7,
        "description_en": "Over-ear active noise cancelling Bluetooth headphones with 40-hour battery life and deep bass tuning. Equipped with ultra-soft memory foam ear cushions and built-in mic.",
        "description_ta": "40 மணி நேர பேட்டரி ஆயுள் கொண்ட புளூடூத் நாய்ஸ் கேன்சலிங் ஹெட்ஃபோன். மிகச்சிறந்த பாஸ் ஒலி மற்றும் மென்மையான குஷன் கொண்டது.",
    },
    {
        "sku": "SKU-CAN-0003",
        "name_en": "Ceramic Coffee Mug Set",
        "name_ta": "பீங்கான் காபி கப் செட்",
        "category": "kitchenware",
        "subcategory": "Spice Jars",
        "price": 899.00,
        "stock_qty": 42,
        "rating": 4.2,
        "description_en": "Handcrafted set of 6 glazed ceramic coffee mugs with comfortable ergonomic handles. Microwave, oven, and dishwasher safe, featuring traditional matte earthen finishes.",
        "description_ta": "பாரம்பரிய கைவினைத் திறனில் செய்யப்பட்ட 6 பீங்கான் காபி குவளைகள் கொண்ட செட். மைக்ரோவேவ் மற்றும் பாத்திரம் கழுவும் இயந்திரத்தில் பயன்படுத்த பாதுகாப்பானது.",
    },
    {
        "sku": "SKU-CAN-0004",
        "name_en": "Running Shoes Blue Size 9",
        "name_ta": "நீல நிற ஓட்டப் பயிற்சி காலணிகள் அளவு 9",
        "category": "footwear",
        "subcategory": "Running Shoes",
        "price": 1299.00,
        "stock_qty": 20,
        "rating": 4.3,
        "description_en": "Lightweight breathable mesh running shoes in navy blue, size 9, with shock-absorbing EVA sole. Engineered for morning jogging and sports activities with non-slip grip.",
        "description_ta": "அளவு 9 கொண்ட நீல நிற ஓட்டப் பயிற்சி காலணிகள். மிகக்குறைந்த எடை, காற்று புகும் மெஷ் மற்றும் வழுக்காத ரப்பர் சோல் கொண்டது.",
    },
    {
        "sku": "SKU-CAN-0005",
        "name_en": "Smart Fitness Watch Pro",
        "name_ta": "ஸ்மார்ட் உடற்பயிற்சி வாட்ச் புரோ",
        "category": "electronics_accessories",
        "subcategory": "Smart Watches",
        "price": 4500.00,
        "stock_qty": 12,
        "rating": 4.6,
        "description_en": "1.78-inch AMOLED display smartwatch with heart rate, SpO2, sleep tracking, and 120 sports modes. Features IP68 water resistance and Bluetooth calling with 7-day battery life.",
        "description_ta": "அமோலெட் திரை கொண்ட ஸ்மார்ட் வாட்ச். இதயத் துடிப்பு, இரத்த ஆக்சிஜன் கண்காணிப்பு, 7 நாட்கள் பேட்டரி மற்றும் நீர் எதிர்ப்பு வசதி கொண்டது.",
    },
    {
        "sku": "SKU-CAN-0006",
        "name_en": "Mechanical Gaming Keyboard",
        "name_ta": "மெக்கானிக்கல் கேமிங் கீபோர்டு",
        "category": "electronics_accessories",
        "subcategory": "Mechanical Keyboards",
        "price": 2199.00,
        "stock_qty": 25,
        "rating": 4.8,
        "description_en": "Tenkeyless mechanical gaming keyboard with responsive blue switches and dynamic RGB backlighting. Braided USB-C detachable cable and solid metal top plate for durability.",
        "description_ta": "ஆர்பிஜி விளக்குகள் மற்றும் நீல நிற மெக்கானிக்கல் சுவிட்சுகள் கொண்ட கணினி விசைப்பலகை. நீடித்த உலோக வடிவமைப்பு மற்றும் வேகமான செயல்பாடு.",
    },
    {
        "sku": "SKU-CAN-0007",
        "name_en": "Stainless Steel Water Bottle 1L",
        "name_ta": "துருப்பிடிக்காத எஃகு தண்ணீர் பாட்டில் 1 லிட்டர்",
        "category": "kitchenware",
        "subcategory": "Stainless Steel Vessels",
        "price": 850.00,
        "stock_qty": 60,
        "rating": 4.6,
        "description_en": "Double-walled vacuum insulated 1000ml stainless steel bottle keeping beverages cold for 24 hours or hot for 12 hours. Rust-free food grade 304 steel with leak-proof cap.",
        "description_ta": "உயர்தர 304 ஸ்டெயின்லெஸ் ஸ்டீல் 1 லிட்டர் தண்ணீர் பாட்டில். 24 மணி நேரம் குளிராகவும் 12 மணி நேரம் சூடாகவும் வைத்திருக்கும் தெர்மோஸ் பாட்டில்.",
    },
    {
        "sku": "SKU-CAN-0008",
        "name_en": "Bluetooth Portable Speaker",
        "name_ta": "போர்ட்டபிள் புளூடூத் ஸ்பீக்கர்",
        "category": "electronics_accessories",
        "subcategory": "Bluetooth Speakers",
        "price": 1599.00,
        "stock_qty": 28,
        "rating": 4.4,
        "description_en": "16W punchy stereo portable Bluetooth speaker with dual passive radiators and 12 hours playback. Compact cylindrical design with tough fabric grill and lanyard strap.",
        "description_ta": "16 வாட்ஸ் ஒலி வெளியீடு மற்றும் 12 மணி நேர பிளேபேக் தரும் போர்ட்டபிள் புளூடூத் ஸ்பீக்கர். கச்சிதமான மற்றும் பயணத்திற்கு ஏற்ற வடிவமைப்பு.",
    },
    {
        "sku": "SKU-CAN-0009",
        "name_en": "Handcrafted Leather Wallet",
        "name_ta": "கைவினை தோல் பர்ஸ்",
        "category": "mens_wear",
        "subcategory": "Trousers",
        "price": 1100.00,
        "stock_qty": 0,  # Out of stock in catalog
        "rating": 4.5,
        "description_en": "Genuine full-grain top leather bi-fold wallet with 8 card slots and dual currency compartments. Features integrated RFID blocking security layer in dark tan finish.",
        "description_ta": "உண்மையான சுத்தமான தோலில் செய்யப்பட்ட ஆண்கள் பர்ஸ். 8 கார்டு ஸ்லாட்டுகள் மற்றும் ஆர்எஃப்ஐடி திருட்டு பாதுகாப்பு அடுக்கு கொண்டது.",
    },
    {
        "sku": "SKU-CAN-0010",
        "name_en": "Air Fryer 4.2L",
        "name_ta": "ஏர் பிரையர் 4.2 லிட்டர்",
        "category": "kitchenware",
        "subcategory": "Air Fryers",
        "price": 2999.00,
        "stock_qty": 15,
        "rating": 4.6,
        "description_en": "Rapid 360-degree air circulation fryer with 4.2-litre non-stick basket using up to 90 percent less oil. Equipped with 8 one-touch preset cooking modes and auto shut-off.",
        "description_ta": "4.2 லிட்டர் கொள்ளளவு கொண்ட எண்ணெய் இல்லா ஏர் பிரையர். குறைந்த மின்சாரத்தில் ஆரோக்கியமான பொரியல் மற்றும் தின்பண்டங்கள் தயாரிக்க சிறந்தது.",
    },
    {
        "sku": "SKU-CAN-0011",
        "name_en": "Men Formal Blazer",
        "name_ta": "ஆண்கள் ஃபார்மல் பிளேசர்",
        "category": "mens_wear",
        "subcategory": "Blazers",
        "price": 1800.00,
        "stock_qty": 14,
        "rating": 4.3,
        "description_en": "Single-breasted slim-fit men's formal blazer in navy blue with notched lapels and satin interior lining. Designed for corporate interviews, formal dinners, and wedding receptions.",
        "description_ta": "நேர்த்தியான தையல் கொண்ட ஆண்கள் ஃபார்மல் பிளேசர். நேவி ப்ளூ நிறத்தில் உயர்தர துணியில் தயாரிக்கப்பட்டது.",
    },
    {
        "sku": "SKU-CAN-0012",
        "name_en": "Silk Sarees Handloom",
        "name_ta": "கைத்தறி பட்டுப் புடவை",
        "category": "sarees_ethnic",
        "subcategory": "Kanchipuram Silk",
        "price": 2000.00,
        "stock_qty": 22,
        "rating": 4.8,
        "description_en": "Traditional handloom soft silk saree featuring authentic gold zari temple border and contrasting rich pallu. Comes with unstitched matching blouse fabric for festive wear.",
        "description_ta": "பாரம்பரிய கைத்தறி பட்டுப் புடவை. தங்க ஜரிகை கொண்ட கோவில் பார்டர் மற்றும் முந்தானையுடன் கூடிய நேர்த்தியான வடிவமைப்பு.",
    },
]

# Vocabulary components for realistic deterministic generation
ADJECTIVES_EN = [
    "Traditional",
    "Handcrafted",
    "Premium",
    "Pure",
    "Organic",
    "Authentic",
    "Ergonomic",
    "Luxury",
    "Handwoven",
    "Classic",
    "Deluxe",
    "Artisanal",
]
ADJECTIVES_TA = [
    "பாரம்பரிய",
    "கைவினை",
    "உயர்தர",
    "தூய",
    "இயற்கை",
    "அசல்",
    "சிறந்த",
    "ஆடம்பர",
    "கைத்தறி",
    "கிளாசிக்",
    "நேர்த்தியான",
    "சுத்தமான",
]

MATERIALS_EN = [
    "Cotton",
    "Silk",
    "Brass",
    "Cast Iron",
    "Stainless Steel",
    "Clay",
    "Teak Wood",
    "Jute",
    "Linen",
    "Copper",
    "Bamboo",
]
MATERIALS_TA = [
    "பருத்தி",
    "பட்டு",
    "பித்தளை",
    "வார்ப்பிரும்பு",
    "துருப்பிடிக்காத எஃகு",
    "மண்",
    "தேக்கு மரம்",
    "சணல்",
    "லினன்",
    "செம்பு",
    "மூங்கில்",
]


def generate_catalog(total_count: int = 2000) -> list[dict]:
    random.seed(SEED)
    products = list(PHASE1_CANONICAL_ITEMS)
    generated_count = len(products)
    sku_counter = 100

    items_per_category = (total_count - generated_count) // len(CATEGORIES) + 2

    for cat in CATEGORIES:
        cat_id = cat["id"]
        subcats = cat["subcategories"]

        for _ in range(items_per_category):
            if len(products) >= total_count:
                break

            sku_counter += 1
            brand = random.choice(FICTIONAL_BRANDS)
            subcat = random.choice(subcats)
            adj_idx = random.randint(0, len(ADJECTIVES_EN) - 1)
            adj_en, adj_ta = ADJECTIVES_EN[adj_idx], ADJECTIVES_TA[adj_idx]

            mat_idx = random.randint(0, len(MATERIALS_EN) - 1)
            mat_en, mat_ta = MATERIALS_EN[mat_idx], MATERIALS_TA[mat_idx]

            sku = f"SKU-{cat_id[:3].upper()}-{sku_counter:05d}"
            name_en = f"{brand} {adj_en} {subcat}"
            name_ta = f"{brand} {adj_ta} {subcat}"

            # Create price distribution with many items around 1500 to 2500 (refund threshold range)
            r = random.random()
            if r < 0.35:
                # 35% around refund threshold 1400 - 2600
                price = float(random.randint(1400, 2600))
            elif r < 0.65:
                price = float(random.randint(cat["price_min"], min(cat["price_max"], 4000)))
            else:
                price = float(random.randint(cat["price_min"], cat["price_max"]))

            # Stock quantity: 12% chance of 0 (out of stock)
            stock_qty = 0 if random.random() < 0.12 else random.randint(3, 120)
            rating = round(random.uniform(3.5, 4.9), 1)

            desc_en = (
                f"{brand} {adj_en} {subcat} crafted from high quality {mat_en}. "
                f"Features authentic finish and dependable durability. "
                f"Packaged securely with manufacturer warranty and satisfaction assurance."
            )
            desc_ta = (
                f"உயர்தர {mat_ta} பொருளால் வடிவமைக்கப்பட்ட {brand} {adj_ta} {subcat}. "
                f"நீடித்த உழைப்பு மற்றும் பாரம்பரிய அழகு தரும் சிறப்பான தயாரிப்பு. "
                f"தரமான பேக்கிங் மற்றும் உற்பத்தியாளர் உத்தரவாதத்துடன் வழங்கப்படுகிறது."
            )

            products.append(
                {
                    "sku": sku,
                    "name_en": name_en,
                    "name_ta": name_ta,
                    "category": cat_id,
                    "subcategory": subcat,
                    "price": price,
                    "stock_qty": stock_qty,
                    "rating": rating,
                    "description_en": desc_en,
                    "description_ta": desc_ta,
                }
            )

    return products[:total_count]


def main():
    parser = argparse.ArgumentParser(description="Generate realistic e-commerce products dataset")
    parser.add_argument("--count", type=int, default=2000, help="Total products to generate")
    parser.add_argument("--out", type=str, default="data/products.json", help="Output JSON path")
    parser.add_argument("--use-llm", action="store_true", help="Enrich descriptions using LLM (optional)")
    args = parser.parse_args()

    out_path = Path(__file__).resolve().parent.parent / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.count} products (Seed: {SEED})...")
    catalog = generate_catalog(args.count)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(catalog)} products written to {out_path}")
    print(f"Categories covered: {len(CATEGORIES)}")
    out_of_stock = sum(1 for p in catalog if p["stock_qty"] == 0)
    print(f"Out of stock products: {out_of_stock} ({out_of_stock / len(catalog) * 100:.1f}%)")
    around_threshold = sum(1 for p in catalog if 1500 <= p["price"] <= 2500)
    print(f"Products in ₹1,500-₹2,500 range: {around_threshold}")


if __name__ == "__main__":
    main()
