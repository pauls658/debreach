"""
Intention of this script:
    - Calculate compression ratios for debreach
    - Calculate compression ratios for standard gzip
    - Compare the rations

If we run the script using string based tainting, the tokens
found in the site's corresponding tokens file will be used as
the unsafe strings. The input file will be searched for the
tokens, and those that are found will be passed to the
compressor.

If we run the script using byte range based tainting, we will
generate random byte ranges for each input file. We don't care
about testing with byte ranges of unsafe data because it will
be the same as string based tainting.

The statistics we output are like this:
site        | zlib      | debreach
---------------------------------------
reddit      | .5        | .55
---------------------------------------
facebook    | .6        | .65

Where the numbers are the average compression ratios using
the listed compressor.
"""
import os, math, mmap, re, random
import pickle
from collections import defaultdict
from prettytable import PrettyTable
from optparse import OptionParser

GOLD_COMP = "../minigzip -h"
INPUT_DIR="input"
TOKENS_DIR="tokens"
TOKEN_RE_FILE = "test_data/token_res"

def trace(msg, level=5):
    print msg

def clear_dirs():
    os.popen('rm -f output/* &> /dev/null')
    os.popen('rm -f output_lits/* &> /dev/null')
    os.popen('rm -f debug/* &> /dev/null')
    os.popen('rm -f brs/* &> /dev/null')
    os.popen('rm -f lz77_brs/* &> /dev/null')

"""
writes the results as a csv for later processing
"""
def write_results(options, gold_data, debreach_data):
    # first do zlib
    pickle.dump(gold_data, open("gold_dump", "wb"))
    # the debreach
    pickle.dump(debreach_data, open("debreach_dump", "wb"))
    # and thats it!
    
def print_tot_expansion(options, gold_data, debreach_data):
    table = PrettyTable(["site", "zlib size", "debreach size", "zlib cr", "debreach cr", "exapansion"])
    for site_name, z_data in gold_data.iteritems():
        d_data = debreach_data[site_name]
        zlib_size = sum(x[1] for x in z_data)
        debreach_size = sum(x[1] for x in d_data)
        orig_size = sum(x[2] for x in d_data)
        d_cr = float(debreach_size)/float(orig_size)
        z_cr = float(zlib_size)/float(orig_size)
        expansion = float(debreach_size - zlib_size)/float(zlib_size)
        table.add_row([site_name, str(zlib_size), str(debreach_size), str(z_cr), str(d_cr), str(expansion)])
    print table

def print_diffs(options, gold_crs, debreach_crs, test_files):
    table = PrettyTable(["site", "min loss", "avg. loss", "max loss"])
    for site_name, crs_gold in gold_crs.iteritems():
        crs_debreach = debreach_crs[site_name]
        diffs = []
        for i, (in_file, cr) in enumerate(crs_gold):
            if in_file != crs_debreach[i][0]:
                print "Error: file mismatch"
                print "zlib file: %s, debreach file: %s" % (in_file, crs_debreach[i][0])
                exit(1) 

            debreach_cr = crs_debreach[i][1]
            if cr == debreach_cr:
                diffs.append((in_file, float(0)))
            else:
                diff = debreach_cr - cr
                if diff < 0:
                    diffs.append((in_file, float(0)))
                else:
                    diffs.append((in_file, diff))
        avg = math.fsum(diff for _, diff in diffs)/float(len(diffs))
        max_diff = max(diffs, key=lambda x: x[1])
        min_diff = min(diffs, key=lambda x: x[1])
        table.add_row([site_name, str(min_diff[1]), str(avg), str(max_diff[1])])
        trace("%s min size file: %s, size: %4f" % (site_name, min_diff[0], min_diff[1]))
        trace("%s max size file: %s, size: %4f" % (site_name, max_diff[0], max_diff[1]))
    print table

def print_crs(options, gold_crs, debreach_crs):
    table = PrettyTable(["site", GOLD_COMP, "debreach", "cr loss"])
    for site_name, cr in gold_crs.iteritems():
        table.add_row([site_name, str(gold_crs[site_name]),
            str(debreach_crs[site_name]), str(debreach_crs[site_name] - gold_crs[site_name])])
    print table

"""
Return value depends on options. If options.diff, then returns a dictionary of lists with tuples containing the cr for each file and the file name. Otherwise, automatically averages the crs, which turns it into a dictionary of floats. Key is always the site name.
"""
def do_zlib(options, test_files):
    crs = {}

    for in_file in test_files:
        if ".gz" in in_file: continue

        fp = INPUT_DIR + "/" + in_file
        site_name = in_file.split("_")[0]

        if site_name not in crs: crs[site_name] = []

        orig_size = os.path.getsize(fp)
        
        ret = os.system(GOLD_COMP + " " + fp)
        if ret != 0:
            print "Error: " + GOLD_COMP + " returned non-zero exit\
            status: " + str(ret)
            exit(1)

        comp_size = os.path.getsize(fp + ".gz")

        os.remove(fp + ".gz") 

        crs[site_name].append((in_file, comp_size, orig_size))

    return crs

def find_tokens(input_file, tokens):
    found_tokens = set()
    with open(input_file, 'rb') as f_ref:
        # 0 means the whole file
        mf = mmap.mmap(f_ref.fileno(), 0, prot=mmap.PROT_READ)
        mf.seek(0)
        for match in re.finditer(r'|'.join(re.escape(token) for token in tokens), mf):
            found_tokens.add(match.group(0))
    return found_tokens

def random_brs(file_size, coverage):
    if coverage >= 1.0:
        return [(0, file_size - 1)]
    elif coverage <= 0.0:
        return [(0,0)]

    # .0025 gives us 400 chunks
    chunk_size = int(math.ceil(file_size*0.0025))
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

