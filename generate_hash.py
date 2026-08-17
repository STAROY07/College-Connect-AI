from werkzeug.security import generate_password_hash

# Run this once to generate the admin password hash
# Change 'admin@vmdc2026' to your desired password
password = "admin@vmdc2026"
hashed = generate_password_hash(password)
print(f"ADMIN_PASSWORD_HASH={hashed}")
print("\nCopy the above line into your admin_config.json")
