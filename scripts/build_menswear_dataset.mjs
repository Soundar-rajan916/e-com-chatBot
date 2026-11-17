import fs from 'fs';
import path from 'path';

const productsPath = path.resolve('backend/data/products.json');
const rawData = JSON.parse(fs.readFileSync(productsPath, 'utf8'));

// 1. Map existing menswear items
const mappedItems = [];
rawData.forEach(p => {
  if (p.category === 'mens_wear') {
    if (p.subcategory === 'Formal Shirts') {
      mappedItems.push({
        ...p,
        category: 'formal_shirts',
        subcategory: 'Formal Shirts'
      });
    } else if (p.subcategory === 'Casual T-Shirts') {
      mappedItems.push({
        ...p,
        category: 'tshirts_polos',
        subcategory: 'T-Shirts & Polos'
      });
    } else if (p.subcategory === 'Trousers') {
      if ((p.name_en || '').toLowerCase().includes('wallet')) {
        mappedItems.push({
          ...p,
          category: 'accessories',
          subcategory: 'Leather Goods'
        });
      } else {
        mappedItems.push({
          ...p,
          category: 'trousers_chinos',
          subcategory: 'Trousers & Chinos'
        });
      }
    } else if (p.subcategory === 'Blazers') {
      mappedItems.push({
        ...p,
        category: 'blazers_suits',
        subcategory: 'Blazers & Suits'
      });
    } else if (p.subcategory === 'Lungi & Vesti') {
      mappedItems.push({
        ...p,
        category: 'dhotis_ethnic',
        subcategory: 'Dhotis & Ethnic'
      });
    }
  } else if (p.category === 'footwear') {
    mappedItems.push({
      ...p,
      category: 'footwear',
      subcategory: p.subcategory || 'Footwear'
    });
  } else if (p.category === 'sarees_ethnic' && (p.subcategory === 'Dhotis' || (p.name_en || '').toLowerCase().includes('dhoti'))) {
    mappedItems.push({
      ...p,
      category: 'dhotis_ethnic',
      subcategory: 'Traditional Silk Dhotis'
    });
  } else if (p.category === 'electronics_accessories' && (p.subcategory === 'Smart Watches' || (p.name_en || '').includes('Smart Watch'))) {
    mappedItems.push({
      ...p,
      category: 'accessories',
      subcategory: 'Gentleman Watches'
    });
  }
});

console.log(`Mapped ${mappedItems.length} existing items.`);

// 2. Synthesize complementary curated menswear items
const newItems = [];

