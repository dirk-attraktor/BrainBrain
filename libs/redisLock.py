import time
import redis

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

class RedisLock():    
    def __init__(self, key):
        self.key = key
        
    def __enter__(self):
        for i in range(0, 999):
            wasset = redisconnection.setnx("locks.%s.locked" % self.key , 23)
            if wasset == 1:
                redisconnection.expire("locks.%s.locked" % self.key, 180)
                break
            print("lock %s is locked, waiting for our turn" % self.key)
            time.sleep(2) 
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        redisconnection.delete("locks.%s.locked" % self.key)
