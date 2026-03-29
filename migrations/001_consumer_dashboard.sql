-- ═══════════════════════════════════════════
-- Consumer Dashboard: DB Migration
-- Run in Supabase SQL Editor
-- ═══════════════════════════════════════════

-- 1. Plans table
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  max_sites INT NOT NULL DEFAULT 1,
  max_daily_posts INT NOT NULL DEFAULT 4,
  max_categories INT NOT NULL DEFAULT 6,
  features JSONB NOT NULL DEFAULT '{}',
  price_monthly INT NOT NULL DEFAULT 0,
  price_yearly INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO plans (id, name, max_sites, max_daily_posts, max_categories, features, price_monthly, price_yearly) VALUES
  ('standard', 'Standard', 1, 4, 6,
   '{"goldenMode":false,"polishing":false,"customSchedule":false,"modelSelection":false,"revenueSimulation":false,"seoAnalysis":false,"telegramAlerts":false,"snsAutomation":false,"marketingContent":false}',
   29000, 290000),
  ('premium', 'Premium', 3, 20, 999,
   '{"goldenMode":true,"polishing":true,"customSchedule":true,"modelSelection":true,"revenueSimulation":true,"seoAnalysis":true,"telegramAlerts":true,"snsAutomation":false,"marketingContent":false}',
   79000, 790000),
  ('mama', 'MaMa', 999, 999, 999,
   '{"goldenMode":true,"polishing":true,"customSchedule":true,"modelSelection":true,"revenueSimulation":true,"seoAnalysis":true,"telegramAlerts":true,"snsAutomation":true,"marketingContent":true}',
   199000, 1990000)
ON CONFLICT (id) DO NOTHING;

-- 2. User profiles (extends Supabase Auth)
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES plans(id) DEFAULT 'standard',
  display_name TEXT,
  onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
  onboarding_step INT NOT NULL DEFAULT 0,
  trial_ends_at TIMESTAMPTZ,
  monetization_stage INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. User-Site mapping
CREATE TABLE IF NOT EXISTS user_sites (
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  site_id TEXT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'owner',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, site_id)
);

-- 4. Milestones tracking
CREATE TABLE IF NOT EXISTS user_milestones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  milestone_id TEXT NOT NULL,
  achieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  data JSONB DEFAULT '{}',
  UNIQUE (user_id, milestone_id)
);

-- 5. RLS Policies
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_milestones ENABLE ROW LEVEL SECURITY;

-- user_profiles: users can read/update only their own profile
CREATE POLICY "users_read_own_profile" ON user_profiles
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "users_update_own_profile" ON user_profiles
  FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "users_insert_own_profile" ON user_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

-- user_sites: users can manage only their own site mappings
CREATE POLICY "users_read_own_sites" ON user_sites
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_insert_own_sites" ON user_sites
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_delete_own_sites" ON user_sites
  FOR DELETE USING (auth.uid() = user_id);

-- user_milestones: users can read/insert only their own milestones
CREATE POLICY "users_read_own_milestones" ON user_milestones
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_insert_own_milestones" ON user_milestones
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 6. Auto-create profile on signup (trigger)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, display_name, trial_ends_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
    NOW() + INTERVAL '7 days'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 7. Updated_at auto-update
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;
CREATE TRIGGER user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- 8. Add owner_id to sites table (if not exists)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sites' AND column_name = 'owner_id'
  ) THEN
    ALTER TABLE sites ADD COLUMN owner_id UUID REFERENCES user_profiles(id);
  END IF;
END $$;
