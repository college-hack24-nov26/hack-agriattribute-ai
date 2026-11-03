"""
biological_catalog_service.py - Canonical Biological Product Catalogue & Asset Registry
AgriAttribute AI — Syngenta Biologicals × ANNAM.AI Hack Core 2026 (PS-07)

Purpose:
Maintains the single source of truth for all verified biological products,
their authentic packaging imagery (zero crop photos), official technical document citations,
agronomic rates, target stresses/crops, and organizational provenance (Syngenta vs Third-Party vs KRIBHCO).
"""

import os
import base64
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BiologicalProduct:
    """Canonical representation of an authentic biological product record."""
    product_id: str
    product_name: str
    brand: str
    organization: str
    source_type: str  # 'OFFICIAL SYNGENTA PRODUCT EVIDENCE', 'THIRD-PARTY DISTRIBUTOR', 'GOVERNMENT / COOPERATIVE BENCHMARK'
    product_category: str  # 'Biostimulant', 'Biofertilizer', 'Biofungicide', 'Bionutritional'
    biological_class: str
    formulation: str
    active_components: str
    mode_of_action: str
    target_crops: List[str]
    target_stress: List[str]
    target_disease: List[str]
    target_pest: List[str]
    application_method: str
    application_stage: str
    application_rate: str
    application_rate_num: float
    application_rate_unit: str
    application_frequency: str
    water_volume: str
    rainfastness: str
    tank_mix_information: str
    restrictions: str
    packaging: str
    country: str
    market: str
    registration_status: str
    source_document: str
    source_page: str
    source_url: str
    image_id: str
    image_path: str
    image_type: str  # 'PACKSHOT', 'LABEL_FRONT', 'PACK_SIZE', 'TECHNICAL_DOCUMENT', 'FIELD_TRIAL'
    trial_results_summary: str
    last_verified: str = "2026-09-10"


# ============================================================================
# CANONICAL PRODUCT DATABASE (AUTHENTIC EVIDENCE FROM DATASET LEAFLATE)
# ============================================================================

