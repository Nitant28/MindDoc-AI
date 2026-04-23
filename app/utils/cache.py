# Simple in-memory cache for repeated queries
from collections import OrderedDict

class QueryCache:
    def __init__(self, size=100):
        self.size = size
        self.cache = OrderedDict()
    def get(self, key):
        return self.cache.get(key)
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.size:
            self.cache.popitem(last=False)
