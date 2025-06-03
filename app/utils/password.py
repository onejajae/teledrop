import argon2

# Password hasher 인스턴스
password_hasher = argon2.PasswordHasher()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        password_hasher.verify(hashed_password, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False