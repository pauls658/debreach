import os, sys
import random
import math
import pycurl
import shutil
import filecmp
import time
from prettytable import PrettyTable
from StringIO import StringIO

class TestCase(object):
    # ALL OF THESE NEED TO BE SET FOR EACH SERVER 
    DEBREACH_FNC = "d_echo"
    APACHE_DIR = "/usr/local/apache2/htdocs"
    SERVER_ROOT = "debreach_validation"
    SERVER_NAME = "localhost"
    TMP_DIR = "/tmp" + "/" + SERVER_ROOT
    SPECIAL_DECOMP = "/home/brandon/blib-better/minigzip"

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
        self.zlib_resource_path = TestCase.SERVER_ROOT + "/zlib_" + self.file_name + ".php"
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
    
    @staticmethod
    def favg(arr):
        return math.fsum(arr) / float(len(arr))

    def run_resp_time_bench(self, iters):
        self.make_php_debreach_file()
        os.system('ssh node1 "sudo a2enmod -f debreach; sudo a2dismod -f deflate; sudo service apache2 restart"')
        time.sleep(1)
        debreach_url = "http://%s/%s" % (TestCase.SERVER_NAME, self.resource_path)
        debreach_results = self.run_benchmark_on_url(debreach_url, iters)
        debreach_times = debreach_results["timings"]

        os.system('ssh node1 "sudo a2dismod -f debreach; sudo a2enmod -f deflate; sudo service apache2 restart"')
        time.sleep(1)
        zlib_url = "http://%s/%s" % (TestCase.SERVER_NAME, self.zlib_resource_path)
        zlib_results = self.run_benchmark_on_url(zlib_url, iters)
        zlib_times = zlib_results["timings"]
 
        table = PrettyTable(["metric", "zlib", "debreach"])
        for key in debreach_times[0].keys():
            d_avg = self.favg([item[key] for item in debreach_times])
            z_avg = self.favg([item[key] for item in zlib_times])
            table.add_row([key, str(z_avg), str(d_avg)])
        for key in filter(lambda x: "timings" not in x, debreach_results.keys()):
            table.add_row([key, str(zlib_results[key]), str(debreach_results[key])])

        print table


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

    def run_benchmark_on_url(self, url, iters):
        req_headers = ["Accept-Encoding: gzip",
                "Cache-Control: no-cache, no-store, must-revalidate",
                "Pragma: no-cache",
                "Expires: 0"]
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.HTTPHEADER, req_headers)
        global size
        size = 0
        def count_size(x):
            global size
            size += len(x)
        c.setopt(c.WRITEFUNCTION, count_size)
        size = float(size)
        # burn one request
        c.perform()
        c.close()
        indiv_results = []
        for i in range(iters):
            c = pycurl.Curl()
            c.setopt(c.URL, url)
            c.setopt(c.HTTPHEADER, req_headers)
            c.setopt(c.WRITEFUNCTION, lambda x: None)
            c.perform()
            result = {
                    "total_time" : c.getinfo(pycurl.TOTAL_TIME),
                    "first_byte" : c.getinfo(pycurl.STARTTRANSFER_TIME)
                    }
            result["xfer_rate"] = size / float(result["total_time"] - result["first_byte"])
            c.close()
            indiv_results.append(result)
            time.sleep(0.001)
        orig_size = os.path.getsize(self.data_file)
        return {
                "orig_size" : orig_size,
                "comp_size" : size,
                "comp_ratio" : float(size)/float(orig_size),
                "timings" : indiv_results
                }

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
        self.zlib_php_fp = TestCase.APACHE_DIR + "/" + self.zlib_resource_path
        file_buf = open(self.data_file, "rb").read()
        debreach_tmp = TestCase.TMP_DIR + "/debreach_tmp.php"
        zlib_tmp = TestCase.TMP_DIR + "/zlib_tmp.php"
        with open(debreach_tmp, "wb+") as out_debreach_fd, open(zlib_tmp, "wb+") as out_zlib_fd:
            # first create the zlib file
            #out_zlib_fd.write("<?php\necho " + self.php_lit_string(file_buf) + ";\n?>")

            tainted = False
            start = 0
            out_debreach_fd.write("<?php\n require_once(\"debreach.php\");\n")
            out_zlib_fd.write("<?php\n")
            for i in range(len(self.brs)):
                end = self.brs[i]
                if tainted:
                    out_debreach_fd.write(TestCase.DEBREACH_FNC + "(" + \
                            self.php_lit_string(file_buf[start:end + 1]) + \
                            ");\n")
                    out_zlib_fd.write("echo " + \
                            self.php_lit_string(file_buf[start:end + 1]) + \
                            ";\n")
                    start = end + 1
                else:
                    # file_buf[end] is tainted
                    out_debreach_fd.write("echo " + \
                            self.php_lit_string(file_buf[start:end]) + \
                            ";\n")
                    out_zlib_fd.write("echo " + \
                            self.php_lit_string(file_buf[start:end]) + \
                            ";\n")
                    start = end 
                tainted = not tainted
            # finish it off
            out_debreach_fd.write("echo " + \
                    self.php_lit_string(file_buf[start:len(file_buf)]) + ";\n")
            out_debreach_fd.write("?>")
            out_zlib_fd.write("echo " + \
                    self.php_lit_string(file_buf[start:len(file_buf)]) + ";\n")
            out_zlib_fd.write("?>")
        os.system("scp %s %s:%s" % (debreach_tmp, TestCase.SERVER_NAME, self.php_fp))
        os.system("scp %s %s:%s" % (zlib_tmp, TestCase.SERVER_NAME, self.zlib_php_fp))
        os.remove(debreach_tmp)
        os.remove(zlib_tmp)
        self.created_files.append(self.php_fp)
        self.created_files.append(self.zlib_php_fp)

