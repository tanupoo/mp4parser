import sys
import os
from adts_parser import parse_adts, adts_hdr, adts_fmt

def read_mdat(buf, file_size):
    print(adts_fmt.format(**adts_hdr))
    i = 0
    while i < file_size:
        if buf[i] == 0xff and buf[i+1] in [0xf0, 0xf1, 0xf8, 0xf9]:
            hdr = parse_adts(buf[i:])
            if (hdr["frame_length"] > 7 and
                hdr["freq"] not in ["RESERVED", "EXPLICIT"] and
                hdr["profile"] == "LC" and
                hdr["ch_conf"] not in ["PCE"]):
                hdr.update({"offset":i})
                print(adts_fmt.format(**hdr))
                i += hdr["frame_length"]
                continue
        elif buf[i:i+3] == b"\x00\x00\x00":
            print(buf[i:i+4].hex(), buf[i+4:i+8].hex())
        # other case
        i += 1

#
# parser main
#
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
ap = ArgumentParser(
        description="mdat parser.",
        formatter_class=ArgumentDefaultsHelpFormatter)
ap.add_argument("input_file", help="data file.")
ap.add_argument("-v", action="store_true", dest="verbose",
                help="enable verbose mode.")
ap.add_argument("-d", action="store_true", dest="debug",
                help="enable debug mode.")
opt = ap.parse_args()

file_size = os.stat(opt.input_file).st_size
print(f"file size: {file_size}")
buf = open(opt.input_file, "rb").read()
read_mdat(buf, file_size)
