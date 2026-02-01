-- Allow Offline Employees (Ghost Users)
-- Currently, the 'labor_contracts' table forces every contract to be linked to a real App User.
-- We must remove this constraint to register employees who haven't joined the app yet.

ALTER TABLE "public"."labor_contracts" ALTER COLUMN "user_id" DROP NOT NULL;
