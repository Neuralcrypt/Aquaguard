
import os

# Test-only environment configuration.
os.environ["DATABASE_URL"] = "sqlite:///./test_water.db"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-32-characters"
os.environ["ADMIN_PASSWORD"] = "123456"
os.environ["DEVICE_API_KEY"] = "test-only-device-key-for-pytest"
