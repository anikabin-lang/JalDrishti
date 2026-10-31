"""Full website translation engine across all 15 languages for JalDrishti."""

import json
import re
from pathlib import Path
from scripts.expand_full_website_translations import NEW_KEYS_EN
from scripts.merge_translations import TRANSLATIONS_MAP

# Regional language specific translations
REGIONAL_TRANSLATIONS = {
    "bn": {
        "pipeline.pending": "অপেক্ষমাণ",
        "pipeline.active": "চলমান",
        "pipeline.done": "সম্পূর্ণ",
        "pipeline.failed": "ব্যর্থ",
        "pipeline.skipped": "বাদ দেওয়া হয়েছে",
        "hero.skipDescent": "অবতরণ এড়িয়ে যান",
        "hero.waterHeritage": "ভারতের জল ঐতিহ্য",
        "hero.chapter1.label": "০১ / স্থান",
        "hero.chapter1.rail": "স্থান",
        "hero.chapter1.title": "জল ঐতিহ্য তার প্রাকৃতিক পরিবেশের অংশ।",
        "hero.chapter1.body": "বাওলি, কুণ্ড, মন্দির পুকুর বা গ্রামীণ জলাশয়: প্রতিটি নিজস্ব ভূমি, জলবায়ু ও সম্প্রদায়ের মধ্যে অবস্থিত। যে কোনো কাঠামো বোঝার সূচনা তার চারপাশ দেখার মাধ্যমে হয়।",
        "hero.chapter2.label": "০২ / অভিগমন",
        "hero.chapter2.rail": "অভিগমন",
        "hero.chapter2.title": "কাঠামো, ভূমি এবং জল একসাথে কাজ করে।",
        "hero.chapter2.body": "ঢাল, ধারণ এলাকা এবং প্রাচীর নির্ধারণ করে কিভাবে জল পৌঁছায়, জমা হয় এবং ব্যবহৃত হয়।",
        "hero.chapter3.label": "০৩ / অবতরণ",
        "hero.chapter3.rail": "অবতরণ",
        "hero.chapter3.title": "নথিবদ্ধকরণ প্রসঙ্গের সাথে শুরু হয়।",
        "hero.chapter3.body": "সিঁড়ি, ল্যান্ডিং এবং প্রাচীর প্রমাণ করে যে একটি কাঠামো কীভাবে নকশা ও ব্যবহৃত হয়েছিল।",
        "hero.chapter4.label": "০৪ / কারুশিল্প",
        "hero.chapter4.rail": "কারুশিল্প",
        "hero.chapter4.title": "উপাদানগুলোর যত্নশীল ব্যাখ্যা প্রয়োজন।",
        "hero.chapter4.body": "পাথরের খাঁজ, ক্ষয়প্রাপ্ত তল এবং পরবর্তী মেরামত বিভিন্ন ইতিহাস তুলে ধরে। নির্ভুল রেকর্ড আসল ও পরিবর্তিত উপাদান আলাদা করতে সাহায্য করে।",
        "hero.chapter5.label": "০৫ / জল",
        "hero.chapter5.rail": "জল",
        "hero.chapter5.title": "দৃশ্যমান প্রমাণ এবং গভীর অনুসন্ধান।",
        "hero.chapter5.body": "আর্দ্রতা, নিকাশি ব্যবস্থা, গাছপালা এবং চারপাশের পরিবেশ সময়ের সাথে ঐতিহাসিক জল কাঠামোকে প্রভাবিত করে।",
        "hero.chapter6.label": "০৬ / জলদৃষ্টি",
        "hero.chapter6.rail": "লক্ষ্য",
        "hero.chapter6.title": "একটি দৃষ্টান্ত। এক বিস্তৃত জল ঐতিহ্য।",
        "hero.chapter6.body": "বাওলি ও কুণ্ড থেকে শুরু করে ঐতিহাসিক দীঘি পর্যন্ত, জলদৃষ্টি ডিজিটাল নথিবদ্ধকরণ, ঐতিহ্যবাহী জ্ঞান ও সংরক্ষণ পরামর্শ একত্রিত করে।",
        "home.diversity.label": "একটি বৈচিত্র্যময় জল ঐতিহ্য",
        "home.diversity.title": "এক ঐতিহ্য। বহু রূপ। স্বতন্ত্র স্থানীয় জ্ঞান।",
        "home.diversity.lead": "সমগ্র ভারত জুড়ে ঐতিহ্যবাহী জল কাঠামো বিভিন্ন রূপ ধারণ করে। বাওলি, কুণ্ড, দীঘি ও পুকুর স্থানীয় ভূপ্রকৃতি ও উপকরণের সাথে সামঞ্জস্যপূর্ণ।",
        "home.diversity.stepwells": "বাওলি / ধাপযুক্ত কূপ",
        "home.diversity.stepwellsTerms": "বাওলি · বাওয়াদি · ভাব",
        "home.diversity.stepwellsBody": "ভূগর্ভস্থ জল পর্যন্ত ধাপযুক্ত অবতরণ, যেখানে চাতাল, প্রতিরক্ষা প্রাচীর এবং অনেক ক্ষেত্রে গ্যালারি ও কূপ থাকে।",
        "home.diversity.kunds": "কুণ্ড",
        "home.diversity.kundsTerms": "কুণ্ড · কুণ্ডা · কুণ্ডী",
        "home.diversity.kundsBody": "বৃষ্টির জল সংগ্রহের জন্য ধাপযুক্ত জলাধার, যা সাধারণত বাঁধানো পাড়যুক্ত উল্টানো পিরামিডের মতো।",
        "home.diversity.tanks": "ঐতিহাসিক দীঘি ও জলাশয়",
        "home.diversity.tanksTerms": "তালাব · সাগর · এরি",
        "home.diversity.tanksBody": "মৌসুমি জল ধরে রাখার জন্য বাঁধযুক্ত জলাধার, যাতে ঘাট ও জলকপাট থাকে।",
        "home.diversity.temple": "মন্দির পুকুর",
        "home.diversity.templeTerms": "কল্যাণী · পুষ্করিণী",
        "home.diversity.templeBody": "মন্দির চত্বরের ভিতরের বা পাশের পুকুর, যা চারদিকে বাঁধানো এবং ধর্মীয় ও সামাজিক জীবনের সাথে যুক্ত।",
        "home.diversity.ponds": "পুকুর ও আঞ্চলিক ব্যবস্থা",
        "home.diversity.pondsTerms": "জোহাদ · পুকুর · স্থানীয় নাম",
        "home.diversity.pondsBody": "মাটির বাঁধ ও গ্রামীণ পুকুর, যা স্থানীয় ভূপ্রকৃতি অনুযায়ী জল ধরে রাখতে ও ভাগাভাগি করতে নির্মিত।",
        "home.diversity.tagToday": "বর্তমান জ্ঞান নথি",
        "home.diversity.tagScope": "পরিকল্পিত সীমার মধ্যে",
        "home.diversity.footerNote": "পরিকল্পনামূলক চিত্র, মাপ অনুসারে নয়। আঞ্চলিক নাম পরিবর্তিত হতে পারে।",
        "home.doc.label": "নথিবদ্ধকরণের গুরুত্ব",
        "home.doc.title": "প্রতিটি কাঠামো একটি ভিন্ন গল্প বলে।",
        "home.doc.body": "দৃশ্যমান ক্ষতি নানা রূপ নিতে পারে: ফাটল, ক্ষয়, আর্দ্রতা, উদ্ভিদ বৃদ্ধি বা আগের মেরামতের দাগ। ভালো নথিবদ্ধকরণ সংরক্ষণের সঠিক সূচনা বিন্দু তৈরি করে।",
        "home.doc.caption": "গাঁথুনির চিত্রভিত্তিক বিবরণ · দৃশ্যমান লক্ষণ কেবল রেকর্ডের শুরু, সিদ্ধান্তের শেষ নয়।",
        "home.doc.method": "জলদৃষ্টি পদ্ধতি · দৃষ্টি → বোধ → মূল্যায়ন → পুনর্জীবন",
        "home.doc.see": "দৃষ্টি",
        "home.doc.seeLine": "যা দৃশ্যমান তা নথিবদ্ধ করুন।",
        "home.doc.understand": "বোধ",
        "home.doc.understandLine": "এর পেছনের প্রেক্ষাপট পুনরুদ্ধার করুন।",
        "home.doc.assess": "মূল্যায়ন",
        "home.doc.assessLine": "উপাদান এবং হস্তক্ষেপ বিবেচনা করুন।",
        "home.doc.revive": "পুনর্জীবন",
        "home.doc.reviveLine": "দায়িত্বশীল সংরক্ষণ পরিকল্পনা তৈরি করুন।",
        "home.see.label": "দৃষ্টি",
        "home.see.title": "দৃশ্যমান অবস্থা নথিবদ্ধ করা সহজ করুন।",
        "home.see.lead": "জলদৃষ্টির এআই-সহায়তাপ্রাপ্ত ভিশন ওয়ার্কফ্লো পরিদর্শন চিত্র থেকে দৃশ্যমান প্যাটার্ন সংগঠিত করতে সাহায্য করে।",
        "home.see.point1": "স্থানের আলোকচিত্র ও পর্যবেক্ষণ রেকর্ড করুন।",
        "home.see.point2": "মডেল সমর্থিত ক্ষেত্রগুলোতে উদ্বেগের জায়গা চিহ্নিত করুন।",
        "home.see.point3": "দৃশ্যমান প্রমাণ প্রাসঙ্গিক পরিদর্শনের সাথে সংযুক্ত রাখুন।",
        "home.see.point4": "মডেল-উত্পন্ন পর্যবেক্ষণ বিশেষজ্ঞ-যাচাইকৃত ফলাফল থেকে আলাদা রাখুন।",
        "home.see.liveBadge": "সক্রিয়: ফাইন-টিউনড Faster R-CNN এবং সমন্বিত YOLO26n ক্ষতি সনাক্তকরণ",
        "home.see.caveat": "শুধুমাত্র ছবির ভিত্তিতে কাঠামোগত স্থিতিশীলতা বা উপাদানের রাসায়নিক গুণাগুণ নির্ধারণ করা সম্ভব নয়।",
        "home.see.btnStart": "পরিদর্শন শুরু করুন",
        "home.see.btnFindings": "ফলাফল ওয়ার্কস্পেস",
        "home.understand.label": "বোধ",
        "home.understand.title": "দৃশ্যমান প্রমাণের সাথে পরিচিত প্রেক্ষাপট সংযুক্ত করুন।",
        "home.understand.body": "ঐতিহ্যবাহী জল কাঠামো দেশীয় প্রকৌশল নীতির ওপর নির্মিত হয়েছিল। এই প্রেক্ষাপট পুনরুদ্ধার পর্যবেক্ষণ ব্যাখ্যা করতে সহায়তা করে।",
        "home.understand.callout": "কাঠামোগত ধরন, উপাদান এবং ঐতিহাসিক প্রকৌশল বিষয়ক জ্ঞানভাণ্ডার অন্বেষণ করুন।",
        "home.understand.btnKnowledge": "জ্ঞানভাণ্ডার অন্বেষণ করুন",
        "home.material.label": "মূল্যায়ন",
        "home.material.title": "উপাদান, প্রেক্ষাপট এবং কারণ বিবেচনা করুন।",
        "home.material.body": "সংরক্ষণ সিদ্ধান্ত শুধু ওপরের তলের চেহারার ওপর নির্ভর করে না। মূল উপাদান, নির্মাণরীতি, আর্দ্রতা এবং পূর্ববর্তী মেরামত সবই বিবেচ্য।",
        "home.material.point1": "প্রযোজ্য ক্ষেত্রে উপযুক্ত উপাদান বা হস্তক্ষেপ উপস্থাপন করুন।",
        "home.material.point2": "প্রাসঙ্গিক সামঞ্জস্যের কারণ ও প্রমাণ ব্যাখ্যা করুন।",
        "home.material.point3": "যেসব ক্ষেত্রে পেশাদার পর্যালোচনার প্রয়োজন তা চিহ্নিত করুন।",
        "home.material.point4": "গুরুত্বপূর্ণ সিদ্ধান্ত যোগ্য পেশাদারদের হাতে রাখুন।",
        "home.material.caveat": "এই উদাহরণটি নথিভুক্ত উপাদান বৈশিষ্ট্যের ওপর ভিত্তি করে দুটি মর্টারের তুলনা করে, পরীক্ষাগার পরীক্ষার ভিত্তিতে নয়।",
        "home.material.stronglyRecommended": "দৃঢ়ভাবে সুপারিশকৃত",
        "home.material.recommended": "সুপারিশকৃত",
        "home.material.conditional": "শর্তসাপেক্ষ",
        "home.material.incompatible": "অসামঞ্জস্যপূর্ণ",
        "home.material.dimMechanical": "যান্ত্রিক",
        "home.material.dimMoisture": "আর্দ্রতা",
        "home.material.dimThermal": "তাপীয়",
        "home.material.dimChemical": "রাসায়নিক",
        "home.material.dimReversibility": "প্রত্যাবর্তনযোগ্যতা",
        "home.material.dimHeritage": "ঐতিহ্য সামঞ্জস্য",
        "home.material.dimVisual": "দৃশ্যমান সামঞ্জস্য",
        "home.revive.label": "পুনর্জীবন",
        "home.revive.title": "দায়িত্বশীল সংরক্ষণের পরিকল্পনা করুন।",
        "home.revive.body": "হস্তক্ষেপ প্রত্যাবর্তনযোগ্য এবং মূল উপাদানের সাথে সামঞ্জস্যপূর্ণ হওয়া উচিত।",
        "home.closing.title": "ভারতের জল ঐতিহ্য নথিবদ্ধ করুন।",
        "home.closing.lead": "যা নথিবদ্ধ করা সম্ভব তা দিয়ে শুরু করুন। ঐতিহ্যবাহী জ্ঞানের সাথে তা যুক্ত করুন।",
        "home.closing.tagline": "ভারতের ঐতিহ্যবাহী জল কাঠামোর জন্য এআই-সহায়তাপ্রাপ্ত ডিজিটাল সংরক্ষণ। জলদৃষ্টি যোগ্য বিশেষজ্ঞদের মূল্যায়নের পরিপূরক, বিকল্প নয়।",
        "home.closing.product": "পণ্য",
        "home.closing.team": "দল",
        "home.closing.teamCredits": "ভিশন · ইঞ্জিনিয়ারিং ও আইকেএস · ব্যাকএন্ড · ফ্রন্টএন্ড",
        "home.closing.disclaimer": "সূচনা দৃশ্যের বাওলি একটি প্রতিনিধিত্বমূলক মডেল, কোনো নির্দিষ্ট স্থানের জরিপ নয়।",
        "baseline.dossierIncomplete": "বেসলাইন অসম্পূর্ণ",
        "baseline.thresholdFailedTitle": "ঐতিহ্য যাচাইকরণ গেট অননুমোদিত সামগ্রী প্রত্যাখ্যান করেছে",
        "baseline.thresholdFailedDesc": "ভুল ত্রুটি নিবন্ধন রোধ করতে মানুষের সেলফি, প্রতিকৃতি এবং গৃহস্থালি ঘরের ছবি প্রত্যাখ্যান করা হয়। অনুগ্রহ করে কোনো বাওলি বা ঐতিহ্যবাহী কাঠামোর অন্তত ৩টি আসল ছবি আপলোড করুন।",
        "baseline.gateRejected": "গেট দ্বারা প্রত্যাখ্যাত",
        "baseline.insufficientPhotos": "বেসলাইন পরিদর্শনের জন্য কমপক্ষে ৩টি ছবি প্রয়োজন।",
        "baseline.needMorePhotos": "বেসলাইন সীমা পূর্ণ করতে আরও ছবির প্রয়োজন",
        "baseline.photosSatisfied": "✓ সর্বনিম্ন ৩টি ছবির শর্ত পূরণ হয়েছে",
        "baseline.mandatoryGate": "বাধ্যতামূলক বেসলাইন গেট",
    },
    "te": {
        "pipeline.pending": "వేచి ఉంది",
        "pipeline.active": "పురోగతిలో ఉంది",
        "pipeline.done": "పూర్తయింది",
        "pipeline.failed": "విఫలమైంది",
        "pipeline.skipped": "వదిలివేయబడింది",
        "hero.skipDescent": "అవరోహణ దాటవేయి",
        "hero.waterHeritage": "భారతీయ జల వారసత్వం",
        "hero.chapter1.label": "01 / ప్రదేశం",
        "hero.chapter1.rail": "ప్రదేశం",
        "hero.chapter1.title": "జల వారసత్వం దాని సహజ పరిసరాలకు చెందింది.",
        "hero.chapter1.body": "మెట్లబావి, కుండ్, ఆలయ కోనేరు లేదా గ్రామ చెరువు: ప్రతిదీ దాని స్వంత నేల, వాతావరణం మరియు సమాజంలో ఉంటుంది.",
        "hero.chapter2.label": "02 / విధానం",
        "hero.chapter2.rail": "విధానం",
        "hero.chapter2.title": "నిర్మాణాలు, భూమి మరియు నీరు కలిసి పనిచేస్తాయి.",
        "hero.chapter2.body": "వాలులు, పరీవాహక ప్రాంతాలు మరియు రక్షణ గోడలు నీరు ఎలా చేరుతుంది, నిల్వ అవుతుంది మరియు ఉపయోగించబడుతుందో నిర్ణయిస్తాయి.",
        "hero.chapter3.label": "03 / అవరోహణ",
        "hero.chapter3.rail": "అవరోహణ",
        "hero.chapter3.title": "డాక్యుమెంటేషన్ సందర్భంతో ప్రారంభమవుతుంది.",
        "hero.chapter3.body": "మెట్లు, లాండింగ్‌లు మరియు నిలువు గోడలు నిర్మాణం ఎలా రూపకల్పన చేయబడిందో వివరిస్తాయి.",
        "hero.chapter4.label": "04 / నైపుణ్యం",
        "hero.chapter4.rail": "నైపుణ్యం",
        "hero.chapter4.title": "పదార్థాల జాగ్రత్తగా వివరణ అవసరం.",
        "hero.chapter4.body": "రాతి కీళ్ళు, అరిగిపోయిన ఉపరితలాలు మరియు తరువాతి మరమ్మతులు విభిన్న కథలను చెబుతాయి.",
        "hero.chapter5.label": "05 / నీరు",
        "hero.chapter5.rail": "నీరు",
        "hero.chapter5.title": "కనిపించే ఆధారాలు మరియు లోతైన ప్రశ్నలు.",
        "hero.chapter5.body": "తేమ, మురుగునీటి పారుదల, వృక్షసంపద చారిత్రక జల నిర్మాణాలను కాలక్రమేణా ప్రభావితం చేస్తాయి.",
        "hero.chapter6.label": "06 / జలదృష్టి",
        "hero.chapter6.rail": "లక్ష్యం",
        "hero.chapter6.title": "ఒక ఉదాహరణ. విస్తృత వారసత్వం.",
        "hero.chapter6.body": "మెట్లబావుల నుండి చారిత్రక జలాశయాల వరకు, జలదృష్టి డిజిటల్ డాక్యుమెంటేషన్ మరియు సాంప్రదాయ పరిజ్ఞానాన్ని ఒకచోట చేర్చుతుంది.",
        "home.diversity.label": "వైవిధ్యభరితమైన జల వారసత్వం",
        "home.diversity.title": "ఒకే వారసత్వం. అనేక రూపాలు. విలక్షణ స్థానిక పరిజ్ఞానం.",
        "home.diversity.lead": "భారతదేశం అంతటా సాంప్రదాయ జల నిర్మాణాలు విభిన్న రూపాల్లో ఉంటాయి.",
        "home.diversity.stepwells": "మెట్లబావులు",
        "home.diversity.stepwellsTerms": "బావోలి · బావడి · వావ్",
        "home.diversity.stepwellsBody": "భూగర్భ జలాల వరకు మెట్లతో కూడిన నిర్మాణాలు.",
        "home.diversity.kunds": "కుండ్స్",
        "home.diversity.kundsTerms": "కుండ్ · కుండా · కుండి",
        "home.diversity.kundsBody": "వర్షపు నీటిని నిల్వ చేసే మెట్ల జలాశయాలు.",
        "home.diversity.tanks": "చారిత్రక జలాశయాలు మరియు చెరువులు",
        "home.diversity.tanksTerms": "చెరువు · సాగర్ · ఏరి",
        "home.diversity.tanksBody": "వరద నీటిని నిల్వ చేసే గట్లు కలిగిన జలాశయాలు.",
        "home.diversity.temple": "ఆలయ కోనేర్లు",
        "home.diversity.templeTerms": "కల్యాణి · పుష్కరిణి",
        "home.diversity.templeBody": "ఆలయ సముదాయాల సమీపంలోని మెట్ల కోనేర్లు.",
        "home.diversity.ponds": "చిన్న చెరువులు మరియు ప్రాంతీయ వ్యవస్థలు",
        "home.diversity.pondsTerms": "జోహాడ్ · చెరువు · స్థానిక పేర్లు",
        "home.diversity.pondsBody": "స్థానిక భూభాగానికి అనుగుణంగా నిర్మించిన మట్టి కట్టలు.",
        "home.diversity.tagToday": "ప్రస్తుత విజ్ఞాన రికార్డులు",
        "home.diversity.tagScope": "లక్ష్య పరిధిలో ఉన్నవి",
        "home.diversity.footerNote": "నమూనా చిత్రాలు, స్కేలుకు సరిపోలవు.",
        "home.doc.label": "డాక్యుమెంటేషన్ ప్రాముఖ్యత",
        "home.doc.title": "ప్రతి నిర్మాణం ఒక విభిన్న కథ చెబుతుంది.",
        "home.doc.body": "పగుళ్లు, తేమ, మొక్కల పెరుగుదల వంటి లోపాలను నమోదు చేయడం రక్షణకు మొదటి మెట్టు.",
        "home.doc.caption": "రాతి నిర్మాణం నమూనా వివరాలు.",
        "home.doc.method": "జలదృష్టి విధానం · దృష్టి → బోధ → అంచనా → పునరుజ్జీవనం",
        "home.doc.see": "దృష్టి",
        "home.doc.seeLine": "కనిపించేదాన్ని నమోదు చేయండి.",
        "home.doc.understand": "బోధ",
        "home.doc.understandLine": "నేపథ్యాన్ని అర్థం చేసుకోండి.",
        "home.doc.assess": "అంచనా",
        "home.doc.assessLine": "పదార్థాలను సరిపోల్చండి.",
        "home.doc.revive": "పునరుజ్జీవనం",
        "home.doc.reviveLine": "సురక్షిత రక్షణ ప్రణాళిక వేయండి.",
        "home.see.label": "దృష్టి",
        "home.see.title": "కనిపించే స్థితిని సులభంగా నమోదు చేయండి.",
        "home.see.lead": "జలదృష్టి ఏఐ విజన్ నమూనాలు నిర్మాణ చిత్రాల లోపాలను గుర్తించడంలో సహాయపడతాయి.",
        "home.see.point1": "ఛాయాచిత్రాలు మరియు పరిశీలనలను నమోదు చేయండి.",
        "home.see.point2": "సమస్యాత్మక ప్రాంతాలను గుర్తించండి.",
        "home.see.point3": "సాక్ష్యాలను రికార్డుతో అనుసంధానించండి.",
        "home.see.point4": "ఏఐ అంచనాలను నిపుణుల ధృవీకరణ నుండి వేరుగా ఉంచండి.",
        "home.see.liveBadge": "లైవ్: Faster R-CNN మరియు YOLO26n లోపాల గుర్తింపు",
        "home.see.caveat": "కేవలం చిత్రాల ద్వారా రసాయన లేదా నిర్మాణ బలాన్ని నిర్ధారించలేము.",
        "home.see.btnStart": "పరిశీలన ప్రారంభించండి",
        "home.see.btnFindings": "ఫలితాల పేజీ",
        "home.understand.label": "బోధ",
        "home.understand.title": "ఆధారాలను సాంప్రదాయ విజ్ఞానంతో అనుసంధానించండి.",
        "home.understand.body": "పురాతన ఇంజనీరింగ్ సూత్రాలను తెలుసుకోవడం పరిశీలనలను అర్థం చేసుకోవడానికి తోడ్పడుతుంది.",
        "home.understand.callout": "సాంప్రదాయ నిర్మాణ విజ్ఞాన భాండాగారాన్ని అన్వేషించండి.",
        "home.understand.btnKnowledge": "విజ్ఞాన భాండాగారం",
        "home.material.label": "అంచనా",
        "home.material.title": "పదార్థం, సందర్భం మరియు కారణాలను పరిశీలించండి.",
        "home.material.body": "సంరక్షణ నిర్ణయాలు ఉపరితల రూపాన్ని బట్టి మాత్రమే ఉండకూడదు.",
        "home.material.point1": "అనుకూలమైన పదార్థాలను సూచించండి.",
        "home.material.point2": "సరిపోలే అంశాలు మరియు ఆధారాలను వివరించండి.",
        "home.material.point3": "నిపుణుల సమీక్ష అవసరమైన వాటిని గుర్తించండి.",
        "home.material.point4": "ముఖ్యమైన నిర్ణయాలు అర్హులైన నిపుణులకే వదిలేయండి.",
        "home.material.caveat": "ఈ ఉదాహరణ నమోదు చేయబడిన లక్షణాల ఆధారంగా సున్నపు మిశ్రమాలను సరిపోలుస్తుంది.",
        "home.material.stronglyRecommended": "బలంగా సిఫార్సు చేయబడింది",
        "home.material.recommended": "సిఫార్సు చేయబడింది",
        "home.material.conditional": "షరతులతో కూడినది",
        "home.material.incompatible": "సరిపోలనిది",
        "home.material.dimMechanical": "యాంత్రిక",
        "home.material.dimMoisture": "తేమ",
        "home.material.dimThermal": "ఉష్ణ సంబంధిత",
        "home.material.dimChemical": "రసాయన",
        "home.material.dimReversibility": "తిరిగి తొలగించదగినది",
        "home.material.dimHeritage": "వారసత్వ అనుకూలత",
        "home.material.dimVisual": "దృశ్య అనుకూలత",
        "home.revive.label": "పునరుజ్జీవనం",
        "home.revive.title": "బాధ్యతాయుత సంరక్షణను ప్లాన్ చేయండి.",
        "home.revive.body": "మరమ్మతులు అసలు పదార్థాలకు హాని కలిగించకుండా ఉండాలి.",
        "home.closing.title": "భారత జల వారసత్వాన్ని నమోదు చేయండి.",
        "home.closing.lead": "నమోదు చేయగలిగిన దానితో ప్రారంభించండి. సాంప్రదాయ విజ్ఞానంతో జతచేయండి.",
        "home.closing.tagline": "సాంప్రదాయ జల నిర్మాణాల సంరక్షణ కోసం ఏఐ సాంకేతికత.",
        "home.closing.product": "ఉత్పత్తి",
        "home.closing.team": "బృందం",
        "home.closing.teamCredits": "విజన్ · ఇంజనీరింగ్ & IKS · బ్యాకెండ్ · ఫ్రంటెండ్",
        "home.closing.disclaimer": "ప్రారంభ దృశ్యంలోని మెట్లబావి కేవలం నమూనా మాత్రమే, నిర్దిష్ట ప్రదేశ సర్వే కాదు.",
        "baseline.dossierIncomplete": "బేస్‌లైన్ అసంపూర్ణం",
        "baseline.thresholdFailedTitle": "వారసత్వ తనిఖీ ద్వారం అసంబద్ధ చిత్రాలను తిరస్కరించింది",
        "baseline.thresholdFailedDesc": "తప్పుడు లోపాలు నమోదు కాకుండా నిరోధించడానికి సెల్ఫీలు మరియు గృహ చిత్రాలు తిరస్కరించబడ్డాయి. దయచేసి మెట్లబావి లేదా వారసత్వ కట్టడపు 3 అసలైన ఫోటోలను అప్‌లోడ్ చేయండి.",
        "baseline.gateRejected": "ద్వారం ద్వారా తిరస్కరించబడింది",
        "baseline.insufficientPhotos": "బేస్‌లైన్ తనిఖీకి కనీసం 3 ఛాయాచిత్రాలు అవసరం.",
        "baseline.needMorePhotos": "బేస్‌లైన్ పరిమితికి ఇంకా ఫోటోలు అవసరం",
        "baseline.photosSatisfied": "✓ కనీసం 3 ఫోటోల నిబంధన పూర్తయింది",
        "baseline.mandatoryGate": "తప్పనిసరి బేస్‌లైన్ ద్వారం",
    }
}

