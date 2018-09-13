import time
import redis

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

class RedisLock():    
    def __init__(self, key):
        self.key = key
        
    def __enter__(self):
        for i in range(0, 10000):
            wasset = redisconnection.setnx("locks.%s.locked" % self.key , 23)
            if wasset == 1:
                redisconnection.expire("locks.%s.locked" % self.key, 240)
                break
            if i % 10 == 0:
                print("lock %s is locked, waiting for our turn %s" % (self.key, i))
            time.sleep(0.2) 
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        redisconnection.delete("locks.%s.locked" % self.key)