def get_files_with_file_size(dirname, reverse=False):
    """ Return list of file paths in directory sorted by file size """

    # Get list of files
    filepaths = []
    for basename in os.listdir(dirname):
        filename = os.path.join(dirname, basename)
        if os.path.isfile(filename):
            filepaths.append(filename)

    # Re-populate list with filename, size tuples
    for i in xrange(len(filepaths)):
        filepaths[i] = (filepaths[i], os.path.getsize(filepaths[i]))

    # Sort list by file size
    # If reverse=True sort from largest to smallest
    # If reverse=False sort from smallest to largest
    filepaths.sort(key=lambda filename: filename[1], reverse=reverse)

    return filepaths

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

    def html_by_size(self, size):
        """
        Gets the html file that is closest to but not less than size.
        """
        filename = None
        files = filter(lambda x: "html" in x[0], get_files_with_file_size(self.data_dir, reverse=True))

        if files[0][1] < size:
            filename = files[0][0]
        else:
            i = 0
            while i < len(files):
                if files[i][1] < size:
                    i -= 1
                    break
                else:
                    i += 1
            filename = files[i][0]

        brs = self.random_brs(size)
        return TestCase(filename, brs)

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
    test_case.run_validation()

def retest():
    pre_cleaning()
    tc = TestCase("input/facebook_text_css_22",
            [366,556,1691,1722,4312,4513,5903,6165,8732,8911,9996,10168,10883,11153,11943,11962,12163,12176,14627,14971,16862,17039,18097,18276,18659,18687,18753,19019,20701,20855,20875,20888,21575,21673,22012,22083,24098,24305,25400,25529,25617,25854,33271,33500,35336,35391,37592,37763,38691,38778,40047,40147,40911,41043,42434,42677,43828,44054,44077,44107,44880,45134,45804,45956,46275,46325,50315,50389,50566,50744,53183,53358,55059,55121,57099,57163,57705,57731])
    tc.run()

def bench():
    pre_cleaning()
    TCMker = TestCaseMaker("input")
    test_case = TCMker.html_by_size(200000)
    test_case.run_resp_time_bench(1000)

if __name__ == "__main__":
    test_case = TestCase("input/facebook_text_css_20",
            [1133,1359,3716,3884,5031,5186,5732,5926,6249,6322,6501,6768,7194,7309,7399,7575,8321,8552,9129,9214,9595,9658,11216,11406,12727,12872,14503,14778,15506,15569,19541,19780,21555,21670,22183,22298,22591,22616,24552,24582,26857,27135,27614,27701,31579,31790,31855,32101,32323,32676,33822,33975,34271,34374,35332,35413,36916,36941,37220,37289,38522,38698,43771,43981,45236,45346,55649,55716,57927,58185,58370,58457,59689,59845,60312,60408,62059,62149,64563,64851,65085,65228,65321,65396,69890,69909,72735,72759,74031,74135])
    test_case.make_php_debreach_file()
