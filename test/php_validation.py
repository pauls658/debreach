import os, sys
import random
import math
import pycurl
import shutil
import filecmp
from StringIO import StringIO

class TestCase(object):
    DEBREACH_FNC = "d_echo"
    APACHE_DIR = "/var/www/html"
    SERVER_ROOT = "debreach_validation"
    SERVER_NAME = "node1"
    TMP_DIR = "/tmp" + "/" + SERVER_ROOT
    SPECIAL_DECOMP = "/users/umdsectb/blib-better-validate/minigzip"
    """
    @param data_file type:string the path to the data file
    @param brs type:list of ints
    """
    def __init__(self, data_file, brs):
        # the absolute path to the file
        self.data_file = data_file
        # just the file name
        self.file_name = data_file.split("/")[-1]
        # the path to the file on the server
        self.resource_path = TestCase.SERVER_ROOT + "/" + self.file_name + ".php"
        # the tainted byte ranges
        self.brs = brs
        #ugh
        self.brs_tuples = []
        for i in range(0, len(self.brs), 2):
            self.brs_tuples.append((self.brs[i], self.brs[i+1]))
        # where we put the php file
        self.php_fp = None
        # where we save the server's compressed response
        self.response_fp = None
        # where we put the byte ranges output by the decompressor when
        # decompressing the server's response
        self.brs_file = None
        # files to delete when we are done
        self.created_files = []

        self.debug_tainted_data()

    def debug_tainted_data(self):
        buf = open(self.data_file, "rb").read()
        with open(self.TMP_DIR + "/tainted_data", "wb+") as out_fd:
            for i in range(0,len(self.brs), 2):
                out_fd.write(buf[self.brs[i]:self.brs[i+1]+1])
                out_fd.write("\n############################ ( %d - %d ) #########################\n" % (self.brs[i], self.brs[i+1]))


    def run_validation(self):
        self.make_php_debreach_file()
        self.curl_from_server()
        self.validate()

    def cleanup(self):
        for f in self.created_files:
            try:
                os.remove(f)
            except OSError as e:
                if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
                    raise # re-raise exception if a different error occurred
                print "Could not remove " + f + ": file not found"

    @staticmethod
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
    
    @staticmethod
    def validate_sec_brs(tainted_brs, match_brs_file):
        match_brs = TestCase.read_brs(match_brs_file)
        return not TestCase.overlaps(tainted_brs, match_brs)
  
    @staticmethod
    def overlaps(brs1, brs2):
        for (s1, e1) in brs2:
            for (s2, e2) in brs1:
                if  min(e1, e2) >= max(s1, s2):
                    print str(s1) + '-' + str(e1)
                    print str(s2) + '-' + str(e2)
                    return True
        return False
    
    def validate(self):
        # decompress the response, and save the decompressor's output
        self.brs_file = TestCase.TMP_DIR + "/" + self.file_name + ".brs"
        self.created_files.append(self.brs_file)
        cmd = TestCase.SPECIAL_DECOMP + " -d " + self.response_fp + " 2> " + \
                        self.brs_file
        print "command: " + cmd
        ret = os.system(cmd)
        if ret != 0:
            print "Error: non-zero exit status from " + TestCase.SPECIAL_DECOMP
            print "return: " + str(ret)
            exit(1)

        if not filecmp.cmp(TestCase.TMP_DIR + "/" + self.file_name, self.data_file):
            raise Exception("Input data file and server response do not match")

        if not TestCase.validate_sec_brs(self.brs_tuples, self.brs_file):
            raise Exception("Validation test failed. Leaving files for debugging")

    def curl_from_server(self):
        headers = {}
        def header_function(header_line):
            # HTTP standard specifies that headers are encoded in iso-8859-1.
            # On Python 2, decoding step can be skipped.
            # On Python 3, decoding step is required.
            header_line = header_line.decode('iso-8859-1')
        
            # Header lines include the first status line (HTTP/1.x ...).
            # We are going to ignore all lines that don't have a colon in them.
            # This will botch headers that are split on multiple lines...
            if ':' not in header_line:
                return
        
            # Break the header line into header name and value.
            name, value = header_line.split(':', 1)
        
            # Remove whitespace that may be present.
            # Header lines include the trailing newline, and there may be whitespace
            # around the colon.
            name = name.strip()
            value = value.strip()
        
            # Header names are case insensitive.
            # Lowercase name here.
            name = name.lower()
        
            # Now we can actually record the header name and value.
            headers[name] = value

        c = pycurl.Curl()

        url = "http://" + TestCase.SERVER_NAME + "/" + self.resource_path
        c.setopt(c.URL, url)


        c.setopt(c.HTTPHEADER, ["Accept-Encoding: gzip"])

        c.setopt(c.HEADERFUNCTION, header_function)

        self.response_fp = TestCase.TMP_DIR + "/" + self.file_name + ".gz"
        with open(self.response_fp, "wb+") as fd:
            c.setopt(c.WRITEFUNCTION, fd.write)
            c.perform()
            c.close()
        self.created_files.append(self.response_fp)

        with open(self.response_fp + ".headers", "wb+") as fd:
            for header, value in headers.iteritems():
                fd.write("%s: %s\n" % (header, value))
        self.created_files.append(self.response_fp + ".headers")

    @staticmethod
    def php_lit_string(string):
        return "'" + \
                string.replace("\\", "\\\\").replace("'", "\\'") + \
                "'"

    def make_php_debreach_file(self):
        self.php_fp = TestCase.APACHE_DIR + "/" + self.resource_path
        self.zlib_php_fp = TestCase.APACHE_DIR + "/" + \
                TestCase.SERVER_ROOT + "/zlib_" + self.file_name + ".php"
        file_buf = open(self.data_file, "rb").read()
        debreach_tmp = TestCase.TMP_DIR + "/debreach_tmp.php"
        zlib_tmp = TestCase.TMP_DIR + "/zlib_tmp.php"
        with open(debreach_tmp, "wb+") as out_debreach_fd, open(zlib_tmp, "wb+") as out_zlib_fd:
            # first create the zlib file
            out_zlib_fd.write("<?php\necho " + self.php_lit_string(file_buf) + ";\n?>")

            tainted = False
            start = 0
            out_debreach_fd.write("<?php\n require_once(\"debreach.php\");\n")
            for i in range(len(self.brs)):
                end = self.brs[i]
                if tainted:
                    out_debreach_fd.write(TestCase.DEBREACH_FNC + "(" + \
                            self.php_lit_string(file_buf[start:end + 1]) + \
                            ");\n")
                    start = end + 1
                else:
                    # file_buf[end] is tainted
                    out_debreach_fd.write("echo " + \
                            self.php_lit_string(file_buf[start:end]) + \
                            ";\n")
                    start = end 
                tainted = not tainted
            # finish it off
            out_debreach_fd.write("echo " + \
                    self.php_lit_string(file_buf[start:len(file_buf)]) + ";\n")
            out_debreach_fd.write("?>")
        os.system("scp %s %s:%s" % (debreach_tmp, TestCase.SERVER_NAME, self.php_fp))
        os.system("scp %s %s:%s" % (zlib_tmp, TestCase.SERVER_NAME, self.zlib_php_fp))
        os.remove(debreach_tmp)
        os.remove(zlib_tmp)
        self.created_files.append(self.php_fp)
        self.created_files.append(self.zlib_php_fp)
                
