#!/usr/bin/python3

import sys

f = open("/u/wjs/Python/Work/ProofPoint/encoding.txt", 'w')
f.write(sys.getdefaultencoding())
f.close()
