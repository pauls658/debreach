"""
Makes random byte range test cases for measuring execution time. Outputs the test
cases as a C header file to be used in compressstream.c.
"""
import os, mmap, re, math, random
import glob
from collections import defaultdict
from optparse import OptionParser


INPUT = 'input'
OUTPUT = 'streams'
TEST_CASE_STREAM = 'stream'
TOKENS_DIR = 'tokens'
INC=0.1

#def test_case_line(filename, arg):
        #return " %s %s/%s\n" % (','.join("%d,%d" % (start, end) for start, end in arg), INPUT, filename)

# .001 gives us 1000 chunks
CHUNK_PROP = 0.001
def random_brs(file_size, coverage):
    if coverage >= 1.0:
        return [(0, file_size - 1)] 
    elif coverage <= 0.0:
        return [(0,0)]

    chunk_size = int(math.ceil(file_size*CHUNK_PROP))
    if chunk_size < 20:
        chunk_size = 20

    chunks = xrange(0, file_size, chunk_size)
    start_bytes = sorted(random.sample(chunks, int(math.ceil(coverage*len(chunks)))))
    brs = []
    first = start_bytes[0]
    last = start_bytes[0]
    for byte in start_bytes[1:]:
        #if byte - chunk_size == last
        # we are still in the same range
        if byte - chunk_size != last:
            brs.append((first, last + chunk_size - 1)) 
            first = byte
        last = byte

    # close the last byte range
    if last + chunk_size - 1 >= file_size:
        last = file_size - 1 
    brs.append((first, last))
    return brs 

def get_all_tokens():
    all_tokens = defaultdict(set)
    for site_name in os.listdir(TOKENS_DIR):
        for line in open(TOKENS_DIR + "/" + site_name, 'rb'):
            line = line.strip()
            all_tokens[site_name].add(line)
    return all_tokens

def make_zlib_test_cases(options, in_dir):
    print "TODO: make_zlib_test_cases"
    exit(1)

def make_token_test_cases(options, in_dir):
    print "TODO: make_token_test_cases"
    exit(1)

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

def make_br_test_cases(options, in_dir):
    all_tokens = get_all_tokens()
   
    sitenames = set(filename.split('_')[0] for filename in os.listdir(in_dir))
    for sitename in sitenames:
        num_in_files = len(glob.glob(in_dir + "/" + sitename + "*"))
        file_buf = "#define NUM_TEST_CASES %d\n" % (num_in_files)
        file_buf += "extern char * const in_files[] = {\n"
        arg_buf = "extern int const arg[] = {\n"
        arg_len_buf = "extern int const arg_len[] = {\n"
        for fp in glob.glob(in_dir + "/" + sitename + "*"):
            in_file = fp.split("/")[-1]
            filesize = os.path.getsize(fp)

            brs, _ = find_byte_ranges(fp, all_tokens[sitename])
            
            file_buf += "\"%s\",\n" % (fp)
            if brs:
                arg_buf += "%s,0,0,\n" % (",".join("%d,%d" % (start, end) for start, end in brs))
            else:
                arg_buf += "0,0,\n"
            arg_len_buf += "%d,\n" % (len(brs)*2 + 2)

        file_buf = file_buf[:-2]
        arg_buf = arg_buf[:-2]
        arg_len_buf = arg_len_buf[:-2]

        file_buf += "\n};\n\n"
        arg_buf += "\n};\n\n"
        arg_len_buf += "\n};\n\n"
    
        output_file = OUTPUT + "/" + TEST_CASE_STREAM + "_br_" + \
                sitename + ".h"
        with open(output_file, 'w+') as out_fd:
            out_fd.write(file_buf)
            out_fd.write(arg_buf)
            out_fd.write(arg_len_buf)




def make_randombr_test_cases(options, in_dir):
    coverage = 0.0
   
    sitenames = set(filename.split('_')[0] for filename in os.listdir(in_dir))
    while coverage <= 1.0:
        for sitename in sitenames:
            num_in_files = len(glob.glob(in_dir + "/" + sitename + "*"))
            file_buf = "#define NUM_TEST_CASES %d\n" % (num_in_files)
            file_buf += "extern char * const in_files[] = {\n"
            arg_buf = "extern int const arg[] = {\n"
            arg_len_buf = "extern int const arg_len[] = {\n"
            for fp in glob.glob(in_dir + "/" + sitename + "*"):
                in_file = fp.split("/")[-1]
                filesize = os.path.getsize(fp)

                brs = random_brs(filesize, coverage)
                
                file_buf += "\"%s\",\n" % (fp)
                arg_buf += "%s,0,0,\n" % (",".join("%d,%d" % (start, end) for start, end in brs))
                arg_len_buf += "%d,\n" % (len(brs)*2 + 2)

            file_buf = file_buf[:-2]
            arg_buf = arg_buf[:-2]
            arg_len_buf = arg_len_buf[:-2]

            file_buf += "\n};\n\n"
            arg_buf += "\n};\n\n"
            arg_len_buf += "\n};\n\n"
        
            stream_id = int(round(coverage*10))
            output_file = OUTPUT + "/" + TEST_CASE_STREAM + "_randombr_" + \
                    sitename + "_" + str(stream_id) + ".h"
            with open(output_file, 'w+') as out_fd:
                out_fd.write(file_buf)
                out_fd.write(arg_buf)
                out_fd.write(arg_len_buf)

        coverage += 0.1

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-b", "--brs",
                        action="store_true", dest="brs", default=False,
                        help="Output byte ranges to test cases. By default, the byte ranges\
                                correspond to tokens. For random byte ranges, use -r.")
    parser.add_option("-r", "--random",
                        action="store_true", dest="random", default=False,
                        help="Generate random byte ranges rather than token byte ranges. Must\
                                used with -b.")
    parser.add_option("-t", "--tokens",
                        action="store_true", dest="tokens", default=False,
                        help="Output tokens to test cases.")
    parser.add_option("-z", "--zlib",
                        action="store_true", dest="zlib", default=False,
                        help="Output nothing to the test cases.")
    (options, args) = parser.parse_args()

    if options.brs:
        if options.random:
            make_randombr_test_cases(options, INPUT)
        else:
            make_br_test_cases(options, INPUT)
    elif options.random:
        parser.error("-r used without -b")
    elif options.tokens:
        make_token_test_cases(options, INPUT)
    elif options.zlib:
        make_zlib_test_cases(options, INPUT)
    else:
        parse.error("need an option")
        exit(1)
