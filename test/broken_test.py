import os

brs_str = "471,558,845,957,1629,1924,6147,6256,6735,6979,7519,7703,9963,10030,12731,12883,16337,16619,16747,16910,20619,20879,20657,20871,20662,20932,22810,22953,22985,23196,24085,24296,24500,24671"
f_name = "facebook_image_jpeg_278"
brs = brs_str.split(',')
for i in reversed(range(0,len(brs),2)):
    os.system("../minidebreach -b " + ",".join(brs[:i]) + " input/" + f_name)
    os.system("mv input/" + f_name + ".gz .")
    ret = os.system("gunzip " + f_name + ".gz")
    if ret == 0:
        print brs[:i]
        break
