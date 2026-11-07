# CI/CD design

## Pull request CI
1. Checkout code.
2. Set up Python and Node.
3. Install dependencies.
4. Run backend tests, ML tests, frontend lint/tests/build.
5. Compile ESP32 firmware using PlatformIO where configured.
6. Run dependency/security checks.

## Main branch delivery
1. Repeat required CI checks.
2. Build Docker images.
3. Scan images with Trivy.
4. Publish versioned images to GHCR.
5. Deploy to configured staging host only when repository secrets and host are configured.
6. Run health/smoke checks.
7. Require approval before production deployment.

## Repository setup needed
- Configure GitHub Actions permissions and GHCR package access.
- Protect `main` with required status checks.
- Configure deployment secrets only if a remote host is used.
- Keep `.env` and device credentials out of Git.
- Treat the included workflows as starter templates; validate them in your repository before relying on releases.
