import random

randomSeed = '0.166241939035787'
random = random.Random(randomSeed)

# NETWORK SETTINGS
NUM_INIT_NODES = 600
NUM_SEEDERS = 6
DNS_QUERY_SIZE = 40

# NODE TYPES
PEER = 0
SEEDER = 1
DARK = 2

# NODE ATTRIBUTES
NUM_TRIED_BUCKETS = 64
NUM_NEW_BUCKETS = 256

# EVENT TYPES
RESTART = 0
DROP = 1
JOIN = 2
CONNECT = 3
CONNECTION_FAILURE = 4
REQUEST_CONNECTION = 5
CONNECTION_INFO = 6
