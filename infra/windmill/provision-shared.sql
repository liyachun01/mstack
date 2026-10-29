-- Prepared, not executed. Dedicated new database and roles only.
-- psql -X -v ON_ERROR_STOP=1; prefix input with a private \set wm_password.
-- Refuse existing names during preflight. Do not make this an automatic init hook.
BEGIN;
CREATE ROLE windmill LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS PASSWORD :'wm_password';
\unset wm_password
CREATE ROLE windmill_user NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS;
CREATE ROLE windmill_admin NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION BYPASSRLS;
GRANT windmill_user TO windmill_admin;
GRANT windmill_user, windmill_admin TO windmill;
COMMIT;
CREATE DATABASE windmill OWNER windmill TEMPLATE template0;
REVOKE ALL ON DATABASE windmill FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE windmill TO windmill;
\connect windmill
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO windmill;
GRANT USAGE ON SCHEMA public TO windmill_user, windmill_admin;
-- Mirror the pinned upstream grants under the actual migration owner.
ALTER DEFAULT PRIVILEGES FOR ROLE windmill IN SCHEMA public
  GRANT ALL ON TABLES TO windmill_user;
ALTER DEFAULT PRIVILEGES FOR ROLE windmill IN SCHEMA public
  GRANT ALL ON SEQUENCES TO windmill_user;