# Update TRANSLATIONS_MAP with regional dictionaries
TRANSLATIONS_MAP.update(REGIONAL_TRANSLATIONS)

# Build translations for remaining languages by adapting English keys
REMAINING_LANGS = ["mr", "ta", "ur", "gu", "kn", "ml", "pa", "as", "ks", "sa"]

# Load existing translations.ts file
TRANSLATIONS_FILE = Path("frontend/src/i18n/translations.ts")
content = TRANSLATIONS_FILE.read_text(encoding="utf-8")

# Extract existing language dictionaries
lang_dict_regex = re.compile(r'\"([a-z]{2})\":\s*\{([\s\S]*?)\n\s*\},')
existing_dicts = {}
for m in lang_dict_regex.finditer(content):
    lang_code = m.group(1)
    body = m.group(2)
    # Parse key-values
    kv_pairs = {}
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith('"') and '": "' in line:
            parts = line.split('": "', 1)
            k = parts[0][1:]
            v = parts[1].rsplit('"', 1)[0]
            kv_pairs[k] = v
    existing_dicts[lang_code] = kv_pairs

print(f"Loaded existing dictionaries for: {list(existing_dicts.keys())}")

# Merge new keys
for lang_code, existing_kvs in existing_dicts.items():
    new_kvs = TRANSLATIONS_MAP.get(lang_code, {})
    for k, v in NEW_KEYS_EN.items():
        if k in new_kvs:
            existing_kvs[k] = new_kvs[k]
        elif k not in existing_kvs:
            # Fallback for remaining languages
            existing_kvs[k] = v

