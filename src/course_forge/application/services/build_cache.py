import hashlib
import json
import os

class BuildCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "build_cache.json")
        self.data = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def save(self):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save build cache: {e}")

    def get_file_hash(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def has_changed(self, src_path: str) -> bool:
        current_hash = self.get_file_hash(src_path)
        old_hash = self.data.get(src_path)
        
        if current_hash != old_hash:
            return True
        return False

    def update(self, src_path: str):
        self.data[src_path] = self.get_file_hash(src_path)
