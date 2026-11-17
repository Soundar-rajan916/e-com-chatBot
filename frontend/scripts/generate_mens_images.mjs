import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BASE_DIR = path.resolve(__dirname, '../public/images');

const IMAGES = {
  // 1. Hero Showcase Images (100% Men's Wear)
  'hero/dhoti.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="silkDhoti" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffbeb" />
      <stop offset="50%" stop-color="#fef3c7" />
      <stop offset="100%" stop-color="#fde68a" />
    </linearGradient>
    <linearGradient id="dhotiZari" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#d97706" />
      <stop offset="50%" stop-color="#fef08a" />
      <stop offset="100%" stop-color="#b45309" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#f8fafc" rx="12" />
  <!-- Folded Silk Dhoti with Gold Zari Border -->
  <path d="M45 40 L255 25 L245 165 L35 175 Z" fill="url(#silkDhoti)" />
  <path d="M35 155 L245 145 L247 165 L35 175 Z" fill="url(#dhotiZari)" />
  <path d="M45 40 L255 25 L253 45 L43 60 Z" fill="url(#dhotiZari)" opacity="0.85" />
  <!-- Pleats / Crease lines -->
  <line x1="85" y1="58" x2="77" y2="155" stroke="#d97706" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.6" />
  <line x1="130" y1="54" x2="122" y2="152" stroke="#d97706" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.6" />
  <line x1="175" y1="50" x2="167" y2="148" stroke="#d97706" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.6" />
  <line x1="215" y1="46" x2="207" y2="145" stroke="#d97706" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.6" />
  <!-- Kurta Collar outline overlay -->
  <path d="M125 18 L150 45 L175 18" fill="none" stroke="#b45309" stroke-width="2.5" stroke-linecap="round" />
</svg>`,

  'hero/blazer.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="blazerNavy" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="50%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#f1f5f9" rx="12" />
  <!-- Shadow -->
  <ellipse cx="150" cy="175" rx="85" ry="12" fill="#000000" opacity="0.15" />
  <!-- Blazer Body -->
  <path d="M85 30 L60 170 Q150 180 240 170 L215 30 Q150 40 85 30 Z" fill="url(#blazerNavy)" />
  <!-- Lapels -->
  <path d="M100 30 L135 110 L150 110 L120 30 Z" fill="#334155" />
  <path d="M200 30 L165 110 L150 110 L180 30 Z" fill="#334155" />
  <!-- Shirt & Tie peek -->
  <polygon points="120,30 150,75 180,30" fill="#ffffff" />
  <polygon points="144,45 156,45 153,95 147,95" fill="#991b1b" />
  <!-- Pocket Square -->
  <rect x="80" y="80" width="30" height="5" rx="1" fill="#475569" />
  <polygon points="86,80 94,65 102,80" fill="#ffffff" />
  <!-- Brass Buttons -->
  <circle cx="150" cy="125" r="4.5" fill="#f59e0b" stroke="#78350f" stroke-width="1" />
  <circle cx="150" cy="145" r="4.5" fill="#f59e0b" stroke="#78350f" stroke-width="1" />
</svg>`,

  'hero/shirt.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="linenBlue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#bae6fd" />
      <stop offset="60%" stop-color="#7dd3fc" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#f0f9ff" rx="12" />
  <ellipse cx="150" cy="172" rx="80" ry="12" fill="#000000" opacity="0.12" />
  <!-- Folded Shirt Body -->
  <rect x="75" y="45" width="150" height="120" rx="8" fill="url(#linenBlue)" stroke="#0284c7" stroke-width="1.5" />
  <!-- Placket -->
  <rect x="140" y="45" width="20" height="120" fill="#0284c7" opacity="0.2" />
  <!-- Mother of pearl buttons -->
  <circle cx="150" cy="65" r="3.5" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
  <circle cx="150" cy="95" r="3.5" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
  <circle cx="150" cy="125" r="3.5" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
  <circle cx="150" cy="150" r="3.5" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
  <!-- Collar -->
  <path d="M110 45 L150 72 L132 40 Z" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
  <path d="M190 45 L150 72 L168 40 Z" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
  <!-- Pocket -->
  <path d="M92 80 L122 80 L122 110 L107 118 L92 110 Z" fill="none" stroke="#0284c7" stroke-width="1.5" />
</svg>`,

  'hero/shoes.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="100%" height="100%">
  <defs>
    <linearGradient id="leatherBrown" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#92400e" />
      <stop offset="50%" stop-color="#78350f" />
      <stop offset="100%" stop-color="#451a03" />
    </linearGradient>
  </defs>
  <rect width="300" height="200" fill="#fafaf9" rx="12" />
  <ellipse cx="150" cy="165" rx="95" ry="14" fill="#000000" opacity="0.15" />
  <!-- Oxford Shoe Upper Profile -->
  <path d="M40 135 C50 115 85 95 130 90 C170 85 195 105 230 120 L260 135 C265 145 255 152 230 152 L45 152 C35 152 32 145 40 135 Z" fill="url(#leatherBrown)" />
  <!-- Sole & Heel -->
  <path d="M42 148 L260 148 C265 154 260 158 245 158 L45 158 Z" fill="#1c1917" />
  <rect x="42" y="152" width="40" height="10" rx="2" fill="#292524" />
  <!-- Wingtip Brogue stitching and laces -->
  <path d="M125 90 L150 115" stroke="#fef08a" stroke-width="1.5" stroke-dasharray="2,2" opacity="0.7" />
  <line x1="130" y1="102" x2="142" y2="98" stroke="#fef08a" stroke-width="2" />
  <line x1="134" y1="110" x2="146" y2="106" stroke="#fef08a" stroke-width="2" />
  <line x1="138" y1="118" x2="150" y2="114" stroke="#fef08a" stroke-width="2" />
  <!-- Gloss highlight -->
  <ellipse cx="215" cy="128" rx="22" ry="8" fill="#ffffff" opacity="0.2" transform="rotate(-5 215 128)" />
</svg>`,

  // 2. 8 Men's Wear Category Shortcuts
  'categories/formal_shirts.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#e0f2fe" />
  <!-- Shirt & Tie -->
  <path d="M26 36 L74 36 L70 82 L30 82 Z" fill="#0284c7" rx="3" />
  <polygon points="38,36 50,56 62,36" fill="#ffffff" />
  <polygon points="46,42 54,42 52,78 48,78" fill="#dc2626" />
  <polygon points="36,36 48,54 44,36" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
  <polygon points="64,36 52,54 56,36" fill="#ffffff" stroke="#0284c7" stroke-width="1" />
</svg>`,

  'categories/linen.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f0fdf4" />
  <!-- Relaxed linen shirt with open collar -->
  <path d="M26 38 L74 38 L68 82 L32 82 Z" fill="#16a34a" rx="4" />
  <path d="M36 38 L50 58 L42 38" fill="#ffffff" />
  <path d="M64 38 L50 58 L58 38" fill="#ffffff" />
  <circle cx="50" cy="66" r="2.5" fill="#ffffff" />
  <circle cx="50" cy="74" r="2.5" fill="#ffffff" />
</svg>`,

  'categories/dhotis.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fffbeb" />
  <!-- Folded Silk Dhoti with Gold Zari -->
  <path d="M24 28 L76 28 L72 78 L28 78 Z" fill="#fef3c7" />
  <rect x="28" y="70" width="44" height="8" fill="#f59e0b" />
  <rect x="24" y="28" width="52" height="6" fill="#f59e0b" />
  <line x1="42" y1="36" x2="42" y2="70" stroke="#d97706" stroke-width="1.5" stroke-dasharray="2,2" />
  <line x1="58" y1="36" x2="58" y2="70" stroke="#d97706" stroke-width="1.5" stroke-dasharray="2,2" />
</svg>`,

  'categories/trousers.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f8fafc" />
  <!-- Tailored Trousers -->
  <path d="M30 26 L70 26 L66 84 L52 84 L50 48 L48 84 L34 84 Z" fill="#334155" />
  <!-- Belt loops & waistband -->
  <rect x="30" y="26" width="40" height="6" fill="#1e293b" />
  <line x1="40" y1="32" x2="40" y2="84" stroke="#475569" stroke-width="1" />
  <line x1="60" y1="32" x2="60" y2="84" stroke="#475569" stroke-width="1" />
</svg>`,

  'categories/blazers.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f1f5f9" />
  <!-- Single-breasted blazer with lapels -->
  <path d="M25 32 L75 32 L68 82 L32 82 Z" fill="#0f172a" />
  <polygon points="36,32 50,62 64,32" fill="#ffffff" />
  <polygon points="46,40 54,40 52,68 48,68" fill="#d97706" />
  <path d="M28 32 L46 62 L50 62 L38 32 Z" fill="#334155" />
  <path d="M72 32 L54 62 L50 62 L62 32 Z" fill="#334155" />
  <circle cx="50" cy="72" r="2.5" fill="#f59e0b" />
</svg>`,

  'categories/polos.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fef2f2" />
  <!-- Polo Shirt -->
  <path d="M24 36 L76 36 L70 82 L30 82 Z" fill="#dc2626" rx="3" />
  <path d="M38 34 L50 50 L42 34 Z" fill="#ffffff" />
  <path d="M62 34 L50 50 L58 34 Z" fill="#ffffff" />
  <rect x="47" y="44" width="6" height="16" fill="#991b1b" />
  <circle cx="50" cy="48" r="1.5" fill="#ffffff" />
  <circle cx="50" cy="54" r="1.5" fill="#ffffff" />
</svg>`,

  'categories/footwear.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fff7ed" />
  <!-- Classic Leather Shoe -->
  <path d="M18 64 C25 50 45 42 65 42 C80 42 85 52 88 64 L88 72 L18 72 Z" fill="#78350f" />
  <rect x="18" y="70" width="70" height="5" rx="2" fill="#1c1917" />
  <rect x="18" y="72" width="18" height="5" fill="#292524" />
  <line x1="50" y1="46" x2="58" y2="46" stroke="#fef08a" stroke-width="1.5" />
  <line x1="52" y1="52" x2="60" y2="52" stroke="#fef08a" stroke-width="1.5" />
</svg>`,

  'categories/accessories.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#f5f3ff" />
  <!-- Leather Belt & Watch -->
  <rect x="20" y="42" width="60" height="16" rx="4" fill="#451a03" />
  <rect x="42" y="38" width="22" height="24" rx="3" fill="none" stroke="#f59e0b" stroke-width="3" />
  <line x1="53" y1="42" x2="53" y2="58" stroke="#f59e0b" stroke-width="3" />
</svg>`,

  // 3. Promo Banner Images (Men's Focus)
  'promos/wedding_silks.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <defs>
    <linearGradient id="pGoldZari" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef3c7" />
      <stop offset="100%" stop-color="#fde68a" />
    </linearGradient>
  </defs>
  <rect width="200" height="160" fill="none" />
  <!-- Traditional Pure Silk Dhoti & Angavastram -->
  <path d="M25 35 L175 22 L165 135 L15 145 Z" fill="url(#pGoldZari)" rx="6" />
  <path d="M15 135 L165 125 L167 140 L17 150 Z" fill="#d97706" />
  <path d="M25 35 L175 22 L173 35 L23 48 Z" fill="#f59e0b" />
  <line x1="50" y1="46" x2="42" y2="135" stroke="#d97706" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
  <line x1="85" y1="43" x2="77" y2="132" stroke="#d97706" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
  <line x1="120" y1="40" x2="112" y2="129" stroke="#d97706" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.6" stroke-width="1.5" />
</svg>`,

  'promos/summer_linen.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <rect width="200" height="160" fill="none" />
  <!-- Folded Linen Shirts Stack -->
  <rect x="35" y="75" width="130" height="65" rx="6" fill="#15803d" />
  <rect x="30" y="55" width="140" height="60" rx="6" fill="#0284c7" />
  <rect x="25" y="35" width="150" height="55" rx="6" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.5" />
  <!-- Top Shirt Collar -->
  <polygon points="80,35 100,58 120,35" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="1" />
  <circle cx="100" cy="70" r="3" fill="#64748b" />
</svg>`,

  'promos/leather_shoes.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160" width="100%" height="100%">
  <rect width="200" height="160" fill="none" />
  <ellipse cx="100" cy="140" rx="75" ry="12" fill="#000000" opacity="0.15" />
  <!-- Pair of Leather Shoes -->
  <path d="M25 110 C35 85 65 75 105 75 C145 75 160 92 175 110 L175 128 L25 128 Z" fill="#78350f" />
  <rect x="25" y="125" width="150" height="8" rx="2" fill="#1c1917" />
  <rect x="25" y="128" width="35" height="8" fill="#292524" />
  <line x1="85" y1="80" x2="105" y2="80" stroke="#fef08a" stroke-width="2" />
  <line x1="88" y1="90" x2="108" y2="90" stroke="#fef08a" stroke-width="2" />
  <line x1="90" y1="100" x2="110" y2="100" stroke="#fef08a" stroke-width="2" />
</svg>`,

  // 4. Testimonial Avatars
  'testimonials/karthik.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#fef3c7" />
  <ellipse cx="50" cy="38" rx="22" ry="18" fill="#18181b" />
  <circle cx="50" cy="50" r="20" fill="#fcd34d" />
  <path d="M30 38 C32 22 68 22 70 38 Z" fill="#18181b" />
  <circle cx="43" cy="48" r="2.5" fill="#1e293b" />
  <circle cx="57" cy="48" r="2.5" fill="#1e293b" />
  <path d="M43 56 Q50 63 57 56" fill="none" stroke="#78350f" stroke-width="2" stroke-linecap="round" />
  <!-- Silk Kurta with Gold Border -->
  <path d="M28 85 C32 68 68 68 72 85 Z" fill="#fffbeb" stroke="#f59e0b" stroke-width="2" />
</svg>`,

  'testimonials/arvind.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="50" fill="#e0f2fe" />
  <ellipse cx="50" cy="38" rx="22" ry="16" fill="#1e293b" />
  <circle cx="50" cy="50" r="20" fill="#fed7aa" />
  <path d="M30 38 C32 24 68 24 70 38 Z" fill="#1e293b" />
  <circle cx="43" cy="48" r="2.5" fill="#1e293b" />
  <circle cx="57" cy="48" r="2.5" fill="#1e293b" />
  <path d="M42 56 Q50 63 58 56 Q55 64 50 65 Q45 64 42 56 Z" fill="#334155" />
  <!-- Navy Blazer & Shirt -->
  <path d="M28 85 C32 70 68 70 72 85 Z" fill="#0f172a" />
  <polygon points="44,70 50,82 56,70" fill="#ffffff" />
</svg>`,
};

for (const [relPath, content] of Object.entries(IMAGES)) {
  const fullPath = path.join(BASE_DIR, relPath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, content.trim(), 'utf-8');
  console.log(`Generated ${relPath}`);
}
console.log("All Men's Wear local SVG images generated successfully.");