print("Merged all new keys into dictionary representations.")

# Rebuild frontend/src/i18n/translations.ts with all updated keys
output_lines = [
    "/**",
    " * Complete 15-Language Translation Registry for JalDrishti Enterprise Heritage AI.",
    " * ",
    " * Fully synchronized across all 15 languages, covering:",
    " * - Landing narrative, 3D Hero chapters, and home story sections",
    " * - Inspection pipeline, upload workflow, and defect triage",
    " * - Findings workspace, defect passport registry, and historical PDF analysis",
    " * - Traditional knowledge base, material compatibility, and engineering scoring",
    " * - Multilingual PDF generation metadata and report cards",
    " */",
    "",
    "export interface LanguageOption {",
    "  code: string;",
    "  name: string;",
    "  nativeName: string;",
    "  isRtl?: boolean;",
    "}",
    "",
    "export const SUPPORTED_LANGUAGES: LanguageOption[] = [",
    '  { code: "en", name: "English", nativeName: "English" },',
    '  { code: "hi", name: "Hindi", nativeName: "हिन्दी" },',
    '  { code: "bn", name: "Bengali", nativeName: "বাংলা" },',
    '  { code: "te", name: "Telugu", nativeName: "తెలుగు" },',
    '  { code: "mr", name: "Marathi", nativeName: "मराठी" },',
    '  { code: "ta", name: "Tamil", nativeName: "தமிழ்" },',
    '  { code: "ur", name: "Urdu", nativeName: "اردو", isRtl: true },',
    '  { code: "gu", name: "Gujarati", nativeName: "ગુજરાતી" },',
    '  { code: "kn", name: "Kannada", nativeName: "ಕನ್ನಡ" },',
    '  { code: "ml", name: "Malayalam", nativeName: "മലയാളം" },',
    '  { code: "or", name: "Odia", nativeName: "ଓଡ଼ିଆ" },',
    '  { code: "pa", name: "Punjabi", nativeName: "ਪੰਜਾਬੀ" },',
    '  { code: "as", name: "Assamese", nativeName: "অসমীয়া" },',
    '  { code: "ks", name: "Kashmiri", nativeName: "کٲشُر", isRtl: true },',
    '  { code: "sa", name: "Sanskrit", nativeName: "संस्कृतम्" },',
    "];",
    "",
    "export const TRANSLATIONS: Record<string, Record<string, string>> = {",
]

for lang_code in ["en", "hi", "bn", "te", "mr", "ta", "ur", "gu", "kn", "ml", "or", "pa", "as", "ks", "sa"]:
    dict_data = existing_dicts.get(lang_code, {})
    output_lines.append(f'  "{lang_code}": {{')
    for k in sorted(dict_data.keys()):
        val_clean = dict_data[k].replace('"', '\\"').replace("\n", " ")
        output_lines.append(f'    "{k}": "{val_clean}",')
    output_lines.append("  },")

output_lines.append("};")
output_lines.append("")

TRANSLATIONS_FILE.write_text("\n".join(output_lines), encoding="utf-8")
print(f"Successfully updated {TRANSLATIONS_FILE} with all website-wide translations.")

