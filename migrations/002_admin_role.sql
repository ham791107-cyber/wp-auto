-- Add role column to user_profiles
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_profiles' AND column_name = 'role'
  ) THEN
    ALTER TABLE user_profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'user';
  END IF;
END $$;

-- Set mymiryu@naver.com as admin
UPDATE user_profiles
SET role = 'admin'
WHERE id = '69d6b4c0-1ea3-4b73-a0b1-98581fdfe090';
