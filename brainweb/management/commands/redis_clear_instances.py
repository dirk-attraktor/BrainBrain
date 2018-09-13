import redis
from django.core.management.base import BaseCommand, CommandError

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

class Command(BaseCommand):
    help = 'clear "individual.*", "population.*", "species.*", "referenceFunction.*", "cachecontrol.*", "instance.*", "locks.*" from redis'
    
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pipe = redisconnection.pipeline()
        cnt = 0
        for rkey in redisconnection.keys():
            rkey = rkey.decode("ASCII")
            for key in ["individual.", "population.", "species.", "referenceFunction.", "cachecontrol.", "instance.", "locks."]:
                if rkey.startswith(key):
                    cnt += 1
                    pipe.delete(rkey)
                    break
            if cnt % 10000 == 0 and cnt > 0:
                print("delete 10000")
                pipe.execute()
            
        pipe.execute()