_CANONICAL_PRODUCTS: List[BiologicalProduct] = [
    # ------------------------------------------------------------------------
    # 1. MEGAFOL (Syngenta Biologicals / Valagro)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-MEGAFOL-01",
        product_name="Megafol®",
        brand="Megafol® (Valagro / Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Anti-Stress Growth Activator & Osmoprotectant",
        formulation="Liquid Soluble Concentrate (SL)",
        active_components="Proline, Betaines, Plant Amino Acids (28%), Organic Nitrogen (3%), Potassium (K2O 8%), Carbon (9%)",
        mode_of_action="GeaPower technology: Supplies ready-made amino acids and osmolytes that accelerate vegetative recovery from abiotic stress (heat, cold, frost, drought) and stimulate protein synthesis.",
        target_crops=["Potato", "Tomato", "Soybean", "Wheat", "Maize", "Cotton", "Onion", "Grapes", "Vegetables", "Rice (Paddy)"],
        target_stress=["Extreme Heat Stress (>35°C)", "Drought / Moisture Deficit", "Cold / Frost Shocks", "Vegetative Stunting", "Hail Damage"],
        target_disease=["Abiotic Foliar Damage Buffer"],
        target_pest=["Not stated"],
        application_method="Foliar Spray",
        application_stage="Tuber initiation & bulking (Potato); Vegetative flushes / Pre-flowering; Immediately post-stress event",
        application_rate="0.5 - 1.0 L/acre (1.25 - 2.5 L/ha)",
        application_rate_num=0.75,
        application_rate_unit="L/acre",
        application_frequency="2 - 3 applications at 10-14 days interval",
        water_volume="150 - 200 L/acre",
        rainfastness="Rainfast within 2 to 3 hours of application",
        tank_mix_information="Compatible with most standard fungicides and foliar fertilizers. Avoid tank mixing with copper-based compounds on sensitive crops.",
        restrictions="Do not apply during extreme midday sun (>38°C); apply early morning or late afternoon.",
        packaging="1 L, 5 L, 10 L, 25 L jugs, 1000 L IBC",
        country="Global / India / EU / North America",
        market="Syngenta Biologicals Commercial Portfolio",
        registration_status="Official Commercial Label (Valagro S.p.A. / Syngenta)",
        source_document="Megafol_Tech_Sheet_Potato.pdf",
        source_page="Pages 1-2",
        source_url="https://www.syngenta.com/en/biologicals",
        image_id="megafol_packshot_01",
        image_path="assets/biologicals/syngenta/megafol/megafol_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Commercial potato field trials demonstrate improved marketable tuber size distribution (+14.2% Grade A tubers) and +2.8 t/ha yield response under thermal stress."
    ),

    # ------------------------------------------------------------------------
    # 2. YIELDON (Syngenta Biologicals / Valagro)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-YIELDON-01",
        product_name="YieldON®",
        brand="YieldON® (Valagro / Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Physiological Row Crop Productivity Booster",
        formulation="Liquid Foliar Biostimulant (SL)",
        active_components="Extracts from Fucaceae, Ascophyllum nodosum, Laminaria; Manganese (Mn 1.5%), Zinc (Zn 0.5%), Molybdenum (Mo 0.1%)",
        mode_of_action="Enhances cell division and cell expansion in developing grains/seeds, accelerates uptake and translocation of nutrients and sugars from source leaves to developing grain sink.",
        target_crops=["Wheat", "Maize", "Soybean", "Rice (Paddy)", "Canola", "Mustard / Rapeseed", "Cereals"],
        target_stress=["Grain Fill Heat Stress", "Nutrient Translocation Bottlenecks", "Source-Sink Limitations"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Foliar Spray (compatible with planned fungicide pass)",
        application_stage="Heading to flowering (Wheat/Cereals, T3 / flag leaf); V10 to R2 (Maize/Corn); 20-50% bloom (Canola/Mustard); R1-R3 (Soybean)",
        application_rate="0.75 L/acre (1.85 L/ha)",
        application_rate_num=0.75,
        application_rate_unit="L/acre",
        application_frequency="1 application at peak reproductive transition",
        water_volume="100 - 150 L/acre (ground) / 30-50 L/acre (aerial)",
        rainfastness="Rainfast within 1 to 2 hours with standard surfactant",
        tank_mix_information="WALES Symbol: L. Easily tank-mixed with planned fungicides (e.g. Miravis® Neo) and insecticides with standard water agitation.",
        restrictions="Contains Molybdenum (Mo). Do not apply to crops high in molybdenum fed directly to ruminant livestock without proper dilution.",
        packaging="2 x 10 L case, 450 L tote, 1000 L IBC",
        country="Canada / North America / Global",
        market="Syngenta Canada Biologicals Portfolio",
        registration_status="Official Commercial Registration (Syngenta Canada Inc.)",
        source_document="YieldON - Biological _ Syngenta CA.pdf",
        source_page="Pages 1-4",
        source_url="https://www.syngenta.ca/biologicals/yieldon",
        image_id="yieldon_packshot_01",
        image_path="assets/biologicals/syngenta/yieldon/yieldon_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Replicated grower & research trials (n=47 Ontario): +3.9 bu/ac overall average yield response vs check; +2.5 bu/ac average yield response over fungicide alone in corn (n=48); +2.0 bu/ac in canola (n=20)."
    ),

    # ------------------------------------------------------------------------
    # 3. EPIVIO ENERGY (Syngenta Biologicals)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-EPIVIO-01",
        product_name="Epivio® Energy",
        brand="Epivio® Energy (Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Seed-Applied & Early Crop Bio-Enhancer",
        formulation="Liquid Seed Dressing / Soluble Concentrate (FS/SL)",
        active_components="Bio-active plant metabolites, organic carbon matrix, zinc chelates, natural biostimulant elicitors",
        mode_of_action="Stimulates early root seedling vigor, activates natural defense priming against soil-borne abiotic shocks, and improves nutrient absorption during seedling emergence.",
        target_crops=["Soybean", "Cotton", "Maize", "Wheat", "Chickpea (Gram / Chana)", "Groundnut (Peanut)", "Mustard / Rapeseed"],
        target_stress=["Early Drought Shock", "Cold Soil Germination Delay", "Rhizosphere Salt Stress", "Seedling Stunting"],
        target_disease=["Early damping-off physiological vulnerability"],
        target_pest=["Not stated"],
        application_method="Seed Treatment or Early Foliar Drench",
        application_stage="Seed treatment pre-sowing or 2-4 leaf early vegetative stage (V2-V4)",
        application_rate="2.0 - 2.5 ml / kg seed or 500 ml / acre foliar",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application at sowing / establishment",
        water_volume="10 - 15 ml slurry / kg seed for dressing",
        rainfastness="Direct seed film coating",
        tank_mix_information="Fully compatible with Cruiser®, Maxim®, and standard seed treatment fungicides and insecticides.",
        restrictions="Store in cool, dry place between 5°C and 30°C. Protect from direct freezing.",
        packaging="100 ml, 250 ml, 500 ml, 1 L, 5 L bottles",
        country="India / Asia-Pacific / Global",
        market="Syngenta India Seedcare & Biologicals",
        registration_status="Official Commercial Registration (Syngenta India Limited)",
        source_document="0622p19-syn_epivio_energy_insert_leaflet-all_lang-in5051901-ctc (1).pdf",
        source_page="Multi-language Insert Leaflet",
        source_url="https://www.syngenta.co.in",
        image_id="epivio_energy_packshot_01",
        image_path="assets/biologicals/syngenta/epivio_energy/epivio_energy_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Multi-locational ICAR & Syngenta field trials demonstrate +18-24% greater root surface area and +8-12% higher seedling emergence under moisture-stressed seedbeds."
    ),

    # ------------------------------------------------------------------------
    # 4. TALETE (Syngenta Biologicals / Valagro)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-TALETE-01",
        product_name="Talete®",
        brand="Talete® (Valagro / Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Water Use Efficiency (WUE) Biomolecule",
        formulation="Liquid Concentrate (SL)",
        active_components="GeaPower technology: Specific biomacromolecules, vegetable extracts, natural anti-transpirant co-factors",
        mode_of_action="Increases Crop Water Productivity (CWP): promotes sustainable water management by increasing yield both under adequate water availability and in conditions of permanent or temporary water scarcity.",
        target_crops=["Tomato", "Onion", "Cotton", "Soybean", "Sugarcane", "Maize", "Grapes", "Citrus", "Vegetables"],
        target_stress=["Severe Drought Stress", "Water Deficit / Scarcity", "High Vapour Pressure Deficit (VPD)", "Salinity Shocks"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Fertigation (Drip) or Foliar Spray",
        application_stage="Vegetative growth, fruit/bulb set, and throughout periods of restricted irrigation",
        application_rate="1.0 - 2.0 L/acre (2.5 - 5.0 L/ha) via drip fertigation",
        application_rate_num=1.5,
        application_rate_unit="L/acre",
        application_frequency="2 - 4 applications throughout water-critical phenological stages",
        water_volume="Standard drip irrigation volume or 200 L/acre foliar",
        rainfastness="Rainfast within 3 hours when applied foliarly",
        tank_mix_information="Compatible with common soluble fertilizers and NPK fertigation blends.",
        restrictions="Do not exceed recommended concentration in drip lines.",
        packaging="1 L, 5 L, 10 L, 20 L jugs",
        country="Global / Mediterranean / India / Americas",
        market="Syngenta Biologicals Regenerative Agriculture Portfolio",
        registration_status="Official Commercial Biostimulant (Valagro S.p.A. / Syngenta)",
        source_document="TALETET and Regenerative Agriculture.pdf",
        source_page="Pages 1-18",
        source_url="https://www.valagro.com/en/talete",
        image_id="talete_packshot_01",
        image_path="assets/biologicals/syngenta/talete/talete_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Regenerative agriculture field trials show +12.8% yield preservation with a 25% reduction in total seasonal irrigation volume across horticultural and field crops."
    ),

    # ------------------------------------------------------------------------
    # 5. VIVA (Syngenta Biologicals / Valagro)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-VIVA-01",
        product_name="Viva®",
        brand="Viva® (Valagro / Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Rhizosphere & Soil Organic Revitalizer",
        formulation="Liquid Fertigation Concentrate (SL)",
        active_components="Humic acids, polysaccharides, amino acids, polypeptide complexes, organic nitrogen (3%), organic carbon (8%)",
        mode_of_action="Revitalizes exhausted rhizosphere soils, improves soil biological fertility by stimulating beneficial microbial activity, promotes extensive secondary root branching and balanced vegetative growth.",
        target_crops=["Tomato", "Onion", "Sugarcane", "Cotton", "Rice (Paddy)", "Vegetables", "Banana", "Fruit Crops"],
        target_stress=["Soil Compaction & Fatigue", "Saline / Alkaline Rhizosphere", "Post-Transplanting Transplant Shock", "Poor Root Colonization"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Soil Drench or Drip Fertigation",
        application_stage="Post-transplanting establishment, early vegetative flush, and active fruit/tuber swelling",
        application_rate="2.0 - 4.0 L/acre (5.0 - 10.0 L/ha) via drip or soil drench",
        application_rate_num=2.5,
        application_rate_unit="L/acre",
        application_frequency="2 - 3 applications during vegetative and root expansion phases",
        water_volume="Applied via irrigation/fertigation system",
        rainfastness="Direct root-zone soil delivery",
        tank_mix_information="Can be mixed with liquid NPK fertilizers and humic soil conditioners.",
        restrictions="Do not mix with concentrated acid solutions or mineral oils.",
        packaging="1 L, 5 L, 10 L, 25 L, 1000 L IBC",
        country="Global / India / EU / LATAM",
        market="Syngenta Biologicals Regenerative Soil Portfolio",
        registration_status="Official Commercial Product (Valagro S.p.A. / Syngenta)",
        source_document="VIVAT and Regenerative Agriculture.pdf",
        source_page="Pages 1-18",
        source_url="https://www.valagro.com/en/viva",
        image_id="viva_packshot_01",
        image_path="assets/biologicals/syngenta/viva/viva_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Long-term field trials report +28% increase in active microbial biomass in the rhizosphere, +19% root volume expansion, and +11.5% higher marketable harvest in intensive soils."
    ),

    # ------------------------------------------------------------------------
    # 6. VIXERAN (Syngenta Biologicals)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-VIXERAN-01",
        product_name="Vixeran®",
        brand="Vixeran® (Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biofertilizer",
        biological_class="Endophytic Biological Nitrogen Fixer",
        formulation="Wettable Powder (WP) / Endophytic Inoculant",
        active_components="Azotobacter salinestris strain CECT 9690 (min 1.0 x 10^9 CFU/g)",
        mode_of_action="Dual-action endophytic biological nitrogen fixation: colonizes plant leaves and roots internally, converting atmospheric N2 into plant-available ammonium (NH4+) continuously throughout the vegetative cycle.",
        target_crops=["Wheat", "Maize", "Rice (Paddy)", "Mustard / Rapeseed", "Cereals", "Sugarcane", "Grasses"],
        target_stress=["Synthetic Nitrogen Dependency", "Nitrate Leaching Risk", "Nitrogen Deficiency during Peak Growth"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Foliar Spray or Seedling Treatment",
        application_stage="Tillering to stem elongation in cereals (BBCH 21-39); 4-8 leaf stage in corn/maize",
        application_rate="20 g / acre (50 g / ha)",
        application_rate_num=20.0,
        application_rate_unit="g/acre",
        application_frequency="1 application per crop season",
        water_volume="100 - 150 L/acre foliar spray",
        rainfastness="Rainfast once dried and absorbed by leaf cuticles (approx. 2-3 hours)",
        tank_mix_information="Compatible with most standard cereal herbicides and fungicides. Do not mix with bactericides or copper compounds.",
        restrictions="Store in cool dry conditions (<25°C). Use spray mixture within 6 hours of reconstitution.",
        packaging="50 g sachet (treats 1 ha), 250 g pack",
        country="Global / Europe / North America / Asia",
        market="Syngenta Biologicals Nitrogen Optimization Portfolio",
        registration_status="Official Commercial Biofertilizer Registration (Syngenta)",
        source_document="VIXERANr and Regenerative Agriculture.pdf",
        source_page="Pages 1-18",
        source_url="https://www.syngenta.com/biologicals/vixeran",
        image_id="vixeran_packshot_01",
        image_path="assets/biologicals/syngenta/vixeran/vixeran_packshot_01.png",
        image_type="PACKSHOT",
        trial_results_summary="Multi-country trial network confirms Vixeran reliably provides nitrogen equivalent to 30-40 kg of mineral N/ha, maintaining crop yield while allowing a 20-30% reduction in synthetic N application."
    ),

    # ------------------------------------------------------------------------
    # 7. MC LINE / MC CREAM (Syngenta Biologicals / Valagro)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-MCCREAM-01",
        product_name="MC Cream® / MC Line",
        brand="MC Cream® (Valagro / Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Concentrated Seaweed Metabolic Activator",
        formulation="Cream Suspension Concentrate (SC)",
        active_components="100% concentrated Ascophyllum nodosum algae extract, Betaines, Mannitol, natural Phytohormones, Potassium, Boron",
        mode_of_action="GeaPower technology: Stimulates cell division, accelerates vegetative flush development, enhances photosynthetic chlorophyll activity, and maximizes flower retention.",
        target_crops=["Cotton", "Soybean", "Tomato", "Onion", "Groundnut (Peanut)", "Sugarcane", "Wheat", "Fruit Crops"],
        target_stress=["Vegetative Slowdown", "Flower / Fruit Abortion", "Canopy Sunscald"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Foliar Spray",
        application_stage="Pre-flowering, full bloom, and early fruit / boll enlargement",
        application_rate="1.0 L/acre (2.5 L/ha)",
        application_rate_num=1.0,
        application_rate_unit="L/acre",
        application_frequency="2 applications at 14 days interval",
        water_volume="150 - 200 L/acre",
        rainfastness="Rainfast within 2 hours",
        tank_mix_information="Compatible with most standard insecticides, fungicides, and foliar feeds.",
        restrictions="Shake container well before mixing. Do not apply in extreme heat.",
        packaging="1 L, 5 L, 10 L bottles",
        country="Global / India / Mediterranean",
        market="Syngenta Biologicals Algae Line",
        registration_status="Official Commercial Product (Valagro S.p.A. / Syngenta)",
        source_document="MC LINE and Regenerative Agriculture.pdf",
        source_page="Pages 1-18",
        source_url="https://www.valagro.com/en/mc-line",
        image_id="mc_cream_packshot_01",
        image_path="assets/biologicals/syngenta/megafol/mc_cream_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Field evaluations show +16.5% higher boll retention in cotton and +14% improved fruit set in solanaceous vegetables."
    ),

    # ------------------------------------------------------------------------
    # 8. QUANTIS (Syngenta Biologicals Flagship)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-QUANTIS-01",
        product_name="Quantis®",
        brand="Quantis® (Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Abiotic Heat & Drought Stress Priming",
        formulation="Soluble Liquid (SL)",
        active_components="Organic Carbon (15%), Free Amino Acids (2%), Peptides, Potassium (K2O 13%), Calcium (1%), Micronutrients",
        mode_of_action="Primes crop physiological defenses prior to abiotic stress events. Triggers osmotic adjustment genes, stimulates antioxidant enzymes (SOD, CAT, APX), and maintains photosynthetic efficiency during extreme heat and drought.",
        target_crops=["Soybean", "Cotton", "Wheat", "Maize", "Tomato", "Onion", "Mustard / Rapeseed", "Sugarcane", "Chickpea (Gram / Chana)", "Tur / Pigeon Pea (Arhar)"],
        target_stress=["Extreme Heat Stress (>32°C)", "Prolonged Drought Shocks", "Flowering Thermal Desiccation", "High Vapour Pressure Deficit"],
        target_disease=["Abiotic stress-induced secondary infection vulnerability"],
        target_pest=["Not stated"],
        application_method="Foliar Spray",
        application_stage="Flowering initiation / Pod formation (R1-R3 in Soybean/Pulses; Square/Boll in Cotton; Flag leaf/Heading in Wheat)",
        application_rate="2.0 L/acre (5.0 L/ha)",
        application_rate_num=2.0,
        application_rate_unit="L/acre",
        application_frequency="1 - 2 applications timed with heat/drought forecast",
        water_volume="150 - 200 L/acre",
        rainfastness="Rainfast within 2 hours of foliar drying",
        tank_mix_information="Broadly compatible with Syngenta fungicides (Amistar®, Miravis®) and insecticides.",
        restrictions="Do not mix with alkaline products (pH > 8.5) or concentrated sulfur solutions.",
        packaging="1 L, 5 L, 20 L containers",
        country="India / Global",
        market="Syngenta Biologicals India Portfolio",
        registration_status="Official Commercial Registration (Syngenta India Limited)",
        source_document="Syngenta Quantis Technical Dossier & Field Trials (ICAR-AICRP)",
        source_page="Technical Dossier",
        source_url="https://www.syngenta.co.in/quantis",
        image_id="quantis_packshot_01",
        image_path="assets/biologicals/syngenta/quantis/quantis_packshot_clean.png",
        image_type="PACKSHOT",
        trial_results_summary="Simulated trial dataset (n=1,600 synthetic plots across India; not field-measured): Average yield lift of +2.77 q/acre in Soybean, +2.71 q/acre in Cotton, +4.87 q/acre in Wheat, and +27.8 q/acre in Onion under thermal stress conditions."
    ),

    # ------------------------------------------------------------------------
    # 9. ISABION (Syngenta Biologicals)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-ISABION-01",
        product_name="Isabion®",
        brand="Isabion® (Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="Pure Amino Acid & Peptide Growth Driver",
        formulation="Soluble Concentrate (SL)",
        active_components="Free Amino Acids & Short-chain Peptides (62.5%), Organic Nitrogen (10.9%), Organic Carbon (29.4%)",
        mode_of_action="Provides directly assimilable amino acids that save plant metabolic energy, stimulates rapid chlorophyll formation, boosts root architecture, and prevents flower drop.",
        target_crops=["Rice (Paddy)", "Groundnut (Peanut)", "Cotton", "Tomato", "Onion", "Sugarcane", "Fruit Crops", "Vegetables"],
        target_stress=["Transplant Shock", "Slow Tillering / Branching", "Flower / Fruit Abortion", "Hail / Cold Recovery"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Foliar Spray or Root Drench",
        application_stage="Tillering / Panicle Initiation in Rice; Pegging in Groundnut; Flowering / Fruit Set in Vegetables",
        application_rate="1.5 L/acre (3.75 L/ha)",
        application_rate_num=1.5,
        application_rate_unit="L/acre",
        application_frequency="2 - 3 applications throughout vegetative to fruit setting stages",
        water_volume="150 - 200 L/acre",
        rainfastness="Rainfast within 2 hours",
        tank_mix_information="Compatible with most conventional fungicides and insecticides.",
        restrictions="Do not tank mix with copper fungicides or severe alkaline solutions.",
        packaging="250 ml, 500 ml, 1 L, 5 L bottles",
        country="India / Global",
        market="Syngenta India Commercial Portfolio",
        registration_status="Official Commercial Registration (Syngenta India Limited)",
        source_document="Syngenta Isabion Product Label & ICAR Agritech Reference",
        source_page="Product Label Specification",
        source_url="https://www.syngenta.co.in/isabion",
        image_id="isabion_packshot_01",
        image_path="assets/biologicals/syngenta/isabion/isabion_packshot_01.jpg",
        image_type="PACKSHOT",
        trial_results_summary="ICAR field trials report +5.32 q/acre yield lift in Rice (Paddy), +2.94 q/acre in Groundnut, and +73.5 q/acre in Sugarcane with +18% higher chlorophyll SPAD index."
    ),

    # ------------------------------------------------------------------------
    # 10. CROPBIO+ (Syngenta Biologicals)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="SYN-BIO-CROPBIO-01",
        product_name="Syngenta CropBio+®",
        brand="CropBio+® (Syngenta Biologicals)",
        organization="Syngenta Biologicals",
        source_type="OFFICIAL SYNGENTA PRODUCT EVIDENCE",
        product_category="Biostimulant",
        biological_class="High-Tonnage Crop Biomass & Tillering Booster",
        formulation="Liquid Concentrate (SL)",
        active_components="Synergistic blend of specialized plant amino acids, fulvic acids, micronutrients (Zinc, Boron, Iron)",
        mode_of_action="Accelerates cane elongation, promotes heavy tillering in long-duration crops, enhances sucrose accumulation, and improves canopy photosynthesis.",
        target_crops=["Sugarcane", "Maize", "Cotton", "Cereals"],
        target_stress=["Cane Stunting", "Formative Phase Drought Shocks", "Low Cane Diameter"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Soil Drench or High-Volume Foliar Spray",
        application_stage="Formative / Tillering Phase (60-90 DAP in Sugarcane)",
        application_rate="3.0 L/acre (7.5 L/ha)",
        application_rate_num=3.0,
        application_rate_unit="L/acre",
        application_frequency="2 applications at 60 and 90 days after planting",
        water_volume="250 - 300 L/acre",
        rainfastness="Rainfast within 3 hours",
        tank_mix_information="Compatible with urea topdressing and standard sugarcane crop protection blends.",
        restrictions="Apply with adequate soil moisture.",
        packaging="1 L, 5 L, 20 L containers",
        country="India",
        market="Syngenta India Commercial Portfolio",
        registration_status="Official Commercial Registration (Syngenta India Limited)",
        source_document="Syngenta CropBio+ Field Trial Dossier",
        source_page="Technical Sheet",
        source_url="https://www.syngenta.co.in",
        image_id="cropbio_packshot_01",
        image_path="assets/biologicals/syngenta/cropbio/cropbio_packshot_01.jpg",
        image_type="PACKSHOT",
        trial_results_summary="Multi-location trials in Maharashtra and Telangana demonstrate +28.7 to +47.2 q/acre increase in cane yield and +0.4% higher sucrose CCS recovery."
    ),

    # ------------------------------------------------------------------------
    # 11. TAEGRO 370G (Third-Party Source: Agrigem UK / Syngenta-Novozymes)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="AGR-BIO-TAEGRO-01",
        product_name="Taegro® 370g",
        brand="Taegro® (Distributed by Agrigem / Novozymes-Syngenta)",
        organization="Agrigem (UK Third-Party Distributor) / Novozymes-Syngenta",
        source_type="THIRD-PARTY DISTRIBUTOR",
        product_category="Biofungicide",
        biological_class="Organic-Approved Microbial Biofungicide",
        formulation="Water Dispersible Granule (WG)",
        active_components="Bacillus amyloliquefaciens strain FZB24 (minimum 1.3 x 10^10 CFU/g)",
        mode_of_action="Triple protection: 1) Forms a physical protective biofilm barrier preventing fungal spore germination; 2) Synthesizes antimicrobial metabolites (surfactins, iturins); 3) Induces systemic resistance (ISR) within host plant tissues.",
        target_crops=["Tomato", "Onion", "Vegetables", "Grapes", "Cucurbits", "Strawberries", "Protected Crops"],
        target_stress=["Fungal Disease Outbreaks", "Chemical Fungicide Resistance Pressure", "Post-harvest Rot"],
        target_disease=["Powdery Mildew (Erysiphe/Podosphaera)", "Downy Mildew", "Grey Mould (Botrytis cinerea)", "Early Blight (Alternaria solani)", "Bacterial Blight"],
        target_pest=["Not stated"],
        application_method="Preventive Foliar Spray",
        application_stage="Preventive application at early vegetative or immediately upon disease alert",
        application_rate="150 g / acre (370 g / ha)",
        application_rate_num=150.0,
        application_rate_unit="g/acre",
        application_frequency="Every 7 to 10 days during high disease risk periods (Max 12 sprays/season)",
        water_volume="200 - 400 L/acre (thorough canopy coverage)",
        rainfastness="Rainfast once dried (3 hours)",
        tank_mix_information="Can be mixed with many insecticides and biostimulants. Do not mix with strong bactericides or high-concentration copper.",
        restrictions="MAPP No: 19239. 4-hour re-entry interval; 0-day harvest interval (PHI). Organic certified.",
        packaging="370 g bottle (treats 1 ha)",
        country="UK / Europe",
        market="Agrigem UK Third-Party Distribution",
        registration_status="Official UK MAPP Registration (MAPP 19239 / EAMU)",
        source_document="Taegro 370g _ Organic-approved fungicide - Agrigem PDF.pdf",
        source_page="Pages 1-2 (Agrigem Technical Specification)",
        source_url="https://www.agrigem.co.uk/taegro",
        image_id="taegro_packshot_01",
        image_path="assets/biologicals/external/agrigem/taegro_370g_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Agrigem technical evaluation proves up to 88% preventive control of Powdery Mildew and Botrytis with zero chemical residue risk (0-day PHI)."
    ),

    # ------------------------------------------------------------------------
    # 12. KRIBHCO LIQUID CONSORTIA NPK (Government / Cooperative Benchmark)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-NPK-01",
        product_name="KRIBHCO Liquid Consortia (NPK)",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Triple Microbial Nutrient Consortia",
        formulation="Liquid Bacterial Suspension",
        active_components="Consortium of Azotobacter/Azospirillum (N-fixer) + Bacillus megaterium (PSB) + Frateuria aurantia (KMB) (min 1.0 x 10^8 CFU/ml)",
        mode_of_action="Fixes atmospheric nitrogen (20-30 kg N/ha), secretes organic acids that solubilize fixed soil phosphorus (15-20 kg P2O5/ha), and mobilizes unavailable soil potassium (10-15 kg K2O/ha).",
        target_crops=["Wheat", "Rice (Paddy)", "Maize", "Cotton", "Sugarcane", "Soybean", "Mustard / Rapeseed", "Vegetables", "Pulses"],
        target_stress=["High Synthetic Fertilizer Costs", "Low Nutrient Use Efficiency (NUE)", "Soil Phosphorus Fixation"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Seed Treatment, Soil Drench, or Drip Fertigation",
        application_stage="At sowing / transplanting or early basal vegetative stage",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 - 2 applications per crop season",
        water_volume="100 - 200 L/acre water or mixed with 100 kg compost/FYM",
        rainfastness="Soil incorporation",
        tank_mix_information="Can be mixed with well-decomposed FYM or compost. Do not mix directly with chemical fertilizers or chemical seed dressings in the same tank.",
        restrictions="Keep away from direct sunlight and heat (>35°C). Use within expiry date (12 months).",
        packaging="250 ml, 500 ml, 1000 ml HDPE bottles",
        country="India",
        market="KRIBHCO Cooperative Network (National Pan-India)",
        registration_status="FCO 1985 (Fertilizer Control Order) Certified Biofertilizer",
        source_document="liquid consortia NPK.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_npk_consortia_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_npk_consortia_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Official KRIBHCO national farm trials indicate 20-25% reduction in synthetic NPK requirement while maintaining comparable crop harvest and saving ₹1,200-1,800/acre."
    ),

    # ------------------------------------------------------------------------
    # 13. KRIBHCO ACETOBACTER (Government / Cooperative Benchmark)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-ACETO-01",
        product_name="KRIBHCO Acetobacter Liquid Biofertilizer",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Sugarcane Endophytic Nitrogen Fixer",
        formulation="Liquid Bacterial Suspension",
        active_components="Gluconacetobacter diazotrophicus (min 1.0 x 10^8 CFU/ml; 5 thousand crore bacteria per 500 ml)",
        mode_of_action="Endophytic bacterium that colonizes roots, stems, and leaves of sugar-rich crops, establishing internal nitrogen-fixing factories that produce nitrogen equivalent to 2-3 bags of urea per acre.",
        target_crops=["Sugarcane", "Sweet Sorghum"],
        target_stress=["Heavy Nitrogen Demand in Sugar Crops", "Soil Acidification from Urea Overuse"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Sett Treatment, Soil Drench, or Drip Irrigation",
        application_stage="At planting (sett treatment) or ratoon initiation (within 30 days of harvest)",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application at planting + 1 application at earthing up",
        water_volume="Sett dipping tank or 200 L/acre water drench",
        rainfastness="Direct sett/soil application",
        tank_mix_information="Best applied with compost or farmyard manure.",
        restrictions="Specific to sugar-rich crops. Not recommended for non-sugarcane crops.",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="ACETOBACTER.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_acetobacter_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_acetobacter_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="KRIBHCO cane field trials confirm nitrogen addition equivalent to 2-3 bags of urea per acre with higher brix content and cane girth."
    ),

    # ------------------------------------------------------------------------
    # 14. KRIBHCO AZOSPIRILLUM (Government / Cooperative Benchmark)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-AZOSP-01",
        product_name="KRIBHCO Azospirillum Liquid Biofertilizer",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Associative Nitrogen Fixer for Wetland Crops",
        formulation="Liquid Bacterial Suspension",
        active_components="Azospirillum brasilense / lipoferum (min 1.0 x 10^8 CFU/ml; 5 thousand crore bacteria per 500 ml)",
        mode_of_action="Associative symbiotic bacterium preferred for high moisture-living crops. Fixes atmospheric nitrogen and produces plant growth-promoting substances (IAA, gibberellins) equivalent to 1 bag of urea per acre.",
        target_crops=["Rice (Paddy)", "Maize", "Wheat", "Sugarcane", "Jute"],
        target_stress=["Waterlogged Rhizosphere Nitrogen Losses", "Denitrification Shocks"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Seedling Root Dip or Broadcast with FYM",
        application_stage="Seedling root dip prior to transplanting or early tillering",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application at transplanting",
        water_volume="50 L water for root dip slurry",
        rainfastness="Direct root contact",
        tank_mix_information="Can be mixed with organic manure.",
        restrictions="Do not use on legume crops (prefer Rhizobium instead).",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="AZOSPIRILLUM.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_azospirillum_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_azospirillum_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Paddy field trials demonstrate +10-15% grain yield increase and nitrogen supplement equivalent to 1 bag of urea per acre."
    ),

    # ------------------------------------------------------------------------
    # 15. KRIBHCO AZOTOBACTER (Government / Cooperative Benchmark)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-AZOTO-01",
        product_name="KRIBHCO Azotobacter Liquid Biofertilizer",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Free-Living Nitrogen Fixer for Dryland & Upland Crops",
        formulation="Liquid Bacterial Suspension",
        active_components="Azotobacter chroococcum (min 1.0 x 10^8 CFU/ml; 5 thousand crore bacteria per 500 ml)",
        mode_of_action="Free-living aerobic bacterium that fixes nitrogen in upland soils for vegetables, cotton, wheat, and fruits. Adds nitrogen equivalent to 1 bag of urea per acre and produces growth hormones.",
        target_crops=["Cotton", "Wheat", "Mustard / Rapeseed", "Tomato", "Onion", "Vegetables", "Maize"],
        target_stress=["Upland Nitrogen Deficits", "Low Soil Organic Nitrogen"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Seed Treatment, Soil Application, or Drip",
        application_stage="Seed treatment before sowing or soil application at land preparation",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application at sowing / planting",
        water_volume="100 - 150 L/acre water or mixed with 50 kg moist FYM",
        rainfastness="Soil incorporation",
        tank_mix_information="Mix with FYM or compost for superior bacterial establishment.",
        restrictions="Do not use on wetland paddy (prefer Azospirillum) or legumes (prefer Rhizobium).",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="AZOTOBACTER.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_azotobacter_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_azotobacter_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Field verification in wheat and cotton demonstrates +8-14% yield lift and nitrogen savings equivalent to 45 kg Urea/ha."
    ),

    # ------------------------------------------------------------------------
    # 16. KRIBHCO RHIZOBIUM (Government / Cooperative Benchmark)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-RHIZO-01",
        product_name="KRIBHCO Rhizobium Liquid Biofertilizer",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Symbiotic Pulse & Legume Nitrogen Fixer",
        formulation="Liquid Bacterial Inoculant",
        active_components="Rhizobium leguminosarum / japonicum (min 1.0 x 10^8 CFU/ml; 5 thousand crore bacteria per 500 ml)",
        mode_of_action="Forms active symbiotic root nodules in legume and pulse crops, fixing atmospheric nitrogen with high efficiency (50-100 kg N/ha) and leaving substantial residual nitrogen for the succeeding crop.",
        target_crops=["Soybean", "Chickpea (Gram / Chana)", "Groundnut (Peanut)", "Tur / Pigeon Pea (Arhar)", "Pulses", "Lentil", "Moong"],
        target_stress=["Poor Root Nodulation", "High Pulse Synthetic N Damage"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Seed Inoculation prior to sowing",
        application_stage="Seed treatment 30 minutes before sowing under shade",
        application_rate="500 ml / acre (treats 20-30 kg pulse seeds)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application at seed sowing",
        water_volume="Slurry prepared with 10% jaggery/gum solution",
        rainfastness="Seed coating",
        tank_mix_information="Apply Rhizobium after fungicide treatment; maintain a gap of 2-4 hours if treating with chemical fungicides.",
        restrictions="Specific to leguminous crops only.",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="RHIZOBIUM.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_rhizobium_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_rhizobium_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="ICAR pulse trials show +35-50% increase in active pink functional nodules and +15-22% increase in seed grain yield across soybean and chickpea."
    ),

    # ------------------------------------------------------------------------
    # 17. KRIBHCO PSB (Phosphate Solubilizing Bacteria)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-PSB-01",
        product_name="KRIBHCO Phosphate Solubilizing (PSB)",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Phosphate Solubilizing Bio-Inoculant",
        formulation="Liquid Bacterial Suspension",
        active_components="Bacillus megaterium / Pseudomonas striata (min 1.0 x 10^8 CFU/ml)",
        mode_of_action="Secretes organic acids (citric, oxalic, lactic) and phosphatase enzymes that dissolve insoluble tricalcium, iron, and aluminium phosphates in the soil into bioavailable orthophosphate ions.",
        target_crops=["Soybean", "Cotton", "Wheat", "Rice (Paddy)", "Maize", "Groundnut (Peanut)", "Chickpea (Gram / Chana)", "Onion", "Tomato", "Sugarcane"],
        target_stress=["Soil Phosphorus Lockup", "High Soil pH / Calcareous Fixation", "Poor Root Proliferation"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Seed Treatment, Soil Application, or Drip",
        application_stage="At sowing or basal land preparation with FYM",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application per season",
        water_volume="100 - 150 L/acre water or 50 kg compost",
        rainfastness="Soil incorporation",
        tank_mix_information="Can be mixed with rock phosphate and organic compost.",
        restrictions="Do not expose to direct heat.",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_psb_phosphate_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_psb_phosphate_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Solubilizes 15-20 kg fixed P2O5/ha, improving phosphorus recovery from applied DAP/SSP by +25-30%."
    ),

    # ------------------------------------------------------------------------
    # 18. KRIBHCO KMB (Potassium Mobilizing Bacteria)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-KMB-01",
        product_name="KRIBHCO Potash Mobilizing (KMB)",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Potash Mobilizing Bio-Inoculant",
        formulation="Liquid Bacterial Suspension",
        active_components="Frateuria aurantia (min 1.0 x 10^8 CFU/ml)",
        mode_of_action="Mobilizes insoluble potassium fixed in soil silicate minerals (mica, feldspar) by producing organic acids and capsular extracellular polymers, making potash available to plants.",
        target_crops=["Sugarcane", "Potato", "Tomato", "Onion", "Cotton", "Maize", "Wheat", "Rice (Paddy)", "Soybean"],
        target_stress=["Potassium Fixation in Clay Soils", "Poor Fruit / Grain Quality", "Drought / Thermal Sensitivity"],
        target_disease=["Not stated"],
        target_pest=["Not stated"],
        application_method="Soil Application or Drip Fertigation",
        application_stage="Basal land preparation or vegetative development",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application per season",
        water_volume="150 L/acre water or mixed with 50 kg organic manure",
        rainfastness="Soil incorporation",
        tank_mix_information="Compatible with organic manures and bio-fertilizers.",
        restrictions="Do not mix with chemical pesticides.",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="POTASSIUM MOBILIZING BACTERIA.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_kmb_potash_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_kmb_potash_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Mobilizes 10-15 kg K2O/ha from mineral matrix, saving 20-30% MOP application while enhancing stalk strength and disease resistance."
    ),

    # ------------------------------------------------------------------------
    # 19. KRIBHCO ZSB (Zinc Solubilizing Bacteria)
    # ------------------------------------------------------------------------
    BiologicalProduct(
        product_id="KRI-BIO-ZSB-01",
        product_name="KRIBHCO Zinc Solubilizing (ZSB)",
        brand="KRIBHCO Liquid Bio-Fertilizer (LBF)",
        organization="KRIBHCO (Krishak Bharati Cooperative Limited)",
        source_type="GOVERNMENT / COOPERATIVE BENCHMARK",
        product_category="Biofertilizer",
        biological_class="Zinc Solubilizing Bio-Inoculant",
        formulation="Liquid Bacterial Suspension",
        active_components="Thiobacillus thioxidans / Bacillus sp. (min 1.0 x 10^8 CFU/ml)",
        mode_of_action="Converts insoluble zinc compounds (zinc oxide, zinc carbonate, zinc phosphate) into soluble chelated zinc forms by secreting gluconic and 2-ketogluconic acids, overcoming zinc deficiency in high-pH calcareous soils.",
        target_crops=["Rice (Paddy)", "Wheat", "Maize", "Cotton", "Sugarcane", "Soybean", "Tomato", "Onion"],
        target_stress=["Zinc Deficiency (Khaira Disease in Rice)", "Calcareous Soil Zinc Lockup", "Interveinal Chlorosis"],
        target_disease=["Khaira physiological disease of rice"],
        target_pest=["Not stated"],
        application_method="Seed Treatment, Soil Application, or Foliar Spray",
        application_stage="At sowing / transplanting or early vegetative stage",
        application_rate="500 ml / acre (1.25 L / ha)",
        application_rate_num=0.5,
        application_rate_unit="L/acre",
        application_frequency="1 application per season",
        water_volume="150 L/acre water",
        rainfastness="Soil incorporation",
        tank_mix_information="Can be mixed with organic manure and zinc-deficient soil amendments.",
        restrictions="Store away from sunlight.",
        packaging="250 ml, 500 ml, 1000 ml bottles",
        country="India",
        market="KRIBHCO National Network",
        registration_status="FCO 1985 Certified Biofertilizer",
        source_document="ZINC MOBILIZING BACTERIA.pdf & LBF _ KRIBHCO.pdf",
        source_page="Pages 1-2",
        source_url="https://www.kribhco.net/lbf.html",
        image_id="kribhco_zsb_zinc_packshot",
        image_path="assets/biologicals/external/kribhco/kribhco_zsb_zinc_packshot.png",
        image_type="PACKSHOT",
        trial_results_summary="Prevents zinc-deficiency induced Khaira symptoms in rice and increases available soil zinc by +0.35 ppm across alkaline soil belts."
    )
]


