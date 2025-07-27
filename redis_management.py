import redis


class RedisConnections:
    def __init__(self, host='localhost', port='6379 ', decode_responses=True):
        self.dbs = {}
        for db_index in range(6):  # assuming databases 0 to 5
            self.dbs[db_index] = redis.StrictRedis(host=host, port=port, db=db_index, decode_responses=decode_responses)

    def get_db(self, db_index):
        return self.dbs.get(db_index)