// Curated Casual Linen & Casual Shirts (35 items)
const casualShirtsTemplates = [
  { en: "Pure European Linen Mandarin Shirt", ta: "தூய ஐரோப்பிய லினன் மேண்டரின் சட்டை", sub: "Linen Shirts", price: 2499, desc_en: "Ultra-breathable 100% natural European flax linen with contemporary Mandarin band collar and coconut shell buttons. Perfect for tropical comfort.", desc_ta: "100% இயற்கை லினன் துணியால் செய்யப்பட்ட நேர்த்தியான மேண்டரின் காலர் சட்டை. கோடை காலத்திற்கு ஏற்ற குளிர்ச்சியான ஆடை." },
  { en: "Madras Heritage Plaid Casual Shirt", ta: "பாரம்பரிய மெட்ராஸ் கட்டம் கேஷுவல் சட்டை", sub: "Casual Cotton", price: 1699, desc_en: "Authentic yarn-dyed pure cotton Madras checks woven in southern Tamil Nadu. Breathable, vibrant, and pre-washed for vintage softness.", desc_ta: "தென் தமிழ்நாட்டின் கைத்தறி பாரம்பரியத்தில் உருவான மெட்ராஸ் செக்ஸ் சட்டை. பருத்தி நூலினால் நெய்யப்பட்ட மென்மையான வடிவம்." },
  { en: "Indigo Washed Chambray Denim Shirt", ta: "இண்டிகோ வாஷ்டு சேம்பிரே டெனிம் சட்டை", sub: "Chambray Shirts", price: 1999, desc_en: "Classic indigo rope-dyed cotton chambray with pearlescent snap buttons and western yokes. Softens gracefully with each wash.", desc_ta: "நீல நிற இண்டிகோ சேம்பிரே பருத்தி சட்டை. நவீன தோற்றமும் உறுதியான நெசவும் கொண்டது." },
  { en: "Coastal Resort Cuban Collar Linen Shirt", ta: "கியூபன் காலர் ரிசார்ட் லினன் சட்டை", sub: "Linen Shirts", price: 2199, desc_en: "Relaxed boxy silhouette with an open camp Cuban collar. Crafted from pure breezy linen for effortless weekend style.", desc_ta: "தளர்வான கியூபன் காலர் கொண்ட லினன் சட்டை. வார இறுதி விடுமுறை மற்றும் கடற்கரை பயணங்களுக்கு உகந்தது." },
  { en: "Striped Slub Cotton Casual Shirt", ta: "வரிகள் அமைந்த ஸ்லப் காட்டன் சட்டை", sub: "Casual Cotton", price: 1499, desc_en: "Richly textured slub yarn cotton with subtle nautical vertical stripes and curved hem. Easy to style untucked.", desc_ta: "அழகான மெல்லிய வரிகள் கொண்ட உயர்தர காட்டன் சட்டை. அன்றாட பயன்பாட்டிற்கு சௌகரியமானது." },
  { en: "Coimbatore Handloom Cotton Kurta Shirt", ta: "கோயம்புத்தூர் கைத்தறி குர்தா சட்டை", sub: "Ethnic Casuals", price: 1799, desc_en: "Mid-length casual short kurta shirt woven on traditional shuttle looms in Coimbatore. Lightweight and naturally temperature regulating.", desc_ta: "கோவை கைத்தறியில் நெய்யப்பட்ட குறுகிய குர்தா சட்டை. காற்றோட்டமான இயற்கை பருத்தி துணி." },
  { en: "Olive Washed Safari Utility Shirt", ta: "ஆலிவ் வாஷ்டு சஃபாரி கேஷுவல் சட்டை", sub: "Utility Shirts", price: 2299, desc_en: "Durable cotton twill utility shirt featuring twin flap chest pockets, reinforced elbow patches, and roll-up sleeve tabs.", desc_ta: "இரட்டை பாக்கெட்டுகள் கொண்ட திடமான காட்டன் ட்வில் சட்டை. பயணம் மற்றும் வெளிப்புற சாகசங்களுக்கு சிறந்தது." },
  { en: "Pastel Mint Pure Linen Slim Shirt", ta: "பேஸ்டல் புதினா லினன் ஸ்லிம் சட்டை", sub: "Linen Shirts", price: 2599, desc_en: "Refreshing mint green pure flax linen tailored in a sharp modern slim silhouette. Crisp yet soft on the skin.", desc_ta: "புத்துணர்ச்சியூட்டும் வெளிர் பச்சை நிற தூய லினன் சட்டை. நவீன ஸ்லிம் ஃபிட் வடிவம்." }
];

for (let i = 0; i < 35; i++) {
  const t = casualShirtsTemplates[i % casualShirtsTemplates.length];
  const idx = String(i + 1).padStart(3, '0');
  newItems.push({
    sku: `SKU-MW-CSH-${idx}`,
    name_en: `${t.en} (Edition ${i + 1})`,
    name_ta: `${t.ta} (${i + 1})`,
    category: "casual_shirts",
    subcategory: t.sub,
    price: t.price + (i % 5) * 100,
    stock_qty: 25 + (i % 15) * 2,
    rating: Number((4.3 + (i % 7) * 0.1).toFixed(1)),
    description_en: t.desc_en,
    description_ta: t.desc_ta
  });
}

