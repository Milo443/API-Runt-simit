import hashlib
import json
import time
from typing import List

def is_prime(n: int) -> bool:
    """Checks if a number is prime (required by qxCaptcha)."""
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0: return False
    return True

def solve_pow(question: str, difficulty: int, current_time: int = None) -> List[dict]:
    """
    Solves the qxCaptcha Proof-of-Work challenge.
    Finds N nonces (where N = difficulty) such that:
    1. nonce is a prime number.
    2. sha256(question + time + nonce) starts with '0000'.
    """
    if current_time is None:
        current_time = int(time.time())
        
    results = []
    nonce = 0
    
    # The portal usually searches for 'difficulty' number of valid solutions
    for _ in range(difficulty):
        found = False
        while not found:
            nonce += 1
            if is_prime(nonce):
                # Data must be stringified with NO spaces (separators=(',', ':'))
                data = {
                    "question": question,
                    "time": current_time,
                    "nonce": nonce
                }
                data_json = json.dumps(data, separators=(',', ':'))
                h = hashlib.sha256(data_json.encode()).hexdigest()
                
                if h.startswith("0000"):
                    results.append(data)
                    found = True
    return results
