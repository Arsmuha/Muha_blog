import sys
import bcrypt
from passlib.context import CryptContext

print(f"Python: {sys.version}")
print(f"bcrypt: {bcrypt.__version__}")

# Проверка атрибутов bcrypt
print(f"\nАтрибуты bcrypt:")
for attr in dir(bcrypt):
    if not attr.startswith('_'):
        print(f"  {attr}")

# Тест хеширования
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hash_result = pwd_context.hash("admin123")
    print(f"\n✅ Хеширование работает: {hash_result[:50]}...")
    
    # Проверка пароля
    verify_result = pwd_context.verify("admin123", hash_result)
    print(f"✅ Проверка пароля: {verify_result}")
except Exception as e:
    print(f"\n❌ Ошибка: {type(e).__name__}: {e}")