// Curated Formal Shirts (20 items)
const formalShirtsTemplates = [
  { en: "Royal Oxford Pure Giza Cotton Shirt", ta: "ராயல் ஆக்ஸ்போர்டு கீசா காட்டன் பார்மல் சட்டை", sub: "Oxford Shirts", price: 2799, desc_en: "Lustrous 100-ply double twisted Egyptian Giza cotton with a structured spread collar and rounded cuffs. Essential boardroom attire.", desc_ta: "100% எகிப்திய கீசா பருத்தியில் நெய்யப்பட்ட கம்பீரமான பார்மல் சட்டை. அலுவலகம் மற்றும் கூட்டங்களுக்கு ஏற்றது." },
  { en: "French Cuff Classic White Poplin Shirt", ta: "பிரெஞ்ச் கஃப் வெள்ளை பாப்லின் பார்மல் சட்டை", sub: "French Cuff", price: 2999, desc_en: "Pristine white silky poplin formal shirt equipped with double French cuffs for bespoke cufflinks. Tailored with mother-of-pearl buttons.", desc_ta: "கஃப்லிங்க்ஸ் பொருத்தும் பிரெஞ்ச் கஃப் வசதியுடன் கூடிய தூய வெள்ளை நிற உயர்தர பார்மல் சட்டை." },
  { en: "Sky Blue Herringbone Twill Shirt", ta: "வான நீல ஹெர்ரிங்போன் ட்வில் சட்டை", sub: "Twill Shirts", price: 2499, desc_en: "Subtle chevron herringbone weave offering an elegant drape and wrinkle-resistant durability throughout long business days.", desc_ta: "சுருக்கமில்லாத ஹெர்ரிங்போன் நெசவு கொண்ட வெளிர் நீல நிற நேர்த்தியான பார்மல் சட்டை." },
  { en: "Micro Houndstooth Dobby Dress Shirt", ta: "மைக்ரோ ஹவுண்ட்ஸ்டூத் டாபி பார்மல் சட்டை", sub: "Dobby Weave", price: 2599, desc_en: "Intricate micro geometric dobby texture woven in premium combed cotton with cutaway collar and split back yoke.", desc_ta: "நுட்பமான டாபி நெசவு அமைப்பும் நவீன காலரும் கொண்ட அழகான பார்மல் சட்டை." }
];

for (let i = 0; i < 20; i++) {
  const t = formalShirtsTemplates[i % formalShirtsTemplates.length];
  const idx = String(i + 1).padStart(3, '0');
  newItems.push({
    sku: `SKU-MW-FML-${idx}`,
    name_en: `${t.en} (Tailored ${i + 1})`,
    name_ta: `${t.ta} (${i + 1})`,
    category: "formal_shirts",
    subcategory: t.sub,
    price: t.price + (i % 4) * 150,
    stock_qty: 30 + (i % 10) * 3,
    rating: Number((4.5 + (i % 5) * 0.1).toFixed(1)),
    description_en: t.desc_en,
    description_ta: t.desc_ta
  });
}

// Curated Polos & T-Shirts (25 items)
const poloTemplates = [
  { en: "Pique Mercerized Cotton Polo Shirt", ta: "மெர்சரைஸ்டு காட்டன் பிகே போலோ சட்டை", sub: "Polos", price: 1499, desc_en: "Silky mercerized cotton honeycomb pique with ribbed flat-knit collar and mother-of-pearl 3-button placket.", desc_ta: "பட்டு போன்ற பளபளப்பும் மென்மையும் கொண்ட உயர்தர மெர்சரைஸ்டு போலோ சட்டை." },
  { en: "Supima Cotton Heavyweight Crewneck T-Shirt", ta: "சுபிமா காட்டன் க்ரூநெக் டி-சர்ட்", sub: "Crewnecks", price: 1199, desc_en: "240 GSM ultra-dense American Supima cotton tee with reinforced bound collar that never loses shape.", desc_ta: "தடித்த மற்றும் நீடித்து உழைக்கும் சுபிமா பருத்தி டி-சர்ட். கழுத்து பகுதி தளர்வடையாது." },
  { en: "Waffle Knit Long Sleeve Henley", ta: "வாஃபிள் நிட் நீண்ட கை ஹென்லி டி-சர்ட்", sub: "Henleys", price: 1599, desc_en: "Thermal waffle textured breathable cotton with antique brass buttons. Ideal layering essential for cooler evenings.", desc_ta: "வாஃபிள் நெசவு கொண்ட மெல்லிய கதகதப்பான நீண்ட கை ஹென்லி டி-சர்ட்." },
  { en: "Tipped Collar Smart Casual Polo", ta: "டிப்டு காலர் ஸ்மார்ட் கேஷுவல் போலோ", sub: "Polos", price: 1699, desc_en: "Contrast jacquard tipped collar and cuffs on rich breathable combed cotton with side split vents.", desc_ta: "வண்ண விளிம்பு காலர் கொண்ட ஸ்டைலான ஸ்மார்ட் கேஷுவல் போலோ." }
];

