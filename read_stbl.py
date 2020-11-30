import sys
import json

def get_stbl(stbl_json, media):
    x = []
    for k,v in stbl_json.items():
        if k.startswith("track") and v["media"] == media:
            x.append(v)
    if len(x) == 0:
        raise ValueError(f"no data for {media}")
    return x

def get_adts_hdr(data_size):
    """
    AAAAAAAA AAAABCCD EEFFFFGH HHIJKLMM MMMMMMMM MMMOOOOO OOOOOOPP
    11111111 11110000 0110000H HH0000MM MMMMMMMM MMM11111 11111100
    """
    hdr_size = 7
    hdr_bin = "1111 1111 1111 0001 0110 000{}0000{}1 1111 1111 1100".format(
            "010", # as 2ch or "001" as 1ch
            bin(hdr_size + data_size)[2:].rjust(13,"0")).replace(" ","")
    return int(hdr_bin,2).to_bytes(hdr_size,"big")

mdat_fmt = "{:4} {:8} {:5} {:5} {:8} {:16}"
mdat_hdr = ("num", "offset", "size", "body", "data", "")

def copy_audio(stbl_json, fd_src, fd_dst):
    print(mdat_fmt.format(*mdat_hdr))
    for x in get_stbl(stbl_json, "audio"):
        sample_num = 0
        for chunk_num,offset in enumerate(x["stco"]):
            fd_src.seek(offset,0)
            for nb_samples in range(x["stsc"][chunk_num]):
                buf = fd_src.read(x["stsz"][sample_num])
                print(mdat_fmt.format(sample_num, offset, x["stsz"][sample_num],
                                 buf[0:4].hex(), buf[4:16].hex()))
                fd_dst.write(get_adts_hdr(len(buf)))
                fd_dst.write(buf)
                sample_num += 1

def copy_video(stbl_json, fd_src, fd_dst):
    print(mdat_fmt.format(*mdat_hdr))
    for x in get_stbl(stbl_json, "video"):
        sample_num = 0
        for chunk_num,offset in enumerate(x["stco"]):
            fd_src.seek(offset,0)
            for nb_samples in range(x["stsc"][chunk_num]):
                buf = fd_src.read(x["stsz"][sample_num])
                body_size = int.from_bytes(buf[0:4],"big")
                print(mdat_fmt.format(sample_num, offset, x["stsz"][sample_num],
                                 body_size, buf[0:4].hex(), buf[4:16].hex()))
                fd_dst.write(buf)
                sample_num += 1

#
# parser main
#
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
ap = ArgumentParser(
        description="stbl box parser.",
        formatter_class=ArgumentDefaultsHelpFormatter)
# 5301  python read_stbl.py stbl.dmp test2.mp4 audio.dmp

ap.add_argument("stbl_file", help="filename of the stbl box in JSON.")
ap.add_argument("-i", action="store", dest="mp4_file",
                help="specify the file name that contained the stbl box.")
ap.add_argument("-m", action="store_true", dest="mdat_file",
                help="specify that the file is mdat box, instaed of MP4 file.")
ap.add_argument("--audio-file", action="store", dest="audio_file",
                help="specify a file name to be stored the audio data.")
ap.add_argument("--video-file", action="store", dest="video_file",
                help="specify a file name to be stored the video data.")
ap.add_argument("-v", action="store_true", dest="verbose",
                help="enable verbose mode.")
ap.add_argument("-d", action="store_true", dest="debug",
                help="enable debug mode.")
opt = ap.parse_args()

with open(opt.stbl_file) as fd:
    stbl_json = json.load(fd)

if opt.audio_file:
    with open(opt.audio_file,"wb") as fd_dst:
        with open(opt.mp4_file,"rb") as fd_src:
            copy_audio(stbl_json, fd_src, fd_dst)

if opt.video_file:
    with open(opt.video_file,"wb") as fd_dst:
        with open(opt.mp4_file,"rb") as fd_src:
            copy_video(stbl_json, fd_src, fd_dst)

