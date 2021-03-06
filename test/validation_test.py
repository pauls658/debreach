import os, math, random, shutil
from subprocess import call
from collections import defaultdict
import re
import mmap
from optparse import OptionParser

INPUT_DIR="input"
TOKENS_DIR="tokens"
TOKEN_RE_FILE = "test_data/token_res" 

site_REs = {}
#for line in open(TOKEN_RE_FILE, 'rb'):
#    site, regex = line.strip().split(' ', 1)
#    site_REs[site] = re.compile(regex)

def validate_validation():
    clear_dirs()
    for in_file in os.listdir(INPUT_DIR):
        full_file = INPUT_DIR + '/' + in_file
        print "Processing: " + full_file
        os.system('../minigzip ' + full_file)
        compressed_file = full_file + '.gz'
        br_file =  'decompbrs/' + in_file
        os.system('../minigzip -d ' + compressed_file + ' 2> ' + br_file)
        if not check_br_records(INPUT_DIR + '/' + in_file, br_file):
            print "Byte range check failed. Quitting."
            exit(1)

"""
Needs zlib to be compiled with -DVALIDATE_SEC.
"""
def check_br_records(in_file, br_file):
    with open(in_file, 'rb') as decomp_fd, open(br_file, 'rb') as br_fd:
        dcf_buf = decomp_fd.read()
        while True:
            # see if we got anything left
            br_buf = br_fd.read(1)
            if not br_buf:
                break
            # read two spaces
            first_space = True
            while True:
                temp = br_fd.read(1)
                if temp == ' ' and not first_space:
                    break
                elif temp == ' ':
                    first_space = False
                br_buf += temp

            br1, br2 = br_buf.split(' ', 1)
            br1 = map(int, br1.split('-', 1))
            br2 = map(int, br2.split('-', 1))
            match_len = br1[1] - br1[0] + 1
            # + 1 because we add a new line in output
            matched_string = br_fd.read(match_len + 1)
            # chomp the extra new line
            matched_string = matched_string[:-1]

            if matched_string != dcf_buf[br1[0]:br1[1] + 1]:
                print "Mismatch for br1: "
                print br1
                print "Actual string: " + matched_string
                print "Found: " + dcf_buf[br1[0]:br1[1] + 1]
                print "Found2: " + dcf_buf[br2[0]:br2[1] + 1]
                return False
            if matched_string != dcf_buf[br2[0]:br2[1] + 1]:
                print "Mismatch for br2:"
                print br2
                print "Actual string: " + matched_string
                print "Found: " + dcf_buf[br2[0]:br2[1] + 1]
                return False
        return True

def read_brs(br_file):
    brs = set()
    with open(br_file, 'rb') as br_fd:
        while True:
            # see if we got anything left
            br_buf = br_fd.read(1)
            if not br_buf:
                break
            # read two spaces
            first_space = True
            while True:
                temp = br_fd.read(1)
                if temp == ' ' and not first_space:
                    break
                elif temp == ' ':
                    first_space = False
                br_buf += temp

            br1, br2 = br_buf.split(' ', 1)
            s1, e1 = map(int, br1.split('-', 1))
            s2, e2 = map(int, br2.split('-', 1))
            brs.add((s1, e1))
            brs.add((s2, e2))
            match_len = e1 - s1 + 1
            # + 1 because we add a new line in output
            br_fd.read(match_len + 1)

    return list(brs)

def validate_sec_brs(tainted_brs, match_brs_file):
    match_brs = read_brs(match_brs_file)
    return not overlaps(tainted_brs, match_brs)

def overlaps(brs1, brs2):
    for (s1, e1) in brs2:
        for (s2, e2) in brs1:
            if  min(e1, e2) >= max(s1, s2):
                print str(s1) + '-' + str(e1)
                print str(s2) + '-' + str(e2)
                return True
    return False

def find_tokens(input_file, site_id):
    tokens = set()
    with open(input_file, 'r') as f_ref:
        for line in f_ref:
            for match in site_REs[site_id].finditer(line):
                tokens.add(match.group(1))
    return tokens 

# http://stackoverflow.com/questions/6980969/how-to-find-position-of-word-in-file
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

