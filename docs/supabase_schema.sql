-- Supabase Cloud PostgreSQL Schema: AgriAttribute AI Farm Memory & Telemetry
-- Project: soham0777/hack-core-ps07-agriattribute (Team 15 - Syngenta & ANNAM.AI)

CREATE TABLE IF NOT EXISTS public.season_journal (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    farmer_id TEXT DEFAULT 'IND_FARMER_001',
    region TEXT NOT NULL,
    crop_type TEXT NOT NULL,
    product_applied TEXT NOT NULL,
    dosage_l_acre NUMERIC(5, 2) DEFAULT 2.00,
    readiness_score INTEGER DEFAULT 85,
    yield_actual_q_acre NUMERIC(6, 2) NOT NULL,
    bio_attributed_lift NUMERIC(5, 2) DEFAULT 2.50,
    net_profit_rs NUMERIC(10, 2) DEFAULT 8000.00,
    farmer_notes TEXT,
    kcc_attestation_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_season_journal_created ON public.season_journal (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_season_journal_crop ON public.season_journal (crop_type);

CREATE TABLE IF NOT EXISTS public.telemetry_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_time TIMESTAMPTZ DEFAULT NOW(),
    farmer_id TEXT DEFAULT 'IND_FARMER_001',
    region TEXT NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    crop_type TEXT NOT NULL,
    temperature_c NUMERIC(5, 2),
    humidity_pct INTEGER,
    rain_probability_pct INTEGER,
    heat_stress_days INTEGER,
    soil_n_kg_ha NUMERIC(6, 2),
    soil_p_kg_ha NUMERIC(6, 2),
    soil_k_kg_ha NUMERIC(6, 2),
    soil_ph NUMERIC(4, 2),
    disease_risk_score NUMERIC(5, 2),
    recommended_product TEXT,
    spray_window_status TEXT
);

CREATE INDEX IF NOT EXISTS idx_telemetry_snapshots_time ON public.telemetry_snapshots (snapshot_time DESC);

ALTER TABLE public.season_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telemetry_snapshots ENABLE ROW LEVEL SECURITY;
