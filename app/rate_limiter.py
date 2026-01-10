from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory limiter (does not require Redis)
limiter = Limiter(key_func=get_remote_address)
