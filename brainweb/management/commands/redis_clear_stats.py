import redis
from django.core.management.base import BaseCommand, CommandError

redisconnection = redis.StrictRedis(unix_socket_path='/var/run/redis/redis.sock', db=8)

class Command(BaseCommand):
    help = 'clear stats from redis'
    
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pipe = redisconnection.pipeline()
        for rkey in redisconnection.keys():
            rkey = rkey.decode("ASCII")
            for key in ["stats."]:
                if rkey.startswith(key):
                    pipe.delete(rkey)
                    break
        pipe.execute()
