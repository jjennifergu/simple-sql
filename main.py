import json
import re

DEBUG = False
LOG_OPS = {'AND', 'OR'}
EQ_OPS = {'=', '!=', '<', '>'}


def parse_json_file(file_path):   
  try: 
    with open(file_path) as f:
      json_str = f.read()

      try:
        return json.loads(json_str)
      except json.JSONDecodeError:
        return None

  except FileNotFoundError:
    return None


def parse_where_clause(cond_str):
  # tokenize
  tokens = re.split(r"(\band\b|\bor\b|\(|\))", cond_str, flags=re.IGNORECASE)
  tokens = [token.strip() for token in tokens if token.strip()]

  # parse expression
  def parse_expression(tokens):

    stack = []
    i = 0
    while i < len(tokens):
      token = tokens[i]
      
      # parentheses
      if token == '(':
        sub_expr = []
        depth = 1
        i += 1
        while i < len(tokens):
          if tokens[i] == '(':
            depth += 1
          elif tokens[i] == ')':
            depth -= 1
            if depth == 0:
              break
          sub_expr.append(tokens[i])
          i += 1
        stack.append(parse_expression(sub_expr))

      # logic operators
      elif token in LOG_OPS:
        stack.append(token)
      
      # equality operators
      elif any(eq_op in token for eq_op in EQ_OPS):
        v1, op, v2 = re.split(r"(!=|=|<|>)", token, maxsplit=1)
        v1 = v1.strip().strip("'\"") # remove quotes
        v2 = v2.strip().strip("'\"")
        stack.append((v1, op.strip(), v2))

      # literals
      elif token.isdigit():
        stack.append(bool(token))
      elif token.lower() == 'true':
        stack.append(True)

      # False otherwise
      else:
        stack.append(False)

      i += 1
    
    # remove unnecessary parentheses
    if len(stack) == 1:
      return stack[0]
    
    return stack
      
  return parse_expression(tokens)


def parse_sql(sql_str):
  # regex pattern
  pattern = (
    r"SELECT\s+(?P<select>\*|[\w\s,]+)\s+" # SELECT * or SELECT field1, field2
    r"FROM\s+(?P<table>\w+)\s*" # FROM table
    r"(?:WHERE\s+(?P<where>.+?)\s*)?" # WHERE clause
    r"(?:LIMIT\s+(?P<limit>\d+))?\s*;" # LIMIT number;
  )

  # match pattern
  match = re.search(pattern, sql_str, flags=re.IGNORECASE)
  if not match:
    return None

  # parse fields
  columns = match.group("select").split(",")
  columns = [c.strip() for c in columns]

  table_name = match.group("table")
  if table_name.lower() != 'table':
    return None

  where_clause = match.group("where")
  conditions = parse_where_clause(where_clause) if where_clause else None

  limit = match.group("limit")
  limit = int(limit) if limit else None

  return columns, conditions, limit


def match_conditions(row, conditions):
  # literal
  if isinstance(conditions, bool):
    return conditions
  
  # logic operators
  elif len(conditions) > 2 and conditions[1] in LOG_OPS:
    left, op, right = conditions[0], conditions[1], conditions[2:]

    # single condition on the right
    if len(right) == 1:
      right = right[0]

    if op == 'AND':
      return match_conditions(row, left) and match_conditions(row, right)
    elif op == 'OR':
      return match_conditions(row, left) or match_conditions(row, right)

  # equality operators
  elif len(conditions) == 3 and conditions[1] in EQ_OPS:
    v1, op, v2 = conditions

    if isinstance(v1, str) and v1 in row:
      v1 = row[v1]
    elif v1.isdigit():
      v1 = float(v1)

    if isinstance(v2, str) and v2 in row:
      v2 = row[v2]
    elif v2.isdigit():
      v2 = float(v2)

    if op == '=':
      return v1 == v2
    elif op == '!=':
      return v1 != v2
    elif op == '<':
      return v1 < v2
    elif op == '>':
      return v1 > v2
  
  else:
    return False


def execute_query(table, parsed_query):
  columns, conditions, limit = parsed_query
  
  # filter by conditions
  if conditions is not None:
    filtered_rows = [row for row in table if match_conditions(row, conditions)]
  else:
    filtered_rows = table

  # select columns
  if columns[0] == '*':
    columns = list(table[0].keys())

  selected_cols = [
    {col: row[col] if col in row else None for col in columns} 
    for row in filtered_rows
  ]

  # limit output
  if limit:
    selected_cols = selected_cols[:limit]

  # return columns and selected columns
  return columns, selected_cols


def print_table(columns, table):
  for i in range(len(columns)):
    col = columns[i]
    print(col.center(20), end='')
    if i != len(columns) - 1:
      print('|', end='')
  
  print('\n', '-' * len(columns) * 20)

  for row in table:
    for i in range(len(columns)):
      col = columns[i]
      print(str(row[col]).center(20), end='')
      if i != len(columns) - 1:
        print('|', end='')
    print()
  
  print()

 
if __name__ == '__main__':
  
  json_str = None

  if DEBUG:
    test_queries = [
      "SELECT state FROM table WHERE pop > 1000000 AND state != 'California';",
      "SELECT * FROM table WHERE pop > 1000000000 OR (pop > 1000000 AND region = 'Midwest');",
      "SELECT * FROM table WHERE pop_male > pop_female;"
    ]
    parsed_json = parse_json_file('test.json')
    for query in test_queries:
      parsed_query = parse_sql(query)
      columns, table = execute_query(parsed_json, parsed_query)
      print_table(columns, table)
    
  else:
    print("\n-------------------- Welcome to the Simple SQL parser --------------------\n")
    print("Please enter the path of a JSON file representing your table:")

    # take command line input
    parsed_json = parse_json_file(input())
    
    # validate input
    while (parsed_json is None):
      print('Invalid input. Please enter a valid path to a JSON file that represents rows of a table.')
      parsed_json = parse_json_file(input())
    
    print("\nYour table (TABLE) has been successfully created!")

    option = 1

    while option:
      print("\nPlease enter your SQL query (e.g. SELECT * FROM TABLE;):")

      # take command line input
      query = parse_sql(input())

      # validate input
      while (query is None):
        print('Invalid input. Please enter a valid SQL query. (e.g. SELECT * FROM TABLE;)')
        query = parse_sql(input())
      
      try:
        columns, table = execute_query(parsed_json, query)
        print("\nSQL query successfully executed.\n")
        print_table(columns, table)
      except Exception as e:
        print(f"Error: {e}")
      
      print("Would you like to execute another query?\n 0: No\n 1: Yes")
      option = int(input())
    
    print("\nThank you for using the Simple SQL parser!\n")

    