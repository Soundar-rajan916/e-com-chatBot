import fs from 'fs';
import path from 'path';

const productsPath = path.resolve('backend/data/products.json');
const products = JSON.parse(fs.readFileSync(productsPath, 'utf8'));

// Curated naming pools for concise, distinct names per category

const namesPool = {
  formal_shirts: [
    { en: "Classic Oxford Shirt", ta: "ஆக்ஸ்போர்டு சட்டை" },
    { en: "White Poplin Dress Shirt", ta: "வெள்ளை பாப்லின் சட்டை" },
    { en: "Sky Blue Twill Shirt", ta: "வான நீல ட்வில் சட்டை" },
    { en: "French Cuff Formal Shirt", ta: "பிரெஞ்ச் கஃப் பார்மல் சட்டை" },
    { en: "Cutaway Collar Shirt", ta: "கட்டவே காலர் சட்டை" },
    { en: "Giza Cotton Dress Shirt", ta: "கீசா காட்டன் சட்டை" },
    { en: "Herringbone Weave Shirt", ta: "ஹெர்ரிங்போன் சட்டை" },
    { en: "Spread Collar Formal Shirt", ta: "ஸ்ப்ரெட் காலர் சட்டை" },
    { en: "Micro Check Dress Shirt", ta: "மைக்ரோ செக் சட்டை" },
    { en: "Navy Executive Shirt", ta: "நேவி பார்மல் சட்டை" },
    { en: "Pinstripe Business Shirt", ta: "வரி அமைந்த பார்மல் சட்டை" },
    { en: "Textured Dobby Shirt", ta: "டாபி நெசவு சட்டை" },
    { en: "Wrinkle-Free Formal Shirt", ta: "சுருக்கமில்லா பார்மல் சட்டை" },
    { en: "Pinpoint Cotton Shirt", ta: "பின்பாயிண்ட் காட்டன் சட்டை" },
    { en: "Tailored Royal Oxford", ta: "ராயல் ஆக்ஸ்போர்டு சட்டை" },
    { en: "Lilac Business Shirt", ta: "இளஞ்சிவப்பு பார்மல் சட்டை" },
    { en: "Slim Fit White Shirt", ta: "ஸ்லிம் ஃபிட் வெள்ளை சட்டை" },
    { en: "Charcoal Twill Shirt", ta: "சாம்பல் நிற ட்வில் சட்டை" },
    { en: "Fine Stripe Dress Shirt", ta: "மெல்லிய கோடு சட்டை" },
    { en: "Classic Collar Shirt", ta: "கிளாசிக் காலர் சட்டை" }
  ],
  casual_shirts: [
    { en: "Linen Mandarin Shirt", ta: "லினன் மேண்டரின் சட்டை" },
    { en: "Madras Plaid Shirt", ta: "மெட்ராஸ் கட்டம் சட்டை" },
    { en: "Indigo Chambray Shirt", ta: "இண்டிகோ சேம்பிரே சட்டை" },
    { en: "Cuban Collar Linen Shirt", ta: "கியூபன் காலர் லினன் சட்டை" },
    { en: "Washed Denim Casual Shirt", ta: "வாஷ்டு டெனிம் சட்டை" },
    { en: "Slub Cotton Casual Shirt", ta: "ஸ்லப் காட்டன் சட்டை" },
    { en: "Olive Safari Shirt", ta: "ஆலிவ் சஃபாரி சட்டை" },
    { en: "Short Sleeve Linen Shirt", ta: "அரைக்கை லினன் சட்டை" },
    { en: "Handloom Short Kurta", ta: "கைத்தறி குர்தா சட்டை" },
    { en: "Pastel Mint Linen Shirt", ta: "புதினா லினன் சட்டை" },
    { en: "Breezy Camp Collar Shirt", ta: "கேம்ப் காலர் சட்டை" },
    { en: "Relaxed Striped Shirt", ta: "வரிகள் கொண்ட சட்டை" },
    { en: "Checked Flannel Shirt", ta: "ஃபிளானல் கட்டம் சட்டை" },
    { en: "Earthy Raw Cotton Shirt", ta: "இயற்கை காட்டன் சட்டை" },
    { en: "Overdyed Utility Shirt", ta: "டைடு கேஷுவல் சட்டை" }
  ],
  tshirts_polos: [
    { en: "Pique Cotton Polo", ta: "பிகே காட்டன் போலோ" },
    { en: "Supima Crewneck Tee", ta: "சுபிமா க்ரூநெக் டி-சர்ட்" },
    { en: "Mercerized Polo Shirt", ta: "மெர்சரைஸ்டு போலோ" },
    { en: "Waffle Long Sleeve Henley", ta: "வாஃபிள் ஹென்லி சட்டை" },
    { en: "Tipped Collar Polo", ta: "டிப்டு காலர் போலோ" },
    { en: "Heavyweight Cotton Tee", ta: "தடித்த காட்டன் டி-சர்ட்" },
    { en: "Minimalist Pocket Tee", ta: "பாக்கெட் டி-சர்ட்" },
    { en: "Slub Jersey T-Shirt", ta: "ஸ்லப் ஜெர்சி டி-சர்ட்" },
    { en: "Nautical Striped Polo", ta: "வரிகள் கொண்ட போலோ" },
    { en: "Soft Knit Henley Tee", ta: "மென்மையான ஹென்லி" },
    { en: "Slim Fit Solid Tee", ta: "ஸ்லிம் ஃபிட் டி-சர்ட்" },
    { en: "Zip Neck Polo Shirt", ta: "ஜிப் நெக் போலோ" },
    { en: "Vintage Washed Tee", ta: "வின்டேஜ் வாஷ்டு டி-சர்ட்" },
    { en: "Ribbed Cotton Polo", ta: "ரிப்டு காட்டன் போலோ" }
  ],
  trousers_chinos: [
    { en: "Slim Fit Chinos", ta: "ஸ்லிம் ஃபிட் சீனோஸ்" },
    { en: "Pleated Dress Trousers", ta: "பிளீட்டட் பார்மல் பேன்ட்" },
    { en: "Stretch Cotton Chinos", ta: "ஸ்ட்ரெட்ச் காட்டன் சீனோஸ்" },
    { en: "Flat-Front Trousers", ta: "பிளாட்-பிரண்ட் பேன்ட்" },
    { en: "Tailored Wool Trousers", ta: "வூல் பார்மல் பேன்ட்" },
    { en: "Linen Drawstring Pants", ta: "லினன் டிராவ்ஸ்ட்ரிங் பேன்ட்" },
    { en: "Relaxed Fit Chinos", ta: "ரிலாக்ஸ்டு சீனோஸ்" },
    { en: "Gurkha Cotton Trousers", ta: "குர்கா காட்டன் பேன்ட்" },
    { en: "Tapered Cargo Pants", ta: "டாப்பர்டு கார்கோ பேன்ட்" },
    { en: "Classic Khaki Chinos", ta: "கிளாசிக் காக்கி பேன்ட்" },
    { en: "Navy Formal Trousers", ta: "நேவி பார்மல் பேன்ட்" },
    { en: "Charcoal Dress Pants", ta: "சாம்பல் நிற பார்மல் பேன்ட்" },
    { en: "Olive Utility Chinos", ta: "ஆலிவ் நிற சீனோஸ்" },
    { en: "Cropped Ankle Trousers", ta: "ஆங்கிள் லெந்த் பேன்ட்" },
    { en: "Selvedge Denim Jeans", ta: "டெனிம் ஜீன்ஸ்" }
  ],
  blazers_suits: [
    { en: "Navy Wool Blazer", ta: "நேவி வூல் ப்ளேசர்" },
    { en: "Summer Linen Blazer", ta: "கோடைக்கால லினன் ப்ளேசர்" },
    { en: "Raw Silk Nehru Jacket", ta: "ரா சில்க் நேரு ஜாக்கெட்" },
    { en: "Black Tuxedo Jacket", ta: "கருப்பு டக்ஷீடோ கோட்" },
    { en: "Single-Breasted Blazer", ta: "சிங்கிள் பிரஸ்டட் ப்ளேசர்" },
    { en: "Double-Breasted Blazer", ta: "டபுள் பிரஸ்டட் ப்ளேசர்" },
    { en: "Houndstooth Wool Jacket", ta: "ஹவுண்ட்ஸ்டூத் ப்ளேசர்" },
    { en: "Classic Tweed Blazer", ta: "கிளாசிக் ட்வீட் ப்ளேசர்" },
    { en: "Festive Bandhgala Coat", ta: "பண்டிகை பந்த்கலா கோட்" },
    { en: "Unstructured Linen Jacket", ta: "லைட்வெயிட் லினன் ஜாக்கெட்" },
    { en: "Charcoal Suit Jacket", ta: "சாம்பல் நிற சூட் கோட்" },
    { en: "Formal Tailored Waistcoat", ta: "பார்மல் வேஸ்ட்கோட்" },
    { en: "Embroidered Nehru Jacket", ta: "எம்பிராய்டரி நேரு ஜாக்கெட்" }
  ],
  dhotis_ethnic: [
    { en: "Mayilkann Silk Dhoti", ta: "மயில்கண் பட்டு வேஷ்டி" },
    { en: "Gold Zari Silk Dhoti", ta: "தங்க ஜரிகை பட்டு வேஷ்டி" },
    { en: "Pure Cotton Panchakacham", ta: "தூய காட்டன் பஞ்சகச்சம்" },
    { en: "Temple Border Silk Dhoti", ta: "கோவில் கரை பட்டு வேஷ்டி" },
    { en: "Kanchipuram Wedding Dhoti", ta: "காஞ்சிபுரம் திருமண வேஷ்டி" },
    { en: "Salem Handloom Vesti", ta: "சேலம் கைத்தறி வேஷ்டி" },
    { en: "Double Layer Silk Dhoti", ta: "இரட்டை பட்டு வேஷ்டி" },
    { en: "Kasavu Border Dhoti", ta: "கசவு கரை வேஷ்டி" },
    { en: "Coimbatore Cotton Dhoti", ta: "கோவை பருத்தி வேஷ்டி" },
    { en: "Silk Dhoti & Angavastram", ta: "பட்டு வேஷ்டி & துண்டு" },
    { en: "Traditional Cotton Lungi", ta: "பாரம்பரிய காட்டன் லுங்கி" },
    { en: "Handloom Checked Lungi", ta: "கைத்தறி கட்டம் லுங்கி" },
    { en: "Vesti & Shirt Match Set", ta: "வேஷ்டி சட்டை செட்" },
    { en: "Pure White Cotton Vesti", ta: "தூய வெள்ளை பருத்தி வேஷ்டி" }
  ],
  footwear: [
    { en: "Oxford Leather Shoes", ta: "ஆக்ஸ்போர்டு தோல் காலணி" },
    { en: "Penny Leather Loafers", ta: "பென்னி லெதர் லோஃபர்ஸ்" },
    { en: "Kolhapuri Leather Chappals", ta: "கோலாப்பூரி தோல் செருப்பு" },
    { en: "Tassel Loafers", ta: "டாஸில் லோஃபர்ஸ்" },
    { en: "Leather Cross Sandals", ta: "தோல் கிராஸ் செருப்பு" },
    { en: "Derby Dress Shoes", ta: "டெர்பி பார்மல் ஷூ" },
    { en: "Double Monk Strap Shoes", ta: "மங்க் ஸ்ட்ராப் ஷூ" },
    { en: "Driving Moccasins", ta: "டிரைவிங் மொக்காசின்ஸ்" },
    { en: "White Leather Sneakers", ta: "வெள்ளை லெதர் ஸ்னீக்கர்ஸ்" },
    { en: "Brogue Leather Shoes", ta: "ப்ரோக் தோல் காலணி" },
    { en: "Braided Leather Sandals", ta: "பின்னல் தோல் செருப்பு" },
    { en: "Suede Slip-On Loafers", ta: "ஸ்வீட் லோஃபர்ஸ்" },
    { en: "Cushioned Running Shoes", ta: "ரன்னிங் ஷூ" },
    { en: "Handcrafted Peshawari Sandals", ta: "பெஷாவரி தோல் காலணி" },
    { en: "Slip-On Mule Loafers", ta: "ஸ்லிப்-ஆன் லோஃபர்ஸ்" }
  ],
  accessories: [
    { en: "Reversible Leather Belt", ta: "இருபுற தோல் பெல்ட்" },
    { en: "Leather Bifold Wallet", ta: "தோல் பணப்பை" },
    { en: "Silk Jacquard Necktie", ta: "பட்டு நெக்டை" },
    { en: "Silver Cufflinks", ta: "வெள்ளி கஃப்லிங்க்ஸ்" },
    { en: "Linen Pocket Square", ta: "லினன் பாக்கெட் ஸ்கொயர்" },
    { en: "Slim Leather Cardholder", ta: "தோல் அட்டைப்பை" },
    { en: "Polished Brass Tie Bar", ta: "பித்தளை டை பார்" },
    { en: "Minimalist Leather Watch", ta: "லெதர் வாட்ச்" },
    { en: "Braided Leather Belt", ta: "பின்னிய தோல் பெல்ட்" },
    { en: "Woven Silk Bow Tie", ta: "பட்டு போ டை" },
    { en: "Chronograph Wristwatch", ta: "குரோனோகிராஃப் வாட்ச்" },
    { en: "Engraved Money Clip", ta: "மணி கிளிப்" }
  ]
};

