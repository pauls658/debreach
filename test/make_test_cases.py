"""
A script to make the the defs.h file for used by the benchtime.c program.
This script makes a C program that declares a static array of all the
input arguments necessary to run benchtime.c.
"""
import os, mmap, re
from collections import defaultdict
from optparse import OptionParser


INPUT = 'input'
TEST_CASE_STREAM = 'stream'
TOKENS_DIR = 'tokens'

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
    if not tokens:
        return [], set()
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
    if not options.zlib:
        all_tokens = get_all_tokens()

    file_buf = ""
    for in_file in os.listdir(in_dir):
        fp = in_dir + "/" + in_file

        [site_name, n1] = in_file.split('_')[:2]
        if not options.zlib:
            if "crafted" in site_name:
                present_tokens = find_tokens(fp, all_tokens[n1])
            else:
                present_tokens = find_tokens(fp, all_tokens[site_name])
    
            brs, _ = find_byte_ranges(fp, present_tokens)        

        if options.tokens:
            file_buf += "%s %s/%s\n" % (",".join(present_tokens), INPUT, in_file)
        elif options.brs:
            file_buf += "%s %s/%s\n" % (','.join("%d,%d" % (start, end) for start, end in brs), INPUT, in_file)
        elif options.zlib:
            file_buf += "%s/%s\n" % (INPUT, in_file)
        else:
            print "WHY I HAB NO OPTION"
            exit(1)

    with open(TEST_CASE_STREAM, 'w+') as out_fd:
        out_fd.write(file_buf)

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
    parser = OptionParser()
    parser.add_option("-b", "--brs",
                        action="store_true", dest="brs", default=False,
                        help="Output byte ranges to test cases")
    parser.add_option("-t", "--tokens",
                        action="store_true", dest="tokens", default=False,
                        help="Output tokens to test cases")
    parser.add_option("-z", "--zlib",
                        action="store_true", dest="zlib", default=False,
                        help="Output nothing to the test cases (used for plain zlib)")
    (options, args) = parser.parse_args()

    if not options.brs and not options.tokens and not options.zlib:
        print "I need to know which module you are testing."
        print "Specify with -b, -t, or -z"
        exit(1)
    make_test_cases(options, INPUT)
