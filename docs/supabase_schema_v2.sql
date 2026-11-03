-- AgriAttribute AI: Farm Waste Market + AquaSentinel River Watch tables
-- Run once in the Supabase SQL editor. The app uses the server-side secret key, so RLS stays on with no public policies.

create table if not exists public.scrap_listings (
    id text primary key,
    created_at timestamptz default now(),
    farmer_name text, phone text, share_phone boolean default false,
    waste_type text not null, quantity numeric, unit text, quantity_q numeric,
    condition text, available_from text, price_expectation numeric,
    lat numeric, lon numeric, place text, state text, notes text,
    photo_b64 text, ai_summary text, status text default 'open'
);
create table if not exists public.scrap_buyers (
    id text primary key,
    created_at timestamptz default now(),
    name text not null, buyer_type text, accepts text, min_qty_q numeric,
    price_min numeric, price_max numeric, lat numeric, lon numeric, place text, state text,
    phone text, is_demo boolean default false, verified boolean default false
);
create table if not exists public.scrap_inquiries (
    id text primary key,
    created_at timestamptz default now(),
    listing_id text, buyer_id text, message text, status text default 'sent'
);
create table if not exists public.river_incidents (
    id text primary key,
    created_at timestamptz default now(),
    event_key text, stretch text, device_id text, severity text, parameter text, value numeric, limit_text text,
    summary text, farmer_message text, gov_message text, status text default 'new', notes text, source text
);
create index if not exists idx_scrap_listings_created on public.scrap_listings (created_at desc);
create index if not exists idx_river_incidents_created on public.river_incidents (created_at desc);

alter table public.scrap_listings enable row level security;
alter table public.scrap_buyers enable row level security;
alter table public.scrap_inquiries enable row level security;
alter table public.river_incidents enable row level security;

-- Direct procurement: companies post what they need, farmers offer to supply
create table if not exists public.buyer_demands (
    id text primary key,
    created_at timestamptz default now(),
    company text not null, company_type text, category text, item text, crop_key text, specs text,
    qty_needed_q numeric, qty_filled_q numeric default 0, price_offer numeric,
    lat numeric, lon numeric, place text, state text, deadline text, terms text, contact_phone text,
    is_demo boolean default false, verified boolean default false, status text default 'open'
);
create table if not exists public.demand_offers (
    id text primary key,
    created_at timestamptz default now(),
    demand_id text, farmer_name text, phone text, qty_q numeric, price_ask numeric, place text, message text,
    status text default 'offered'
);
alter table public.buyer_demands enable row level security;
alter table public.demand_offers enable row level security;
