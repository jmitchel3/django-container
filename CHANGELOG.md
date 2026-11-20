# Changelog

## v0.1.0 (2026-11-20)

- feat: Add runtime secret injection and versioned Django container releases
  - Fetch secrets from Doppler at startup or load mounted files and provider-supplied environment variables, including for one-off management commands.
  - Ship non-root PostgreSQL, MySQL, and static frontend images with Django 6.0.10, locked dependencies, and configurable release steps.
  - Require stable signing keys outside debug mode, restrict automatic Railway trust to the service's domains, and protect existing admin accounts during bootstrap.
  - Check fresh database startup and secret injection in CI. Automatically push local commits and publish semantic versions with a cumulative changelog after main passes.
