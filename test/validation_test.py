import os
import re
import mmap
from optparse import OptionParser

INPUT_DIR='./input'

site_REs = {
        'gmail' : re.compile(r'GM_ACTION_TOKEN="(\w*)"')
}

def find_token(input_file, site_id):
    with open(input_file, 'r') as f_ref:
        for line in f_ref:
            match = site_REs[site_id].search(line)
            if match:
                return match.group(1) 
    return None 

# http://stackoverflow.com/questions/6980969/how-to-find-position-of-word-in-file
def find_byte_ranges(input_file, token):
    brs = []
    with open(input_file, 'rb') as f_ref:
        # 0 means the whole file
        mf = mmap.mmap(f_ref.fileno(), 0, prot=mmap.PROT_READ)
        mf.seek(0)
        for match in re.finditer(token, mf):
            brs.append(match.start())
            brs.append(match.end())
    return brs 

def validate_security(input_file, token, num_tokens):
    with open(input_file, 'r') as f_ref:
        mf = mmap.mmap(f_ref.fileno(), 0, prot=mmap.PROT_READ)
        mf.seek(0)
        found_tokens = 0
        for _ in re.finditer(token, mf):
            found_tokens += 1
    return num_tokens == found_tokens

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
                    print buf[brs[i]:brs[i+1]]
            line = f_ref.readline()
    return True

def clear_dirs():
    os.system('rm output/*')
    os.system('rm output_lits/*')
    os.system('rm debug/*')
    os.system('rm brs/*')

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
        print "Token found: " + token

        os.system('../minidebreach -s ' + token + ' ' + INPUT_DIR + '/' + in_file + ' 1> brs/' + in_file)
        os.system('mv ' + INPUT_DIR + '/' + in_file + '.gz output')

        # validate the brs
        if not validate_brs('brs/' + in_file, [token]):
            print "Error: bad tainted region"

def full_test():
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
        print "Token found: " + token

        byte_ranges = find_byte_ranges(INPUT_DIR + '/' + in_file, token)
        num_tokens = len(byte_ranges) / 2

        # run debreach on the test file
        print '../minidebreach -b ' + ','.join(str(n) for n in byte_ranges) + ' ' + INPUT_DIR + '/' + in_file + ' 1> output_lits/' + in_file + ' 2> debug/' + in_file
        os.system('../minidebreach -b ' + ','.join(str(n) for n in byte_ranges) + ' ' + INPUT_DIR + '/' + in_file + ' 1> output_lits/' + in_file + ' 2> debug/' + in_file)
        os.system('mv ' + INPUT_DIR + '/' + in_file + '.gz output')
        # ensure that we find the token present in the literal output
        # the correct number of times
        if not validate_security('output_lits/' + in_file, token, num_tokens):
            print "Error: did not find correct number of tokens"
            exit(1)
        # validate integreity
        ret = os.system('gunzip output/' + in_file + '.gz')
        if ret != 0:
            print "Error: non-zero exit status from gunzip"
            exit(1)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-b", "--brs-only",
                        action="store_true", dest="brs_only", default=False,
                        help="Only very the byte ranges. Remember to compile with -DBRS_ONLY")
    (options, args) = parser.parse_args()
    if options.brs_only:
        brs_only()
    else:
        full_test()

