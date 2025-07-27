import redis
import json


# Setup Redis connection
redis_host = "localhost"  # Change as per your setup
redis_port = 6379         # Default port
db_index = 3           # Database index for games, change as needed

# Initialize Redis client
r = redis.StrictRedis(host=redis_host, port=redis_port, db=db_index, decode_responses=True)

# Fetch game dictionary data
game_dict_data = r.get("game_dict")

if game_dict_data:
    # Assuming the data is stored in JSON format
    game_dict = json.loads(game_dict_data)
    print("game Dictionary is populated with the following data:")
    print(json.dumps(game_dict, indent=4))
else:
    print("game Dictionary is not populated.")
