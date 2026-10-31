"""Expand Full Website Translations across all 15 languages for JalDrishti.

Includes:
- Pipeline stage status values (pending, active, done, failed, skipped)
- Hero 3D chapters and narration
- Homepage narrative sections (Diversity, Documentation, See, Understand, Material, Revive, Closing)
- Baseline inspection wizard warnings and threshold notifications
- Full site-wide UI terms
"""

import json
from pathlib import Path

# Base English dictionary for new website-wide keys
NEW_KEYS_EN = {
    # Pipeline stage statuses
    "pipeline.pending": "Waiting",
    "pipeline.active": "In progress",
    "pipeline.done": "Complete",
    "pipeline.failed": "Failed",
    "pipeline.skipped": "Skipped",

    # Hero Scene & 3D Chapters
    "hero.skipDescent": "Skip descent",
    "hero.waterHeritage": "India's water heritage",
    "hero.chapter1.label": "01 / The place",
    "hero.chapter1.rail": "Place",
    "hero.chapter1.title": "Water heritage belongs to its landscape.",
    "hero.chapter1.body": "A stepwell, a kund, a temple tank, a village pond: each sits within its own ground, climate, and community. The stepwell here is one illustrative example. Understanding any of them begins by looking beyond the structure itself.",
    "hero.chapter2.label": "02 / The approach",
    "hero.chapter2.rail": "Approach",
    "hero.chapter2.title": "Structures, land, and water work together.",
    "hero.chapter2.body": "Slopes, catchments, approaches, and enclosing walls shape how water arrives, is held, and is reached. The form of each traditional water structure responds to its own setting.",
    "hero.chapter3.label": "03 / The descent",
    "hero.chapter3.rail": "Descent",
    "hero.chapter3.title": "Documentation begins with context.",
    "hero.chapter3.body": "Stairs, landings, retaining walls, and changing levels are evidence of how a structure was designed and used. Recording them in context gives every later observation a place to belong.",
    "hero.chapter4.label": "04 / The craft",
    "hero.chapter4.rail": "Craft",
    "hero.chapter4.title": "Materials need careful interpretation.",
    "hero.chapter4.body": "Joints, worn surfaces, displaced masonry, and later repairs may each tell a different story. A careful record helps separate what is original, what has changed, and what needs closer study.",
    "hero.chapter5.label": "05 / The water",
    "hero.chapter5.rail": "Water",
    "hero.chapter5.title": "Visible evidence, wider questions.",
    "hero.chapter5.body": "Moisture, drainage, vegetation, and the surrounding environment influence how historic water structures change over time. A photograph offers clues; understanding causes often needs investigation on site.",
    "hero.chapter6.label": "06 / JalDrishti",
    "hero.chapter6.rail": "Mission",
    "hero.chapter6.title": "One example. A much wider heritage.",
    "hero.chapter6.body": "From stepwells and kunds to historic tanks and regional water systems, JalDrishti brings digital documentation, traceable knowledge, and conservation-oriented insight together to support how India's water heritage is understood and cared for.",

    # Homepage Diversity Section
    "home.diversity.label": "A diverse water heritage",
    "home.diversity.title": "One heritage. Many forms. Distinct local knowledge.",
    "home.diversity.lead": "Across India, traditional water structures take many forms. Stepwells, baolis, kunds, tanks, ponds, and other regional systems respond to different landscapes, communities, materials, and relationships with water. Understanding them requires attention to their individual context.",
    "home.diversity.stepwells": "Stepwells",
    "home.diversity.stepwellsTerms": "Baoli · Bawari · Vav",
    "home.diversity.stepwellsBody": "Stepped descents to groundwater, with landings, retaining walls and, in many cases, galleries and a well shaft. The form shown in the opening is one illustrative example.",
    "home.diversity.kunds": "Kunds",
    "home.diversity.kundsTerms": "Kund · Kunda · Kundi",
    "home.diversity.kundsBody": "Stepped reservoirs that gather rainwater, often an inverted stepped pyramid with a paved catchment around the rim.",
    "home.diversity.tanks": "Historic tanks and reservoirs",
    "home.diversity.tanksTerms": "Talab · Sagar · Eri",
    "home.diversity.tanksBody": "Embanked bodies of water that hold seasonal runoff, from village tanks to larger reservoirs with inlets, sluices and ghats.",
    "home.diversity.temple": "Temple tanks",
    "home.diversity.templeTerms": "Kalyani · Pushkarini",
    "home.diversity.templeBody": "Tanks within or beside temple complexes, frequently stepped on every side and bound up with ritual and civic life.",
    "home.diversity.ponds": "Ponds and regional systems",
    "home.diversity.pondsTerms": "Johad · Pond · local terms",
    "home.diversity.pondsBody": "Earthen embankments, village ponds and other regional ways of catching, holding and sharing water, each shaped by local terrain and practice.",
    "home.diversity.tagToday": "Knowledge records today",
    "home.diversity.tagScope": "Within the intended scope",
    "home.diversity.footerNote": "Schematic sections and plans, not to scale. Regional names overlap and vary; these are examples, not a catalogue. 'Knowledge records today' marks the typologies in JalDrishti's current knowledge base.",

    # Homepage Documentation Section
    "home.doc.label": "Why documentation matters",
    "home.doc.title": "Every structure tells a different story.",
    "home.doc.body": "Visible deterioration can take many forms: cracks, displaced material, moisture, vegetation, surface loss, or signs of earlier intervention. Their significance depends on the structure and the conditions around it. Good documentation creates a clearer starting point for investigation and conservation.",
    "home.doc.caption": "Illustrative detail of coursed masonry · Visible signs are where a record begins, not where a diagnosis ends.",
    "home.doc.method": "The JalDrishti method · See → Understand → Assess → Revive",
    "home.doc.see": "See",
    "home.doc.seeLine": "Document what is visible.",
    "home.doc.understand": "Understand",
    "home.doc.understandLine": "Recover the context behind it.",
    "home.doc.assess": "Assess",
    "home.doc.assessLine": "Weigh materials and interventions.",
    "home.doc.revive": "Revive",
    "home.doc.reviveLine": "Plan care that can be accounted for.",

    # Homepage See Section
    "home.see.label": "See",
    "home.see.title": "Make the visible condition easier to document.",
    "home.see.lead": "JalDrishti's AI-assisted vision workflow aims to help organise observable patterns from inspection imagery. By making visual evidence easier to review and document, it can support a more structured starting point for understanding a heritage structure.",
    "home.see.point1": "Record site photographs and observations.",
    "home.see.point2": "Identify candidate areas of concern where the implemented model supports them.",
    "home.see.point3": "Keep visual evidence connected to the relevant inspection.",
    "home.see.point4": "Distinguish model-generated observations from expert-confirmed findings.",
    "home.see.liveBadge": "Live today: fine-tuned Faster R-CNN & unified YOLO26n damage detection",
    "home.see.caveat": "It has not been validated across every type of water structure, and image-based observations cannot establish structural stability, hidden defects or material chemistry.",
    "home.see.btnStart": "Start an inspection",
    "home.see.btnFindings": "Findings workspace",

    # Homepage Understand Section
    "home.understand.label": "Understand",
    "home.understand.title": "Connect what is visible with what is known.",
    "home.understand.body": "Traditional water structures were built with indigenous engineering principles that balanced ground pressure, seasonal water levels, and local stone behavior. Recovering this context helps interpret what we observe.",
    "home.understand.callout": "Explore the curated indigenous knowledge base covering structural typologies, materials, and historical engineering.",
    "home.understand.btnKnowledge": "Explore knowledge base",

    # Homepage Material Section
    "home.material.label": "Assess",
    "home.material.title": "Consider the material, the context, and the cause.",
    "home.material.body": "Conservation decisions depend on more than the appearance of a damaged surface. Existing materials, construction, moisture, drainage, prior repairs, local practices, and possible causes of deterioration all deserve consideration. JalDrishti is intended to support this thinking with organised observations and conservation-oriented material considerations.",
    "home.material.point1": "Present candidate material or intervention considerations where implemented.",
    "home.material.point2": "Explain relevant compatibility factors and evidence.",
    "home.material.point3": "Flag cases that require inspection, testing, or professional review.",
    "home.material.point4": "Keep consequential decisions with qualified practitioners.",
    "home.material.caveat": "The example on this page compares candidate mortars against a substrate using rule-based indications from documented material properties, not laboratory results. Photographs alone cannot establish mortar chemistry or structural capacity; original materials must be identified on site.",
    "home.material.stronglyRecommended": "Strongly recommended",
    "home.material.recommended": "Recommended",
    "home.material.conditional": "Conditional",
    "home.material.incompatible": "Incompatible",
    "home.material.dimMechanical": "Mechanical",
    "home.material.dimMoisture": "Moisture",
    "home.material.dimThermal": "Thermal",
    "home.material.dimChemical": "Chemical",
    "home.material.dimReversibility": "Reversibility",
    "home.material.dimHeritage": "Heritage",
    "home.material.dimVisual": "Visual",

    # Homepage Revive Section
    "home.revive.label": "Revive",
    "home.revive.title": "Plan care that can be accounted for.",
    "home.revive.body": "Establish reversible, compatible conservation roadmaps rooted in traditional engineering and verified structural analysis.",

    # Homepage Closing Section
    "home.closing.title": "Document India's water heritage.",
    "home.closing.lead": "Begin with what can be documented. Connect it with what is known. Build a clearer basis for considering how it should be cared for.",
    "home.closing.tagline": "AI-assisted digital conservation for India's traditional water structures. JalDrishti supports — and does not replace — assessment by qualified conservation professionals.",
    "home.closing.product": "Product",
    "home.closing.team": "Team",
    "home.closing.teamCredits": "Vision · Engineering & IKS · Backend · Frontend",
    "home.closing.disclaimer": "The stepwell and site in the opening sequence are an illustrative composite, modelled procedurally: one example of India's water heritage, not a survey of a specific site.",

    # Baseline Inspection Wizard
    "baseline.dossierIncomplete": "Baseline Incomplete",
    "baseline.thresholdFailedTitle": "Heritage Verification Gate Rejected Non-Heritage Content",
    "baseline.thresholdFailedDesc": "Photographs of human selfies, portraits, and indoor domestic scenes are rejected to prevent false defect registration. Please upload at least 3 genuine photographs of a baoli, stepwell, or heritage masonry structure.",
    "baseline.gateRejected": "Gate Rejected",
    "baseline.insufficientPhotos": "At least 3 photographs are required for a baseline inspection.",
    "baseline.needMorePhotos": "Need more photo(s) to satisfy baseline threshold",
    "baseline.photosSatisfied": "✓ Minimum 3 photos threshold satisfied",
    "baseline.mandatoryGate": "Feature 2 & 3: Mandatory Baseline Gate",
}

print(f"Total new keys defined: {len(NEW_KEYS_EN)}")

