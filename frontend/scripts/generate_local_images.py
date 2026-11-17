import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "public" / "images"

IMAGES = {
    # 1. Hero Showcase Images
    "hero/saree.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="silkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#991b1b" />
      <stop offset="50%" stop-color="#dc2626" />
      <stop offset="100%" stop-color="#7f1d1d" />
    </linearGradient>
    <linearGradient id="goldZari" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f59e0b" />
      <stop offset="50%" stop-color="#fef08a" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#fdf2f8" rx="12" />
  <!-- Fabric drapes -->
  <path d="M40 30 Q120 70 200 40 Q260 20 280 60 L260 170 Q180 190 100 160 Q40 140 30 110 Z" fill="url(#silkGrad)" />
  <path d="M60 45 Q130 80 190 55 L175 165 Q115 180 60 155 Z" fill="#b91c1c" opacity="0.6" />
  <!-- Golden Zari Border -->
  <path d="M35 110 Q40 140 100 160 Q180 190 260 170 L265 180 Q185 200 95 170 Q30 150 25 115 Z" fill="url(#goldZari)" />
  <!-- Intricate Zari Patterns -->
  <line x1="80" y1="60" x2="120" y2="160" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.7" />
  <line x1="110" y1="55" x2="150" y2="165" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.7" />
  <line x1="140" y1="50" x2="180" y2="160" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.7" />
  <!-- Silk Sheen Highlight -->
  <ellipse cx="140" cy="90" rx="40" ry="20" fill="#ffffff" opacity="0.25" transform="rotate(-15 140 90)" />
</svg>""",

    "hero/cookware.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <radialGradient id="stoneBody" cx="40%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#52525b" />
      <stop offset="60%" stop-color="#27272a" />
      <stop offset="100%" stop-color="#18181b" />
    </radialGradient>
    <linearGradient id="brassHandle" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a" />
      <stop offset="50%" stop-color="#d97706" />
      <stop offset="100%" stop-color="#92400e" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#f4f4f5" rx="12" />
  <!-- Shadow -->
  <ellipse cx="150" cy="165" rx="90" ry="16" fill="#000000" opacity="0.2" />
  <!-- Brass Handles -->
  <path d="M45 90 C30 90 25 110 40 120 C50 125 55 115 50 100" fill="none" stroke="url(#brassHandle)" stroke-width="7" stroke-linecap="round" />
  <path d="M255 90 C270 90 275 110 260 120 C250 125 245 115 250 100" fill="none" stroke="url(#brassHandle)" stroke-width="7" stroke-linecap="round" />
  <!-- Pot Body -->
  <path d="M50 85 C50 155 80 165 150 165 C220 165 250 155 250 85 Z" fill="url(#stoneBody)" />
  <!-- Pot Rim -->
  <ellipse cx="150" cy="85" rx="100" ry="24" fill="#3f3f46" stroke="#27272a" stroke-width="2" />
  <ellipse cx="150" cy="85" rx="88" ry="18" fill="#18181b" />
  <!-- Subtle steam wisps -->
  <path d="M130 65 Q135 45 145 35 Q150 25 140 15" fill="none" stroke="#a1a1aa" stroke-width="2" opacity="0.4" stroke-linecap="round" />
  <path d="M165 60 Q175 40 168 30 Q160 20 170 10" fill="none" stroke="#a1a1aa" stroke-width="2" opacity="0.4" stroke-linecap="round" />
</svg>""",

    "hero/coffee.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="brassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a" />
      <stop offset="40%" stop-color="#eab308" />
      <stop offset="80%" stop-color="#ca8a04" />
      <stop offset="100%" stop-color="#854d0e" />
    </linearGradient>
    <linearGradient id="crema" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fed7aa" />
      <stop offset="70%" stop-color="#c2410c" />
      <stop offset="100%" stop-color="#431407" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#fffbeb" rx="12" />
  <ellipse cx="150" cy="170" rx="80" ry="14" fill="#000000" opacity="0.15" />
  <!-- Davarah (Wide bottom cup) -->
  <path d="M75 125 L95 162 Q150 172 205 162 L225 125 Z" fill="url(#brassGrad)" />
  <ellipse cx="150" cy="125" rx="75" ry="18" fill="#ca8a04" />
  <!-- Tumbler (Tall glass) -->
  <path d="M110 70 L120 145 Q150 152 180 145 L190 70 Z" fill="url(#brassGrad)" />
  <ellipse cx="150" cy="70" rx="40" ry="12" fill="url(#brassGrad)" />
  <!-- Coffee Crema Foam -->
  <ellipse cx="150" cy="70" rx="36" ry="10" fill="url(#crema)" />
  <ellipse cx="145" cy="69" rx="15" ry="4" fill="#fef3c7" opacity="0.6" />
  <!-- Steam -->
  <path d="M142 50 Q138 35 146 25" fill="none" stroke="#ca8a04" stroke-width="2" opacity="0.5" stroke-linecap="round" />
  <path d="M156 46 Q162 30 154 20" fill="none" stroke="#ca8a04" stroke-width="2" opacity="0.5" stroke-linecap="round" />
</svg>""",

    "hero/spices.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <rect width="300" height="200" fill="#fff7ed" rx="12" />
  <ellipse cx="150" cy="165" rx="85" ry="16" fill="#000000" opacity="0.15" />
  <!-- Wooden Bowl -->
  <path d="M65 95 C65 155 100 165 150 165 C200 165 235 155 235 95 Z" fill="#78350f" />
  <ellipse cx="150" cy="95" rx="85" ry="24" fill="#92400e" />
  <!-- Turmeric & Spices mound -->
  <ellipse cx="150" cy="95" rx="76" ry="20" fill="#f59e0b" />
  <!-- Red Chilies -->
  <path d="M100 95 Q130 70 170 85 Q135 105 100 95 Z" fill="#dc2626" />
  <path d="M170 85 L180 82" stroke="#15803d" stroke-width="3" stroke-linecap="round" />
  <!-- Star Anise -->
  <g transform="translate(130, 85) scale(0.7)" fill="#451a03">
    <ellipse cx="20" cy="20" rx="6" ry="18" />
    <ellipse cx="20" cy="20" rx="18" ry="6" />
    <ellipse cx="20" cy="20" rx="6" ry="18" transform="rotate(45 20 20)" />
    <ellipse cx="20" cy="20" rx="6" ry="18" transform="rotate(-45 20 20)" />
    <circle cx="20" cy="20" r="4" fill="#78350f" />
  </g>
  <!-- Cardamom pods -->
  <ellipse cx="185" cy="100" rx="8" ry="4" fill="#65a30d" transform="rotate(25 185 100)" />
  <ellipse cx="115" cy="105" rx="7" ry="4" fill="#65a30d" transform="rotate(-20 115 105)" />
</svg>""",

    # 2. Categories Circular Icons
    "categories/textiles.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fce4ec" />
  <path d="M22 25 Q50 45 78 28 L72 75 Q48 85 24 72 Z" fill="#be185d" />
  <path d="M24 72 Q48 85 72 75 L73 80 Q48 90 23 77 Z" fill="#f59e0b" />
  <line x1="38" y1="36" x2="40" y2="76" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="2,2" />
  <line x1="52" y1="38" x2="54" y2="79" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="2,2" />
</svg>""",

    "categories/cookware.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#e1f5fe" />
  <path d="M20 45 C20 72 32 78 50 78 C68 78 80 72 80 45 Z" fill="#27272a" />
  <ellipse cx="50" cy="45" rx="30" ry="8" fill="#3f3f46" />
  <ellipse cx="50" cy="45" rx="26" ry="6" fill="#18181b" />
  <path d="M16 48 C12 48 10 54 16 57 C20 59 22 55 20 49" fill="none" stroke="#d97706" stroke-width="2.5" />
  <path d="M84 48 C88 48 90 54 84 57 C80 59 78 55 80 49" fill="none" stroke="#d97706" stroke-width="2.5" />
</svg>""",

    "categories/spices.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#ffe0b2" />
  <path d="M25 50 C25 74 35 78 50 78 C65 78 75 74 75 50 Z" fill="#78350f" />
  <ellipse cx="50" cy="50" rx="25" ry="8" fill="#f59e0b" />
  <path d="M35 50 Q50 36 68 44 Q50 56 35 50 Z" fill="#dc2626" />
  <circle cx="44" cy="48" r="2.5" fill="#65a30d" />
  <circle cx="58" cy="49" r="2" fill="#451a03" />
</svg>""",

    "categories/groceries.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#e8f5e9" />
  <ellipse cx="50" cy="68" rx="26" ry="10" fill="#047857" />
  <path d="M26 62 Q50 40 74 62 Q50 75 26 62 Z" fill="#34d399" />
  <!-- Grain stalks -->
  <path d="M50 64 L50 22" stroke="#065f46" stroke-width="2" />
  <ellipse cx="46" cy="28" rx="3" ry="5" fill="#fef08a" transform="rotate(-30 46 28)" />
  <ellipse cx="54" cy="28" rx="3" ry="5" fill="#fef08a" transform="rotate(30 54 28)" />
  <ellipse cx="45" cy="38" rx="3" ry="5" fill="#fef08a" transform="rotate(-30 45 38)" />
  <ellipse cx="55" cy="38" rx="3" ry="5" fill="#fef08a" transform="rotate(30 55 38)" />
</svg>""",

    "categories/coffee.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fff3e0" />
  <path d="M26 64 L34 78 Q50 82 66 78 L74 64 Z" fill="#ca8a04" />
  <ellipse cx="50" cy="64" rx="24" ry="6" fill="#ca8a04" />
  <path d="M36 38 L40 70 Q50 73 60 70 L64 38 Z" fill="#eab308" />
  <ellipse cx="50" cy="38" rx="14" ry="5" fill="#451a03" />
  <ellipse cx="48" cy="37" rx="11" ry="3.5" fill="#c2410c" />
  <path d="M47 30 Q45 22 50 16" fill="none" stroke="#ca8a04" stroke-width="1.5" stroke-linecap="round" />
</svg>""",

    "categories/sweets.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fff8e1" />
  <ellipse cx="50" cy="65" rx="30" ry="10" fill="#cbd5e1" opacity="0.6" />
  <!-- Mysore pak & laddus -->
  <rect x="28" y="44" width="22" height="18" rx="2" fill="#d97706" transform="rotate(-10 39 53)" />
  <circle cx="62" cy="48" r="10" fill="#f59e0b" />
  <circle cx="52" cy="55" r="9" fill="#fbbf24" />
  <circle cx="62" cy="46" r="1.5" fill="#dc2626" />
</svg>""",

    "categories/crafts.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f3e5f5" />
  <path d="M35 30 L65 30 L60 48 C60 62 68 66 68 76 C68 80 32 80 32 76 C32 66 40 62 40 48 Z" fill="#9333ea" />
  <ellipse cx="50" cy="30" rx="15" ry="4" fill="#c084fc" />
  <ellipse cx="50" cy="56" rx="14" ry="4" fill="#7e22ce" />
  <circle cx="50" cy="66" r="3" fill="#fef08a" />
</svg>""",

    "categories/all.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f1f5f9" />
  <g transform="translate(28, 28)" fill="#0f382c">
    <rect x="2" y="2" width="18" height="18" rx="4" />
    <rect x="24" y="2" width="18" height="18" rx="4" fill="#10b981" />
    <rect x="2" y="24" width="18" height="18" rx="4" fill="#f59e0b" />
    <rect x="24" y="24" width="18" height="18" rx="4" fill="#0284c7" />
  </g>
</svg>""",

    # 3. Promo Banner Images
    "promos/handloom.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <defs>
    <linearGradient id="pSaree" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#be185d" />
      <stop offset="100%" stop-color="#831843" />
    </linearGradient>
  </defs>
  <rect width="200" height="160" fill="none" />
  <!-- Folded Saree with Zari -->
  <path d="M30 35 L170 20 L160 130 L20 145 Z" fill="url(#pSaree)" rx="8" />
  <path d="M20 135 L160 120 L163 135 L23 150 Z" fill="#f59e0b" />
  <path d="M30 35 L170 20 L168 35 L28 50 Z" fill="#fef08a" opacity="0.8" />
  <line x1="50" y1="48" x2="42" y2="135" stroke="#fef08a" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
  <line x1="85" y1="45" x2="77" y2="132" stroke="#fef08a" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
  <line x1="120" y1="42" x2="112" y2="129" stroke="#fef08a" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
</svg>""",

    "promos/cookware.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <rect width="200" height="160" fill="none" />
  <ellipse cx="100" cy="135" rx="70" ry="12" fill="#000000" opacity="0.15" />
  <path d="M30 65 C30 125 55 135 100 135 C145 135 170 125 170 65 Z" fill="#27272a" />
  <ellipse cx="100" cy="65" rx="70" ry="18" fill="#3f3f46" />
  <ellipse cx="100" cy="65" rx="60" ry="14" fill="#18181b" />
  <!-- Handles -->
  <path d="M22 68 C12 68 10 78 20 84 C26 86 28 80 26 72" fill="none" stroke="#d97706" stroke-width="5" stroke-linecap="round" />
  <path d="M178 68 C188 68 190 78 180 84 C174 86 172 80 174 72" fill="none" stroke="#d97706" stroke-width="5" stroke-linecap="round" />
</svg>""",

    "promos/spices.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <rect width="200" height="160" fill="none" />
  <ellipse cx="100" cy="135" rx="65" ry="12" fill="#000000" opacity="0.12" />
  <path d="M38 75 C38 125 60 135 100 135 C140 135 162 125 162 75 Z" fill="#78350f" />
  <ellipse cx="100" cy="75" rx="62" ry="18" fill="#92400e" />
  <ellipse cx="100" cy="75" rx="55" ry="15" fill="#ea580c" />
  <!-- Red Chilies & Spices -->
  <path d="M60 75 Q90 52 130 65 Q95 85 60 75 Z" fill="#dc2626" />
  <circle cx="120" cy="74" r="5" fill="#facc15" />
  <circle cx="85" cy="78" r="4" fill="#65a30d" />
</svg>""",

    # 4. Customer Testimonial Portraits
    "testimonials/sarah.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fce7f3" />
  <!-- Hair back -->
  <circle cx="50" cy="46" r="28" fill="#451a03" />
  <!-- Face -->
  <circle cx="50" cy="48" r="20" fill="#fcd34d" />
  <!-- Hair style -->
  <path d="M28 42 C30 24 70 24 72 42 C64 34 56 34 50 36 C44 34 36 34 28 42 Z" fill="#451a03" />
  <!-- Eyes & Smile -->
  <circle cx="43" cy="46" r="2.5" fill="#1e293b" />
  <circle cx="57" cy="46" r="2.5" fill="#1e293b" />
  <path d="M44 55 Q50 60 56 55" fill="none" stroke="#b91c1c" stroke-width="2" stroke-linecap="round" />
  <!-- Blouse -->
  <path d="M30 84 C34 68 66 68 70 84 Z" fill="#0f382c" />
</svg>""",

    "testimonials/michael.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#e0f2fe" />
  <!-- Hair back -->
  <ellipse cx="50" cy="38" rx="22" ry="16" fill="#1e293b" />
  <!-- Face -->
  <circle cx="50" cy="50" r="20" fill="#fed7aa" />
  <!-- Hair top -->
  <path d="M30 38 C32 24 68 24 70 38 Z" fill="#1e293b" />
  <!-- Eyes & Beard -->
  <circle cx="43" cy="48" r="2.5" fill="#1e293b" />
  <circle cx="57" cy="48" r="2.5" fill="#1e293b" />
  <path d="M42 56 Q50 63 58 56 Q55 64 50 65 Q45 64 42 56 Z" fill="#334155" />
  <!-- Shirt -->
  <path d="M28 85 C32 70 68 70 72 85 Z" fill="#0369a1" />
</svg>""",

    "testimonials/priya.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fef3c7" />
  <!-- Long dark hair -->
  <ellipse cx="50" cy="50" rx="28" ry="32" fill="#18181b" />
  <!-- Face -->
  <circle cx="50" cy="48" r="20" fill="#f59e0b" opacity="0.6" />
  <!-- Hair parting -->
  <path d="M28 44 C34 28 66 28 72 44 C65 38 56 36 50 38 C44 36 35 38 28 44 Z" fill="#18181b" />
  <!-- Bindi -->
  <circle cx="50" cy="42" r="1.5" fill="#dc2626" />
  <!-- Eyes & Smile -->
  <ellipse cx="43" cy="48" rx="2.5" ry="2" fill="#0f172a" />
  <ellipse cx="57" cy="48" rx="2.5" ry="2" fill="#0f172a" />
  <path d="M44 56 Q50 61 56 56" fill="none" stroke="#991b1b" stroke-width="2" stroke-linecap="round" />
  <!-- Kurti neck -->
  <path d="M30 85 C34 68 66 68 70 85 Z" fill="#be185d" />
</svg>""",
}

def main():
    for rel_path, svg_content in IMAGES.items():
        out_path = BASE_DIR / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        print(f"Generated {out_path}")

if __name__ == "__main__":
    main()
