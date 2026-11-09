# Publishing notes — E-DBA

This is a **curated public-portfolio candidate**, not a validated working release.
Keep the original `a04.zip` intact as a private course archive.

## Files selected from the submission

- `src/app/`: core Flask source, templates, static resources, excluding stale `src/app/USER/` alternate route implementation, cache files, duplicate ZIPs, uploaded documents and external data.
- `src/run.py` and `src/config.py`: development launcher and sanitized, environment-driven configuration.
- `tests/ActivityRecord_Test.py`: existing database-backed test.
- Fresh `README.md`, `.gitignore`, `.env.example`, `requirements*.txt`.

## Intentionally excluded

- `.git/` and `.idea/`: historical Git objects and local IDE workspace.
- `sdwEnv/`: complete Python virtual environment.
- `database/*.json`: database exports containing sample or potentially personal information.
- `uploads/`, `thesis_files/`, `src/uploads/`, `src/thesis_files/`: user-provided PDFs and upload artifacts.
- `src.zip`, `src/app/datauser.zip`, `src/app/templates/datauser.zip`: duplicate archives.
- `src/app/USER/`: unregistered legacy user-route implementation; two files contain accidental HTML template fragments that make Python parsing fail. Retain only in the private course archive.
- `minutes/`, `minute/`: 11 weekly meeting-minutes documents, not needed in a portfolio.
- `docs/Requirements/SRS_a04_v*.pdf` and full original Design/Testing PDFs: several versions, not included pending collaborator review; choose only final, approved documents if you later want to publish them.
- Python `__pycache__`, `*.pyc`, `.DS_Store`, `._*` and `__MACOSX` metadata.

## Security review before publishing (important)

1. Rotate any actual database credentials and secret keys from the original submission if ever used. Git history can retain earlier values even after deletion, so start a *new* repository with no old `.git` history.
2. Verify that `src/app/static/images/` may be redistributed (e.g., image licenses).
3. Review every remaining source file and template for real identifiers, passwords, tokens, and external endpoint credentials. Automated screening is not an assurance of confidentiality.
4. Review user authentication and authorization: some request handlers use an untrusted `X-User-Email` header. Never deploy publicly without addressing this.
5. Ensure the intended MongoDB instance is local and filled only with synthetic test data for demonstrations.
6. Agree on attribution and publication rights with group contributors.
7. Confirm the actual startup, test and OTP flows locally before claiming the repository is fully runnable.

## Technical audit findings from the uploaded snapshot

- `requirements.txt` omitted dependencies imported by the source (`flask_pymongo`, `requests`, `pandas` and Excel support); the curated package adds these as direct requirements.
- `src/config.py` contained hardcoded sensitive settings and a misspelled session-lifetime setting; curated config is environment-driven. The development launcher defaults debug mode off.
- The unused legacy `src/app/USER/auth_decorators.py` and `src/app/USER/service/verification_service.py` contain HTML in Python files and fail syntax checks. They were not copied into the package.
- The existing application depends on local collections and mock services. This packaging step does not redesign or end-to-end validate the application.

## Suggested GitHub metadata

**Repository name:** `E-DBA-Education-Data-Sharing-Platform`

**Description:** `Flask and MongoDB prototype for role-based, cross-university data sharing, organization management, and academic services.`

**Topics:** `flask`, `mongodb`, `python`, `rest-api`, `role-based-access-control`, `data-sharing`, `software-engineering`