class TestCaseMaker(object):
    """ A class for making these dumb ole files of random junk."""

    """
    @param data_dir type:string a directory containing 
    """
    def __init__(self, data_dir):
        if os.path.isdir(data_dir):
            if os.listdir(data_dir):
                self.data_dir = data_dir.rstrip("/")
            else:
                raise Exception("There is nothing in " + data_dir)
        else:
            raise Exception(data_dir + " is not a directory!")

    def real_testcase(self):
        files = os.listdir(self.data_dir)
        real_file = self.data_dir + "/" + random.choice(files)
        size = os.path.getsize(real_file)
        brs = self.random_brs(size)
        return TestCase(real_file, brs)
    
    @staticmethod
    def delete_overlaps(brs):
        if len(brs) == 2:
            return brs

        ret = [brs[0]]
        prev_end = brs[1]
        for i in range(2, len(brs), 2):
            # brs[i] is start
            # brs[i + 1]= end
            if prev_end >= brs[i]:
                if prev_end >= brs[i + 1]:
                    # enclosed whole br
                    continue
                else:
                    prev_end = brs[i + 1]
            else:
                ret.append(prev_end)
                ret.append(brs[i])
                prev_end = brs[i+1]
        if prev_end > brs[-1]:
            ret.append(prev_end)
        else:
            ret.append(brs[-1])

        return ret
 

    def random_brs(self, file_size, coverage=0.1, max_len=300, min_len=3):
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
        
        untupled = []
        for start, end in brs:
            untupled.append(start)
            untupled.append(end)

        return self.delete_overlaps(untupled)

"""
    Gets rid of the files from previous iterations.
"""
def pre_cleaning():
    for f in os.listdir(TestCase.TMP_DIR):
        os.remove(TestCase.TMP_DIR + "/" + f)
    os.system('ssh %s "rm %s/%s/*"' % (TestCase.SERVER_NAME, TestCase.APACHE_DIR, TestCase.SERVER_ROOT))


def random_testcase():
    pre_cleaning()
    TCMker = TestCaseMaker("input")
    test_case = TCMker.real_testcase()
    test_case.run()

def retest():
    pre_cleaning()
    tc = TestCase("input/facebook_text_css_22",
            [366,556,1691,1722,4312,4513,5903,6165,8732,8911,9996,10168,10883,11153,11943,11962,12163,12176,14627,14971,16862,17039,18097,18276,18659,18687,18753,19019,20701,20855,20875,20888,21575,21673,22012,22083,24098,24305,25400,25529,25617,25854,33271,33500,35336,35391,37592,37763,38691,38778,40047,40147,40911,41043,42434,42677,43828,44054,44077,44107,44880,45134,45804,45956,46275,46325,50315,50389,50566,50744,53183,53358,55059,55121,57099,57163,57705,57731])
    tc.run()

if __name__ == "__main__":
    pre_cleaning()
    TCMker = TestCaseMaker("input")
    test_case = TCMker.real_testcase()
    test_case.make_php_debreach_file()
