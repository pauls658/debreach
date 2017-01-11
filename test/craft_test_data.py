import os, glob, random
from collections import defaultdict

OUTPUT_DIR = "input"
TOKENS_DIR = "tokens"
TEST_DATA_DIR = "test_data"
DOCS_DIR = "docs"
IGNORE_DIRS = ["crafted", "token_res"]
DATA_TYPES = ["application/x-javascript", "text/html"]

def get_strings(file_name, num_strings):
    min_len = 20
    max_len = 300

    buf = ""
    with open(file_name, 'rb') as f_ref:
        buf = f_ref.read()

    strings = []

    for _ in xrange(num_strings):
        start = random.randint(0, len(buf))
        end = random.randint(min_len, max_len)
        if start + end > len(buf):
            end = len(buf)
        strings.append(buf[start:end])

    return strings

def craft_data(site_name, data_type, tokens):
    total_strings = 5000
    number_files = 20
    file_size = 100000
    
    strings = []
    files = glob.glob(TEST_DATA_DIR + "/" + site_name + "/" + DOCS_DIR + "/" + data_type + "*")

    if not files:
        return False

    for file_name in files:
        strings.extend(get_strings(file_name, total_strings/len(files))) 

    partial_tokens = []
    for _ in xrange(100):
        token = random.choice(tokens)
        start = random.randint(0, len(token) - 1)
        end = random.randint(1, len(token) - 1)
        if start + end > len(token):
            end = len(token)
        partial_tokens.append(token[start:end])

    the_data = [tokens, partial_tokens, strings]
    for i in xrange(number_files):
        outfile_name = OUTPUT_DIR + "/crafted_" + site_name + "_" + data_type.replace("/", "_") + "_" + str(i)
        buf = ''.join(["CRAFTED_TOKEN=\"" + token +"\"" for token in tokens])
        while len(buf) < file_size:
            buf += random.choice(random.choice(the_data))
        with open(outfile_name, 'w+') as out_ref:
            out_ref.write(buf)

def main():
    for site_name in os.listdir(TEST_DATA_DIR):
        if site_name in IGNORE_DIRS: continue

        all_tokens = [line.strip() for line in open(TOKENS_DIR + "/" + site_name, 'rb')]

        for data_type in DATA_TYPES:
            if not craft_data(site_name, data_type, all_tokens):
                print "Could not craft data of type " + data_type + " for site " + site_name

if __name__ == "__main__":
    main()
