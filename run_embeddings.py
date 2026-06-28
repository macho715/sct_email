import sys
sys.path.insert(0, ".")
from build_db import add_embeddings, DB
add_embeddings(DB)
print("EMBEDDINGS COMPLETE")