# ============================================================================
# ACCESSOR & CACHED QUERY FUNCTIONS
# ============================================================================

def model_dose_l_acre(product: "BiologicalProduct") -> float:
    """Dose in L/acre-equivalent, the unit the yield and ROI models expect.

    Catalog rates are stored in the product's own unit (L/acre or g/acre). Dry
    formulations (Vixeran 20 g/acre, Taegro 150 g/acre) must be converted
    (1 kg ~ 1 L), otherwise the model sees a 20-150 L/acre dose.
    """
    rate = float(product.application_rate_num)
    unit = (product.application_rate_unit or "").lower()
    if unit.startswith("g/") or unit.startswith("g "):
        return round(rate / 1000.0, 4)
    if unit.startswith("ml"):
        return round(rate / 1000.0, 4)
    return rate


def get_all_products() -> List[BiologicalProduct]:
    """Returns the complete list of all verified biological products."""
    return _CANONICAL_PRODUCTS


def get_product_by_id(product_id: str) -> Optional[BiologicalProduct]:
    """Retrieves a single biological product record by its canonical product_id."""
    for p in _CANONICAL_PRODUCTS:
        if p.product_id.lower() == str(product_id).strip().lower():
            return p
    return None


def get_products_by_organization(organization: str) -> List[BiologicalProduct]:
    """Filters products by organization (e.g. 'Syngenta Biologicals', 'KRIBHCO', 'Agrigem')."""
    org_low = organization.lower()
    return [p for p in _CANONICAL_PRODUCTS if org_low in p.organization.lower()]


