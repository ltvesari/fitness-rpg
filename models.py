import json
import os
import hashlib
from datetime import datetime
import uuid
import streamlit as st
from supabase import create_client, Client

# Sabitler
XP_PER_LEVEL_MULTIPLIER = 1000

# Antrenman Katsayıları
WORKOUT_MULTIPLIERS = {
    "Ağırlık (STR)": {"xp_mult": 1.2, "primary": "STR", "secondary": "VIT"},
    "Kardiyo (AGI)": {"xp_mult": 1.0, "primary": "AGI", "secondary": "VIT"},
    "Yoga/Esneme (WIS)": {"xp_mult": 0.8, "primary": "WIS", "secondary": "AGI"},
    "HIIT (AGI)": {"xp_mult": 1.1, "primary": "AGI", "secondary": "STR"},
}

# Supabase Setup
# Try to get secrets from Streamlit secrets, environment, or local file
def get_supabase_client():
    url = None
    key = None
    
    # 1. Try Streamlit Secrets (Best for Cloud)
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except Exception:
        pass
    
    # 2. Try Environment Variables
    if not url:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

    # 3. Try loading local .streamlit/secrets.toml (For local scripts outside Streamlit)
    if not url:
        try:
             # Python 3.11+
            import tomllib
            with open(".streamlit/secrets.toml", "rb") as f:
                secrets = tomllib.load(f)
                url = secrets["supabase"]["url"]
                key = secrets["supabase"]["key"]
        except Exception:
            pass

    if not url or not key:
        raise ValueError("Supabase credentials not found! Please check .streamlit/secrets.toml or Streamlit Cloud Secrets.")
        
    return create_client(url, key)

# Initialize Client
try:
    supabase: Client = get_supabase_client()
except Exception as e:
    # Fail gracefully if secrets aren't set yet (e.g. during initial setup)
    print(f"Warning: {e}")
    supabase = None

