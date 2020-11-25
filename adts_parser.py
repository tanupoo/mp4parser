import sys
import os

# https://wiki.multimedia.cx/index.php/ADTS
# https://wiki.multimedia.cx/index.php/MPEG-4_Audio

profile_map = {
        "00": "Main",
        "01": "LC",     # Low Complexity
        "10": "SSR",    # Scalable Sample Rate
        "11": "LTP",    # Long Term Prediction
        }

freq_index_map = {
        "0000": "96000Hz",
        "0001": "88200Hz",
        "0010": "64000Hz",
        "0011": "48000Hz",
        "0100": "44100Hz",
        "0101": "32000Hz",
        "0110": "24000Hz",
        "0111": "22050Hz",
        "1000": "16000Hz",
        "1001": "12000Hz",
        "1010": "11025Hz",
        "1011": "8000Hz",
        "1100": "7350Hz",
        "1101": "RESERVED",
        "1110": "RESERVED",
        "1111": "EXPLICIT",
        }

ch_conf_map = {
        "000": "PCE",
        "001": "1ch",
        "010": "2ch",
        "011": "3ch",
        "100": "4ch",
        "101": "5ch",
        "110": "5.1ch",
        "111": "7.1ch",
        }

hdrs = {
        "offset": "Offset",
        "version": "Ver",
        "b_crc_absent": "C",
        "profile": "Prof",
        "freq": "Freq",
        "b_private_bit": "P",
        "ch_conf": "Conf",
        "b_originality": "O",
        "b_home": "H",
        "b_crid_bit": "C",
        "b_crid_start": "C",
        "frame_length": "Size",
        "buffer_fullness": "Buffers",
        "nb_aac_frames": "AC",
        }

fmt = "{offset:8} {version:3} {b_crc_absent:1} {profile:4} {freq:8} {b_private_bit:1} {ch_conf:5} {b_originality:1} {b_home:1} {b_crid_bit:1} {b_crid_start:1} {frame_length:6} {buffer_fullness:6} {nb_aac_frames:2}"

def parse_adts(buf, offset=0):
    h = bin(int.from_bytes(buf[:7],"big"))[2:].rjust(56,"0")
    return {
            "offset": offset,
            "version": "MP4" if h[12] == "1" else "MP2",
            "b_crc_absent": h[15], # 0:CRC 1:No-CRC
            "profile": profile_map.get(h[16:18]),
            "freq": freq_index_map.get(h[18:22]),
            "b_private_bit": h[22],
            "ch_conf": ch_conf_map.get(h[23:26]),
            "b_originality": h[26],
            "b_home": h[27],
            "b_crid_bit": h[28],
            "b_crid_start": h[29],
            "frame_length": int(h[30:43],2),
            "buffer_fullness": int(h[43:54],2),
            "nb_aac_frames": 1 + int(h[54:56],2), # nb of AAC frames - 1
            }

def parse_aac(buf, file_size):
    print(fmt.format(**hdrs))
    i = 0
    while i < file_size:
        hdr = parse_adts(buf[i:], i)
        print(fmt.format(**hdr))
        i += hdr["frame_length"]

def search_adts(buf, file_size):
    print(fmt.format(**hdrs))
    i = 0
    while i < file_size:
        if buf[i] == 0xff and buf[i+1] in [0xf0, 0xf1, 0xf8, 0xf9]:
            hdr = parse_adts(buf[i:], i)
            if (hdr["frame_length"] > 7 and
                hdr["freq"] not in ["RESERVED", "EXPLICIT"] and
                hdr["profile"] == "LC" and
                hdr["ch_conf"] not in ["PCE"]):
                print(fmt.format(**hdr))
                i += hdr["frame_length"]
                continue
        # other case
        i += 1

#
# parser main
#
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
ap = ArgumentParser(
        description="a parser for ADTS file.",
        formatter_class=ArgumentDefaultsHelpFormatter)
ap.add_argument("input_file", help="data file.")
ap.add_argument("-r", action="store_true", dest="rip_adts",
                help="enable to search ADTS from the file.")
ap.add_argument("-v", action="store_true", dest="verbose",
                help="enable verbose mode.")
ap.add_argument("-d", action="store_true", dest="debug",
                help="enable debug mode.")
opt = ap.parse_args()

file_size = os.stat(opt.input_file).st_size
print(f"file size: {file_size}")
with open(opt.input_file, "rb") as fd:
    buf = fd.read()
if opt.rip_adts:
    search_adts(buf, file_size)
else:
    parse_aac(buf, file_size)
