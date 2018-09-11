import time
import redis

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

class RedisLock():    
    @staticmethod
    def lock(key, timeout = 400):
        for i in range(0, timeout):
            wasset = redisconnection.setnx("locks.%s.locked" % key , 23)
            if wasset == 1:
                redisconnection.expire("locks.%s.locked" % key, 180)
                #print("lock aquired")
                break
            print("lock %s is locked, waiting for our turn" % key)
            time.sleep(2)        
        
        
    @staticmethod
    def unlock(key):
        #print("lock released")
        redisconnection.delete("locks.%s.locked" % key)