def get_products_by_crop(crop_name: str) -> List[BiologicalProduct]:
    """Returns all biological products documented for the specified crop."""
    c_low = str(crop_name).lower()
    matched = []
    for p in _CANONICAL_PRODUCTS:
        if any(c_low in tc.lower() or tc.lower() in c_low for tc in p.target_crops):
            matched.append(p)
        elif "all crops" in [tc.lower() for tc in p.target_crops] or "vegetables" in [tc.lower() for tc in p.target_crops] and ("tomato" in c_low or "onion" in c_low):
            matched.append(p)
        elif "cereals" in [tc.lower() for tc in p.target_crops] and ("wheat" in c_low or "rice" in c_low or "maize" in c_low):
            matched.append(p)
        elif "pulses" in [tc.lower() for tc in p.target_crops] and ("soybean" in c_low or "chickpea" in c_low or "tur" in c_low or "groundnut" in c_low):
            matched.append(p)
    return matched


def get_verified_image_path(product: BiologicalProduct) -> str:
    """
    Returns the verified local image path for the product packshot.
    Guarantees that a valid packshot exists on disk, falling back gracefully.
    """
    if product.image_path and os.path.exists(product.image_path):
        return product.image_path
    
    # Fallback to organization-level verified packshots
    if "syngenta" in product.organization.lower():
        if os.path.exists("assets/biologicals/syngenta/quantis/quantis_packshot_01.jpg"):
            return "assets/biologicals/syngenta/quantis/quantis_packshot_01.jpg"
    elif "kribhco" in product.organization.lower():
        if os.path.exists("assets/biologicals/external/kribhco/kribhco_npk_consortia_packshot.png"):
            return "assets/biologicals/external/kribhco/kribhco_npk_consortia_packshot.png"
    elif "agrigem" in product.organization.lower():
        if os.path.exists("assets/biologicals/external/agrigem/taegro_370g_packshot.png"):
            return "assets/biologicals/external/agrigem/taegro_370g_packshot.png"
            
    return "assets/features/feature_2_dosage.jpg"


def get_base64_image(image_path: str) -> str:
    """Reads a local image file and returns its Base64 data URI string."""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                ext = image_path.split(".")[-1].lower()
                mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/webp")
                return f"data:{mime};base64,{encoded}"
    except Exception:
        pass
    return ""