def random_brs(file_size, coverage=0.1, max_len=300, min_len=3):
    file_size = float(file_size)
    brs = []
    avg_size = math.ceil(float(max_len - min_len)/float(2))
    starts = random.sample(xrange(int(file_size)), int(math.ceil((file_size*coverage)/avg_size)))
    starts.sort()
    brs = []
    last_end = -1
    for i in range(len(starts)):
        if last_end >= starts[i]:
            # increase the last br end
            brs[-1] = (brs[-1][0], brs[-1][0] + random.randint(min_len, max_len + 1))
        else:
            brs.append((starts[i], starts[i] + random.randint(min_len, max_len + 1) - 1))

    if brs[-1][1] >= file_size:
        brs[-1] = (brs[-1][0], int(file_size - 1))

    return brs

br_RE = re.compile(r'^byteranges: [0-9 ]*$')
def validate_brs(br_file, tokens):
    with open(br_file, 'rb') as f_ref:
        line = f_ref.readline()
        while True:
            if not line:
                break
            if br_RE.search(line):
                _, brs_str = line.split(':', 1)
                brs_str = brs_str.strip()

                if not brs_str:
                    line = f_ref.readline()
                    continue

                brs = [int(b) for b in brs_str.split(' ')]

                line = f_ref.readline()
                buf = ""
                while line and not br_RE.search(line):
                    buf += line
                    line = f_ref.readline()

                for i in xrange(0, len(brs), 2):
                    print buf[brs[i]:brs[i+1] + 1]
            line = f_ref.readline()
    # Always True for now, until we implement some type of actual
    # validtion test
    return True

def clear_dirs():
    os.popen('rm -f output/* &> /dev/null')
    os.popen('rm -f output_lits/* &> /dev/null')
    os.popen('rm -f debug/* &> /dev/null')
    os.popen('rm -f brs/* &> /dev/null')
    os.popen('rm -f lz77_brs/* &> /dev/null')

def stored_test():
    clear_dirs()
    for in_file in os.listdir(INPUT_DIR):

        if in_file.endswith('.gz'): continue

        site_id = in_file.split('_')[0]
        print "Processing file: " + in_file
        if site_id not in site_REs:
            print "Error: no regex found for site_id=" + site_id
            exit(1)

        token = find_token(INPUT_DIR + '/' + in_file, site_id)

        if not token:
            print "Error: no token found"
            exit(1)

        tokens = [token]
        byte_ranges = find_byte_ranges(INPUT_DIR + '/' + in_file, token)
        num_tokens = len(byte_ranges) / 2
        print "Num tokens: " + str(num_tokens)
        # run debreach on the test file
        print '../minidebreach-stored -s ' + ','.join(tokens) + ' ' + INPUT_DIR + '/' + in_file + ' 1> output_lits/' + in_file + ' 2> debug/' + in_file
        os.system('../minidebreach-stored -s ' + ','.join(tokens) + ' ' + INPUT_DIR + '/' + in_file + ' 1> output_lits/' + in_file + ' 2> debug/' + in_file)
        os.system('mv ' + INPUT_DIR + '/' + in_file + '.gz output')
        # ensure that we find the token present in the literal output
        # the correct number of times
        if not validate_security('output/' + in_file + '.gz', token, num_tokens):
            print "Error: security validation failed"
            exit(1)
        # validate integreity
        continue
        ret = os.system('../minigzip -d output/' + in_file + '.gz 2> lz77_brs/' + in_file)
        if ret != 0:
            print "Error: non-zero exit status from gunzip"
            exit(1)

def brs_only():
    clear_dirs()
    for in_file in os.listdir(INPUT_DIR):
        site_id = in_file.split('_')[0]
        print "Processing file: " + in_file
        if site_id not in site_REs:
            print "Error: no regex found for site_id=" + site_id
            exit(1)

        token = find_token(INPUT_DIR + '/' + in_file, site_id)

        if not token:
            print "Error: no token found"
            exit(1)
        tokens = [token]
        print "Tokens found: " + ','.join(tokens)
        print '../minidebreach -s ' + ','.join(tokens) + ' ' + INPUT_DIR + '/' + in_file + ' 1> brs/' + in_file
        os.system('../minidebreach -s ' + ','.join(tokens) + ' ' + INPUT_DIR + '/' + in_file + ' 1> brs/' + in_file)
        os.system('mv ' + INPUT_DIR + '/' + in_file + '.gz output')

        # validate the brs
        if not validate_brs('brs/' + in_file, tokens):
            print "Error: bad tainted region"