// Modifiers to ensure uniqueness while keeping names strictly 2-4 words
const modifiers = [
  "Classic", "Premium", "Tailored", "Heritage", "Signature", "Refined", "Essential",
  "Urban", "Modern", "Royal", "Artisan", "Handwoven", "Slim", "Relaxed", "Vintage"
];

// Group products by category
const catGroups = {};
products.forEach(p => {
  if (!catGroups[p.category]) catGroups[p.category] = [];
  catGroups[p.category].push(p);
});

let updatedCount = 0;

for (const [cat, items] of Object.entries(catGroups)) {
  const pool = namesPool[cat] || namesPool.formal_shirts;
  const poolLen = pool.length;

  items.forEach((p, idx) => {
    const base = pool[idx % poolLen];
    const cycle = Math.floor(idx / poolLen);

    let shortEn = base.en;
    let shortTa = base.ta;

    if (cycle > 0) {
      const mod = modifiers[(cycle - 1 + idx) % modifiers.length];
      // Keep it short: prepend or replace adjective
      if (!shortEn.startsWith(mod)) {
        shortEn = `${mod} ${shortEn}`;
        shortTa = `${shortTa} (${mod})`;
      }
    }

    p.name_en = shortEn;
    p.name_ta = shortTa;
    updatedCount++;
  });
}

console.log(`Updated ${updatedCount} products with short, concise names.`);
console.log('Sample updated names:');
products.slice(0, 20).forEach((p, i) => {
  console.log(`${i + 1}. [${p.category}] ${p.name_en} (${p.name_ta})`);
});

fs.writeFileSync(productsPath, JSON.stringify(products, null, 2), 'utf8');
console.log('Saved short names to backend/data/products.json successfully!');
