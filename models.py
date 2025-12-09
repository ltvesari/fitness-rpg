import json
import os
import hashlib
from datetime import datetime

# Sabitler
XP_PER_LEVEL_MULTIPLIER = 1000
DATA_FILE = "characters.json"

class Character:
    def __init__(self, name, char_class, password, avatar_id="warrior_male", level=1, xp=0, stats=None, history=None):
        self.name = name
        self.char_class = char_class
        # Store password as simple hash for this MVP (Not secure for prod, but fits request scope)
        self.password = self._hash_password(password) if len(password) < 64 else password
        self.avatar_id = avatar_id
        self.level = level
        self.xp = xp
        self.stats = stats if stats else self._get_initial_stats()
        self.history = history if history else []

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password == self._hash_password(password)

    def get_avatar_image(self):
        """Seviyeye göre avatar görselini döndürür."""
        # Determine tier based on level
        if self.level < 5:
            tier = "lvl1"
        elif self.level < 10:
            tier = "lvl10" # Intermediate
        else:
            tier = "lvl20" # Master / Evolved
            
        # Dosya yolunu oluştur
        path = f"assets/avatars/{self.avatar_id}_{tier}.png"
        
        # Eğer henüz o seviyenin görseli yoksa (örn lvl20 daha çizilmediyse), lvl1'e fallback yap
        if not os.path.exists(path):
             # Fallback logic: try lvl10 then lvl1
             if tier == "lvl20" and os.path.exists(f"assets/avatars/{self.avatar_id}_lvl10.png"):
                 return f"assets/avatars/{self.avatar_id}_lvl10.png"
             return f"assets/avatars/{self.avatar_id}_lvl1.png"
             
        return path

    def _get_initial_stats(self):
        """Sınıfa göre başlangıç statlarını belirler."""
        base_stats = {"STR": 10, "AGI": 10, "VIT": 10, "WIS": 10}
        if self.char_class == "Savaşçı":
            base_stats["STR"] += 5
        elif self.char_class == "Korucu":
            base_stats["AGI"] += 3
            base_stats["VIT"] += 2
        elif self.char_class == "Keşiş":
            base_stats["WIS"] += 5
        return base_stats

    def add_xp(self, amount):
        """XP ekler ve seviye atlamayı kontrol eder."""
        # Sınıf bonusları
        # Not: Bu mantık aktivite tipine göre dışarıdan çağrılırken handle edilmeli
        # veya buraya aktivite tipi parametresi eklenmeli. 
        # Şimdilik düz XP ekliyoruz.
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
        # Basitçe tüm statlara +1 ekleyelim
        for stat in self.stats:
            self.stats[stat] += 1

    def log_activity(self, activity_type, description, xp_reward, stat_rewards=None, proof_image=None):
        """Aktivite kaydeder."""
        
        # ID oluştur (Basit timestamp tabanlı)
        activity_id = f"{self.name}_{int(datetime.now().timestamp())}"

        entry = {
            "id": activity_id,
            "date": datetime.now().isoformat(),
            "type": activity_type,
            "description": description,
            "xp_reward": xp_reward,
            "stat_rewards": stat_rewards,
            "proof_image": proof_image,
            "status": "pending" if proof_image else "approved" # Fotoğraf varsa onay bekle
        }
        
        # Eğer kanıt yoksa veya basit bir işlemse (örn su içme) direkt onaylı sayılabilir
        # Ama isteğe göre her şey onaya düşebilir. Şimdilik sadece proof_image varsa pending.
        
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
            "password": self.password,
            "avatar_id": self.avatar_id,
            "level": self.level,
            "xp": self.xp,
            "stats": self.stats,
            "history": self.history
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            char_class=data["char_class"],
            password=data.get("password", ""), # Fallback for old data if any
            avatar_id=data.get("avatar_id", "warrior_male"), # Default for existing users
            level=int(data["level"]), # Ensure int
            xp=int(data["xp"]), # Ensure int
            stats=data["stats"],
            history=data.get("history", [])
        )

class GameSystem:
    @staticmethod
    def load_characters():
        if not os.path.exists(DATA_FILE):
            return {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {name: Character.from_dict(char_data) for name, char_data in data.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    @staticmethod
    def save_character(character):
        characters = GameSystem.load_characters()
        characters[character.name] = character
        
        data = {name: char.to_dict() for name, char in characters.items()}
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
