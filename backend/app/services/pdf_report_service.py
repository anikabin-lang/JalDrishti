"""Multilingual PDF Report Generation Service for JalDrishti.

Generates professional, publication-grade heritage conservation dossiers
in 15 languages adhering to archaeological and conservation engineering standards.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# 15-Language dictionary for PDF headings & labels
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "JALDRISHTI HERITAGE INSPECTION DOSSIER",
        "subtitle": "AI-Assisted Structural Health & Defect Assessment",
        "structure_info": "Heritage Structure Identification",
        "inspection_meta": "Inspection Metadata",
        "summary": "Executive Summary of Findings",
        "photo_breakdown": "Individual Photograph Analysis",
        "defect_passport": "Defect Passport Registry",
        "materials": "Material Compatibility & IKS Conservation Guidelines",
        "disclaimer": "Engineering Limitations & Conservation Ethics",
        "structure_name": "Structure Name",
        "typology": "Typology",
        "location": "Location",
        "region": "Region",
        "inspection_id": "Inspection ID",
        "date": "Inspection Date",
        "type": "Inspection Type",
        "total_images": "Total Photographs",
        "valid_images": "Valid Heritage Views",
        "total_cracks": "Cracks Detected",
        "total_veg": "Vegetation / Biological Growth",
        "overall_status": "Structural Health Status",
        "models": "Computer Vision Pipeline Models",
    },
    "hi": {
        "title": "जलदृष्टि धरोहर निरीक्षण रिपोर्ट",
        "subtitle": "एआई-सहायता प्राप्त संरचनात्मक स्वास्थ्य एवं दोष मूल्यांकन",
        "structure_info": "धरोहर संरचना विवरण",
        "inspection_meta": "निरीक्षण मेटाडेटा",
        "summary": "निष्कर्षों का सारांश",
        "photo_breakdown": "व्यक्तिगत छायाचित्र विश्लेषण",
        "defect_passport": "दोष पासपोर्ट रजिस्ट्री",
        "materials": "सामग्री अनुकूलता एवं पारंपरिक संरक्षण दिशानिर्देश",
        "disclaimer": "अभियांत्रिकी सीमाएं एवं संरक्षण आचारनीति",
        "structure_name": "संरचना का नाम",
        "typology": "प्रकार",
        "location": "स्थान",
        "region": "क्षेत्र",
        "inspection_id": "निरीक्षण आईडी",
        "date": "निरीक्षण तिथि",
        "type": "निरीक्षण प्रकार",
        "total_images": "कुल छायाचित्र",
        "valid_images": "वैध धरोहर दृश्य",
        "total_cracks": "दरारें पाई गईं",
        "total_veg": "वनस्पति / जैविक वृद्धि",
        "overall_status": "संरचनात्मक स्वास्थ्य स्थिति",
        "models": "कंप्यूटर विजन मॉडल",
    },
    "bn": {
        "title": "জলদৃষ্টি ঐতিহ্য পরিদর্শন প্রতিবেদন",
        "subtitle": "এআই-সহায়তাপ্রাপ্ত কাঠামোগত স্বাস্থ্য এবং ত্রুটি মূল্যায়ন",
        "structure_info": "ঐতিহ্য কাঠামো পরিচয়",
        "inspection_meta": "পরিদর্শন মেটাডেটা",
        "summary": "ফলাফলের নির্বাহী সারাংশ",
        "photo_breakdown": "স্বতন্ত্র ছবি বিশ্লেষণ",
        "defect_passport": "ত্রুটি পাসপোর্ট রেজিস্ট্রি",
        "materials": "উপাদান সামঞ্জস্য ও ঐতিহ্যবাহী সংরক্ষণ নির্দেশিকা",
        "disclaimer": "প্রকৌশলগত সীমাবদ্ধতা এবং সংরক্ষণ নীতি",
        "structure_name": "কাঠামোর নাম",
        "typology": "ধরণ",
        "location": "অবস্থান",
        "region": "অঞ্চল",
        "inspection_id": "পরিদর্শন আইডি",
        "date": "পরিদর্শন তারিখ",
        "type": "পরিদর্শন প্রকার",
        "total_images": "মোট আলোকচিত্র",
        "valid_images": "বৈধ ঐতিহ্য দৃশ্য",
        "total_cracks": "চিহ্নিত ফাটল",
        "total_veg": "উদ্ভিদ / জৈবিক অনুপ্রবেশ",
        "overall_status": "কাঠামোগত স্থিতি",
        "models": "কম্পিউটার ভিশন মডেল",
    },
    "te": {
        "title": "జలదృష్టి వారసత్వ తనిఖీ నివేదిక",
        "subtitle": "AI-సహాయక నిర్మాణాత్మక ఆరోగ్యం మరియు లోపాల అంచనా",
        "structure_info": "వారసత్వ నిర్మాణ గుర్తింపు",
        "inspection_meta": "తనిఖీ మెటాడేటా",
        "summary": "ఫలితాల కార్యనిర్వాహక సారాంశం",
        "photo_breakdown": "వ్యక్తిగత ఛాయాచిత్ర విశ్లేషణ",
        "defect_passport": "లోప పాస్‌పోర్ట్ రిజిస్ట్రీ",
        "materials": "సామగ్రి అనుకూలత మరియు సాంప్రదాయ పరిరక్షణ మార్గదర్శకాలు",
        "disclaimer": "ఇంజనీరింగ్ పరిమితులు మరియు పరిరక్షణ నీతి",
        "structure_name": "నిర్మాణం పేరు",
        "typology": "రకం",
        "location": "ప్రాంతం",
        "region": "ప్రాంతం",
        "inspection_id": "తనిఖీ ID",
        "date": "తనిఖీ తేదీ",
        "type": "తనిఖీ రకం",
        "total_images": "మొత్తం ఛాయాచిత్రాలు",
        "valid_images": "చెల్లుబాటు అయ్యే వారసత్వ దృశ్యాలు",
        "total_cracks": "గుర్తించిన పగుళ్లు",
        "total_veg": "వృక్షసంపద / జీవ పెరుగుదల",
        "overall_status": "నిర్మాణాత్మక స్థితి",
        "models": "కంప్యూటర్ విజన్ మోడల్స్",
    },
    "mr": {
        "title": "जलदृष्टी वारसा तपासणी अहवाल",
        "subtitle": "एआय-सहाय्यित संरचनात्मक आरोग्य आणि दोष मूल्यांकन",
        "structure_info": "वारसा संरचना ओळख",
        "inspection_meta": "तपासणी मेटाडेटा",
        "summary": "निष्कर्षांचा सारांश",
        "photo_breakdown": "वैयक्तिक छायाचित्र विश्लेषण",
        "defect_passport": "दोष पासपोर्ट नोंदवही",
        "materials": "साहित्य सुसंगतता आणि पारंपारिक संवर्धन मार्गदर्शक तत्त्वे",
        "disclaimer": "अभियांत्रिकी मर्यादा आणि संवर्धन तत्त्वे",
        "structure_name": "संरचनेचे नाव",
        "typology": "प्रकार",
        "location": "स्थान",
        "region": "विभाग",
        "inspection_id": "तपासणी आयडी",
        "date": "तपासणी तारीख",
        "type": "तपासणी प्रकार",
        "total_images": "एकूण छायाचित्रे",
        "valid_images": "वैध वारसा दृश्ये",
        "total_cracks": "आढळलेल्या भेगा",
        "total_veg": "वनस्पती / जैविक वाढ",
        "overall_status": "संरचनात्मक स्थिती",
        "models": "संगणक दृष्टी मॉडेल",
    },
    "ta": {
        "title": "ஜல்திருஷ்டி பாரம்பரிய ஆய்வு அறிக்கை",
        "subtitle": "AI-உதவியுடன் கூடிய கட்டமைப்பு ஆரோக்கியம் மற்றும் குறைபாடுகள் மதிப்பீடு",
        "structure_info": "பாரம்பரிய கட்டமைப்பு அடையாளம்",
        "inspection_meta": "ஆய்வு மெட்டாடேட்டா",
        "summary": "கண்டுபிடிப்புகளின் சுருக்கம்",
        "photo_breakdown": "தனிப்பட்ட புகைப்பட பகுப்பாய்வு",
        "defect_passport": "குறைபாடு பாஸ்போர்ட் பதிவேடு",
        "materials": "பொருட்கள் பொருந்தக்கூடிய தன்மை மற்றும் பாரம்பரிய பாதுகாப்பு வழிகாட்டுதல்கள்",
        "disclaimer": "பொறியியல் வரம்புகள் மற்றும் பாதுகாப்பு நெறிமுறைகள்",
        "structure_name": "கட்டமைப்பின் பெயர்",
        "typology": "வகை",
        "location": "இடம்",
        "region": "மண்டலம்",
        "inspection_id": "ஆய்வு ஐடி",
        "date": "ஆய்வு தேதி",
        "type": "ஆய்வு வகை",
        "total_images": "மொத்த புகைப்படங்கள்",
        "valid_images": "செல்லுபடியாகும் பாரம்பரிய காட்சிகள்",
        "total_cracks": "கண்டறியப்பட்ட விரிசல்கள்",
        "total_veg": "தாவரங்கள் / உயிரியல் வளர்ச்சி",
        "overall_status": "கட்டமைப்பு நிலை",
        "models": "கணினி பார்வை மாதிரிகள்",
    },
    "ur": {
        "title": "جلدریشتی روایتی معائنہ ڈوزیئر",
        "subtitle": "مصنوعی ذہانت کی مدد سے ساختی صحت اور نقائص کا جائزہ",
        "structure_info": "ورثے کی ساخت کی شناخت",
        "inspection_meta": "معائنہ میٹا ڈیٹا",
        "summary": "نتائج کا خلاصہ",
        "photo_breakdown": "انفرادی تصاویر کا تجزیہ",
        "defect_passport": "نقص پاسپورٹ رجسٹری",
        "materials": "مواد کی مطابقت اور روایتی تحفظ کے رہنما اصول",
        "disclaimer": "انجینئرنگ کی حدود اور اخلاقیات",
        "structure_name": "عمارت کا نام",
        "typology": "قسم",
        "location": "مقام",
        "region": "علاقہ",
        "inspection_id": "معائنہ آئی ڈی",
        "date": "تاریخ معائنہ",
        "type": "معائنہ کی قسم",
        "total_images": "کل تصاویر",
        "valid_images": "درست روایتی مناظر",
        "total_cracks": "دریافت شدہ دراڑیں",
        "total_veg": "نباتات / حیاتیاتی دخل اندازی",
        "overall_status": "ساختی حیثیت",
        "models": "کمپیوٹر وژن ماڈلز",
    },
    "gu": {
        "title": "જલદ્રષ્ટિ વારસો નિરીક્ષણ અહેવાલ",
        "subtitle": "AI-સહાયિત માળખાકીય સ્વાસ્થ્ય અને ક્ષતિ મૂલ્યાંકન",
        "structure_info": "વારસા સ્થાપત્ય ઓળખ",
        "inspection_meta": "નિરીક્ષણ મેટાડેટા",
        "summary": "તારણોનો સારાંશ",
        "photo_breakdown": "વ્યક્તિગત તસવીર વિશ્લેષણ",
        "defect_passport": "ક્ષતિ પાસપોર્ટ રજિસ્ટ્રી",
        "materials": "સામગ્રી સુસંગતતા અને પરંપરાગત સંરક્ષણ માર્ગદર્શિકા",
        "disclaimer": "ઈજનેરી મર્યાદાઓ અને સંરક્ષણ નીતિ",
        "structure_name": "માળખાનું નામ",
        "typology": "પ્રકાર",
        "location": "સ્થળ",
        "region": "વિસ્તાર",
        "inspection_id": "નિરીક્ષણ આઈડી",
        "date": "નિરીક્ષણ તારીખ",
        "type": "નિરીક્ષણ પ્રકાર",
        "total_images": "કુલ તસવીરો",
        "valid_images": "માન્ય વારસા દ્રશ્યો",
        "total_cracks": "મળેલી તિરાડો",
        "total_veg": "વનસ્પતિ / જૈવિક વૃદ્ધિ",
        "overall_status": "માળખાકીય સ્થિતિ",
        "models": "કમ્પ્યુટર વિઝન મોડેલ",
    },
    "kn": {
        "title": "ಜಲದೃಷ್ಟಿ ಪರಂಪರೆ ಪರಿಶೀಲನಾ ವರದಿ",
        "subtitle": "AI-ಸಹಾಯದ ರಚನಾತ್ಮಕ ಆರೋಗ್ಯ ಮತ್ತು ದೋಷ ಮೌಲ್ಯಮಾಪನ",
        "structure_info": "ಪರಂಪರೆ ರಚನೆ ಗುರುತಿಸುವಿಕೆ",
        "inspection_meta": "ಪರಿಶೀಲನಾ ಮೆಟಾಡೇಟಾ",
        "summary": "ಫಲಿತಾಂಶಗಳ ಸಾರಾಂಶ",
        "photo_breakdown": "ಪ್ರತ್ಯೇಕ ಛಾಯಾಚಿತ್ರ ವಿಶ್ಲೇಷಣೆ",
        "defect_passport": "ದೋಷ ಪಾಸ್‌ಪೋರ್ಟ್ ನೋಂದಣಿ",
        "materials": "ಸಾಮಗ್ರಿ ಹೊಂದಾಣಿಕೆ ಮತ್ತು ಸಾಂಪ್ರದಾಯಿಕ ಸಂರಕ್ಷಣಾ ಮಾರ್ಗಸೂಚಿಗಳು",
        "disclaimer": "ಎಂಜಿನಿಯರಿಂಗ್ ಮಿತಿಗಳು ಮತ್ತು ಸಂರಕ್ಷಣಾ ನೀತಿ",
        "structure_name": "ರಚನೆಯ ಹೆಸರು",
        "typology": "ಮಾದರಿ",
        "location": "ಸ್ಥಳ",
        "region": "ಪ್ರದೇಶ",
        "inspection_id": "ಪರಿಶೀಲನಾ ಐಡಿ",
        "date": "ಪರಿಶೀಲನಾ ದಿನಾಂಕ",
        "type": "ಪರಿಶೀಲನಾ ಪ್ರಕಾರ",
        "total_images": "ಒಟ್ಟು ಛಾಯಾಚಿತ್ರಗಳು",
        "valid_images": "ಮಾನ್ಯ ಪರಂಪರೆ ದೃಶ್ಯಗಳು",
        "total_cracks": "ಕಂಡುಬಂದ ಬಿರುಕುಗಳು",
        "total_veg": "ಸಸ್ಯವರ್ಗ / ಜೈವಿಕ ನುಸುಳುವಿಕೆ",
        "overall_status": "ರಚನಾತ್ಮಕ ಸ್ಥಿತಿ",
        "models": "ಕಂಪ್ಯೂಟರ್ ದೃಷ್ಟಿ ಮಾದರಿಗಳು",
    },
    "ml": {
        "title": "ജലദൃഷ്ടി പൈതൃക പരിശോധനാ റിപ്പോർട്ട്",
        "subtitle": "AI-സഹായത്തോടെയുള്ള ഘടനാപരമായ ആരോഗ്യവും തകരാറുകളുടെ വിലയിരുത്തലും",
        "structure_info": "പൈതൃക ഘടന തിരിച്ചറിയൽ",
        "inspection_meta": "പരിശോധനാ മെറ്റാഡാറ്റ",
        "summary": "കണ്ടെത്തലുകളുടെ സംഗ്രഹം",
        "photo_breakdown": "വ്യക്തിഗത ഫോട്ടോ വിശകലനം",
        "defect_passport": "തകരാറ് പാസ്പോർട്ട് രജിസ്ട്രി",
        "materials": "മെറ്റീരിയൽ അനുയോജ്യതയും പരമ്പരാഗത സംരക്ഷണ മാർഗ്ഗനിർദ്ദേശങ്ങളും",
        "disclaimer": "എഞ്ചിനീയറിംഗ് പരിമിതികളും സംരക്ഷണ തത്വങ്ങളും",
        "structure_name": "ഘടനയുടെ പേര്",
        "typology": "തരം",
        "location": "സ്ഥലം",
        "region": "മേഖല",
        "inspection_id": "പരിശോധനാ ഐഡി",
        "date": "പരിശോധനാ തീയതി",
        "type": "പരിശോധനാ തരം",
        "total_images": "ആകെ ഫോട്ടോകൾ",
        "valid_images": "സാധുവായ പൈതൃക കാഴ്ചകൾ",
        "total_cracks": "കണ്ടെത്തിയ വിള്ളലുകൾ",
        "total_veg": "സസ്യങ്ങൾ / ജൈവിക വളർച്ച",
        "overall_status": "ഘടനാപരമായ അവസ്ഥ",
        "models": "കമ്പ്യൂട്ടർ വിഷൻ മോഡലുകൾ",
    },
    "or": {
        "title": "ଜଳଦୃଷ୍ଟି ଐତିହ୍ୟ ଯାଞ୍ଚ ରିପୋର୍ଟ",
        "subtitle": "AI-ସହାୟକ ଗଠନମୂଳକ ସ୍ୱାସ୍ଥ୍ୟ ଏବଂ ତ୍ରୁଟି ମୂଲ୍ୟାଙ୍କନ",
        "structure_info": "ଐତିହ୍ୟ ସଂରଚନା ପରିଚୟ",
        "inspection_meta": "ଯାଞ୍ଚ ମେଟାଡାଟା",
        "summary": "ନିଷ୍କର୍ଷର ସାରାଂଶ",
        "photo_breakdown": "ବ୍ୟକ୍ତିଗତ ଫଟୋ ବିଶ୍ଳେଷଣ",
        "defect_passport": "ତ୍ରୁଟି ପାସପୋର୍ଟ ପଞ୍ଜିକା",
        "materials": "ସାମଗ୍ରୀ ଉପଯୁକ୍ତତା ଏବଂ ପାରମ୍ପରିକ ସଂରକ୍ଷଣ ନିର୍ଦ୍ଦେଶାବଳୀ",
        "disclaimer": "ଇଞ୍ଜିନିୟରିଂ ସୀମା ଏବଂ ସଂରକ୍ଷଣ ନୀତି",
        "structure_name": "ସଂରଚନାର ନାମ",
        "typology": "ପ୍ରକାର",
        "location": "ସ୍ଥାନ",
        "region": "ଅଞ୍ଚଳ",
        "inspection_id": "ଯାଞ୍ଚ ଆଇଡି",
        "date": "ଯାଞ୍ଚ ତାରିଖ",
        "type": "ଯାଞ୍ଚ ପ୍ରକାର",
        "total_images": "ମୋଟ ଫଟୋଗ୍ରାଫ୍",
        "valid_images": "ବୈଧ ଐତିହ୍ୟ ଦୃଶ୍ୟ",
        "total_cracks": "ଚିହ୍ନଟ ହୋଇଥିବା ଫାଟ",
        "total_veg": "ଉଦ୍ଭିଦ / ଜୈବିକ ଅନୁପ୍ରବେଶ",
        "overall_status": "ଗଠନମୂଳକ ସ୍ଥିତି",
        "models": "କମ୍ପ୍ୟୁଟର ଭିଜନ ମଡେଲ",
    },
    "pa": {
        "title": "ਜਲਦ੍ਰਿਸ਼ਟੀ ਵਿਰਾਸਤੀ ਨਿਰੀਖਣ ਰਿਪੋਰਟ",
        "subtitle": "AI-ਸਹਾਇਤਾ ਪ੍ਰਾਪਤ ਢਾਂਚਾਗਤ ਸਿਹਤ ਅਤੇ ਨੁਕਸ ਮੁਲਾਂਕਣ",
        "structure_info": "ਵਿਰਾਸਤੀ ਢਾਂਚਾ ਪਛਾਣ",
        "inspection_meta": "ਨਿਰੀਖਣ ਮੈਟਾਡੇਟਾ",
        "summary": "ਸਿੱਟਿਆਂ ਦਾ ਸਾਰ",
        "photo_breakdown": "ਵਿਅਕਤੀਗਤ ਫੋਟੋ ਵਿਸ਼ਲੇਸ਼ਣ",
        "defect_passport": "ਨੁਕਸ ਪਾਸਪੋਰਟ ਰਜਿਸਟਰੀ",
        "materials": "ਸਮੱਗਰੀ ਅਨੁਕੂਲਤਾ ਅਤੇ ਰਵਾਇਤੀ ਸੰਭਾਲ ਦਿਸ਼ਾ-ਨਿਰਦੇਸ਼",
        "disclaimer": "ਇੰਜੀਨੀਅਰਿੰਗ ਸੀਮਾਵਾਂ ਅਤੇ ਸੰਭਾਲ ਨੈਤਿਕਤਾ",
        "structure_name": "ਢਾਂਚੇ ਦਾ ਨਾਮ",
        "typology": "ਕਿਸਮ",
        "location": "ਸਥਾਨ",
        "region": "ਖੇਤਰ",
        "inspection_id": "ਨਿਰੀਖਣ ਆਈਡੀ",
        "date": "ਨਿਰੀਖਣ ਮਿਤੀ",
        "type": "ਨਿਰੀਖਣ ਕਿਸਮ",
        "total_images": "ਕੁੱਲ ਤਸਵੀਰਾਂ",
        "valid_images": "ਮਾਨਤਾ ਪ੍ਰਾਪਤ ਵਿਰਾਸਤੀ ਦ੍ਰਿਸ਼",
        "total_cracks": "ਲੱਭੀਆਂ ਤਰੇੜਾਂ",
        "total_veg": "ਬਨਸਪਤੀ / ਜੈਵਿਕ ਵਾਧਾ",
        "overall_status": "ਢਾਂਚਾਗਤ ਸਥਿਤੀ",
        "models": "ਕੰਪਿਊਟਰ ਵਿਜ਼ਨ ਮਾਡਲ",
    },
    "as": {
        "title": "জলদৃষ্টি ঐতিহ্য পৰিদৰ্শন প্ৰতিবেদন",
        "subtitle": "AI-সহায়তাকৃত গাঁথনিগত স্বাস্থ্য আৰু ত্ৰুটি মূল্যায়ন",
        "structure_info": "ঐতিহ্য গাঁথনি চিনাক্তকৰণ",
        "inspection_meta": "পৰিদৰ্শন মেটাডেটা",
        "summary": "ফলাফলৰ কাৰ্যবাহী সাৰাংশ",
        "photo_breakdown": "ব্যক্তিগত ফটো বিশ্লেষণ",
        "defect_passport": "ত্ৰুটি পাছপ'ৰ্ট পঞ্জীয়ন",
        "materials": "সামগ্ৰীৰ অনুকূলতা আৰু পৰম্পৰাগত সংৰক্ষণ নিৰ্দেশনা",
        "disclaimer": "অভিযান্ত্ৰিক সীমাবদ্ধতা আৰু সংৰক্ষণ নীতি",
        "structure_name": "গাঁথনিৰ নাম",
        "typology": "প্ৰকাৰ",
        "location": "স্থান",
        "region": "অঞ্চল",
        "inspection_id": "পৰিদৰ্শন আইডি",
        "date": "পৰিদৰ্শনৰ তাৰিখ",
        "type": "পৰিদৰ্শনৰ প্ৰকাৰ",
        "total_images": "মুঠ আলোকচিত্ৰ",
        "valid_images": "বৈধ ঐতিহ্য দৃশ্য",
        "total_cracks": "চিনাক্ত ফাট",
        "total_veg": "উদ্ভিদ / জৈৱিক বৃদ্ধি",
        "overall_status": "গাঁথনিগত অৱস্থা",
        "models": "কম্পিউটাৰ ভিজন মডেল",
    },
    "ks": {
        "title": "جلدریشتی ورثہ معائنہ رپورٹ",
        "subtitle": "مصنوعی ذہانت پؠٹھ مبنی ساختی صحت تہٕ خرابی ہُنٛد جائزہ",
        "structure_info": "ورثہ ڈھانچک پچھان",
        "inspection_meta": "معائنہ میٹا ڈیٹا",
        "summary": "خلاصہ",
        "photo_breakdown": "انفرادی تصویر تجزیہ",
        "defect_passport": "خرابی پاسپورٹ رجسٹری",
        "materials": "مواد مطابقت تہٕ روایتی تحفظ ہند اصول",
        "disclaimer": "انجینئرنگ حدود",
        "structure_name": "عمارت ناو",
        "typology": "قسم",
        "location": "جائے",
        "region": "علاقہ",
        "inspection_id": "معائنہ نمبر",
        "date": "معائنہ تاریخ",
        "type": "معائنہ قسم",
        "total_images": "کل تصویر",
        "valid_images": "صحیح ورثہ مناظر",
        "total_cracks": "دراڑن ہند تعداد",
        "total_veg": "گھاس پھوس",
        "overall_status": "ساختی حالت",
        "models": "ویژن ماڈل",
    },
    "sa": {
        "title": "जलदृष्टिः पुरातत्त्व-निरीक्षण-पत्रम्",
        "subtitle": "कृत्रिमप्रज्ञोपकृतं संरचनात्मक-स्वास्थ्य-दोष-मूल्यांकनम्",
        "structure_info": "पुरातन-संरचना-परिचयः",
        "inspection_meta": "निरीक्षण-विवरणम्",
        "summary": "निष्कर्ष-संक्षेपः",
        "photo_breakdown": "प्रत्येक-चित्र-विश्लेषणम्",
        "defect_passport": "दोष-पारपत्र-पञ्जिका",
        "materials": "द्रव्य-सामञ्जस्यं पारम्परिक-संरक्षण-सूत्राणि च",
        "disclaimer": "यान्त्रिक-सीमाः संरक्षण-धर्माश्च",
        "structure_name": "संरचनायाः नाम",
        "typology": "प्रकारः",
        "location": "स्थानम्",
        "region": "मण्डलम्",
        "inspection_id": "निरीक्षण-संकेतः",
        "date": "निरीक्षण-दिनाङ्कः",
        "type": "निरीक्षण-भेदः",
        "total_images": "कुल-चित्राणि",
        "valid_images": "प्रमाणित-पुरातन-दृश्यानि",
        "total_cracks": "दृष्टाः विदारयः (Cracks)",
        "total_veg": "पादप-प्रसारः / जैविक-वृद्धिः",
        "overall_status": "संरचनात्मक-स्वास्थ्यम्",
        "models": "दृष्टि-प्रतिमानानि",
    },
}


def get_t(lang: str) -> Dict[str, str]:
    return TRANSLATIONS.get(lang.lower(), TRANSLATIONS["en"])


class PDFReportService:
    """Generates standardized engineering and archaeological conservation reports."""

    def generate_inspection_pdf(
        self,
        structure: Dict[str, Any],
        inspection: Dict[str, Any],
        passports: List[Dict[str, Any]],
        lang: str = "en",
    ) -> bytes:
        t = get_t(lang)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        # Custom palette based on JalDrishti Design System: Deep Slate (#1A1A1A), Laterite (#C0714F), Jade (#7FA393)
        slate = colors.HexColor("#1A1A1A")
        laterite = colors.HexColor("#C0714F")
        stone_bg = colors.HexColor("#F8F7F4")
        border_color = colors.HexColor("#E5E0D8")

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=slate,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=laterite,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=slate,
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=slate,
        )
        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#666666"),
        )
        meta_val_style = ParagraphStyle(
            "MetaValue",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=slate,
        )

        story = []

        # --- 1. Header Banner ---
        story.append(Paragraph(t["title"], title_style))
        story.append(Paragraph(t["subtitle"], subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=laterite, spaceAfter=12))

        # --- 2. Structure & Inspection Metadata (Side-by-side table) ---
        meta_table_data = [
            [
                Paragraph(t["structure_name"], meta_label_style),
                Paragraph(str(structure.get("name", "Heritage Water Structure")), meta_val_style),
                Paragraph(t["inspection_id"], meta_label_style),
                Paragraph(str(inspection.get("inspection_id", "N/A")), meta_val_style),
            ],
            [
                Paragraph(t["typology"], meta_label_style),
                Paragraph(str(structure.get("typology", "baoli")).upper(), meta_val_style),
                Paragraph(t["date"], meta_label_style),
                Paragraph(str(inspection.get("inspection_date", datetime.now().strftime("%Y-%m-%d"))), meta_val_style),
            ],
            [
                Paragraph(t["location"], meta_label_style),
                Paragraph(str(structure.get("location", "N/A")), meta_val_style),
                Paragraph(t["type"], meta_label_style),
                Paragraph(str(inspection.get("inspection_type", "baseline")).upper(), meta_val_style),
            ],
            [
                Paragraph(t["region"], meta_label_style),
                Paragraph(str(structure.get("region", "Northern India")), meta_val_style),
                Paragraph(t["models"], meta_label_style),
                Paragraph("Faster R-CNN MobileNetV3 + YOLO26n", meta_val_style),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[1.3 * inch, 2.2 * inch, 1.3 * inch, 2.4 * inch])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), stone_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # --- 3. Executive Summary Cards ---
        story.append(Paragraph(t["summary"], heading_style))
        summary_data = [
            [
                Paragraph("<b>Total Views:</b>", meta_label_style),
                Paragraph(str(inspection.get("total_images", 0)), meta_val_style),
                Paragraph("<b>Valid Heritage Views:</b>", meta_label_style),
                Paragraph(str(inspection.get("valid_images", 0)), meta_val_style),
            ],
            [
                Paragraph("<b>Total Cracks:</b>", meta_label_style),
                Paragraph(str(inspection.get("total_cracks", 0)), meta_val_style),
                Paragraph("<b>Vegetation Findings:</b>", meta_label_style),
                Paragraph(str(inspection.get("vegetation_count", 0)), meta_val_style),
            ],
            [
                Paragraph("<b>Defect Passports Active:</b>", meta_label_style),
                Paragraph(str(len(passports)), meta_val_style),
                Paragraph("<b>Baseline Completed:</b>", meta_label_style),
                Paragraph("YES (Verified)" if structure.get("baseline_completed") else "IN PROGRESS", meta_val_style),
            ],
        ]
        summary_table = Table(summary_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
        summary_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # --- 4. Defect Passport Registry Table ---
        story.append(Paragraph(t["defect_passport"], heading_style))
        if passports:
            pass_headers = ["Defect ID", "Category", "Confidence", "Severity", "Status", "First Observed"]
            pass_rows = [[Paragraph(f"<b>{h}</b>", meta_label_style) for h in pass_headers]]
            for p in passports:
                pass_rows.append([
                    Paragraph(p["defect_id"], meta_val_style),
                    Paragraph(p["defect_category"].replace("_", " ").title(), meta_val_style),
                    Paragraph(f"{p['confidence']:.1%}", meta_val_style),
                    Paragraph(p.get("severity", "moderate").upper(), meta_val_style),
                    Paragraph(p.get("status", "active").upper(), meta_val_style),
                    Paragraph(p["first_detected_date"][:10], meta_val_style),
                ])
            pass_table = Table(pass_rows, colWidths=[1.2 * inch, 1.8 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch])
            pass_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECE7DF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(pass_table)
        else:
            story.append(Paragraph("No persistent defect passports currently registered for this structure.", body_style))

        story.append(Spacer(1, 14))

        # --- 5. Photograph-Wise Findings ---
        story.append(Paragraph(t["photo_breakdown"], heading_style))
        images = inspection.get("images", [])
        if images:
            img_headers = ["#", "Filename", "Quality", "Relevance", "Status", "Defects Found"]
            img_rows = [[Paragraph(f"<b>{h}</b>", meta_label_style) for h in img_headers]]
            for idx, img in enumerate(images, 1):
                img_rows.append([
                    Paragraph(str(idx), meta_val_style),
                    Paragraph(img.get("original_filename", "photo.jpg")[:24], meta_val_style),
                    Paragraph(img.get("quality_status", "good").title(), meta_val_style),
                    Paragraph(img.get("relevance_status", "relevant").title(), meta_val_style),
                    Paragraph(img.get("inspection_status", "accepted").upper(), meta_val_style),
                    Paragraph(str(img.get("defects_count", 0)), meta_val_style),
                ])
            img_table = Table(img_rows, colWidths=[0.4 * inch, 2.2 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch, 1.2 * inch])
            img_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECE7DF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(img_table)
        else:
            story.append(Paragraph("No individual photograph analysis records available.", body_style))

        story.append(Spacer(1, 14))

        # --- 6. IKS Traditional Materials Guidelines & Conservation Warnings ---
        story.append(Paragraph(t["materials"], heading_style))
        iks_text = (
            "<b>Recommended Repair Mortar:</b> Authentic Hydraulic Lime-Surkhi Mortar (1 part slaked fat lime putty, "
            "cured >90 days : 2 parts finely pulverized calcined terracotta surkhi : 1 part sieved quartz river sand, "
            "tempered with fermented jaggery (gur) decoction and urad dal mucilage).<br/>"
            "<b>PROHIBITED INTERVENTIONS:</b> Application of Ordinary Portland Cement (OPC) or non-breathable synthetic "
            "epoxies is strictly prohibited. OPC forms an impermeable vapor barrier that induces severe cryptoflorescence "
            "and accelerated spalling on historic masonry surfaces."
        )
        story.append(Paragraph(iks_text, body_style))
        story.append(Spacer(1, 10))

        # --- 7. Limitations & Ethical Disclaimer ---
        story.append(Paragraph(t["disclaimer"], heading_style))
        disc_text = (
            "<i>This dossier was generated automatically by the JalDrishti Computer Vision & Heritage Engineering Pipeline. "
            "Defect detections represent candidate regions identified by Faster R-CNN and YOLO26n models. Surface photographic "
            "analysis cannot determine internal foundation settlement, subterranean hydrostatic pressure, or hidden masonry voids. "
            "All candidate defects must be verified on site by a qualified archaeological conservator or structural engineer before "
            "implementing physical conservation interventions.</i>"
        )
        story.append(Paragraph(disc_text, body_style))

        doc.build(story)
        return buffer.getvalue()


pdf_report_service = PDFReportService()

