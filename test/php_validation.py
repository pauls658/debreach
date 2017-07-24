import os, sys
import random
import math
import pycurl
import shutil
from StringIO import StringIO

class TestCase(object):
    DEBREACH_FNC = "d_echo"
    APACHE_DIR = "/usr/local/apache2/htdocs"
    SERVER_ROOT = "debreach_validation"
    SERVER_NAME = "localhost"
    TMP_DIR = "/tmp" + "/" + SERVER_ROOT
    SPECIAL_DECOMP = "/home/pauls658/blib-better/minigzip"
    """
    @param data_file type:string the path to the data file
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


    def run(self):
        self.make_php_file()
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

    def make_php_file(self):
        self.php_fp = TestCase.APACHE_DIR + "/" + self.resource_path
        file_buf = open(self.data_file, "rb").read()
        with open(self.php_fp, "wb+") as out_fd:
            tainted = False
            start = 0
            out_fd.write("<?php\n require_once(\"debreach.php\");\n")
            for i in range(len(self.brs)):
                end = self.brs[i]
                if tainted:
                    out_fd.write(TestCase.DEBREACH_FNC + "(" + \
                            self.php_lit_string(file_buf[start:end+1]) + \
                            ");\n")
                else:
                    # file_buf[end] is tainted
                    out_fd.write("echo " + \
                            self.php_lit_string(file_buf[start:end]) + \
                            ";\n")
                start = end + 1
                tainted = not tainted
            # finish it off
            out_fd.write("echo " + \
                    self.php_lit_string(file_buf[start:len(file_buf)]) + ";\n")
            out_fd.write("?>")
        self.created_files.append(self.php_fp)
                
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
        
        ret = []
        for start, end in brs:
            ret.append(start)
            ret.append(end)
        return ret

"""
    Gets rid of the files from previous iterations.
"""
def pre_cleaning():
    for f in os.listdir(TestCase.TMP_DIR):
        os.remove(TestCase.TMP_DIR + "/" + f)
    for f in os.listdir(TestCase.APACHE_DIR + "/" + TestCase.SERVER_ROOT):
        os.remove(TestCase.APACHE_DIR + "/" + TestCase.SERVER_ROOT + "/" + f)


if __name__ == "__main__":
    pre_cleaning()
    TCMker = TestCaseMaker("input")
    test_case = TCMker.real_testcase()
    test_case.run()
