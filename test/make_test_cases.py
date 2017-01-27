"""
A script to make the the defs.h file for used by the benchtime.c program.
This script makes a C program that declares a static array of all the
input arguments necessary to run benchtime.c.
"""
import os, mmap, re
from collections import defaultdict

INPUT = 'input'
TEST_CASE_DIR = 'testcases'
TOKENS_DIR = 'tokens'
DEFS_FILE = 'defs.h'

def max_filename_len(in_dir):
    return max(len(f_name) for f_name in os.listdir(in_dir)) + len(in_dir) + 1

def find_tokens(input_file, tokens):
    found_tokens = set()
    with open(input_file, 'rb') as f_ref:
        # 0 means the whole file
        mf = mmap.mmap(f_ref.fileno(), 0, prot=mmap.PROT_READ)
        mf.seek(0)
        for match in re.finditer(r'|'.join(re.escape(token) for token in tokens), mf):
            found_tokens.add(match.group(0))
    return found_tokens

def get_all_tokens():
    all_tokens = defaultdict(set)
    for site_name in os.listdir(TOKENS_DIR):
        for line in open(TOKENS_DIR + "/" + site_name, 'rb'):
            line = line.strip()
            all_tokens[site_name].add(line)
    return all_tokens

def find_byte_ranges(input_file, tokens):
    brs = []
    found_tokens = set()
    with open(input_file, 'rb') as f_ref:
        # 0 means the whole file
        mf = mmap.mmap(f_ref.fileno(), 0, prot=mmap.PROT_READ)
        mf.seek(0)
        for match in re.finditer(r'|'.join(re.escape(token) for token in tokens), mf):
            brs.append((match.start(), match.end() - 1)) 
            found_tokens.add(match.group(0))
    return brs, found_tokens 

def make_test_cases(options, in_dir):
    max_token_len = -1
    max_num_tokens = -1
    all_tokens = get_all_tokens()

    for in_file in os.listdir(in_dir):
        fp = in_dir + "/" + in_file
        test_case_file = TEST_CASE_DIR + "/" + in_file
        [site_name, n1] = in_file.split('_')[:2]
        if "crafted" in site_name:
            present_tokens = find_tokens(fp, all_tokens[n1])
        else:
            present_tokens = find_tokens(fp, all_tokens[site_name])

        brs, _ = find_byte_ranges(fp, present_tokens)        

        with open(test_case_file, 'w+') as fd:
            fd.write(",".join(str(s) + "," + str(e) for s, e in brs))

def main():
    filename_len = max_filename_len(INPUT)
    num_inputs = len(os.listdir(INPUT))
    tokens_data, max_num_tokens, max_token_len = get_token_data(INPUT)
    with open(DEFS_FILE, 'w+') as def_fd:
        # write the number of files in the array
        def_fd.write('#define NUM_IN_FILES %d\n' % num_inputs)
        # write the declaration
        def_fd.write('extern char in_files[%d][%d] = {\n' % (num_inputs, filename_len + 1))
        def_fd.write(',\n'.join("\t\"" + f_name + "\"" for f_name in sorted(os.listdir(INPUT)))) 
        def_fd.write('};\n')

if __name__ == "__main__":
    make_test_cases(None, INPUT)
