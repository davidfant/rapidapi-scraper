import os
import json
from collections import defaultdict

if __name__ == '__main__':
  # loop through data dir recrusively and count number of json files
  data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

  counts = defaultdict(int)
  for root, dirs, files in os.walk(data_dir):
    for file in files:
      if file.endswith('.json'):
        counts['products'] += 1

        with open(os.path.join(root, file), 'r') as f:
          data = json.load(f)
          if not data['version']:
            continue
          for endpoint in data['version']['endpoints']:
            counts['endpoints'] += 1
            if endpoint['responsePayloads']:
              counts['endpoints_with_examples'] += 1
            counts['endpoint_examples'] += len(endpoint['responsePayloads'])
  
  print(json.dumps(counts, indent=2))