def random_test():
    clear_dirs()
    for in_file in os.listdir(INPUT_DIR):
        if in_file.endswith('.gz'): continue
        byte_ranges = random_brs(os.path.getsize(INPUT_DIR + '/' + in_file), max_len=300, min_len=5)
        br_arg = ','.join(str(s) + ',' + str(e) for (s, e) in byte_ranges)
        # run debreach on the test file
        print '../minidebreach -b ' +  br_arg + ' ' + INPUT_DIR + '/' + in_file + ' 2> debug/' + in_file
        ret = os.system('../minidebreach -b ' + br_arg + ' ' + INPUT_DIR + '/' + in_file + ' 2> debug/' + in_file)
        if ret != 0:
            print "Error: non-zero exit status from minidebreach"
            print ret
            exit(1)
        
        shutil.move(INPUT_DIR + '/' + in_file + '.gz', 'output/' + in_file + '.gz')

        # validate integreity
        ret = os.system('../minigzip -d output/' + in_file + '.gz 2> lz77_brs/' + in_file)
        if ret != 0:
            print "Error: non-zero exit status from gunzip"
            exit(1)

        if not validate_sec_brs(byte_ranges, 'lz77_brs/' + in_file):
            print "Error: security validation failed"
            exit(1)
        else:
            os.remove('lz77_brs/' + in_file)
            os.remove('output/' + in_file)

def token_test(verbose=False):
    clear_dirs()

    all_tokens = defaultdict(set)
    for site_name in os.listdir(TOKENS_DIR):
        for line in open(TOKENS_DIR + "/" + site_name, 'rb'):
            line = line.strip()
            all_tokens[site_name].add(line)

    for in_file in os.listdir(INPUT_DIR):
        if in_file.endswith('.gz'): continue

        fp = INPUT_DIR + "/" + in_file
        site_name = in_file.split('_')[0]

        tainted_brs, present_tokens = find_byte_ranges(fp, all_tokens[site_name])

        unsafe_arg = ",".join(present_tokens)
        print "../minidebreach -s " + unsafe_arg + " " + fp + " 2> debug/" + in_file
        ret = os.system("../minidebreach -s '" + unsafe_arg + "' " + fp + " 2> debug/" + in_file)
        if ret != 0:
            print "Error: non-zero exit status from minidebreach"
            exit(1)

        shutil.move(INPUT_DIR + '/' + in_file + '.gz', 'output/' + in_file + '.gz')

        # validate integreity
        ret = os.system('../minigzip -d output/' + in_file + '.gz 2> lz77_brs/' + in_file)
        if ret != 0:
            print "Error: non-zero exit status from gunzip"
            exit(1)

        if verbose:
            print "Validating against brs:"
            print tainted_brs
        if not validate_sec_brs(tainted_brs, 'lz77_brs/' + in_file):
            print "Error: security validation failed"
            exit(1)
        else:
            os.remove('lz77_brs/' + in_file)
            os.remove('output/' + in_file)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-b", "--brs-only",
                        action="store_true", dest="brs_only", default=False,
                        help="Only very the byte ranges. Remember to compile with -DBRS_ONLY")
    parser.add_option("-s", "--stored",
                        action="store_true", dest="stored_test", default=False,
                        help="Test the debreach stored module")
    parser.add_option("-x", "--validate-validation",
                        action="store_true", dest="valval", default=False,
                        help="Validate the validation module lolololol")
    parser.add_option("-r", "--random-brs",
                        action="store_true", dest="random", default=False,
                        help="Do validation with random byte ranges")
    parser.add_option("-t", "--token-validation",
                        action="store_true", dest="token_test", default=False,
                        help="Do validation test for tokens")
    parser.add_option("-v", "--verbose",
                        action="store_true", dest="verbose", default=False,
                        help="Be verbose")
    (options, args) = parser.parse_args()
    if options.brs_only:
        brs_only()
    elif options.stored_test:
        stored_test()
    elif options.valval:
        validate_validation()
    elif options.random:
        random_test()
    elif options.token_test:
        token_test(options.verbose)
