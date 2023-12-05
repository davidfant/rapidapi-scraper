import os
import json
import argparse
import requests
from tqdm import tqdm
from datasets import load_from_disk

graphql_endpoint = 'https://rapidapi.com/gateway/graphql'

collections_query = '''
query GetCollectionsCollapsed($page: Int, $limit: Int) {
  collections: collapsedCollections(
    orderByField: "weight"
    orderDirection: asc
    page: $page
    limit: $limit
  ) {
    id
    title
    slugifiedKey
    weight
    thumbnail
    shortDescription
    items: apis
    type: __typename
  }
}
'''

categories_query = '''
{
  categories: categoriesV2 {
    nodes {
      id
      createdAt
      name
      weight
      slugifiedName
      thumbnail
      status
      longDescription
      shortDescription
      type: __typename
      __typename
    }
    __typename
  }
}
'''

products_query = '''
query GetProducts(
	$searchApiWhereInput: SearchApiWhereInput!,
	$paginationInput: PaginationInput
) {
  products: searchApis(
    where: $searchApiWhereInput
    pagination: $paginationInput
  ) {
    nodes {
      type: __typename
      __typename
      id
      name
      title
      description
      visibility
      slugifiedName
      pricing
      updatedAt
      category: categoryName
      thumbnail
			score {
				avgServiceLevel
				avgLatency
				avgSuccessRate
				popularityScore
				__typename
			}
      user: User {
        id
        username: username
        __typename
      }
      version {
        id
#         endpoints(pagingArgs: {limit: 3}) {
				endpoints {
          id
          isGraphQL
          route
          method
          name
          description
					params {
						parameters
					}
					responsePayloads {
						id
						name
						format
						body
						headers
						description
						type
						statusCode
						examples
						schema
					}
          __typename
        }
        __typename
      }
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
      __typename
    }
    queryID
    replicaIndex
    total
    __typename
  }
}
'''


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--page-size', type=int, default=10)
  parser.add_argument('--output-dir', type=str, default='data')
  parser.add_argument('--csrf-token', type=str, required=True)
  parser.add_argument('--cookie', type=str, required=True)
  parser.add_argument('--offset', type=int, default=0)
  return parser.parse_args()


def get_collections(headers):
  response = requests.post(
    graphql_endpoint,
    json={'query': collections_query, 'variables': {} },
    headers=headers
  )
  return response.json()['data']['collections']


def get_categories(headers):
  response = requests.post(
    graphql_endpoint,
    json={'query': categories_query, 'variables': {} },
    headers=headers
  )
  return response.json()['data']['categories']['nodes']


def get_products(filters, pagination_token, page_size, headers):
  variables = {
    'searchApiWhereInput': { 'term': '', **filters },
    'paginationInput': { 'first': args.page_size, 'after': pagination_token },
    'searchApiOrderByInput': {
      'sortingFields': [{ 'fieldName': 'installsAllTime', 'by': 'ASC' }]
    }
  }

  response = requests.post(
    graphql_endpoint,
    json={'query': products_query, 'variables': variables},
    headers=headers
  )

  if response.status_code != 200:
    print(response.text)
    return [], None, 0

  products = response.json()['data']['products']['nodes']
  pagination_token = response.json()['data']['products']['pageInfo']['endCursor']
  total = response.json()['data']['products']['total']
  return products, pagination_token, total


if __name__ == '__main__':
  args = parse_args()

  headers = {
    'content-type': 'application/json',
    'csrf-token': args.csrf_token,
    'cookie': args.cookie,
  }
  product_ids = set()
  # for collection in tqdm(get_collections(headers)[args.offset:], desc='Collections'):
  #   filters = { 'collectionIds': [collection['id']] }
  #   group_name = collection['slugifiedKey']
  for category in tqdm(get_categories(headers)[args.offset:], desc='Categories'):
    filters = { 'categoryNames': [category['name']] }
    group_name = category['name']

    pagination_token: str = None
    group_product_ids = set()
    while True:
      products, pagination_token, total = get_products(filters, pagination_token, args.page_size, headers)

      print(f'Fetched {len(products) + len(group_product_ids)} products in {group_name} of {total} total ({products[0]["id"] if products else None})')

      for product in products:
        product_path = os.path.join(args.output_dir, product['category'] or 'None', product['slugifiedName'] + '.json')

        if not os.path.exists(os.path.dirname(product_path)):
          os.makedirs(os.path.dirname(product_path))
        
        with open(product_path, 'w') as f:
          json.dump(product, f, indent=2)
      
      group_product_ids.update([product['id'] for product in products])
      if len(products) < args.page_size:
        break
    
    product_ids_len = len(product_ids)
    product_ids.update(group_product_ids)
    print(f'Fetched {len(group_product_ids)} ({len(product_ids) - product_ids_len} unique, {len(product_ids)} total) products for group: {group_name}')


