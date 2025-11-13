import json
import os
from typing import Dict, List, Optional

class UserManager:
    def __init__(self, users_file: str = "users.json"):
        self.users_file = users_file
        self._ensure_users_file_exists()
    
    def _ensure_users_file_exists(self):
        """Membuat file users.json jika belum ada"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({"users": []}, f, indent=4)
    
    def _read_users(self) -> Dict:
        """Membaca data users dari file JSON"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"users": []}
    
    def _write_users(self, data: Dict):
        """Menulis data users ke file JSON"""
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    def user_exists(self, username: str) -> bool:
        """Cek apakah username sudah ada"""
        data = self._read_users()
        users = data.get("users", [])
        return any(user['username'] == username for user in users)
    
    def email_exists(self, email: str) -> bool:
        """Cek apakah email sudah ada"""
        data = self._read_users()
        users = data.get("users", [])
        return any(user['email'] == email for user in users)
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """Mendaftarkan user baru"""
        if self.user_exists(username):
            return False, "Username already exists"
        
        if self.email_exists(email):
            return False, "Email already registered"
        
        data = self._read_users()
        
        new_user = {
            "username": username,
            "email": email,
            "password": password,  # Dalam production, seharusnya di-hash
            "created_at": self._get_current_timestamp(),
            "last_login": None,
            "is_active": True
        }
        
        data["users"].append(new_user)
        self._write_users(data)
        
        return True, "User registered successfully"
    
    def verify_user(self, username: str, password: str) -> bool:
        """Verifikasi login user"""
        data = self._read_users()
        users = data.get("users", [])
        
        for user in users:
            if user['username'] == username and user['password'] == password and user['is_active']:
                # Update last login
                user['last_login'] = self._get_current_timestamp()
                self._write_users(data)
                return True
        
        return False
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Mendapatkan informasi user"""
        data = self._read_users()
        users = data.get("users", [])
        
        for user in users:
            if user['username'] == username:
                return user
        
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Mendapatkan semua users (untuk admin)"""
        data = self._read_users()
        return data.get("users", [])
    
    def _get_current_timestamp(self):
        """Mendapatkan timestamp saat ini"""
        from datetime import datetime
        return datetime.now().isoformat()