def coverage(file_size, brs):
    covered = 0
    for start, end in brs:
        covered += end - start - 1
    return float(covered) / float(file_size)

#def random_brs(file_size, coverage=0.1):
#    remaining_bytes = xrange(file_size)
#    if coverage > 1.0:
#        coverage = 1.0
#    elif coverage <= 0.0:
#        return [(0,0)]
#    tainted_bytes = sorted(random.sample(remaining_bytes, int(coverage*file_size)))
#    brs = []
#    last = tainted_bytes[0]
#    first = tainted_bytes[0]
#    for byte in tainted_bytes[1:]:
#        # if byte == last -1
#        # we are in the same byte range
#        if byte != last - 1:
#            # close the last byte range
#            brs.append((first, last))
#            # start a new one
#            first = byte
#
#        last = byte
#
#    # close the last byte range
#    brs.append((first, last))
#    return brs

"""

"""
INC = .1
def do_debreach_brs(options, test_files):
    global INC
    clear_dirs()

    taint_prop = 0.1
    
    crs = {}
    while taint_prop <= 1.0:
        print taint_prop
        for in_file in test_files:
            print in_file
            if in_file.endswith('.gz'): continue
    
            fp = INPUT_DIR + "/" + in_file
            [site_name, n1] = in_file.split('_')[:2]

            if site_name not in crs: crs[site_name] = {}
            if taint_prop not in crs[site_name]: crs[site_name][taint_prop] = []
    
            orig_size = os.path.getsize(fp)

            byte_ranges = random_brs(orig_size, taint_prop)
            br_arg = ','.join(str(s) + ',' + str(e) for (s, e) in byte_ranges)
            print "../minidebreach -b " + br_arg + " " + fp + " 2> debug/" + in_file
            ret = os.system("../minidebreach -b " + br_arg + " " + fp + " 2> debug/" + in_file)
            if ret != 0:
                print "Error: non-zero exit status from minidebreach: " + str(ret)
                for line in open("debug/" + in_file, 'rb'):
                    print line
                exit(1)
    
            comp_size = os.path.getsize(fp + ".gz")
    
            crs[site_name][taint_prop].append((in_file, comp_size, orig_size))
    
            os.remove(fp + ".gz")
        taint_prop += INC

    return crs

"""
Return value depends on options. If options.diff, then returns a dictionary of lists with tuples containing the cr for each file and the file name. Otherwise, automatically averages the crs, which turns it into a dictionary of floats. Key is always the site name.
"""
def do_debreach_string(options, test_files):
    clear_dirs()

    all_tokens = defaultdict(set)
    for site_name in os.listdir(TOKENS_DIR):
        for line in open(TOKENS_DIR + "/" + site_name, 'rb'):
            line = line.strip()
            all_tokens[site_name].add(line)

    crs = {}

    for in_file in test_files:
        if in_file.endswith('.gz'): continue

        fp = INPUT_DIR + "/" + in_file
        [site_name, n1] = in_file.split('_')[:2]
        if "crafted" in site_name:
            present_tokens = find_tokens(fp, all_tokens[n1])
        else:
            present_tokens = find_tokens(fp, all_tokens[site_name])

        if site_name not in crs: crs[site_name] = []

        orig_size = os.path.getsize(fp)

        unsafe_arg = ",".join(present_tokens)
        print "../minidebreach -s '" + unsafe_arg + "' " + fp + " 2> debug/" + in_file
        ret = os.system("../minidebreach -s '" + unsafe_arg + "' " + fp + " 2> debug/" + in_file)
        if ret != 0:
            print "Error: non-zero exit status from minidebreach: " + str(ret)
            for line in open("debug/" + in_file, 'rb'):
                print line
            exit(1)

        comp_size = os.path.getsize(fp + ".gz")

        crs[site_name].append((in_file, comp_size, orig_size))

        os.remove(fp + ".gz")

    return crs

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--string",
                        action="store_true", dest="string", default=False,
                        help="Taint data using strings")
    parser.add_option("-b", "--byte-ranges",
                        action="store_true", dest="brs", default=False,
                        help="Taint data using random byte ranges. Byte ranges will be random.")
    parser.add_option("-d", "--diffs",
                        action="store_true", dest="diffs", default=False,
                        help="Print the average differences rather than average crs for each method")
    parser.add_option("-e", "--tot-expansion",
                        action="store_true", dest="tot_expansion", default=False,
                        help="Print the total expansion.")
    parser.add_option("-w", "--write-results",
                        action="store_true", dest="write_results", default=False,
                        help="Write results to file")
    (options, args) = parser.parse_args()
    
    clear_dirs()
    test_files = list(os.listdir(INPUT_DIR))
    # Always calculate the gold zlib cr's
    gold_data = do_zlib(options, test_files) 

    if options.string:
        debreach_data = do_debreach_string(options, test_files)
    elif options.brs:
        debreach_data = do_debreach_brs(options, test_files)
    else:
        print "What do you even want me to do?!?!?"
        exit(1)

# put your hack scripts here
#    for site_name, z_data in gold_data.iteritems():
#        d_data = debreach_data[site_name]
#        diffs = []
#        for i, file_data in enumerate(z_data):
#            diffs.append((file_data[0], d_data[i][1] - file_data[1], file_data[2]))
#        m = max(diffs, key=lambda x: x[1])
#        print m

    if options.diffs:
        print "gotta update this diffs func man"
        exit(1)
    elif options.write_results:
        if options.string:
            print "implement me"
        elif options.brs:
            pass
            #write_results(options, gold_data, debreach_data)
        else:
            print "wat how did i get here"
    elif options.tot_expansion:
        print_tot_expansion(options, gold_data, debreach_data)
    else:
        print "need to update the cr func"
        exit(1)
