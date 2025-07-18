"""
Password Service for password hashing and verification
"""

import logging
import secrets
import string
from typing import Optional, Dict

from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Password hashing and verification service using bcrypt
    """
    
    def __init__(self):
        # Configure password context with bcrypt
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Higher rounds for better security
        )
    
    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        try:
            if not password:
                raise ValueError("Password cannot be empty")
            
            hashed = self.pwd_context.hash(password)
            logger.debug("✅ Password hashed successfully")
            return hashed
            
        except Exception as e:
            logger.error(f"❌ Failed to hash password: {e}")
            raise

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            if not plain_password or not hashed_password:
                return False
            
            is_valid = self.pwd_context.verify(plain_password, hashed_password)
            
            if is_valid:
                logger.debug("✅ Password verification successful")
            else:
                logger.debug("❌ Password verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Password verification error: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password needs to be rehashed (e.g., due to updated algorithm)
        
        Args:
            hashed_password: Hashed password from database
            
        Returns:
            True if password needs rehashing, False otherwise
        """
        try:
            return self.pwd_context.needs_update(hashed_password)
        except Exception as e:
            logger.error(f"❌ Error checking if password needs rehash: {e}")
            return False

    def generate_password(self, length: int = 12) -> str:
        """
        Generate a secure random password
        
        Args:
            length: Length of the password (minimum 8)
            
        Returns:
            Generated password string
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")
        
        try:
            # Character sets
            lowercase = string.ascii_lowercase
            uppercase = string.ascii_uppercase
            digits = string.digits
            special_chars = "!@#$%^&*"
            
            # Ensure at least one character from each set
            password = [
                secrets.choice(lowercase),
                secrets.choice(uppercase),
                secrets.choice(digits),
                secrets.choice(special_chars)
            ]
            
            # Fill the rest with random characters from all sets
            all_chars = lowercase + uppercase + digits + special_chars
            for _ in range(length - 4):
                password.append(secrets.choice(all_chars))
            
            # Shuffle the password
            secrets.SystemRandom().shuffle(password)
            
            generated_password = ''.join(password)
            logger.debug(f"✅ Generated password with length {length}")
            return generated_password
            
        except Exception as e:
            logger.error(f"❌ Failed to generate password: {e}")
            raise

    def validate_password_strength(self, password: str) -> Dict[str, bool]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                "min_length": len(password) >= 8,
                "max_length": len(password) <= 128,
                "has_lowercase": any(c.islower() for c in password),
                "has_uppercase": any(c.isupper() for c in password),
                "has_digit": any(c.isdigit() for c in password),
                "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
                "no_common_patterns": not self._has_common_patterns(password)
            }
            
            # Overall strength
            validation_results["is_strong"] = all([
                validation_results["min_length"],
                validation_results["max_length"],
                validation_results["has_lowercase"],
                validation_results["has_uppercase"],
                validation_results["has_digit"],
                validation_results["has_special"],
                validation_results["no_common_patterns"]
            ])
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Password strength validation error: {e}")
            return {"is_strong": False}

    def _has_common_patterns(self, password: str) -> bool:
        """
        Check for common password patterns
        
        Args:
            password: Password to check
            
        Returns:
            True if password has common patterns, False otherwise
        """
        password_lower = password.lower()
        
        # Common patterns
        common_patterns = [
            "123456",
            "password",
            "qwerty",
            "abc123",
            "letmein",
            "welcome",
            "admin",
            "user"
        ]
        
        # Check for common patterns
        for pattern in common_patterns:
            if pattern in password_lower:
                return True
        
        # Check for keyboard patterns
        keyboard_patterns = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
            "1234567890"
        ]
        
        for pattern in keyboard_patterns:
            if pattern in password_lower or pattern[::-1] in password_lower:
                return True
        
        # Check for repeated characters
        if len(set(password)) < 4:  # Too few unique characters
            return True
        
        return False

    def hash_and_validate(self, password: str) -> tuple[str, bool]:
        """
        Validate password strength and hash it if strong
        
        Args:
            password: Plain text password
            
        Returns:
            Tuple of (hashed_password, is_strong)
        """
        try:
            validation = self.validate_password_strength(password)
            
            if validation["is_strong"]:
                hashed = self.hash_password(password)
                return hashed, True
            else:
                logger.warning("❌ Password does not meet strength requirements")
                return "", False
                
        except Exception as e:
            logger.error(f"❌ Password hash and validation error: {e}")
            return "", False 