class Character:
    def __init__(self, name, char_class, password, email="", avatar_id="warrior_male", level=1, xp=0, stats=None, history=None):
        self.name = name
        self.char_class = char_class
        self.email = email
        self.password = self._hash_password(password) if len(password) < 64 else password
        self.avatar_id = avatar_id
        self.level = level
        self.xp = xp
        self.stats = stats if stats else self._get_initial_stats()
        self.history = history if history else []

    def _get_initial_stats(self):
        return {"STR": 10, "AGI": 10, "VIT": 10, "WIS": 10}

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password == self._hash_password(password)

    def add_xp(self, amount):
        """XP ekler ve seviye atlamayı kontrol eder."""
        self.xp += amount
        self.check_level_up()

    def check_level_up(self):
        """Seviye atlama kontrolü."""
        xp_needed = self.level * XP_PER_LEVEL_MULTIPLIER
        while self.xp >= xp_needed:
            self.xp -= xp_needed
            self.level += 1
            self.level_up_rewards()
            xp_needed = self.level * XP_PER_LEVEL_MULTIPLIER

    def level_up_rewards(self):
        """Seviye atlayınca gelen stat artışları."""
        for stat in self.stats:
            self.stats[stat] += 1

    def log_activity(self, activity_type, description, xp_reward, stat_rewards=None, proof_image=None):
        """Aktivite kaydeder."""
        activity_id = f"{self.name}_{str(uuid.uuid4())[:8]}"

        entry = {
            "id": activity_id,
            "date": datetime.now().isoformat(),
            "type": activity_type,
            "description": description,
            "xp_reward": xp_reward,
            "stat_rewards": stat_rewards,
            "proof_image": proof_image,
            "status": "pending" if (proof_image or activity_type == "Extra") else "approved",
            "admin_bonus_applied": False,
        }
        
        if entry["status"] == "approved":
            self._apply_rewards(activity_type, xp_reward, stat_rewards)
        
        self.history.append(entry)

    def _apply_rewards(self, activity_type, xp_reward, stat_rewards):
        # Sınıf Bonusları Kontrolü
        bonus_xp = 0
        if self.char_class == "Savaşçı" and activity_type == "Strength":
            bonus_xp = int(xp_reward * 0.10)
        
        total_xp = xp_reward + bonus_xp
        self.add_xp(total_xp)

        if stat_rewards:
            for stat, amount in stat_rewards.items():
                if stat in self.stats:
                    self.stats[stat] += amount

    def approve_activity(self, activity_id):
        for entry in self.history:
            if entry.get("id") == activity_id and entry["status"] == "pending":
                entry["status"] = "approved"
                self._apply_rewards(entry["type"], entry["xp_reward"], entry["stat_rewards"])
                return True
        return False

    def reject_activity(self, activity_id):
        for entry in self.history:
            if entry.get("id") == activity_id and entry["status"] == "pending":
                entry["status"] = "rejected"
                return True
        return False

    def to_dict(self):
        return {
            "name": self.name,
            "char_class": self.char_class,
            "email": self.email,
            "password": self.password,
            "avatar_id": self.avatar_id,
            "level": self.level,
            "xp": self.xp,
            "stats": self.stats,
            "stats": self.stats,
            "history": self.history
        }

    @staticmethod
    def calculate_workout_rewards(workout_type, duration_minutes):
        """
        Süre ve türe göre ödül hesaplar.
        Base XP: Dakika başı 5 XP
        Stat: Her 30 dakikada +1 Primary, +0.5 Secondary (Tam sayıya yuvarlanır)
        """
        if duration_minutes <= 0:
            return 0, {}

        # Default config
        config = WORKOUT_MULTIPLIERS.get(workout_type, {"xp_mult": 1.0, "primary": "VIT", "secondary": "STR"})
        
        # XP Calculation
        base_xp = duration_minutes * 5
        final_xp = int(base_xp * config["xp_mult"])
        
        # Stat Calculation
        # Her 30 dk bir ana stat
        primary_gain = int(duration_minutes / 30)
        # Her 60 dk bir yan stat (veya 30 dk için 0.5 mantığı ama int casting ile 60dk gerekebilir)
        secondary_gain = int(duration_minutes / 45) # Biraz daha zor
        
        # En azından emek varsa 1 puan verelim mi? Hayır, süre teşviki olsun. 
        # Ama 10 dk antrenman yapana 0 stat vermek acımasız olabilir.
        # User request: "statlar ve expler süreye göre artmalı"
        
        stats = {}
        if primary_gain > 0:
            stats[config["primary"]] = primary_gain
        if secondary_gain > 0:
            stats[config["secondary"]] = secondary_gain
            
        return final_xp, stats

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            char_class=data["char_class"],
            password=data.get("password", ""), 
            email=data.get("email", ""), 
            avatar_id=data.get("avatar_id", "warrior_male"), 
            level=int(data["level"]), 
            xp=int(data["xp"]), 
            stats=data["stats"],
            history=data.get("history", [])
        )
    
    def get_avatar_image(self):
        # Determine base gender from initial avatar_id or defaults
        # Assume format was like "warrior_male" or we can infer/store gender. 
        # For now, let's detect from the stored avatar_id if it contains "female"
        gender = "female" if "female" in self.avatar_id else "male"
        
        # Level thresholds
        thresholds = [20, 15, 10, 5, 1]
        
        # Find the highest threshold the user has reached
        target_level = 1
        for t in thresholds:
            if self.level >= t:
                target_level = t
                break
        
        # Construct filename: e.g. "assets/avatars/male_10.png"
        path = f"assets/avatars/{gender}_{target_level}.png"
        
        # Local check if file exists (optional, keeping fallback simple)
        if os.path.exists(path):
             return path
        
        # Fallback if image missing
        return f"assets/avatars/{gender}_1.png"

class GameSystem:
    @staticmethod
    def load_characters():
        if not supabase:
            return {}
        try:
            # Fetch all characters from Supabase
            response = supabase.table("characters").select("*").execute()
            
            # Map 'data' column back to Character objects
            chars = {}
            for row in response.data:
                char_data = row['data']
                # Ensure name in data matches row name (it should)
                # char_data['name'] = row['name'] 
                chars[row['name']] = Character.from_dict(char_data)
            return chars
            
        except Exception as e:
            print(f"Error loading characters: {e}")
            return {}

    @staticmethod
    def save_character(character):
        if not supabase:
            return
        
        try:
            # Upsert into Supabase (Insert or Update)
            data_payload = {
                "name": character.name,
                "data": character.to_dict(),
                "updated_at": datetime.now().isoformat()
            }
            
            supabase.table("characters").upsert(data_payload).execute()
        except Exception as e:
            print(f"Error saving character: {e}")
            raise e
