"""
Takes in a single har file and outputs a bunch of docs
"""
import sys, os, shutil
import json
from optparse import OptionParser

def get_headers(response_obj):
    headers = {}
    for header in response_obj["headers"]:
        headers[header["name"].lower()] = header["value"].lower()
    return headers

def har2docs(options, in_file, output_dir, site_name):
    compressible_types = ["text", # include all text types
                          "json", # json data
                          "javascript" # javascript can have app as super type
                          ]

    har_data = json.load(open(in_file, 'rb'))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 'pair' cause they are request/response pairs
    for pair in har_data["log"]["entries"]:
        headers = get_headers(pair["response"])

        if options.comp_only:
            if "content-encoding" not in headers or "identity" in headers["content-encoding"]:
                continue

        content = pair["response"]["content"]
        if int(content["size"]) == 0:
            print content
            print "Size 0"
            continue
        if "text" not in content:
            print "No text"
            continue

        c_type = content.get("mimeType", "other/other").split(';')[0]
        if options.comp_types:
            # is the file a compressible type
            comp_type = False
            for ct in compressible_types:
                if ct in c_type:
                    comp_type = True
                    break
            if not comp_type:
                continue

        base_type, sub_type = c_type.split('/', 1)

        # check that output directory exists
        if not os.path.isdir(output_dir + '/' + base_type) and not options.stream:
            os.makedirs(output_dir + '/' + base_type)

        # find a name that hasn't been taken
        counter = 0
        if options.stream:
            out_file = output_dir + '/' + site_name + '_' + c_type.replace('/', '_') + '_'
        else:
            out_file = output_dir + '/' + c_type + '_'
        while os.path.isfile(out_file + str(counter)): counter += 1
        out_file += str(counter)

        # write the data
        with open(out_file, 'w+') as fd:
            if "encoding" in content and content["encoding"] == "base64":
                fd.write(content["text"].decode('base64'))
            else:
                fd.write(content["text"])

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--compressed-only",
                        action="store_true", dest="comp_only", default=False,
                        help="Only get files that were compressed.")
    parser.add_option("-a", "--compressible-types",
                        action="store_true", dest="comp_types", default=False,
                        help="Get files that are compressible type in addition to files that were compressed.")

    parser.add_option("-s", "--stream",
                        action="store_true", dest="stream", default=False,
                        help="Don't make directories for the different content types. Used to make the test stream.")
    (options, args) = parser.parse_args()
    if len(args) != 3:
        print args
        print "Invalid number of args"
        print "Usage: python har2docs [options] <input-har-file> <output-dir> <site-name>"
        exit(1)
    reload(sys)
    sys.setdefaultencoding('utf8')
    har2docs(options, args[0], args[1], args[2])
