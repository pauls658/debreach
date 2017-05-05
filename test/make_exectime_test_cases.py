"""
Makes random byte range test cases for measuring execution time.
"""
import os, mmap, re, math, random
import glob
from collections import defaultdict
from optparse import OptionParser


INPUT = 'input'
TEST_CASE_STREAM = 'stream'
TOKENS_DIR = 'tokens'
INC=0.1

def test_case_line(filename, arg):
        return " %s %s/%s\n" % (','.join("%d,%d" % (start, end) for start, end in arg), INPUT, filename)

# .0025 gives us 400 chunks
CHUNK_PROP = 0.0025
def random_brs(file_size, coverage):
    if coverage >= 1.0:
        return [(0, file_size - 1)] 
    elif coverage <= 0.0:
        return [(0,0)]

    chunk_size = int(math.ceil(file_size*CHUNK_PROP))
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

def make_test_cases(in_dir):
    coverage = 0.0
    
    sitenames = set(filename.split('_')[0] for filename in os.listdir(in_dir))
    while coverage <= 1.0:
        for sitename in sitenames:
            file_buf = ""
            for fp in glob.glob(in_dir + "/" + sitename + "*"):
                in_file = fp.split("/")[-1]
                filesize = os.path.getsize(fp)
                brs = random_brs(filesize, coverage)
        
                file_buf += test_case_line(in_file, brs)
        
            stream_id = int(round(coverage*10))
            with open(TEST_CASE_STREAM + "_" + sitename + "_" + str(stream_id), 'w+') as out_fd:
                out_fd.write(file_buf)

        coverage += 0.1

if __name__ == "__main__":
    make_test_cases(INPUT)
