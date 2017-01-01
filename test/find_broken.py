good = "facebook_good"
bad = "facebook_broken"

with open(good, 'rb') as gfd, open(bad, 'rb') as bfd:
    counter = 0
    while 1:
        g = gfd.read(1)
        b = bfd.read(1)
        if not g or not b:
            break

        if g == b:
            counter += 1
        else:
            break
    print counter