for (let i = 0; i < 25; i++) {
  const t = poloTemplates[i % poloTemplates.length];
  const idx = String(i + 1).padStart(3, '0');
  newItems.push({
    sku: `SKU-MW-POL-${idx}`,
    name_en: `${t.en} (Series ${i + 1})`,
    name_ta: `${t.ta} (${i + 1})`,
    category: "tshirts_polos",
    subcategory: t.sub,
    price: t.price + (i % 4) * 100,
    stock_qty: 40 + (i % 20) * 2,
    rating: Number((4.4 + (i % 6) * 0.1).toFixed(1)),
    description_en: t.desc_en,
    description_ta: t.desc_ta
  });
}

// Curated Blazers & Suits (15 items)
const blazerTemplates = [
  { en: "Italian Wool Blend Bespoke Navy Blazer", ta: "இத்தாலியன் வூல் பிளெண்ட் நேவி ப்ளேசர்", sub: "Tailored Blazers", price: 7999, desc_en: "Signature tailored midnight navy blazer crafted from fine Italian wool blend with peak lapels, pick-stitch detailing, and brass buttons.", desc_ta: "இத்தாலிய கம்பளி கலவையில் தைக்கப்பட்ட நேவி நீல நிற கம்பீரமான ப்ளேசர் கோட்." },
  { en: "Summer Linen Unstructured Sports Jacket", ta: "கோடைக்கால லினன் ஸ்போர்ட்ஸ் ஜாக்கெட்", sub: "Casual Blazers", price: 5499, desc_en: "Unlined, lightweight pure linen jacket tailored for breezy tropical elegance with patch pockets and double back vents.", desc_ta: "எடைக் குறைவான தூய லினன் ஜாக்கெட். கோடைக்கால கொண்டாட்டங்களுக்கு ஏற்றது." },
  { en: "Festive Raw Silk Embroidered Nehru Jacket", ta: "பண்டிகை கால எம்பிராய்டரி நேரு ஜாக்கெட்", sub: "Nehru Jackets", price: 4299, desc_en: "Pure raw Matka silk waistcoat adorned with tonal threadwork and metallic buttons. Layers effortlessly over kurtas and shirts.", desc_ta: "தூய ரா சில்க் துணியில் தைக்கப்பட்ட பாரம்பர்ய நேரு ஜாக்கெட். குர்தாக்களின் மேல் அணிய சிறந்தது." },
  { en: "Classic Black Tuxedo Dinner Jacket", ta: "கிளாசிக் பிளாக் டக்ஷீடோ ஜாக்கெட்", sub: "Tuxedos", price: 8999, desc_en: "Satin shawl lapel single-breasted black tuxedo jacket with jetted pockets and satin-covered buttons for formal galas.", desc_ta: "சாட்டின் காலர் கொண்ட கருப்பு நிற டக்ஷீடோ கோட். உயர்தர இரவு விருந்துகளுக்கு ஏற்றது." }
];

