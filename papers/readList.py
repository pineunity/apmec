import os
import ast

base_path = os.path.dirname(os.path.abspath(__file__))


req_path = base_path + '/' + 'requests.txt'
with open(req_path, 'r') as f:
        for line in f:
            a = ast.literal_eval(line)
            print type(a)