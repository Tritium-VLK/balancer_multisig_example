pool_tokens_query = """
        query {
          pools(first: 1000) {
            id
            totalLiquidity
            poolType
            totalWeight
            tokens {
              address
            }
          }
        }
        """