for (let i = 0; i < 15; i++) {
  const t = blazerTemplates[i % blazerTemplates.length];
  const idx = String(i + 1).padStart(3, '0');
  newItems.push({
    sku: `SKU-MW-BLZ-${idx}`,
    name_en: `${t.en} (Cut ${i + 1})`,
    name_ta: `${t.ta} (${i + 1})`,
    category: "blazers_suits",
    subcategory: t.sub,
    price: t.price + (i % 3) * 500,
    stock_qty: 15 + (i % 8) * 2,
    rating: Number((4.6 + (i % 4) * 0.1).toFixed(1)),
    description_en: t.desc_en,
    description_ta: t.desc_ta
  });
}

// Curated Accessories (25 items)
const accessoryTemplates = [
  { en: "Full-Grain Reversible Italian Leather Belt", ta: "இருபுறமும் பயன்படுத்தக்கூடிய தோல் பெல்ட்", sub: "Belts", price: 1699, desc_en: "Handcrafted 34mm genuine full-grain leather belt with reversible twist buckle (Classic Black & Rich Cognac Brown).", desc_ta: "கருப்பு மற்றும் பிரவுன் ஆகிய இரு பக்கமும் அணியக்கூடிய உயர்தர தோல் பெல்ட்." },
  { en: "Handmade RFID-Blocking Leather Bifold Wallet", ta: "ஆர்.எஃப்.ஐ.டி பாதுகாப்பு தோல் பணப்பை", sub: "Wallets", price: 1499, desc_en: "Slim vegetable-tanned cowhide wallet featuring 8 card slots, dual currency compartments, and integrated RFID security shielding.", desc_ta: "பாதுகாப்பான அட்டை அமைப்பும் இயற்கை தோல் நெகிழ்வும் கொண்ட நேர்த்தியான பணப்பை." },
  { en: "Pure Mulberry Silk Woven Jacquard Necktie Set", ta: "தூய மல்பெரி பட்டு நெக்டை செட்", sub: "Ties & Pocket Squares", price: 1899, desc_en: "Hand-rolled 8cm silk necktie accompanied by matching silk pocket square and polished silver tie bar in an archival gift box.", desc_ta: "பட்டு நெக்டை, பாக்கெட் ஸ்கொயர் மற்றும் வெள்ளி டை கிளிப் அடங்கிய பிரீமியம் செட்." },
  { en: "Monogrammed Mother-of-Pearl & Silver Cufflinks", ta: "வெள்ளி மற்றும் சிப்பி கஃப்லிங்க்ஸ்", sub: "Cufflinks", price: 1299, desc_en: "Polished rhodium-plated brass cufflinks inlaid with natural iridescent mother-of-pearl for refined formal shirts.", desc_ta: "பார்மல் சட்டைகளின் பிரெஞ்ச் கஃப்களுக்கு அழகு சேர்க்கும் இயற்கை சிப்பி பதிக்கப்பட்ட கஃப்லிங்க்ஸ்." }
];

for (let i = 0; i < 25; i++) {
  const t = accessoryTemplates[i % accessoryTemplates.length];
  const idx = String(i + 1).padStart(3, '0');
  newItems.push({
    sku: `SKU-MW-ACC-${idx}`,
    name_en: `${t.en} (Model ${i + 1})`,
    name_ta: `${t.ta} (${i + 1})`,
    category: "accessories",
    subcategory: t.sub,
    price: t.price + (i % 4) * 100,
    stock_qty: 35 + (i % 15) * 2,
    rating: Number((4.5 + (i % 5) * 0.1).toFixed(1)),
    description_en: t.desc_en,
    description_ta: t.desc_ta
  });
}

const finalCatalog = [...mappedItems, ...newItems];

console.log(`Total exclusive menswear products: ${finalCatalog.length}`);
const finalCats = {};
finalCatalog.forEach(p => finalCats[p.category] = (finalCats[p.category] || 0) + 1);
console.log('Final Category Breakdown:', JSON.stringify(finalCats, null, 2));

// Backup old products.json and write new one
fs.writeFileSync(path.resolve('backend/data/products.json.bak'), JSON.stringify(rawData, null, 2), 'utf8');
fs.writeFileSync(productsPath, JSON.stringify(finalCatalog, null, 2), 'utf8');
console.log('Saved 100% Menswear catalog to backend/data/products.json successfully!');
